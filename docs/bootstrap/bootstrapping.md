# Example Music — Infrastructure Bootstrapping Guide



> **IP addressing note:**
>
> Throughout this document, `192.168.139.0/24` is the real internal provisioning subnet. `192.0.8.x` addresses are real public IPs assigned by OVH.
> These are entirely separate ranges — `192.168.x.x` is RFC 1918 private space: `192.0.8.x` is a publicly routed OVH block. Do not confuse them with `192.0.2.x` (RFC 5737 documentation range, used only in worked examples in other docs).
>
> The domain used throughout is `jukebox.internal` (internal AD forest root). Public DNS uses `example.com` — see §0.4.

---

## Changelog

| Date       | Change                                                       |
| ---------- | ------------------------------------------------------------ |
| 2026-03-07 | Initial version                                              |
| 2026-03-08 | Rework some sections. Explain more about "starting with nothing but a laptop and a flask of tea" |
| 2026-05-17 | Spruce up the static web server output for easier debug      |
| 2026-07-10 | Major correction pass, prompted by a full line-by-line audit against `benarbejde/`'s source-of-truth files and the real `bootstrap/web/` tree. Corrected: the Standard IP Convention table (firewall was mapped to `.1`, actually `.253`/`.254`; `.15` PRV and `.82`-`.94` WAP were missing entirely); the firewall's identity throughout (`EXAFWLCLD001` → `EXAFWLVRK001`, with its real vRACK/CLD-LAN dual-interface addressing, not a single `192.168.139.253`); the provisioning-server narrative (`EXASTRPCLD001` was superseded by `EXAPRVVRK001`, not "migrated to" `EXAANSCLD001` — those are two separate hosts on separate subnets); the §1.5 topology diagram (added the missing `EXADNSVRK001`, fixed the PBX/firewall IPs, fixed the `192.168.139.0/24` subnet mislabel); the `web/` directory tree in §2.3 (previously described several directories and files — `gparted/`, `phoenixpe/`, `proxmox/boot/`, two `.msi` files — that don't exist anywhere in this repo; replaced with the real, verified current layout); the `.ipxe` dotfile claim in §4.2 (never existed; real file is `menu.ipxe`); site-code errors (`ABR`→`ABD`, fictional `GAA` removed, the known-site-codes list refreshed against `sites.csv`); the first-boot.sh sample transcript (was internally inconsistent — wrong hostname for the worked example, wrong gateway octet reinforcing the `.1`-is-gateway error, mismatched IPs before/after reboot); §8's PostOOBE.cmd/Join-DomainAndBootstrap.ps1 description (previously described a `Z:`-mapping/`DEPLOYTOOLS_PASS` flow and a "12-stage" script that don't match the real files — real `PostOOBE.cmd` is a 3-line hardcoded-UNC-path launcher, real script is 22+ stages); §9's boot-server-IP-change file table (wrong/nonexistent paths). Also flagged, not resolved: `example.org`'s status as a registered domain is inconsistent between this doc, `Join-DomainAndBootstrap.ps1`, and `ad_forest.json`; `PostOOBE.cmd`'s `\\DC01\deploytools\` vs the script's own `$DeployToolsShare` (`\\EXADCSCPH001\DeployTools`) disagree and neither matches a real inventoried host. See `at_have_ryggen_fri/` (the repo's verification harness) for how some of these are now checked automatically going forward. |
| 2026-07-10 | Second correction pass, prompted by Robert planning to physically test this document. The first pass above was thorough but, checked again from scratch against the real files rather than trusting the earlier edits, missed real gaps: §4.4's boot menu list was still describing an old menu (missing Ubuntu/OpenBSD/Spejder entirely, still saying "PhoenixPE" for what the real file's own changelog records as replaced by WinPE at v1.8) — the real `menu.ipxe` is at v2.2 with a **gateway-based dual-datacentre boot-url detection mechanism** (Edinburgh vs a "Fredericia" fallback) not documented anywhere before now, added as new §4.1a. §2.3's "not committed" note was Proxmox-only; widened to a full table of every missing asset directory `menu.ipxe` references, cross-checked against what the PFY's actual plan needs (only Proxmox VE's kernel/initrd, confirmed nothing else required). §6 ("first-boot.sh") was almost entirely rewritten: the real script was substantially trimmed on 2026-07-07 (confirmed via its own changelog) — the interactive site/hostname/IP/gateway prompt, virt-v2v/VirtIO/proxmoxbmc steps, and the node-rename-and-network step are **all gone**, moved into Ansible (`bootstrap-new-node.yml`, `40-scripts.yml`); the whole sample transcript was fictional relative to the current script and has been replaced with one quoted from the real, current output. §7.2 ("late_command.sh") had a step (LVM kernel modules) that the real script's own changelog records as deliberately removed, and was missing several real, current actions (fetching `sites.csv`/`devices.csv`/`begyndelse.json`, the "safety dance" prompt scripts, the same gateway detection as §4.1a). Also moved `bootstrap/web/proxmox/ansible_sshkey.pub` to the web root (matching every real consumer) and marked `Join-DomainAndBootstrap.ps1`/`PostOOBE.cmd` as historical artefacts, not break-glass tools — see the git log around this date for the separate commits. **Lesson for whoever picks this up next:** a "thorough" pass against source-of-truth files is not the same as checking every referenced file's *current* content — several of the errors found this time were real files that had been correctly identified as sources of truth in the first pass, then not fully read. |
| 2026-07-10 | §6 rewritten again, same day as the above but a separate, deliberate change (not a correction of an error): `first-boot.sh` was trimmed a second time, this time by design rather than as dead-code removal — applying the "foot in the door" principle explicitly to the ansible-user step, on top of what 2026-07-07 already did for hostname/rename. The script now does only enough for the `ansible` user to be SSH-reachable (sshd present, user created, SSH key installed, `NOPASSWD` sudoers); everything else (apt repo fix, subscription-nag removal, packages, VMware guest tools, `/etc/.environment` prompt, dynamic MOTD, single-disk ZFS check, kvm-group membership, dotfiles/zsh) moved into `ansible/playbooks/proxmox/playbooks/` (`00-preflight.yml`, `10-packages.yml`, `40-scripts.yml`) or `group_vars/pvenodes/main.yml`, reusing `20-ansible-access.yml`/`playbooks/linux/tools.yml` where they already covered the same ground redundantly. The single-disk ZFS console "type I UNDERSTAND" gate became an explicit `-e pve_acknowledge_single_disk=true` override flag in `00-preflight.yml`, for an auditable non-interactive run instead of a console-only prompt. §6.1 and §6.4 rewritten to match; §6.4's transcript is now ~15 lines instead of ~70. |
| 2026-07-10 | Same day again, prompted by Robert noticing the `/etc/.environment` prompt just added to `00-preflight.yml` above was itself a legacy pattern worth cleaning up: every consumer across the whole estate (`bindme.sh`, `ansibleme.sh`, `firewallme.sh`, firewallme's `00_preflight.yml`, `bind9-dns.yml`, `rudder_server.yml`, and the just-added PVE preflight) only ever used `/etc/.environment` to seed one field — `nodeinfo.json`'s `environment` — which every one of them writes anyway. New shared task `ansible/tasks/nodeinfo_environment.yml` resolves the environment from an already-deployed `nodeinfo.json` if present, prompting only if not; the four Ansible-side duplicates of the old check/prompt/write block (firewallme, bind9, rudder, proxmox) were replaced with a one-line include. Also fixed a real latent bug this surfaced: `linux/tools.yml`'s best-effort `nodeinfo.json` write (runs on every Linux host, including a routine sweep after a role-specific play has already set a real environment) previously had no way to see an existing value and always fell back to `production`, silently clobbering a correctly-set `staging`/`development` marker if it ran after the role-specific play. Initially scoped to the Ansible side only, with the three bash break-glass scripts flagged as a follow-up (different `jq`-availability ordering in each). |
| 2026-07-10 | Follow-up to the above, same day: the three bash break-glass scripts (`bindme.sh`, `ansibleme.sh`, `firewallme.sh`) migrated too. Each now checks its own `nodeinfo.json` first via `jq`, falls back to the legacy `/etc/.environment` file (for hosts already provisioned), then prompts — and no longer writes `/etc/.environment` itself. `bindme.sh` and `ansibleme.sh` already had `jq` installed before their environment block, so no reordering was needed; `firewallme.sh` didn't (its `BOOTSTRAP_PKGS` batch, which includes `jq`, doesn't install until later), so it got a small standalone defensive `jq` install immediately before the check, mirroring `bindme.sh`'s existing pattern for the same reason. `ansible/tasks/nodeinfo_environment.yml` also gained the same legacy-file fallback tier, so an Ansible run against a node that already has `/etc/.environment` but no `nodeinfo.json` yet reuses that value instead of re-prompting. `linux/tools.yml` now deletes `/etc/.environment` once `nodeinfo.json` has captured it (on the success path only — a host that isn't EXA-hostname-conformant yet keeps its file, since `nodeinfo.json` isn't written for it either). |
| 2026-07-20 | Standard IP Convention table's `.15` PRV row replaced with `.19` NAS. `.15` was retired 2026-07-19 (see `README.md`'s Addressing table and `docs/proxmox/proxmox-dcm-pbs-planning.md`) — never real for any ordinary site, provisioning is centralised at VRK/FRD only, whose real `EXAPRVVRK001`/`EXAPRVFRD001` devices are untouched. Missed in the original sweep; caught on a follow-up pass. |
| 2026-07-21 | VRK/FRD's provisioning servers (Type=`TMP` in `devices.csv`, formerly `PRV`) deliberately no longer have a formal `EXA<ROLE><SITE><NNN>` hostname or DNS record at all — Robert: these are bootstrap-only helpers, not real managed nodes, so they shouldn't carry the same identity every real node gets. Every `EXAPRVVRK001`/`EXAPRVFRD001` mention throughout this document replaced with the real IP (`192.168.139.50` / `172.16.124.1`) plus a plain description; the worked shell-prompt transcript's hostname likewise genericised to `provisioning-server`. |
| 2026-07-27 | §2.3's `web/` directory tree and "not committed" table updated for the `debian/` split into `trixie/` (current-stable, fetched via `benarbejde/asset_manifest.json`) and `bookworm/` (3CX's installer kernel, confirmed genuine unmodified Debian and moved here rather than duplicated), plus a new `3cx/` entry (3CX Phone System's own installer, custom initrd + preseed, driving `menu.ipxe`'s new `:3cx-install` entry). Note: this section's older "already present"/"not committed" framing predates several since-completed sessions of `benarbejde/asset_manifest.json` fetch work (Spejder, klargoring, wimboot, OpenBSD, gparted now genuinely committed via git-lfs) and still shows stale detail elsewhere (e.g. OpenBSD `7.5`, `rocky/` vs the real `rockylinux/`) — not corrected in this pass, flagged for a full re-sweep of this table separately. |

---

## Standard IP Convention

Every site follows this addressing scheme within its `/24` subnet.
Exceptions are noted in individual site entries.

| Address       | Role                                                         | Hostname pattern                      |
| ------------- | ------------------------------------------------------------ | ------------------------------------- |
| `.1`          | Upstream router (RTR) — not the firewall, see `.253`/`.254`  | `EXARTR<SITE>001`                     |
| `.2`          | BMC pool slot 1 — DRAC / iLO / Redfish                       | `EXARAC<SITE>001`                     |
| `.3`          | BMC pool slot 2 — or RAC emulator VM on single-PVE-node sites | `EXARAC<SITE>002`                     |
| `.4`          | BMC pool slot 3 — or RAC emulator VM on two-PVE-node sites   | `EXARAC<SITE>003`                     |
| `.5`          | PVE node 1                                                   | `EXAPVE<SITE>001`                     |
| `.6`          | PVE node 2                                                   | `EXAPVE<SITE>002`                     |
| `.7`          | PVE node 3                                                   | `EXAPVE<SITE>003`                     |
| `.10`         | Domain Controller — primary                                  | `EXADCS<SITE>001`                     |
| `.11`         | Domain Controller — secondary                                | `EXADCS<SITE>002`                     |
| `.19`         | Storage — NAS/SAN (e.g. TrueNAS)                             | `EXANAS<SITE>001`                     |
| `.48`         | VOIP SBC — trunks to `EXAPBXCLD001`                          | `EXASBC<SITE>001`                     |
| `.82`–`.94`   | Wireless access points (static, one per WAP; count varies)   | `EXAWAP<SITE>00N`                     |
| `.100`–`.249` | DHCP pool                                                    | —                                     |
| `.250`–`.252` | RT switches                                                  | `EXASWI<SITE>001`–`003`               |
| `.253`        | Firewall — primary (FWL1). **This is the site's actual gateway/internet-facing device, not `.1`.** | `EXAFWL<SITE>001` |
| `.254`        | Firewall — secondary (FWL2)                                  | `EXAFWL<SITE>002`                     |

> **Role codes match `benarbejde/address_policy.json`, the single source of truth this table is derived from — if the two ever disagree, `address_policy.json` is correct and this table needs fixing, not the other way round.**
>
> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM (a training/lab tool — see `docs/lab/rac-emulator.md` — not a real BMC control plane). Physical PVE node BMCs consume from `.2` upward; the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.
>
> ***NB: On three-PVE-node sites the pool is fully consumed by physical BMCs.***

## 1. Prerequisites — Cloud Infrastructure

Before any site node can be bootstrapped, the CLD (cloud) infrastructure must exist. This section documents what was purchased, how it is configured, and what DNS records are required. This is a one-time setup that underpins the entire estate.

### 1.1 OVH Dedicated Server — EXAPVECLD001

A dedicated server was purchased from OVH in their **Pulseant datacentre in Edinburgh**. Edinburgh was chosen deliberately: it is geographically equidistant between Falkirk (head office, FAL) and Glasgow (GLA), keeps the infrastructure within Scotland, and is on separate physical infrastructure from both sites.

| Property | Value |
|---|---|
| Hostname | `EXAPVECLD001` |
| FQDN | `exapvecld001.example.com` |
| Public IP | `192.0.8.86` |
| OS | Proxmox VE 9 |
| Role | Cloud hypervisor — hosts all CLD VMs |

The server runs Proxmox VE directly on bare metal. Its public IP (`192.0.8.86`) is the primary IP assigned by OVH to the host itself. This device has been provisioned via virtual media and an IPVKM within OVH's infrastructure.

*NB: Working with OVH's infrastructure falls outside the scope of this document.*

### 1.2 Additional IP — EXAFWLVRK001 WAN

> **Naming correction (2026-07-10):** this device was originally referred to throughout this section as
> `EXAFWLCLD001`, with a single LAN interface at `192.168.139.253/24`. It has since been split into its
> current, correct form — `EXAFWLVRK001`, with a `192.168.139.0/24`-facing (vRACK) address distinct from
> its `192.168.69.0/24`-facing (CLD LAN) address — see `benarbejde/devices.csv`. The values below reflect
> the current, correct state, not the original one-address model.

OVH allows the purchase of additional IPs that can be assigned to VMs via MAC virtualisation. One additional IP was purchased for the firewall VM:

| Property | Value |
|---|---|
| VM Hostname | `EXAFWLVRK001` |
| FQDN | `exafwlvrk001.example.com` |
| WAN IP (OVH additional IP, real internet uplink) | `192.0.8.131` |
| WAN Gateway | `192.0.8.254` |
| vRACK-facing interface | `192.168.139.69/24` |
| CLD LAN-facing interface | `192.168.69.253/24` |
| Role | Internet-facing firewall/gateway; also the gateway for the `192.168.69.0/24` (CLD) and `192.168.139.0/24` (vRACK) subnets |
| MAC Address | `00:50:00:C0:FF:EE` (OVH will require you ot set the MAC they provide) |

`EXAFWLVRK001` is a VM running on `EXAPVECLD001`. Its WAN interface uses the additional OVH IP (`192.0.8.131`) with a virtual MAC assigned in the OVH control panel — this is required for OVH's network to route the additional IP to the VM rather than the host. Internally it has two further interfaces: `192.168.139.69` (vRACK-facing) and `192.168.69.253` (CLD LAN-facing, the default gateway for CLD's own subnet).

`EXAFWLVRK001` runs **dnsmasq** on its vRACK interface, providing DHCP and iPXE tagging for `192.168.139.0/24`. Authoritative DNS for `jukebox.internal` is **not** handled by the firewall — that's BIND9 on `EXADNSVRK001` (`192.168.139.8`, see §4a below); the firewall's `dns_forwarders` point at it.

**Firewall rules on EXAFWLVRK001:** Inbound access to the provisioning network from site WAN IPs is permitted, but each site is restricted to a `/32` — i.e. the single known public IP of each site (FAL, BRK, ODE, and all other commissioned sites). No wider ranges are permitted inbound.

### 1.3 Temporary Bootstrapping Node — EXASTRPCLD001

> 🇩🇰 **This node does not follow the EXA naming convention. The non-standard name is intentional — it is a deliberate red flag that this machine is temporary and must be decommissioned.**

| Property | Value |
|---|---|
| Hostname | `EXASTRPCLD001` |
| IP | `192.168.139.50` (static) |
| OS | Windows 11 (minimal install) |
| Role | Temporary HTTP provisioning server — serves `web/` |

This is a VM on `EXAPVECLD001`, sitting behind `EXAFWLVRK001` on `192.168.139.0/24`. It runs `static-web-server.exe` serving the `web/` directory tree. It exists purely because it was the fastest way to stand up an HTTP server at the start of the project. You may use `Python3 -m http.server` too

> **Correction (2026-07-10):** the line that originally stood here said this node "must be migrated to
> `EXAANSCLD001` (the Ansible node) once that VM is commissioned." That was wrong even as a plan, not just
> stale — `EXASTRPCLD001` was in fact superseded by a permanent Linux provisioning
> server that keeps the same role (serving `web/` at `192.168.139.50`) and the same IP. `EXAANSCLD001` (the
> Ansible control node) is a separate box entirely, on a different subnet (`192.168.69.0/24`, not
> `192.168.139.0/24`) — see `benarbejde/begyndelse.json`'s `provisioning_edinburgh` and `ansible_control`
> entries, which are two distinct hosts. **`EXASTRPCLD001` was decommissioned once the provisioning server took
> over `192.168.139.50`.** (2026-07-21: that provisioning server has since been given no formal
> hostname of its own either — see §1.5's own note — referenced by IP only from here on.)

### 1.4 Domain Registration and Public DNS

Two domains are registered for the estate:

| Domain | Use |
|---|---|
| `example.com` | Primary public domain — AD forest root is `jukebox.internal` (internal); `example.com` is used for public-facing DNS records |
| `example.net` | Secondary domain — used as a UPN suffix and internal DNS alias zone (see `ExampleMusic_UPN_DNS_dnsmasq_Procedure.md`); not an AD domain in its own right |

The following public DNS records exist:

| Record | Type | Value | Notes |
|---|---|---|---|
| `exapvecld001.example.com` | A | `192.0.8.86` | Proxmox host — web UI, SSH |
| `exafwlvrk001.example.com` | A | `192.0.8.131` | Firewall WAN IP |
| `ansible.jukebox.internal` | A | `192.0.8.131` | Provisioning server name — resolves to EXAFWLVRK001's WAN IP (port-forwarded through to `192.168.139.50`, the provisioning server) |
| `ansible.example.com` | CNAME | `ansible.jukebox.internal` | Alias |
| `www.jukebox.internal` | CNAME | `ansible.jukebox.internal` | Fallback used by `bootstrap.ipxe` |

The `ansible.jukebox.internal` A record is the one that matters for iPXE boot. The embedded `bootstrap.ipxe` script tries hostnames in this order: `ansible.jukebox.internal` → `www.jukebox.internal` → direct IP `192.168.139.50`. The CNAME aliases mean all three resolve correctly as long as public DNS is functioning. **Note:** despite the `ansible.*` name, this DNS record always points at the *provisioning* server (bootstrap-only, no formal hostname or internal DNS record of its own — this `ansible.jukebox.internal` alias is a separate, public-facing DNS name, not the internal `EXA<ROLE><SITE><NNN>` convention), never at the Ansible control node (`EXAANSCLD001`) — the two are separate hosts on separate subnets (see the correction in §1.3). The name predates that distinction and is being kept for compatibility with existing iPXE/preseed configs rather than renamed.

Port forwarding on EXAFWLVRK001 forwards inbound HTTP (port `80/TCP`) on `192.0.8.131` through to `192.168.139.50` (the provisioning server).

### 1.5 Network topology summary

```
Internet
    │
    │  192.0.8.86 (EXAPVECLD001 — Proxmox host, OVH Edinburgh)
    │
    ├─ VM: EXAFWLVRK001
    │       WAN (internet): 192.0.8.131 (OVH additional IP, gw 192.0.8.254)
    │       WAN (vRACK):    192.168.139.69/24
    │       LAN (CLD):      192.168.69.253/24
    │       Runs: dnsmasq (vRACK DHCP/iPXE), firewall, WireGuard hub (CLD spoke)
    │
    ├─ 192.168.139.0/24  (vRACK / provisioning subnet)
    │       │
    │       ├─ 192.168.139.8    EXADNSVRK001 (BIND9 — authoritative for jukebox.internal)
    │       ├─ 192.168.139.50   provisioning HTTP server (bootstrap-only, no formal hostname; was EXASTRPCLD001, decommissioned)
    │       └─ 192.168.139.69   EXAFWLVRK001 (vRACK-facing face of the firewall above)
    │
    └─ 192.168.69.0/24   (CLD LAN)
            │
            ├─ 192.168.69.9     EXAANSCLD001 (Ansible control node)
            ├─ 192.168.69.48    EXAPBXCLD001 (PBX)
            ├─ 192.168.69.253   EXAFWLVRK001 (CLD LAN-facing face of the firewall above)
            └─ ...              Other CLD VMs (EXADCSCLD001, etc.)

Public DNS:
    ansible.jukebox.internal  A      192.0.8.131  ← iPXE boot target
    www.jukebox.internal      CNAME  ansible.jukebox.internal
    ansible.example.com      CNAME  ansible.jukebox.internal
```

---

## Overview

This document covers the full lifecycle of bringing a new site node from bare metal (or bare VM) to a provisioned Proxmox hypervisor ready for workloads. It also covers the Windows workstation side — setting up the provisioning HTTP server on your engineer's laptop — and the KeePassXC credential database structure.

The pipeline is:

```
Internet → ansible.jukebox.internal (192.0.8.131, EXAFWLVRK001)
               └─ port 80 forwarded to 192.168.139.50 (provisioning server, no formal hostname)
                    └─ static-web-server serving web/
                         └─ iPXE boot (embedded bootstrap.ipxe → chains to menu.ipxe)
                              ├─ Proxmox VE auto-install (VRK/FRD-answer.toml / -degraded.toml)
                              │    └─ first-boot.sh (post-install provisioning)
                              └─ Debian auto-install (lvm.seed → late_command.sh)
                                   └─ Windows VM: PostOOBE.cmd → Join-DomainAndBootstrap.ps1
```

---

## 2. Engineer Workstation Setup

### 2.1 Required software

You need the following on your Windows/Mac/Linux machine before starting.

**Remote access / SSH:**

| Tool | Purpose |
|---|---|
| PuTTY / KiTTY / OpenSSH | SSH client (Windows / MacOS / Linux) |
| Hyper / iTerm2 / gnome-terminal | Terminal (Windows / macOS / Linux) |
| WinSCP / OpenSSH | SFTP file transfer (Windows / MaCOS / Linux) |
| Pageant / ssh-agent | SSH agent for key management |
| Typora / MarkText | Markdown Viewer (Windows / MacOS / Linux) |
| vim / notepad.exe / notepad++ / sublime / edit.exe | Text Editor (pick your favourite - ***(not nano, it corrupts files!)*** |
| ipcalc / ipcalc.ps1 (in this repo) | IP/Subnet calculator |
| Virt-viewer | https://gitlab.com/virt-viewer/virt-viewer/-/releases/ (Mac/Windows/Linux) |
| Spice guest tools (in addition to virtIO drivers) | https://www.spice-space.org/download/windows/spice-guest-tools/spice-guest-tools-latest.exe |

**Core utilities:**

| Tool | Purpose |
|---|---|
| python3 | `python3 -m http.server` fallback HTTP server |
| python3-proxmoxer | Proxmox API library (used by management scripts) |
| KeePassXC | Credential database (see §2) |

All of the above are available via Chocolatey on Windows (installed automatically by `Join-DomainAndBootstrap.ps1` on managed machines). For an engineer's unmanaged laptop, install manually.

### 2.2 Setting up the HTTP server

The provisioning pipeline is driven by an HTTP server serving the `web/` directory tree. In production this runs permanently on the Edinburgh provisioning server (`192.168.139.50`, bootstrap-only, no formal hostname). For field use from a laptop, use `static-web-server.exe`:

```powershell
PS> .\static-web-server.exe -d web\ -g info -a 192.168.139.50 --directory-listing
```

Replace `192.168.139.50` with the IP address of the interface facing the target network. The `-g info` flag enables request logging to the console. If you have Powershell 7.0 available, this will give you a nice colourful output:

```powershell
.\static-web-server-x64.exe -d web/ -g info -a 192.168.139.50 --directory-listing 2>&1 | Tee-Object -FilePath server.log | ForEach-Object {
  if ($_ -match '^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\.\d+Z(.*)$') {
    Write-Host "`e[38;5;166m$($matches[1]) `e[0m" -NoNewline
    Write-Host "`e[38;5;33m$($matches[2])`e[0m" -NoNewline
    $rest = ($matches[3] -replace 'static_web_server::', '') -replace '^\s{2}', ' '
    if ($rest -match '::server:')     { Write-Host $rest -ForegroundColor Magenta }
    elseif ($rest -match '\sERROR\s') { Write-Host $rest -ForegroundColor Red }
    elseif ($rest -match '\sWARN\s')  { Write-Host $rest -ForegroundColor Yellow }
    elseif ($rest -match '\sINFO\s')  { Write-Host $rest -ForegroundColor Cyan }
    else                              { Write-Host $rest }
  } else { Write-Host $_ }
}
```



Alternatively, if `static-web-server.exe` is not available:

```bash
## Linux / macOS
python3 -m http.server 80 --bind 192.168.139.50 -d web/
```

If you would like osmething a little bit more snazzy:

```
## sudo is mandatory for prots < 1024 this avoids breaking scripts, infra, etc. Alternativelly, using 8080 upstream removes this requirement for the security concious perosn.

sudo python3 -m http.server 80 --bind 127.0.0.1 -d web/ | while IFS= read -r line; do ;
  ts=$(echo "$line" | grep -oP '\[\K[^\]]+')
  if echo "$line" | grep -qP '" [45]\d{2} '; then ; echo -e "\e[38;5;160m${line}\e[0m"
  elif echo "$line" | grep -qP '" 3\d{2} ' ; then ; echo -e "\e[38;5;136m${line}\e[0m"
  elif echo "$line" | grep -qP '" 2\d{2} ' ; then ; echo -e "\e[38;5;64m${line}\e[0m"
  else ; echo -e "\e[38;5;37m${line}\e[0m" ; fi ; done
```

> **Note:** Python's `http.server` is single-threaded and will stall if a client disconnects mid-transfer. For iPXE kernel/initrd loads (which are large) prefer `static-web-server`.

### 2.3 The `web/` directory tree

> **Correction (2026-07-10):** the structure and `mkdir` commands that used to stand here (`web/proxmox/boot/`,
> `web/gparted/`, `web/phoenixpe/`, `web/autodeploy/`, plus `qemu-ga-x86_64.msi`/`virtio-win-gt-x64.msi` at the
> `web/` root) do not match this repo — none of those paths or files exist anywhere in `bootstrap/web/`, and
> there's no evidence they were ever built out beyond this document. Replaced below with the real, current
> layout (`bootstrap/web/`, confirmed against the actual tree, not reconstructed from memory).

This structure ships in the repo already — you don't need to build it from scratch, only add the large
binary assets (installer kernels/initrds, ISOs) that aren't committed (see the note at the end of this
section for why).

```cmd
bootstrap/web/
├── bootstrap.ipxe               ← embedded iPXE boot script — see §4.3
├── menu.ipxe                    ← main iPXE boot menu, chained to from bootstrap.ipxe
├── boot.ipxe, lvm.seed          ← STALE/superseded pre-rename leftovers (not part of the real
│                                    boot chain — see each file's own 2026-07-11 note); the real
│                                    preseeds are debian/lvm-bios.seed and debian/lvm-efi.seed
├── ipxe.lkrn, ipxeaa64_arch.efi ← prebuilt iPXE binaries
├── ansible_sshkey.pub           ← Ansible user public key — served from the web root; every
│                                    consumer (first-boot.sh, late_command.sh, docs) fetches it
│                                    from here, not from proxmox/ — moved here 2026-07-10 to
│                                    match, rather than fixing every fetch path individually
│
├── debian/
│   ├── late_command.sh          ← Debian post-install hook
│   ├── lvm.seed / lvm-bios.seed / lvm-efi.seed
│   ├── trixie/x86_64/linux, trixie/x86_64/initrd.gz  ← Debian netboot kernel+initrd (AMD64),
│   │                                current stable — fetched via benarbejde/asset_manifest.json
│   ├── trixie/arm64/linux, trixie/arm64/initrd.gz    ← same, ARM64
│   └── bookworm/x86_64/linux    ← NOT fetched — this is 3CX's own installer kernel (see 3cx/
│                                    below), confirmed byte-identical to genuine Debian 12
│                                    (Bookworm) 2026-07-27 and moved here rather than duplicated.
│                                    No initrd here: 3CX's initrd.gz is a custom build, stays in
│                                    3cx/ (see below). Split into trixie/+bookworm/ subfolders
│                                    2026-07-27 to keep the two releases apart now that a second
│                                    one exists.
│
├── 3cx/
│   ├── boot.txt                 ← 3CX's own vendor netboot recipe (isolinux APPEND syntax) —
│   │                                translated into menu.ipxe's :3cx-install entry, not run
│   │                                directly
│   ├── preseed_*.txt            ← 3CX's vendor preseed, unmodified; menu.ipxe's url= points at
│   │                                this local copy rather than 3CX's downloads-global.3cx.com
│   ├── post-install_*.txt       ← local copy of the post-install script the preseed's own
│   │                                late_command still fetches live from 3CX during install
│   │                                (unmodified vendor content, outside iPXE's control)
│   ├── initrd.gz                ← 3CX's custom installer initrd (confirmed NOT stock Debian)
│   └── 3cx_key.pub, 3CXPhoneSystem20.exe, 3cx.sh  ← supplied by Robert alongside the above,
│                                    not part of the netboot chain itself
│
├── proxmox/
│   ├── select-pve-answer.sh      ← run at the installer's own root shell (BusyBox ash) after
│   │                                mounting a plain Proxmox ISO via iLO/iDRAC/BMC virtual media
│   │                                — detects site from the default gateway, offers answer/
│   │                                degraded, fetches the matching *-answer.toml. No PXE menu
│   │                                entry drives Proxmox install any more; see §4.5/§6.3.
│   ├── VRK-answer.toml, FRD-answer.toml     ← PVE auto-install: ZFS RAID-1 (2 disks), one per site
│   ├── VRK-degraded.toml, FRD-degraded.toml ← PVE auto-install: ZFS RAID-0 (1 disk, degraded), one per site
│   ├── first-boot.sh            ← PVE post-install provisioning script, chained via each
│   │                                answer.toml's own [first-boot] block
│   ├── post-pve-install.sh, create-vm.py, convert-v2v.py, manage-pool.py, pve-bootorder.py, ...
│   ├── sites.csv, devices.csv, address_policy.json, begyndelse.json, ad_forest.json
│   │   ← synced copies of benarbejde/*, kept in sync by .githooks/pre-commit — edit the
│   │     benarbejde/ originals, never these
│
├── windows/
│   ├── unattend/headlessunattend.xml    ← the one real unattend XML (see the Windows section) --
│   │                                        does NOT install Salt (see §8.3's note on why not)
│   ├── Salt-Minion-Setup.msi            ← committed to git 2026-07-20 (AMD64, 3008.2,
│   │                                        checksum-verified). NOT part of this Setup-time
│   │                                        flow -- pushed later by ansible/playbooks/
│   │                                        windows_bootstrap/playbooks/82-salt-minion.yml,
│   │                                        over SSH, well after this file's own chain
│   │                                        completes. See docs/buildsheets/
│   │                                        buildsheet-salt-minion.md. ARM64 does not exist
│   │                                        for Windows Salt minions (confirmed against the
│   │                                        real package repo) -- AMD64/x86 only
│   ├── PostOOBE.cmd, SetupComplete.cmd, Install-OpenSSH.ps1, Deploy-OpenSSH.cmd
│   └── Join-DomainAndBootstrap.ps1      ← legacy; see the Windows section for current status
│
├── provision/
│   └── ansibleme.sh, bindme.sh, firewallme.sh, rudderme.sh   ← break-glass bootstrap scripts
│
├── arch/x86_64/          ← Arch Linux netboot assets
└── rocky/                ← Rocky Linux netboot assets
```

**Not committed to this repo** (installer kernels/initrds and full ISOs — hundreds of MB to
multiple GB each, deliberately kept out of git). Confirmed 2026-07-10 by checking the real tree
directly, not assumed — **none of the following directories exist yet**, even though `menu.ipxe`
references every one of them:

| Menu entry | Expected directory | Needed for the PFY's plan (PVE/Ansible/DNS/FWL/Windows)? |
|---|---|---|
| Debian | `debian/trixie/x86_64/`, `debian/trixie/arm64/` | Already present — nothing to add |
| 3CX Phone System | `3cx/` (installer initrd + preseed), kernel shared with `debian/bookworm/x86_64/` | Already present — nothing to add |
| Arch Linux | `arch/x86_64/` | Already present — nothing to add |
| GParted | `gparted/${arch}/` | No |
| WinPE (x86_64/ARM64) | `winpe/x86_64/`, `winpe/arm64/` | No — Windows Server 2022 uses the unattend-XML path (§7), not this WinPE menu entry |
| Ubuntu | `alpine/`, `ubuntu/` (Alpine dd-writer pattern — see the file's own header comment) | No |
| Rocky Linux | `rockylinux/${arch}/` | No |
| OpenBSD | `openbsd/7.5/${arch}/` | No |
| Hardware Detection Tool | `hdt/` | No |
| Spejder | `spejder/${arch}/` | No (separate external tool, see above) |
| Auto-deploy | `autodeploy/` (optional — chain fails silently if absent) | No, unless you specifically want zero-touch MAC-based deploy |

For the PFY's plan specifically: nothing above needs adding for Proxmox VE — it's no longer PXE-served
at all (see §4.5/§6.3). Debian and Arch are already there. The only thing still needed for a real PVE
install is a genuine, untampered Proxmox VE ISO, mounted via iLO/iDRAC/BMC virtual media — if you don't
have a copy already, ask whoever owns this repo — do not guess a source and download a potentially
tampered installer image.

**Separately, `bootstrap/web/rocky/install.ks` appears to be dead** — an Anaconda-kickstart-based
Rocky install approach, referenced from nowhere else in the repo, and superseded by the "custom
installer initrd" approach `menu.ipxe`'s own Rocky section comments describe (which expects
`rockylinux/`, a different, not-yet-populated directory). Not touched here — Rocky isn't part of the
PFY's plan — but flagged since it's confusing to find two different, seemingly-competing Rocky
approaches if you go looking.

---

## 3. KeePassXC Credential Database

Create a KeePassXC database (`.kdbx`) at the start of each estate deployment. Keep it on an encrypted volume or in a secure location — it will hold every password generated during provisioning. Make judicious use of folders and subfolders, e.g `FAL, BRK, ODE`. 

***NB: `kpcli` is the command line binary for those with an interest in such matters.***

### 3.1 Database structure

Organise entries into groups as follows:

```cmd
Example Music.kdbx
├── Infrastructure
├──── CLD
│   ├── Provisioning server (192.168.139.50) — root (bootstrap-only, no formal hostname; was EXASTRPCLD001, decommissioned)
│   ├── PVE root password (answer.toml hash source)
│   └── Ansible user password (per-node if not key-only)
│
├── Active Directory
│   └── JUKEBOX\Administrator (forest DA — the only AD credential; there are no per-domain
│       DA accounts, because example.net/example.org/example.com are not real, joinable AD
│       domains — see §1.4. Resolved 2026-07-11, confirmed with Robert: every host joins
│       `jukebox.internal` and only `jukebox.internal`; the example.* names are UPN suffixes
│       and DNS aliases only. Join-DomainAndBootstrap.ps1's `$AllowedDomains` still lists
│       them as selectable join targets — that script is a documented HISTORICAL ARTEFACT
│       (see its own header) deliberately not kept in sync with current live behaviour, not
│       a live inconsistency to chase.)
│
├── Network
│   ├── WireGuard pre-shared keys (per peer)
│   └── IPMI / BMC passwords (per server, see §6)
│
├── Services
│   ├── Proxmox API tokens (per script/user)
│   └── Any third-party service credentials
│
├── Site Credentials
│   ├── ABD (Aberdeen, UK)
│   ├── AMS (Amsterdam, NL)
│   ├── BON (Bonn, W. Germany)
│   ├── <etc>
│   └── TOR (Toronto, CA)
│
└── Bootstrap
    ├── iPXE SSH console password (network-console/password — default: install)
    └── Preseed ansible user password (if not locked to key-only)
```

### 3.2 Generating the PVE root password hash

All four TOML files (`VRK-answer.toml`, `FRD-answer.toml`, `VRK-degraded.toml`, `FRD-degraded.toml`)
contain a pre-hashed root password — the same hash in all four, so update all four together if it's
ever rotated. To generate a new one:

```bash
# On any Linux system with openssl or mkpasswd. The example files use Password1! which is obviously for exmaple purposes only!
openssl passwd -6 'YourPasswordHere'
# or
mkpasswd -m sha-512 'YourPasswordHere'
```

Paste the resulting `$6$...` string into both TOML files at `root-password-hashed`. Store the plaintext in KeePassXC under **Infrastructure → PVE root password**.

---

## 4. iPXE Boot Infrastructure

### 4.1 How it fits together

There are two iPXE script files, and they solve two different problems —
**do not conflate them**, they were checked separately on 2026-07-10 and
both are accurate as documented, but for different reasons:

| File | Role |
|---|---|
| `bootstrap.ipxe` | **Embedded** into the compiled iPXE ISO/USB/ROM. Runs before any network is configured. Does DHCP, then locates `menu.ipxe` via a DNS-name fallback chain (§4.3), with a gateway-detected direct-IP address as the last-resort step if DNS fails entirely — this only has to get you to a working `menu.ipxe`, once, from a cold boot with no other context. |
| `menu.ipxe` | **Remote** boot menu, fetched by `bootstrap.ipxe`. Served by the HTTP server at `bootstrap/web/menu.ipxe`. Once it's running, it does its **own, separate** gateway-based environment detection (§4.1a) to pick which datacentre to fetch every subsequent OS installer file from — `bootstrap.ipxe`'s DNS chain is not involved again after this point. |

> **Correction (2026-07-11):** `bootstrap.ipxe` previously had no gateway-based detection at all —
> its direct-IP last resort was a single hardcoded Edinburgh value (`192.168.139.50`), even though
> DHCP (and therefore `${net0/gateway}`) has already succeeded by the point that fallback is reached.
> It now runs the same `iseq ${net0/gateway} ...` check `menu.ipxe` uses (§4.1a) to set `boot-ip`
> correctly for whichever datacentre it's actually on, before falling through to the DNS chain. This
> only changes the *last-resort, DNS-down* case — the DNS chain (`ansible.jukebox.internal` →
> `www.jukebox.internal`) is still tried first and is unaffected.

The flow is: BIOS/UEFI boots iPXE ISO → `bootstrap.ipxe` runs → DHCP →
locates and fetches `menu.ipxe` (DNS chain) → `menu.ipxe` detects which
datacentre it's on (gateway IP) → operator selects an OS from the menu →
every kernel/initrd/seed fetch from that point on uses the datacentre
`menu.ipxe` detected, not anything `bootstrap.ipxe` decided.

#### 4.1a Gateway-based datacentre detection (inside `menu.ipxe`)

`menu.ipxe` (not `bootstrap.ipxe`) sets a `${boot-url}` variable once, near
the top of the file, by checking the DHCP-assigned gateway IP — every
kernel/initrd/seed URL for every menu entry below uses `${boot-url}`
exclusively, never a hardcoded IP:

| Gateway seen | Environment | `${boot-url}` |
|---|---|---|
| `192.168.139.254` | Edinburgh — `192.168.139.50` (bootstrap-only, no formal hostname) | `http://192.168.139.50` |
| `172.16.124.2` | Fredericia — `172.16.124.1` (see the file's own comment: *"Legal fiction — physically a MacBook running `python3 -m http.server 8000`, mirroring `/debian` from Edinburgh. Only the IP differs."*) | `http://172.16.124.1:8000` |
| anything else | falls back to Edinburgh with a warning | `http://192.168.139.50` |

This matters for testing on an unfamiliar network segment: if the gateway
doesn't match either known value, you silently get Edinburgh's `boot-url`
regardless of whether that host is actually reachable from where you are
— the menu still renders, but every install attempt will time out fetching
its kernel/initrd. Watch for `Environment: <name>` in the iPXE console
output right after DHCP completes; if it says "not recognised — defaulting
to Edinburgh" and you're not actually on the Edinburgh network, that's
your failure mode before you've picked anything from the menu.

### 4.2 The `menu.ipxe` filename and URL mapping

> **Correction (2026-07-10):** this section previously claimed the menu file is stored on disk as a hidden
> dotfile (`web/.ipxe`) and discussed working around web servers that refuse to serve dotfiles. That was
> never accurate — the real file is `bootstrap/web/menu.ipxe`, a perfectly normal, non-hidden filename. No
> dotfile has ever existed in this repo; there was nothing to work around.

The menu file is stored on disk as `bootstrap/web/menu.ipxe`. The HTTP server serves it at the path configured in `bootstrap.ipxe`:

```
set boot-path  /menu.ipxe
```

### 4.3 Embedded bootstrap (`bootstrap.ipxe`)

This script is compiled into the iPXE binary. Key configuration at the top:

```ipxe
set boot-domain   jukebox.internal
set boot-ansible  ansible.${boot-domain}
set boot-www      www.${boot-domain}
set boot-ip       192.168.139.50          ← placeholder only, see below
set boot-path     /menu.ipxe
```

`boot-ip`'s value here is a placeholder — DHCP hasn't run yet at this point in the script, so
`${net0/gateway}` isn't known. Immediately after `ifconf` succeeds (gateway now known), the script
re-sets `boot-ip` for real using the same gateway check `menu.ipxe` uses (§4.1a):

```ipxe
iseq ${net0/gateway} 172.16.124.2 && set boot-ip 172.16.124.1:8000 || set boot-ip 192.168.139.50
```

**Boot server resolution order:** The script tries three methods in sequence, falling back if each fails:

1. `ansible.jukebox.internal` (DNS lookup first — skips the chain timeout if DNS is broken)
2. `www.jukebox.internal`
3. Direct IP: `${boot-ip}` — now gateway-detected (`192.168.139.50` for Edinburgh/VRK,
   `172.16.124.1:8000` for Fredericia/FRD), not hardcoded to Edinburgh regardless of location

If all three fail, the script drops to an iPXE shell with diagnostic instructions printed on screen.

**Ctrl-B shell escape:** There is a 5-second window at startup to press Ctrl-B and drop to an interactive iPXE shell. This is useful for diagnosing DHCP or DNS issues on a new network.

**Compiling the iPXE binary** (run on a Linux build host):

```bash
┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap]
└──╼ git clone https://github.com/ipxe/ipxe.git

┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap]
└──╼cd ipxe/src

┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ cat bootstrap.ipxe
#!ipxe
################################################
## Example Music — iPXE embedded bootstrap
## This script is embedded into the iPXE binary.
## It kicks off DHCP, then chains to the full
## boot menu served by the Ansible node.
##
## Embed into ISO with:
##   make bin/ipxe.iso EMBED=bootstrap.ipxe
## or for a USB image:
##   make bin/ipxe.usb EMBED=bootstrap.ipxe
## or for a PXE ROM:
##   make bin/undionly.kpxe EMBED=bootstrap.ipxe
################################################

## ------------------------------------------------------------
## Boot server configuration: update these as needed
## ------------------------------------------------------------
set boot-domain   jukebox.internal
set boot-ansible  ansible.${boot-domain}
set boot-www      www.${boot-domain}
set boot-ip       192.168.139.50
set boot-path     /menu.ipxe

echo
echo ============================================================
echo   Example Music Infrastructure: iPXE Boot
echo ============================================================
echo

## ------------------------------------------------------------
## Ctrl-B shell escape — 5 second window
## If the prompt times out, execution falls through to DHCP.
## ------------------------------------------------------------
prompt --key 0x02 --timeout 5000 Press Ctrl-B for iPXE shell... && shell ||

## ------------------------------------------------------------
## DHCP — try all interfaces
## ifconf attempts DHCP on every available NIC.
## To pin to a specific interface replace with: dhcp net0
## ------------------------------------------------------------
echo
echo Requesting DHCP lease...
ifconf --timeout 15000 || goto dhcp_failed
echo Got address: ${net0/ip}
echo Gateway:     ${net0/gateway}
echo
goto fetch_menu

:dhcp_failed
echo
echo DHCP failed on all interfaces.
echo Dropping to shell — check cabling and DHCP server.
echo
shell
goto end

## ------------------------------------------------------------
## Fetch remote boot menu
## Try ansible → www → direct IP, using nslookup first
## to skip the chain timeout if DNS is broken
## ------------------------------------------------------------
:fetch_menu
echo Attempting to locate boot server...
echo

## Step 1 — try ansible.jukebox.internal
nslookup ${boot-ansible} && goto try_ansible || goto try_www

:try_ansible
echo Trying ${boot-ansible}...
chain --timeout 30000 http://${boot-ansible}${boot-path} && goto end || goto try_www

## Step 2 — try www.jukebox.internal
:try_www
echo ${boot-ansible} unreachable, trying ${boot-www}...
nslookup ${boot-www} && goto do_www || goto try_ip

:do_www
echo Trying ${boot-www}...
chain --timeout 30000 http://${boot-www}${boot-path} && goto end || goto try_ip

## Step 3 — try direct IP
:try_ip
echo DNS failed, trying ${boot-ip} directly...
chain --timeout 30000 http://${boot-ip}${boot-path} && goto end || goto fetch_failed

## ------------------------------------------------------------
## All methods failed
## ------------------------------------------------------------
:fetch_failed
echo
echo *** Could not reach boot server by any method ***
echo
echo Tried:
echo   1. http://${boot-ansible}${boot-path}
echo   2. http://${boot-www}${boot-path}
echo   3. http://${boot-ip}${boot-path}
echo
echo Possible causes:
echo   - No network / DHCP lease lost
echo   - DNS not resolving ${boot-domain}
echo   - HTTP server not running on boot server
echo
echo Useful recovery commands:
echo   dhcp net0                              -- retry DHCP
echo   nslookup ${boot-ansible}               -- test DNS
echo   chain http://${boot-ip}${boot-path}    -- retry by IP
echo
shell

:end

## Enable BOTH serial console (115,200 8N1 and VGA at the same time)
┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ cat config/local/console.h
#define CONSOLE_PCBIOS    /* VGA — interactive TUI */
#define CONSOLE_SERIAL    /* COM1, 115200 8n1 — for FWL/RTR/SBC VMs */

## Enable colours and extra functions
┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ cat config/local/general.h
#define CONSOLE_FRAMEBUFFER
#define PING_CMD
#define IPSTAT_CMD
#define REBOOT_CMD
#define POWEROFF_CMD
#define NSLOOKUP_CMD
#define ROUTE_CMD

┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ make bin/ipxe.iso EMBED=bootstrap.ipxe

## This is the iso you boot devices with
┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ copy bin/ipxe.iso ./ipxe.iso

## copy lkrn module too if that's what oyu want as a bootfile. It's 6 and 2x3
┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ copy bin/ipxe.lkrn.iso ./ipxe.lkrn

# ISO (for CD/CDROM/IPMI virtual media):
┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ make bin/ipxe.iso EMBED=bootstrap.ipxe

# USB image:
┌─[ansible@provisioning-server]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ make bin/ipxe.usb EMBED=bootstrap.ipxe

# PXE ROM (for DHCP/TFTP environments):
make bin/undionly.kpxe EMBED=bootstrap.ipxe
```

Pre-built binaries for common configurations are in `x86_64/ipxe.iso` and `arm64/ipxe.iso` in the repository.

### 4.4 Boot menu (`menu.ipxe`)

> **Correction (2026-07-10):** the entry list below was significantly out of date — missing
> Ubuntu and OpenBSD entirely, missing the "Spejder" entry, and still listing "PhoenixPE
> Environment" for what the real file's own changelog records as replaced back at v1.8
> ("Replace PhoenixPE entry with lean custom WinPE build"). The real file is at v2.2 as of
> this correction — quoted directly from `bootstrap/web/menu.ipxe`, not reconstructed.

The remote boot menu offers the following entries (grouped exactly as the real menu groups them):

```
-- Default Selection --
  Boot local disk  (default, 30s timeout)
  Spejder Hardware Provisioning Runtime (Console and Serial ttyS0/COM1)

-- Debian --
  Debian  Auto install
  Debian  Auto install  (SSH console)
  Debian  Auto install  (ttyS0 serial)
  Debian  Auto install  (SSH + ttyS0 serial)
  Debian  [TEST] seed file relocation fix -- try this first

-- Ubuntu --
  Ubuntu  Auto install
  Ubuntu  Auto install  (ttyS0 serial)
  Ubuntu  Auto install  (SSH + ttyS0 serial)

-- Rocky Linux --
  Rocky   Auto install
  Rocky   Auto install  (SSH console)
  Rocky   Auto install  (ttyS0 serial)
  Rocky   Auto install  (SSH + ttyS0 serial)

-- Arch Linux --
  Arch    Auto install
  Arch    Install  (SSH console)
  Arch    Auto install  (ttyS0 serial)
  Arch    Install  (SSH + ttyS0 serial)

-- OpenBSD --
  OpenBSD 7.5  Auto install
  OpenBSD 7.5  Auto install  (ttyS0 serial)
  OpenBSD 7.5  Interactive   (ttyS0 serial)

-- Hypervisors --
  Proxmox VE 9   (x86_64 only)
  Proxmox DCM 9  (x86_64 only)             ← not yet configured, returns to menu

-- Utilities --
  GParted Live
  WinPE deployment environment  (x86_64)
  WinPE deployment environment  (ARM64)
  Hardware Detection Tool  (x86_64 only)

-- System --
  iPXE shell / Reboot / Shutdown
```

**"Spejder Hardware Provisioning Runtime"** is a separate, external tool
(`github.com/knightmare2600/Spejder` — see the root `README.md`'s
"related projects" table), not documented in this repo beyond its menu
entry existing. It's a minimal, stateless, multi-architecture hardware
inventory/provisioning runtime — worth knowing it's there and selectable
from this menu, but its own repo is the source of truth for what it does.

The default selection is **Boot local disk**, with a 30-second timeout. This means a machine that accidentally PXE-boots will fall through to its local OS without intervention.

**MAC-based auto-deploy:** Before showing the menu, the script attempts to chain to `${boot-url}/autodeploy/<mac-address>.ipxe` (`${boot-url}` per the gateway detection in §4.1a — so this is datacentre-relative, not a hardcoded IP). If a file exists for that MAC, it runs instead of the menu, enabling fully automated zero-touch deployment. If the file does not exist, the chain fails silently and the menu appears. Create per-MAC scripts using the hyphenated MAC format (e.g. `aa-bb-cc-dd-ee-ff.ipxe`), under `bootstrap/web/autodeploy/` for Edinburgh (not committed to git — create it yourself if you need per-MAC entries; it's optional, the chain simply fails silently without it).

**Serial console variants:** entries suffixed `(ttyS0 serial)`/`(SSH + ttyS0 serial)` add `console=ttyS0,115200n8` (and `console=tty0` where both consoles need to stay active). Use these for headless servers accessed via IPMI serial-over-LAN.

**The Debian menu currently has 5 entries, not 4** — `debian-test` was added 2026-07-08 as a deliberately separate, clearly-labelled entry after a real bug was found and fixed (the preseed files `lvm-bios.seed`/`lvm-efi.seed` had never actually been copied to the served location, so the four pre-existing Debian entries would have 404'd on `${seed}` if anyone had actually used them). Per the file's own comment, try `debian-test` first to confirm the fix holds before trusting the other four.

### 4.5 Proxmox VE boot entry

> **PXE does not install Proxmox VE at all any more (since v2.5, 2026-07-18).** The kernel/initrd
> auto-install approach shown in earlier revisions of this section was tried and abandoned — see
> `docs/proxmox/pxe-proxmox-autoinstall-build-log.md` for the full history. The real, current
> `:proxmox-ve` menu entry is a stub that tells the operator to mount a plain Proxmox ISO via
> iLO/iDRAC/BMC virtual media instead, then run `select-pve-answer.sh` at the installer's own root
> shell — see §6.3 for that full flow, which is the actual current procedure.

```ipxe
:proxmox-ve
echo Proxmox VE is not built via PXE -- mount a plain Proxmox ISO via iLO/BMC
echo virtual media instead, then run select-pve-answer.sh at the installer's
echo root shell. See docs/proxmox/pxe-proxmox-autoinstall-build-log.md.
prompt Press any key to return to menu...
goto main
```


### Build ARM64 iPXE ISO for VMware Fusion (Apple Silicon)

This procedure documents how to:

 1. Install necessary ARM64 cross-compilation tools
 2. Build an ARM64 iPXE binary with an embedded menu
 3. Prepare a UEFI ISO tree
 4. Produce a bootable ARM64 ISO
 5. Notes for booting in VMware Fusion or UTM

#### Step 1: Install ARM64 cross-compiler and ISO tools

Required packages:

- `gcc-aarch64-linux-gnu` : ARM64 cross-compiler
- `binutils-aarch64-linux-gnu` : ARM64 linker, objcopy, etc.
- `xorriso` : create ISO images

```bash
sudo apt update
sudo apt install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu xorriso
```

#### Step 2: Build ARM64 iPXE binary

Uses the cross-compiler to produce UEFI EFI binary.
EMBED=bootstrap.ipxe embeds your custom menu/script.

```bash
make CROSS_COMPILE=aarch64-linux-gnu- bin-arm64-efi/ipxe.efi EMBED=bootstrap.ipxe

[BUILD] bin-arm64-efi/__divdi3.o
[AR] bin-arm64-efi/blib.a
[HOSTCC] util/elf2efi64
[LD] bin-arm64-efi/ipxe.efi.tmp
[FINISH] bin-arm64-efi/ipxe.efi
```

#### Step 3: Prepare ISO directory structure for UEFI

UEFI boot for ARM64 requires BOOTAA64.EFI

```
mkdir -p iso/EFI/BOOT
cp bin-arm64-efi/ipxe.efi iso/EFI/BOOT/BOOTAA64.EFI
```

#### Step 4: Create bootable ARM64 UEFI ISO


xorriso options:
 -volid : ISO label
 -eltorito-alt-boot : enable alternative boot image
 -e : path to EFI boot file
 -no-emul-boot : EFI does not need floppy emulation
 -isohybrid-gpt-basdat : hybrid ISO with GPT support

```
xorriso -as mkisofs -o ipxe-arm64.iso -volid "IPXE_ARM64" -eltorito-alt-boot -e EFI/BOOT/BOOTAA64.EFI -no-emul-boot -isohybrid-gpt-basdat iso/
```

Output (success):

```
Added to ISO image: directory '/'='iso'
ISO image produced: 761 sectors
Written to medium successfully
Resulting file: ipxe-arm64.iso
```

#### Step 5: Verify ISO exists

```
ls -lh ipxe-arm64.iso
```

#### Step 6: Notes for booting

- Works on VMware Fusion or UTM on Apple Silicon (M1/M2/M4)
- iPXE menu automatically detects architecture:
  iseq ${buildarch} arm64 && set arch arm64 || set arch x86_64
 - Non-ARM systems default to x86_64
 - ISO is UEFI-only; no legacy BIOS support
 - Use the ISO as a CD-ROM in a VM to boot into your custom iPXE menu

---

## 5. Proxmox VE Auto-Install

### 5.1 VRK-answer.toml / FRD-answer.toml — normal install (ZFS RAID-1)

Use this when both disks are present.

> **Site-prefixed files (fixed 2026-07-11).** There is no bare `answer.toml` any more — each
> provisioning server has its own file (`VRK-answer.toml` for Edinburgh, `FRD-answer.toml` for
> Fredericia Havn), each with its own correct `[first-boot] url`. `menu.ipxe`'s gateway detection
> sets `${site-prefix}` (`VRK`/`FRD`) alongside `${boot-url}` and requests
> `${boot-url}/proxmox/${site-prefix}-answer.toml` (§4.5) — so whichever server actually answers
> the request, it serves its own correctly-pinned file. TOML itself still can't do conditionals
> (that constraint hasn't changed — see the note below), but the file split means there's no
> longer a single file that's only correct for one site; there are two files, each correct for
> its own site, and the iPXE layer picks the right one. This replaces the previous design, where
> a single `answer.toml` was permanently pinned to Edinburgh and using it from Fredericia would
> have silently pointed a fresh node's `first-boot.sh` fetch at the wrong datacentre.

`VRK-answer.toml` (Edinburgh):

```toml
[global]
keyboard = "en-gb"
country = "gb"
fqdn = "pve-install.jukebox.internal"
mailto = "root@jukebox.internal"
timezone = "Europe/London"
root-password-hashed = "$6$..."        ← see §2.2
root-ssh-keys = ["ssh-... ansible@exaanscld001.example.com"]  ← see note below

[network]
source = "from-dhcp"

[disk-setup]
filesystem = "zfs"
zfs.raid = "raid1"
disk-list = ["sda", "sdb"]

[first-boot]
source = "from-url"
ordering = "fully-up"
url = "http://192.168.139.50/proxmox/first-boot.sh"
```

`FRD-answer.toml` (Fredericia Havn) is identical except for the `[first-boot] url`:

```toml
url = "http://172.16.124.1:8000/proxmox/first-boot.sh"
```

The `fqdn` here is a placeholder used during install only. `first-boot.sh` will rename the node to its real hostname.

> **`root-ssh-keys` (added 2026-07-10) — the earliest possible foot-in-the-door.** Confirmed against
> Proxmox's own automated-installer schema (`[global] root-ssh-keys` — "SSH public keys to add to the
> `authorized_keys` file of the `root` user after the installation"): root is SSH-reachable by key the
> *moment install finishes*, before `first-boot.sh` has even run. **This does not replace anything** —
> Ansible's whole estate connects as the `ansible` user, not root (`ansible.cfg`'s `remote_user`), so
> `first-boot.sh` still creates that user and its own key as before. `root-ssh-keys` is purely an earlier
> / recovery path, useful if you need to poke at a node before `first-boot.sh` completes. Same key as
> `bootstrap/web/ansible_sshkey.pub` — if that key is ever rotated, update all four TOML files to match.
> Considered and rejected as part of this change: a `pveme.sh` script duplicating parts of
> `late_command.sh` (Debian's post-install hook) — decided against once this simpler, script-free option
> was confirmed to exist; see the git log around 2026-07-10 for the fuller reasoning.

> **TOML still can't do conditionals.** Each `[first-boot] url` above is a static value — TOML has no
> conditionals, so neither file can do the gateway-based `${boot-url}` detection `menu.ipxe`,
> `late_command.sh`, and `first-boot.sh` itself all use (§4.1). That's exactly why there are now two
> files instead of one with an "if" in it — the site-awareness lives in which *file* gets requested
> (`menu.ipxe`'s `${site-prefix}`), not inside the file itself. If a third provisioning server is ever
> added, it needs its own `<SITE>-answer.toml`/`<SITE>-degraded.toml` pair plus one `iseq`/`set site-prefix`
> line in `menu.ipxe` — nothing else.

### 5.2 VRK-degraded.toml / FRD-degraded.toml — single-disk install

Use when a replacement disk hasn't arrived yet. Creates a ZFS mirror with only one disk (degraded state). The second disk can be added later with `zpool attach`.

```toml
[disk-setup]
filesystem = "zfs"
zfs.raid = "raid0"          ← single-disk, equivalent to degraded mirror
disk-list = ["sda"]
```

Everything else is identical to the site's own `*-answer.toml` — including the `[first-boot] url`,
which is `VRK-degraded.toml` → Edinburgh, `FRD-degraded.toml` → Fredericia Havn, matching §5.1.

<u>***NB: Warning! A single-disk ZFS pool has no redundancy. Add the second disk and run `zpool attach rpool sda sdb` before putting workloads on the node***</u>. This is covered in it's onw procedure in this repo!

### 5.3 Switching between TOML files

The iPXE menu's Proxmox VE entry always references `${site-prefix}-answer.toml` — the RAID-1,
both-disks-present file (§5.1). To use the matching `*-degraded.toml` for a specific install
instead (single disk), press Ctrl-B at the boot prompt and change `answer` to `degraded` in the
`proxmox-auto-install-url` parameter — e.g. `.../proxmox/VRK-answer.toml` becomes
`.../proxmox/VRK-degraded.toml`. No file renaming on the server is needed any more (that was the
old workaround, back when there was only one site-agnostic pair of files); a MAC-specific
autodeploy script overriding the URL is still an option too, for a repeatable single-disk build.

### 5.4 What happens after the installer finishes

The `[first-boot]` section in both TOML files instructs the Proxmox installer to fetch and run `first-boot.sh` once the node is up. The `ordering = "fully-up"` setting means the script runs only after the network is fully online — important since it downloads packages.

See §6 for full details of what `first-boot.sh` does.

---

## 6. Proxmox Node Post-Install: first-boot.sh

The `first-boot.sh` is fetched and executed automatically by the PVE installer as configured in `[first-boot]`. It is idempotent and safe to re-run.

### 6.1 What it does (in order)

> **Correction (2026-07-10, second trim):** this whole section previously described a script that did a
> fair amount beyond the ansible user — apt repo fixing, subscription-nag removal, package installs,
> an `/etc/.environment` prompt, VMware guest-tools detection, dotfiles/zsh, a dynamic MOTD, and a
> single-disk ZFS warning. **All of that moved into Ansible on 2026-07-10** (see the real script's own
> changelog), following the same "foot in the door" principle already applied to hostname/rename/
> static-IP on 2026-07-07: this script now does *only* what must happen before Ansible can connect at
> all — ensure `sshd` is present, create the `ansible` user, install its SSH key, configure `NOPASSWD`
> sudoers. Everything else moved to `ansible/playbooks/proxmox/playbooks/`:
> `10-packages.yml` (apt repo fix, subscription nag, packages, VMware tools), `00-preflight.yml`
> (environment prompt — resolved via `ansible/tasks/nodeinfo_environment.yml`, which reads it
> straight from an already-deployed `nodeinfo.json` rather than a separate `/etc/.environment`
> file, same day this was added here — see the second 2026-07-10 changelog entry below; single-disk
> ZFS check — now an explicit `-e pve_acknowledge_single_disk=true` flag instead of a console "type
> I UNDERSTAND" prompt),
> `40-scripts.yml` (dynamic MOTD), and `group_vars/pvenodes/main.yml` (the extra packages). kvm-group
> membership and dotfiles/zsh were dropped from the script entirely rather than moved, since
> `20-ansible-access.yml` and `playbooks/linux/tools.yml` already did them redundantly. The step list
> below is quoted directly from the real, current `bootstrap/web/proxmox/first-boot.sh` (~145 lines,
> down from 576) — **this is the single most consequential correction in this document for anyone about
> to actually run this script**, since the old version would have had you sitting at a keyboard waiting
> for prompts and package installs that no longer happen here.

**Step 1 — Ensure sshd is present**

Defensively installs `openssh-server` and `sudo` (PVE ISO installs already include both — this is a
belt-and-braces check, not a real dependency fix) and ensures `ssh` is enabled/running.

**Step 4 — Ansible user**

Creates the `ansible` service account with:
- Password hardcoded to `Password1!` (matches the pattern used elsewhere in this repo's demo/lab scenarios — deliberate, not a bug, but change it before any real production use)
- SSH public key fetched from `${BOOT_SERVER}/ansible_sshkey.pub`, where `${BOOT_SERVER}` is picked by the same gateway-based detection described in §4.1a (Edinburgh vs Fredericia) — added 2026-07-08, this used to be hardcoded to Edinburgh only
- Full `NOPASSWD` sudo access via `/etc/sudoers.d/ansible` (syntax-checked with `visudo -c`; the file is removed again if the check fails, rather than leaving a broken sudoers drop-in)

That's the entire script now. No packages beyond `openssh-server`/`sudo`, no MOTD, no dotfiles, no
prompts other than what's built into the ansible-user steps above (none, in fact — there is no
interactive prompt left in this script at all).

**Summary and next steps**

Prints a short summary (current DHCP IP, ansible user + key count) and — this is the important part —
tells you exactly what to run next, verbatim:

```
NEXT STEP: Ansible finishes this node's setup

This node still has its installer placeholder hostname and a DHCP IP -- that's expected. From
the Ansible control node, run:

  ansible-playbook -i "<this node's current DHCP IP>," -i configs/inventory \
    -e target="<same DHCP IP>" playbooks/proxmox/bootstrap-new-node.yml

Both extras are required. -i configs/inventory (a second, additional -i source, not a
replacement) is needed purely so group_vars/pvenodes/ -- e.g. pve_packages -- has a path to be
found from at all; without it, later stages like 10-packages.yml fail with "'pve_packages' is
undefined". -e target= (same address as the first -i) is needed because the full site.yml chain
this now runs straight into (see below) resolves its own hosts: pattern before any task in the
run executes, so it can't pick up the address from a fact set earlier in the same run -- and
without it, once configs/inventory is loaded, this playbook's own plays would otherwise match
every real PVE node in the whole inventory, not just this one. Forgetting either fails fast
(this playbook checks for the inventory source, and Ansible itself hard-fails immediately on a
missing target) before anything is touched.

You'll be prompted for this node's real hostname (from your build sheet, e.g. EXAPVEKGE001) --
it sets the real hostname and static network config, then continues straight into the full
site.yml chain (packages incl. GRUB serial console, access setup, /etc/example-music/
deployment, scripts, virt-tools, proxmorph, systemd units) in the same run, still connected via
the DHCP IP throughout. Only once everything is done does it reboot -- once, at the very end,
not before -- to apply the identity/network change. The SSH session on this DHCP IP will not
survive that reboot -- reconnect via the new hostname/IP once it's back up (the site's PVE1 slot
is already in configs/inventory/, generated active by default -- see generate_inventory.py --
there is nothing to add by hand). At that point the node is fully onboarded; nothing further to
run.
```

**No reboot is required or performed automatically** — nothing left in this script needs one, so unlike
the pre-2026-07-10 version there is no `y/N` reboot prompt at all any more.

**What happens to hostname/rename/static-IP now:** none of it happens in this script any more (unchanged
from the 2026-07-07 trim). The node stays on its DHCP-assigned IP with the Proxmox installer's placeholder
hostname (`pve-install`) until you run `ansible-playbook -i "<dhcp-ip>," -i configs/inventory -e target="<dhcp-ip>" playbooks/proxmox/bootstrap-new-node.yml`
from the Ansible control node, per the script's own on-screen instructions above. That single invocation now
does everything this script used to do on real hardware, plus the entire site.yml chain, plus one final reboot
-- previously a separate, manual second step.

### 6.2 Alternate/historical method: `pve-iso-2-pxe`

> This is a **third-party tool, kept for historical reference — not the currently-documented or
> supported method.** The current, supported way to get the Proxmox VE installer kernel/initrd onto the
> provisioning server is the simple mount-and-copy (or 7-Zip, on Windows) approach in §2.3: extract
> `boot/linux26` and `boot/initrd` directly from the official Proxmox VE ISO into
> `bootstrap/web/proxmox/x86_64/boot/`. The transcript below, using a third-party GitHub tool
> (`morph027/pve-iso-2-pxe`) to build a separate PXE-TFTP image bundle, predates that and was never
> confirmed to still be needed — if you're setting up a new provisioning server, use §2.3's method, not
> this one.

```bash
┌─[knightmare@ovhfwl]─[/home/knightmare/vmware]
└──╼ $ git clone https://github.com/morph027/pve-iso-2-pxe
Cloning into 'pve-iso-2-pxe'...
: <snip>

┌─[knightmare@ovhfwl]─[/home/knightmare/vmware/pve-iso-2-pxe]
└──╼ $ wget https://enterprise.proxmox.com/iso/proxmox-ve_9.1-1.iso
: <snip, ~1.7 GB download>

┌─[knightmare@ovhfwl]─[/home/knightmare/vmware/pve-iso-2-pxe]
└──╼ $ sudo bash pve-iso-2-pxe.sh proxmox-ve_*.iso
Using proxmox-ve_9.1-1.iso...
extracting kernel...
extracting initrd...
Finished! pxeboot files can be found in /home/knightmare/vmware/pve-iso-2-pxe.

┌─[knightmare@ovhfwl]─[/home/knightmare/vmware/pve-iso-2-pxe]
└──╼ $ tree pxeboot
pxeboot
├── initrd
└── linux26
```

### 6.3 Deploying and debugging

The actual install flow (confirmed accurate against `docs/buildsheets/buildsheet-pve.md` and the real
`VRK-answer.toml`): boot a plain, unmodified Proxmox ISO (mounted via iLO/iDRAC virtual media) → auto-install
mode "fails" to fetch the answer file (expected, this is the mechanism, not an error) → drops to a root
shell → `wget http://192.168.139.50/proxmox/select-pve-answer.sh && sh select-pve-answer.sh` (Fredericia
Havn: `http://172.16.124.1:8000/proxmox/select-pve-answer.sh`) → follow the prompts → `exit` → installs
unattended → on first login (root), `bash /var/lib/proxmox-first-boot/proxmox-first-boot` to run §6.1's
script by hand if it didn't already fire via `[first-boot]`.

`select-pve-answer.sh` (see its own header for the full detail) replaces what used to be a fully manual
`wget -O /run/automatic-installer-answers http://.../VRK-answer.toml` — the operator had to know which
provisioning network they were on and pick the right `${site-prefix}-answer.toml` vs
`${site-prefix}-degraded.toml` by hand. The script instead detects the provisioning network itself
(same gateway logic `menu.ipxe` uses), counts real physical disks to suggest `answer` vs `degraded`,
fetches the right file, and verifies it looks like real TOML before saying it's safe to `exit`. Written
in POSIX `sh` (BusyBox `ash` has no bash) — its gateway/disk-detection logic was tested directly against
a real `busybox ash` interpreter before being committed, though the actual fetch against a genuine
Proxmox installer environment hasn't been confirmed live yet.

**Why the automatic fetch "fails" at all:** `proxmox-fetch-from-url` (the raw installer boot parameter)
sends the request as an HTTP POST — the node's system properties go in the body, so the answer file's
`[[match]]` filters can key off them — not a GET. Neither `python3 -m http.server` (Fredericia Havn) nor
`static-web-server.exe` (Edinburgh, §2.2) answer POST — both are plain static-file servers — so this raw
fetch always lands as an error and the shell drop is the only way in. `select-pve-answer.sh`'s own
`wget` is a plain GET, same as the old fully-manual version — neither server needs to answer POST for
this flow at all.

**A more automated approach — `proxmox-auto-install-assistant prepare-iso --fetch-from http --pxe`
baking the answer-file URL into a per-site/mode `.iso`, delivered via BMC virtual media, no operator
interaction needed — was built and confirmed working in pieces, then failed its first real end-to-end
test boot outright (2026-07-18, blank cursor).** See `docs/proxmox/pxe-proxmox-autoinstall-build-log.md`
for the full history, including the abandoned approach and why `select-pve-answer.sh` replaces it
rather than debugging BMC delivery further: PVE nodes are built rarely enough, with an operator
physically at the console for BMC virtual media anyway, that this trade made sense. `bootstrap/serve.py`
and `bootstrap/Start-ProxmoxAnswerShim.ps1` (the two POST-capable server tools built for the abandoned
approach) are both still real, tested, working tools — just no longer load-bearing for how Proxmox
actually gets installed. Kept for whatever else might need a POST-capable static file server later.

Useful debugging commands if `first-boot.sh` didn't run automatically or you need to inspect state
afterward:

```bash
## Did it try to fetch the script automatically?
journalctl -u proxmox-first-boot

## Is the script even reachable from the node?
wget -O /tmp/test.sh http://192.168.139.50/proxmox/first-boot.sh && echo "OK"
```

**A standalone tip, unrelated to `first-boot.sh` itself — resetting a forgotten BMC/IPMI password from
the OS once Proxmox is up:**

```bash
root@pve-install:~# apt install ipmitool
: <snip>
root@pve-install:~# ipmitool user set password 2
Password for user 2:
Password for user 2:
Set User Password command successful (user 2)
```

### 6.4 What the real script's output actually looks like

> Quoted directly from the real, current `bootstrap/web/proxmox/first-boot.sh` (2026-07-10, second trim)
> — see §6.1's correction notice for what changed. This transcript is now much shorter than an earlier
> version of this document showed — no repo/nag/package/environment/MOTD/disk-warning output any more,
> since none of that happens in this script.

```text
root@pve-install:~# bash /var/lib/proxmox-first-boot/proxmox-first-boot

  +======================================================+
  |        PROXMOX VE - NODE PROVISIONING                |
  |              jukebox.internal                        |
  +======================================================+

  ================================================
  ENSURING SSH SERVER
  ================================================
  [->] Installing openssh-server + sudo (if missing)...
  [+] sshd present and enabled

  ================================================
  ANSIBLE USER SETUP
  ================================================
  [i] Boot server detected: http://192.168.139.50 (gateway: 192.168.139.254)
  [->] Creating ansible user...
  [+] User ansible created
  [->] Setting password...
  [+] Password set to Password1!
  [->] Fetching SSH public key...
  [+] SSH key installed
  [->] Setting permissions...
  [+] Permissions set
  [->] Configuring NOPASSWD sudo...
  [+] Sudoers configured

  +======================================================+
  |  ANSIBLE-BOOTSTRAP COMPLETE                           |
  +======================================================+

  [+]  Current IP :        192.168.139.87 (DHCP, provisioning network)
  [+]  Ansible user :      ansible -- 1 SSH key(s)

  +------------------------------------------------------+
  |  NEXT STEP: Ansible finishes this node's setup       |
  |                                                       |
  |  This node still has its installer placeholder       |
  |  hostname and a DHCP IP -- that's expected. From      |
  |  the Ansible control node, run:                      |
  |                                                       |
  |    ansible-playbook -i "192.168.139.87," \            |
  |      -i configs/inventory \                            |
  |      -e target="192.168.139.87" \                     |
  |      playbooks/proxmox/bootstrap-new-node.yml         |
  |                                                       |
  |  You'll be prompted for this node's real hostname     |
  |  (from your build sheet, e.g. EXAPVEKGE001) -- it     |
  |  sets the real hostname/network, then continues       |
  |  straight into the full site.yml chain (packages,     |
  |  access, systemd units, etc.) in this same run.       |
  |  One reboot at the very end applies it all -- the     |
  |  SSH session on this DHCP IP will not survive that.   |
  |  Reconnect via the new hostname/IP once it is back up.|
  +------------------------------------------------------+

  [i] No reboot is required by this script -- nothing here needs one.
```

**The single most important thing in that output, for the PFY's plan:** the node never gets a real
hostname or static IP from this script — it stays on its DHCP lease with the Proxmox installer's
placeholder hostname the whole time. The very next command to run, from the Ansible control node, is
printed on-screen at the end: `ansible-playbook -i "<dhcp-ip>," -i configs/inventory -e target="<dhcp-ip>" playbooks/proxmox/bootstrap-new-node.yml`
Both extras are required — `-i configs/inventory` (additional, not a replacement) so
`group_vars/pvenodes/` (e.g. `pve_packages`) has a path to be found from at all, and
`-e target=` because the full `site.yml` chain this now runs straight into resolves its own
`hosts:` pattern before any task in the run executes, so it can't be told the address by a fact
set earlier in the same run — without it, this playbook's own plays would otherwise match every
real PVE node in the whole inventory once `configs/inventory` is loaded, not just this one. That
single invocation asks for the real hostname, sets the permanent
site-LAN IP, then continues straight into `proxmox/site.yml`'s full stage chain (`00-preflight.yml`,
`10-packages.yml`, `20-ansible-access.yml`, `30-example-music.yml`, `40-scripts.yml`,
`45-virt-tools.yml`, `46-proxmorph.yml`, `50-systemd-units.yml`) in the same run — apt repo fix,
subscription-nag removal, packages (incl. GRUB serial console), the environment prompt, VMware guest
tools, access setup, `/etc/example-music/` deployment, the dynamic MOTD, and the single-disk ZFS check
— and only reboots once, right at the very end, once everything is actually done. Previously this was
two separate manual steps with a reboot in between; as of 2026-07-12 it's one.

---

## 7. Debian Auto-Install

### 7.1 lvm.seed (preseed file)

The `lvm.seed` preseed file drives a fully automated Debian installation with:

- Locale `en_GB.UTF-8`, keyboard `gb`, domain `jukebox.internal`
- Standard kernel (`linux-image-amd64` — not cloud/virtual, for compatibility with LVM)
- LVM on `/dev/sda` with 100% of disk used; VG name set to the hostname automatically via `partman/early_command`
- Partition layout: 384–1536 MB `/boot` (ext3) + GPT BIOS-grub partition + 512 MB swap LV + 5 GB+ root LV (ext4)
- `ansible` user created with passwordless sudo, added to `adm cdrom sudo dip` groups
- Packages installed: `vim tmux openssh-server net-tools tree sudo zsh zsh-autosuggestions zsh-syntax-highlighting`
- `unattended-upgrades` enabled for security updates
- GRUB installed to `/dev/sda`
- On completion, fetches and runs `late_command.sh` from the provisioning server

The hostname is **not** set by the preseed — the installer will prompt for it. This is intentional: it ensures each machine gets its correct EXA-convention name rather than a generic placeholder. To supply a hostname without a prompt (for fully automated deploys), add `netcfg/get_hostname=EXASRVXXX001` to the kernel command line in the iPXE menu entry.

### 7.2 late_command.sh

> **Correction (2026-07-10):** the LVM-kernel-module bullet below was removed at the real script's own
> v1.2 ("stop re-adding LVM2 kernel modules" — the file's own changelog, not a guess) and no longer
> happens at all. Several real, current actions were previously undocumented entirely — the gateway-based
> boot-server detection, and fetching `sites.csv`/`devices.csv`/`begyndelse.json`. Rewritten against the
> real, current `bootstrap/web/debian/late_command.sh` (v1.5).
>
> **Correction (2026-07-11):** dropped at v1.6 — `sites.csv`/`devices.csv` are no longer fetched here.
> `ansible/playbooks/linux/tools.yml` deploys both (and `address_policy.json`/`ad_forest.json`/
> `ad_groups.json`/`ad_users.json`/`ad_computers.json`) to every Ansible-managed Linux host, so
> pre-staging just these two here was pure duplicate work once a node is actually under management —
> and `bindme.sh`/`firewallme.sh`/`rudderme.sh`'s own documented "expected, supported path" for the
> pre-Ansible break-glass case has always been a manual wget anyway (see each script's own header),
> not reliance on this pre-staged copy. `begyndelse.json` is kept — no Ansible playbook deploys it,
> so it remains the one file this script is the *only* source for before Ansible exists on the box.

Runs inside the Debian installer environment (busybox `sh` — no bash, no arrays, no `[[ ]]`). Uses `in-target` to run commands inside the installed system chroot.

Actions performed, in order:

- **Gateway-based boot-server detection** — same mechanism as §4.1a/§6.1's Step 4: checks the DHCP gateway (`172.16.124.2` → Fredericia, anything else → Edinburgh) and uses that server for every fetch below. Not a separate concept from the Proxmox side — the exact same detection logic, independently implemented in three places (`bootstrap.ipxe`'s embedded chain fetches `menu.ipxe` differently, but `menu.ipxe`, `first-boot.sh`, and `late_command.sh` all do this same gateway check).
- Adds `ansible` to the `sudo` group (the user account itself is created by the preseed directly, via `d-i passwd/user-default-groups string adm cdrom sudo dip` — not by this script, despite an earlier version of this doc implying otherwise)
- Installs `openssh-server sudo net-tools bash-completion` (belt-and-braces, some are already in the preseed package list)
- Creates `/etc/example-music/` and fetches `begyndelse.json` into it — the one single-source-of-truth file no Ansible playbook deploys, so this node has it from first boot rather than never getting it at all before a break-glass script needs it. `sites.csv`/`devices.csv` are fetched separately, later, by `ansible/playbooks/linux/tools.yml` once the node is under Ansible management (see the v1.6 correction above)
- Creates `/home/ansible/.ssh/authorized_keys` by fetching `ansible_sshkey.pub` from the (gateway-detected) provisioning server using busybox `wget`
- Fetches `server-prompts.zsh`/`server-prompts.sh` (the "safety dance" prompt scripts — see `bootstrap/web/server-prompts.{sh,zsh}`) and wires them into `/etc/zsh/zshrc` and `/etc/bash.bashrc` so they load for every shell on this node
- Writes a `.vimrc` (ruler, dark background, syntax highlighting) to the ansible home dir
- Sets correct ownership and permissions (`700` on `.ssh/`, `600` on `authorized_keys`) using numeric UID/GID (necessary because the script runs outside the chroot, in the installer environment, not inside the target system)
- Creates `/etc/sudoers.d/ansible` with `NOPASSWD: ALL` and validates it with `visudo -c` — removes the file and aborts if validation fails
- Prints verification output at the end (passwd entry, authorized_keys content, `/etc/example-music` listing, permissions) — useful to check on-screen if something later goes wrong and you're wondering whether this step actually completed

---

## 8. Windows VM Post-OOBE Bootstrap

This applies to new Windows VMs (or physical Windows machines) being provisioned into the domain. It is not part of the Proxmox node build — it runs inside Windows after the OS installation OOBE completes.

### 8.1 PostOOBE.cmd

> **Correction (2026-07-10):** this section previously described `PostOOBE.cmd` mapping a `Z:` drive to
> `\\EXADCSCPH001\DeployTools` with a `DEPLOYTOOLS_PASS` environment variable, launching the script from
> `Z:\panther\`, then unmapping on exit. None of that matches the real, current `bootstrap/web/windows/
> PostOOBE.cmd` — corrected below.
>
> **Status: historical artefact, not a live path.** `PostOOBE.cmd`/`Join-DomainAndBootstrap.ps1` predate
> Ansible's `windows_bootstrap` chain. Domain join and everything else this script does are now handled by
> `windows_bootstrap/playbooks/80-domainjoin.yml` and the rest of the numbered chain, run the normal way
> once a host has OpenSSH reachable (unattend XML → OpenSSH → Ansible). The manually-mapped `DeployTools`
> share this script depends on is itself moot now that Ansible bootstrapping handles this end to end — it
> is not being actively maintained or kept in sync, and its `\\DC01\deploytools\` vs `$DeployToolsShare`
> (`\\EXADCSCPH001\DeployTools`) UNC-path disagreement (noted below) is left as-is rather than reconciled.
> This section documents it as a historical record, not a recommended path.

The real, current `PostOOBE.cmd` is much simpler than previously described:

```cmd
timeout /t 8 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "& '\\DC01\deploytools\Join-DomainAndBootstrap.ps1'"
```

It waits 8 seconds for networking, then runs `Join-DomainAndBootstrap.ps1` directly from a hardcoded UNC
path (`\\DC01\deploytools\`) — no `Z:` drive mapping, no credential environment variable, no unmap step.

> **Known, unresolved inconsistency:** `PostOOBE.cmd` hardcodes `\\DC01\deploytools\`, but
> `Join-DomainAndBootstrap.ps1`'s own `$DeployToolsShare` variable is set to `\\EXADCSCPH001\DeployTools`
> — two different UNC paths for what should be the same share. `DC01` doesn't follow the `EXA*` naming
> convention used everywhere else in this estate, and no `DCS` host is defined for site `CPH` in
> `benarbejde/devices.csv`. Flagging this rather than guessing which one is correct — confirm with
> whoever set up the DeployTools share before relying on either path.

### 8.2 Join-DomainAndBootstrap.ps1

The PowerShell script runs as a 22-stage bootstrap (stages 0, 0b, 1 through 22, plus 17b and 22b —
see the script's own `# ---------- Stage N: ... ----------` comments for the authoritative list; the
"12-stage" figure previously stated here was wrong). A sentinel file at
`C:\Windows\Temp\PostOOBE-Bootstrap.done` prevents re-running.

**Stage 1 — Hypervisor detection**

Reads `Win32_ComputerSystem.Manufacturer` to determine whether the machine is a VMware guest, Proxmox/KVM guest, or physical hardware. This controls which guest tools are installed in Stage 7.

**Stage 2 — Site detection**

Reads the local IPv4 address and matches the third octet against the `$SubnetSiteMap` table to identify the site code and suggest the correct AD domain. The map is a hardcoded table inside the script (not derived from `sites.csv`), so it needs a manual entry added whenever a new site is commissioned — check `$SubnetSiteMap` directly in the script for the current, authoritative list rather than trusting a specific count here.

**Stage 3 — Hostname and domain**

Prompts for a hostname (max 15 characters, alphanumeric + hyphens) and the target AD domain. The site-detected domain is offered as the default — every entry in `$SubnetSiteMap` suggests `jukebox.internal`, since that's the only real, joinable domain (see the §3.1 correction above). `$AllowedDomains` also still lists `example.com`/`example.net`/`example.org` as selectable, a leftover from this script's pre-`ad_forest.json` design — this is a documented historical-artefact quirk, not something to rely on or "fix" going forward (see the script's own header).

**Stage 4 — OU enumeration**

Queries AD via `System.DirectoryServices.DirectorySearcher` and lists available OUs in the target domain, filtered to exclude `Domain Controllers` and system OUs. The operator selects by number.

**Stage 5 — Rename and domain join**

Renames the computer if needed, then calls `Add-Computer` to join the domain into the selected OU using the credentials entered in Stage 4.

**Stage 6–11 — Software installation**

| Stage | What is installed |
|---|---|
| 6 | Chocolatey package manager |
| 7 | VMware Tools *or* QEMU guest agent (platform-dependent) |
| 8 | RustDesk (from local `DeployTools\utils\` copy if present, else Chocolatey) |
| 9 | WinSCP, PuTTY, Hyper, Notepad++, PowerShell 7, 7-Zip, Far Manager, dua-cli |
| 10 | RSAT: Active Directory, DNS, Group Policy tools |
| 11 | PS7 modules: PSConsoleTools, PSWindowsUpdate, PSWriteColor, PSReadLine, Terminal-Icons, CompletionPredictor |

**Stage 12 — Finish**

Writes the sentinel file and reboots after 20 seconds.

### 8.3 Salt minion — deliberately NOT part of this Setup-time flow

Every Windows node (`WKS`/`LAP`/`SUR`/`SVR`/`DCS`) gets a Salt minion, but not through
anything in this section. It was briefly wired into
`headlessunattend.xml`'s `FirstLogonCommands` the same day this was written (2026-07-20), then
moved out again before anything was built against it: the unattend XML sets `ComputerName` to
`*` (a random Setup-time name) and `FirstLogonCommands` fires before any rename happens, so the
Salt minion would have registered under that random name — `EXASLTCLD001` would have
accumulated one dead/renamed key per build, needing manual `salt-key` cleanup forever.

The real install is `ansible/playbooks/windows_bootstrap/playbooks/82-salt-minion.yml`,
running over SSH near the end of the normal windows_bootstrap chain — well after
`00-preflight.yml`'s Phase G has already renamed the host to its final `EXA<ROLE><SITE><NNN>`
hostname, so the minion's identity is always correct, first time. See
`docs/buildsheets/buildsheet-salt-minion.md` and `ansible/playbooks/salt/README.md` for the
full mechanism, scope, and the manual fallback for endpoints that never go through
windows_bootstrap at all.

The MSI (`bootstrap/web/windows/Salt-Minion-Setup.msi`) is genuinely committed to this repo,
though — see the tree entry above. Unlike most large binaries referenced from this file
(§2.3's Debian/Proxmox netboot assets), this one's a deliberate exception: it's genuinely open
source (Apache-2.0) and checksum-verified before being placed; see the buildsheet for the full
reasoning.

---

## 9. Updating the Boot Server IP

If the provisioning server IP changes from `192.168.139.50`, the following files must be updated:

> **Correction (2026-07-10):** the table below previously referenced `web/.ipxe` (doesn't exist — see
> §4.2's correction) and gave `web/`-root paths for `lvm.seed`/`late_command.sh` that don't match the
> real tree. Corrected against the actual files.
>
> **Correction (2026-07-11):** `bootstrap/web/boot.ipxe` and `bootstrap/web/lvm.seed` turned out to be
> stale/superseded pre-rename leftovers (see each file's own note) — dropped from this table, since
> updating a hardcoded IP in a file nothing live reads doesn't accomplish anything. `late_command.sh`'s
> two copies (`bootstrap/web/debian/late_command.sh`, the real one, and `bootstrap/web/late_command.sh`,
> a synced copy) no longer need manual reconciliation — `.githooks/pre-commit` keeps them in sync
> automatically now (same mechanism as `sites.csv` etc.), so only `debian/late_command.sh`'s own
> `BOOT_SERVER` line needs changing by hand.
>
> **Correction (2026-07-11, second):** `answer.toml`/`degraded.toml` are now site-prefixed
> (`VRK-answer.toml`/`FRD-answer.toml`/`VRK-degraded.toml`/`FRD-degraded.toml`, §5.1) — if
> **Edinburgh's** IP specifically changes, only the `VRK-*` files need their `[first-boot] url`
> updated; the `FRD-*` files are unaffected (they're already pinned to Fredericia Havn, not
> Edinburgh). If Fredericia Havn's IP changes instead, it's the `FRD-*` files, not `VRK-*`.

| File | Variable / line to change |
|---|---|
| `bootstrap/web/bootstrap.ipxe` | `set boot-ip 192.168.139.50` |
| `bootstrap/web/menu.ipxe` | `set boot-url http://192.168.139.50` in the `:env_edinburgh` branch (§4.1) — `${site-prefix}` itself doesn't change |
| `bootstrap/web/proxmox/VRK-answer.toml` | `url = "http://192.168.139.50/proxmox/first-boot.sh"` |
| `bootstrap/web/proxmox/VRK-degraded.toml` | `url = "http://192.168.139.50/proxmox/first-boot.sh"` |
| `bootstrap/web/debian/late_command.sh` | `BOOT_SERVER="http://192.168.139.50"` — `bootstrap/web/late_command.sh` syncs automatically via `.githooks/pre-commit`, don't edit it directly |
| `bootstrap/web/proxmox/first-boot.sh` | Any references to provisioning server URL |

After changing `bootstrap.ipxe`, the iPXE binary must be recompiled and redistributed to all IPMI virtual media mounts and USB keys.

---

## 10. Quick Reference — Deploy a New Proxmox Node

1. **Prepare** — ensure `web/` is being served from `192.168.139.50` (or the real provisioning IP)
2. **Boot** — mount a plain, unmodified Proxmox VE ISO via iLO/iDRAC/BMC virtual media, power on
3. **Select answer file** — auto-install "fails" to fetch its answer file (expected — no PXE entry
   drives this any more) and drops to a root shell; run
   `wget http://192.168.139.50/proxmox/select-pve-answer.sh && sh select-pve-answer.sh`, follow its
   prompts (it detects the site from the gateway and suggests `answer` vs `degraded` from the real
   disk count), then `exit` — see §6.3 for the full flow
4. **Install** — runs unattended once the answer file is confirmed; takes approximately 5–10 minutes
   depending on disk speed
5. **first-boot.sh** — runs automatically via the answer file's own `[first-boot]` block; no
   prompts — it only creates the `ansible` user and ensures `sshd` is present (see §6.1)
6. **Verify** — SSH to the node as `ansible` using the key from `ansible_sshkey.pub`; check `pvesh get /nodes` to confirm API is up
7. **ZFS** — if degraded install, add second disk: `zpool attach rpool sda sdb` once the disk arrives
8. **Proceed** — run `ansible-playbook -i "<dhcp-ip>," -i configs/inventory -e target="<dhcp-ip>" playbooks/proxmox/bootstrap-new-node.yml` per `first-boot.sh`'s own on-screen instructions (§6.1) — node is not fully onboarded until this completes

   

   
   

   *Example Music Limited — Internal Infrastructure Documentation*   *Do not distribute outside the organisation*cloud
