# Plan: harness tool-dependency checks + bootstrap asset freshness

**Status: DRAFT — for tomorrow. Nothing here built yet.**

Written 2026-08-06 after Robert's live frustration: `kpcli_wrapper.py` failed
outright (`keepassxc-cli` not installed on the control node) with nothing in
the harness having warned about it beforehand, `fyrtaarn` (a real, released
spin-off tool) was never picked up into `bootstrap/web/`, and Debian's
netboot images turned out to have a real functional problem he had to work
around by hand with mini.iso images — none of which the harness caught.
Robert: "the entire bloody point of the harness is to catch all this type of
stuff." Four separate, genuinely distinct problems below — don't conflate
them into one check.

## 1. Host-local required-tool checks (generalise the existing pattern)

**BUILT 2026-08-07 (check 36, `check_required_tools.py`).** Robert's own
scoping answer, live: check for `keepassxc-cli`/`keepassxc-full` on
Debian, `keepassxc` on macOS/Windows; concern this primarily with
"Problem A" (control-node tools) over "Problem B" (validating each
provisioning script's own self-heal list) -- Problem B not started, still
open. Seeded with `keepassxc-cli` only (the confirmed real gap); `bc` was
reconsidered and correctly excluded -- it's a `bootstrap/web/provision/`
target-host tool that already self-heals via its own `command -v bc ||
BOOTSTRAP_PKGS+=(bc)` pattern, not a control-node requirement at all (see
that check's own header for the full scoping reasoning). Hand-maintained
`REQUIRED_TOOLS` dict, not auto-derived from scanning `subprocess.run()`
call sites -- considered and rejected, see the check's own header.


**Precedent already exists, just never generalised**: `check_gitleaks.py`
(check 33), `check_ssh_keys.py` (check 11), and `check_mermaid.py` (check 13)
each already implement the exact right shape for ONE tool each — informational
by default (a bare clone genuinely might not have the binary), `--strict`
promotes to a hard failure. Nothing currently generalises this across every
tool this repo's own scripts actually shell out to.

**Known, confirmed-real requirements found by grepping this session (not
exhaustive — a real pass needs to grep every `bootstrap/web/provision/*.sh`
and harness script systematically)**:
- `keepassxc-cli` — `benarbejde/kpcli_wrapper.py`,
  `benarbejde/push_credentials_to_keepass.py`
- `bc` — `bootstrap/web/provision/bindme.sh`,
  `bootstrap/web/provision/firewallme.sh`
- `gitleaks` — already covered by check 33, the template to match

**Design**: a new check (or extend `check_bootstrap_assets.py`'s own
host-local-tool framing) that:
1. Enumerates every `command -v <tool>`/`which <tool>` guard already present
   in `bootstrap/web/provision/*.sh` and `at_have_ryggen_fri/*.py` — derive
   the list from the scripts themselves, not a hand-typed second copy (same
   "don't hand-roll a second source of truth" principle every other check in
   this harness already follows).
2. For each, check presence via `shutil.which()`, informational by default,
   `--strict` fails.
3. OS-aware install instructions in the output (this repo already knows
   `ansible_distribution`-style facts elsewhere; for a host-local check
   running on whatever OS the operator is on, `platform.system()`/
   `shutil.which('apt')` vs `brew` vs `choco` is enough to print the right
   one-liner, matching `check_bootstrap_assets.py`'s existing "3 platform
   setup scripts" messaging pattern).

## 2. Spin-off repo release tracking (klargoring, fyrtaarn, Spejder, ...)

**Two different problems, don't conflate**:
- **klargoring**: already correctly wired (asset_manifest.json + menu.ipxe),
  this session's own work — the pattern to copy for a NEW check that keeps
  it that way going forward: compare `asset_manifest.json`'s recorded `tag`
  (currently `"latest"` for all github_release entries, not pinned) against
  each repo's actual latest release via the GitHub API, flag drift.
- **fyrtaarn**: never wired in at all — Type-1-gap, needs the SAME kind of
  integration work klargoring got (decide what it's for in this repo's own
  workflow — a downloadable tool in `bootstrap/`? An `asset_manifest.json`
  entry? Something a provision script fetches?) before a freshness check
  even makes sense. This needs Robert's own design input on WHERE fyrtaarn
  fits into this repo's actual usage (it's used narratively in
  `docs/INCIDENT-LOG.md` already, by a technician, standalone — is it meant
  to be a fetchable binary this repo ships, or just referenced/documented as
  an external tool technicians bring themselves?).

**Design for the freshness-checking half** (once fyrtaarn's integration is
decided): a new check that, for every `github_release`-sourced
`asset_manifest.json` entry, queries `api.github.com/repos/<repo>/releases/
latest` (read-only, same "check kroki.io" exception `check_mermaid.py`
already has for going outside localhost) and compares against what's
actually committed/fetched — informational, since a bare clone won't have
fetched anything at all, `--strict` for "you're about to deploy, is this
current."

## 3. Debian netboot images -- functional regression, not a dead link

Confirmed: the current URL in `asset_manifest.json`
(`ftp.debian.org/.../netboot/debian-installer/...`) returns HTTP 200 right
now — not a broken link from where this was checked. Robert's actual
problem was functional (the netboot image itself not working correctly for
arm64+amd64, both bookworm and trixie), worked around by sourcing mini.iso
images instead by hand.

**Needs Robert's input before any code changes**: where are the mini.iso
files he already sourced, and does he want `asset_manifest.json`/
`menu.ipxe` switched to a mini.iso-based boot path instead of the current
netboot kernel+initrd path (a bigger structural change — mini.iso is a
different boot mechanism, not a drop-in file swap) — or kept as a documented
fallback alongside the existing path. Don't guess at this, ask directly
first.

## 4. KeePassXC master password file

**RESOLVED 2026-08-07 — real root cause found, was not what it looked like.**
The original 2026-08-06 finding ("not a bug in this checkout, master
password file is correctly gitignored and matches") was correct as far as it
went, but incomplete — checked EXAANSCLD001 itself live and found the real
problem: `~/KeePassXC/` doesn't exist there at all. `keepassxc-cli` IS now
installed there (`/usr/bin/keepassxc-cli` — that part of the original
2026-08-06 complaint is independently resolved, presumably fixed separately
since then). The actual root cause: **the vault database itself was never
created.** Robert's own mental model was that Ansible/the harness were
"fattening up" the vault automatically as playbooks ran — corrected live:
nothing in this repo's design ever creates a `.kdbx` file from scratch, by
design (the one-way flow's whole point is that automation only ever adds
entries into an already-human-created vault; creating the database itself
is a one-time, human, out-of-band step via the real KeePassXC app or
`keepassxc-cli db-create`, deliberately not something any script here does).

A real, populated vault (genuine pre-existing entries, e.g. `EXARACEDI001`)
was confirmed reachable from a different environment during this session's
own KeePass push work — so a real vault does exist somewhere, just not on
EXAANSCLD001. Robert to locate/create the actual vault and place it wherever
he wants `push_credentials_to_keepass.py` to run from.

Side finding, same investigation: `benarbejde/.keepassxc_master_password` on
EXAANSCLD001 is 26 bytes vs the known-correct 25-byte value elsewhere, and
was modified 2026-08-07 (today), not 2026-07-14 like the known-good copy —
genuinely different content, not just a stale-mtime false alarm. Not yet
explained; worth a byte-level diff once the vault question is settled, since
the master password is moot until a real database exists to unlock.

Also fixed the same day: renamed the default vault filename from
`Example Music.kdbx` to `ExampleMusic.kdbx` (Robert: a space in a filename
is "playing with fire" on Unix/macOS) — code + docs updated, no live file
touched.

## Explicitly not started

None of the above is built. This document exists so today's frustration
translates into a concrete, ordered list rather than getting lost — pick up
tomorrow, one item at a time, same "plan first, then build phase by phase"
pacing as everything else this week.
