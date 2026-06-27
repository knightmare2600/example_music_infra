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

---

## Standard IP Convention

Every site follows this addressing scheme within its `/24` subnet.
Exceptions are noted in individual site entries.

| Address       | Role                                                         | Hostname pattern                      |
| ------------- | ------------------------------------------------------------ | ------------------------------------- |
| `.1`          | Primary internet gateway                                     | `EXAFWL<SITE>001` / `EXARTR<SITE>001` |
| `.2`          | BMC pool slot 1 — DRAC / iLO                                 | `EXARAC<SITE>001`                     |
| `.3`          | BMC pool slot 2 — or RAC emulator VM on single-PVE-node sites | `EXARAC<SITE>002`                     |
| `.4`          | BMC pool slot 3 — or RAC emulator VM on two-PVE-node sites   | `EXARAC<SITE>003`                     |
| `.5`          | PVE node 1                                                   | `EXAPVE<SITE>001`                     |
| `.6`          | PVE node 2                                                   | `EXAPVE<SITE>002`                     |
| `.7`          | PVE node 3                                                   | `EXAPVE<SITE>003`                     |
| `.10`         | Domain Controller — primary                                  | `EXADCS<SITE>001`                     |
| `.11`         | Domain Controller — secondary                                | `EXADCS<SITE>002`                     |
| `.48`         | VOIP SBC — trunks to `EXACLDPBX001`                          | `EXASBC<SITE>001`                     |
| `.100`–`.249` | DHCP pool                                                    | —                                     |
| `.250`–`.252` | RT switches                                                  | `EXASWI<SITE>001`–`003`               |
| `.253`        | Secondary internet gateway                                   | —                                     |

> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM. Physical PVE node BMCs consume from `.2` upward; the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.
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

### 1.2 Additional IP — EXAFWLCLD001 WAN

OVH allows the purchase of additional IPs that can be assigned to VMs via MAC virtualisation. One additional IP was purchased for the firewall VM:

| Property | Value |
|---|---|
| VM Hostname | `EXAFWLCLD001` |
| FQDN | `exafwlcld001.example.com` |
| WAN IP (OVH additional IP) | `192.0.8.131` |
| WAN Gateway | `192.0.8.254` |
| LAN interface | `192.168.139.253/24` |
| Role | Firewall/gateway for the `192.168.139.0/24` provisioning subnet |
| MAC Address | `00:50:00:C0:FF:EE` (OVH will require you ot set the MAC they provide) |

`EXAFWLCLD001` is a VM running on `EXAPVECLD001`. Its WAN interface uses the additional OVH IP (`192.0.8.131`) with a virtual MAC assigned in the OVH control panel — this is required for OVH's network to route the additional IP to the VM rather than the host. The LAN interface (`192.168.139.253`) is the default gateway for the entire `192.168.139.0/24` provisioning subnet.

EXAFWLCLD001 runs **dnsmasq** on the LAN interface, providing both DHCP and DNS for `192.168.139.0/24`. It also handles DNS for `jukebox.internal` internally.

**Firewall rules on EXAFWLCLD001:** Inbound access to the provisioning network from site WAN IPs is permitted, but each site is restricted to a `/32` — i.e. the single known public IP of each site (FAL, BRK, ODE, and all other commissioned sites). No wider ranges are permitted inbound.

### 1.3 Temporary Bootstrapping Node — EXASTRPCLD001

> 🇩🇰 **This node does not follow the EXA naming convention. The non-standard name is intentional — it is a deliberate red flag that this machine is temporary and must be decommissioned.**

| Property | Value |
|---|---|
| Hostname | `EXASTRPCLD001` |
| IP | `192.168.139.50` (static) |
| OS | Windows 11 (minimal install) |
| Role | Temporary HTTP provisioning server — serves `web/` |

This is a VM on `EXAPVECLD001`, sitting behind `EXAFWLCLD001` on `192.168.139.0/24`. It runs `static-web-server.exe` serving the `web/` directory tree. It exists purely because it was the fastest way to stand up an HTTP server at the start of the project. You may use `Python3 -m http.server` too

**This node must be migrated to EXAANSCLD001 (the Ansible node) once that VM is commissioned.** At that point `EXASTRPCLD001` will be shut down and destroyed. The IP `192.168.139.50` is the address hardcoded throughout all provisioning scripts and Proxmox TOML files — when migrating, either assign `192.168.139.50` to EXAANSCLD001 or update every reference (see §8).

### 1.4 Domain Registration and Public DNS

Two domains are registered for the estate:

| Domain | Use |
|---|---|
| `example.com` | Primary public domain — AD forest root is `jukebox.internal` (internal); `example.com` is used for public-facing DNS records |
| `example.net` | Secondary domain — used for the majority of child AD domains across sites |

The following public DNS records exist:

| Record | Type | Value | Notes |
|---|---|---|---|
| `exapvecld001.example.com` | A | `192.0.8.86` | Proxmox host — web UI, SSH |
| `exafwlcld001.example.com` | A | `192.0.8.131` | Firewall WAN IP |
| `ansible.jukebox.internal` | A | `192.0.8.131` | Primary provisioning server name — resolves to EXAFWLCLD001's WAN IP (port-forwarded through to `192.168.139.50`) |
| `ansible.example.com` | CNAME | `ansible.jukebox.internal` | Alias |
| `www.jukebox.internal` | CNAME | `ansible.jukebox.internal` | Fallback used by `bootstrap.ipxe` |

The `ansible.jukebox.internal` A record is the one that matters for iPXE boot. The embedded `bootstrap.ipxe` script tries hostnames in this order: `ansible.jukebox.internal` → `www.jukebox.internal` → direct IP `192.168.139.50`. The CNAME aliases mean all three resolve correctly as long as public DNS is functioning.

Port forwarding on EXAFWLCLD001 forwards inbound HTTP (port `80/TCP`) on `192.0.8.131` through to `192.168.139.50` (EXASTRPCLD001, or EXAANSCLD001 once migrated).

### 1.5 Network topology summary

```
Internet
    │
    │  192.0.8.86 (EXAPVECLD001 — Proxmox host, OVH Edinburgh)
    │
    ├─ VM: EXAFWLCLD001
    │       WAN: 192.0.8.131 (OVH additional IP, gw 192.0.8.254)
    │       LAN: 192.168.139.253/24
    │       Runs: dnsmasq, DHCP, firewall, WireGuard hub (CLD spoke)
    │
    └─ 192.168.139.0/24  (provisioning / CLD LAN)
            │
            ├─ 192.168.139.50   EXASTRPCLD001 (temp bootstrap — Windows 11)  ⚠ temporary
            ├─ 192.168.139.48   PBX (per-site convention)
            ├─ 192.168.139.253  EXAFWLCLD001 LAN
            └─ ...              Future VMs (EXAANSCLD001, EXADCSCLD001, etc.)

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
Internet → ansible.jukebox.internal (192.0.8.131, EXAFWLCLD001)
               └─ port 80 forwarded to 192.168.139.50 (EXASTRPCLD001)
                    └─ static-web-server serving web/
                         └─ iPXE boot (embedded bootstrap.ipxe → chains to .ipxe menu)
                              ├─ Proxmox VE auto-install (answer.toml / degraded.toml)
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

The provisioning pipeline is driven by an HTTP server serving the `web/` directory tree. In production this runs permanently on EXASTRPCLD001. For field use from a laptop, use `static-web-server.exe`:

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

### 2.3 Building the `web/` directory tree

The following structure must exist before the server starts. Create it with:

**Windows (PowerShell):**
```powershell
mkdir -Force web/proxmox/boot,web/debian,web/gparted,web/phoenixpe,web/arch,web/autodeploy
```

**Linux / macOS:**
```bash
mkdir -p web/proxmox/boot web/debian web/gparted web/phoenixpe web/arch web/autodeploy
```

Minimum required files and where they come from:

```cmd
web/
├── menu.ipxe                    ← boot menu (served as /menu.ipxe — see §3.2)
├── lvm.seed                     ← Debian preseed file
├── late_command.sh              ← Debian post-install hook
├── ansible_sshkey.pub           ← Ansible user public key
├── convert-v2v.py               ← V2V migration script
├── create-vm.py                 ← VM creation script
├── manage-pool.py               ← Pool management script
├── PostOOBE.cmd                 ← Windows post-OOBE bootstrap launcher
├── Join-DomainAndBootstrap.ps1  ← Windows domain join + software install
├── qemu-ga-x86_64.msi           ← QEMU guest agent MSI (offline fallback)
├── virtio-win-gt-x64.msi        ← VirtIO guest tools MSI (offline fallback)
│
├── proxmox/
│   ├── answer.toml              ← PVE auto-install: ZFS RAID-1 (2 disks)
│   ├── degraded.toml            ← PVE auto-install: ZFS RAID-0 (1 disk, degraded mirror)
│   ├── first-boot.sh            ← PVE post-install provisioning script
│   └── boot/
│       ├── linux26              ← Proxmox VE installer kernel
│       └── initrd               ← Proxmox VE installer initrd
│
├── debian/
│   ├── linux                    ← Debian netboot kernel (from netboot.tar.gz)
│   └── initrd.gz                ← Debian netboot initrd
│
├── gparted/
│   ├── vmlinuz
│   ├── initrd.img
│   └── filesystem.squashfs
│
└── phoenixpe/
    ├── wimboot
    ├── bootmgr.exe
    ├── boot.sdi
    └── Boot.wim
```

#### Proxmox VE boot files

Extract the kernel and initrd from the Proxmox VE ISO:

```bash
# Mount the ISO (Linux)
mount -o loop proxmox-ve_9.1-1.iso /mnt/iso

# Copy boot files
cp /mnt/iso/boot/linux26 web/proxmox/boot/
cp /mnt/iso/boot/initrd  web/proxmox/boot/

umount /mnt/iso
```

On Windows, use 7-Zip to open the ISO and extract `boot/linux26` and `boot/initrd`.

#### Debian netboot files

The `debian/` subdirectory uses the Trixi netboot image (not the full ISO). Download the netboot tarball for your Debian version:

```bash
# Debian 12 (Bookworm) example
wget https://deb.debian.org/debian/dists/bookworm/main/installer-amd64/current/images/netboot/netboot.tar.gz
tar xf netboot.tar.gz ./debian-installer/amd64/linux ./debian-installer/amd64/initrd.gz
cp debian-installer/amd64/linux   web/debian/
cp debian-installer/amd64/initrd.gz web/debian/
```

These are small (~50 MB combined). The installer fetches everything else from the network during install.

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
│   ├── EXASTRPCLD001 — root (Proxmox provisioning node)
│   ├── PVE root password (answer.toml hash source)
│   └── Ansible user password (per-node if not key-only)
│
├── Active Directory
│   ├── JUKEBOX\Administrator (forest DA)
│   ├── DEPLOYTOOLS_PASS (used by PostOOBE.cmd)
│   └── Per-domain DA accounts (example.net, example.org, example.com)
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
│   ├── ABR (Aberdeen, UK)
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

The `answer.toml` and `degraded.toml` files contain a pre-hashed root password. To generate a new one:

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

There are two iPXE script files:

| File | Role |
|---|---|
| `bootstrap.ipxe` | **Embedded** into the compiled iPXE ISO/USB/ROM. Runs before any network is configured. Does DHCP, then chains to the boot menu. |
| `web/.ipxe` (served as `/menu.ipxe`) | **Remote** boot menu. Served by the HTTP server. Contains all OS installer entries. |

The flow is: BIOS/UEFI boots iPXE ISO → `bootstrap.ipxe` runs → DHCP → chains to `http://192.168.139.50/menu.ipxe` → operator selects OS.

### 4.2 The `.ipxe` filename and URL mapping

The menu file is stored on disk as `web/.ipxe` (dotfile, hidden on Unix). The HTTP server serves it at the path configured in `bootstrap.ipxe`:

```
set boot-path  /menu.ipxe
```

When using `static-web-server`, the dotfile is served normally. With `python3 -m http.server` you may need to rename it to `menu.ipxe` if the server refuses to serve dotfiles.

### 4.3 Embedded bootstrap (`bootstrap.ipxe`)

This script is compiled into the iPXE binary. Key configuration at the top:

```ipxe
set boot-domain   jukebox.internal
set boot-ansible  ansible.${boot-domain}
set boot-www      www.${boot-domain}
set boot-ip       192.168.139.50          ← update to real provisioning IP if needed
set boot-path     /menu.ipxe
```

**Boot server resolution order:** The script tries three methods in sequence, falling back if each fails:

1. `ansible.jukebox.internal` (DNS lookup first — skips the chain timeout if DNS is broken)
2. `www.jukebox.internal`
3. Direct IP: `192.168.139.50`

If all three fail, the script drops to an iPXE shell with diagnostic instructions printed on screen.

**Ctrl-B shell escape:** There is a 5-second window at startup to press Ctrl-B and drop to an interactive iPXE shell. This is useful for diagnosing DHCP or DNS issues on a new network.

**Compiling the iPXE binary** (run on a Linux build host):

```bash
┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap]
└──╼ git clone https://github.com/ipxe/ipxe.git

┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap]
└──╼cd ipxe/src

┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap/src]
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
┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ cat config/local/console.h
#define CONSOLE_PCBIOS    /* VGA — interactive TUI */
#define CONSOLE_SERIAL    /* COM1, 115200 8n1 — for FWL/RTR/SBC VMs */

## Enable colours and extra functions
┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ cat config/local/general.h
#define CONSOLE_FRAMEBUFFER
#define PING_CMD
#define IPSTAT_CMD
#define REBOOT_CMD
#define POWEROFF_CMD
#define NSLOOKUP_CMD
#define ROUTE_CMD

┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ make bin/ipxe.iso EMBED=bootstrap.ipxe

## This is the iso you boot devices with
┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ copy bin/ipxe.iso ./ipxe.iso

## copy lkrn module too if that's what oyu want as a bootfile. It's 6 and 2x3
┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ copy bin/ipxe.lkrn.iso ./ipxe.lkrn

# ISO (for CD/CDROM/IPMI virtual media):
┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ make bin/ipxe.iso EMBED=bootstrap.ipxe

# USB image:
┌─[ansible@EXAPRVCLD001]─[C:\Users\Ansible\Desktop\Boottrap/src]
└──╼ $ make bin/ipxe.usb EMBED=bootstrap.ipxe

# PXE ROM (for DHCP/TFTP environments):
make bin/undionly.kpxe EMBED=bootstrap.ipxe
```

Pre-built binaries for common configurations are in `x86_64/ipxe.iso` and `arm64/ipxe.iso` in the repository.

### 4.4 Boot menu (`.ipxe`)

The remote boot menu offers the following entries:

```
INSTALLERS
  Debian  - Automated Install
  Debian  - Install (SSH console)
  Debian  - Automated Install (serial ttyS0)
  Debian  - SSH Install (serial ttyS0)
  Arch Linux Install
  Proxmox VE 9 (Hypervisor)
  Proxmox DCM 9 (Datacentre Manager)      ← not yet configured

UTILITIES
  GParted Live
  PhoenixPE Environment
  Hardware Detection Tool

SYSTEM
  iPXE shell / Reboot / Shutdown
```

The default selection is **Boot from local disk**, with a 30-second timeout. This means a machine that accidentally PXE-boots will fall through to its local OS without intervention.

**MAC-based auto-deploy:** Before showing the menu, the script attempts to chain to `http://192.168.139.50/autodeploy/<mac-address>.ipxe`. If a file exists for that MAC, it runs instead of the menu, enabling fully automated zero-touch deployment. If the file does not exist, the chain fails silently and the menu appears. Create per-MAC scripts in `web/autodeploy/` using the hyphenated MAC format (e.g. `aa-bb-cc-dd-ee-ff.ipxe`).

**Serial console variants:** The serial entries add `console=ttyS0,115200n8` (and `console=tty0` for the SSH variant to keep both consoles active). Use these for headless servers accessed via IPMI serial-over-LAN.

### 4.5 Proxmox VE boot entry

```ipxe
:proxmox-ve
kernel ${boot-url}/proxmox/boot/linux26 vga=791 video=vesafb:ywrap,mtrr ramdisk_size=16777216 proxmox-start-auto-installer=1 \
proxmox-auto-install-mode=http proxmox-auto-install-url=${boot-url}/proxmox/answer.toml
initrd ${boot-url}/proxmox/boot/initrd
boot
```

This always pulls `answer.toml`. To do a **manual interactive install** instead, edit the menu file and swap in the commented-out manual block (present in `web/.ipxe`):

```ipxe
# PROXMOX VE — MANUAL INSTALL (uncomment to use)
# :proxmox-ve
# kernel ${boot-url}/proxmox/boot/linux26 vga=791 video=vesafb:ywrap,mtrr ramdisk_size=16777216
# initrd ${boot-url}/proxmox/boot/initrd
# boot
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

### 5.1 answer.toml — normal install (ZFS RAID-1)

Use this when both disks are present.

```toml
[global]
keyboard = "en-gb"
country = "gb"
fqdn = "pve-install.jukebox.internal"
mailto = "root@jukebox.internal"
timezone = "Europe/London"
root-password-hashed = "$6$..."        ← see §2.2

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

The `fqdn` here is a placeholder used during install only. `first-boot.sh` will rename the node to its real hostname.

### 5.2 degraded.toml — single-disk install

Use when a replacement disk hasn't arrived yet. Creates a ZFS mirror with only one disk (degraded state). The second disk can be added later with `zpool attach`.

```toml
[disk-setup]
filesystem = "zfs"
zfs.raid = "raid0"          ← single-disk, equivalent to degraded mirror
disk-list = ["sda"]
```

Everything else is identical to `answer.toml`.

<u>***NB: Warning! A single-disk ZFS pool has no redundancy. Add the second disk and run `zpool attach rpool sda sdb` before putting workloads on the node***</u>. This is covered in it's onw procedure in this repo!

### 5.3 Switching between TOML files

The iPXE menu always references `answer.toml`. To use `degraded.toml` for a specific install, either:

- Temporarily rename `degraded.toml` to `answer.toml` on the server before booting, or
- Edit the iPXE menu entry's `proxmox-auto-install-url` parameter at boot time by pressing Ctrl-B, or
- Create a MAC-specific autodeploy script that overrides the URL.

### 5.4 What happens after the installer finishes

The `[first-boot]` section in both TOML files instructs the Proxmox installer to fetch and run `first-boot.sh` once the node is up. The `ordering = "fully-up"` setting means the script runs only after the network is fully online — important since it downloads packages.

See §5 for full details of what `first-boot.sh` does.

---

## 6. Proxmox Node Post-Install: first-boot.sh

The `first-boot.sh` is fetched and executed automatically by the PVE installer as configured in `[first-boot]`. It is idempotent and safe to re-run.

### 6.1 What it does (in order)

**Step 1 — APT repositories**

Disables the Proxmox enterprise repository (requires a subscription) and adds the no-subscription community repository. Removes the subscription nag from the web UI.

**Step 2 — Node identity**

Prompts interactively for:
- Site code (e.g. `FAL`, `ODE`, `BRK`)
- Hostname (becomes `EXAPVExxx001` per naming convention)
- IP address (with collision detection via `arping`)
- Gateway

> If running unattended from a fully automated pipeline, pre-seed these values by setting environment variables before invoking the script — see the script header for variable names.

**Step 3 — Core package installation**

Installs: `openssh-server`, `sudo`, `net-tools`, `molly-guard`, `arping`, `nmap`, `python3-proxmoxer`, `zsh`, `zsh-autosuggestions`, `zsh-syntax-highlighting`, and other required packages.

If the node is itself a VMware guest (detected via `systemd-detect-virt`), VMware Tools are also installed — this applies during the migration period when some PVE nodes may themselves run inside VMware.

**Step 3b — virt-v2v Windows prerequisites**

Installs `rpm2cpio` and `cpio`, then downloads and extracts `pvvxsvc.exe` / `rhsrvany.exe` from a Fedora Koji RPM into `/usr/share/virt-tools/`. These are required by `virt-v2v` for converting Windows VMs — without them, conversion of Windows guests will fail.

```bash
wget -O /tmp/srvany.rpm https://kojipkgs.fedoraproject.org//packages/mingw-srvany/1.1/4.fc38/noarch/mingw32-srvany-1.1-4.fc38.noarch.rpm
wget -O /tmp/vmdp.iso https://github.com/SUSE/vmdp/releases/download/v2.5.5.1/VMDP-WIN-2.5.5.1-Community.iso
rpm2cpio /tmp/srvany.rpm | cpio -idmv

mkdir -p /usr/share/virt-tools
mv ./usr/i686-w64-mingw32/sys-root/mingw/bin/*.exe /usr/share/virt-tools/
mv /tmp/pvvxsvc.rpm
```

**Step 3c — VirtIO driver extraction**

Downloads `virtio-win.iso` (~500 MB) to `/var/lib/vz/template/iso/virtio-win.iso` (Proxmox's ISO store, making it available for VM CDROM attachment via the web UI). Then extracts the ISO contents to `/usr/share/virtio-win/` using `p7zip-full`.

This step is idempotent — if the extraction directory already exists and contains the expected subdirectories (`vioscsi`, `NetKVM`, `balloon`, `viostor`), it is skipped.

The extracted drivers are used by `convert-v2v.py` to inject VirtIO drivers during Windows VM conversion, allowing converted VMs to boot with VirtIO storage and networking rather than falling back to emulated IDE/RTL8139.

**Step 4 — Ansible user**

Creates the `ansible` service account with:
- Password set (prompted, or pre-seeded)
- SSH public key fetched from `http://192.168.139.50/ansible_sshkey.pub`
- Full `NOPASSWD` sudo access via `/etc/sudoers.d/ansible`
- Added to the `kvm` group (required for `virt-v2v` / `libguestfs` to access KVM without root)
- zsh configured as default shell

**Step 5 — Molly-guard, MOTD, node info file**

Molly-guard is configured to prevent accidental shutdown/reboot of the wrong node over SSH. A custom MOTD is written. A node info file is written to `/etc/example-music/nodeinfo.json` — a JSON record of the build configuration that re-runs of the script and Ansible playbooks can read to detect a completed bootstrap and verify the node role.

**Step 6 — ZFS single-disk warning**

If the ZFS pool was created on a single disk (degraded install), the script prints a prominent warning and requires the operator to type `I UNDERSTAND` before continuing. This prevents single-disk nodes from being forgotten about.

**Step 7 — Node rename and network**

Renames the node from the `pve-install` placeholder to the real hostname, updates `/etc/network/interfaces` with the correct static IP, and sets DNS via `pvesh`.

```bash
┌─[ansible@exaanscld001]─[/home/ansible/bootstrap]
└──╼ $ sudo apt install wget genisoimage gzip zstd
Reading package lists... Done
: <snbip>

┌─[ansible@exaanscld001]─[/home/ansible/bootstrap]
└──╼ $ git clone https://github.com/morph027/pve-iso-2-pxe
cd pve-iso-2-pxe
Cloning into 'pve-iso-2-pxe'...
remote: Enumerating objects: 132, done.
remote: Counting objects: 100% (71/71), done.
remote: Compressing objects: 100% (54/54), done.
remote: Total 132 (delta 28), reused 43 (delta 17), pack-reused 61 (from 1)
Receiving objects: 100% (132/132), 38.45 KiB | 546.00 KiB/s, done.
Resolving deltas: 100% (45/45), done.

┌─[knightmare@ovhfwl]─[/home/knightmare/vmware/pve-iso-2-pxe]
└──╼ $ wget https://enterprise.proxmox.com/iso/proxmox-ve_9.1-1.iso
--2026-02-24 14:54:39--  https://enterprise.proxmox.com/iso/proxmox-ve_9.1-1.iso
Resolving enterprise.proxmox.com (enterprise.proxmox.com)... 185.219.221.167, 2001:41d0:b00:5900::34
Connecting to enterprise.proxmox.com (enterprise.proxmox.com)|185.219.221.167|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: 1831886848 (1.7G) [application/octet-stream]
Saving to: ‘proxmox-ve_9.1-1.iso’

proxmox-ve_9.1-1.iso       100%[===========================================================================>]   1.71G  54.4MB/s    in 44s

2026-02-24 14:55:23 (39.5 MB/s) - ‘proxmox-ve_9.1-1.iso’ saved [1831886848/1831886848]

┌─[ansible@exaanscld001]─[/home/ansible/bootstrap/pve-iso-2-pxe]
└──╼ $ sudo bash pve-iso-2-pxe.sh proxmox-ve_*.iso

#########################################################################################################
# Create PXE bootable Proxmox image including ISO                                                       #
#                                                                                                       #
# Author: mrballcb @ Proxmox Forum (06-12-2012)                                                         #
# Thread: http://forum.proxmox.com/threads/8484-Proxmox-installation-via-PXE-solution?p=55985#post55985 #
# Modified: morph027 @ Proxmox Forum (23-02-2015) to work with 3.4                                      #
#########################################################################################################

Using proxmox-ve_9.1-1.iso...
extracting kernel...
extracting initrd...
adding iso file ...
3577905 blocks
Finished! pxeboot files can be found in /home/knightmare/vmware/pve-iso-2-pxe.
┌─[ansible@exaanscld001]─[/home/ansible/bootstrap/pve-iso-2-pxe]
└──╼ $ ls
LICENSE  proxmox.iso  proxmox-ve_9.1-1.iso  pve-iso-2-pxe.sh  pxeboot  README.md
┌─[ansible@exaanscld001]─[/home/ansible/bootstrap/pve-iso-2-pxe]
└──╼ $ df -hT
Filesystem                Type   Size  Used Avail Use% Mounted on
tmpfs                     tmpfs  197M  740K  197M   1% /run
/dev/mapper/vgovhfwl-root ext4    24G   21G  2.6G  89% /
tmpfs                     tmpfs  984M     0  984M   0% /dev/shm
tmpfs                     tmpfs  5.0M     0  5.0M   0% /run/lock
/dev/sda1                 vfat   511M  4.0K  511M   1% /boot/efi
tmpfs                     tmpfs  984M     0  984M   0% /run/qemu
tmpfs                     tmpfs  197M  8.0K  197M   1% /run/user/1000
┌─[ansible@exaanscld001]─[/home/ansible/bootstrap/pve-iso-2-pxe]
└──╼ $ tree pxeboot
pxeboot
├── initrd
└── linux26

1 directory, 2 files
┌─[ansible@exaanscld001]─[/home/ansible/bootstrap/pve-iso-2-pxe]
└──╼ $ ls -lh pxeboot
total 2.1G
-rw-r--r-- 1 root root 2.1G Feb 24 14:56 initrd
-rw-r--r-- 1 root root  15M Feb 24 14:55 linux26

## Deploying

Boot → auto mode → "fails" to fetch answer
wget -O /run/automatic-installer-answers http://192.168.139.50/proxmox/answer.toml
exit
Installs perfectly
on first boot, sing in as root / P.....
bash /var/lib/proxmox-first-boot/proxmox-first-boot/

## Debugging

## Did it try to fetch the script?
journalctl -u proxmox-first-boot

## Is the script even reachable from the node?
wget -O /tmp/test.sh http://192.168.139.50/proxmox/first-boot.sh && echo "OK"

## TODO: make this backup part of script of playbook
tar czf /root/pve-host-backup-$(date +%F).tar.gz /etc/pve /etc/network/interfaces /etc/hosts /etc/fstab

## And also this database file
cp /var/lib/pve-cluster/config.db /root/pve-config-db-backup-$(date +%F).db

## Now out figure out how to restore these...?

##################### on real hardware ##############################

root@pve-install:~# bash /var/lib/proxmox-first-boot/proxmox-first-boot

  +======================================================+
  |        PROXMOX VE - NODE PROVISIONING                |
  |              jukebox.internal                        |
  +======================================================+

  ================================================
  FIXING APT REPOSITORIES
  ================================================
  [->] Disabling Proxmox enterprise repos (require paid subscription)...
  [->] Adding Proxmox no-subscription community repo...
  [+] No-subscription repo added
  [->] Running apt update...
  [+] Repositories updated

  ================================================
  NODE CONFIGURATION
  ================================================
  Known site codes:
    ABR AKL AMS BIR BON BRD BRK CLD CLY COV CPH DUN EDI FAL FAX GAA GLA GOT HAL HUL KGE KOR LAX LIV LND MCR MEL MIA MIL MTL MUN NEW NJC NYC ODE OSL PER SHE SYD VIE

  Site code (e.g. FAL, MCR, GLA): FAL
  [+] Site   : FAL -- Falkirk, Scotland
  [+] Entity : Example Music (Scotland) Ltd
  [+] Subnet : 192.168.76.0/24
  Hostname (short, e.g. EXAFALPVE001): EXAPVECLD001
  Gateway last octet (e.g. 253 -> 192.168.76.253): 1
  [+] Gateway: 192.168.76.1

  [->] Scanning 192.168.76.5-10 for available IPs...
  [+] Suggested: 192.168.76.5 (first free in .5-.10 range)
  IP Address [192.168.76.5]: 192.168.139.5
  [->] Checking 192.168.139.5 is not already in use...
  [+] 192.168.139.5 is free

  [i] Hostname : EXAPVECLD001.jukebox.internal
  [i] IP       : 192.168.139.5/24
  [i] Gateway  : 192.168.76.1
  [i] Site     : FAL -- Falkirk, Scotland
  [i] Entity   : Example Music (Scotland) Ltd

  Proceed with these settings? [y/N]: y

  ================================================
  INSTALLING PACKAGES
  ================================================
  [->] Installing core packages...
    Unpacking sudo (1.9.16p2-3) ...
    Unpacking arping (2.25-1) ...
    : <snip>
    Setting up parted (3.6-5) ...
    Setting up python3-paramiko (3.5.1-3) ...
  [+] Core packages installed
  [+] molly-guard active -- protects against accidental reboots/shutdowns
  [->] Checking hypervisor type...
  [i] Detected virtualisation: none unknown <-- Not a mistake. This is for nested virtualisaiton
  [i] Not a VMware VM (none unknown) -- skipping open-vm-tools

  ================================================
  ANSIBLE USER SETUP
  ================================================
  [->] Creating ansible user...
  [!] User ansible already exists -- updating password
  [->] Setting password...
  [+] Password set to Password1!
  [->] Fetching SSH public key...
  [+] SSH key installed
  [->] Setting permissions...
  [+] Permissions set
  [->] Configuring NOPASSWD sudo...
  /etc/sudoers.d/ansible: parsed OK
  [+] Sudoers configured
  [->] Writing .vimrc...
  [+] .vimrc written
  [->] Configuring zsh for ansible user...
  [+] zsh configured for ansible user (green prompt)
  [->] Configuring zsh for root...
  [+] zsh configured for root (red prompt)

  ================================================
  WRITING NODE INFO FILE
  ================================================
  [+] Node info written -> /etc/example-music/nodeinfo.json

  ================================================
  CONFIGURING DYNAMIC MOTD
  ================================================
  [+] MOTD written
  [+] MOTD configured -- shows on SSH login and console

  ================================================
  RENAMING NODE AND FIXING NETWORK
  ================================================
  [->] Setting /etc/hostname...
  [+] /etc/hostname -> EXAPVECLD001
  [->] Updating /etc/hosts...
  [+] /etc/hosts updated
  [->] Fixing /etc/network/interfaces...
  [+] Physical NIC: eno1
  [+] /etc/network/interfaces written (192.168.139.5/24 gw 192.168.76.1 via eno1)
  [->] Applying hostname to running system...
  [+] Hostname: EXAPVECLD001
  [->] Updating postfix...
  [+] Postfix myhostname -> EXAPVECLD001.jukebox.internal

  +======================================================+
  |  PROVISIONING COMPLETE                               |
  +======================================================+
  [+] Hostname   : EXAPVECLD001.jukebox.internal
  [+] New IP     : 192.168.139.5/24 via 192.168.76.1
  [+] Site       : FAL -- Falkirk, Scotland
  [+] Entity     : Example Music (Scotland) Ltd
  [+] ansible    : password + 0 SSH key(s)
  [+] Node info  : /etc/example-music/nodeinfo.json
  [+] molly-guard: active
  [+] Web UI     : https://192.168.139.5:8006

  +------------------------------------------------------+
  |  NETWORK MIGRATION ON REBOOT                         |
  |                                                      |
  |  Current (provisioning) : 192.168.139.2/24           |
  |  After reboot (site LAN): 192.168.139.5/24           |
  |                                                      |
  |  This SSH session will DROP on reboot.               |
  |  Reconnect on the site LAN to 192.168.139.5          |
  +------------------------------------------------------+

  +======================================================+
  |                                                      |
  |  WARNING  WARNING  WARNING  WARNING  WARNING         |
  |                                                      |
  |      THIS NODE HAS NO DISK REDUNDANCY                |
  |                                                      |
  |  Only 1 disk detected in ZFS pool rpool              |
  |  This node WILL lose ALL data if this disk fails     |
  |                                                      |
  |  When the second disk arrives:                       |
  |    Follow zfs-raid0-to-raid1.md to upgrade to        |
  |    a full RAID1 mirror before production use         |
  |                                                      |
  |  DO NOT put this node into production as-is          |
  |                                                      |
  +======================================================+

  Type 'I UNDERSTAND' to confirm you have read this warning: I UNDERSTAND
  [!] Acknowledged. Do not forget -- add the second disk before production.

  Reboot now? [y/N]: n
  [i] Skipped -- run: ifreload -a   to apply network without reboot

## Reset forgotten BMC password
root@pve-install:~# apt install ipmitool
Installing:
  ipmitool

Installing dependencies:
  freeipmi-common  libfreeipmi17  libopenipmi0t64  libsnmp-base  libsnmp40t64  openipmi

Suggested packages:
  freeipmi-tools  snmp-mibs-downloader

Summary:
  Upgrading: 0, Installing: 7, Removing: 0, Not Upgrading: 80
  Download size: 8,597 kB
  Space needed: 23.2 MB / 963 GB available

Continue? [Y/n] y
Get:1 http://deb.debian.org/debian trixie/main amd64 freeipmi-common all 1.6.15-1 [357 kB]
: <snip>
Processing triggers for libc-bin (2.41-12) ...

## Reset admin password (will _not_ echo)
root@pve-install:~# ipmitool user set password 2
Password for user 2:
Password for user 2:
Set User Password command successful (user 2)

## Reboot ofr changes ot take effect
root@pve-install:~# poweroff
W: molly-guard: SSH session detected!
Please type in hostname of the machine to poweroff: EXAPVECLD001
root@pve-install:~# Connection to 192.168.139.2 closed by remote host.
Connection to 192.168.139.2 closed.
```

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

Runs inside the Debian installer environment (busybox `sh` — no bash, no arrays, no `[[ ]]`). Uses `in-target` to run commands inside the installed system chroot.

Actions performed:

- Forces LVM modules (`dm_mod`, `dm_snapshot`, `dm_mirror`) into the initramfs and rebuilds it — required for the standard kernel to boot from LVM at first boot
- Adds `ansible` to the `sudo` group
- Installs `openssh-server sudo net-tools bash-completion` (belt-and-braces, some are already in the preseed package list)
- Creates `/home/ansible/.ssh/authorized_keys` by fetching `ansible_sshkey.pub` from the provisioning server using busybox `wget`
- Writes a `.vimrc` (ruler, dark background, syntax highlighting) to the ansible home dir
- Creates `/etc/sudoers.d/ansible` with `NOPASSWD: ALL` and validates it with `visudo -c` — removes the file and aborts if validation fails
- Sets correct ownership and permissions (`700` on `.ssh/`, `600` on `authorized_keys`) using numeric UID/GID (necessary because the script runs outside the chroot)

---

## 8. Windows VM Post-OOBE Bootstrap

This applies to new Windows VMs (or physical Windows machines) being provisioned into the domain. It is not part of the Proxmox node build — it runs inside Windows after the OS installation OOBE completes.

### 8.1 PostOOBE.cmd

`PostOOBE.cmd` is the entry point. It is placed in `C:\Windows\System32\oobe\SetupComplete.cmd` (or run manually at first logon). It:

1. Waits 12 seconds for networking to settle
2. Maps `Z:` to `\\EXADCSCPH001\DeployTools` using the forest DA credential (`JUKEBOX\Administrator` with the password from the `DEPLOYTOOLS_PASS` environment variable — set this from KeePassXC before running, or inject it via your provisioning toolchain)
3. Launches `Join-DomainAndBootstrap.ps1` from `Z:\panther\`
4. Unmaps `Z:` on exit

> **TODO:** Once all sites are commissioned, update the UNC in `PostOOBE.cmd` from `\\EXADCSCPH001\DeployTools` to `\\jukebox.internal\DeployTools` (DFS namespace).

> **Security note:** Do not hardcode the `DEPLOYTOOLS_PASS` value in the script. Set it as an environment variable at deploy time, or retrieve it from a secrets vault.

### 8.2 Join-DomainAndBootstrap.ps1

The PowerShell script runs as a 12-stage bootstrap. It must be run elevated from the mapped `DeployTools` share (the script checks its own path and aborts if run from elsewhere). A sentinel file at `C:\Windows\Temp\PostOOBE-Bootstrap.done` prevents re-running.

**Stage 1 — Hypervisor detection**

Reads `Win32_ComputerSystem.Manufacturer` to determine whether the machine is a VMware guest, Proxmox/KVM guest, or physical hardware. This controls which guest tools are installed in Stage 7.

**Stage 2 — Site detection**

Reads the local IPv4 address and matches the third octet against the `$SubnetSiteMap` table to identify the site code and suggest the correct AD domain. All 42 sites plus CLD are in the map.

**Stage 3 — Hostname and domain**

Prompts for a hostname (max 15 characters, alphanumeric + hyphens) and the target AD domain. The site-detected domain is offered as the default. Forest root (`jukebox.internal`) is explicitly rejected as a join target — only the child domains (`example.com`, `example.net`, `example.org`) are valid.

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

---

## 9. Updating the Boot Server IP

If the provisioning server IP changes from `192.168.139.50`, the following files must be updated:

| File | Variable / line to change |
|---|---|
| `bootstrap.ipxe` | `set boot-ip 192.168.139.50` |
| `web/.ipxe` | `set boot-url http://192.168.139.50` |
| `web/boot.ipxe` | `set boot-url http://192.168.139.50` |
| `web/proxmox/answer.toml` | `url = "http://192.168.139.50/proxmox/first-boot.sh"` |
| `web/proxmox/degraded.toml` | `url = "http://192.168.139.50/proxmox/first-boot.sh"` |
| `web/lvm.seed` | `wget ... http://192.168.139.50/late_command.sh` |
| `web/late_command.sh` | `SSH_KEY_URL="http://192.168.139.50/ansible_sshkey.pub"` |
| `first-boot.sh` | Any references to provisioning server URL |

After changing `bootstrap.ipxe`, the iPXE binary must be recompiled and redistributed to all IPMI virtual media mounts and USB keys.

---

## 10. Quick Reference — Deploy a New Proxmox Node

1. **Prepare** — ensure `web/` is being served from `192.168.139.50` (or the real provisioning IP)
2. **Check TOML** — use `answer.toml` if both disks are present; use `degraded.toml` if shipping delays mean only one disk is installed
3. **Boot** — attach iPXE ISO via IPMI virtual media (or physical USB), power on, select **Proxmox VE 9** from the menu
4. **Install** — fully automated; takes approximately 5–10 minutes depending on disk speed
5. **first-boot.sh** — runs automatically when the node comes up; provide hostname, IP, and site code when prompted
6. **Verify** — SSH to the node as `ansible` using the key from `ansible_sshkey.pub`; check `pvesh get /nodes` to confirm API is up
7. **ZFS** — if degraded install, add second disk: `zpool attach rpool sda sdb` once the disk arrives
8. **Proceed** — node is now ready for VM creation (`create-vm.py`) or V2V migration (`convert-v2v.py`)

   

   
   

   *Example Music Limited — Internal Infrastructure Documentation*   *Do not distribute outside the organisation*cloud
