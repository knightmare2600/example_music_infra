# Plan: TacticalRMM as an end-to-end Ansible install

**Status: superseded direction as of 2026-08-06 — see "2026-08-06 pivot" below.**
**Phase 1 (question-gathering + secret generation) DONE. Phases 2-13 not started.**

## 2026-08-06 pivot

The original plan (below, kept for history) was to treat `install.sh` as an
untouchable "known source of truth" and wrap it with a break-glass script
(`bootstrap/web/provision/tacticalrmmme.sh`) that pre-flights, patches the
Trixie version gate, and hands off to the real interactive installer.
Robert, 2026-08-06, after actually running that wrapper against
`EXARMMCLD001` and finding it just stops before doing anything useful:

> "The entire point of having an ansible playbook and me giving you the
> output yesterday was so we could dispense with their install script and
> make it into an end-to-end ansible playbook... You fatten up this
> playbook for it, so it asks me all the questions and so on up front then
> we take each step out of install.sh and turn it into an ansible step."

Direction reversed: `install.sh` gets fully reimplemented as real,
idempotent Ansible tasks inside `tacticalrmm_server.yml`. Nothing shells
out to the upstream script at all once this is complete.
`bootstrap/web/provision/tacticalrmmme.sh` is parked, not deleted — it
stays in the repo until the Ansible-native path is built and proven, in
case it's needed as a fallback, but is no longer the intended path.

## The real install.sh, step by step

Fetched fresh from `github.com/amidaware/tacticalrmm` 2026-08-06 (not
guessed, not reconstructed from the earlier OS-check-only fetch) and
enumerated in full. 31 logical steps, in order:

 1. **Base packages** — curl, wget, jq, dirmngr, gnupg, lsb-release,
    ca-certificates, software-properties-common, openssl.
 2. **Compatibility checks** — rejects LXC, existing install, non-x86_64/
    aarch64, <4GB RAM, non-Debian-11/12/Ubuntu-22.04 (already patched for
    Trixie in the wrapper's Section 2 — same patch needs porting here),
    Turnkey/Webmin, root user, non-UTF-8 locale.
 3. **Secret generation** — Django secret key (80 chars), admin URL
    (70 chars), MeshCentral password (25 chars), PostgreSQL username
    (8 lowercase)/password (20 alphanumeric) for the `tacticalrmm` DB,
    MeshCentral username (8 lowercase) + its own separate PostgreSQL
    username/password for the `meshcentral` DB. All random, all
    install.sh's own job today — becomes Ansible-generated + persisted
    (idempotent: generate once, read back on every re-run) in Phase 1.
 4. **Domain/cert prompts** — backend/frontend/meshcentral subdomains,
    root domain, admin email. **Not re-prompted here** — subdomains and
    root domain are already fixed estate facts (`rmm`/`api`/`mesh` under
    `jukebox.internal`, from `role_codes.csv`'s `RMM`/`MSH` rows +
    `bind9-dns.yml`'s `bind9_extra_cnames`) — re-asking a human to retype
    an already-known-and-DNS-verified value would be exactly the
    "known source of truth" violation this repo keeps catching itself on.
    Only email/admin username/admin password are genuine per-run choices.
 5. **Certificate acquisition** — self-signed (`--insecure`), own cert, or
    Certbot/Let's Encrypt DNS challenge. `EXARMMCLD001` is internal/
    WireGuard-only (same reasoning as `EXAMSHCLD001`) — self-signed only,
    Certbot path out of scope.
 6. **`/etc/hosts`** — adds the three subdomains, NAT detection.
 7. **Nginx** — official repo + GPG key, replaces `nginx.conf`.
 8. **NodeJS** — v24 via NodeSource repo + GPG key, npm upgrade.
 9. **Python 3.11.8 from source** — build deps, download/compile/install,
    cleanup.
10. **Redis + Git** — plain package install.
11. **PostgreSQL 18** — official repo + GPG key, install, two databases
    (`tacticalrmm`, `meshcentral`) with their own generated users/roles.
12. **Repo clones** — `amidaware/tacticalrmm` → `/rmm/`,
    `amidaware/community-scripts` → `/opt/trmm-community-scripts`.
13. **NATS server** — arch-detected binary download to `/usr/local/bin/`.
14. **MeshCentral install** — `/meshcentral/` dir, generated
    `package.json`/`config.json`, `npm install`.
15. **Django `local_settings.py`** — secret key, debug=False, allowed
    hosts, DB creds, MeshCentral integration, `TRMM_INSECURE`/cert paths.
16. **`nats-api` binary** — arch-specific, `/usr/local/bin/`.
17. **Backend install** — weasyprint deps, venv at `/rmm/api/env`, pip/
    setuptools/wheel, `requirements.txt`, migrations, JSON schemas,
    `collectstatic`, NATS API config, uWSGI config, Chocolatey/community
    script loading.
18. **Superuser + TOTP** — prompts for Django admin username, creates
    superuser + installer account, generates TOTP secret, displays
    barcode, waits for confirmation. **The one place Robert flagged as
    genuinely risky** — needs the most careful Ansible design of all 31
    steps (see "TOTP handling" below).
19. **Systemd units ×7** — `rmm` (uwsgi), `daphne` (uvicorn/websocket),
    `nats`, `nats-api`, `celery`, `celerybeat`, `meshcentral`.
20. **`/etc/conf.d/celery.conf`** — worker config, autoscale 20-2.
21. **Nginx site configs ×3** — backend (`rmm.conf`), MeshCentral
    (`meshcentral.conf`), frontend (`frontend.conf`, React SPA).
22. **Nginx symlinking** — `sites-available` → `sites-enabled`.
23. **Service enable/start** — rmm, daphne, celery, celerybeat, nginx.
24. **MeshCentral first boot** — enable/restart, poll journal for
    "MeshCentral HTTP server running on port" every 5s.
25. **MeshCentral token key** — `node --logintokenkey`, capture
    `MESHTOKENKEY`, append to `local_settings.py`.
26. **MeshCentral account/group setup** — stop, `--createaccount`,
    `--adminaccount`, restart, wait for ready, create "TacticalRMM"
    device group via `meshctrl.js` over WSS.
27. **NATS init** — enable/start, initial DB setup command, reload,
    sync MeshCentral with TacticalRMM.
28. **`nats-api` enable/start.**
29. **Disable Django admin UI** — flip `ADMIN_ENABLED` to `False` in
    `local_settings.py`.
30. **Final restart** — rmm, daphne, celery, celerybeat.
31. **Completion report** — frontend URL, MeshCentral creds, NAT guidance.

## Phased Ansible build order

Same "phase by phase, checked in after each one" pacing Robert set for the
wrapper script — carried over to this rebuild, not abandoned. Each phase
below is a natural dependency group from the list above; build and verify
one at a time, don't jump ahead.

| Ansible phase | install.sh steps | Status |
|---|---|---|
| 1. Prompts + secret generation | 3, 4 (partial — email/admin user/password only) | **DONE, this session** |
| 2. Compatibility checks + base packages | 1, 2 | Not started |
| 3. Nginx, NodeJS, Python 3.11.8, Redis, Git | 7, 8, 9, 10 | Not started |
| 4. PostgreSQL 18 + databases | 11 | Not started |
| 5. Repo clones | 12 | Not started |
| 6. NATS server + nats-api binaries | 13, 16 | Not started |
| 7. MeshCentral install (files, not yet running) | 14 | Not started |
| 8. Django settings + backend install/migrate | 15, 17 | Not started |
| 9. Superuser + TOTP | 18 | Not started — see below |
| 10. Systemd units + celery.conf | 19, 20 | Not started |
| 11. Nginx site configs + enable | 21, 22 | Not started |
| 12. Service start + MeshCentral first-boot sequence | 23, 24, 25, 26 | Not started |
| 13. NATS init/sync + final cleanup + completion report | 27, 28, 29, 30, 31 | Not started |

## TOTP handling (Robert's flagged risk area, observation 3)

Not designed yet — needs its own decision before Phase 9 starts. Real
constraints from the actual script: the TOTP secret is generated
server-side (Django management command), the barcode is ASCII-rendered to
the terminal, and a human scans/records it before continuing — there is no
way to skip this and no way to regenerate it without visiting the account
again. Ansible's `debug`/`pause` can display captured stdout and block for
confirmation the same way, but this is the one step where "idempotent
re-run" and "one-time secret" are in real tension (a re-run must NOT
silently regenerate a TOTP secret the operator already scanned into an
authenticator app) — needs a guard (skip TOTP generation if the superuser
account already exists) before this phase is built, not after.

## Secret persistence (Phase 1's other real design question)

install.sh generates 6 random secrets in memory and uses them once, same
run. An idempotent Ansible re-run can't regenerate them each time (would
invalidate the already-configured database users/Django install) — Phase 1
generates each one via `lookup('password', <path>, ...)`, which persists
to a file next to the play and returns the same value on every subsequent
run. Chosen path: `/root/.tacticalrmm_ansible_secrets/<name>` — root-only,
outside `/rmm`/`/meshcentral` entirely, never templated into a world-
readable file directly. Final credentials banner (still to design, matches
the wrapper's original Phase 5 intent) prints these for KeePass entry —
generated, never auto-pushed, per the estate's one-way KeePass flow.

## What stays out of scope

- Certbot/Let's Encrypt path — `EXARMMCLD001` is internal-only.
- `--use-own-cert` path — no external cert to provide.
- Turnkey/Webmin/LXC rejection checks — not applicable to this estate's
  Proxmox-VM-only deployment model, safe to drop rather than port.

## Original plan (2026-08-05, superseded — kept for history)

### Robert's five observations (source of the original plan)

1. `install.sh` is a "known source of truth" — make it a "break glass"
   script like the others (`bindme.sh`/`rudderme.sh`).
2. Aside from the interactive prompts, nothing `install.sh` does (package
   installs, repo clones) is something Ansible couldn't also do.
3. The authenticator QR/TOTP moment is the one place this could genuinely
   go wrong — needs careful capture/handling.
4. The install prints back credentials (MeshCentral auto-generated
   username/password) that need capturing into the KeePassXC harness, with
   a terminal fallback.
5. DNS records (`rmm`/`api`/`mesh`) must be verified to exist before
   starting.

### What was built under the original plan

`bootstrap/web/provision/tacticalrmmme.sh`, Sections 1-3 (pre-flight,
fetch+patch `install.sh`, answer cheat-sheet) — parked as of the pivot
above, not deleted. Full history in git log for that file.
