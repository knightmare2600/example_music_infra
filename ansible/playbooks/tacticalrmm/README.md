# playbooks/tacticalrmm/

> **CONFIRMED LIVE END TO END, 2026-08-07.** `install.sh` (github.com/
> amidaware/tacticalrmm) is interactive-only upstream, with no scriptable
> path (checked the real script, not guessed) — all 31 of its real steps
> have been reimplemented as idempotent Ansible tasks directly in
> `tacticalrmm_server.yml` instead, not wrapped/run manually. All 13
> phases built, and a full real run against `EXARMMCLD001` covering
> Phases 10-13 in one pass completed `failed=0` on the first attempt --
> MeshCentral first boot, NATS init, admin UI lockdown, and the final
> service restart all succeeded. See `PLAN-tacticalrmmme.md` for the full
> phase-by-phase build history, including two deliberate deviations from
> `install.sh`'s own approach (Phase 12), one genuinely missing step the
> original 31-step audit didn't catch (17a, Phase 11), and the real
> research trail behind running this on Debian Trixie (upstream's own
> `install.sh` only allows Debian 11/12 or Ubuntu 22.04 -- confirmed via
> `apt.postgresql.org`'s real `trixie-pgdg` repo that the version gate was
> an untested allowlist, not a hard technical wall).

Preps and fully installs `EXARMMCLD001` (hostname, static IP, base packages,
firewall, TacticalRMM itself end to end). Remote management platform, phase
3 — see `ansible/README.md`'s `## meshcentral` section and project notes
for the full brief.

TacticalRMM is for endpoint inventory/monitoring/alerting/dashboards/
reporting only — explicitly **not** config management or software
deployment, those stay SaltStack/Chocolatey's job (same non-negotiable split
the whole platform brief specifies).

**For day-to-day use of an already-built `EXARMMCLD001`** — logging in,
deploying/moving an agent, troubleshooting the mesh-agent-download bug —
see [docs/management/TacticalRMM_Beginners_Guide.md](../../../docs/management/TacticalRMM_Beginners_Guide.md)
instead of this file. Everything below is about building/rebuilding the
server itself.

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

**Step 5 onward — deploying/moving agents, day-to-day troubleshooting**: see
[docs/management/TacticalRMM_Beginners_Guide.md](../../../docs/management/TacticalRMM_Beginners_Guide.md),
not this file.

## Not yet built

- **Reverse proxy, monitoring, logging, backups, hardening, disaster
  recovery** — later phases of the platform brief, not started.

## `EXAMSHCLD001` (standalone MeshCentral) — RETIRED 2026-08-08

Decided, not just "revisit later" anymore: Robert used TacticalRMM's own
bundled MeshCentral for real remote-access work on 2026-08-07/08 and
confirmed it's a full replacement -- standalone `EXAMSHCLD001` is no longer
needed. Removed from live inventory (`configs/inventory/cld.ini`,
`configs/inventory/meshcentral.ini`, `host_vars/EXAMSHCLD001/`) -- its
`192.168.69.13` address is free for reuse. `playbooks/meshcentral/` itself
is kept as historical/reference material (see that role's own README,
retitled RETIRED), not deleted -- same treatment this estate already gives
other retired-but-real infrastructure (e.g. the FAL/ODE/BRK WireGuard hubs
in `group_vars/firewalls/main.yml`).
