# Plan: TacticalRMM as an end-to-end Ansible install

**Status: superseded direction as of 2026-08-06 — see "2026-08-06 pivot" below.**
**CONFIRMED LIVE END TO END, 2026-08-07.** All 13 phases / all 31
install.sh steps (+ step 17a, found missing) built, and a full run of
`tacticalrmm_server.yml` against `EXARMMCLD001` covering Phases 10-13 in
one pass completed with `failed=0` (ok=170, changed=39, skipped=39) on
the first real attempt -- MeshCentral first boot, admin account creation,
`AddDeviceGroup`, NATS init, admin UI lockdown, and the final backend
service restart all succeeded. Phases 1-9 were already independently
live-verified earlier the same day. See each phase's own section below
for what was found/decided along the way, including two deliberate
deviations from install.sh's own approach (Phase 12) and one genuinely
missing step the original 31-step audit didn't catch (17a, Phase 11).

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
17a. **Frontend web build download** — genuinely missing from this list
    until 2026-08-07, found while researching Phase 11. `WEB_VERSION`/
    `WEBTAR_URL` via `manage.py get_config webversion` / `get_webtar_url`,
    tarball downloaded + extracted to `/var/www/rmm/dist`, `env-config.js`
    written, `chown www-data:www-data`. `frontend.conf` (step 21) serves
    directly from this directory and 404s without it. See "Phase 11" section
    below for the full finding, including why `get_webtar_url` living in
    an Enterprise-Edition-licensed app doesn't block a plain self-hosted
    install.
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
| 7. MeshCentral install (files, not yet running) | 14 | **DONE, this session** |
| 8. Django settings + backend install/migrate | 15, 17 | **DONE, live-verified 2026-08-07** |
| 9. Superuser + TOTP | 18 | **Built + live-verified 2026-08-07** — see below |
| 10. Systemd units + celery.conf | 19, 20 | **Built + live-verified 2026-08-07** |
| 11. Nginx site configs + enable | 21, 22 (+ 17a, found missing) | **Built + live-verified 2026-08-07** — see below |
| 12. Service start + MeshCentral first-boot sequence | 23, 24, 25, 26 | **Built + live-verified 2026-08-07** — see below |
| 13. NATS init/sync + final cleanup + completion report | 27, 28, 29, 30, 31 | **Built + live-verified 2026-08-07** — see below |

## TOTP handling (Robert's flagged risk area, observation 3)

**Built + live-verified 2026-08-07 (Section 16), against EXARMMCLD001 --
superuser+installer account created, TOTP secret generated, barcode
displayed with a clean leading blank line, backup file written, both
credentials banners fired, failed=0.** Real constraints
confirmed against `install.sh` and the real `generate_totp.py`/`models.py`
source (not guessed): `generate_totp` only prints a random base32 value
and touches no database table.

**Correction, 2026-08-07 (live, Robert hit the actual `generate_barcode`
bug below and this got checked properly as a result):** the passage
that used to sit here claimed the secret only gets bound to the
account's `totp_key` field later, during the operator's own first
browser login -- that was wrong, not re-verified against the real
source at the time it was written. Checked `generate_barcode.py`
directly: `user.totp_key = code; user.save(update_fields=["totp_key"])`
runs immediately and unconditionally, BEFORE the command even attempts
to render the barcode -- so the secret is bound to the account the
moment this playbook's own `generate_barcode` task runs, not later in
a browser. The guard (whether the Django superuser account already
exists) is still correct and still needed -- just for the right
reason: it stops a re-run from creating a second account and binding a
second, different secret, not because the playbook "can't see" the
binding moment (it's the one causing it).

`generate_barcode.py` also shells out to `qr` (the `qrcode` pip
package's own console-script, already in the venv from Section 15's
`requirements.txt` -- not an apt package, `install.sh` doesn't install
one either) via `subprocess.run(..., shell=True)`, PATH-dependent. Real
live bug, 2026-08-07: this task called the venv's Python directly
(correct for imports, matches every other `manage.py` task in this
file) but never put `/rmm/api/env/bin` on `PATH` for that subprocess
call -- `install.sh` always `source`s the venv first for exactly this
reason. `qr` silently failed to be found; `generate_barcode.py` never
checks the subprocess result, so nothing errored, the barcode just
never rendered -- while `totp_key` was still correctly set (per the
correction above), Robert had no visible barcode to scan and manually
re-ran the command later, hitting the same PATH gap directly. Fixed by
adding `environment: PATH: "/rmm/api/env/bin:{{ ansible_env.PATH }}"`
to the task.

`createsuperuser` runs `--noinput` with `DJANGO_SUPERUSER_PASSWORD` set
from Section 8's already-ephemeral `rmm_django_admin_password` -- avoids
Ansible needing to handle an interactive TTY password prompt at all, and
matches Robert's own instruction that Django passwords are Ansible's to
generate like any other secret.

Display + backup, per Robert's explicit ask (2026-08-07): the raw barcode
is echoed via `debug` with a leading/trailing blank line so the module's
own "msg:" header line doesn't run into row 1 of the barcode's character
grid, AND the raw secret is additionally written to a root-only
(`0600`, `owner: root`) file on the target host,
`/root/.tacticalrmm_totp_backup.txt` -- "cover our arses" durable backup,
not just a one-time terminal display. The file also documents the exact
`generate_barcode` invocation needed to re-render the same barcode later
if the terminal output is lost before scanning. Not KeePass-routed --
this is a target-host operational backup file, not a control-node secret
store, so the one-way-flow policy (`docs/Example Music Limited —
KeePassXC CLI Automation.md` §7a) doesn't apply the same way it does to
Section 8's control-node-adjacent secrets; still never committed to git
since it never leaves the target host.

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

## Phase 8 live confirmation — two real bugs, 2026-08-07

`manage.py migrate` hard-failed live with `IndexError: list index out of
range` on `settings.py`'s own `ALLOWED_HOSTS[0]` -- two distinct root
causes, found and fixed one after the other, both against real
`EXARMMCLD001` runs, not guessed:

1. **Write gate never fired.** Sections 14/15 originally gated writing
   `config.json`/`local_settings.py` on "was the Postgres role just
   created THIS run" -- false once the roles already existed from earlier
   Phase 4 testing, so the files had literally never been written.
   Decoupled the gate onto the settings file's own existence (`stat` +
   `force: false`), with the Postgres role's password explicitly
   `ALTER ROLE`'d to match immediately before the first-ever write. Fixed
   for both sections; credentials banners added for the password-sync
   path (Section 11's own banner only covers role *creation*, not this
   resync-on-first-write case).
2. **Wrong path, once the write did fire.** `local_settings.py` was still
   landing at `/rmm/api/tacticalrmm/local_settings.py` -- but
   `settings.py`'s own `from .local_settings import *` (confirmed via the
   real settings.py source, not guessed) is a relative import *inside*
   the `tacticalrmm` package, resolving to
   `/rmm/api/tacticalrmm/tacticalrmm/local_settings.py`, one directory
   deeper. `with suppress(ImportError)` upstream swallowed the miss
   silently -- same exact traceback as bug 1, from an unrelated cause.
   Confirmed the correct path against `install.sh`'s own `$local_settings`
   variable before fixing. Section 14's `config.json` path was swept for
   the same class of bug and found correct -- no matching issue there.

## Phase 10 -- why nats.service is write-only here, not enable/start too

Built 2026-08-07 (Section 17): all 7 systemd unit files
(rmm/daphne/nats/nats-api/celery/celerybeat/meshcentral) + `/etc/conf.d/
celery.conf`, written only -- no `systemctl enable`/`start` of anything.
Confirmed against the real `install.sh`, not guessed: none of these units
get enabled/started until its own step 23 (a separate, later block in the
script, well after every unit file and nginx site config already exists) --
this repo's own Phase 12 is the equivalent point.

`nats.service`'s `ExecStart` references `/rmm/api/tacticalrmm/nats-rmm.conf`,
a file that does not exist yet at this point and won't until much later.
Traced its actual origin through three layers, since `install.sh` itself
never writes it directly: `manage.py reload_nats` (a step inside
`install.sh`'s own step 27, "NATS init") calls `reload_nats()` in
`tacticalrmm/utils.py`, which is the function that actually generates
`nats-rmm.conf` and only then signals `nats-server` to reload -- confirmed
by reading that function's real source, not the management command
wrapper alone. `install.sh` itself: `systemctl enable nats.service` happens
early (alongside the other units), but `systemctl start nats.service` is
the very last thing done in that block, strictly after
`initial_db_setup`/`reload_nats`/`sync_mesh_with_trmm` all run. Starting
`nats.service` any earlier than that would crash-loop against a config file
that doesn't exist. This repo's own Phase 13 (NATS init/sync + final
cleanup) is where `reload_nats`'s equivalent needs to run, before anything
tries to start this unit.

## Phase 11 -- frontend web build download, missing from the original audit

Built 2026-08-07 (Section 18): nginx site configs for backend
(`rmm.conf`)/MeshCentral (`meshcentral.conf`)/frontend (`frontend.conf`),
`sites-available`→`sites-enabled` symlinks, and the frontend web build
download+extract that step 17a above documents. Not yet live-tested.

Confirmed `/etc/nginx/sites-available`/`sites-enabled` don't exist on this
build without an explicit `mkdir` -- the nginx.org upstream package
(Section 10's own apt source) doesn't ship the Debian-style
sites-available/sites-enabled convention; `install.sh` itself `mkdir -p`s
both right after writing `nginx.conf`, ported the same way.

`frontend.conf`'s `root /var/www/rmm/dist;` was the thing that surfaced
the missing step 17a: nothing in the original 31-step enumeration
downloads the actual React SPA build. Traced it in `install.sh`:
`WEB_VERSION=$(manage.py get_config webversion)` /
`WEBTAR_URL=$(manage.py get_webtar_url)`, then `wget`+`tar` into
`/var/www/rmm`, `env-config.js` written with the backend URL, `chown
www-data:www-data -R` on `dist/`. `get_webtar_url` turned out to live in
`api/tacticalrmm/ee/reporting/` (Enterprise Edition-licensed code) --
checked the actual command source before trusting `install.sh` calls it
safely for a plain self-hosted install: it returns a public,
unauthenticated GitHub Releases URL
(`github.com/amidaware/tacticalrmm-web/releases/...`) unless a paid
`CodeSignToken` database row already exists, which nothing in this
estate's install ever creates -- confirmed the `reporting` app's own
migrations already ran cleanly in Phase 8's real live output, so the app
is genuinely active regardless of EE licensing, only specific paid
features inside it are gated. Gated the whole download+extract+chown
block on `/var/www/rmm/dist/env-config.js` not already existing, same
existence-check idiom used throughout this file.

## Phase 12 -- service start + MeshCentral first boot, two deliberate deviations

Built 2026-08-07 (Section 19): enables + starts
rmm/daphne/celery/celerybeat/nginx, enables + first-boots MeshCentral,
generates and appends `MESH_TOKEN_KEY` to `local_settings.py`, creates the
MeshCentral admin account + promotes it + adds the "TacticalRMM" device
group. Not yet live-tested.

**Deviation 1 -- `state: started`, not `state: restarted`.** install.sh
unconditionally stops-then-starts rmm/daphne/celery/celerybeat/nginx on
every run, harmless for a script that only ever runs once. This playbook
is meant to stay safely re-runnable -- blindly restarting live services
(dropping in-flight uWSGI/websocket connections, celery workers) on every
ongoing maintenance run would be a real regression, not a faithful port.
First run here still starts everything correctly since nothing is running
yet. **RETROFITTED 2026-08-08** (Robert's ask, post-LAX-onboarding backlog
item 5): every config-writing task in Sections 10/15/17/18/19/20
(local_settings.py write + MESH_TOKEN_KEY append, every rmm/daphne/celery/
celerybeat/nats/nats-api/meshcentral systemd unit, nginx.conf + every
site config + its sites-enabled symlink) now carries the right `notify:`
handler(s), mapped to exactly which service(s) each config affects --
"Restart TacticalRMM backend services" (rmm/daphne/celery/celerybeat),
"Restart NATS services" (nats/nats-api), "Restart MeshCentral", "Reload
nginx" (a graceful `systemctl reload`, not a full restart), alongside the
pre-existing "Reload systemd daemon". Section 19's own `state: started`
first-boot loop is unchanged -- still correct, distinct behaviour for a
box with nothing running yet; the notify: handlers only fire on a re-run
where one of those files genuinely changed. Every `notify:` name
cross-checked against the handlers block (no typos/dangling references)
and the whole file re-passed `ansible-playbook --syntax-check` before
landing.

**Deviation 2 -- readiness check uses `journalctl -u meshcentral.service
--no-pager -n 100` (last 100 lines), not install.sh's own `-b` (entire
current boot).** `-b` risks matching a stale "ready" line from a much
earlier start within the same boot on a re-run, giving a false-positive
before the just-issued restart has actually produced a fresh one. Also
bounded (retries: 60, delay: 5 -- 5 minutes total, matching install.sh's
own comment that first boot "can take anywhere from a few seconds to a
few minutes") rather than install.sh's unbounded while-loop -- a play
that can hang forever on a genuine failure is worse than one that fails
loudly with a clear timeout.

Two separate first-boot gates, matching install.sh's own two distinct
steps (25 vs 26), not conflated: `MESH_TOKEN_KEY` presence in
`local_settings.py` gates the restart + readiness-wait + `--logintokenkey`
dance; a marker file this playbook writes itself
(`meshcentral-data/.trmm_admin_setup_done`) gates account creation +
`AddDeviceGroup` -- MeshCentral's own CLI has no clean "does this account
already exist" query to check against instead, so this playbook owns that
idempotency itself, same class of problem Section 16 already solved for
the Django superuser (there, a native `manage.py shell` check exists to
use instead).

## Phase 13 -- NATS init/sync, admin UI lockdown, completion report (final phase)

Built 2026-08-07 (Section 20) -- **all 13 phases / all 31 install.sh
steps (+ step 17a) are now built.** Not yet live-tested end to end.

Gated on `/rmm/api/tacticalrmm/nats-rmm.conf`'s own existence -- the
exact file `manage.py reload_nats` generates (see Phase 10's own section
above), so its presence is a precise, already-established proxy for
"has `initial_db_setup`/`reload_nats`/`sync_mesh_with_trmm` already run",
rather than a new marker file. `nats.service` only gets `state: started`
inside this same gate -- the config it needs to not crash-loop on
(`nats-rmm.conf`) is the exact thing this block just created.

`ADMIN_ENABLED = False` uses `lineinfile`'s own native idempotency (won't
rewrite a line that already says `False`) rather than a custom gate. Its
restart of `rmm`/`daphne`/`celery`/`celerybeat` is wired as a real
`notify:` handler, firing only when that line actually changes --
Django only reads `local_settings.py` at process start, so this restart
is genuinely necessary whenever it fires, unlike Section 19's initial
service bring-up (deliberately not restarting live services on every
run). A concrete instance of the `notify:`-handler pattern flagged as a
broader follow-up in Phase 12's own section above -- this one narrow
case is wired up now because the trigger condition (the line actually
changing) is precise and easy to get right; the general case (mapping
every config file to exactly which services it affects) is still the
scoped follow-up work, not done.

Completion report split into two `debug` tasks: a general one (frontend
URL) shown every run, and a MeshCentral-credentials one gated on the same
`_rmm_mesh_account_check` used in Section 19 -- `rmm_mesh_password` is
one of Section 8's ephemeral secrets, so printing it unconditionally on
every re-run (once account creation is already skipped) would show a
fresh, wrong value that no longer matches the live account's real
password. install.sh's own NAT/hairpin guidance is deliberately not
ported -- `EXARMMCLD001` has no port-forwarded/public-facing scenario to
warn about, internal-DNS + WireGuard-routed only, same reasoning already
established elsewhere in this repo for why `--insecure`/self-signed was
chosen over Let's Encrypt.

## Phases 11-13 live confirmation, 2026-08-07 -- full end-to-end run, first attempt

One real `tacticalrmm_server.yml` run against `EXARMMCLD001` (no `-k`,
key auth worked cleanly per the SSH preflight gate) covered Phases 11-13
in a single pass -- `failed=0`, `ok=170`, `changed=39`, `skipped=39`.
Nothing needed a second fix. Confirmed live, not just harness-clean:

- `rmm`/`daphne`/`celery`/`celerybeat`/`nginx` all started cleanly on
  first bring-up (confirmed running/active in the transcript's own
  systemd status output for each).
- MeshCentral's first boot generated its own certs
  (`mesh.jukebox.internal`, real SHA384 hashes in the journal) and
  reported ready inside the 5-minute bound -- actual wall-clock time was
  well under a minute (cert generation + code-signing + startup all
  finished by the "MeshCentral HTTP server running on port 4430, alias
  port 443" line, ~23 seconds after the unit started).
- MeshCentral admin account created, promoted, `AddDeviceGroup` succeeded
  over WSS, `.trmm_admin_setup_done` marker written.
- `initial_db_setup`/`reload_nats`/`sync_mesh_with_trmm` all ran clean;
  `nats.service` started successfully against the freshly-generated
  `nats-rmm.conf`; `nats-api.service` enabled and started.
- `ADMIN_ENABLED = False` applied, `notify:`-triggered restart of the
  four backend services fired correctly (confirmed in the handler output
  -- all four show `"state": "restarted"` in `invocation.module_args`,
  not just `started`).
- Completion report printed the frontend URL and (first-run only)
  MeshCentral credentials, both banners gated correctly.

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
