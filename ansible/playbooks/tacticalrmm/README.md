# playbooks/tacticalrmm/

> **2026-08-06 pivot — the section below is being superseded, in progress.**
> `install.sh` is being fully reimplemented as idempotent Ansible tasks
> directly in `tacticalrmm_server.yml`, not wrapped/run manually. See
> `PLAN-tacticalrmmme.md`'s "2026-08-06 pivot" section for the full
> reasoning and the phased build order. Phases 1-8 (prompts/secrets
> through Django settings + backend install/migrate) are done and
> live-verified against `EXARMMCLD001` as of 2026-08-07; Phases 9-13
> (superuser+TOTP, systemd units, nginx configs, service start +
> MeshCentral first boot, NATS init + cleanup) are not started. The rest
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

**Step 3 — VM prep (this playbook)**

```bash
ansible-playbook playbooks/tacticalrmm/tacticalrmm_server.yml \
  --limit tacticalrmm_servers
```

No `--user root -k` needed — the `ansible` user's SSH key is already
installed during the box's own PXE/preseed Debian install.

**Step 4 — DNS**: run `bind9-dns.yml --tags zones-full` (generates all three
CNAMEs — `rmm`/`api`/`mesh` — automatically, no manual step).

**Step 5 — Manual install** (on `EXARMMCLD001` itself, over SSH):

```bash
curl -o install.sh https://raw.githubusercontent.com/amidaware/tacticalrmm/master/install.sh
# Patch the OS check -- see above
chmod +x install.sh
./install.sh --insecure
```

When prompted:

| Prompt | Answer |
|---|---|
| Root domain | `jukebox.internal` |
| Frontend (rmm) subdomain | `rmm` |
| Backend (api) subdomain | `api` |
| Mesh subdomain | `mesh` |
| Email address | (Robert's own — used only for cert metadata under `--insecure`, not a real Let's Encrypt registration) |
| Django admin username | (Robert's choice) |

`--insecure` generates a self-signed certificate instead of requesting
Let's Encrypt — same reasoning as `EXAMSHCLD001`'s own TLS choice:
`EXARMMCLD001` is strictly internal/WireGuard-only, ACME's public-DNS +
inbound-80/443 requirement can't be satisfied here.

## Not yet built

- **Live-tested against real hardware, Trixie or otherwise.** Sections 1-4
  (hostname/network/packages/firewall) are a direct, proven adaptation of
  `rudder_server.yml`'s/`meshcentral_server.yml`'s own live-tested pattern.
  The Trixie/TacticalRMM combination is genuinely unverified — see above.
- **`EXAMSHCLD001` (standalone MeshCentral) role reconsideration.** Built and
  working (phase 1/2), but no longer the primary remote-access path now that
  TacticalRMM's bundled MeshCentral is the intended one — revisit later,
  not decided yet.
- **Reverse proxy, monitoring, logging, backups, hardening, disaster
  recovery** — later phases of the platform brief, not started.
