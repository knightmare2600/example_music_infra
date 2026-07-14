# windows_dc — Domain Controller Onboarding

Example Music Limited — JUKEBOX domain

## Overview

This module onboards a bare Windows Server host as an Additional Domain
Controller in the `jukebox.internal` domain.  It mirrors the `windows_bootstrap`
module for all generic stages (rename through OpenSSH), then adds DC-specific
stages 00 onwards.

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

Generic bootstrap (delegated to `windows_bootstrap/playbooks/`, no duplication here):

| File                      | Tag            | Description                                    |
|---------------------------|----------------|------------------------------------------------|
| `windows_bootstrap/playbooks/00-preflight.yml` | `bootstrap`   | Full PostOOBE bootstrap (rename → join → tools) |
| `windows_bootstrap/playbooks/20-registry.yml`  | `registry`    | Registry hardening                             |
| `windows_bootstrap/playbooks/30-chocolatey.yml`| `chocolatey`  | Chocolatey installation                        |
| `windows_bootstrap/playbooks/40-choco-packages.yml` | `choco_packages` | Packages (RSAT + server set)          |
| `windows_bootstrap/playbooks/50-binaries.yml`  | `binaries`    | Arch-aware binary deployment                   |
| `windows_bootstrap/playbooks/75-openssh.yml`   | `openssh`     | OpenSSH + Ansible key                          |
| `windows_bootstrap/playbooks/80-domainjoin.yml`| `domainjoin`  | Join JUKEBOX domain                            |

DC-specific (this module — own 00-preflight/major-step-of-10 numbering, separate from bootstrap's above):

| File                              | Tag            | Description                                    |
|------------------------------------|----------------|------------------------------------------------|
| `playbooks/00-dc-preflight.yml`       | `dc_preflight` | Replication source resolution + cred prompt |
| `playbooks/10-dc-install-features.yml`| `dc_features`  | AD-DS/DNS/GPMC feature install              |
| `playbooks/20-dc-promote.yml`         | `dc_promote`   | Install-ADDSDomainController (or Forest)    |
| `playbooks/30-dc-replicate.yml`       | `dc_replicate` | Force replication + SYSVOL + health check   |
| `playbooks/40-dc-summary.yml`         | `dc_summary`   | dcdiag + colourised build report            |

`00` is always the preflight ("before take off"); major steps increment by 10.
In-between/minor steps, if ever needed, would be `11`/`12`/`13`, `21`/`22`/`23`, etc.

---

## Usage

Run from the `ansible/` root. The DC onboarding inventory for each site lives in
`configs/inventory/<site>.ini` (e.g. `configs/inventory/fal.ini`).

### Full run (fresh build)

```bash
ansible-playbook -i configs/inventory playbooks/windows_dc/site.yml \
  -e target=EXADCSFAL002
```

### DC stages only (host already bootstrapped and domain-joined)

```bash
ansible-playbook -i configs/inventory playbooks/windows_dc/site.yml \
  -e target=EXADCSFAL002 \
  --skip-tags bootstrap
```

### DC promotion only

```bash
ansible-playbook -i configs/inventory playbooks/windows_dc/site.yml \
  -e target=EXADCSFAL002 \
  --tags dc_preflight,dc_features,dc_promote,dc_replicate,dc_summary
```

### Replication health check only (post-build)

```bash
ansible-playbook -i configs/inventory playbooks/windows_dc/site.yml \
  -e target=EXADCSFAL002 \
  --tags dc_replicate,dc_summary
```

---

## Credentials

`00-dc-preflight.yml` prompts for **four** values at runtime:

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

### Forest root — any site, not just CLD

Any site's DC can be the **first DC ever built** (forest root), not only
CLD. `00-dc-preflight.yml` prompts upfront (alongside the other operator
prompts, not mid-play):

> Is this the first DC in the AD Forest? (yes/no) `[no]`

It then probes candidate sources in priority order (see below). A
**reachable** candidate always wins regardless of the answer — the prompt
is only consulted if **none** are reachable:

- **yes** → `dc_is_forest_root=true` → `Install-ADDSForest`
- **no**  (the default) → the play aborts (no replication source, and not
  confirmed as a from-scratch forest build)

This is an operator-confirmed fact, not something inferred from the site
code — a non-CLD site being built first (e.g. before CLD exists yet, or in
a disconnected environment) is expected to answer "yes" too.

### CLD (Datacenter)

CLD probes FAL, then ODE, then BRK.

### FAL (Head office)

FAL DCs prefer to replicate from CLD if reachable.  If not, they replicate
from ODE or BRK.

### ODE and BRK (Regional hubs)

Same logic as FAL — CLD first, then other hubs (skipping self).

### Standard sites

Standard site DCs probe CLD → FAL → ODE → BRK in order.  If none is
reachable, the play falls back to any existing DC at `.10` for that site's
subnet.

---

## FSMO roles

FSMO placement is **reported** in `30-dc-replicate.yml` for hub sites but
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
- 2026-07-06  Renumbered 85/90/95/99 → 00/10/20/30/40; split promote into
  feature-install (10) and dcpromo (20); forest-root is now operator-
  confirmed on any site, not hardcoded to CLD
- 2026-07-06  Standard-site probe order now CLD → FAL → ODE → BRK (CLD
  added ahead of FAL)
- 2026-07-06  Forest-root confirmation ("Is this the first DC in the AD
  Forest?") moved from an interactive mid-play pause to a `dc_is_first_in_forest`
  vars_prompt answered upfront with the other operator prompts
