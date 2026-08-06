# Plan: TacticalRMM as an end-to-end Ansible install

**Status: superseded direction as of 2026-08-06 — see "2026-08-06 pivot" below.**
**Phases 1-6 (prompts/secrets, compatibility checks + base packages, nginx/
NodeJS/Python 3.11.8/Redis/Git, PostgreSQL 18 + databases, repo clones,
NATS server + nats-api) DONE. Phases 7-13 not started.**

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
| 2. Compatibility checks + base packages | 1, 2 | **DONE, this session** |
| 3. Nginx, NodeJS, Python 3.11.8, Redis, Git | 7, 8, 9, 10 | **DONE, this session** |
| 4. PostgreSQL 18 + databases | 11 | **DONE, this session** |
| 5. Repo clones | 12 | **DONE, this session** |
| 6. NATS server + nats-api binaries | 13, 16 | **DONE, this session** |
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

## Secret persistence — corrected 2026-08-06, real live catch

First attempt at this got it wrong twice over: generated secrets via
`lookup('password', <path>, ...)` pointed at `/root/.tacticalrmm_ansible_
secrets/<name>` on the control node, to persist across re-runs. Failed
live — `EXAANSCLD001` runs Ansible as the `ansible` user, not root, on
purpose, and `delegate_to: localhost`/`become: false` can never write to
`/root/*` there. Robert's correction went further than the path bug
though: inventing a private Ansible-only secret store at all was the wrong
instinct. This estate already has a specific, deliberate posture for
locally-generated secrets — `docs/Example Music Limited — KeePassXC CLI
Automation.md` §7a's one-way flow (Ansible MUST NEVER write to KeePass; a
read-only lookup plugin is listed under §9 Future Enhancements, doesn't
exist yet) — and a real, working precedent for exactly this situation:
`salt/playbooks/20-saltgui.yml`. Its pattern: generate/prompt the secret,
use it immediately in the same run to configure the real thing, print it
**once** in a final banner, and the human runs `benarbejde/kpcli_
wrapper.py` themselves afterward to file it into KeePassXC. Nothing
Ansible-managed ever touches disk.

Section 8 now generates each secret via `lookup('password', '/dev/null',
...)` — the standard Ansible idiom for a genuinely ephemeral random value,
verified locally (two calls return different values, nothing persisted).
Idempotency for whatever later phase actually creates the PostgreSQL
roles/writes `local_settings.py` with these is that phase's own problem —
solved by checking the target's already-deployed state first (e.g.
`postgresql_user`'s `no_password_changes`, or reading an existing
`local_settings.py`'s `SECRET_KEY` back rather than overwriting it), not
by a secret store here. Final credentials banner (still to design, later
phase) prints what needs to go in KeePass, once, matching
`20-saltgui.yml`'s own convention exactly.

## What stays out of scope

- Certbot/Let's Encrypt path — `EXARMMCLD001` is internal-only.
- `--use-own-cert` path — no external cert to provide.
- Turnkey/Webmin/LXC rejection checks — not applicable to this estate's
  Proxmox-VM-only deployment model, safe to drop rather than port.

## Deliberate deviation: dedicated service user (Phase 5, carries to Phase 10)

install.sh creates no dedicated service user at all — every later systemd
unit (`rmm`/`daphne`/etc.) runs as `${USER}` (whichever human ran the
installer via sudo), group `www-data`. That doesn't translate to this
play's all-root Ansible execution model, and running the real services as
root would be worse than install.sh's own non-root intent, not equivalent
to it. Phase 5 creates a dedicated system account instead
(`rmm_service_user`, default `tacticalrmm`, no login shell) — owns `/rmm`
and the community-scripts checkout now; Phase 10's systemd units need to
use `User={{ rmm_service_user }}` / `Group=www-data` instead of
install.sh's own `${USER}`, not a plain port.

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
