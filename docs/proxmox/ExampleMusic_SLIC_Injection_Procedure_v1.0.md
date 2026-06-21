# Example Music Limited — Proxmox VM SLIC Table Injection & SMBIOS Spoofing

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Applies To:** Proxmox VE 9.x / QEMU 10.x — SeaBIOS VMs (non-UEFI)
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Changelog

| Date       | Version | Change           | Author               |
|------------|---------|------------------|----------------------|
| 2025-04-26 | 1.0     | Initial document | Infrastructure Team  |

---

## Overview

This procedure covers injecting a Dell SLIC (Software Licensing Infrastructure Certificate) ACPI table into a Proxmox KVM/QEMU virtual machine, and spoofing the SMBIOS Type 1 fields so that Windows reports correct Dell OEM hardware identity.

The SLIC table enables OEM licence activation — Windows checks for it during activation to confirm the machine is the licensed OEM hardware. SMBIOS spoofing makes tools such as `Get-CimInstance` report Dell manufacturer strings rather than QEMU defaults.

> ⚠️ **WARNING**
> - This procedure applies only to SeaBIOS VMs (no `bios: ovmf` line in `qm config`).
> - UEFI/OVMF VMs require a different approach and are not covered here.
> - The `-bios` flag in QEMU args is **not** the correct method for SLIC injection and will prevent the VM from starting.

---

## Prerequisites

| Requirement   | Detail                                                              |
|---------------|---------------------------------------------------------------------|
| Proxmox VE    | 9.x (tested on 9.1.8)                                              |
| QEMU          | 10.x (tested on 10.1.2)                                            |
| VM firmware   | SeaBIOS — no `bios: ovmf` in `qm config`                           |
| Source ROM    | Full BIOS ROM containing embedded SLIC table                        |
| OS access     | SSH to Proxmox node as a user with sudo                             |
| Tools         | `xxd`, `strings`, `dd`, `grep` (standard), `acpica-tools`          |

---

## Step 1 — Install Required Tools

The `xxd` utility is part of the `vim-common` package. Install `acpica-tools` which provides `acpixtract` and `acpidump` for ACPI table work.

```bash
sudo apt update
sudo apt install vim-common acpica-tools -y
```

**Expected result:** Both packages install without error. `xxd --version` and `acpidump --version` return output.

---

## Step 2 — Inspect the Source ROM File

Before extracting anything, confirm the ROM file is a full BIOS image and that a SLIC table is present within it.

### 2.1 — Check file size and type

```bash
file /usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM
wc -c /usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM
```

Output:

```
/usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM: ISO-8859 text, with very long lines (65536), with no line terminators
524288 /usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM
```

> ℹ️ **NOTE:** 524288 bytes = 512 KB. This is a full BIOS ROM, not a standalone SLIC binary. The `file` command misidentifies it as text — this is normal for binary firmware blobs.

### 2.2 — Confirm SLIC table is present

```bash
xxd /usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM | grep -i "SLIC\|RSDT\|RSDP\|XSDT" | head -20
strings /usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM | grep -E "^(SLIC|RSDT|RSDP|XSDT|FACP|DSDT)" | head -20
strings /usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM | grep -iE "dell|oem|microsoft" | head -20
```

Output:

```
SLICv
DELL  PE_SC3
DELL
DELL  PE_SC3  WINDOWS
```

**Expected result:** SLIC signature found. OEM strings confirm Dell PE_SC3 with a Windows OEM marker.

---

## Step 3 — Locate the SLIC Table Offset

Use `grep` to find the exact byte offset of the SLIC signature within the ROM, then dump 64 bytes from that offset to read the ACPI table header.

```bash
grep -obUaP "SLIC" /usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM
```

Output:

```
398767:SLIC
```

```bash
xxd -s 398767 -l 64 /usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM
```

Output:

```
000615af: 534c 4943 7601 0000 0100 4445 4c4c 2020  SLICv.....DELL
000615bf: 5045 5f53 4333 2020 0100 0000 4445 4c4c  PE_SC3  ....DELL
000615cf: 0100 0000 0000 0000 9c00 0000 0602 0000  ................
000615df: 0024 0000 5253 4131 0004 0000 0100 0100  .$..RSA1........
```

### Header Decode

| Bytes (hex) | Field         | Value                    | Notes                          |
|-------------|---------------|--------------------------|--------------------------------|
| 00–03       | Signature     | `534c 4943` = `SLIC`     | Table identifier               |
| 04–07       | Length        | `7601 0000` = `0x176` = 374 | Total table size in bytes   |
| 08          | Revision      | `01`                     | SLIC v2.0                      |
| 10–15       | OEM ID        | `DELL  `                 | 6-char OEM identifier          |
| 16–23       | OEM Table ID  | `PE_SC3  `               | 8-char table identifier        |
| 36–39       | RSA1          | Present                  | Public key block — confirms v2.0 SLIC |

---

## Step 4 — Extract the SLIC Table

Use `dd` to extract exactly 374 bytes from offset 398767 into a standalone binary file.

```bash
sudo dd if=/usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM bs=1 skip=398767 count=374 of=/usr/share/kvm/DELL_PE_SC3.SLIC.bin
```

Output:

```
374+0 records in
374+0 records out
374 bytes copied, 0.00341842 s, 109 kB/s
```

### Verify the extraction

```bash
wc -c /usr/share/kvm/DELL_PE_SC3.SLIC.bin
xxd -s 0 -l 32 /usr/share/kvm/DELL_PE_SC3.SLIC.bin
```

Output:

```
374 /usr/share/kvm/DELL_PE_SC3.SLIC.bin
00000000: 534c 4943 7601 0000 0100 4445 4c4c 2020  SLICv.....DELL
00000010: 5045 5f53 4333 2020 0100 0000 4445 4c4c  PE_SC3  ....DELL
```

> ✔️ **EXPECTED RESULT:**
> - File is exactly 374 bytes.
> - First four bytes are `534c 4943` (`SLIC`).
> - OEM fields show `DELL` and `PE_SC3`.
> - If any of these checks fail, repeat Steps 3–4. Do not proceed with a corrupt extraction.

---

## Step 5 — Remove the Broken VM Args

The original `args` line used `-bios` which is incorrect for SLIC injection and prevents the VM from starting. Remove it cleanly before setting the correct value.

> ⚠️ **WARNING:** Confirm the VM is shut down before modifying args. Use: `sudo qm status <vmid>`

```bash
sudo qm set 1029 --delete args
```

Output:

```
update VM 1029: -delete args
```

---

## Step 6 — Set Correct ACPI Table and SMBIOS Args

Set both the `-acpitable` flag (injects the SLIC table) and the `-smbios` flag (spoofs hardware identity) in a single `args` value.

> ⚠️ **WARNING:**
> - Proxmox 9.x requires `smbios1` field values to be base64 encoded when set via `--smbios1`.
> - However, Proxmox does **not** decode them before passing to QEMU, so QEMU receives raw base64 strings and Windows shows garbled values.
> - The correct approach is to bypass `--smbios1` entirely and pass plain-text values via `args`.
> - Spaces in `-smbios` field values cause argument splitting — use underscores instead (e.g. `Dell_Inc.` not `Dell Inc.`).

```bash
sudo qm set 1029 --args '-acpitable file=/usr/share/kvm/DELL_PE_SC3.SLIC.bin -smbios type=1,uuid=ab05d25c-e5a7-4229-bf07-310e16bfa0db,manufacturer=Dell_Inc.,product=PowerEdge_SC3,version=2.7,serial=GX7K3P1,sku=PowerEdge_SC3,family=PowerEdge'
```

Output:

```
update VM 1029: -args -acpitable file=/usr/share/kvm/DELL_PE_SC3.SLIC.bin -smbios type=1,uuid=ab05d25c-e5a7-4229-bf07-310e16bfa0db,manufacturer=Dell_Inc.,product=PowerEdge_SC3,version=2.7,serial=GX7K3P1,sku=PowerEdge_SC3,family=PowerEdge
```

> ℹ️ **NOTE:**
> - The UUID value must match the existing `smbios1: uuid` in `qm config` to avoid VM identity conflicts.
> - The serial number (`GX7K3P1`) is a plausible Dell-format 7-character alphanumeric placeholder.
> - Underscores in `Dell_Inc.` and `PowerEdge_SC3` are required — spaces break QEMU argument parsing.

---

## Step 7 — Verify the Configuration

Check the stored config and the generated QEMU command line before starting the VM.

```bash
sudo qm config 1029 | grep -E "^args|^smbios"
sudo qm showcmd 1029 | grep -o "\-smbios '[^']*'"
```

Output:

```
args: -acpitable file=/usr/share/kvm/DELL_PE_SC3.SLIC.bin -smbios type=1,uuid=ab05d25c-e5a7-4229-bf07-310e16bfa0db,manufacturer=Dell_Inc.,product=PowerEdge_SC3,version=2.7,serial=GX7K3P1,sku=PowerEdge_SC3,family=PowerEdge
-smbios 'type=1,uuid=ab05d25c-e5a7-4229-bf07-310e16bfa0db,manufacturer=Dell_Inc.,product=PowerEdge_SC3,version=2.7,serial=GX7K3P1,sku=PowerEdge_SC3,family=PowerEdge'
```

> ✔️ **EXPECTED RESULT:**
> - `args` line shows plain-text values — no base64 strings.
> - `showcmd` output shows the full `-smbios` string untruncated.
> - If `showcmd` truncates at a space (e.g. `manufacturer=Dell'`) the args value contains a literal space — re-run Step 6 ensuring underscores are used throughout.

---

## Step 8 — Start the VM and Verify

### 8.1 — Start the VM

```bash
sudo qm shutdown 1029 && sleep 5 && sudo qm start 1029
```

### 8.2 — Check QEMU process args (live confirmation)

> ℹ️ **NOTE:** The VM must be running before this command will work.

```bash
sudo cat /proc/$(sudo cat /var/run/qemu-server/1029.pid)/cmdline | tr '\0' '\n' | grep -A1 smbios
```

### 8.3 — Verify inside the Windows guest

Run the following in an elevated PowerShell session inside the VM:

```powershell
Get-CimInstance -ClassName Win32_ComputerSystemProduct | Select-Object Vendor, Name, Version
Get-CimInstance -ClassName Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, SerialNumber
```

Expected values:

| CIM Class                    | Field          | Expected Value   |
|------------------------------|----------------|------------------|
| `Win32_ComputerSystemProduct`| Vendor         | `Dell_Inc.`      |
| `Win32_ComputerSystemProduct`| Name           | `PowerEdge_SC3`  |
| `Win32_ComputerSystemProduct`| Version        | `2.7`            |
| `Win32_BIOS`                 | Manufacturer   | `Dell_Inc.`      |
| `Win32_BIOS`                 | SerialNumber   | `GX7K3P1`        |

### 8.4 — Verify SLIC table is visible (optional)

```powershell
Get-WmiObject -Namespace "root\cimv2" -Query "SELECT * FROM SoftwareLicensingService" | Select-Object OA2xBiosOemId, OA2xBiosOemTableId
```

> ✔️ **EXPECTED RESULT:** `OA2xBiosOemId` returns `DELL`. `OA2xBiosOemTableId` returns `PE_SC3`. Windows OEM activation will proceed normally.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| VM refuses to start | `-bios` flag in args | Remove args with `--delete args`, re-apply per Step 6 |
| `showcmd` truncates at `manufacturer=Dell'` | Literal space in args value | Re-run Step 6 — use underscores in all `-smbios` fields |
| SMBIOS shows base64 strings in guest | Used `--smbios1` flag (Proxmox 9.x bug) | Delete `smbios1` config key, use `args` instead per Step 6 |
| `wc -c` shows wrong size after `dd` | Wrong `skip` or `count` value | Re-check offset from `grep -obUaP` and length from `xxd` header bytes 04–07 |
| SLIC not visible in guest WMI | SLIC binary corrupt or wrong offset | Repeat Steps 3–4 and verify `xxd` output matches expected header |
| VM starts but activation fails | SLIC table mismatch or wrong product | Confirm the ROM file matches the Windows OEM licence being activated |

---

## Quick Reference — Key Values for This VM

| Item            | Value                                    |
|-----------------|------------------------------------------|
| VM ID           | `1029`                                   |
| VM Name         | `EXADCSMCR001`                           |
| Site            | MCR (Manchester) — `192.168.161.0/24`    |
| VLAN Tag        | `161`                                    |
| SLIC source ROM | `/usr/share/kvm/WORKSTATION_25H2_DELL2.7_BIOS.440.ROM` |
| SLIC binary     | `/usr/share/kvm/DELL_PE_SC3.SLIC.bin`   |
| SLIC offset     | `398767` bytes                           |
| SLIC length     | `374` bytes                              |
| OEM ID          | `DELL`                                   |
| OEM Table ID    | `PE_SC3`                                 |
| Spoofed serial  | `GX7K3P1`                                |
| VM UUID         | `ab05d25c-e5a7-4229-bf07-310e16bfa0db`  |

---

## Appendix A — ACPI Table Header Structure

For reference when manually parsing a ROM to locate and validate an embedded SLIC table.

| Byte Offset | Length | Field         | Description                                      |
|-------------|--------|---------------|--------------------------------------------------|
| 0           | 4      | Signature     | ASCII table identifier, e.g. `SLIC`             |
| 4           | 4      | Length        | Total table size in bytes (little-endian uint32) |
| 8           | 1      | Revision      | Table revision — SLIC v2.0 = `0x01`             |
| 9           | 1      | Checksum      | All bytes sum to `0x00`                          |
| 10          | 6      | OEM ID        | 6-char ASCII OEM identifier, e.g. `DELL  `       |
| 16          | 8      | OEM Table ID  | 8-char ASCII table ID, e.g. `PE_SC3  `           |
| 24          | 4      | OEM Revision  | OEM-defined revision                             |
| 28          | 4      | Creator ID    | Tool that created the table                      |
| 32          | 4      | Creator Rev   | Tool revision                                    |
| 36          | +      | Table Data    | RSA1 public key block and Windows marker         |

---

## Appendix B — HP SLIC Feasibility Notes

This procedure uses a Dell SLIC ROM. HP SLIC tables are technically identical in ACPI structure — the extraction and injection process is the same. However there are practical differences to be aware of before attempting an HP implementation.

| Consideration           | Dell                                            | HP                                                          |
|-------------------------|-------------------------------------------------|-------------------------------------------------------------|
| SLIC ACPI structure     | Standard ACPI v2.0 — 374 bytes typical          | Standard ACPI v2.0 — 374 bytes typical                      |
| OEM ID field            | `DELL  ` (6 chars)                              | `HPQOEM` or `HP____` depending on product line             |
| OEM Table ID field      | Product-specific, e.g. `PE_SC3  `              | Product-specific, e.g. `30B4    ` or `SLIC-MPC`            |
| ROM availability        | Widely available from Dell support site         | HP BIOSes are generally harder to source legitimately       |
| Extraction method       | As per this procedure                           | Identical — `grep` for SLIC offset, `dd` to extract        |
| SMBIOS spoofing         | `manufacturer=Dell_Inc.`                        | `manufacturer=HP` or `Hewlett-Packard` — varies by product  |
| Windows OEM cert match  | Dell certs are well-documented                  | HP certs exist but product string matching is less predictable |
| Risk of mismatch        | Low — `PE_SC3` is a known stable identifier     | Higher — HP OEM Table IDs vary significantly across product ranges |

The procedure is feasible for HP, but the Dell approach is more predictable and better documented. Stick with Dell SLIC unless there is a specific reason to use HP — for example if the Windows licence being activated is an HP OEM key.

> ℹ️ **NOTE:**
> Windows OEM activation matches on three things: the SLIC signature, the OEM certificate embedded in the licence, and the product key. A Dell SLIC will not activate an HP OEM key, and vice versa. The SLIC, certificate, and key must all originate from the same OEM.

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
