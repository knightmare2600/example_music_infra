# RAC Emulator — jukebox.internal

**Document ID:** NET-RAC-001  
**Classification:** Internal — Network Engineering  
**Last Updated:** 2026-03-04  
**Depends on:** NET-BUILD-PVE-001, NET-AD-DC-001

> **What this is:** A virtual BMC/iLO node per site, running the HPE iLO
> Redfish emulator on a dedicated Debian VM. It serves a realistic Redfish
> API endpoint so engineers can learn and test against iLO-style BMC
> interfaces without requiring physical HP hardware.
>
> **What this is not:** It does not control anything. Power actions respond
> correctly but nothing happens. It is a training and development tool,
> not a management plane.

---

## Table of Contents

1. [What is Redfish / iLO](#what-is-redfish--ilo)
2. [Node Naming and IP Convention](#node-naming-and-ip-convention)
3. [Prerequisites](#prerequisites)
4. [Node Specification](#node-specification)
5. [Create the VM](#create-the-vm)
6. [Install Debian and Run rac-setup.sh](#install-debian-and-run-rac-setupsh)
7. [Verifying the Emulator](#verifying-the-emulator)
8. [Using the Redfish API](#using-the-redfish-api)
9. [BMC Profiles Available](#bmc-profiles-available)
10. [Changing Profile After Install](#changing-profile-after-install)
11. [Service Management](#service-management)
12. [Appendix A — Redfish Endpoint Reference](#appendix-a--redfish-endpoint-reference)
13. [Appendix B — Terminology](#appendix-b--terminology)
14. [Related Documents](#related-documents)

---

## What is Redfish / iLO

**iLO** (Integrated Lights-Out) is HP's brand name for their BMC
(Baseboard Management Controller) — the dedicated out-of-band management
chip embedded in HP ProLiant servers. Dell calls theirs iDRAC, Supermicro
calls theirs IPMI/BMC. They all do the same thing: give you a separate
management interface to the server that works regardless of what the host
OS is doing, even if it's powered off.

**Redfish** is the modern industry-standard REST API for BMC management,
defined by the DMTF. iLO 4 and later speak Redfish. It replaced the older
IPMI binary protocol for most management tasks. If you can make HTTP
requests, you can talk to a Redfish BMC.

**What a RAC node gives you:**

- A realistic Redfish API endpoint at `https://<RAC-IP>/redfish/v1/`
- Full HP ProLiant server inventory (CPUs, RAM, storage, NICs, fans,
  power supplies) served as real Redfish JSON responses
- Power state queries and reset actions (responds correctly, no-op)
- A target for tools like `curl`, Ansible's `redfish` modules, Rudder
  techniques, and anything else that speaks Redfish
- Somewhere safe to make mistakes — you cannot break anything

---

## Node Naming and IP Convention

RAC nodes follow the standard jukebox.internal naming convention.
RAC is Dell's name for iDRAC (Remote Access Controller) — used here
as the generic term for the virtual BMC node regardless of the HP
profile being emulated.

| Component | Convention | Example |
|-----------|-----------|---------|
| Hostname | `EXARAC<SITE><INSTANCE>` | `EXARACFAL001` |
| FQDN | `EXARAC<SITE><INSTANCE>.jukebox.internal` | `EXARACFAL001.jukebox.internal` |
| IP | Next free slot in BMC pool — see below | `192.168.76.3` |

### BMC Pool — `.2` / `.3` / `.4`

`.2`, `.3`, and `.4` are a shared pool for all BMC-type addresses at
a site — physical DRAC/iLO interfaces on PVE nodes and the RAC
emulator VM all draw from this pool. Physical PVE node BMCs consume
from `.2` upward; the RAC VM takes the next free slot.

| Physical PVE nodes at site | BMCs occupy | RAC VM gets |
|---------------------------|-------------|-------------|
| 1 (typical spoke) | `.2` | `.3` |
| 2 (hub site) | `.2`, `.3` | `.4` |
| 3 (large hub) | `.2`, `.3`, `.4` | Pool exhausted — manual address needed |

`rac-setup.sh` asks how many physical PVE nodes are at the site and
calculates the correct RAC IP automatically. On three-node sites
where the pool is fully consumed by physical BMCs it prompts for a
manual address instead.

### Full Site Address Layout (reference)

| Address | Role |
|---------|------|
| `.1` | Primary internet gateway |
| `.2` | PVE node 1 BMC (DRAC/iLO) |
| `.3` | PVE node 2 BMC — or RAC VM on single-node sites |
| `.4` | PVE node 3 BMC — or RAC VM on two-node sites |
| `.5` | PVE node 1 |
| `.6` | PVE node 2 |
| `.7` | PVE node 3 |
| `.10` | Domain Controller (EXADCS) |
| `.11`+ | SRV nodes (EXASRV) |
| `.2`–`.99` | Static allocation range |
| `.100`–`.249` | DHCP pool |
| `.250`–`.252` | RT switches |
| `.253` | Secondary internet gateway |

---

## Prerequisites

| Requirement | Detail |
|-------------|--------|
| PVE node online | Site PVE node to host the VM |
| `create-vm.py` deployed | On the site PVE node at `/usr/local/bin/` |
| Debian Trixie ISO | Available via PXE or attached ISO |
| Provisioning server reachable | `192.168.139.50` for Ansible key fetch |
| DNS working | `jukebox.internal` resolves from the site |

---

## Node Specification

| Parameter | Value |
|-----------|-------|
| Hostname | `EXARAC<SITE>001` |
| OS | Debian GNU/Linux 13 (Trixie) |
| vCPU | 1 |
| RAM | 1 GB |
| Disk | 10 GB |
| IP | `192.168.<site-octet>.15` |
| Service port | 443 (HTTPS, runs as root) |
| Redfish web UI | `https://<RAC-IP>/redfish/v1/` |
| Default credentials | `root` / `root_password` |

This is a deliberately minimal spec — the emulator is a Python Flask
app serving static JSON. 1 vCPU and 1GB RAM is generous.

---

## Create the VM

```bash
# On the site PVE node
# IP = next free BMC pool slot — .3 on a single-PVE-node site
python3 /usr/local/bin/create-vm.py \
    --name   EXARACFAL001 \
    --cores  1 \
    --memory 1024 \
    --disk   10 \
    --os     debian \
    --ip     192.168.76.3 \
    --gateway 192.168.76.1 \
    --dns    192.168.76.10 \
    --site   FAL
```

Refer to `proxmox/pve-create-vm.md` for full parameter reference.

---

## Install Debian and Run rac-setup.sh

### 1. Install Debian Trixie

Minimal install — SSH server and standard system utilities only.
No desktop environment.

### 2. Copy and run rac-setup.sh

```bash
# From your workstation or the provisioning server
scp rac-setup.sh root@192.168.76.15:/root/

# SSH in and run
ssh root@192.168.76.15
bash /root/rac-setup.sh
```

The script will prompt for:

- **Site code** — e.g. `FAL` (auto-detected from hostname if already set)
- **Instance number** — `001`
- **Site LAN octet** — e.g. `76` for the FAL `192.168.76.0/24` subnet
- **BMC profile** — presented as a numbered menu (see below)

It will then:

1. Set the hostname to `EXARAC<SITE><INSTANCE>`
2. Configure `/etc/hosts` and DNS
3. Install Python 3, git, and dependencies
4. Clone the HPE iLO Redfish emulator to `/opt/rac-emulator/`
5. Create a Python virtualenv and install Flask
6. Generate a self-signed TLS certificate matching the node FQDN
7. Write a per-site config file to `/opt/rac-emulator/rac-<SITE>.conf`
8. Install and start `rac-emulator.service` via systemd
9. Configure UFW (ports 22 and 443 only)
10. Print a summary with the Redfish URL and quick test command

### 3. Verify

```bash
# Quick smoke test — from the PVE node or any site workstation
curl -sk https://192.168.76.15/redfish/v1/ | python3 -m json.tool | head -20
```

Expected output begins with the Redfish service root:

```json
{
    "@odata.context": "/redfish/v1/$metadata#ServiceRoot",
    "@odata.id": "/redfish/v1/",
    "@odata.type": "#ServiceRoot.v1_1_0.ServiceRoot",
    "Id": "RootService",
    "Name": "HPE RESTful Root Service",
    ...
}
```

---

## Verifying the Emulator

### Service status

```bash
systemctl status rac-emulator
journalctl -u rac-emulator -n 50 --no-pager
```

### End-to-end connectivity test

```bash
# From any node on the WireGuard fabric
curl -sk \
    -u root:root_password \
    https://192.168.76.15/redfish/v1/Systems/1/ \
    | python3 -m json.tool
```

You should see a full ProLiant server inventory response including
model name, serial number, processor summary, memory summary, and
power state.

### Check certificate

```bash
openssl s_client -connect 192.168.76.15:443 -showcerts \
    </dev/null 2>/dev/null \
    | openssl x509 -noout -subject -dates
```

---

## Using the Redfish API

All requests use HTTPS with basic authentication.
The self-signed certificate requires `-k` / `--insecure` in curl,
or adding the cert to your trust store.

**Credentials:** `root` / `root_password`

### Browse the service root

```bash
BASE="https://192.168.76.15"
AUTH="-u root:root_password"

curl -sk $AUTH $BASE/redfish/v1/ | python3 -m json.tool
```

### Get system inventory

```bash
# Full system info — model, serial, CPU, RAM, power state
curl -sk $AUTH $BASE/redfish/v1/Systems/1/ | python3 -m json.tool

# Processor details
curl -sk $AUTH $BASE/redfish/v1/Systems/1/Processors/ | python3 -m json.tool

# Memory
curl -sk $AUTH $BASE/redfish/v1/Systems/1/Memory/ | python3 -m json.tool

# Storage
curl -sk $AUTH $BASE/redfish/v1/Systems/1/Storage/ | python3 -m json.tool

# Network interfaces
curl -sk $AUTH $BASE/redfish/v1/Systems/1/NetworkInterfaces/ \
    | python3 -m json.tool
```

### Power state

```bash
# Query current power state
curl -sk $AUTH $BASE/redfish/v1/Systems/1/ \
    | python3 -m json.tool \
    | grep -A1 "PowerState"
```

### Power actions (safe — no-op)

```bash
# Power on
curl -sk $AUTH -X POST \
    -H "Content-Type: application/json" \
    -d '{"ResetType": "On"}' \
    $BASE/redfish/v1/Systems/1/Actions/ComputerSystem.Reset/

# Graceful shutdown
curl -sk $AUTH -X POST \
    -H "Content-Type: application/json" \
    -d '{"ResetType": "GracefulShutdown"}' \
    $BASE/redfish/v1/Systems/1/Actions/ComputerSystem.Reset/

# Force reset
curl -sk $AUTH -X POST \
    -H "Content-Type: application/json" \
    -d '{"ResetType": "ForceRestart"}' \
    $BASE/redfish/v1/Systems/1/Actions/ComputerSystem.Reset/
```

### Chassis and manager

```bash
# Chassis (enclosure, fans, power supplies, temperatures)
curl -sk $AUTH $BASE/redfish/v1/Chassis/1/ | python3 -m json.tool

# Thermal (fan speeds, temperatures)
curl -sk $AUTH $BASE/redfish/v1/Chassis/1/Thermal/ | python3 -m json.tool

# Power (PSU status, consumption)
curl -sk $AUTH $BASE/redfish/v1/Chassis/1/Power/ | python3 -m json.tool

# Manager (iLO itself — firmware version, network config)
curl -sk $AUTH $BASE/redfish/v1/Managers/1/ | python3 -m json.tool
```

### Using with Ansible redfish modules

```yaml
# Example Ansible task — get system facts from the RAC emulator
- name: Get server facts from RAC emulator
  community.general.redfish_info:
    baseuri: "192.168.76.15"
    username: "root"
    password: "root_password"
    category: Systems
    command: GetSystemInventory
  register: redfish_facts

- name: Show power state
  debug:
    msg: "Power state: {{ redfish_facts.redfish_facts.systems[0].PowerState }}"
```

### Using with Python

```python
import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE  = "https://192.168.76.15"
AUTH  = ("root", "root_password")

# Get system info
r = requests.get(f"{BASE}/redfish/v1/Systems/1/", auth=AUTH, verify=False)
system = r.json()

print(f"Model:       {system.get('Model')}")
print(f"Serial:      {system.get('SerialNumber')}")
print(f"Power state: {system.get('PowerState')}")
print(f"CPU count:   {system.get('ProcessorSummary', {}).get('Count')}")
print(f"RAM (GB):    {system.get('MemoryGiB')}")
```

---

## BMC Profiles Available

The profile is selected during `rac-setup.sh` and stored in the
per-site config file. It determines which HP server model is emulated.

| # | Profile folder | Server model |
|---|---------------|-------------|
| 1 | `DL360` | ProLiant DL360 Gen10 Plus |
| 2 | `DL380a` | ProLiant DL380a Gen11 (2x Nvidia H100 NVL) |
| 3 | `DL380a_Gen12` | ProLiant DL380 Gen12 (4x Nvidia H200 NVL) |
| 4 | `DL360_Gen12` | ProLiant DL360 Gen12 |
| 5 | `DL365_Gen10Plus` | ProLiant DL365 Gen10 Plus (w/ HBA) |
| 6 | `DL325_Gen10Plus_FC` | ProLiant DL325 Gen10 Plus (w/ Fibre Channel) |

The DL360 Gen10 Plus (profile 1) is the most common 1U rack server
profile and the best default for general BMC familiarisation. The
Gen11/Gen12 profiles with GPU inventory are useful if the training
scenario involves AI/ML infrastructure management.

---

## Changing Profile After Install

Edit the config file and restart the service:

```bash
# Edit the site config
vim /opt/rac-emulator/rac-FAL.conf
# Change: MOCKUP_FOLDER=DL360_Gen12

# Update the service environment and restart
systemctl edit rac-emulator --force
# Add under [Service]:
# Environment="MOCKUP_FOLDER=DL360_Gen12"

systemctl restart rac-emulator
systemctl status  rac-emulator
```

Or re-run `rac-setup.sh` — it will detect the existing install,
pull latest from git, and let you select a new profile.

---

## Service Management

```bash
# Status
systemctl status rac-emulator

# Logs (live)
journalctl -fu rac-emulator

# Logs (last 100 lines)
journalctl -u rac-emulator -n 100 --no-pager

# Restart
systemctl restart rac-emulator

# Stop
systemctl stop rac-emulator

# Disable autostart
systemctl disable rac-emulator
```

### Config file location

```
/opt/rac-emulator/rac-<SITE>.conf    # per-site config
/opt/rac-emulator/certs/rac.crt      # TLS certificate
/opt/rac-emulator/certs/rac.key      # TLS private key
/opt/rac-emulator/                   # emulator install root
```

---

## Appendix A — Redfish Endpoint Reference

Key endpoints served by the emulator. All are GET unless noted.

| Endpoint | Description |
|----------|-------------|
| `/redfish/v1/` | Service root — links to all collections |
| `/redfish/v1/Systems/` | Collection of managed systems |
| `/redfish/v1/Systems/1/` | System 1 — full server inventory |
| `/redfish/v1/Systems/1/Processors/` | CPU collection |
| `/redfish/v1/Systems/1/Memory/` | RAM DIMMs |
| `/redfish/v1/Systems/1/Storage/` | Storage controllers and drives |
| `/redfish/v1/Systems/1/NetworkInterfaces/` | NIC collection |
| `/redfish/v1/Systems/1/Actions/ComputerSystem.Reset/` | Power action (POST) |
| `/redfish/v1/Chassis/` | Chassis collection |
| `/redfish/v1/Chassis/1/` | Chassis 1 — enclosure info |
| `/redfish/v1/Chassis/1/Thermal/` | Fan speeds and temperatures |
| `/redfish/v1/Chassis/1/Power/` | PSU status and power consumption |
| `/redfish/v1/Managers/` | Manager collection |
| `/redfish/v1/Managers/1/` | iLO manager — firmware, network |
| `/redfish/v1/Managers/1/EthernetInterfaces/` | iLO NIC |
| `/redfish/v1/AccountService/` | User accounts |
| `/redfish/v1/SessionService/` | Sessions |
| `/redfish/v1/EventService/` | Event subscriptions |
| `/redfish/v1/UpdateService/` | Firmware update service |

---

## Appendix B — Terminology

| Term | Full name | Description |
|------|-----------|-------------|
| **BMC** | Baseboard Management Controller | The dedicated management chip on a server motherboard. Runs independently of the host CPU and OS. Has its own NIC, power, and firmware. |
| **iLO** | Integrated Lights-Out | HP's brand name for their BMC implementation. Found on ProLiant servers. |
| **iDRAC** | Integrated Dell Remote Access Controller | Dell's equivalent of iLO. RAC in jukebox.internal node names is a nod to this. |
| **IPMI** | Intelligent Platform Management Interface | The older binary protocol for BMC communication. UDP port 623. `ipmitool` speaks this. |
| **Redfish** | — | The modern DMTF REST API standard for BMC management. HTTPS/JSON. Replaced IPMI for most tasks on modern hardware. |
| **OOB** | Out-of-Band | Management that works independently of the host OS — i.e. through the BMC rather than through the OS network stack. Works when the server is powered off or the OS is hung. |
| **In-band** | — | Management through the running OS. SSH, RDP, Ansible, etc. Requires the OS to be up and reachable. |
| **KVM** | Keyboard Video Mouse | Remote console access — seeing the screen and controlling keyboard/mouse remotely. iLO/iDRAC provide this. JetKVM provides it for machines without a BMC. |
| **Virtual media** | — | Mounting an ISO remotely so the server boots from it as if a USB or DVD were physically attached. |
| **POST** | Power-On Self Test | The firmware startup sequence before the OS boots. Visible via KVM/console even when the OS isn't up yet. |
| **UEFI** | Unified Extensible Firmware Interface | The modern replacement for BIOS. Accessible via BMC console during POST. |
| **SOL** | Serial Over LAN | Serial console access over the network via the BMC. Useful when the graphical KVM console isn't working. |
| **RAC** | Remote Access Controller | Dell's generic term for iDRAC. Used in jukebox.internal as the node naming prefix for virtual BMC nodes. |
| **Mockup** | — | In the context of this emulator: a folder of static JSON files that represent a specific server model's Redfish responses. |

---

## Related Documents

| Document | Relationship |
|----------|-------------|
| `proxmox/pve-create-vm.md` | VM creation via `create-vm.py` |
| `network-inventory.md` | `.15` RAC IP convention per site |
| `management/rudder-setup.md` | Ansible/Rudder can target RAC endpoints for Redfish training |
| `bootstrap/ad-dc-wireguard-deployment.md` | WireGuard fabric RAC nodes sit on |

---

*Internal Use Only — Network Engineering — jukebox.internal*  
*Emulator source: https://github.com/HewlettPackard/ilo-redfish-emulator*
