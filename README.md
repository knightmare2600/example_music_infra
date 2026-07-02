# Example Music Infra

Infrastructure as Code repository for Example Music Limited.

This repository contains everything needed to take a site from bare metal to production — from bootstrapping the first device on an empty network through to Ansible-managed configuration and operational runbooks.

---

## Repository Structure

```
example_music_infra/
├── ansible/          # Playbooks, inventory, group_vars, host_vars
├── benarbejdet/      # Legwork in advance — shared data files (sites.csv, devices.csv)
├── bootstrap/        # Day-zero site bootstrap toolkit
├── docs/             # Operational documentation and runbooks
├── hardware/         # Hardware reference documents
└── .githooks/        # Pre-commit hooks — see One-time setup below
```

### One-time setup (per clone)

```bash
git config core.hooksPath .githooks
```

This enables the pre-commit hook that enforces sync between `benarbejdet/` and `bootstrap/web/proxmox/` for `sites.csv` and `devices.csv`. Without it, the hook does not fire and the copies can drift.

---

## benarbejdet/

*Benarbejdet* — Danish: the legwork done in advance.

Shared data files referenced from multiple parts of the repo. Single edit point for anything that needs to be consistent across Ansible, bootstrap, and documentation.

| File | Description |
|------|-------------|
| `sites.csv` | Authoritative site registry — every site code, subnet, gateway, city, timezone and legal entity |
| `devices.csv` | Authoritative device inventory — every hostname, IP octet, role and OS across the estate |

Both files also live in `bootstrap/web/proxmox/` where the preseed web server serves them during bare-metal installs. The two copies **MUST** stay identical. The `.githooks/pre-commit` hook enforces this — if the copies differ at commit time, it shows a diff and blocks until you resolve it.

These are the **Known source of truth** (0xDF). If any other source disagrees with these files, the other source is wrong.

---

## bootstrap/

Day-zero toolkit for new site deployments. This is what goes on the technician's USB drive or laptop when they walk into an empty server room.

The bootstrap network is always `192.168.139.0/24`. The bootstrap server runs at `192.168.139.50` and provides DHCP, TFTP, HTTP and DNS for the provisioning subnet during deployment.

**Contents:**

- Custom iPXE ISO and `.lkrn` binary — chainloads into the boot menu from any machine that can PXE boot, pointed at `192.168.139.50`
- iPXE boot menu — presents install options for Proxmox VE and other supported targets
- `static-web-server.exe` — portable HTTP server, no install required, serves the bootstrap content from a Windows laptop if needed
- Proxmox answer files:
  - `answer.toml` — standard two-disk ZFS RAID1 install
  - `degraded.toml` — single-disk ZFS RAID0 install for when the second disk hasn't arrived yet
- `first-boot.sh` — post-install provisioning script, runs on first boot, configures hostname, networking, DNS, packages and raises a single-disk warning if RAID1 is not yet in place
- `ansibleme.sh` — provisions the Ansible control node (`EXAANSCLD001`) from scratch — installs packages, deploys keys, clones the repo, places `sites.csv` and `devices.csv` at `/etc/example-music/`
- `firewallme.sh` — interactive firewall bootstrap script, handles WireGuard key generation, site code lookup and peer configuration

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
2026-06-12 09:25:21 INFO server: http1 server is listening on http://192.168.139.50:80
```

3. PXE boot target machine — it will chainload the iPXE menu from `192.168.139.50`

4. Select install target (Proxmox VE RAID1 or degraded single-disk)

5. Unattended install completes, node reboots

6. `first-boot.sh` runs, configures the node, sets persistent DNS via `pvesh`

7. If single-disk: operator is prompted to acknowledge the no-redundancy warning before proceeding

8. Hand off to Ansible for full configuration

---

## ansible/

Ansible playbooks for post-bootstrap configuration and ongoing management. Run all commands from the `ansible/` directory.

```
ansible/
├── ansible.cfg
├── callback_plugins/        # Custom output formatting (exa_pretty.py)
├── configs/
│   └── inventory/           # Static inventory — all sites and nodes
├── files/                   # Static files deployed by playbooks (sudoer_ansible etc.)
├── group_vars/              # Per-group variable files
│   ├── all/                 # common_packages, ansible_user
│   ├── firewalls/
│   ├── linux/
│   ├── pvenodes/
│   ├── rudder_servers/
│   ├── windows/
│   ├── windows_dc/
│   └── ...
├── handlers/
├── host_vars/               # Per-host overrides
├── playbooks/
│   ├── bind9/               # BIND9 DNS zone generation from devices.csv
│   ├── firewallme/          # Firewall bootstrap (wraps firewallme.sh)
│   ├── linux/               # Common Linux tooling — packages, /etc/example-music deploy
│   ├── proxmox/             # Proxmox VE onboarding (pve_onboard.yml)
│   ├── rudder/              # Rudder configuration management server
│   ├── windows_adschema/    # AD schema, OUs, groups, computers, users
│   ├── windows_bootstrap/   # Windows host PostOOBE bootstrap (replaces Join-DomainAndBootstrap.ps1)
│   └── windows_dc/          # Domain controller promotion
└── vars/
```

**Key playbooks:**

| Playbook | Purpose |
|----------|---------|
| `linux/tools.yml` | Deploy common packages and `/etc/example-music/{sites,devices}.csv` to all Linux hosts |
| `bind9/bind9-dns.yml` | Generate and deploy BIND9 zones from `devices.csv` |
| `proxmox/pve_onboard.yml` | Onboard a new Proxmox VE node — Zabbix, packages, SSH, sudoers |
| `windows_bootstrap/site.yml` | Full Windows host PostOOBE bootstrap — rename, static IP, domain join, packages, wallpaper |
| `windows_dc/site.yml` | Promote a Windows Server to domain controller |
| `windows_adschema/ad_schema.yml` | Create AD OUs, groups, computers and users from TDF data |

---

## docs/

Operational runbooks and deployment procedures. See `docs/INDEX.md` for the full document registry.

```
docs/
├── INDEX.md                        # Full document index and ID registry
├── ExampleMusic_Beginners_Guide.md # Start here — estate overview, conventions, architecture
├── network-inventory.md            # Full global device register
├── site-inventory.md               # Per-site commissioning checklists
├── ExampleMusic_Procedure_Template.md
└── ...                             # Buildsheets, runbooks, proxmox, wireguard guides
```

---

## Conventions

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **RECOMMENDED**, and **OPTIONAL** in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174).

**SHOULD and SHOULD NOT are ambiguous and MUST NOT be used in this repository.**

### Addressing

Unless explicitly stated otherwise, all deployments MUST conform to these conventions:

| Offset | Role |
|--------|------|
| `.1` | RTR — upstream / ISP gateway |
| `.2–.4` | BMC / RAC — iDRAC, iLO, Redfish |
| `.5–.7` | PVE — Proxmox VE nodes |
| `.10–.11` | DCS — Domain Controllers |
| `.15` | PRV — provisioning server |
| `.48` | SBC — VOIP SBC |
| `.100–.249` | DHCP pool |
| `.250–.252` | SWI — switches |
| `.253` | FWL — firewall LAN face / site gateway |

The authoritative source for site subnet allocations is `benarbejdet/sites.csv` (and its sync copy at `bootstrap/web/proxmox/sites.csv`). If any other source disagrees, `sites.csv` wins.

### Naming

Format: `EXA` + `<ROLE>` + `<SITE>` + `<NNN>`

Example: `EXAFWLFAL001` — EXA estate, firewall, Falkirk, first unit.

### WireGuard

WireGuard networks use `10.0.<site-octet>.0/24`. The firewall WireGuard endpoint is always `.1`. CLD is the **sole WireGuard hub** — every site connects directly to CLD. No site intermediates WireGuard traffic for another.

---

## CLD Special Case

CLD (Edinburgh, OVH Pulseant datacentre) is the sole special-case deployment. It hosts shared infrastructure consumed by all sites and intentionally differs from the standard site model in several respects.

Automation MUST assume standard site conventions by default. Automation MUST NOT assume CLD conforms to standard branch architecture. CLD-specific logic MUST remain isolated from standard site logic.

CLD has two networks, each with its own site code in `sites.csv`:

| Site code | Network | Range | Gateway |
|-----------|---------|-------|---------|
| `CLD` | LAN | `192.168.69.0/24` | `192.168.69.253` |
| `VRK` | OVH vRACK | `192.168.139.0/24` | `192.168.139.254` |

The vRACK (`VRK`) is an OVH product providing 256 statically routed IPs. Treat them as real-world IPs operationally — they are routed across OVH's infrastructure to site FWL WAN interfaces. Technically RFC 1918, operationally not.

### CLD Hosts

**vRACK (`192.168.139.0/24` — site code `VRK`):**

| IP | Hostname | Role |
|----|----------|------|
| `192.168.139.8` | `EXADNSCLD001` | BIND9 — authoritative DNS for `jukebox.internal` |
| `192.168.139.50` | `EXAPRVCLD001` | Provisioning / PXE server |
| `192.168.139.68` | `EXAFWLCLD001` (WAN) | Firewall WAN face — LAN face at `192.168.69.253` |
| `192.168.139.254` | — | vRACK gateway (OVH infrastructure, not a site device) |

**LAN (`192.168.69.0/24` — site code `CLD`):**

| IP | Hostname | Role |
|----|----------|------|
| `192.168.69.9` | `EXAANSCLD001` | Ansible control node |
| `192.168.69.10` | `EXADCSCLD001` | Domain Controller — primary, forest root |
| `192.168.69.11` | `EXADCSCLD002` | Domain Controller — secondary |
| `192.168.69.12` | `EXARDRCLD001` | Rudder configuration management |
| `192.168.69.20` | `EXASVRCLD002` | Windows Admin Centre |
| `192.168.69.48` | `EXACLDPBX001` | Central 3CX PBX — all site SBCs trunk here |
| `192.168.69.253` | `EXAFWLCLD001` (LAN) | Firewall LAN face / gateway — WAN face at `192.168.139.68` |

For full architectural details see `docs/ExampleMusic_Beginners_Guide.md` (NET-BEGIN-001).

---

## Requirements

- Ansible 2.14+
- Python 3.10+
- `community.general` and `community.windows` Ansible collections
- SSH key at `~/ansible/configs/ansible-id_rsa` — remote user `ansible` with passwordless sudo
- Proxmox nodes must have `/etc/example-music/nodeinfo.json` present with `"role": "proxmox"` (written by `first-boot.sh`)
- Linux hosts must have `/etc/example-music/sites.csv` and `/etc/example-music/devices.csv` — deployed by `linux/tools.yml`

---

# Related Projects & Ecosystem that were created, updated or paid forward by this work

## Spin-offs from This Repository

| Repository | Description | Why is it named "Projectname"? | Reason for Name |
|---|---|---|---|
| [Spejder](https://github.com/knightmare2600/Spejder) | Spejder — Hardware Provisioning Runtime | Spejder (Danish: scout/ranger) — sent ahead to gather intelligence and report back. | A minimal, stateless, multi-architecture provisioning runtime built on Debian. Boots via iPXE, collects hardware inventory, and uploads it to a deployment share. No persistent storage. No installer. No nonsense. ISOs also available. |
| [Fyrtaarn](https://github.com/knightmare2600/fyrtaarn) | Nordic Out-of-Band Management for IPMI, BMC, iLO, DRAC, and friends. | "Fyrtaarn" is Danish for: lighthouse / beacon / watchtower | The name reflects the project's purpose: visibility, remote control, and infrastructure oversight — without tying the project to a single vendor. |
| [pe_tools](https://github.com/knightmare2600/pe_tools) | Tools to help when using WinPE images on x86_64 and arm64 windows | Windows Pre-install Environment tools | They have to be self contained/minimal by design |
| [example_music_infra](https://github.com/knightmare2600/example_music_infra) | This repo | A repo that helps you get going if you want an entire AD environment using the JUKEBOX Domain with various bands as the "branch offices" and "AD users" | Warning: Some jokes are part of the fun, for example, [Ian Hislop](https://en.wikipedia.org/wiki/Ian_Hislop)'s "office" is The Old Bailey in London. [Kate Adie](https://en.wikipedia.org/wiki/Kate_Adie) is a VPN user in Beirut with a PSION (no politics here, just some old school humour). There's other such Easter Eggs & amusements inside the code and AD data. |
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
