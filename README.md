# Example Music Infra

Infrastructure as Code repository for Example Music Limited.

This repository contains everything needed to take a site from bare metal to production — from bootstrapping the first device on an empty network through to Ansible-managed configuration and operational runbooks.

---

## Repository Structure
```
exa-infra/
├── ansible/          # Ansible roles and playbooks
├── bootstrap/        # Site bootstrap toolkit — day zero tooling
└── docs/             # Operational documentation and procedures
```

---

## bootstrap/

Day-zero toolkit for new site deployments. This is what goes on the technician's USB drive or laptop when they walk into an empty server room.

The bootstrap network is always `192.168.139.0/24`. The bootstrap server runs at `192.168.139.50` and provides DHCP, TFTP, HTTP and DNS for the provisioning subnet. Nothing else should be on this subnet during deployment.

**Contents:**

- Custom iPXE ISO and `.lkrn` binary — chainloads into the boot menu from any machine that can PXE boot, pointed at `192.168.139.50`
- iPXE boot menu — presents install options for Proxmox VE and other supported targets
- `static-web-server.exe` — portable HTTP server, no install required, serves the bootstrap content from a Windows laptop if needed
- Proxmox answer files:
  - `answer.toml` — standard two-disk ZFS RAID1 install
  - `degraded.toml` — single-disk ZFS RAID0 install for when the second disk hasn't arrived yet
- `first-boot.sh` — post-install provisioning script, runs on first boot, configures hostname, networking, DNS, packages and raises a single-disk warning if RAID1 is not yet in place

**Typical bootstrap sequence:**

1. Connect bootstrap laptop to the provisioning switch on `192.168.139.0/24`

2. Start `static-web-server.exe` or equivalent serving the bootstrap directory:

```
.\static-web-server-x64.exe -d web/ -g info -a 192.168.139.50 --directory-listing 2>&1 | Tee-Object -FilePath server.log | ForEach-Object {
>>   if ($_ -match '^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\.\d+Z(.*)$') {
>>     Write-Host "`e[38;5;166m$($matches[1]) `e[0m" -NoNewline
>>     Write-Host "`e[38;5;33m$($matches[2])`e[0m" -NoNewline
>>     $rest = ($matches[3] -replace 'static_web_server::', '') -replace '^\s{2}', ' '
>>     if ($rest -match '::server:')     { Write-Host $rest -ForegroundColor Magenta }
>>     elseif ($rest -match '\sERROR\s') { Write-Host $rest -ForegroundColor Red }
>>     elseif ($rest -match '\sWARN\s')  { Write-Host $rest -ForegroundColor Yellow }
>>     elseif ($rest -match '\sINFO\s')  { Write-Host $rest -ForegroundColor Cyan }
>>     else                              { Write-Host $rest }
>>   } else { Write-Host $_ }
>> }
2026-06-12 09:25:21 INFO server: static-web-server 2.40.1
2026-06-12 09:25:21 INFO server: log level: info
2026-06-12 09:25:21 INFO server: server bound to tcp socket 192.168.139.50:80
2026-06-12 09:25:21 INFO server: runtime worker threads: 16
2026-06-12 09:25:21 INFO server: runtime max blocking threads: 512
2026-06-12 09:25:21 INFO server: redirect trailing slash: enabled=true
2026-06-12 09:25:21 INFO server: ignore hidden files: enabled=false
2026-06-12 09:25:21 INFO server: disable symlinks: enabled=false
2026-06-12 09:25:21 INFO server: grace period before graceful shutdown: 0s
2026-06-12 09:25:21 INFO server: index files: index.html
2026-06-12 09:25:21 INFO directory_listing: directory listing: enabled=true
2026-06-12 09:25:21 INFO directory_listing: directory listing order code: 6
2026-06-12 09:25:21 INFO directory_listing: directory listing format: Html
2026-06-12 09:25:21 INFO directory_listing_download: directory listing download: enabled=false
2026-06-12 09:25:21 INFO fallback_page: fallback page: enabled=false, value=""
2026-06-12 09:25:21 INFO health: health endpoint: enabled=false
2026-06-12 09:25:21 INFO log_addr: log requests with remote IP addresses: enabled=false
2026-06-12 09:25:21 INFO log_addr: log X-Real-IP header: enabled=false
2026-06-12 09:25:21 INFO log_addr: log X-Forwarded-For header: enabled=false
2026-06-12 09:25:21 INFO log_addr: trusted IPs for X-Forwarded-For: all
2026-06-12 09:25:21 INFO basic_auth: basic authentication: enabled=false
2026-06-12 09:25:21 INFO maintenance_mode: maintenance mode: enabled=false
2026-06-12 09:25:21 INFO maintenance_mode: maintenance mode status: 503
2026-06-12 09:25:21 INFO maintenance_mode: maintenance mode file: ""
2026-06-12 09:25:21 INFO compression_static: compression static: enabled=false
2026-06-12 09:25:21 INFO compression: auto compression: enabled=true, formats=deflate,gzip,brotli,zstd, compression level=Default
2026-06-12 09:25:21 INFO control_headers: cache control headers: enabled=true
2026-06-12 09:25:21 INFO security_headers: security headers: enabled=false
2026-06-12 09:25:21 INFO mem_cache::cache: in-memory cache (experimental): enabled=false
2026-06-12 09:25:21 INFO server: installing graceful shutdown ctrl+c signal handler
2026-06-12 09:25:21 INFO Server::start_server{addr_str="192.168.139.50:80" threads=16}: server: close time.busy=0.00ns time.idle=2.70┬╡s
2026-06-12 09:25:21 INFO server: http1 server is listening on http://192.168.139.50:80
2026-06-12 09:25:21 INFO server: press ctrl+c to shut down the server
:<snip>
2026-06-13 16:40:37 WARN error_page: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe status=404 error="Not Found"
2026-06-13 16:41:31 INFO log_addr: incoming request: method=GET uri=/menu.ipxe
2026-06-13 16:41:31 INFO log_addr: incoming request: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe
2026-06-13 16:41:31 WARN error_page: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe status=404 error="Not Found"
2026-06-13 16:42:25 INFO log_addr: incoming request: method=GET uri=/menu.ipxe
2026-06-13 16:42:25 INFO log_addr: incoming request: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe
2026-06-13 16:42:25 WARN error_page: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe status=404 error="Not Found"
2026-06-13 16:43:18 INFO log_addr: incoming request: method=GET uri=/menu.ipxe
2026-06-13 16:43:19 INFO log_addr: incoming request: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe
2026-06-13 16:43:19 WARN error_page: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe status=404 error="Not Found"
2026-06-13 16:44:12 INFO log_addr: incoming request: method=GET uri=/menu.ipxe
2026-06-13 16:44:12 INFO log_addr: incoming request: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe
2026-06-13 16:44:12 WARN error_page: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe status=404 error="Not Found"
2026-06-13 16:45:06 INFO log_addr: incoming request: method=GET uri=/menu.ipxe
2026-06-13 16:45:06 INFO log_addr: incoming request: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe
2026-06-13 16:45:06 WARN error_page: method=GET uri=/autodeploy/bc-24-11-ad-b0-d5.ipxe status=404 error="Not Found"
2026-06-14 10:16:13 INFO log_addr: incoming request: method=GET uri=/menu.ipxe
2026-06-14 10:16:13 INFO log_addr: incoming request: method=GET uri=/autodeploy/00-0c-29-ad-ff-74.ipxe
2026-06-14 10:16:13 WARN error_page: method=GET uri=/autodeploy/00-0c-29-ad-ff-74.ipxe status=404 error="Not Found"
2026-06-14 10:16:20 INFO log_addr: incoming request: method=GET uri=/debian/x86_64/linux
2026-06-14 10:16:20 INFO log_addr: incoming request: method=GET uri=/debian/x86_64/initrd.gz
2026-06-14 10:16:47 INFO log_addr: incoming request: method=GET uri=/debian/lvm-bios.seed
2026-06-14 10:19:54 INFO log_addr: incoming request: method=GET uri=/debian/late_command.sh
2026-06-14 10:19:55 INFO log_addr: incoming request: method=GET uri=/ansible_sshkey.pub
2026-06-14 10:19:55 INFO log_addr: incoming request: method=GET uri=/server-prompts.zsh
2026-06-14 10:19:55 INFO log_addr: incoming request: method=GET uri=/server-prompts.sh
2026-06-14 10:22:45 INFO log_addr: incoming request: method=GET uri=/firewallme.sh
2026-06-14 10:23:37 INFO log_addr: incoming request: method=GET uri=/proxmox/sites.csv
2026-06-14 10:31:15 INFO log_addr: incoming request: method=GET uri=/firewallme.sh
2026-06-14 10:34:36 INFO log_addr: incoming request: method=GET uri=/firewallme.sh
2026-06-14 10:38:51 INFO log_addr: incoming request: method=GET uri=/ansibleme.sh
2026-06-14 10:39:35 INFO log_addr: incoming request: method=GET uri=/sites.csv
2026-06-14 10:39:43 INFO log_addr: incoming request: method=GET uri=/proxmox/sites.csv
```

3. PXE boot target machine — it will chainload the iPXE menu from the `192.168.139.50` device:

```
2026-02-28T10:29:28.678023Z  INFO static_web_server::log_addr: incoming request: method=GET uri=/menu.ipxe
2026-02-28T10:29:28.682221Z  INFO static_web_server::log_addr: incoming request: method=GET uri=/autodeploy/00-0c-29-81-fc-e1.ipxe
2026-02-28T10:29:28.682459Z  WARN static_web_server::error_page: method=GET uri=/autodeploy/00-0c-29-81-fc-e1.ipxe status=404 error="Not Found"
2026-02-28T10:29:33.055129Z  INFO static_web_server::log_addr: incoming request: method=GET uri=/debian/linux
2026-02-28T10:29:33.366703Z  INFO static_web_server::log_addr: incoming request: method=GET uri=/debian/initrd.gz
2026-02-28T10:30:08.322125Z  INFO static_web_server::log_addr: incoming request: method=GET uri=/lvm.seed
```

4. Select install target (Proxmox VE RAID1 or degraded single-disk)

5. Unattended install completes, node reboots

6. `first-boot.sh` runs, configures the node, sets persistent DNS via `pvesh`

7. If single-disk: operator is prompted to acknowledge the no-redundancy warning before proceeding

8. Hand off to Ansible for full configuration

---

## ansible/

Ansible roles and playbooks for post-bootstrap configuration and ongoing management.
```
ansible/
├── ansible.cfg
├── inventory/
│   └── hosts.yml          # Static inventory — all sites and nodes
├── playbooks/
│   └── zfs-disk-replace.yml
└── roles/
    └── pve_zfs_replace/   # ZFS disk replacement / RAID1 upgrade
        ├── defaults/
        ├── meta/
        └── tasks/
            ├── main.yml
            ├── assess.yml      # Read-only assessment — always runs
            ├── validate.yml    # Safety checks before any changes
            ├── replace.yml     # Partition, resilver, bootloader
            ├── expand.yml      # Pool expansion if new disk is larger
            └── summarise.yml   # Final verification and report
```

**ZFS disk replacement playbook** runs in two phases:
```bash
# Phase 1 — assessment only, no changes made
ansible-playbook playbooks/zfs-disk-replace.yml -l EXAPVEFAL001

# Phase 2 — execute replacement
ansible-playbook playbooks/zfs-disk-replace.yml -l EXAPVEFAL001 \
  -e new_disk=sdb -e confirmed=yes
```

Phase 1 always runs and prints a summary of pool state, healthy disk, missing vdev and candidate disks. It then intentionally fails to prevent accidental execution. Phase 2 requires both `new_disk` and `confirmed=yes` to be explicitly passed.

Safety features: `serial: 1` (never runs on more than one node simultaneously), node role check (`jq -e '.role == "proxmox"' /etc/example-music/nodeinfo.json`), reboot-pending check, disk identity assertions, GUID uniqueness verification, ESP count verification post-completion.

---

## docs/

Operational runbooks and deployment procedures.
```
docs/
├── site-inventory.md          # Per-site device register and network map
├── network-inventory.md       # Full global infrastructure inventory
├── zfs-disk-replace.md        # ZFS RAID1 disk replacement procedure
├── zfs-raid0-to-raid1.md      # Single-disk to RAID1 upgrade procedure
└── zfs-pool-expansion.md      # Expanding pool after replacing with larger disk
```

| Document | Description |
|---|---|
| `site-inventory.md` | Template and per-site checklist — one section per site, tracks completion status, ZFS mirror health and boot independence testing |
| `network-inventory.md` | Full global device register — all 30+ sites, infrastructure, endpoints, IoT, domain controllers and known issues |
| `zfs-disk-replace.md` | Runbook for replacing a failed disk in an existing RAID1 mirror — manual procedure with verified command sequence |
| `zfs-raid0-to-raid1.md` | Runbook for upgrading a single-disk (degraded) node to full RAID1 when the second disk arrives — uses `zpool attach` not `zpool replace` |
| `zfs-pool-expansion.md` | Runbook for expanding pool capacity after replacing both disks with larger ones — `parted resizepart`, `autoexpand`, `zpool online -e` |

---

# The Special Case: Cloud Network & vRACK Legal Ficiton

The CLD network on `192.168.69.0/24` and it's vRACK `192.168.139.0/24` are a special case. Below is the documentation which covers this:

## Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174).

**NB: I personally treat SHOULD and SHOULD NOT as ambigious, so they MUST NOT be used!**

### Conventions

The Example Music infrastructure follows a consistent addressing convention throughout the estate. Once the addressing scheme is understood, the function and location of most hosts can be determined from their IP address alone.

Unless explicitly stated otherwise, **all deployments MUST conform to the conventions defined below.**

- **vRACK:** A *legal fiction* representing the upstream OVH vRACK. This network uses **192.168.139.0/24**, with the upstream gateway assumed to be **192.168.139.254**. Virtual machines attached to this network MUST be assigned their "real-world" addresses from this subnet.

- **Provisioning Network:** **192.168.139.0/24**. This network MUST be used exclusively during the bootstrap process. Following successful deployment, it represents the upstream WAN connection, emulating an ISP/OVH vRACK.

- **Bootstrap Server:** **192.168.139.50**. This host MAY be a laptop, desktop workstation, lightweight container or virtual machine. It provides the HTTP, PXE, TFTP and associated services required to provision the remainder of the environment. Without this host, the estate cannot bootstrap.

- **Site LANs:** Site LANs MUST use the format **192.168.xx.0/24**, where **xx** is the allocated site octet (for example, **192.168.76.0/24** for the FAL site). The authoritative source for site allocations MUST be:

- **VPN Networks:** WireGuard networks MUST use **10.0.xx.0/24**, where **xx** matches the corresponding site number. The firewall WireGuard endpoint MUST always be assigned **.1**.

- **Proxmox Nodes:** Proxmox VE hosts MUST occupy addresses **.5–.7** on the site LAN.

- **Domain Controllers:** Active Directory Domain Controllers MUST occupy address **.10** on the site LAN.

- **Remote Management:** Hardware management interfaces (iDRAC, iLO, Redfish, etc.) MUST occupy address **.3** wherever practical.

## CLD Special Case

The **CLD** deployment is the sole special-case deployment within the estate.

Unlike every branch deployment, CLD hosts shared infrastructure consumed by multiple sites. Consequently, several addressing conventions and infrastructure roles intentionally differ from the standard site model.

This behaviour is intentional, documented, and REQUIRED.

Automation MUST assume the standard site conventions by default.

Automation MUST NOT assume that CLD conforms to the standard branch architecture.

Any behaviour required specifically for CLD MUST be implemented explicitly and MUST remain isolated to the CLD deployment. Under no circumstances MUST the baseline conventions be weakened or modified solely to accommodate CLD.

The CLD deployment hosts infrastructure including (but not limited to):

- Central DNS
- Central PBX
- Ansible Automation
- Bootstrap / Provisioning Services
- Active Directory
- Central Windows Administration
- Shared management infrastructure

For complete architectural details, refer to:

## CLD Special Hosts

| IP Address        | Hostname       | Role                                  | Notes |
|------------------|----------------|--------------------------------------|-------|
| `192.168.139.1`  | EXARTRCLD001   | Secondary Internet Gateway / Firewall | Fallback Internet connection |
| `192.168.139.2`  | EXARACCLD001   | BMC Pool Slot 1                      | Proxmox Node 1 iDRAC/iLO |
| `192.168.139.5`  | EXAPVECLD001   | Proxmox VE Node                      | Hosts core CLD infrastructure |
| `192.168.139.8`  | EXADNSCLD001   | BIND9 DNS Server                     | Primary DNS for `jukebox.internal` |
| `192.168.139.9`  | EXAANSCLD001   | Ansible Automation Server            | Planned migration to 192.168.69.0/24 |
| `192.168.139.10` | EXADCSCLD001   | Active Directory Domain Controller    | AD for `jukebox.internal` |
| `192.168.139.20` | EXASVRCLD001   | Windows Administration Server         | Central Windows management |
| `192.168.139.48` | EXAPBXCLD001   | Central PBX                          | All remote site SBCs trunk here |
| `192.168.139.50` | EXAPRVCLD001   | Provisioning Server                  | Bootstrap / PXE / TFTP (*legal fiction*) |
| `192.168.139.69` | EXAFWLCLD001   | CLD Firewall                        | Internal LAN: 192.168.69.253/24 |
| `192.168.139.253`| EXARTRCLD001   | Primary Internet Gateway            | Physical upstream router (not managed) |

## Normative Requirements

The following requirements are MANDATORY:

- Site addressing MUST follow the conventions defined in this document.
- Site allocations MUST be recorded in `bootstrap/web/proxmox/sites.csv`.
- Automation MUST treat branch deployments as the default case.
- CLD MUST be treated as the sole special-case deployment.
- CLD-specific logic MUST remain isolated from standard site logic.
- Contributors MUST NOT modify baseline conventions to accommodate CLD.
- Any future special-case deployments MUST be explicitly documented before implementation.

Check the `CLD_Network_Overview.md` document for full details for the "Black Swan" Network 

## Requirements

- Ansible 2.14+
- Python 3.10+
- SSH key at `~/.ssh/ansible_key` — remote user `ansible` with passwordless sudo
- Proxmox nodes must have `/etc/example-music/nodeinfo.json` present with `"role": "proxmox"` (written by `first-boot.sh`)

---

*Example Music Limited — Internal Infrastructure*
*Do not distribute outside the organisation*

# Related Projects & Ecosystem that were created, updated or paid forward by this work

## Spin-offs from This Repository

| Repository | Description | Why is it named "Projectname"? | Reason for Name | 
|---|---|---|---|
| [Spejder](https://github.com/knightmare2600/Spejder)  | Spejder — Hardware Provisioning Runtime | Spejder (Danish: scout/ranger) — sent ahead to gather intelligence and report back. |A minimal, stateless, multi-architecture provisioning runtime built on Debian. Boots via iPXE, collects hardware inventory, and uploads it to a deployment share. No persistent storage. No installer. No nonsense. ISOs also avilable. |
| [Fyrtaarn](https://github.com/knightmare2600/fyrtaarn) | Nordic Out-of-Band Management for IPMI, BMC, iLO, DRAC, and friends. | "Fyrtaarn" is Danish for: lighthouse / beacon / watchtower | The name reflects the project's purpose: visibility, remote control, and infrastructure oversight — without tying the project to a single vendor. |
| [pe_tools](https://github.com/knightmare2600/pe_tools) | Tools to help when using WinPE images on x86_64 and arm64 windows | Windows Pre-install Envrionment tools | They have to be self contained/mininmal by design | 
| [example_music_infra](https://github.com/knightmare2600/example_music_infra) | This repo | A repo that helps you get going if you want an entire AD environment using the JUKEBOX Domain with various bands as the "branch offices" and "AD users" | Warning: Some jokes are part of the fun, for example, [Ian Hislop](https://en.wikipedia.org/wiki/Ian_Hislop)'s "office" is The Old Bailey in London. [Kate Aide](https://en.wikipedia.org/wiki/Kate_Adie) is a VPN user in Beruit with a PSION (no politics here, just some old school humour). There's other such Easter Eggs & amusements inside the code and AD data. |
| [wintools/pwsh](https://github.com/knightmare2600/wintools/tree/master/pwsh) | Windows TUI scripts in Powershell | TUI PowerShell Helpers | Designed to defang the "fear" of PowerShell til Nutidens Unge. Hello Paige, Ellen and Ollie! |

## Recently Updated

| Repository | Description |
|---|---|
| [zabbix_templates](https://github.com/knightmare2600/zabbix_templates) | FLOSS'd Proxmox VE templates for detecting VM snapshots and incorrect zpool locations. If you were using the VMware equivalents, this is the migration path. |
| [dotfiles](https://github.com/knightmare2600/dotfiles) | A heavily customised Zsh setup, plus a long-overdue fix to get Midnight Commander to properly honour the Solarized Dark colour scheme. |

## Porting Work

Native ARM64 binaries for tools that either lacked them entirely or only offered x86 builds. All ports listed below — I didn't write the originals.

| Repository | Description |
|---|---|
| [dua-cli](https://github.com/knightmare2600/dua-cli) | Additional ARM64 ports of this disk usage analyser |
| [jq](https://github.com/knightmare2600/jq) | Native ARM64 binary for the indispensable JSON processor |
| [NTop](https://github.com/knightmare2600/NTop) | Native ARM64 binaries for the `ntop` network monitor |
| [ColorEcho](https://github.com/knightmare2600/ColorEcho) | ARM64 port of `colorecho`; patches submitted and merged upstream |
| [proxmoxbmc](https://github.com/knightmare2600/proxmoxbmc) | Fork adding Debian `.deb` packaging, which was conspicuously absent |
| [ScreenRes](https://github.com/knightmare2600/ScreenRes) | WinPE native ARM64 binary — handy when travelling with an M1 MacBook |

## Silly Season

Because the pointy wee guy with heating problems downstairs (the devil) makes work for idle hands, and the motto of [my town](https://en.wikipedia.org/wiki/List_of_mottos) is:

> *"Touch 'Ane, Touch 'Aw – Better meddle wi the De'il than the bairns o' Fawkirk (Strike one, strike all – easier to pick a fight with the devil, than the children of Falkirk)"*

### [putty-win32s](https://github.com/knightmare2600/putty-win32s)
`psftp` made to behave more like WinSCP — but for Windows 3.11. Why? My first OS was Windows for Workgroups 3.11, I had a soft spot for this chap's work, and that was reason enough.

### [ÆldreC2](https://github.com/knightmare2600/aeldreC2)
Yes, really. A fully functional retro Command & Control framework targeting Windows 3.1x and Win32s, because apparently the pointy wee guy with heating problems (devil) finds work for idle hands.

Built on top of the PuTTY-Win32s codebase and lovingly themed around *WarGames* and *Tron*, it includes:

- **Joshua** — MDI C2 controller (*"Shall we play a game?"*)
- **Tank** — Win32s and Win16 connect-back implants
- **CLU** — implant generator and binary patcher
- **Grid** — TCP subnet scanner for Win32s/WFW 3.11
- **markuped** — a fully working split-pane Markdown editor with live preview
- **wget** — HTTP/HTTPS/FTP downloader, Win32s and Win16 builds
- **ipcalc** — subnet calculator, Win32 and Win16 builds

Pre-built binaries for all of the above can be found in the [pages README](https://github.com/knightmare2600/aeldreC2/blob/main/README.md).

---

> **NB:** I follow [Janteloven](https://en.wikipedia.org/wiki/Law_of_Jante). This repository — and everything linked from it — is not intended as peacocking or a conspicuous display of IT prowess. It's simply a *"hey, I hope this helps, en tusind tak"* kind of thing. If you want to see me show off, come to a Falkirk or Odense Boldklub match.
