#!/usr/bin/env python3
"""
check_bootstrap_assets.py -- part of at_have_ryggen_fri.

bootstrap/web/ holds two different kinds of asset the technician's PXE/USB
bootstrap kit depends on, with two different required-ness rules -- neither
of which is "just check the IP" (192.168.139.50 isn't a fixed host at all;
README.md confirms it's a role a technician's laptop assumes temporarily
via static-web-server.exe, so there's nothing fixed to detect):

  Tier 1 (bootstrap/web/proxmox/*.toml -- Proxmox unattended-install answer
  files): always required, no soft mode, ever. Derived from
  select-pve-answer.sh's own site_prefix/variant literals (cross product) --
  not hand-copied a third time (check_ssh_keys.py's ANSWER_TOMLS is the
  existing copy; deriving here instead of adding a second hardcoded list).

  Tier 2 (kernels/initrd/iPXE-fetched boot binaries referenced by
  bootstrap/web/menu.ipxe): expected to be missing on an ordinary working
  checkout -- this repo's own bootstrap/web/{rockylinux,openbsd,gparted,
  winpe,alpine,spejder}/ and bootstrap/web/proxmox/klargoring/ genuinely
  don't exist on disk as of 2026-07-27, despite menu.ipxe referencing them,
  so expect a large warning count on every normal run -- that's not a bug in
  this check, it reflects real repo state. Soft (informational) by default;
  --strict promotes it to a hard failure, same idiom already used for
  check_references.py's drop-in binaries / check_ssh_keys.py's local keypair
  / check_keepass_freshness.py's vault drift / check_network_session_safety.py's
  ungated nmcli findings -- "you said you're about to deploy, not just
  reading the repo."

  ipxe.lkrn/ipxeaa64_arch.efi (the loader binaries a technician boots FROM)
  and ipxe_amd64.iso/ipxe-arm64.iso (real, git-tracked files, consumed by
  bootstrap/web/proxmox/create-vm.py's own separate Proxmox-ISO auto-select
  logic) are deliberately out of scope -- menu.ipxe doesn't reference any of
  them, and this check is scoped to "assets menu.ipxe references."

Tier 2's variable expansion only covers the small, enumerable set menu.ipxe
actually uses (${arch}, ${alpine-arch}, ${seed}) plus ${base}/${winpe-boot}
indirection (resolved from the nearby `set base ...`/`set winpe-boot ...`
line(s) in the same file). Anything left with an unresolved ${...} after
that (e.g. the autodeploy chain's ${mac:hexhyp}) is counted separately as
skipped-dynamic, never failed -- same honesty-about-coverage philosophy as
check_references.py's own skipped_dynamic count. .toml paths are excluded
from Tier 2 entirely -- that's Tier 1's domain, not a boot binary.

Exit code: 0 unless a Tier 1 (TOML) file is missing. Tier 2 issues are
printed and counted but never fail the run by themselves -- run.sh's
--strict flag escalates that count.

2026-07-27: each missing Tier 2 entry is now cross-referenced against
bootstrap/asset_manifest.yml -- if a fetch-on-demand source is configured
for it, the message names the fetch playbook
(ansible/playbooks/bootstrap_assets/fetch-assets.yml); if not, it says so
explicitly rather than leaving the operator to guess whether "missing" means
"run one command" or "needs real work" (a manual drop-in or git-lfs). This
check still never fetches anything itself -- stays read-only/offline, same
as every other check in this harness. Fetching is always a separate,
explicit ansible-playbook invocation.
"""
import itertools
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_WEB = REPO_ROOT / "bootstrap" / "web"
SELECT_ANSWER_SH = BOOTSTRAP_WEB / "proxmox" / "select-pve-answer.sh"
MENU_IPXE = BOOTSTRAP_WEB / "menu.ipxe"
ASSET_MANIFEST = REPO_ROOT / "bootstrap" / "asset_manifest.yml"
FETCH_PLAYBOOK = "ansible-playbook ansible/playbooks/bootstrap_assets/fetch-assets.yml"

# The only enumerable iPXE variables menu.ipxe's asset paths actually use.
KNOWN_VAR_VALUES = {
    "arch": ["x86_64", "arm64"],
    "alpine-arch": ["x86_64", "aarch64"],
    "seed": ["lvm-bios.seed", "lvm-efi.seed"],
}

ASSET_LINE_RE = re.compile(r"^\s*(kernel|initrd|chain)\s+(.*)$")
INLINE_PARAM_RE = re.compile(r"\b(?:url|fetch|modloop|apkovl)=(\S+)")
SET_INDIRECT_RE = re.compile(r"\bset\s+(base|winpe-boot)\s+(\S+)")


def first_non_flag_token(rest_of_line):
    """kernel/initrd/chain's actual path is the first whitespace-separated
    token that isn't an iPXE flag (--autofree, --replace, etc) -- e.g.
    `chain --autofree ${boot-url}/autodeploy/....ipxe || goto main`."""
    for tok in rest_of_line.split():
        if not tok.startswith("--"):
            return tok
    return None


def derive_answer_tomls():
    """Tier 1: derive the real TOML file list from select-pve-answer.sh's own
    site_prefix/variant literals, rather than hand-copying check_ssh_keys.py's
    ANSWER_TOMLS a second time."""
    text = SELECT_ANSWER_SH.read_text(encoding="utf-8")
    sites = sorted(set(re.findall(r'site_prefix="([A-Z]+)"', text)))
    variants = sorted(set(re.findall(r'variant="([a-z]+)"', text)))
    return [f"proxmox/{site}-{variant}.toml" for site in sites for variant in variants]


def check_answer_tomls():
    if not SELECT_ANSWER_SH.exists():
        return [f"{SELECT_ANSWER_SH.relative_to(REPO_ROOT)} doesn't exist -- can't derive "
                f"the answer TOML list from it."], []

    tomls = derive_answer_tomls()
    if not tomls:
        return [f"Derived zero TOML files from {SELECT_ANSWER_SH.relative_to(REPO_ROOT)} -- "
                f"its site_prefix=/variant= literals may have changed shape; this check's "
                f"regex needs updating, not silently passing with nothing checked."], []

    failures = []
    for rel in tomls:
        if not (BOOTSTRAP_WEB / rel).exists():
            failures.append(f"bootstrap/web/{rel} is missing (required -- Proxmox answer "
                             f"files are never optional).")
    return failures, tomls


def resolve_indirection(lines):
    """Collects every `set base ...` / `set winpe-boot ...` value seen
    anywhere in the file. Not per-section-scoped (both var names are only
    ever used within their own single section today), but tracked as a set
    so an iseq-conditional line's two possible values (winpe-boot) are both
    captured."""
    indirect = {}
    for line in lines:
        if line.strip().startswith("#"):
            continue
        for m in SET_INDIRECT_RE.finditer(line):
            var, value = m.group(1), m.group(2)
            indirect.setdefault(var, set()).add(value)
    return indirect


def strip_boot_url(raw, indirect):
    """Returns a list of candidate boot-url-relative path strings (still
    possibly containing unresolved ${...} tokens) for one raw path token."""
    candidates = [raw]
    for var, values in indirect.items():
        new_candidates = []
        for c in candidates:
            if f"${{{var}}}" in c:
                for v in values:
                    resolved = v
                    if resolved.startswith("${boot-url}/"):
                        resolved = resolved[len("${boot-url}/"):]
                    new_candidates.append(c.replace(f"${{{var}}}", resolved))
            else:
                new_candidates.append(c)
        candidates = new_candidates

    out = []
    for c in candidates:
        if c.startswith("${boot-url}/"):
            c = c[len("${boot-url}/"):]
        out.append(c)
    return out


def expand_known_vars(path_str):
    """Expands every ${arch}/${alpine-arch}/${seed} token via the cross
    product of their known values, by plain substring replacement (not
    identifier-based regex extraction -- iPXE's ${var:filter} syntax, e.g.
    ${mac:hexhyp}, isn't a bare identifier and would otherwise slip past a
    regex built only for ${name} and get silently treated as a static,
    already-resolved path). Returns (list_of_resolved_paths,
    still_has_unknown_vars: bool) -- "unknown" means "${" is still present
    anywhere after substituting every known variable, regardless of what's
    inside the braces."""
    resolved = [path_str]
    for var, values in KNOWN_VAR_VALUES.items():
        token = f"${{{var}}}"
        new_resolved = []
        for p in resolved:
            if token in p:
                new_resolved.extend(p.replace(token, val) for val in values)
            else:
                new_resolved.append(p)
        resolved = new_resolved

    if any("${" in p for p in resolved):
        return [], True
    return resolved, False


def collect_referenced_assets():
    """Tier 2: parses menu.ipxe for kernel/initrd/chain/url=/fetch=/
    modloop=/apkovl= tokens, expands the enumerable variables, and returns
    (resolved_paths, skipped_dynamic_raw_tokens)."""
    lines = MENU_IPXE.read_text(encoding="utf-8").splitlines()
    indirect = resolve_indirection(lines)

    raw_tokens = set()
    for line in lines:
        if line.strip().startswith("#"):
            continue  # documentation comments (e.g. "url=..." as a placeholder) aren't code
        m = ASSET_LINE_RE.match(line)
        if m:
            tok = first_non_flag_token(m.group(2))
            if tok:
                raw_tokens.add(tok)
        for m in INLINE_PARAM_RE.finditer(line):
            raw_tokens.add(m.group(1))

    resolved_paths = set()
    skipped_dynamic = set()

    for raw in raw_tokens:
        for boot_relative in strip_boot_url(raw, indirect):
            if boot_relative.endswith(".toml"):
                continue  # Tier 1's domain, not a boot binary
            paths, has_unknown = expand_known_vars(boot_relative)
            if has_unknown:
                skipped_dynamic.add(raw)
                continue
            resolved_paths.update(paths)

    return sorted(resolved_paths), sorted(skipped_dynamic)


def load_manifest_dests():
    """Every `dest` bootstrap/asset_manifest.yml covers, from both its flat
    `assets:` list and its `archives: -> members -> dest` entries. Missing or
    unparseable manifest -> empty set, not an error (the manifest is
    optional infrastructure for this check, not a hard dependency of it)."""
    if not ASSET_MANIFEST.exists():
        return set()
    try:
        manifest = yaml.safe_load(ASSET_MANIFEST.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return set()

    dests = {a["dest"] for a in manifest.get("assets", []) if "dest" in a}
    for archive in manifest.get("archives", []):
        dests.update(m["dest"] for m in archive.get("members", []) if "dest" in m)
    return dests


def check_boot_binaries():
    if not MENU_IPXE.exists():
        return [f"{MENU_IPXE.relative_to(REPO_ROOT)} doesn't exist -- can't check referenced "
                f"boot binaries."], [], 0

    resolved_paths, skipped_dynamic = collect_referenced_assets()
    missing = [p for p in resolved_paths if not (BOOTSTRAP_WEB / p).exists()]
    return missing, skipped_dynamic, len(resolved_paths)


def main():
    print("-- Tier 1: bootstrap/web/proxmox/*.toml answer files (always required) --")
    toml_failures, tomls = check_answer_tomls()
    if toml_failures:
        print(f"{len(toml_failures)} issue(s):")
        for f in toml_failures:
            print(f"  {f}")
    else:
        print(f"All {len(tomls)} derived answer TOML(s) present: {', '.join(tomls)}")

    print()
    print("-- Tier 2: menu.ipxe-referenced boot binaries (informational unless --strict) --")
    missing, skipped_dynamic, checked_count = check_boot_binaries()
    print(f"Checked {checked_count} resolved path(s); skipped {len(skipped_dynamic)} "
          f"genuinely dynamic reference(s) (unresolvable ${{...}} tokens, e.g. per-MAC "
          f"autodeploy).")
    if missing:
        manifest_dests = load_manifest_dests()
        print(f"{len(missing)} boot binary issue(s) (informational; --strict fails on this):")
        for m in missing:
            if m in manifest_dests:
                print(f"  bootstrap/web/{m}  [fetchable: {FETCH_PLAYBOOK}]")
            else:
                print(f"  bootstrap/web/{m}  [no fetch source configured -- manual drop-in "
                      f"or git-lfs]")
    else:
        print("All resolved boot binary references exist.")

    if toml_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
