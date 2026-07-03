# Example Music Limited — Building an ARM64 iPXE Boot ISO

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
| MCR | `192.168.161.0/24` | `192.168.161.1` | `192.168.161.10` | `192.168.161.253` |
| LIV | `192.168.151.0/24` | `192.168.151.1` | `192.168.151.10` | `192.168.151.253` |
| GLA | `192.168.141.0/24` | `192.168.141.1` | `192.168.141.10` | `192.168.141.253` |
| NEW | `192.168.191.0/24` | `192.168.191.1` | `192.168.191.10` | `192.168.191.253` |
| KGE | `192.168.65.0/24` | `192.168.65.1` | `192.168.65.10` | `192.168.65.253` |
| FAX | `192.168.246.0/24` | `192.168.246.1` | `192.168.246.10` | `192.168.246.253` |
| TOR | `192.168.164.0/24` | `192.168.164.1` | `192.168.164.10` | `192.168.164.253` |
| MTL | `192.168.154.0/24` | `192.168.154.1` | `192.168.154.10` | `192.168.154.253` |
| SYD | `192.168.29.0/24` | `192.168.29.1` | `192.168.29.10` | `192.168.29.253` |
| CLD | `192.168.139.0/24` | `192.168.139.1` | `192.168.139.10` | `192.168.139.253` |
| ATL | `192.168.33.0/24` | `192.168.33.1` | `192.168.33.10` | `192.168.33.253` |

> **Note:** All other sites can be found in the master CSV (`sites_extended.csv`).

---

### Hostname / IP Suffix Conventions

| IP Suffix | Role | Hostname Template |
|-----------|------|-----------------|
| `.1`      | Primary Internet Gateway | `EXAFWL<SITE>001` / `EXARTR<SITE>001` |
| `.2`      | BMC pool slot 1 — DRAC/iLO | `EXARAC<SITE>001` |
| `.3`      | BMC pool slot 2 / RAC emulator (single-PVE) | `EXARAC<SITE>002` |
| `.4`      | BMC pool slot 3 / RAC emulator (two-PVE) | `EXARAC<SITE>003` |
| `.5`      | PVE node 1 | `EXAPVE<SITE>001` |
| `.6`      | PVE node 2 | `EXAPVE<SITE>002` |
| `.7`      | PVE node 3 | `EXAPVE<SITE>003` |
| `.10`     | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11`     | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.48`     | VOIP SBC / PBX (`CLD`) | `EXASBC<SITE>001` / `EXAPBX<CLD>001` |
| `.253`    | Secondary internet gateway / DNS | `EXAFWL<SITE>001` |

---

<details>
<summary>💻 Code Helpers (click to expand)</summary>

#### **Python**

```python
from site_ip import SiteIP, SiteHostnames
hosts = SiteHostnames("sites_extended.csv")
print(hosts.get_ip("ATL", "DC"))       # 192.168.33.10
print(hosts.get_hostname("CLD", ".48")) # EXAPBXCLD001
```

#### **Bash**

```bash
./site_ip.sh ATL DC      # returns 192.168.33.10
./site_ip.sh CLD .48     # returns EXAPBXCLD001
```

#### **PowerShell**

```powershell
Get-SiteIP -Site ATL -Type DC       # 192.168.33.10
Get-SiteHostname -Site CLD -IPSuffix .48  # EXAPBXCLD001
```

---

### CSV Reference

**File:** `sites_extended.csv`

**Key columns:**

| Column             | Description                          |
| ------------------ | ------------------------------------ |
| `Site`             | Short site code                      |
| `Subnet`           | `/24` subnet                         |
| `Gateway`          | `.1` IP                              |
| `DC`               | `.10` IP                             |
| `FW`               | `.253` IP                            |
| `GatewayTemplate`  | `.1` host template                   |
| `BMC1Template`     | `.2` host template                   |
| `BMC2Template`     | `.3` host template                   |
| `BMC3Template`     | `.4` host template                   |
| `PVE1Template`     | `.5` host template                   |
| `PVE2Template`     | `.6` host template                   |
| `PVE3Template`     | `.7` host template                   |
| `DC1Template`      | `.10` host template                  |
| `DC2Template`      | `.11` host template                  |
| `SBC_PBX_Template` | `.48` host template (SBC or CLD PBX) |

> **Tip:** Update `sites_extended.csv` to add new sites, subnets, or host templates. All helper scripts reference this CSV dynamically.

</details>

---

## Changelog

| Date       | Change |
|------------|--------|
| 2026-05-06 | Initial document — ARM64 iPXE ISO build procedure |

---

## Overview

VMware Fusion on Apple Silicon (ARM64) requires a UEFI-bootable ISO. The standard iPXE `genfsimg` target produces an ISO that Fusion's firmware does not recognise. The approach documented here uses GRUB as a shim — Fusion boots GRUB from a Debian-derived `efi.img`, GRUB reads a `grub.cfg` from the ISO and chainloads the iPXE EFI binary. This is the minimum deviation from standard ISO structure needed to satisfy Fusion's firmware.

**Boot chain:** Fusion firmware → `bootaa64.efi` (GRUB shim, from Debian `efi.img`) → `grubaa64.efi` (GRUB ARM64) → reads `grub.cfg` from ISO → `chainloader` → `BOOTAA64.EFI` (iPXE ARM64 EFI binary)

### Prerequisites

All steps are performed on the Edinburgh provisioning host (`EXAPRVSCOTCLD001`, `192.168.139.50`) running Debian Trixie, unless otherwise noted.

| Requirement | Notes |
|-------------|-------|
| Debian Trixie ARM64 netinst ISO | Source for `efi.img` — must be present on the build host |
| `xorriso` | ISO creation |
| `mtools` | FAT32 image manipulation |
| `gcc-aarch64-linux-gnu` | ARM64 cross-compiler |
| `make`, `liblzma-dev` | iPXE build dependencies |
| iPXE source | Cloned from `https://github.com/ipxe/ipxe.git` |
| `bootstrap.ipxe` | Embedded boot script — see `src/bootstrap.ipxe` in this repo |

Install build dependencies:

```bash
apt install gcc make gcc-aarch64-linux-gnu git liblzma-dev mtools xorriso
```

---

## Standard IP Convention

Every site follows this addressing scheme within its `/24` subnet. Exceptions are noted in individual site entries.

| Address       | Role | Hostname pattern |
|---------------|------|-----------------|
| `.1`          | Primary internet gateway | `EXAFWL<SITE>001` / `EXARTR<SITE>001` |
| `.2`          | BMC pool slot 1 — DRAC / iLO | `EXARAC<SITE>001` |
| `.3`          | BMC pool slot 2 — or RAC emulator VM on single-PVE-node sites | `EXARAC<SITE>002` |
| `.4`          | BMC pool slot 3 — or RAC emulator VM on two-PVE-node sites | `EXARAC<SITE>003` |
| `.5`          | PVE node 1 | `EXAPVE<SITE>001` |
| `.6`          | PVE node 2 | `EXAPVE<SITE>002` |
| `.7`          | PVE node 3 | `EXAPVE<SITE>003` |
| `.10`         | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11`         | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.48`         | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBC<SITE>001` |
| `.100`–`.249` | DHCP pool | — |
| `.250`–`.252` | RT switches | `EXASWI<SITE>001`–`003` |
| `.253`        | Secondary internet gateway | — |

> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM. Physical PVE node BMCs consume from `.2` upward; the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.  
> ***NB: On three-PVE-node sites the pool is fully consumed by physical BMCs.***

---

## Naming Convention Reference

| Prefix              | Role | Example |
|---------------------|------|---------|
| `EXAFWL`            | Firewall | `EXAFWLFAL001` |
| `EXARTR`            | Router | `EXARTRFAL001` |
| `EXASWI`            | Switch | `EXASWIFAL001` |
| `EXADCS` / `EXADCR` | Domain Controller (site/regional) | `EXADCSFAL001` |
| `EXAPVE`            | Proxmox VE node | `EXAPVEFAL001` |
| `EXASRV`            | Server | `EXASVRCLD001` |
| `EXARAC`            | Remote Access Console (DRAC/iLO/RAC emulator) | `EXARACFAL001` |
| `EXANAS`            | NAS | `EXANASFAL001` |
| `EXASBC`            | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBCFAL001` |
| `EXAPBX`            | PBX | `EXACLDPBX001` |
| `EXAPRV`            | Provisioning / bootstrap server | `EXAPRVFAL001` |
| `EXAWAP`            | WiFi Access Point | `EXAWAPFAL001` |
| `EXAWKS`            | Workstation | `EXAWKSFAL001` |
| `EXALAP`            | Laptop | `EXALAPFAL001` |
| `EXAMBP`            | MacBook Pro | `EXAMBPFAL001` |
| `EXAMAC`            | iMac | `EXAMACFAL001` |
| `EXASUR`            | Surface | `EXASURFAL001` |
| `EXATAB`            | Tablet | `EXATABFAL001` |
| `EXAPHN`            | Phone | `EXAPHNFAL001` |
| `EXACAM`            | Camera | `EXACAMFAL001` |
| `EXAVND` / `EXADON` | Vending machine | `EXAVNDFAL001` |
| `EXAMUS`            | Jukebox / instrument | `EXAMUSFAL001` |
| `EXAPAY`            | Payphone | `EXAPAYFAL001` |
| `EXANIX`            | Unix / legacy system | `EXANIXPER001` |

---

## Procedure

### Step 1 — Clone iPXE and build the ARM64 EFI binary

```bash
git clone https://github.com/ipxe/ipxe.git
cd ipxe/src
cp /path/to/bootstrap.ipxe bootstrap.ipxe
make CROSS=aarch64-linux-gnu- bin-arm64-efi/ipxe.efi EMBED=bootstrap.ipxe
```

Output: `bin-arm64-efi/ipxe.efi`

> **Note:** Do not specify `ARCH=` — it is calculated from the build target automatically. Use `CROSS=` not `CROSS_COMPILE=`.

---

### Step 2 — Extract `efi.img` from the Debian ARM64 ISO

Fusion's firmware requires GRUB's EFI shim to boot. We extract the EFI image directly from a known-good Debian Trixie ARM64 netinst ISO rather than building GRUB from scratch.

```bash
xorriso -indev debian-13.3.0-arm64-netinst.iso -osirrox on -extract /boot/grub/efi.img /tmp/efi.img
```

Inspect the contents to confirm structure:

```bash
mdir -i /tmp/efi.img -/ ::
```

Expected output includes `efi/boot/bootaa64.efi`, `efi/boot/grubaa64.efi`, and `efi/debian/grub.cfg`.

---

### Step 3 — Patch `grub.cfg` inside `efi.img`

The Debian `grub.cfg` inside `efi.img` points at the Debian installer. We replace it with one that chainloads the iPXE EFI binary instead.

Extract the original to understand the prefix path:

```bash
mcopy -i /tmp/efi.img ::/efi/debian/grub.cfg /tmp/grub-original.cfg
cat /tmp/grub-original.cfg
```

The original sets `$prefix` to `($root)/boot/grub` and sources the arch config from there. We redirect it to a `grub.cfg` we will place on the ISO at `boot/grub/grub.cfg`:

```bash
cat > /tmp/grub-ipxe.cfg << 'EOF'
set prefix=(cd0)/boot/grub
set root=cd0
configfile ($root)/boot/grub/grub.cfg
EOF
chmod 644 /tmp/efi.img
mcopy -oi /tmp/efi.img /tmp/grub-ipxe.cfg ::/efi/debian/grub.cfg
```

---

### Step 4 — Build the ISO directory tree

```bash
mkdir -p /tmp/ipxe-arm64/boot/grub
mkdir -p /tmp/ipxe-arm64/EFI/BOOT

# Patched efi.img — GRUB shim, boots Fusion into GRUB
cp /tmp/efi.img /tmp/ipxe-arm64/boot/grub/efi.img

# iPXE EFI binary — GRUB chainloads this
cp bin-arm64-efi/ipxe.efi /tmp/ipxe-arm64/EFI/BOOT/BOOTAA64.EFI

# grub.cfg on the ISO filesystem — read by GRUB after efi.img redirects $prefix
cat > /tmp/ipxe-arm64/boot/grub/grub.cfg << 'EOF'
set default=0
set timeout=0
menuentry "iPXE" {
  chainloader /EFI/BOOT/BOOTAA64.EFI
}
EOF
```

The resulting tree must look like this:

```
/tmp/ipxe-arm64/
├── boot/
│   └── grub/
│       ├── efi.img       ← Debian GRUB shim (patched grub.cfg inside)
│       └── grub.cfg      ← chainloader config, read by GRUB at runtime
└── EFI/
    └── BOOT/
        └── BOOTAA64.EFI  ← iPXE ARM64 EFI binary
```

---

### Step 5 — Build the ISO

The `xorriso` command mirrors the structure of the official Debian ARM64 ISO as closely as possible. This is what Fusion's firmware expects.

```bash
xorriso -as mkisofs \
  -o ipxe-arm64.iso \
  -V "iPXE_ARM64" \
  -partition_cyl_align all \
  -partition_offset 0 \
  -partition_hd_cyl 64 \
  -partition_sec_hd 32 \
  -append_partition 2 0xef /tmp/ipxe-arm64/boot/grub/efi.img \
  -c /boot.catalog \
  -e boot/grub/efi.img \
  -no-emul-boot \
  /tmp/ipxe-arm64
```

Verify the El Torito boot entry:

```bash
xorriso -indev ipxe-arm64.iso -report_el_torito as_mkisofs
```

Expected output includes `Boot record : El Torito , MBR cyl-align-all`, `-append_partition 2 0xef`, and `-e /boot/grub/efi.img`.

---

### Step 6 — Copy ISO to web server

```bash
cp ipxe-arm64.iso /path/to/webroot/ipxe/arm64/ipxe-arm64.iso
```

The ISO is then used directly in VMware Fusion — attach as a CD/DVD drive in the VM settings before first boot.

---

## Troubleshooting

### Fusion says "No bootable media"

The ISO El Torito entry is not structured correctly. Verify with `xorriso -indev ipxe-arm64.iso -report_el_torito as_mkisofs` and compare against the Debian ISO structure. The `-partition_cyl_align all` and `-append_partition 2 0xef` flags are required.

### GRUB drops to `grub>` prompt

GRUB cannot find `grub.cfg`. From the prompt, inspect:

```
echo $root
echo $prefix
ls ($root)/boot/grub/
```

`$prefix` should be `(cd0)/boot/grub` and `grub.cfg` should be listed. If `$prefix` points elsewhere, the `grub-ipxe.cfg` patch in Step 3 did not write correctly — repeat Step 3 and rebuild the ISO.

If `grub.cfg` is present but GRUB still drops to a prompt, verify the chainloader path:

```
ls ($root)/EFI/BOOT/
```

`BOOTAA64.EFI` must be present. If missing, repeat Step 4 and rebuild.

### iPXE boots but cannot reach the boot server

Check network connectivity from the iPXE shell:

```
dhcp
echo ${net0/ip}
echo ${net0/gateway}
chain http://${net0/gateway}:8000/menu.ipxe
```

On Fredericia (VMware Fusion NAT), the gateway is `172.16.124.2` and the boot server is `172.16.124.1:8000`. `bootstrap.ipxe` detects the environment by gateway IP automatically — see `bootstrap.ipxe` for the detection logic.

---

## Files Produced

| File | Location on web server | Purpose |
|------|----------------------|---------|
| `ipxe-arm64.iso` | `ipxe/arm64/` | Bootable ISO for VMware Fusion ARM64 VMs |
| `bin-arm64-efi/ipxe.efi` | Build artefact only | ARM64 iPXE EFI binary (embedded in ISO) |

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
