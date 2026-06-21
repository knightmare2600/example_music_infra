# Proxmox VE — VM Creation Script

## Changelog

| Date | Change |
|---|---|
| 2026-03-01 | Initial document — create-vm.py reference, role/site codes, hardware defaults, networking |
| 2026-03-03 | BRD renamed to BER, TOR added (192.168.146.0/24) |
| 2026-03-03 | Role codes: added AST, DCS, DRM→LIN, FCL, IOT, LIN, MIC, MID, NAS, OBS, PAY, PVE, RAD, SMP→FCL, SYN; removed DRM/SMP |
| 2026-03-03 | DON clarified as donut-specific; VND as generic vending; SRV as Windows general purpose; SVR as legacy/non-Proxmox |
| 2026-03-03 | Hardware defaults updated — SRV/SVR and NIX split into separate profiles; PVE added |
| 2026-03-03 | Console table updated — NIX added to serial console defaults |
| 2026-03-03 | CPU sockets × cores added to hardware section |
| 2026-03-03 | Pool selection added; guest agent enabled by default |

## `create-vm.py` Reference & Usage Guide

> **Applies to:** Proxmox VE 8.x · Python 3.8+
> **Requires:** `proxmoxer`, `requests` (`pip3 install proxmoxer requests`)
> **Location:** `bootstrap/create-vm.py`

---

## Overview

`create-vm.py` is an interactive Python script for creating VMs on a Proxmox node following the `EXA[ROLE][SITE][NNN]` naming convention. It runs anywhere Python is available — the Proxmox node itself, a Windows workstation, a Mac, a Linux laptop — and communicates entirely via the Proxmox REST API using `proxmoxer`.

`proxmoxer` is installed on all PVE nodes by `first-boot.sh` automatically.

---

## Quick Start

```bash
# Fully interactive — prompts for everything
python3 create-vm.py

# Specify host, prompt for the rest
python3 create-vm.py --host 192.168.139.50

# API token auth
python3 create-vm.py --host 192.168.139.50 --user root@pam \
    --token-name mytoken \
    --token-value xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Dry run — shows full config, makes zero API calls
python3 create-vm.py --host 192.168.139.50 --dry-run

# Help
python3 create-vm.py --help
```

---

## Command Line Flags

| Flag | Description | Default |
|---|---|---|
| `--host` | Proxmox host/IP | Prompted |
| `--port` | API port | `8006` |
| `--user` | Proxmox username (e.g. `root@pam`) | Prompted |
| `--token-name` | API token name | Prompted if using token auth |
| `--token-value` | API token value | Prompted if using token auth |
| `--password` | Password | Prompted if using password auth |
| `--node` | Proxmox node name | Auto-detected or prompted |
| `--dry-run` | Show config without creating anything | Off |
| `--log` | Log file path | `~/pve-vm-create.log` |

Any flag not supplied on the command line will be prompted at runtime. Nothing is hardcoded.

---

## Authentication

The script supports both authentication methods Proxmox offers:

**API Token (recommended)**

Create a token in the Proxmox web UI under **Datacenter → Permissions → API Tokens**. Tokens can be scoped to specific permissions and do not require storing a password anywhere.

```bash
python3 create-vm.py \
    --host 192.168.139.50 \
    --user root@pam \
    --token-name create-vm \
    --token-value xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Username + Password**

```bash
python3 create-vm.py --host 192.168.139.50 --user root@pam
# Password prompted at runtime — not echoed to terminal
```

---

## VM Naming Convention

All VMs follow the standard `EXA[ROLE][SITE][NNN]` convention:

```
EXA  FWL  FAL  001
 |    |    |    |
 |    |    |    +-- Sequence number (001–999, zero padded)
 |    |    +------- Site code (3 letters)
 |    +------------ Role code (3 letters)
 +----------------- Prefix (always EXA)
```

The script:
- Knows all valid role codes and site codes
- Checks existing VM names on the node to prevent duplicates
- Suggests the next available NNN for the chosen ROLE+SITE combination
- Allows manual override of the suggested name (still validates format and uniqueness)

### Role Codes

| Code | Role |
|---|---|
| `AST` | Atari ST (Retro Hardware) |
| `BPS` | Badge Programming Station |
| `CAM` | Security Camera |
| `CLK` | Time Clock / Punch Clock |
| `COF` | Coffee Machine (Smart Appliance) |
| `DCS` | Domain Controller |
| `DON` | Donut Vending Machine (Tim Hortons compatible) |
| `FCL` | Fairlight CMI Sampler |
| `FWL` | Firewall Appliance |
| `ILO` | Integrated Lights-Out (HP iLO) |
| `IOT` | IoT / Miscellaneous Embedded Device |
| `LAP` | Laptop (Windows) |
| `LCD` | LCD Wallboard / Information Display |
| `LIN` | LinnDrum Drum Machine |
| `MAC` | macOS Desktop (iMac / Mac Mini) |
| `MBP` | MacBook Pro |
| `MIC` | Microphone (IP/Dante Audio) |
| `MID` | MIDI Sequencer / Workstation |
| `MUS` | Music Workstation / Studio System / Jukebox |
| `NAS` | Network Attached Storage |
| `NIX` | Unix/Linux/Solaris System |
| `OBS` | Outside Broadcast Station |
| `PAY` | Payphone |
| `PBX` | PBX (Telephone Server) |
| `PHN` | Mobile / Desk Phone |
| `PMP` | Petrol Pump |
| `PRN` | Printer / MFD |
| `PVE` | Proxmox VE Node |
| `RAC` | Remote Access Controller (Dell iDRAC) |
| `RAD` | Radio Transmitter / Broadcast |
| `RDR` | Card Reader / Badge Reader |
| `RTR` | Router |
| `SBC` | Session Border Controller |
| `SRV` | Server (General Purpose — Windows) |
| `SUR` | Microsoft Surface Device |
| `SVR` | Server (Legacy / Non-Proxmox) |
| `SWI` | Network Switch |
| `SYN` | Synthesizer (e.g. Moog) |
| `TAB` | Tablet |
| `TAR` | Tape Archiver |
| `TEA` | Internet Connected Tea/Coffee Machine (RFC2324) |
| `TTY` | Teletype / Serial Terminal / VDU |
| `TVS` | Television / Digital Signage |
| `VCU` | Video Conferencing Unit |
| `VND` | Vending Machine |
| `WAP` | Wireless Access Point |
| `WKS` | Workstation (Desktop) |

---

## VM IDs

- All VMs use IDs starting at **1000** and incrementing upward
- The script finds the next free ID automatically
- Manual override is available — must be ≥ 1000 and not already in use
- IDs below 1000 are reserved for Proxmox internal use

---

## Hardware Defaults

The script suggests sensible defaults based on role, which the technician can override:

| Role Family | Default CPU | Default RAM | Default Disk | Console | Notes |
|---|---|---|---|---|---|
| FWL / RTR / SBC / PBX | 2 vCPU | 2048MB | 20GB | Serial | Appliance roles |
| PVE | 4 vCPU | 8192MB | 120GB | VGA | Proxmox VE node |
| SRV / SVR | 4 vCPU | 8192MB | 80GB | VGA | Windows servers |
| NIX | 2 vCPU | 2048MB | 40GB | Serial | Unix/Linux/Solaris |
| WKS / LAP / MBP / MAC / SUR | 2 vCPU | 4096MB | 80GB | VGA | Desktop/laptop |
| All others | 2 vCPU | 2048MB | 32GB | VGA | |

All VMs use `--cpu host` (full CPU pass-through) and have memory ballooning disabled.

---

## Storage

The script queries `pvesm status` via the API, filters to storage that supports VM disk images, and presents a numbered menu showing:

- Storage name and type
- Used / free / total space
- Active/inactive status

The technician selects from the menu. The disk is created as a VirtIO SCSI device on the selected storage.

---

## Console

| Role | Default Console | Connect With |
|---|---|---|
| FWL, RTR, SBC, PBX | Serial (ttyS0) | `qm terminal VMID` |
| NIX | Serial (ttyS0) | `qm terminal VMID` |
| All others | VGA | Proxmox web UI console |

The technician can override the default at the console selection prompt. Serial console VMs behave like headless appliances — no VGA output, the serial port is the only console interface, exactly like a physical Cisco ASA or FortiGate with a rollover cable.

---

## Boot Order & iPXE

All VMs are configured with SeaBIOS (required for iPXE compatibility) and boot in this order:

1. `scsi0` — local disk (boots installed OS if present)
2. `ide2` — iPXE ISO (CD-ROM)
3. `net0` — PXE network boot

The script scans the local ISO store for `ipxe.iso` and pre-selects it if found. The technician can select a different ISO or skip ISO attachment entirely.

This means a fresh VM with an empty disk will fall through to the iPXE ISO on second boot attempt, chainloading your boot menu from `192.168.139.50` automatically.

---

## Network Configuration

NIC assignment is automatic based on role and site code. All NICs use VirtIO.

**Dual-NIC roles (FWL, RTR):**

| NIC | Bridge | VLAN | Purpose |
|---|---|---|---|
| net0 | vmbr0 | untagged | WAN / provisioning |
| net1 | vmbr1 | site VLAN | LAN — site subnet |

**All other roles — single NIC:**

| NIC | Bridge | VLAN | Purpose |
|---|---|---|---|
| net0 | vmbr1 | site VLAN | Site LAN |

The site VLAN ID is derived from the site code — it matches the third octet of the site subnet (e.g. FAL = VLAN 76, MIA = VLAN 135). The technician is shown the proposed NIC layout and asked to confirm before proceeding.

If the technician declines the auto NIC layout, the VM is created without NICs and they are added manually afterwards.

---

## Confirmation Flow

The script confirms at each major stage before proceeding:

1. **Connection** — connects and shows node info
2. **Hardware** — shows CPU/RAM/disk, asks to accept
3. **Storage** — shows storage selection, asks to accept
4. **ISO** — shows ISO selection, asks to accept
5. **Console** — shows console type, asks to accept
6. **Network** — shows NIC layout, asks to accept
7. **Final summary** — shows complete VM config, asks to create
8. **Start VM** — after creation, asks whether to start immediately

All confirmation prompts default to **No** except the NIC layout confirmation which defaults to Yes (since the auto layout is almost always correct).

---

## Dry Run

```bash
python3 create-vm.py --host 192.168.139.50 --dry-run
```

Dry run mode goes through the complete interactive flow — connecting to Proxmox, querying storage and ISOs, collecting all inputs — but makes zero API calls at the creation step. The full VM config summary is printed exactly as it would appear before a real creation.

A log entry is written with `[DRY-RUN]` prefix so dry runs are traceable.

Useful for:
- Verifying config before committing
- Training new technicians
- Testing that API connectivity and credentials work

---

## Log File

Every VM creation (and dry run) is appended to the log file (default: `~/pve-vm-create.log`):

```
2026-03-01T10:23:45Z  VMID=1001  NAME=EXAFWLFAL001  NODE=EXAPVEFAL001  OS=other  CPU=2c  RAM=2048MB  DISK=20GB@local-zfs  CONSOLE=serial  NICS=[net0=vmbr0; net1=vmbr1(VLAN76)]
2026-03-01T10:31:12Z  [DRY-RUN] VMID=1002  NAME=EXASRVFAL001  NODE=EXAPVEFAL001  OS=l26  CPU=4c  RAM=4096MB  DISK=60GB@local-zfs  CONSOLE=vga  NICS=[net0=vmbr1(VLAN76)]
```

Specify a custom log path with `--log /path/to/logfile.log`.

---

## Dependencies

**On the Proxmox node** — already handled by `first-boot.sh`:
```bash
apt install python3-proxmoxer python3-requests
```

**On a Windows / Mac / Linux workstation** (not a managed Debian system):
```bash
pip3 install proxmoxer requests
```

Python 3.8 or later required.

---

## Creating an API Token (Recommended)

1. In the Proxmox web UI go to **Datacenter → Permissions → API Tokens → Add**
2. Select user `root@pam` (or a dedicated service user)
3. Give it a name e.g. `create-vm`
4. Untick **Privilege Separation** if you want it to inherit root permissions
5. Copy the token value — it is only shown once
6. Use with `--token-name create-vm --token-value <value>`

For a dedicated service user with minimal permissions, the token user needs at minimum:
- `VM.Allocate` on `/`
- `VM.Config.CDROM`, `VM.Config.CPU`, `VM.Config.Disk`, `VM.Config.Memory`, `VM.Config.Network`, `VM.Config.Options` on `/vms`
- `Datastore.AllocateSpace` on the target storage
- `SDN.Use` on `/sdn` (for bridge/VLAN assignment)

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
