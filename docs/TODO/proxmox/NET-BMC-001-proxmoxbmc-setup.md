# Example Music Limited — Virtual BMC / IPMI Emulation (proxmoxbmc)

> **Document ref:** NET-BMC-001
> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Reference / Helpers

### Standard Site Subnets & Gateways

| Site | Subnet | `.1` Gateway | `.10` DC | `.253` FW |
|------|--------|-------------|----------|-----------|
| FAL | `192.168.76.0/24` | `192.168.76.1` | `192.168.76.10` | `192.168.76.253` |
| CPH | `192.168.231.0/24` | `192.168.231.1` | `192.168.231.10` | `192.168.231.253` |
| ODE | `192.168.126.0/24` | `192.168.126.1` | `192.168.126.10` | `192.168.126.253` |
| BRK | `192.168.136.0/24` | `192.168.136.1` | `192.168.136.10` | `192.168.136.253` |
| CLY | `192.168.41.0/24`  | `192.168.41.1`  | `192.168.41.10`  | `192.168.41.253`  |
| GLA | `192.168.141.0/24` | `192.168.141.1` | `192.168.141.10` | `192.168.141.253` |
| CLD | `192.168.139.0/24` | `192.168.139.1` | `192.168.139.10` | `192.168.139.253` |

> **Note:** All other sites can be found in the master CSV (`sites.csv`).

---

### Hostname / IP Suffix Conventions

| IP Suffix | Role | Hostname Template |
|-----------|------|------------------|
| `.2` | BMC pool slot 1 — DRAC/iLO or RAC emulator | `EXARAC<SITE>001` |
| `.3` | BMC pool slot 2 / RAC emulator (single-PVE) | `EXARAC<SITE>002` |
| `.4` | BMC pool slot 3 / RAC emulator (two-PVE)    | `EXARAC<SITE>003` |
| `.5` | PVE node 1 | `EXAPVE<SITE>001` |

> **BMC pool note:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM. On three-PVE-node sites the pool is fully consumed by physical BMCs.

<details>
<summary>💻 Code Helpers (click to expand)</summary>

#### Python
```python
from site_ip import SiteIP, SiteHostnames
hosts = SiteHostnames("sites.csv")
print(hosts.get_ip("CLY", "DC"))        # 192.168.41.10
print(hosts.get_hostname("CLY", ".2"))  # EXARACLY001
```

#### Bash
```bash
./site_ip.sh CLY DC     # returns 192.168.41.10
./site_ip.sh CLY .2     # returns EXARACCLY001
```

</details>

---

## Changelog

| Date       | Change |
|------------|--------|
| 2026-03-22 | Section 4b added -- Windows EMS/SAC serial console, bcdedit configuration,
|            | SAC to PowerShell workflow, worked example, Ansible playbook snippet |
| 2026-03-22 | Initial document — proxmoxbmc setup, .deb packaging, SOL/serial console configuration |
| 2026-03-22 | Added quick-reference block, --address binding explanation, VLAN selection, firewall hardening, BMC port exposure detail, troubleshooting entry for wrong bind address |

---

## Overview — What This Is and Why It Exists

If you have worked with Dell iDRAC, HP iLO, Sun's ALOM/ILOM, or Supermicro IPMI, you already understand what a BMC is: a small independent processor on the server that gives you out-of-band access to the machine regardless of what the OS is doing. You can power the machine on or off, change the boot device, and get a serial console even when the OS has completely lost the plot — all over the network using standard IPMI commands or the vendor's web interface.

Virtual machines on Proxmox do not have a physical BMC. By default the only way to get into a broken VM is via the Proxmox web console, which requires a browser and a working Proxmox session. This is fine for development work but it is not how production infrastructure operates — technicians are trained on `ipmitool`, not on clicking through a web GUI.

**proxmoxbmc** solves this. It is an implementation of the IPMI protocol that sits on the Proxmox node and proxies IPMI commands to the Proxmox API. Each VM gets its own UDP port. A technician at any machine that can reach the Proxmox node can run:

```bash
ipmitool -I lanplus -H 192.168.41.5 -p 7069 -U admin -P changeme power status
ipmitool -I lanplus -H 192.168.41.5 -p 7069 -U admin -P changeme sol activate
```

The first command returns `Chassis Power is on` or `off`. The second drops them straight into the VM's serial console — the same experience as connecting to a physical server's IPMI SOL port.

### What proxmoxbmc Gives You vs Physical DRAC/iLO

| Feature | Physical DRAC/iLO | proxmoxbmc |
|---------|-------------------|------------|
| Power on/off/reset | ✅ | ✅ |
| Boot device selection (PXE/disk/cdrom) | ✅ | ✅ |
| SOL serial console | ✅ | ✅ (requires guest config — see below) |
| Chassis status | ✅ | ✅ |
| Sensor data (CPU temp, fan speed) | ✅ | ❌ (not emulated) |
| Graphical remote KVM console | ✅ | ❌ (use Proxmox VNC/SPICE instead) |
| Virtual media (mount ISO remotely) | ✅ | ❌ |
| Firmware update | ✅ | ❌ |

The serial console via SOL is the most operationally important feature. Once configured correctly on the guest, a technician can recover a VM with a broken network stack, a wedged service, or a misconfigured `/etc/fstab` using exactly the same muscle memory they would use on physical hardware.

---

## Quick Reference

For a technician who knows what they are doing and just needs the commands.

```bash
# Set these once per session
export PBMC_HOST=192.168.41.5   # Proxmox node IP (site LAN)
export PBMC_PORT=7069           # 6000 + VMID  (EXACOFCLY001 = VMID 1069)
export PBMC_USER=admin
export PBMC_PASS=changeme       # retrieve from password manager

# Power
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS power status
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS power on
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS power off
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS power reset

# Boot device (takes effect on next power-on)
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS chassis bootdev pxe
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS chassis bootdev disk
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS chassis bootdev cdrom

# Serial over LAN console -- exit with: ~ then . (tilde, full stop)
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS sol activate

# List all registered BMCs on this node
pbmc list

# Register a new VM (run on the Proxmox node)
pbmc add --username admin --password <pass> --port $((6000 + VMID)) \
  --address <bind-ip> \
  --proxmox-address <pve-ip> \
  --token-user root@pam --token-name proxmoxbmc --token-value <token> \
  <VMID>
pbmc start <VMID>
```

| VMID | Hostname | IP | BMC port |
|------|----------|----|----------|
| 1069 | EXACOFCLY001 | 192.168.41.69 | 7069 |
| `[PLACEHOLDER]` | `[PLACEHOLDER]` | `[PLACEHOLDER]` | `[PLACEHOLDER]` |

---

## Architecture

```
Technician workstation
    ipmitool -I lanplus -H <pve-node-ip> -p <port> -U admin -P <pass> sol activate
         |
         | UDP — one port per VM (convention: 6000 + VMID)
         v
Proxmox node  (EXAPVECLY001  192.168.41.5)
    pbmcd daemon — listens on assigned ports
         |
         | proxmoxer → Proxmox API → qm start/stop/reset <vmid>
         |
         | QEMU args on VM:
         |   -device ipmi-bmc-sim,id=bmc0
         |   -device isa-ipmi-kcs,bmc=bmc0,irq=5
         v
Guest OS  (e.g. EXACOFCLY001  192.168.41.69)
    /dev/ipmi0  — IPMI device node
    ipmitool -I open ...   ← local IPMI commands from inside the guest
    ttyS0  ← serial console (GRUB + kernel + getty all configured to use it)
```

---

## Section 1 — The .deb Package

proxmoxbmc is not currently in Debian or Proxmox's package repositories. We have built a proper native `.deb` package from source with all dependencies satisfied by packaged `python3-*` apt packages. No pip, no venv, no `--break-system-packages`.

### 1.1 Package Details

| Field | Value |
|-------|-------|
| Package name | `python3-proxmoxbmc` |
| Version | `1.0.1-2` |
| Architecture | `all` (pure Python, architecture-independent) |
| Upstream | https://github.com/agnon/proxmoxbmc |
| Our fork / releases | https://github.com/knightmare2600/proxmoxbmc/releases/tag/builds |
| Upstream PR | https://github.com/agnon/proxmoxbmc/pull/10 |

### 1.2 What the Package Installs

```
/usr/bin/pbmc                                    ← CLI management tool
/usr/bin/pbmcd                                   ← daemon
/usr/lib/python3/dist-packages/proxmoxbmc/       ← Python module
/usr/lib/systemd/system/proxmoxbmc.service       ← systemd unit
```

On `dpkg -i`, the `postinst` script automatically runs `systemctl enable proxmoxbmc` and `systemctl start proxmoxbmc`. On `apt remove`, `prerm` runs `systemctl stop proxmoxbmc`. Config and state in `/var/lib/proxmoxbmc/` are left untouched on remove (preserved on `apt remove`, removed on `apt purge`).

### 1.3 Package Dependencies (all apt, no pip)

| apt package | Purpose |
|-------------|---------|
| `python3-proxmoxer` | Proxmox API client — talks to PVE on behalf of pbmcd |
| `python3-pyghmi` | IPMI server library — implements the IPMI protocol |
| `python3-cliff` | CLI framework used by the `pbmc` command |
| `python3-zmq` | ZeroMQ — inter-process communication between pbmc and pbmcd |
| `python3-pbr` | OpenStack build tooling |
| `python3-requests` | HTTP library |

All of these are present in Debian trixie, which is the base for Proxmox 8.

### 1.4 Building the Package from Source

The `debian/` directory lives in our fork. To rebuild from source on any Proxmox 8 or Debian trixie node:

```bash
# Install build tools
apt-get install -y debhelper dh-python python3-all python3-setuptools python3-pbr git

# Clone our fork (contains the debian/ directory)
git clone https://github.com/knightmare2600/proxmoxbmc.git
cd proxmoxbmc

# Build
dpkg-buildpackage -us -uc -b

# The .deb lands one directory up
ls ../python3-proxmoxbmc_*.deb
```

The `debian/` directory contains four source files:

**`debian/control`** — package metadata and dependency declarations:
```
Source: proxmoxbmc
Section: python
Priority: optional
Maintainer: [your name and email]
Build-Depends: debhelper-compat (= 13), dh-python, python3-all,
 python3-setuptools, python3-pbr
Standards-Version: 4.6.2

Package: python3-proxmoxbmc
Architecture: all
Depends: ${python3:Depends}, ${misc:Depends},
 python3-pyghmi (>= 1.2.0), python3-cliff (>= 2.8.0),
 python3-zmq (>= 19.0.0), python3-proxmoxer (>= 1.3.0),
 python3-requests, python3-pbr (>= 2.0.0)
```

**`debian/rules`** — three-line build instructions using `dh-python` and `pybuild`:
```makefile
#!/usr/bin/make -f
export PYBUILD_NAME=proxmoxbmc
%:
	dh $@ --with python3 --buildsystem=pybuild
override_dh_installsystemd:
	dh_installsystemd --name=proxmoxbmc
```

**`debian/proxmoxbmc.service`** — the systemd unit file (see Section 2.3).

**`debian/changelog`** — version history in Debian format.

---

## Section 2 — Installation on a Proxmox Node

### 2.1 Prerequisites

```bash
apt-get update
apt-get install -y python3-proxmoxer python3-pyghmi python3-cliff python3-zmq python3-pbr python3-requests ipmitool
```

### 2.2 Install the .deb

Download `python3-proxmoxbmc_1.0.1-2_all.deb` from the releases page and install:

```bash
dpkg -i python3-proxmoxbmc_1.0.1-2_all.deb
```

Verify:

```bash
systemctl status proxmoxbmc
pbmc list
```

### 2.3 The systemd Unit File

The service file installed by the package:

```ini
[Unit]
Description=proxmoxbmc -- Virtual BMC for Proxmox VE VMs
Documentation=https://github.com/agnon/proxmoxbmc
After=network-online.target pve-cluster.service
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/pbmcd --foreground
Restart=on-failure
RestartSec=5
TimeoutStopSec=20
RuntimeDirectory=proxmoxbmc
StateDirectory=proxmoxbmc

[Install]
WantedBy=multi-user.target
```

Key points: `After=pve-cluster.service` ensures pbmcd does not start before Proxmox is ready. `StateDirectory=proxmoxbmc` instructs systemd to create and manage `/var/lib/proxmoxbmc/` which is where pbmcd stores VM registration data — this persists across reboots.

### 2.4 Create a Proxmox API Token

proxmoxbmc authenticates to the Proxmox API using a token rather than a password. The token must belong to a user with sufficient permissions to start, stop, and reset VMs.

Via the Proxmox web UI: `Datacenter` → `Permissions` → `API Tokens` → `Add`

- User: `root@pam`
- Token ID: `proxmoxbmc`
- Privilege separation: **unchecked**

Copy the token value immediately — it is shown only once.

Via CLI on the Proxmox node:

```bash
pveum user token add root@pam proxmoxbmc --privsep=0
```

> **Credentials:** Store the token value in the password manager under the entry for the Proxmox node. Do not put it in this document or in any script committed to version control.

### 2.5 Register a VM

Each VM that should have IPMI access must be registered individually. The port convention is `6000 + VMID`.

```bash
# Example: VMID 1069 (EXACOFCLY001) → port 7069
# --address binds only to the provisioning VLAN IP -- see Section 2.6
pbmc add --username admin --password <bmc-password-from-password-manager> --port 7069 --address 192.168.139.5 \
  --proxmox-address 192.168.41.5 --token-user root@pam --token-name proxmoxbmc --token-value <token-from-password-manager> 1069

pbmc start 1069
pbmc list
```

Expected output from `pbmc list`:

```
+------+---------+------+---------+--------+
| Name | Address | Port | Status  | Active |
+------+---------+------+---------+--------+
| 1069 | ::      | 7069 | running | True   |
+------+---------+------+---------+--------+
```

### 2.6 Network Exposure — Which Interfaces proxmoxbmc Listens On

**This section is important. Read it before registering any VM.**

By default, proxmoxbmc binds to `0.0.0.0` — meaning it listens on **all interfaces** on the Proxmox node, including the site LAN bridge. Any machine that can reach the Proxmox node's IP on the registered UDP port can send IPMI commands. The firewall rules below are therefore not optional — they are the primary access control mechanism.

#### The `--address` parameter — binding to a specific interface

The recommended approach is to use `pbmc add --address <ip>` to bind each BMC listener to a specific IP rather than all interfaces. This provides defence in depth — even if the firewall rules are misconfigured, the listener simply is not reachable on other interfaces.

The IP you bind to determines which VLAN the BMC is reachable from:

| Bind address | Reachable from |
|--------------|---------------|
| `0.0.0.0` (default) | All interfaces — site LAN, provisioning VLAN, everything |
| `192.168.139.5` (provisioning VLAN IP) | Provisioning VLAN only (`192.168.139.0/24`) |
| `192.168.41.5` (site LAN IP) | Site LAN only (`192.168.41.0/24`) |
| `127.0.0.1` | Proxmox node itself only — useful for testing |

For production, binding to the provisioning VLAN IP is recommended:

```bash
pbmc add   --username admin   --password <bmc-password-from-password-manager>   --port 7069   --address 192.168.139.5   --proxmox-address 192.168.41.5   --token-user root@pam   --token-name proxmoxbmc   --token-value <token-from-password-manager>   1069
```

#### VLAN selection

proxmoxbmc has no direct VLAN-awareness — it does not tag traffic or select a VLAN by ID. VLAN membership is determined entirely by which IP address you bind to. On the Proxmox node, each VLAN-aware bridge interface has its own IP:

```bash
# Check which IPs and interfaces are present on the Proxmox node
ip -brief addr show
# Example output:
# vmbr0   UP  192.168.41.5/24      ← site LAN (VLAN 41 on upstream switch)
# vmbr1   UP  192.168.139.5/24     ← provisioning VLAN
```

Binding to `192.168.139.5` restricts IPMI access to machines on the provisioning VLAN. Binding to `192.168.41.5` allows access from the site LAN. There is no way to restrict to a specific VLAN ID within proxmoxbmc itself — use the `--address` binding and firewall rules together.

#### Firewall rules

Even when using `--address` binding, firewall rules provide the outer layer of protection. IPMI must never be exposed to the internet.

```bash
# On the Proxmox node -- allow IPMI ports from provisioning VLAN only
# Adjust the range to match your registered VMs
for port in $(seq 7000 7200); do
  ufw allow from 192.168.139.0/24 to any port $port proto udp
done

# Explicitly deny from everywhere else (belt and braces)
for port in $(seq 7000 7200); do
  ufw deny to any port $port proto udp
done

ufw reload
ufw status numbered
```

### 2.7 Removing a VM Registration

```bash
pbmc stop 1069
pbmc delete 1069
```

---

## Section 3 — Using ipmitool

Once a VM is registered and the BMC service is running, standard `ipmitool` commands work exactly as they would against physical hardware.

```bash
# Set these for convenience
PBMC_HOST=192.168.41.5   # IP of the Proxmox node
PBMC_PORT=7069           # 6000 + VMID
PBMC_USER=admin
PBMC_PASS=changeme       # use password manager value

# Power control
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS power status
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS power on
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS power off
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS power reset

# Boot device (persistent=false means next boot only, which is usually what you want)
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS chassis bootdev pxe
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS chassis bootdev disk
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS chassis bootdev cdrom

# SOL serial console
ipmitool -I lanplus -H $PBMC_HOST -p $PBMC_PORT -U $PBMC_USER -P $PBMC_PASS sol activate

# Exit SOL: press ~ then . (tilde then full stop)
# This is the standard SSH/SOL escape sequence
```

> **proxmoxbmc boot device assumptions:** `disk` maps to `scsi0`, `cdrom` maps to `ide2`, and `pxe` maps to `net0`. These match the Proxmox VM naming conventions used by `create-vm.py`.

---

## Section 4 — Guest OS Configuration for SOL Console

This section covers what needs to be done to a Linux guest so that the serial console actually works end-to-end. Think of it as the equivalent of enabling "Console Redirection" in a physical server's BIOS and then configuring the OS to match.

The goal is console output and a login prompt on `ttyS0` from the moment GRUB starts counting down through kernel boot messages, through to a full login prompt — simultaneously with the normal VGA/SPICE console. Both consoles work at once.

### 4.1 Why This Is Still Necessary

Modern systemd-based distributions will automatically start a getty on `ttyS0` if `console=ttyS0` appears on the kernel command line. However this only covers the running OS. To get output during GRUB (so you can select a boot entry or enter recovery mode over SOL) and during early kernel boot (initramfs, filesystem checks), GRUB itself must also be configured to use the serial port. These are three separate layers — QEMU/SeaBIOS, GRUB, and the OS — and all three need to be consistent.

### 4.2 Layer 1 — QEMU / SeaBIOS (the "BIOS" layer)

In Proxmox, the VM must have `serial0: socket` set in its configuration. This tells QEMU to create a serial device and expose it as a Unix socket on the host. SeaBIOS (the default Proxmox BIOS) emulates a standard 16550A UART on the ISA bus at `0x3f8 IRQ 4` — this is `ttyS0` inside the guest.

When BMC emulation is also enabled (as configured by `create-vm.py`), the VM config will look like:

```
serial0: socket
args: -device ipmi-bmc-sim,id=bmc0 -device isa-ipmi-kcs,bmc=bmc0,irq=5
```

SeaBIOS does not itself output to the serial port by default — that is a BIOS-level serial console feature that physical servers have but QEMU's SeaBIOS does not fully implement in the same way. What matters is that the UART exists and is functional for GRUB and Linux to use.

You can verify the UART is present from inside the guest:

```bash
dmesg | grep tty
# Expected output:
# [    0.000000] console [tty0] enabled
# [    0.464947] 00:01: ttyS0 at I/O 0x3f8 (irq = 4) is a 16550A
```

If you see a `16550A` at `0x3f8` then the serial device is present and functional.

### 4.3 Layer 2 — GRUB

GRUB must be configured to output its menu and prompts to both the VGA console and the serial port simultaneously. Edit `/etc/default/grub`:

```bash
# Both tty0 (VGA/SPICE) and ttyS0 (serial/SOL) receive output.
# The order matters: ttyS0 first means the serial port gets kernel messages
# from the earliest possible point. tty0 second keeps the normal console working.
GRUB_CMDLINE_LINUX="console=ttyS0,115200n8 console=tty0"

# Tell GRUB to output its own menu to both serial and VGA.
# Without this, GRUB only appears on VGA even if the kernel later uses serial.
GRUB_TERMINAL="serial console"

# Serial port parameters must match the kernel console= line above.
GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"

# Increase timeout slightly -- gives time to connect via SOL before auto-boot
GRUB_TIMEOUT=10
```

After editing, regenerate the GRUB config:

```bash
# Debian / Ubuntu
update-grub

# Arch Linux
grub-mkconfig -o /boot/grub/grub.cfg
```

> **GRUB_TERMINAL note:** `"serial console"` (both, space-separated) outputs to both simultaneously. `"serial"` alone would break the VGA/SPICE console which you always want to keep working as a fallback.

### 4.4 Layer 3 — The Running OS (systemd getty)

With `console=ttyS0` on the kernel command line, modern systemd automatically starts `serial-getty@ttyS0.service` — you do not need to enable it manually. However it is good practice to verify it is running and to enable it explicitly as a belt-and-braces measure, particularly on older distributions or minimal installs:

```bash
systemctl enable serial-getty@ttyS0.service
systemctl start serial-getty@ttyS0.service
systemctl status serial-getty@ttyS0.service
```

If you see a login prompt over SOL after boot then this layer is working.

> **Conflict warning:** If you have both `console-getty.service` and `serial-getty@ttyS0.service` active and they both try to own `ttyS0`, you will see garbled output or no login prompt. Check with `systemctl status 'getty@tty*' 'serial-getty@tty*'`. Only one service should own `ttyS0`.

### 4.5 Worked Example — EXACOFCLY001 (Coffee Pot, Clydebank)

`EXACOFCLY001` is an internet-connected coffee machine running embedded Linux at `192.168.41.69` in the Clydebank office. It is used here as a concrete example of bringing a VM "up to BMC standards" — the same steps apply to any Linux guest.

**Starting state:** VM created with `create-vm.py`, BMC emulation enabled (KCS interface), SPICE console, standard install. Serial console not configured. ipmitool SOL connects but shows nothing.

**Step 1 — Verify the serial device exists:**

```bash
ssh ansible@192.168.41.69
dmesg | grep tty
# Should show: ttyS0 at I/O 0x3f8 (irq = 4) is a 16550A
```

If no `ttyS0` appears, check that `serial0: socket` is set in the VM's Proxmox config and that the VM was restarted after the BMC args were added.

**Step 2 — Configure GRUB:**

```bash
sudo cp /etc/default/grub /etc/default/grub.bak

sudo tee /etc/default/grub << 'EOF'
GRUB_DEFAULT=0
GRUB_TIMEOUT=10
GRUB_DISTRIBUTOR=$(lsb_release -i -s 2>/dev/null || echo Linux)
GRUB_CMDLINE_LINUX="console=ttyS0,115200n8 console=tty0"
GRUB_CMDLINE_LINUX_DEFAULT=""
GRUB_TERMINAL="serial console"
GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"
EOF

sudo update-grub
```

**Step 3 — Enable serial getty:**

```bash
sudo systemctl enable serial-getty@ttyS0.service
```

The explicit enable is belt-and-braces — systemd will auto-start it from the kernel cmdline anyway, but being explicit makes the intent clear and survives any future kernel cmdline changes.

**Step 4 — Reboot:**

```bash
sudo reboot
```

**Step 5 — Verify via SOL:**

From a technician workstation (or from `EXAANSCLD001`):

```bash
ipmitool -I lanplus -H 192.168.41.5 -p 7069 -U admin -P changeme sol activate
```

You should see GRUB output, then kernel boot messages, then a login prompt. Press `~.` to exit SOL.

**Step 6 — Verify VGA/SPICE console still works:**

Open the Proxmox web console for the VM and confirm a normal login prompt is present there too.

**Step 7 — Verify IPMI power control:**

```bash
ipmitool -I lanplus -H 192.168.41.5 -p 7069 -U admin -P changeme power status
# Chassis Power is on

ipmitool -I lanplus -H 192.168.41.5 -p 7069 -U admin -P changeme chassis bootdev pxe
# Set chassis boot device to pxe
```

---

## Section 4b — Windows Guest: EMS / SAC Serial Console

This section covers the Windows equivalent of Section 4's Linux serial console configuration. The goal is identical: a rescue console accessible over SOL from `ipmitool` that works even when the OS is wedged, and a boot menu visible on the serial port so you can select boot entries or enter recovery mode without a screen.

### Background for those coming from physical hardware

On a physical Dell server with iDRAC, the SAC (Special Administration Console) is available automatically because the iDRAC handles serial redirection at the firmware level. With a VM you have to configure Windows itself to redirect to COM1 — the equivalent of telling a physical server's BIOS to enable "Console Redirection" and then configuring Windows to honour it.

Two things need to be configured:

**Windows Boot Manager (BCD)** — this is the GRUB equivalent. `bcdedit` redirects the boot menu to COM1 so you see the entry selection screen over SOL at power-on, can press F8 for advanced options, and can boot into WinRE (Windows Recovery Environment) over serial.

**EMS / SAC** — once the OS is running, SAC is a lightweight background console that accepts commands over the serial port. It is not a full shell — it is a small set of management commands — but from SAC you can open a CMD channel and from CMD you can launch PowerShell. Full PowerShell session over SOL.

### 4b.1 Prerequisites

- VM must have `serial0: socket` in its Proxmox config (set by `create-vm.py` when BMC emulation is enabled)
- COM1 must be visible inside the guest: `Get-WmiObject Win32_SerialPort | Where-Object DeviceID -eq COM1`
- Edition must support SAC: Windows Server 2016/2019/2022/2025 Standard and Datacenter. SAC is **not** present in Windows 10/11 or Server Essentials.

### 4b.2 Configuration — `bcdedit` commands

Run once on the VM as Administrator (or via Ansible, or `Join-DomainAndBootstrap.ps1` Stage 17b does this automatically):

```powershell
# Redirect the Windows Boot Manager menu to COM1
# Without this the boot menu is silent on serial even if EMS is on
bcdedit /set '{bootmgr}' displaybootmenu yes
bcdedit /set '{bootmgr}' timeout 10
bcdedit /set '{bootmgr}' bootems yes

# Enable EMS for the running OS boot entry
bcdedit /ems '{current}' on

# Set COM1 at 115200 8N1 -- must match Proxmox serial0 and ipmitool
bcdedit /emssettings EMSPORT:1 EMSBAUDRATE:115200

# Verify
bcdedit /enum '{bootmgr}'
# Should show: bootems   Yes
# Should show: emssettings EMSPORT:1 EMSBAUDRATE:115200
```

Then reboot. After reboot, SAC is active and the boot menu appears on COM1.

> **Server Core note:** `Join-DomainAndBootstrap.ps1` enables EMS automatically on Server Core without prompting — there is no GUI recovery path on Core, so serial is essential.

### 4b.3 What you see over SOL after configuration

**At power-on (boot menu):**

```
Windows Boot Manager
--------------------
Choose an operating system to start, or press TAB to select a tool:

   Windows Server 2022 Datacenter
   Windows Server 2022 Datacenter [EMS Enabled]

   To specify an advanced option for this choice, press F8.
   Seconds until the highlighted choice will be started automatically: 10

ENTER=Choose  TAB=Menu  ESC=Cancel
```

Press F8 on the highlighted entry for advanced boot options (Safe Mode, WinRE, disable driver signature enforcement etc.) — all over serial, no screen needed.

**Once booted — the SAC prompt:**

```
Computer is booting, SAC started and initialized.
Use the "ch -?" command for information about using channels.
To authenticate on this channel, please enter the user name and password.

SAC>
```

### 4b.4 Getting to PowerShell via SAC

```
SAC> cmd
The Command Prompt session was successfully launched.

SAC> ch
Channel List
(Use "ch -?" for information on using channels)
# Channel  Type    Status
0          SAC     Active
1  Cmd0001 CMD     Active

SAC> ch -sn Cmd0001

Username: Administrator
Domain:               <- press Enter for local account
Password:             <- from password manager

Microsoft Windows [Version 10.0.20348.xxx]
(c) Microsoft Corporation. All rights reserved.

C:\Windows\system32> powershell
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

PS C:\Windows\system32> Get-Service | Where-Object Status -eq Stopped
```

From here you have a full PowerShell session. You can fix a broken network stack, repair a misconfigured service, unlock an account, or do anything you would do at a local console — all over the ipmitool SOL connection.

**Exit SOL:** `~` then `.` (tilde, full stop) — the standard ipmitool escape.

**Exit SAC channel and return to SAC prompt:** press `<Esc>` `<Tab>` `<Esc>`.

### 4b.5 Worked Example — EXADCSCLY001 (Domain Controller, Clydebank)

Starting state: Windows Server 2022 DC, SAC not configured, ipmitool SOL connects but shows nothing.

**Step 1 — Verify COM1 is present:**

```powershell
Get-WmiObject Win32_SerialPort | Select-Object DeviceID, Description
# Expected: DeviceID COM1, Description Communications Port
```

If COM1 is missing, check `serial0: socket` is in the VM config:

```bash
# On the Proxmox node
qm config <vmid> | grep serial
# Expected: serial0: socket
```

**Step 2 — Run `bcdedit` commands** (Section 4b.2 above, or re-run `Join-DomainAndBootstrap.ps1` if Stage 17b was skipped).

**Step 3 — Reboot and verify over SOL:**

```bash
ipmitool -I lanplus -H 192.168.41.5 -p 7010 -U admin -P changeme sol activate
```

You should see the boot menu, then kernel/driver messages, then the SAC prompt.

**Step 4 — Verify PowerShell access works** (Section 4b.4 above).

### 4b.6 Ansible — Apply EMS Configuration Across the Estate

Once `Join-DomainAndBootstrap.ps1` has run on a machine and configured EMS, there is nothing further to do. For machines that were built before Stage 17b was added, apply via Ansible:

```yaml
# roles/windows_ems/tasks/main.yml
- name: Enable EMS boot manager serial redirect
  win_shell: |
    bcdedit /set '{bootmgr}' displaybootmenu yes
    bcdedit /set '{bootmgr}' timeout 10
    bcdedit /set '{bootmgr}' bootems yes
    bcdedit /ems '{current}' on
    bcdedit /emssettings EMSPORT:1 EMSBAUDRATE:115200
  register: ems_result
  changed_when: true

- name: Set sacsvr to automatic
  win_service:
    name: sacsvr
    start_mode: auto
  ignore_errors: true   # not present on all editions

- name: Verify EMS settings
  win_shell: bcdedit /enum '{bootmgr}'
  register: bcd_out

- name: Show BCD output
  debug:
    var: bcd_out.stdout_lines
```

---

## Section 5 — BMC NIC (The IPMI LAN Channel)

### What this is — for those familiar with physical BMC hardware

On a physical Dell server, the iDRAC has its own dedicated network port (the "iDRAC port" on the rear panel, sometimes shared with LOM1 depending on configuration). This is a completely separate network interface from the host OS's NICs — it runs independently of the OS, even when the OS is powered off or crashed. HP iLO works the same way. This separation is what makes out-of-band management so reliable.

With proxmoxbmc the equivalent is the Proxmox node's own network interface. proxmoxbmc listens on a UDP port on the Proxmox node's IP address. The "BMC network" is therefore the Proxmox node's management network. There is no separate physical NIC for the BMC — the Proxmox node IS the BMC from a networking perspective.

### Implications for firewall rules

On physical infrastructure, IPMI traffic goes to the iDRAC/iLO IP which is on a dedicated management VLAN. With proxmoxbmc, IPMI traffic goes to the Proxmox node IP on a high UDP port. Your firewall rules should therefore restrict these ports to the management VLAN only — the provisioning network (`192.168.139.0/24`) in this estate.

### The `ipmi-bmc-sim` device inside the guest

When `create-vm.py` adds BMC emulation, it adds the following to the VM's QEMU args:

```
-device ipmi-bmc-sim,id=bmc0 -device isa-ipmi-kcs,bmc=bmc0,irq=5
```

The `ipmi-bmc-sim` is QEMU's built-in IPMI BMC simulator. It presents itself to the guest OS as an IPMI KCS (Keyboard Controller Style) interface on the ISA bus. This creates `/dev/ipmi0` inside the guest — the same device node you would see on a physical server with a real BMC.

KCS is the recommended interface for Linux guests. BT (Block Transfer) is slightly faster but KCS has broader driver support and is what all major distributions ship drivers for in the standard kernel.

From inside the guest, once `/dev/ipmi0` exists, the `ipmitool` package can be used for local IPMI operations:

```bash
# Install inside the guest
apt-get install -y ipmitool

# Local commands (no -I lanplus, no host/port needed -- uses /dev/ipmi0 directly)
ipmitool mc info          # shows BMC firmware info (simulated values)
ipmitool power status     # chassis power status
ipmitool chassis status   # full chassis status
ipmitool lan print        # shows IPMI LAN channel config
```

The distinction between the "local" interface (`-I open`, uses `/dev/ipmi0`) and the "remote" interface (`-I lanplus`, uses the network) maps exactly to the physical server equivalent: on a Dell box you can run `ipmitool -I open mc info` while logged into the OS to query the iDRAC locally, or `ipmitool -I lanplus -H <idrac-ip>` from another machine to query it remotely.

---

## Section 6 — Port Convention

| VMID range | Port formula | Example |
|------------|-------------|---------|
| Any VMID | `6000 + VMID` | VMID 1069 → port 7069 |

This works for VMIDs up to 59535 before exceeding port 65535. In practice Proxmox VMIDs start at 100 (so minimum port 6100) and rarely exceed a few thousand in a lab environment.

The advantage of this convention is that given a VMID you can always derive the port, and given a port you can always derive the VMID. There is no lookup table to maintain.

---

## Section 7 — Production Installation

> **[PLACEHOLDER — to be completed when rolling out to production nodes]**

### Production prerequisites

- [ ] Proxmox 8.x node confirmed running Debian trixie base
- [ ] All apt dependencies installed (Section 2.1)
- [ ] `python3-proxmoxbmc_1.0.1-2_all.deb` transferred to node
- [ ] API token created and value recorded in password manager (Section 2.4)
- [ ] Firewall rules reviewed and applied for site VLAN (Section 2.6)

### Production node deployment steps

```bash
# [PLACEHOLDER — fill in production node hostname and IPs]
# Example structure:
ssh ansible@EXAPVE<SITE>001

apt-get update
apt-get install -y python3-proxmoxer python3-pyghmi python3-cliff \
  python3-zmq python3-pbr python3-requests ipmitool

dpkg -i python3-proxmoxbmc_1.0.1-2_all.deb

systemctl status proxmoxbmc

# Register VMs -- one pbmc add per VM that needs IPMI access
# [PLACEHOLDER -- list of VMIDs to register at this site]
```

### Per-VM checklist for production

For each VM requiring BMC access:

- [ ] VM created with BMC emulation enabled in `create-vm.py` (KCS interface)
- [ ] `serial0: socket` confirmed in VM config (`qm config <vmid>`)
- [ ] GRUB configured for dual console output (Section 4.3)
- [ ] Serial getty enabled and confirmed working (Section 4.4)
- [ ] SOL tested via `ipmitool sol activate` (Section 3)
- [ ] VGA/SPICE console confirmed still working (Section 4.5 step 6)
- [ ] VM registered in pbmcd (`pbmc add` + `pbmc start`) (Section 2.5)
- [ ] Power control tested (`ipmitool power status`) (Section 3)

---

## Appendix — Troubleshooting

### SOL connects but shows nothing

The most common cause is that GRUB and/or the kernel are not configured to output to `ttyS0`. Work through Section 4 in order. Verify with `dmesg | grep tty` from inside the guest that `ttyS0 at I/O 0x3f8 is a 16550A` appears — if it does not, the serial device is not present and you need to check `serial0: socket` in the VM config.

### SOL shows boot messages but no login prompt

`serial-getty@ttyS0.service` is not running. Run `systemctl enable --now serial-getty@ttyS0.service`. Also check for getty conflicts with `systemctl status 'getty@tty*' 'serial-getty@tty*'`.

### ipmitool: `Error in open session response message: insufficient resources for session`

Usually means the port is not open or pbmcd is not listening. Check `pbmc list` on the Proxmox node and verify the firewall rules permit UDP on the relevant port.

### ipmitool: `Error: Unable to establish IPMI v2 / RMCP+ session`

Authentication failure. Verify `--username` and `--password` match the values used in `pbmc add`. IPMI passwords are case-sensitive.

### pbmcd not starting after reboot

Check `journalctl -u proxmoxbmc`. The most common cause on Proxmox is that `pve-cluster.service` has not started yet when pbmcd tries to contact the API. The `After=pve-cluster.service` in the unit file handles this, but a misconfigured cluster or slow disk can delay `pve-cluster`. Run `systemctl restart proxmoxbmc` once the node is fully up.

### BMC reachable from wrong network / not reachable at all

Check what IP `pbmc add --address` was bound to:

```bash
pbmc list
# The Address column shows the bind IP.
# If it shows "::" or "0.0.0.0" the BMC is listening on all interfaces.
```

If the bind IP is wrong, remove and re-add the registration:

```bash
pbmc stop <VMID>
pbmc delete <VMID>
pbmc add --address <correct-ip> ... <VMID>
pbmc start <VMID>
```

Also verify the interface with the bind IP is actually up and has that IP:

```bash
ip -brief addr show
```

### GRUB menu only appears on VGA, not on SOL

`GRUB_TERMINAL` is not set to `"serial console"`. Check `/etc/default/grub` and re-run `update-grub`. Note the value must be `"serial console"` (both words, space-separated) — `"serial"` alone disables the VGA output which breaks the SPICE console.

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
