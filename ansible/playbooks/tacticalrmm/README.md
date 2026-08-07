# playbooks/tacticalrmm/

> **2026-08-06 pivot — the section below is being superseded, in progress.**
> `install.sh` is being fully reimplemented as idempotent Ansible tasks
> directly in `tacticalrmm_server.yml`, not wrapped/run manually. See
> `PLAN-tacticalrmmme.md`'s "2026-08-06 pivot" section for the full
> reasoning and the phased build order. **CONFIRMED LIVE END TO END,
> 2026-08-07.** All 13 phases / all 31 install.sh steps built, and a full
> real run against `EXARMMCLD001` covering Phases 10-13 in one pass
> completed `failed=0` on the first attempt -- MeshCentral first boot,
> NATS init, admin UI lockdown, and the final service restart all
> succeeded. See `PLAN-tacticalrmmme.md`'s own per-phase sections for
> what was found/decided along the way, including two deliberate
> deviations from install.sh's own approach (Phase 12) and one genuinely
> missing step the original 31-step audit didn't catch (17a, Phase 11).
> The rest
> of "Why the actual install isn't automated here" below still describes
> `install.sh`'s own constraints accurately, it just no longer describes
> what this repo does about them.

Preps `EXARMMCLD001` (hostname, static IP, base packages, firewall) for
TacticalRMM's own official installer. Remote management platform, phase 3 —
see `ansible/README.md`'s `## meshcentral` section and project notes for the
full brief. MeshCentral (phase 1/2) got priority; this is next.

TacticalRMM is for endpoint inventory/monitoring/alerting/dashboards/
reporting only — explicitly **not** config management or software
deployment, those stay SaltStack/Chocolatey's job (same non-negotiable split
the whole platform brief specifies).

## Why the actual install isn't automated here (superseded, see banner above)

TacticalRMM's `install.sh` (github.com/amidaware/tacticalrmm) has no
scriptable path — checked the real script, not guessed. It's
interactive-only: prompts for the root domain, three subdomains (frontend/
backend/mesh), an email address, and Django admin credentials, and displays
a TOTP barcode mid-install. No flags, environment variables, or config file
bypass any of this.

Automating it via `ansible.builtin.expect` was considered and rejected —
Robert's call, 2026-08-04. The risk of a scripted prompt-feed dying partway
through, after `install.sh` has already made irreversible changes (DB
migrations, cert generation, systemd units), outweighs the convenience.
Treated the same way this estate already treats `bindme.sh`/`rudderme.sh`: a
documented, deliberate manual step, not a gap to force-close.

## Debian Trixie — genuinely untested combination

`install.sh`'s own OS check only allows Debian 11 (bullseye), Debian 12
(bookworm), or Ubuntu 22.04 (jammy) — it hard-rejects anything else,
including Trixie. Checked the actual script before deciding what to do about
it:

- PostgreSQL's apt repo line uses `$codename-pgdg`, dynamically interpolated
  from `lsb_release`, not hardcoded to a specific release.
- Python is built from source at a pinned version (3.11.8), not taken from
  the OS's own `python3` package — version-independent by construction.
- Node.js and nginx are similarly fetched from generic, codename-parameterised
  repos.

The version gate itself is a simple `if` block early in the script comparing
`$relno`/`$codename` against an allowlist and printing `"ERROR: Only Debian
11, Debian 12 and Ubuntu 22.04 are supported."` if it doesn't match. Nothing
found in the package-install logic looks genuinely Trixie-incompatible — this
reads like an untested support allowlist, not a hard technical wall. Robert's
call, 2026-08-04: try Trixie anyway, with the guard patched, rather than
downgrade `EXARMMCLD001` to bookworm.

**Update, 2026-08-06 — confirmed, not just presumed anymore:** `apt.postgresql.org`
genuinely publishes a `trixie-pgdg` repo (curled its `dists/` listing
directly), and `postgresql-18` is really in it (curled the `trixie-pgdg`
Packages index, real version strings returned). Resolved while building
`tacticalrmm_server.yml`'s Section 11 (Ansible-native PostgreSQL install,
see `PLAN-tacticalrmmme.md`'s "2026-08-06 pivot") — the whole
"genuinely unverified" framing below described the now-superseded manual
`install.sh` path; kept for the parked wrapper's own historical context.

### Patching the OS check

Before running `install.sh`, download it and patch the version comparison
(the exact line numbers will drift as upstream changes the script — find the
block that prints the "Only Debian 11, Debian 12 and Ubuntu 22.04" error and
widen the accepted `$relno` list to include Trixie's release number, or
comment the whole check block out). Do this on a copy, not by piping
`curl | bash` directly, so the patch is inspectable before it runs:

```bash
curl -o install.sh https://raw.githubusercontent.com/amidaware/tacticalrmm/master/install.sh
# Edit install.sh: find the Debian/Ubuntu version check (search for
# "Only Debian 11, Debian 12 and Ubuntu 22.04") and widen it, or comment
# out that one `not_supported` call. Leave everything else untouched.
chmod +x install.sh
```

If PGDG doesn't have a `trixie-pgdg` repo yet, the PostgreSQL install step
will fail loudly and cleanly (apt 404) rather than silently — at that point
the fallback is rebuilding `EXARMMCLD001` on bookworm and re-running this
playbook against it (no work lost — the playbook is idempotent VM prep, not
tied to Trixie specifically).

## DNS — three subdomains needed

`install.sh` will prompt for three subdomains, all under the same root
domain (`jukebox.internal`):

| Subdomain | Purpose | Auto-generated? |
|---|---|---|
| `rmm.jukebox.internal` | Frontend web UI | **Yes** — `role_codes.csv`'s `RMM` row has `DNSAlias=rmm` |
| `api.jukebox.internal` | Backend API | **Yes** — `bind9-dns.yml`'s `bind9_extra_cnames` var |
| `mesh.jukebox.internal` | TacticalRMM's own bundled MeshCentral | **Yes** — `bind9-dns.yml`'s `bind9_extra_cnames` var (this name was freed from the standalone `EXAMSHCLD001` build specifically for this — see `role_codes.csv`'s `MSH` row notes) |

All three are now generated on every `bind9-dns.yml --tags zones-full` run —
no manual DNS step. `role_codes.csv`'s `DNSAlias` column is one-alias-per-
role-code, so it only ever covers `rmm`; `api`/`mesh` come from a small
`bind9_extra_cnames` list in `bind9-dns.yml`'s own `vars:` (added 2026-08-04,
Robert: "add these records to the bind9 playbook" — the alternative, hand-
editing the deployed zone file, would have been silently overwritten on the
next run same as any other Ansible-templated file). Add more entries there
if another device ever needs a second/third friendly name.

## Quick start

**Step 1 — Inventory is already in `configs/inventory/tacticalrmm.ini`.**

**Step 2 — host_vars are pre-filled** (`host_vars/EXARMMCLD001/main.yml`) —
static IP `192.168.69.14`, CLD LAN.

**Step 3 — full install (this playbook)**

```bash
ansible-playbook playbooks/tacticalrmm/tacticalrmm_server.yml \
  --limit tacticalrmm_servers
```

No `--user root -k` needed — the `ansible` user's SSH key is already
installed during the box's own PXE/preseed Debian install. This one
playbook now does the entire install end to end (VM prep through NATS
init and the completion report — see the banner at the top of this file
and `PLAN-tacticalrmmme.md` for the full phase breakdown) — there is no
separate manual `install.sh` step any more, superseded 2026-08-06 and
confirmed live end to end 2026-08-07.

`--insecure` (baked into the playbook, Section 15) generates a
self-signed certificate instead of requesting Let's Encrypt — same
reasoning as `EXAMSHCLD001`'s own TLS choice: `EXARMMCLD001` is strictly
internal/WireGuard-only, ACME's public-DNS + inbound-80/443 requirement
can't be satisfied here.

**Step 4 — DNS**: run `bind9-dns.yml --tags zones-full` (generates all three
CNAMEs — `rmm`/`api`/`mesh` — automatically, no manual step).

**Step 5 — Deploy an agent to an endpoint**

From the TacticalRMM web UI (`https://rmm.jukebox.internal`): **Agents →
+ Add Agent**, pick the target Client/Site and agent type
(`server`/`workstation` — match the actual endpoint, don't default to
`server`). This generates a **signed, time-limited download URL** (expires
within about an hour) and a matching one-time `--auth` deployment token —
copy both fresh each time, neither is reusable and neither belongs in a
committed doc or script.

On the Windows endpoint (PowerShell, confirmed live 2026-08-07):

```powershell
# 1. Download the installer -- <signed-url> and the version/arch in the
#    filename both come straight from the web UI dialog above, copy exactly
iwr '<signed-download-url-from-web-ui>' -OutFile tacticalagent-v<version>-windows-<arch>.exe

# 2. Silent install of the installer itself
tacticalagent-v<version>-windows-<arch>.exe /VERYSILENT /SUPPRESSMSGBOXES

# 3. Brief pause -- lets the installer settle before the next step registers
#    the agent with the backend
ping 127.0.0.1 -n 7

# 4. Register the agent with EXARMMCLD001
"C:\Program Files\TacticalAgent\tacticalrmm.exe" -m install `
  --api https://api.jukebox.internal `
  --client-id <client-id> --site-id <site-id> `
  --agent-type server `
  --auth <auth-token-from-step-1> `
  --rdp --ping --insecure
```

`--insecure` is **required** here too — same self-signed cert as the
server itself; omitting it fails the install. `--rdp`/`--ping` are
optional per-endpoint feature toggles (enable RDP, respond to ICMP), not
required for a successful install.

**Troubleshooting — "Unable to download the mesh agent from the RMM."**
A real bug hit live 2026-08-07, root-caused and fixed in
`tacticalrmm_server.yml` (see `PLAN-tacticalrmmme.md`'s Phase 12 section):
a race in the playbook's own MeshCentral-readiness check let
`AddDeviceGroup` run before MeshCentral had actually finished restarting,
so the `TacticalRMM` device group silently never got created despite the
task reporting success. Diagnose directly rather than guessing:

```bash
sudo -u tacticalrmm bash -c "cd /rmm/api/tacticalrmm && /rmm/api/env/bin/python manage.py check_mesh"
```

Walks the exact same code path the agent installer hits and reports
exactly which stage fails. If it stops at "Error: you are using a custom
mesh device group name...", check what device groups actually exist
(`meshctrl.js ... ListDeviceGroups`, credentials in the MeshCentral
completion banner / KeePass) and create the missing one directly rather
than re-running the whole playbook.

## Not yet built

- **`EXAMSHCLD001` (standalone MeshCentral) role reconsideration.** Built and
  working (phase 1/2), but no longer the primary remote-access path now that
  TacticalRMM's bundled MeshCentral is the intended one — revisit later,
  not decided yet.
- **Reverse proxy, monitoring, logging, backups, hardening, disaster
  recovery** — later phases of the platform brief, not started.
