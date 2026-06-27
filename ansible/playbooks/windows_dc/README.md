# windows_dc — Domain Controller Onboarding

Example Music Limited — JUKEBOX domain

## Overview

This module onboards a bare Windows Server host as an Additional Domain
Controller in the `jukebox.internal` domain.  It mirrors the `windows_bootstrap`
module for all generic stages (rename through OpenSSH), then adds DC-specific
stages 85 onwards.

`sites.csv` remains the single source of truth for site codes, subnets and
hub topology.

---

## Hostname convention

All DCs follow the standard EXA convention:

```
EXADCS<SITE><NNN>
```

Examples: `EXADCSFAL001`, `EXADCSODE002`, `EXADCSCLD001`

The `DCS` role code is the canonical form — any legacy `DCR` entries in
`devices.csv` are typos and treated as `DCS`.

---

## Playbook order

| File                      | Tag            | Description                                    |
|---------------------------|----------------|------------------------------------------------|
| `playbooks/00-bootstrap.yml` | `bootstrap`   | Full PostOOBE bootstrap (rename → join → tools) |
| `playbooks/10-rename.yml`    | `rename`      | Rename to EXADCS\<SITE\>\<NNN\>                |
| `playbooks/20-registry.yml`  | `registry`    | Registry hardening                             |
| `playbooks/30-chocolatey.yml`| `chocolatey`  | Chocolatey installation                        |
| `playbooks/40-choco-packages.yml` | `choco_packages` | Packages (RSAT + server set)          |
| `playbooks/50-binaries.yml`  | `binaries`    | Arch-aware binary deployment                   |
| `playbooks/75-openssh.yml`   | `openssh`     | OpenSSH + Ansible key                          |
| `playbooks/80-domainjoin.yml`| `domainjoin`  | Join JUKEBOX domain                            |
| `playbooks/85-dc-preflight.yml` | `dc_preflight` | Replication source resolution + cred prompt |
| `playbooks/90-dc-promote.yml`   | `dc_promote`   | AD-DS install + DC promotion               |
| `playbooks/95-dc-replicate.yml` | `dc_replicate` | Force replication + SYSVOL + health check  |
| `playbooks/99-dc-summary.yml`   | `dc_summary`   | dcdiag + colourised build report           |

Stages 00–80 delegate to `windows_bootstrap/playbooks/` — no duplication.

---

## Usage

### Full run (fresh build)

```bash
ansible-playbook -i inventory/<site>.ini site.yml \
  -e target=EXADCSFAL002 \
  -e sites_csv=../../files/sites.csv
```

### DC stages only (host already bootstrapped and domain-joined)

```bash
ansible-playbook -i inventory/<site>.ini site.yml \
  -e target=EXADCSFAL002 \
  -e sites_csv=../../files/sites.csv \
  --skip-tags bootstrap
```

### DC promotion only

```bash
ansible-playbook -i inventory/<site>.ini site.yml \
  -e target=EXADCSFAL002 \
  -e sites_csv=../../files/sites.csv \
  --tags dc_preflight,dc_promote,dc_replicate,dc_summary
```

### Replication health check only (post-build)

```bash
ansible-playbook -i inventory/<site>.ini site.yml \
  -e target=EXADCSFAL002 \
  -e sites_csv=../../files/sites.csv \
  --tags dc_replicate,dc_summary
```

---

## Credentials

`85-dc-preflight.yml` prompts for **four** values at runtime:

| Prompt                    | Purpose                                   | Default                   |
|---------------------------|-------------------------------------------|---------------------------|
| Domain Admin username     | Used for domain join + AD-DS promotion    | `JUKEBOX\Administrator`   |
| Domain Admin password     | As above                                  | *(masked)*                |
| Local Administrator user  | Pre-domain-join SSH auth + DSRM password  | `Administrator`           |
| Local Administrator pass  | As above                                  | *(masked)*                |

Credentials are **never written to disk** — they live only as in-memory
facts for the duration of the play.

---

## Special-sauce site logic

### CLD (Datacenter)

CLD may be the **first DC ever built** (forest root) or an additional DC
added later.  `85-dc-preflight.yml` probes FAL, ODE, and BRK on TCP/389:

- **None reachable** → `dc_is_forest_root=true` → `Install-ADDSForest`
- **Any reachable**  → `dc_is_forest_root=false` → `Install-ADDSDomainController`

CLD is never used as a replication *source* for site DCs.

### FAL (Head office)

FAL DCs prefer to replicate from CLD if reachable.  If not, they replicate
from ODE or BRK.  FAL cannot be a forest root.

### ODE and BRK (Regional hubs)

Same logic as FAL — CLD first, then other hubs (skipping self), then ABORT.

### Standard sites

Standard site DCs probe FAL → ODE → BRK in order.  If none is reachable,
the play falls back to any existing DC at `.10` for that site's subnet.
If still nothing is reachable the play aborts — a standard site DC cannot
be promoted without a replication source.

---

## FSMO roles

FSMO placement is **reported** in `95-dc-replicate.yml` for hub sites but
**never moved automatically**.  Moves are change-controlled operations.

Use `ntdsutil` or `Move-ADDirectoryServerOperationMasterRole` manually after
reviewing the summary output.

---

## devices.csv

Add the new DC to `devices.csv` after a successful build:

```
FAL,EXADCSFAL002,11,EXADCS,Windows Server 2022,DC secondary. Global Catalog
```

Then re-run `bind9-dns.yml` to refresh the DNS zone files if the IP is not
already covered by the suffix_map.

---

## Changelog

- 2026-06-25  Initial release
