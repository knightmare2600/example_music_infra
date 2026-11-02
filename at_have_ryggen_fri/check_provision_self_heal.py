#!/usr/bin/env python3
"""
check_provision_self_heal.py -- part of at_have_ryggen_fri.

Backlog item 1, "Problem B" (PLAN-harness-and-bootstrap-backlog-2026-08-06.md):
check_required_tools.py (check 36) only ever covered "Problem A" -- tools
the CONTROL NODE itself needs (keepassxc-cli and friends). This checks the
other half: the self-heal pattern each bootstrap/web/provision/*.sh script
(ansibleme.sh, bindme.sh, firewallme.sh, rudderme.sh, tacticalrmmme.sh,
zabbixme.sh) already uses to make the TARGET box it's building provision
itself -- lines like:

    command -v bc &>/dev/null || BOOTSTRAP_PKGS+=(bc)
    dpkg -s molly-guard &>/dev/null || BASE_PKGS+=(molly-guard)
    command -v jq &>/dev/null || { info "Installing jq..."; apt-get install -y -qq jq; }

These scripts already self-heal live, every run -- this check isn't about
telling an operator a tool is missing (the script already fixes that
itself). It's three separate static things that can go wrong in a self-heal
LINE itself, none of which anything previously checked, scoped per Robert's
own three-way answer (2026-11-02) to "which gap do you actually want closed":

  1. PACKAGE EXISTENCE (hard fail): every package name appearing in any
     self-heal line, across all 6 scripts, actually exists in Debian's
     archive right now -- checked live against the same public madison API
     `dak ls`/`apt-cache madison` use (api.ftp-master.debian.org), no auth,
     resolves both source and binary package names. A typo'd or
     upstream-renamed package name here would silently crash `apt-get
     install` on the very first real provision run against a fresh box --
     nothing previously caught that beforehand.

  2. USED BUT UNCHECKED (informational -- static analysis, human triage):
     for each script, every OTHER tool already proven (by some script's own
     self-heal line) to need self-healing, that this script actually
     invokes in command position somewhere in its own body without ever
     self-healing it itself. Real example found by hand while scoping this
     check, confirmed live in the committed file: firewallme.sh's
     ip_in_use() calls `arping` (gated behind `if command -v arping`, so it
     never crashes -- it just silently falls back to ping-only IP-collision
     detection) but firewallme.sh never adds arping to BOOTSTRAP_PKGS
     anywhere, unlike every one of the other 5 scripts that uses arping.
     Command-position detection is a heuristic (splits each non-check,
     non-comment line on `;`/`&&`/`||`/pipes/subshell-opens, strips leading
     bash keywords, takes the first resulting token) -- not a real shell
     parser, so this can both miss real cases and occasionally flag a false
     one. Informational only, by design, same honesty-about-coverage
     philosophy as check 27/28's own static-analysis limitations.

  3. CROSS-SCRIPT CONSISTENCY (informational): the same tool or package
     self-healed in 2+ scripts, where the package set queued differs
     between them (e.g. one script's `command -v zsh` self-heal also pulls
     in zsh-autosuggestions/zsh-syntax-highlighting, another's doesn't).
     Not necessarily a bug -- a control-node script genuinely may not need
     the same extras a user-facing shell does -- but previously invisible
     anywhere, and exactly the shape of thing that goes stale silently when
     one script's self-heal line gets fixed and the others don't.

Scope: only bootstrap/web/provision/*.sh. ZBX_INSTALL_PKGS in zabbixme.sh is
deliberately excluded from all three checks -- it's the actual Zabbix
server package set to install unconditionally, not a "is this missing,
self-heal it" gate, a structurally different category.

Same host-local network-dependency pattern as check 13/17/37/49 -- madison
being unreachable is reported informationally, not a hard failure.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVISION_DIR = REPO_ROOT / "bootstrap" / "web" / "provision"

CHECK_ANYWHERE_RE = re.compile(r"\b(?:command\s+-v|dpkg\s+-s)\s+(\S+)")
TOOL_DEFERRED_RE = re.compile(r"\bcommand\s+-v\s+(\S+)\s*&>\s*/dev/null\s*\|\|\s*\w*PKGS\+=\(([^)]*)\)")
TOOL_IMMEDIATE_RE = re.compile(r"\bcommand\s+-v\s+(\S+)\s*&>\s*/dev/null\s*\|\|\s*\{.*?\bapt-get\s+install\s+-y\s+-qq\s+([a-zA-Z0-9][a-zA-Z0-9.+-]*)")
PKG_DEFERRED_RE = re.compile(r"\bdpkg\s+-s\s+(\S+)\s*&>\s*/dev/null\s*\|\|\s*\w*PKGS\+=\(([^)]*)\)")

BASH_KEYWORDS = {"if", "then", "else", "elif", "fi", "while", "until", "do", "done",
                  "for", "in", "case", "esac", "function", "time", "!", "sudo"}
SPLIT_RE = re.compile(r"\|\||&&|[;|]")

# A dpkg -s self-heal checks a PACKAGE name, which doesn't always textually match the
# BINARY name a later command invokes (command -v's own check target). Two confirmed-genuine
# cases, found by hand while verifying this check's own findings (2026-11-02) -- both already
# correctly self-healed via dpkg -s, just under a different name than the binary used:
#   rudderme.sh: `dpkg -s gnupg &>/dev/null || BASE_PKGS+=(gnupg)` (gnupg provides /usr/bin/gpg,
#   no textual relationship at all -- can't be derived, has to be an explicit, small, named
#   exception, same spirit as demurred.yml/ALLOWED_HOSTNAME_REUSE elsewhere in this harness)
#   and `dpkg -s lsb-release &>/dev/null || BASE_PKGS+=(lsb-release)` (lsb-release provides
#   /usr/bin/lsb_release -- a plain dash/underscore difference, handled generically below
#   instead of hardcoded here).
KNOWN_PACKAGE_PROVIDES = {"gnupg": {"gpg"}}


def madison_exists(pkg, cache):
    if pkg in cache:
        return cache[pkg]
    url = f"https://api.ftp-master.debian.org/madison?package={pkg}&f=json"
    req = urllib.request.Request(url, headers={"User-Agent": "example-music-harness"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as e:
        cache[pkg] = None
        return None
    result = bool(data)
    cache[pkg] = result
    return result


def parse_script(text):
    """Returns (tool_self_heal: {tool: {pkgs}}, pkg_self_heal: {pkg: {pkgs}},
    used_tokens: {first-word-in-command-position tokens found outside any
    check line})."""
    tool_self_heal = {}
    pkg_self_heal = {}
    used_tokens = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m = TOOL_DEFERRED_RE.search(line)
        if m:
            tool_self_heal.setdefault(m.group(1), set()).update(m.group(2).split())
        m = TOOL_IMMEDIATE_RE.search(line)
        if m:
            tool_self_heal.setdefault(m.group(1), set()).add(m.group(2))
        m = PKG_DEFERRED_RE.search(line)
        if m:
            pkg_self_heal.setdefault(m.group(1), set()).update(m.group(2).split())

        if CHECK_ANYWHERE_RE.search(line):
            continue  # a presence-check line (command -v / dpkg -s) never counts as "using" the tool

        probe = line.replace("$(", ";").replace("`", ";")
        for chunk in SPLIT_RE.split(probe):
            tokens = chunk.strip().split()
            while tokens and tokens[0] in BASH_KEYWORDS:
                tokens = tokens[1:]
            if not tokens:
                continue
            first = tokens[0].strip("()`\"';")
            if first:
                used_tokens.add(first)

    return tool_self_heal, pkg_self_heal, used_tokens


def main():
    if not PROVISION_DIR.is_dir():
        return [f"{PROVISION_DIR.relative_to(REPO_ROOT)} does not exist."], []

    scripts = sorted(PROVISION_DIR.glob("*.sh"))
    if not scripts:
        print(f"No *.sh files under {PROVISION_DIR.relative_to(REPO_ROOT)} -- nothing to check.")
        return [], []

    per_script = {}
    for path in scripts:
        name = path.name
        tool_heal, pkg_heal, used = parse_script(path.read_text(encoding="utf-8"))
        per_script[name] = {"tool": tool_heal, "pkg": pkg_heal, "used": used}

    hard_failures = []
    soft_findings = []

    # -- 1. Package existence --
    all_packages = set()
    for info in per_script.values():
        for pkgs in info["tool"].values():
            all_packages.update(pkgs)
        for pkgs in info["pkg"].values():
            all_packages.update(pkgs)

    cache = {}
    for pkg in sorted(all_packages):
        exists = madison_exists(pkg, cache)
        if exists is None:
            soft_findings.append(f"package existence: could not reach the Debian madison API for {pkg!r} -- skipping, informational only.")
        elif not exists:
            hard_failures.append(f"package existence: {pkg!r} (queued by a self-heal line) does not exist in Debian's archive -- typo, or upstream renamed/removed it.")

    # -- 2. Used but unchecked --
    global_tools = set()
    for info in per_script.values():
        global_tools.update(info["tool"].keys())

    for name, info in per_script.items():
        # A dpkg -s self-heal already covers a tool if its package key matches the tool name
        # (dash/underscore-insensitive, e.g. lsb-release -> lsb_release) or is a known
        # package-provides-binary exception (e.g. gnupg -> gpg, see KNOWN_PACKAGE_PROVIDES).
        pkg_covered_tools = set()
        for pkg_key in info["pkg"].keys():
            pkg_covered_tools.add(pkg_key.replace("-", "_"))
            pkg_covered_tools.update(KNOWN_PACKAGE_PROVIDES.get(pkg_key, set()))

        unchecked = sorted((info["used"] & global_tools) - set(info["tool"].keys()) - pkg_covered_tools)
        for tool in unchecked:
            soft_findings.append(f"{name}: invokes {tool!r} in command position, but never self-heals it here -- "
                                  f"self-healed elsewhere by: {', '.join(sorted(n for n, i in per_script.items() if tool in i['tool']))}.")

    # -- 3. Cross-script consistency --
    combined_keys = {}  # key -> {script: frozenset(pkgs)}
    for name, info in per_script.items():
        for tool, pkgs in info["tool"].items():
            combined_keys.setdefault(("cmd", tool), {})[name] = frozenset(pkgs)
        for pkg, pkgs in info["pkg"].items():
            combined_keys.setdefault(("pkg", pkg), {})[name] = frozenset(pkgs)

    for (kind, key), by_script in combined_keys.items():
        if len(by_script) < 2:
            continue
        distinct = set(by_script.values())
        if len(distinct) > 1:
            detail = "; ".join(f"{n}={sorted(p)}" for n, p in sorted(by_script.items()))
            label = "command" if kind == "cmd" else "dpkg package"
            soft_findings.append(f"cross-script drift: {label} {key!r} self-healed with different package sets across scripts -- {detail}")

    return hard_failures, soft_findings


if __name__ == "__main__":
    strict = "--strict" in sys.argv
    hard_failures, soft_findings = main()

    if soft_findings:
        print(f"{len(soft_findings)} informational finding(s):")
        for f in soft_findings:
            print(f"  {f}")

    if hard_failures:
        print(f"{len(hard_failures)} problem(s):")
        for f in hard_failures:
            print(f"  {f}")
        sys.exit(1)

    if strict and soft_findings:
        sys.exit(1)

    if not soft_findings:
        print("Every provision script self-heal package name exists upstream, no cross-script drift, no used-but-unchecked tools found.")
    sys.exit(0)
