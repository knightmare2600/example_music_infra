# Plan: `tacticalrmmme.sh` break-glass script

**Status: DRAFT — pending Robert's review. Nothing in this plan has been built yet.**

Written 2026-08-05 after Robert's first live manual install against `EXARMMCLD001`
(Debian Trixie), following his five observations from that run. This doc exists
so the plan survives context/session boundaries and can be reviewed calmly
rather than acted on immediately — see "Open decisions" at the bottom before
anything here gets built.

## Robert's five observations (source of this plan)

1. `install.sh` is a "known source of truth" — make it a "break glass" script
   like the others (`bindme.sh`/`rudderme.sh`).
2. Aside from the interactive prompts, nothing `install.sh` does (package
   installs, repo clones) is something Ansible couldn't also do — but see
   "What stays exactly as `install.sh` does it" below for why we don't
   actually duplicate it.
3. The authenticator QR/TOTP moment is the one place this could genuinely go
   wrong — needs careful capture/handling.
4. The install prints back credentials (MeshCentral auto-generated
   username/password) that need capturing into the KeePassXC harness, with a
   terminal fallback.
5. DNS records (`rmm`/`api`/`mesh`) must be verified to exist before starting,
   because "all hell can break loose" otherwise. The interactive prompts
   (`read -p` in the upstream script) can have sensible defaults surfaced as
   part of pre-flight.

## What "break glass" means here (confirmed against the real precedent)

Checked `bootstrap/web/provision/bindme.sh` and `rudderme.sh` directly before
writing this plan, rather than guessing at the pattern:

- Both are self-contained bash (`set -euo pipefail`, root-run), **not**
  `ansible-playbook` wrappers — they do real work themselves.
- Both end with a printed "REMAINING MANUAL STEPS" banner rather than trying
  to automate everything.
- **Neither auto-pushes credentials to KeePass.** `rudderme.sh` prints "store
  it in your password manager" and stops — matches the estate-wide one-way
  KeePass flow (`push_credentials_to_keepass.py`/`kpcli_wrapper.py` are
  human-run only, per `project_keepass_one_way_flow.md`).
- **One real difference from our case:** `bindme.sh`/`rudderme.sh` must work
  *before* DNS/Ansible connectivity exists on the target box (that's why they
  have their own 3-tier `sites.csv` lookup). `EXARMMCLD001` is different — by
  the time we reach this step, `tacticalrmm_server.yml` has already run
  (Ansible reachable) and `bind9-dns.yml` has already run (DNS live). So
  `tacticalrmmme.sh` doesn't need that pre-Ansible fallback logic — Phase 1's
  DNS/Ansible pre-flight checks replace it. Robert's call: keep the script
  in `bootstrap/web/provision/` alongside its siblings anyway, for location
  consistency, despite this difference in constraints.

## What stays exactly as `install.sh` does it (point 2)

Confirmed from the real transcript: package installs (curl/git/redis/
postgresql/nginx/nodejs, Python built from source), repo clones (`rmm`,
`trmm-community-scripts`), DB/role creation, Django migrations, systemd unit
creation — all of this is `install.sh`'s own job. We do **not** reimplement
any of it in Ansible. Reasoning: `install.sh` is the source of truth Robert
named it as; duplicating its logic in Ansible would be exactly the
"hand-rolled reconstruction that duplicates logic that already exists"
anti-pattern — it would drift the moment upstream changes anything, and we'd
have no way of knowing. Ansible's job stays exactly what
`tacticalrmm_server.yml` already does today (hostname/static-IP/packages/
firewall) — VM prep only, unchanged. `tacticalrmmme.sh` **wraps** `install.sh`,
it doesn't replace it.

## Proposed script structure

### Phase 1 — Pre-flight (new)

1. **RAM check.** Robert's real run hit `ERROR: A minimum of 4GB of RAM is
   required` partway through — after several minutes of apt work and a QR
   code had already been generated (see Phase 4). Add a `free -m` check as
   literally the first thing the script does, before any package install or
   TOTP generation, so a too-small VM fails in one second instead of several
   minutes.
2. **DNS resolution check** (point 5, directly). Verify `rmm.`, `api.`,
   `mesh.jukebox.internal` all resolve, and resolve to `EXARMMCLD001`'s own
   IP (`192.168.69.14`), via `getent hosts` or `dig`. Fail with a clear
   message pointing at `bind9-dns.yml --tags zones-full,reload` if not —
   don't let the operator discover this mid-`install.sh`.
3. **Existing-install check.** Does `/rmm` already exist? Warn/abort rather
   than re-running blind against a populated box.
4. **Root + hostname sanity.** Confirm running as root and confirm the box's
   own hostname is `EXARMMCLD001` (copying `bindme.sh`'s own sanity-check
   habit) before doing anything destructive.

### Phase 2 — Fetch + patch `install.sh`

- Download fresh from upstream **every run** — never vendor/fork a local
  copy. This is the point of calling it a "known source of truth": we always
  defer to upstream, never a copy that silently drifts.
- Apply the exact Trixie patch Robert already hand-verified works. His own
  `grep 13 install.sh` after editing showed the patched line:
  ```
  if [[ "$relno" -ne 11 && "$relno" -ne 12 && "$relno" -ne 13 ]]; then
  ```
  Script applies this via `sed` against the *unpatched* upstream line (which
  presumably reads `-ne 11 && "$relno" -ne 12` without the `13`) — scripted
  so it's not manual vim surgery every single run, and so a failed sed match
  (upstream changed the line) is a loud, caught error rather than a silent
  no-op.

### Phase 3 — Answer cheat-sheet (point 5, "sensible defaults")

`install.sh` has zero non-interactive bypass (confirmed earlier, no
env/flag/config path) and `ansible.builtin.expect` was already rejected by
Robert for the irreversible-changes risk — so the script still can't *feed*
the interactive prompts. What it can do:

- Print the exact answers to give (domain/subdomains derived from
  `role_codes.csv`'s `RMM` row + `bind9-dns.yml`'s `bind9_extra_cnames` —
  already the source of truth, not re-derived by hand) immediately before
  handing off to `install.sh`, so the operator reads-and-types rather than
  recalling from a README days later.
- Prompt the operator once, at the top, for the two genuinely-personal
  values: admin email and Django admin username — echoed back for
  confirmation, not hardcoded into the script.

### Phase 4 — TOTP/QR handling (point 3)

Confirmed from Robert's own transcript: the QR + setup key print **even on a
run that later fails** (the RAM error happened *after* the QR had already
been shown once). Phase 1's RAM check now catches that specific case before
the QR point is ever reached — but other downstream failures could still
orphan a still-valid, never-used TOTP key.

- Script pauses immediately after `install.sh` prints the QR/key (before
  scrollback can bury it) with an explicit "scan or record the key above now
  — press Enter once captured" prompt, on top of `install.sh`'s own "Press
  any key to continue..." moment.
- Flag the TOTP setup key as a KeePassXC **TOTP-type** entry (KeePassXC
  supports these natively) alongside the admin username/password — captured
  in the final credentials banner (Phase 5), never auto-pushed.

### Phase 5 — Credential capture output (point 4)

- `tee` the whole `install.sh` run to a timestamped logfile on
  `EXARMMCLD001` itself (`/root/tacticalrmm-install-<date>.log`) so the
  MeshCentral auto-generated username/password aren't only in terminal
  scrollback.
- Script's own final banner (matching `rudderme.sh`'s "store it in your
  password manager" framing) pulls out and re-prints together: MeshCentral
  username + password, Django admin username (not password — Robert typed
  that himself), TOTP setup key. One block, easy to KeePass-enter in one go.
- **Not auto-pushed to KeePass** — matches the estate's one-way flow.

### Phase 6 — REMAINING MANUAL STEPS banner (matches `rudderme.sh` convention)

- Push the Phase 5 credential block into KeePassXC by hand.
- Verify login at `https://rmm.jukebox.internal`.
- (Anything else that only becomes clear once this is actually built/tested.)

## Decisions (Robert, 2026-08-05)

1. **Location: `bootstrap/web/provision/tacticalrmmme.sh`.** Matches
   `bindme.sh`/`rudderme.sh`'s actual location exactly, for consistency of
   "where break-glass scripts live" — even though the pre-Ansible constraint
   that put them there doesn't strictly apply to this one.
2. **Naming: `tacticalrmmme.sh`.** Matches the `<thing>me.sh` convention
   exactly.
3. **Admin email/Django username: prompt live every run.** Matches
   `bindme.sh`'s own habit of prompting for hostname each run — nothing
   hardcoded, always explicit.
4. **Sed patch: scripted.** Idempotent `sed` against the known unpatched
   line, fails loudly if upstream has moved the line rather than silently
   no-op'ing. Removes the manual vim step from every run.

## Explicitly not in scope for this plan

- Reverse proxy, monitoring, logging, backups, hardening, disaster recovery
  — later phases of the platform brief, untouched here.
- `EXAMSHCLD001` standalone MeshCentral role reconsideration — separately
  parked, not this plan's concern.
