# V2V Migration Scenario Walkthroughs

---

**Document ID:** NET-VIRT-V2V-002  
**Classification:** Internal — Network Operations  
**Author:** Network Engineering  
**Last Updated:** 2026-03-04  
**Version:** 0.9 — DRAFT (real terminal output pending)**  
**Depends on:** NET-VIRT-V2V-001 (V2V Migration Guide), NET-VPN-WG-001 (WireGuard Guide)

> **⚠️ DRAFT STATUS**
> Sections marked `[PENDING OUTPUT]` contain placeholder blocks where real terminal output will be inserted once test VMs have been run through the conversion pipeline. Placeholders indicate exactly what command to run and what to capture.
> 
> See the end of this document for the output collection checklist.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Scenario 1 — Debian Trixie (Linux Firewall VM)](#scenario-1--debian-trixie-linux-firewall-vm)
3. [Scenario 2 — Windows Server 2022](#scenario-2--windows-server-2022)
4. [Scenario 3 — OpenBSD (Curveball)](#scenario-3--openbsd-curveball)
5. [Cross-Scenario Comparison](#cross-scenario-comparison)
6. [Output Collection Checklist](#output-collection-checklist)

---

## Introduction

This document provides step-by-step walkthroughs of the `convert-v2v.py` script for three representative guest operating systems, covering the happy path, known failure modes, and required remediation steps for each.

Each scenario uses the same source environment:

| Item | Value |
|------|-------|
| VMware Workstation host | Windows (VM folder copied to Linux workstation) |
| Conversion host | Linux workstation with `virt-v2v` installed (WORKSTATION mode) |
| Proxmox node | `EXAPVEFAL001` — `192.168.76.x` |
| Proxmox storage | `local-zfs` (ZFS mirror pool) — **raw format** |
| Script | `convert-v2v.py` |

The three scenarios are deliberately chosen to represent the spectrum of difficulty:

- **Debian Trixie** — best-case, fully supported by `virt-v2v`, expected clean conversion
- **Windows Server 2022** — supported with caveats; virtio driver handling requires manual steps
- **OpenBSD** — unsupported by `virt-v2v`; requires `qemu-img` fallback + manual boot remediation

---

## Scenario 1 — Debian Trixie (Linux Firewall VM)

### Environment

| Item | Value |
|------|-------|
| Source VM name | `EXAFWLFAL001` |
| Guest OS | Debian GNU/Linux 13 (Trixie) |
| Role | Firewall / WireGuard gateway |
| VMware NIC(s) | 2 × `e1000` (presented as `ens33`, `ens34`) |
| VMX path | `/home/user/vms/EXAFWLFAL001/EXAFWLFAL001.vmx` |
| VMDK size | ~8 GB (thin provisioned) |
| VMware Tools | `open-vm-tools` installed |
| Special config | `firewallme.sh`, WireGuard `wg0`, systemd drop-in override |

### Expected Outcome

`virt-v2v` has excellent Debian support. Conversion should complete cleanly, removing `open-vm-tools` and rebuilding the `initramfs` with `virtio` drivers. The main post-boot task is handling the NIC rename.

---

### Step 1 — VMX File

The VMX as it appears on the conversion host before running the script.

```
[PENDING OUTPUT]
Command : cat /home/user/vms/EXAFWLFAL001/EXAFWLFAL001.vmx
Capture : Full file contents (sanitise PrivateKey / pre-shared keys if present)
Expected: displayName, memsize, numvcpus, ethernet0/1 blocks, scsi0:0.fileName


 python3 convert-v2v.py --dry-run  --host 192.168.139.5 --user root@pam --search-path Migration/EXAFWLFAL001
```

Key lines to look for:

```ini
displayName = "EXAFWLFAL001"
memsize = "2048"
numvcpus = "2"
guestOS = "debian11-64"
ethernet0.present = "TRUE"
ethernet0.virtualDev = "e1000"
ethernet0.connectionType = "nat"
ethernet1.present = "TRUE"
ethernet1.virtualDev = "e1000"
ethernet1.connectionType = "bridged"
scsi0:0.fileName = "EXAFWLFAL001.vmdk"
```

---

### Step 2 — Script Run (WORKSTATION mode)

```
[PENDING OUTPUT]
Command : python3 convert-v2v.py --host 192.168.76.x --user root@pam \
              --ssh-key ~/.ssh/id_rsa --search-path /home/user/vms/
Capture : Full interactive session output from VMX selection through to
          "CONVERSION COMPLETE" banner
Note    : Accept all defaults; select local-zfs as storage
```

Key sections to capture:

**Binary check output** — should show all green:
```
[PENDING OUTPUT]
Expected:
  [+] virt-v2v     /usr/bin/virt-v2v   —  VMware→KVM guest conversion
  [+] qemu-img     /usr/bin/qemu-img   —  VMDK inspection and fallback conversion
  [+] scp          /usr/bin/scp        —  Upload converted disk to Proxmox
  [+] ssh          /usr/bin/ssh        —  Remote command execution on Proxmox
  [+] All required binaries present
```

**Storage selection** — should show `local-zfs` with `raw` format:
```
[PENDING OUTPUT]
Expected:
  [i] Storage : local-zfs  (ZFS Pool)
  [i] Format  : raw  (block device — raw required)
  [i] Free    : XX.X GB available
```

**ZFS advisory** — should appear before import:
```
[PENDING OUTPUT]
Expected:
  [i] ZFS storage detected (local-zfs)
  [i] Import will create a zvol — block device, not a file
  [i] Format: raw  (qcow2 is not supported on ZFS zvols)
  [i] Note: zvol volblocksize defaults to 8K on Proxmox (fine for most workloads)
```

---

### Step 3 — virt-v2v Log

```
[PENDING OUTPUT]
Command : cat /tmp/v2v-EXAFWLFAL001.log
Capture : Full log
```

Key lines to look for — these confirm successful guest surgery:

```
ansible@EXAPVECLD001:~> python3 convert-v2v.py --host 192.168.139.5 --user root@pam --search-path Migration/EXAFWLFAL001

  +============================================================+
  |      PROXMOX VE — VMware V2V CONVERSION                  |
  |             jukebox.internal                              |
  +============================================================+


  ============================================================
  CONNECTING TO PROXMOX
  ============================================================


  Authentication method:
    1  API Token (recommended)
    2  Username + Password

  Select [1]: 2
  Password:
  [->] Connecting to https://192.168.139.5:8006 as root@pam...
  [+] Connected to 192.168.139.5:8006
  [+] Single node: EXAPVECLD001
  [+] Mode: LOCAL — running directly on the Proxmox node
  [i] virt-v2v will run via subprocess; no file transfers needed

  ============================================================
  BINARY / DEPENDENCY CHECK
  ============================================================

  [+] virt-v2v   /usr/bin/virt-v2v  —  VMware→KVM guest conversion
  [+] qemu-img   /usr/bin/qemu-img  —  VMDK inspection and fallback conversion
  [X] qm         NOT FOUND  —  Proxmox VM management (disk import, config)

  The following required tools are missing:

    qm
      Install: Should be present on any Proxmox node — check your PATH


  ============================================================
  LOCATE SOURCE VM
  ============================================================

  [i] Searching for .vmx files in: Migration/EXAFWLFAL001

  Found 1 VMX file(s):

    1  EXAFWLFAL001.vmx                         (Migration/EXAFWLFAL001/EXAFWLFAL001.vmx)  [10888.4MB total]

  Select VMX to convert [1]:
  [+] Selected: Migration/EXAFWLFAL001/EXAFWLFAL001.vmx

  ============================================================
  VMX PARSED HARDWARE
  ============================================================


  Parsed from VMX:
    Display name  : EXAFWLFAL001
    Guest OS (raw): debian12-64
    OS type guess : l26
    vCPUs         : 1
    RAM           : 512 MB

    Disk(s):
      1.  Migration/EXAFWLFAL001/EXAFWLFAL001-000002.vmdk  [found]  4255.5MB on disk

    NIC(s) detected:
      eth0  type=e1000  conn=nat  mac=00:0c:29:11:3c:9a
      eth1  type=e1000  conn=custom  mac=00:0C:29:11:3C:A4

  Proceed with this source VM? [Y/n]: y

  ============================================================
  TARGET VM IDENTITY
  ============================================================


  Role codes:
    AST   Atari ST (Retro Hardware)                 BPS   Badge Programming Station                 CAM   Security Camera
    CLK   Time Clock / Punch Clock                  COF   Coffee Machine                            DCS   Domain Controller
    DON   Donut Vending Machine (Tim Hortons compatible)  FCL   Fairlight CMI Sampler                     FWL   Firewall Appliance
    ILO   Integrated Lights-Out (HP iLO)            IOT   IoT / Miscellaneous Embedded Device       LAP   Laptop (Windows)
    LCD   LCD Wallboard / Information Display       LIN   LinnDrum Drum Machine                     MAC   macOS Desktop
    MBP   MacBook Pro                               MIC   Microphone (IP/Dante Audio)               MID   MIDI Sequencer / Workstation
    MUS   Music Workstation / Studio System / Jukebox  NAS   Network Attached Storage                  NIX   Unix/Linux/Solaris System
    OBS   Outside Broadcast Station                 PAY   Payphone                                  PBX   PBX (Telephone Server)
    PHN   Mobile / Desk Phone                       PMP   Petrol Pump                               PRN   Printer / MFD
    PVE   Proxmox VE Node                           RAC   Remote Access Controller (Dell iDRAC)     RAD   Radio Transmitter / Broadcast
    RDR   Card Reader / Badge Reader                RTR   Router                                    SBC   Session Border Controller
    SRV   Server (General Purpose)                  SUR   Microsoft Surface Device                  SVR   Server (Legacy / Non-Proxmox)
    SWI   Network Switch                            SYN   Synthesizer (e.g. Moog)                   TAB   Tablet
    TAR   Tape Archiver                             TEA   Internet Connected Tea/Coffee Machine (RFC2324)  TTY   Teletype / Serial Terminal / VDU
    TVS   Television / Digital Signage              VCU   Video Conferencing Unit                   VND   Vending Machine
    WAP   Wireless Access Point                     WKS   Workstation (Desktop)

  [i] Suggested role based on VMX guest OS: NIX
  Role code (e.g. FWL, NIX, SRV) [NIX]: FWL

  Known site codes:
    ABR Aberdeen            AKL Auckland            AMS Amsterdam           BER West Berlin         BIR Birmingham          BON Bonn
    BRK Brockville          CLD Cloud/Provisioning  CLY Clydebank           COV Coventry            CPH Copenhagen          DUN Dundee
    EDI Edinburgh           FAL Falkirk             FAX Faxe                GAA Georgia AL          GLA Glasgow             GOT Gothenburg
    HAL Halifax             HUL Hull                KGE Koge                KOR Korsor              LAX Los Angeles         LIV Liverpool
    LND London              MCR Manchester          MEL Melbourne           MIA Miami               MIL Milan               MTL Montreal
    MUN Munich              NEW Newcastle           NJC New Jersey          NYC New York            ODE Odense              OSL Oslo
    PER Perth               SHE Sheffield           SYD Sydney              TOR Toronto             VIE Vienna

  Site code (e.g. FAL, LND, BRK): FAL
  [i] Next available name: EXAFWLFAL002
  VM name [EXAFWLFAL002]:
  [+] Name: EXAFWLFAL002
  [i] Next free VM ID: 1006
  VM ID [1006]:
  [+] VM ID: 1006

  ============================================================
  OPERATING SYSTEM
  ============================================================

  [i] VMX guest OS: debian12-64  →  suggested Proxmox ostype: l26

     1  Linux 2.6+ kernel (Debian, Ubuntu, etc)
     2  Linux 2.4 kernel (legacy)
     3  Windows 11
     4  Windows 10
     5  Windows Server 2022
     6  Windows Server 2019
     7  Windows Server 2016
     8  Windows Server 2012/R2
     9  Windows Server 2008/R2
    10  Windows XP/2003
    11  Solaris/OpenSolaris
    12  Other / Unknown

  Select OS type [1]: 1
  [+] OS type: Linux 2.6+ kernel (Debian, Ubuntu, etc) (l26)

  ============================================================
  STORAGE
  ============================================================


  Available storage:
    1  local-zfs            ZFS Pool       810.6GB free of 812.3GB  fmt=raw  [active]

  [i] fmt=raw  → ZFS/LVM/Ceph block storage   (zvol/logical volume)
  [i] fmt=qcow2→ Directory/NFS file storage    (supports snapshots)

  Select storage for imported disk: 1
  [+] Storage : local-zfs  (ZFS Pool)
  [+] Format  : raw  (block device — raw required)
  [+] Free    : 810.6 GB available

  ============================================================
  CONSOLE
  ============================================================


  Console type:
    1  VGA only
    2  VGA + Serial  (boot via VGA, OS console via ttyS0 — recommended for appliances)
    3  Serial only   (fully headless)

  Select console [2]:
  [+] Console: both

  ============================================================
  NETWORK CONFIGURATION
  ============================================================


  +-- NIC NAMING ADVISORY -----------------------------------------------+
  |                                                                      |
  |  VMware presents NICs as  ens33, ens34, etc.                         |
  |  Proxmox/virtio presents  enp6s18, enp7s18 — or eth0/eth1           |
  |  depending on udev rules and kernel parameters.                      |
  |                                                                      |
  |  After first boot, the guest's /etc/network/interfaces               |
  |  (Debian) or /etc/netplan/*.yaml (Ubuntu) may reference the         |
  |  OLD VMware NIC names — causing a silent no-network boot.            |
  |                                                                      |
  |  REMEDIATION OPTIONS (choose one):                                   |
  |                                                                      |
  |  1. Force old-style names — add to GRUB before converting:         |
  |     Edit /etc/default/grub on the SOURCE VM:                        |
  |     GRUB_CMDLINE_LINUX="net.ifnames=0 biosdevname=0"                |
  |     Then: update-grub                                               |
  |     This restores eth0/eth1 naming — best if scripts hardcode NICs  |
  |                                                                      |
  |  2. Fix after migration — on first boot via console:               |
  |     ip link show   (find new name)                                  |
  |     sed -i 's/ens33/enp6s18/g' /etc/network/interfaces             |
  |     systemctl restart networking                                    |
  |                                                                      |
  |  3. WireGuard / firewallme.sh users — also update the systemd      |
  |     drop-in override.conf BindsTo= and After= interface names.      |
  |     See NET-VPN-WG-001 for the full procedure.                      |
  |                                                                      |
  +----------------------------------------------------------------------+


  [i] Source VM has 2 NIC(s) — proposing dual-NIC layout:
  [i]   net0  vmbr0  untagged      (WAN / provisioning)
  [i]   net1  vmbr1  VLAN 76      (LAN — FAL site, 192.168.76.0/24)

  Accept this NIC layout? [Y/n]: y
  [+] net0  vmbr0  untagged  virtio  — WAN / provisioning (untagged)
  [+] net1  vmbr1  tag=76  virtio  — LAN — FAL site VLAN 76

  ============================================================
  POOL
  ============================================================

  [i] Available pools: ABD, AKL, AMS, ATL, BER, BIR, BON, BRK, CHI, CLD, CLY, COV, CPH, DEV, DUN, EDI, FAL, FAX, GLA, GOT, HAL, HUL, KGE, KOR, LAX, LIV, LND, MCR, MEL, MIA, MIL, MTL, MUN, NEW, NJC, NYC, NYJ, ODE, OSL, PER, Provisioning, SHE, SYD, TOR, VIE
  [i] Pool matching site FAL: FAL
  Pool (blank = none) [FAL]:
  [+] Pool: FAL
  [i] virt-v2v output directory : /tmp/v2v-import-output
  [i] Disk format for local-zfs : raw  (ZFS/LVM block storage)

  ============================================================
  CONVERSION SUMMARY
  ============================================================

  Source
    VMX         : Migration/EXAFWLFAL001/EXAFWLFAL001.vmx
    Display name: EXAFWLFAL001
    Guest OS    : debian12-64 → l26

  Target
    VM ID   : 1006
    Name    : EXAFWLFAL002
    Pool    : FAL
    Storage : local-zfs
    Mode    : LOCAL (runs locally)

  Hardware (from VMX)
    vCPUs   : 1
    RAM     : 512 MB
    Disk(s) : 1 VMDK(s) detected

  Console : both

  NICs
    net0   vmbr0  untagged    virtio  — WAN / provisioning (untagged)
    net1   vmbr1  VLAN 76     virtio  — LAN — FAL site VLAN 76

  Proceed with conversion? [y/N]: y

  ============================================================
  virt-v2v CONVERSION
  ============================================================

  [i] Mode        : LOCAL
  [i] Source VMX  : Migration/EXAFWLFAL001/EXAFWLFAL001.vmx
  [i] Output dir  : /tmp/v2v-import-output  (local)

  [->] Running: virt-v2v -i vmx Migration/EXAFWLFAL001/EXAFWLFAL001.vmx -o local -of raw -os /tmp/v2v-import-output -v
  [->] Logging to /tmp/v2v-EXAFWLFAL001.log
  [+] virt-v2v completed successfully

  ============================================================
  PRE-FLIGHT CHECKS
  ============================================================

  [->] Checking VMID 1006 is free...
  [+] VMID 1006 is free
  [->] Checking name 'EXAFWLFAL002' is free...
  [+] Name 'EXAFWLFAL002' is free

  ============================================================
  PRE-IMPORT DISK VERIFICATION
  ============================================================

  [+] File exists   : /tmp/v2v-import-output/EXAFWLFAL001-sda
  [+] Size on disk  : 10240.0 MB
  [+] Image format  : raw  (qemu-img confirmed readable)
  [+] Virtual size  : 10.0 GB
  [->] Checking available space on target storage...
  [+] Storage local-zfs: 810.0GB free — looks sufficient

  [i] ZFS storage detected (local-zfs)
  [i] Import will create a zvol — block device, not a file
  [i] Format: raw  (qcow2 is not supported on ZFS zvols)
  [i] Note: zvol volblocksize defaults to 8K on Proxmox (fine for most workloads)


  ============================================================
  CREATING VM
  ============================================================

  [->] Creating VM shell...
  [+] VM 1006 (EXAFWLFAL002) created on EXAPVECLD001

  ============================================================
  DISK IMPORT
  ============================================================

  [->] Importing: /tmp/v2v-import-output/EXAFWLFAL001-sda
  [->]        → : local-zfs  (format: raw)
  [!] 'qm' not found in PATH — are we running on a Proxmox node?
  [!] Run manually: qm importdisk 1006 /tmp/v2v-import-output/EXAFWLFAL001-sda local-zfs --format raw
  Import reported errors — attempt to continue configuring VM? [y/N]: y
  [->] Waiting for imported disk to appear in VM 1006 config...
  [!] Disk did not appear as unusedN within 30s
  [!] unusedN not found — attempting constructed path: local-zfs:vm-1006-disk-0
  [+] Disk attached as scsi0 (constructed path)
  [->] Configuring console...
  [+] Console: VGA + Serial ttyS0 — connect: qm terminal {vmid}
  [->] Configuring NICs...
  [+] net0: vmbr0 untagged virtio
  [+] net1: vmbr1 VLAN 76 virtio

  ============================================================
  POST-IMPORT VERIFICATION
  ============================================================

  [->] Verifying VM config looks sane...
  [+] scsi0    : local-zfs:vm-1006-disk-0,size=10G
  [+] boot     : order=scsi0;net0
  [+] memory   : 512 MB
  [+] agent    : qemu-guest-agent enabled
  [!] Import had errors — preserving staging files for manual recovery:
  [!]   /tmp/v2v-import-output

  +============================================================+
  |  CONVERSION COMPLETE                                           |
  +============================================================+

  [+] VM ID  : 1006
  [+] Name   : EXAFWLFAL002
  [+] Node   : EXAPVECLD001



[PENDING OUTPUT]
Expected sequence:
  [  0.x] Opening the source -i vmx ...
  [ 15.x] Converting Debian GNU/Linux 13 (trixie) to run on KVM
  [ 15.x] Removing VMware Tools
  [ 20.x] Installing virtio drivers
  [ 45.x] Updating initramfs
  [ 90.x] Copying disk 1/1 to /tmp/v2v-output/EXAFWLFAL001-sda (raw)
  [XXX.x] Finishing off
```

Confirm `open-vm-tools` removal line appears in the log:
```
[PENDING OUTPUT]
Expected: "Removing package: open-vm-tools" or similar
```

---

### Step 4 — Pre-Import Verification Output

```
[PENDING OUTPUT]
Command : (captured from script output during PRE-IMPORT DISK VERIFICATION section)
Capture : qemu-img info output as shown by the script
Expected:
  [+] File exists   : /tmp/v2v-output/EXAFWLFAL001-sda
  [+] Size on disk  : XXXX.X MB
  [+] Image format  : raw  (qemu-img confirmed readable)
  [+] Virtual size  : XX.XX GB
```

---

### Step 5 — Proxmox VM Config After Import

```
[PENDING OUTPUT]
Command : qm config <VMID>
Capture : Full output
Expected:
  agent: enabled=1
  boot: order=scsi0;net0
  cores: 2
  memory: 2048
  name: EXAFWLFAL001
  net0: virtio=XX:XX:XX:XX:XX:XX,bridge=vmbr0
  net1: virtio=XX:XX:XX:XX:XX:XX,bridge=vmbr1,tag=76
  ostype: l26
  scsi0: local-zfs:vm-XXX-disk-0,size=20G
  scsihw: virtio-scsi-pci
  serial0: socket
  vga: std,memory=32
```

---

### Step 6 — First Boot

Connect to the serial console immediately after starting:

```bash
qm start <VMID>
qm terminal <VMID>
```

```
[PENDING OUTPUT]
Command : qm terminal <VMID>  (connect immediately after qm start)
Capture : Boot messages from kernel start through to login prompt
          Pay particular attention to:
          - virtio_blk lines (confirms disk driver loaded)
          - Network interface names as they appear
          - Any systemd unit failures
          - WireGuard wg-quick@wg0 status
```

#### NIC Rename — What to Expect

This is the most likely issue on first boot. VMware presented NICs as `ens33`/`ens34`.
Proxmox virtio will present them under a different name.

```
[PENDING OUTPUT]
Command (inside VM after boot): ip link show
Capture : Full output showing new NIC names
Expected: Something like enp6s18, enp7s18 — or eth0/eth1 if net.ifnames=0 was set
```

If networking is down due to rename, fix with:

```bash
# Identify new names
ip link show

# Update interfaces file (substitute actual new name)
sed -i 's/ens33/enp6s18/g' /etc/network/interfaces
sed -i 's/ens34/enp7s18/g' /etc/network/interfaces

systemctl restart networking
```

```
[PENDING OUTPUT]
Command : cat /etc/network/interfaces  (before and after fix)
Capture : File contents showing old names, then corrected names
```

---

### Step 7 — WireGuard Validation

After networking is restored, re-run the WireGuard checklist from NET-VPN-WG-001:

```bash
systemctl status wg-quick@wg0
wg show
ip addr show wg0
```

```
[PENDING OUTPUT]
Command : systemctl status wg-quick@wg0 && wg show && ip addr show wg0
Capture : Full output of all three commands
Expected:
  - wg-quick@wg0: active (running)
  - latest handshake: X seconds ago
  - inet 192.168.131.254/24 on wg0
```

If `wg-quick@wg0` failed due to NIC rename (BindsTo= interface no longer exists):

```bash
# Update the drop-in override with new interface names
cat /etc/systemd/system/wg-quick@wg0.service.d/override.conf

# Edit BindsTo= and After= to use new NIC names, then:
systemctl daemon-reload
systemctl restart wg-quick@wg0
```

```
[PENDING OUTPUT]
Command : cat /etc/systemd/system/wg-quick@wg0.service.d/override.conf
Capture : Before and after edit
```

---

### Step 8 — firewallme.sh Validation

```bash
bash /usr/local/bin/firewallme.sh
```

```
[PENDING OUTPUT]
Command : bash /usr/local/bin/firewallme.sh
Capture : Full output
Expected: Completes without errors, confirms WireGuard active
```

---

### Step 8 — Post-Migration Boot Fixes

`convert-v2v.py` applies Fixes 1 and 2 automatically using `virt-customize` before the
disk is imported into Proxmox. No manual action is required unless `virt-customize` was
unavailable or reported a non-zero exit (e.g. encrypted LVM).

Fix 3 (stale interface names) cannot be automated and must always be done manually.

#### Fix 1 — NetworkManager Ordering Cycle (automated)

virt-v2v leaves a systemd dependency tangle where NetworkManager is expected to both bring up
`network.target` and wait for it, creating a cycle. Systemd resolves the cycle by silently
deleting the NM start job so NM never starts, with zero journal entries to debug.

Symptoms: `systemctl status NetworkManager` shows `inactive (dead)`, `nmcli` shows no IPs,
dnsmasq and cockpit fail on boot. The journal will show:

```
network-online.target: Job network.target/start deleted to break ordering cycle
NetworkManager.service: Job dbus.service/start deleted to break ordering cycle
```

`convert-v2v.py` injects the following drop-in via `virt-customize` before import:

```ini
# /etc/systemd/system/NetworkManager.service.d/override.conf
[Unit]
After=network-pre.target
After=dbus.service
Before=network.target
```

If applying manually post-boot:

```bash
sudo mkdir -p /etc/systemd/system/NetworkManager.service.d
sudo tee /etc/systemd/system/NetworkManager.service.d/override.conf << EOF
[Unit]
After=network-pre.target
After=dbus.service
Before=network.target
EOF
sudo systemctl daemon-reload
```

#### Fix 2 — Disable guestfs-firstboot (automated)

virt-v2v installs `guestfs-firstboot.service` which runs one-shot scripts on first boot
then leaves itself enabled, contributing to the ordering cycle on every subsequent boot.
`convert-v2v.py` disables it via `virt-customize` if the scripts directory is empty.

If applying manually:

```bash
ls /usr/lib/virt-sysprep/scripts/   # should be empty after first boot
sudo systemctl disable guestfs-firstboot.service
sudo systemctl daemon-reload
```

#### Fix 3 — Audit Config Files for Stale Interface Names (manual, always required)

virt-v2v renames interfaces from VMware names (`ens33`, `ens34`) to KVM VirtIO names
(`enp6s18`, `enp7s18` or similar). Config files referencing old interface names will
silently fail. This cannot be automated as the new names are only known at first boot.

Files to check:

```bash
# dnsmasq
grep "interface" /etc/dnsmasq.d/*.conf

# nftables
grep -E "iifname|oifname" /etc/nftables.conf

# WireGuard drop-ins
grep -rn "BindsTo" /etc/systemd/system/wg-quick@wg0.service.d/

# NetworkManager profiles
grep "interface-name" /etc/NetworkManager/system-connections/*.nmconnection
```

Update stale names then restart affected services:

```bash
sudo systemctl daemon-reload
sudo systemctl restart dnsmasq nftables NetworkManager
sudo wg-quick down wg0 && sudo wg-quick up wg0
```

---

### Scenario 1 — Known Issues Summary

| Issue | Cause | Fix |
|-------|-------|-----|
| No network on first boot | NIC rename ens33→enp6s18 | `sed` fix in `/etc/network/interfaces` |
| `wg-quick@wg0` failed | BindsTo= references old NIC name | Update drop-in override, daemon-reload |
| `firewallme.sh` errors | NIC name in script hardcoded | Update interface variable in script |
| `open-vm-tools` service error in logs | Removal incomplete | `apt remove --purge open-vm-tools` |
| NetworkManager dead on boot, zero journal entries | virt-v2v creates systemd ordering cycle; NM job silently deleted | **Automated** — NM drop-in injected by `convert-v2v.py` via `virt-customize` (Step 8 Fix 1). Manual fallback in Step 8 if `virt-customize` failed. |
| dnsmasq fails with `unknown interface` | Config references old VMware NIC name after rename | Manual — update `interface=` in `/etc/dnsmasq.d/lan.conf` (Step 8 Fix 3) |
| cockpit.socket fails on boot | Bound to LAN IP that doesn't exist because NM is dead | Resolved automatically when NM ordering fix is applied |
| `guestfs-firstboot` contributing to boot cycle | virt-v2v leaves service enabled after scripts already ran | **Automated** — disabled by `convert-v2v.py` via `virt-customize` (Step 8 Fix 2) |
| `virt-customize` exits non-zero, fixes not applied | Encrypted LVM or unusual partition layout | Apply Step 8 Fixes 1 and 2 manually post-boot |

---

---

## Scenario 2 — Windows Server 2022

### Environment

| Item | Value |
|------|-------|
| Source VM name | `EXASRVFAL001` (placeholder) |
| Guest OS | Windows Server 2022 Standard |
| Role | General purpose server |
| VMware NIC(s) | 1 × `e1000` or `vmxnet3` |
| VMDK size | ~40 GB |
| VMware Tools | VMware Tools installed |
| Special config | None assumed |

### The VirtIO Driver Problem

Windows does not ship with VirtIO drivers. VMware presents virtual hardware that Windows has drivers for (`e1000` NIC, `LSI Logic` SCSI). Proxmox presents VirtIO hardware that Windows has **no inbox drivers for** — meaning without intervention, Windows will boot to a bluescreen or simply not find the disk at all.

There are two approaches, covered below:

- **Approach A** — `virt-v2v` driver injection (automatic, works on older Windows,
  unreliable on Server 2022)
- **Approach B** — Attach `virtio-win` ISO, boot with legacy emulated hardware,
  install drivers, switch to VirtIO (reliable, always works)

**Approach B is recommended for Windows Server 2022.**

---

### virt-v2v and Windows — Limitations

`virt-v2v` does support Windows guests but with important caveats for Server 2022:

- It will attempt to inject VirtIO drivers from a driver database into the guest image
- On Server 2022 this is hit and miss — newer Windows versions have changed driver signing requirements that `virt-v2v` doesn't always handle correctly
- `virt-v2v` will still convert the disk and remove VMware Tools; it just may not
  successfully inject working VirtIO drivers
- The conversion is still worth running — it handles the disk format conversion and VMware Tools removal cleanly even if driver injection is partial

---

### Step 1 — VMX File

```
[PENDING OUTPUT — Windows VM not yet available]
Command : type C:\Users\<user>\Documents\Virtual Machines\EXASRVFAL001\EXASRVFAL001.vmx
          (on Windows host) or cat after copying to Linux
Capture : Full VMX contents
Note    : guestOS line will be something like "windows9srv-64" or "windows2019srvnext-64"
```

---

### Step 2 — Script Run

```
[PENDING OUTPUT — Windows VM not yet available]
Command : python3 convert-v2v.py --host 192.168.76.x --user root@pam \
              --ssh-key ~/.ssh/id_rsa
Capture : Full session
Note    : Select OS type 5 (Windows Server 2022 / w2k22) when prompted
          Select SRV as role
```

---

### Step 3 — virt-v2v Log (Windows)

This is where Windows diverges from Linux. Expected log output for a Windows guest:

```
[PENDING OUTPUT — Windows VM not yet available]
Command : cat /tmp/v2v-EXASRVFAL001.log
Capture : Full log
```

What to look for — driver injection result:

```
[PENDING OUTPUT]
Possible outcomes:

SUCCESS case:
  [xx.x] Converting Windows Server 2022 to run on KVM
  [xx.x] Removing VMware Tools
  [xx.x] Installing virtio block driver
  [xx.x] Installing virtio net driver
  [xx.x] Finishing off

PARTIAL/FAILURE case (common on Server 2022):
  [xx.x] Converting Windows Server 2022 to run on KVM
  [xx.x] Removing VMware Tools
  [xx.x] WARNING: could not inject virtio drivers
  [xx.x] WARNING: this guest may not boot or may lose network after conversion
  [xx.x] Finishing off
```

If the warning appears, proceed to Approach B below.

---

### Approach A — virt-v2v Driver Injection (Attempt)

`virt-v2v` can be pointed at a `virtio-win` driver ISO to inject drivers:

```bash
# Download virtio-win ISO on the conversion host
# https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/

virt-v2v \
  -i vmx EXASRVFAL001.vmx \
  -o local -of raw -os /tmp/v2v-output \
  --win-virtio-drivers /path/to/virtio-win.iso \
  -v
```

> **Note:** The `convert-v2v.py` script does not currently pass `--win-virtio-drivers` automatically — this is a manual step for Windows guests. Run `virt-v2v` manually, for Windows if you want to attempt pre-emptive injection.

If injection succeeds, the VM should boot directly to virtio hardware.
If it fails or produces warnings, use Approach B.

---

### Approach B — virtio-win ISO (Reliable Manual Method)

This is the belt-and-braces approach that always works.

#### Step B1 — Download virtio-win ISO

On the Proxmox node:

```bash
cd /var/lib/vz/template/iso/
wget https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso
```

Or download on your workstation and upload via the Proxmox web UI:
**Datacenter → Node → local → ISO Images → Upload**

#### Step B2 — Create VM with Legacy Hardware First

After `convert-v2v.py` creates and imports the VM, **before first boot**, switch the disk and NIC to legacy emulated hardware:

```bash
# Switch scsi0 to IDE (legacy, Windows has inbox drivers)
# In Proxmox UI: Hardware → Hard Disk (scsi0) → Edit → Bus/Device → IDE → IDE 0

# Switch net0 to e1000 (legacy Intel NIC, Windows has inbox drivers)
qm set <VMID> --net0 e1000,bridge=vmbr1,tag=76

# Attach virtio-win ISO as second CD
qm set <VMID> --ide2 local:iso/virtio-win.iso,media=cdrom
```

#### Step B3 — First Boot with Legacy Hardware

Start the VM and connect via VNC/console:

```bash
qm start <VMID>
# Connect via Proxmox web UI console (VGA)
```

Windows should boot successfully using legacy emulated hardware.

```
[PENDING OUTPUT — Windows VM not yet available]
Capture : Screenshot or console text of successful Windows boot
          Confirm: desktop or Server Manager visible
          Confirm: Device Manager shows any unknown devices (these are the virtio devices)
```

#### Step B4 — Install VirtIO Drivers from ISO

Inside the running Windows VM:

1. Open **Device Manager** — you will see unknown devices for the VirtIO controllers
2. Open **File Explorer** → browse to the virtio-win ISO (usually `D:\` or `E:\`)
3. Run `virtio-win-guest-tools.exe` from the ISO root — this installs everything:
   - `vioscsi` — VirtIO SCSI controller driver
   - `NetKVM` — VirtIO network driver
   - `Balloon` — VirtIO memory balloon
   - `qemu-ga` — QEMU Guest Agent (replaces VMware Tools)
   - `vioserial` — VirtIO serial (for `qm terminal`)

```
[PENDING OUTPUT — Windows VM not yet available]
Capture : Device Manager before and after driver installation
          Confirm: all devices showing correctly after install
```

#### Step B5 — Switch to VirtIO Hardware

With drivers installed, shut down the VM and switch hardware to VirtIO:

```bash
# Shut down Windows gracefully first, then:

# Switch disk to VirtIO SCSI
# Proxmox UI: Hardware → Hard Disk (ide0) → Edit → Bus/Device → SCSI → scsi0

# Switch NIC to VirtIO
qm set <VMID> --net0 virtio,bridge=vmbr1,tag=76

# Add serial console (now that vioserial is installed)
qm set <VMID> --serial0 socket --vga std,memory=32
```

#### Step B6 — Second Boot on VirtIO Hardware

```bash
qm start <VMID>
```

```
[PENDING OUTPUT — Windows VM not yet available]
Capture : Successful boot on VirtIO hardware
          Confirm: Network adapter visible in Device Manager as "Red Hat VirtIO Ethernet Adapter"
          Confirm: Disk visible as VirtIO SCSI
          Confirm: qemu-guest-agent service running in Services
```

---

### Scenario 2 — Known Issues Summary

| Issue | Cause | Fix |
|-------|-------|-----|
| Bluescreen on first boot | No VirtIO disk driver | Boot with IDE first (Approach B) |
| No network after boot | No VirtIO NIC driver | Install from virtio-win ISO |
| VMware Tools broken/missing | Removed by virt-v2v, replacement not installed | Run `virtio-win-guest-tools.exe` |
| Driver signing error during install | Server 2022 strict signing | Ensure using latest `virtio-win.iso` (stable channel) |
| `qm terminal` not working | `vioserial` not installed | Install from virtio-win ISO before switching to serial VGA |
| Guest agent shows offline in Proxmox | `qemu-ga` not running | Start `QEMU Guest Agent` service in Windows Services |

---

---

## Scenario 3 — OpenBSD (Curveball)

### Environment

| Item | Value |
|------|-------|
| Source VM name | `EXANIXFAL001` (placeholder) |
| Guest OS | OpenBSD 7.x (current) |
| Role | NIX / miscellaneous |
| VMware NIC(s) | 1 × `e1000` (presented as `em0`) |
| VMDK size | ~8 GB |
| VMware Tools | Not installed (not available for OpenBSD) |
| Special config | None assumed |

### Why This Is a Curveball

`virt-v2v` explicitly does not support BSD guests. It will detect the OS and refuse to proceed. This is not a bug — BSD kernels handle VirtIO differently enough that the Linux-oriented guest surgery `virt-v2v` performs would produce an unbootable system.

The path forward is:

1. `qemu-img convert` — converts the VMDK to raw format (no guest surgery)
2. Manually verify VirtIO kernel support in the OpenBSD guest
3. Boot with legacy emulated hardware if VirtIO modules are absent
4. Install VirtIO support, then switch to VirtIO hardware

The good news: OpenBSD has had solid VirtIO support since 5.3 (2013), and modern OpenBSD 7.x boots cleanly on Proxmox with `virtio0` NIC and `vioblk0` disk in most cases — **if the modules are in the running kernel**.

---

### Step 1 — VMX File

```
[PENDING OUTPUT]
Command : cat /home/user/vms/EXANIXFAL001/EXANIXFAL001.vmx
Capture : Full VMX contents
Note    : guestOS line will be something like "freebsd-64" or "other-64"
          OpenBSD has no specific VMware guestOS identifier
```

---

### Step 2 — Script Run — virt-v2v Refusal

Running `convert-v2v.py` normally will attempt `virt-v2v` first. Here is the expected failure:

```
[PENDING OUTPUT]
Command : python3 convert-v2v.py --host 192.168.76.x --user root@pam \
              --ssh-key ~/.ssh/id_rsa
Capture : Full session up to and including the virt-v2v error
```

Expected `virt-v2v` refusal in the log:

```
[PENDING OUTPUT]
Command : cat /tmp/v2v-EXANIXFAL001.log
Expected output (approximately):
  virt-v2v: error: inspection of the guest failed: could not detect
  the source guest operating system. Please check the debug output.
  Or:
  virt-v2v: error: no bootable operating system was found
  Or (if it detects BSD):
  virt-v2v: error: this guest OS is not supported
```

The script will present the "Continue anyway?" prompt at this point. Answer **N** — do not attempt to import a virt-v2v-failed disk.

---

### Step 3 — Fallback: qemu-img Convert

Run `qemu-img convert` directly on the VMDK:

```bash
# On the conversion host (workstation mode)
mkdir -p /tmp/v2v-output

qemu-img convert \
  -f vmdk \
  -O raw \
  -p \
  /home/user/vms/EXANIXFAL001/EXANIXFAL001.vmdk \
  /tmp/v2v-output/EXANIXFAL001-sda

# Verify the output
qemu-img info /tmp/v2v-output/EXANIXFAL001-sda
```

```
[PENDING OUTPUT]
Command : qemu-img convert -f vmdk -O raw -p \
            /home/user/vms/EXANIXFAL001/EXANIXFAL001.vmdk \
            /tmp/v2v-output/EXANIXFAL001-sda && \
          qemu-img info /tmp/v2v-output/EXANIXFAL001-sda
Capture : Full output including progress and info block
Expected qemu-img info output:
  image: /tmp/v2v-output/EXANIXFAL001-sda
  file format: raw
  virtual size: X GiB (XXXXXXXXXX bytes)
  disk size: X.X GiB
```

---

### Step 4 — Upload Raw Image and Create VM Manually

Since we bypassed `convert-v2v.py` for the conversion step, create the VM manually:

```bash
# Upload raw image to Proxmox
scp /tmp/v2v-output/EXANIXFAL001-sda root@192.168.76.x:/tmp/

# On Proxmox node — create VM shell
# Note: ostype 'other' for OpenBSD
qm create <VMID> \
  --name EXANIXFAL001 \
  --memory 2048 \
  --cores 2 \
  --ostype other \
  --scsihw virtio-scsi-pci \
  --boot order=scsi0 \
  --serial0 socket \
  --vga std,memory=32

# Import disk as raw into ZFS pool
qm importdisk <VMID> /tmp/EXANIXFAL001-sda local-zfs --format raw

# Attach disk
qm set <VMID> --scsi0 local-zfs:vm-<VMID>-disk-0

# Initially use legacy NIC (e1000) — safer for first boot
qm set <VMID> --net0 e1000,bridge=vmbr1,tag=76
```

```
[PENDING OUTPUT]
Commands : all of the above in sequence
Capture  : Full terminal output including qm importdisk progress
```

---

### Step 5 — Pre-Boot: Check VirtIO Kernel Module Availability

**Before starting the VM**, we need to know if the OpenBSD kernel on disk has VirtIO support compiled in or available as modules. We can inspect the disk
without booting using `virt-ls` (part of `libguestfs-tools`):

```bash
# On Proxmox node or conversion host — inspect OpenBSD filesystem
virt-ls -a /tmp/EXANIXFAL001-sda /bsd
# If /bsd exists, it's the kernel

# Check for VirtIO modules in the kernel (OpenBSD links statically — no modules)
# OpenBSD compiles VirtIO into the GENERIC kernel by default since 5.3
# We can check the kernel config embedded in the binary:
virt-cat -a /tmp/EXANIXFAL001-sda /bsd | strings | grep -i virtio
```

```
[PENDING OUTPUT]
Commands : virt-ls and strings/grep check above
Capture  : Output confirming virtio strings present in kernel
Expected : Lines containing "virtio", "vioblk", "vio" etc.
Note     : If nothing appears, the kernel may be custom-compiled without VirtIO —
           boot with legacy hardware (Step 6A) and recompile or install GENERIC kernel
```

---

### Step 6A — First Boot with Legacy Emulated Hardware

Start with `e1000` NIC (already set in Step 4) and IDE disk:

```bash
# Switch to legacy IDE disk for first boot safety
# Proxmox UI: Hardware → Hard Disk (scsi0) → Edit → IDE → ide0

qm start <VMID>
# Connect via Proxmox web UI console
```

```
[PENDING OUTPUT]
Capture : Boot console output — OpenBSD boot loader through to login prompt
          Specifically capture:
          - Boot device detection lines
          - NIC detection (look for "em0" VMware NIC or "vio0" virtio NIC)
          - Disk detection (look for "wd0" IDE or "sd0" virtio block)
          - Any kernel panic or ddb prompt (indicates driver issue)
```

**If OpenBSD boots cleanly on legacy hardware**, proceed to Step 7 to switch to VirtIO.

**If it kernel panics or drops to ddb**, capture the panic message:

```
[PENDING OUTPUT]
Capture : Full panic output if it occurs
Common causes:
  - Missing/wrong root device (fstab references wrong disk name)
  - BIOS geometry mismatch
  - VMware-specific kernel options that conflict with QEMU
```

---

### Step 6B — First Boot on VirtIO (If Kernel Supports It)

If `strings | grep virtio` confirmed VirtIO support, you can try booting directly on VirtIO hardware without the legacy step:

```bash
# Ensure scsi0 is attached (VirtIO SCSI) — already set from Step 4
# Switch NIC to VirtIO
qm set <VMID> --net0 virtio,bridge=vmbr1,tag=76

qm start <VMID>
```

```
[PENDING OUTPUT]
Capture : Boot console output
Expected OpenBSD VirtIO detection lines (approximately):
  virtio0 at pci0 dev 4 function 0 "Virtio Storage" rev 0x00
  vioblk0 at virtio0: qsize 128
  vioblk0: 20480MB
  sd0 at scsibus2 targ 1 lun 0: <VirtIO, Block Device, >
  virtio1 at pci0 dev 3 function 0 "Virtio Network" rev 0x00
  vio0 at virtio1: address xx:xx:xx:xx:xx:xx
```

---

### Step 7 — NIC Name Change on OpenBSD

OpenBSD uses deterministic interface naming tied to the driver:

| Hardware | VMware name | Proxmox name |
|----------|------------|--------------|
| `e1000` emulated | `em0` | `em0` (same) |
| VirtIO NIC | n/a | `vio0` |

If you booted with `e1000` first then switch to VirtIO, `/etc/hostname.em0` will not apply to `vio0`. Fix:

```bash
# Inside running OpenBSD VM
cp /etc/hostname.em0 /etc/hostname.vio0
# Edit /etc/hostname.vio0 if needed (usually identical content)

# Similarly for /etc/hosts, pf.conf if they reference em0 explicitly
grep -r 'em0' /etc/
```

```
[PENDING OUTPUT]
Command : ls /etc/hostname.* && cat /etc/hostname.em0
Capture : Existing hostname file and its contents
```

---

### Step 8 — `/etc/fstab` Disk Name Check

The most common OpenBSD migration failure. If `fstab` references the old disk device name, the system will hang at boot with a "cannot find root device" error.

VMware disk was probably `wd0` (IDE) or `sd0` (SCSI). On Proxmox VirtIO it will be `sd0`.

```bash
# Inside running OpenBSD VM
cat /etc/fstab
```

```
[PENDING OUTPUT]
Command : cat /etc/fstab
Capture : Full fstab
Example of what to look for:
  /dev/wd0a  /     ffs  rw,softdep  1 1   ← wd0 = IDE, will break on VirtIO
  /dev/sd0a  /     ffs  rw,softdep  1 1   ← sd0 = SCSI/VirtIO, correct
```

If `fstab` references `wd0` and you're switching to VirtIO SCSI, update it:

```bash
sed -i 's/wd0/sd0/g' /etc/fstab
```

---

### Step 9 — pf.conf NIC Reference Check

OpenBSD firewalls typically have `pf.conf` rules that reference interface names explicitly. After a NIC rename (`em0` → `vio0`) these will silently fail or
cause `pfctl` to error on boot.

```bash
grep 'em0\|em1' /etc/pf.conf
```

```
[PENDING OUTPUT]
Command : grep -n 'em0\|em1\|vio' /etc/pf.conf
Capture : Any matching lines
If em0 references exist, update to vio0 and reload:
  pfctl -f /etc/pf.conf
```

---

### Scenario 3 — Known Issues Summary

| Issue | Cause | Fix |
|-------|-------|-----|
| `virt-v2v` refuses to convert | OpenBSD not supported | Use `qemu-img convert` (Appendix A of NET-VIRT-V2V-001) |
| Kernel panic on boot | No VirtIO in kernel, or fstab wrong | Boot with legacy IDE/e1000 first |
| `cannot find root device` | `fstab` references old disk name (`wd0`) | `sed -i 's/wd0/sd0/g' /etc/fstab` |
| No network after VirtIO switch | `hostname.em0` not copied to `hostname.vio0` | `cp /etc/hostname.em0 /etc/hostname.vio0` |
| pf rules failing silently | `pf.conf` references `em0` | Update to `vio0`, `pfctl -f /etc/pf.conf` |
| Custom kernel without VirtIO | Compiled without GENERIC drivers | Boot on legacy, install GENERIC kernel, switch to VirtIO |

---

---

## Cross-Scenario Comparison

| | Debian Trixie | Windows Server 2022 | OpenBSD |
|---|---|---|---|
| `virt-v2v` support | ✅ Full | ⚠️ Partial (driver injection unreliable) | ❌ Refused |
| Conversion method | `virt-v2v` | `virt-v2v` + manual drivers | `qemu-img convert` |
| VMware Tools removal | ✅ Automatic | ✅ Automatic | N/A (not installed) |
| VirtIO driver injection | ✅ Automatic | ⚠️ Attempt, verify | ❌ Not applicable |
| Guest agent | `qemu-guest-agent` auto | `virtio-win-guest-tools.exe` manual | Not available |
| NIC rename required | Yes (`ens33`→`enp6s18`) | No (driver install handles it) | Yes (`em0`→`vio0`) |
| Legacy boot required | No | Yes (Approach B) | Possibly (if no VirtIO in kernel) |
| fstab check needed | No (udev handles it) | No | **Yes** — critical |
| pf/firewall config update | `firewallme.sh` / iptables | Windows Firewall unaffected | **Yes** — `pf.conf` NIC refs |
| Complexity | Low | Medium | High |
| Recommended operator | Junior | Senior | Senior |

---

## Output Collection Checklist

When test VMs are available, collect the following for each OS and insert into the `[PENDING OUTPUT]` blocks above.

### All scenarios

- [ ] VMX file contents (sanitised)
- [ ] Full `convert-v2v.py` interactive session
- [ ] `virt-v2v` log (`/tmp/v2v-<name>.log`)
- [ ] `qemu-img info` output on converted disk
- [ ] `qm config <VMID>` output after import
- [ ] First boot console output (serial or VGA)
- [ ] `ip link show` or equivalent after first boot

### Debian specific

- [ ] `/etc/network/interfaces` before and after NIC rename fix
- [ ] `systemctl status wg-quick@wg0`
- [ ] `wg show`
- [ ] `bash /usr/local/bin/firewallme.sh` output
- [ ] `/etc/systemd/system/wg-quick@wg0.service.d/override.conf` before/after
- [ ] `convert-v2v.py` output confirming `virt-customize` boot fixes applied
- [ ] `cat /etc/systemd/system/NetworkManager.service.d/override.conf` — confirm drop-in present post-import
- [ ] `systemctl is-enabled guestfs-firstboot` — should be disabled
- [ ] `grep interface /etc/dnsmasq.d/lan.conf` — confirm correct KVM interface name (Fix 3, manual)
- [ ] `systemctl status NetworkManager` on first boot — confirm active, not dead
- [ ] `journalctl -b 0 -p err` — confirm no ordering cycle errors

### Windows specific

- [ ] virt-v2v log showing driver injection result (success or warning)
- [ ] Device Manager screenshot/description before virtio-win install
- [ ] Device Manager screenshot/description after virtio-win install
- [ ] Services list confirming `QEMU Guest Agent` running
- [ ] Second boot output on full VirtIO hardware

### OpenBSD specific

- [ ] `virt-v2v` error output (exact refusal message)
- [ ] `qemu-img convert` progress and `qemu-img info` output
- [ ] `virt-ls` / `strings | grep virtio` kernel check output
- [ ] First boot on legacy hardware (console output)
- [ ] First boot on VirtIO hardware (console output)
- [ ] `/etc/fstab` before and after (if fix needed)
- [ ] `/etc/hostname.em0` and `/etc/hostname.vio0` contents
- [ ] `pf.conf` relevant lines and `pfctl -f` output

---

**Document End**  
*Internal Use Only — Network Engineering*  
*For questions or corrections, raise a ticket in the internal helpdesk.*

---
