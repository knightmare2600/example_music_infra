# SLIC/MSDM BIOS Extraction and Proxmox VM Import

**Document ID:** NET-LAB-SLIC-001  
**Classification:** Internal — Network Engineering / Lab  
**Last Updated:** 2026-03-05

> **Purpose:** Extract ACPI SLIC/MSDM tables and SMBIOS data from a licensed donor machine and inject them into a Proxmox VM for
> wargaming/testing purposes. This allows Windows activation testing without requiring physical hardware in the lab.
> 
> **Prerequisites:** You must own a valid Windows licence and have a licensed donor machine with the corresponding BIOS tables. This
>procedure is for lab/test use only.

---

## Table of Contents

1. [Background](#background)
2. [What You Need](#what-you-need)
3. [Part 1 — Extract from Donor Machine](#part-1--extract-from-donor-machine)
4. [Part 2 — Import to Proxmox](#part-2--import-to-proxmox)
5. [Part 3 — Verify in the VM](#part-3--verify-in-the-vm)
6. [Troubleshooting](#troubleshooting)
7. [Notes on SLIC vs MSDM](#notes-on-slic-vs-msdm)

---

## Background

**SLIC** (Software Licensing Description Table) and **MSDM** (Microsoft Data Management) are ACPI tables embedded in the BIOS/UEFI firmware of
OEM machines that have been pre-licensed for Windows. When Windows Setup or activation checks the machine, it reads these tables to confirm the
licence is valid for that hardware.

**SMBIOS** type 0 and type 1 records carry the BIOS vendor/version and system manufacturer/model strings. Windows cross-references these against
the SLIC/MSDM table — they must match or activation fails.

When you virtualise a machine in Proxmox, QEMU presents its own generic SMBIOS strings and has no ACPI licence tables. This procedure replaces
those with the real values from the donor machine so the VM behaves identically to the physical hardware from an activation perspective.

---

## What You Need

| Item | Notes |
|------|-------|
| Donor machine | Licensed OEM machine with SLIC or MSDM in BIOS |
| Live Linux ISO | Ubuntu, Debian, or any distro with `dmidecode`, `curl`, `xxd` |
| Proxmox host | With the VM already created (note its VM ID) |
| Storage path on Proxmox | Somewhere the VM config can reference — e.g. `/rpool/data/MSDM/` |
| `dmidecode` | Usually pre-installed on Ubuntu live ISOs |

---

## Part 1 — Extract from Donor Machine

Boot the donor machine from a live Linux ISO. You do not need to install anything — just boot to a shell. Connect it to the internet if you want
to use the sprunge.us method to retrieve the files; otherwise copy them manually to a USB stick.

### extract.sh

```bash
#!/bin/bash
# Run this on the donor machine booted from a live Linux ISO.
# Extracts ACPI SLIC/MSDM tables and SMBIOS type 0 and type 1 records,
# tarballs them, and posts to sprunge.us for easy retrieval.
# If you have no internet on the donor, copy the files from /tmp/MSDM/
# to a USB stick manually instead of the sprunge step.

mkdir -p /tmp/MSDM
cd /tmp/MSDM

# Extract ACPI tables — SLIC is found on older OEM machines (Win 7/8 era)
# MSDM is found on newer machines (Win 8+ OEM activation)
# Either or both may be present depending on the donor machine
for f in SLIC MSDM; do
  if [ -e /sys/firmware/acpi/tables/$f ]; then
    cat /sys/firmware/acpi/tables/$f > $f.bin
    echo "Extracted $f.bin"
  else
    echo "WARNING: $f not found in ACPI tables — skipping"
  fi
done

# Extract SMBIOS type 0 (BIOS info — vendor, version, release date)
dmidecode -t 0 -u | awk '/^\t\t[0-9A-F][0-9A-F]( |$)/' | xxd -r -p > smbios_type_0.bin

# Extract SMBIOS type 1 (System info — manufacturer, product name, UUID)
dmidecode -t 1 -u | awk '/^\t\t[0-9A-F][0-9A-F]( |$)/' | xxd -r -p > smbios_type_1.bin

echo "Files in /tmp/MSDM/:"
ls -lh /tmp/MSDM/

# Tar, base64-encode, and post to sprunge.us for retrieval
# You will get a URL — note it down, you need it on the Proxmox host
tar zcf - . | base64 | curl -F 'sprunge=<-' http://sprunge.us
echo ""
echo "Note the URL above — use it in import.sh on the Proxmox host"
```

### Check what was extracted

Before you close the donor session, verify the files look sensible:

```bash
# Should show SLIC.bin and/or MSDM.bin, smbios_type_0.bin, smbios_type_1.bin
ls -lh /tmp/MSDM/

# Sanity check — SLIC is typically ~374 bytes, MSDM ~55 bytes
# smbios_type_0 and type_1 are variable but usually 50-200 bytes each
# If any are 0 bytes something went wrong

# Human-readable check of SMBIOS type 1 to confirm it's the right machine
dmidecode -t 1
# Should show the donor machine's manufacturer and model
```

> **If SLIC and MSDM are both absent:** The donor machine may use a different activation method (MAK key, KMS, or retail licence). SLIC/MSDM
> OEM activation is found on machines that shipped with Windows pre-installed from the manufacturer — Dell, HP, Lenovo, etc.

---

## Part 2 — Import to Proxmox

Run this on the Proxmox host. Replace `VMID` with your actual VM ID and the sprunge URL with the one from Part 1.

### import.sh

```bash
#!/bin/bash
# Run this on the Proxmox host as root.
# Retrieves the extracted BIOS files and injects them into a VM config.

# ── Configuration ────────────────────────────────────────────
VMID=200                          # Change to your VM ID
MDIR=/rpool/data/MSDM             # Storage path — must be accessible to QEMU
SPRUNGE_URL="https://sprunge.us/XXXXXXXX"  # URL from extract.sh output
# ─────────────────────────────────────────────────────────────

QFILE=/etc/pve/qemu-server/${VMID}.conf

# Verify VM exists
[ -f "$QFILE" ] || { echo "ERROR: VM config not found at $QFILE"; exit 1; }

# Create storage directory
mkdir -p "$MDIR"
cd "$MDIR"

# Retrieve and unpack the files from sprunge.us
# (or replace this with: tar zxvf /path/to/manual-copy.tar.gz)
echo "Retrieving BIOS files from $SPRUNGE_URL ..."
curl -s "$SPRUNGE_URL" | base64 -d | tar zxvf -

echo "Files retrieved:"
ls -lh "$MDIR"

# Verify we have at least one ACPI table and both SMBIOS files
ACPI_ARGS=""
[ -f "$MDIR/SLIC.bin" ]  && ACPI_ARGS="$ACPI_ARGS -acpitable file=$MDIR/SLIC.bin"
[ -f "$MDIR/MSDM.bin" ]  && ACPI_ARGS="$ACPI_ARGS -acpitable file=$MDIR/MSDM.bin"

if [ -z "$ACPI_ARGS" ]; then
  echo "ERROR: Neither SLIC.bin nor MSDM.bin found in $MDIR"
  exit 1
fi

if [ ! -f "$MDIR/smbios_type_0.bin" ] || [ ! -f "$MDIR/smbios_type_1.bin" ]; then
  echo "ERROR: smbios_type_0.bin or smbios_type_1.bin missing from $MDIR"
  exit 1
fi

SMBIOS_ARGS="-smbios file=$MDIR/smbios_type_0.bin -smbios file=$MDIR/smbios_type_1.bin"

# Back up the VM config before modifying
cp "$QFILE" "${QFILE}.bak.$(date +%Y%m%d%H%M%S)"
echo "Config backed up"

# Remove any existing smbios lines (Proxmox adds its own by default)
sed -i '/^smbios/d' "$QFILE"

# Remove any existing args line (we'll replace it)
sed -i '/^args:/d' "$QFILE"

# Inject the new args line
echo "args: $ACPI_ARGS $SMBIOS_ARGS" >> "$QFILE"

echo ""
echo "Done. Updated $QFILE:"
echo "---"
grep "^args:" "$QFILE"
echo "---"
echo ""
echo "Start the VM and verify activation with: slmgr /dlv"
```

### What the resulting config line looks like

For a machine with both SLIC and MSDM:

```
args: -acpitable file=/rpool/data/MSDM/SLIC.bin -acpitable file=/rpool/data/MSDM/MSDM.bin -smbios file=/rpool/data/MSDM/smbios_type_0.bin -smbios file=/rpool/data/MSDM/smbios_type_1.bin
```

For a machine with MSDM only (typical modern OEM):

```
args: -acpitable file=/rpool/data/MSDM/MSDM.bin -smbios file=/rpool/data/MSDM/smbios_type_0.bin -smbios file=/rpool/data/MSDM/smbios_type_1.bin
```

### Storage path considerations

The path you choose for `MDIR` must:

- Be on the Proxmox host's local filesystem (not a remote mount that may not be available when QEMU starts)
- Be readable by the `qemu` / `kvm` process — `/rpool/data/` on a ZFS-backed Proxmox node is the natural choice
- Persist across reboots — do not use `/tmp`

If you are running multiple VMs with different donor profiles, use separate subdirectories:

```
/rpool/data/MSDM/
    FAL-donor/      ← files from FAL physical machine
    BIR-donor/      ← files from BIR physical machine
```

And reference the appropriate path in each VM's `args:` line.

---

## Part 3 — Verify in the VM

Start the VM and boot into Windows. Open an elevated PowerShell or Command Prompt and run:

```powershell
# Check licence status
slmgr /dlv

# Quick activation status
slmgr /xpr

# Check ACPI tables are visible (confirms injection worked at QEMU level)
# Run from an elevated prompt
powershell -Command "Get-WmiObject -Class SoftwareLicensingService | Select-Object OA3xOriginalProductKey"
```

You can also verify at the QEMU level before booting Windows — on the Proxmox host, while the VM is running:

```bash
# Check QEMU is actually using the args
ps aux | grep "qemu-system" | grep "$VMID" | tr ' ' '\n' | grep -A1 acpitable
```

### Expected activation behaviour

| Scenario | Expected result |
|----------|----------------|
| MSDM present, correct SMBIOS | Windows activates automatically (OEM activation) |
| SLIC present, correct SMBIOS | Windows activates automatically (legacy OEM) |
| SMBIOS mismatch | Activation fails — manufacturer/model must match |
| Neither SLIC nor MSDM | Windows prompts for product key |

---

## Troubleshooting

**`slmgr /dlv` shows activation error 0xC004F074**  
KMS server not reachable — not related to SLIC/MSDM. This appears on volume licence installs trying to reach a KMS server.

**`slmgr /dlv` shows activation error 0xC004E003**  
SLIC/MSDM table found but SMBIOS manufacturer/model does not match. Re-extract the SMBIOS files from the same donor machine. Common cause
is mixing SMBIOS files from one machine with SLIC/MSDM from another.

**VM config has `smbios1:` line after import**  
Proxmox may regenerate the `smbios1:` line. The `sed -i '/^smbios/d'` in import.sh removes it, but if Proxmox re-adds it via the GUI, remove
it again:

```bash
sed -i '/^smbios/d' /etc/pve/qemu-server/200.conf
```

Or edit the config in the Proxmox web UI — remove the SMBIOS line from the Hardware tab, or it will conflict with the injected SMBIOS binary.

**`/sys/firmware/acpi/tables/SLIC` not found on donor**  
The donor machine either: doesn't have a SLIC table (try MSDM instead), or you're running in an OS that doesn't expose ACPI tables via sysfs
(unlikely on a modern Linux live ISO but possible on very old kernels). Try: `ls /sys/firmware/acpi/tables/` to see what's available.

**sprunge.us is unavailable**  
Copy the files manually:

```bash
# On donor — write to USB stick
tar zcf /media/usb/msdm-files.tar.gz -C /tmp/MSDM .

# On Proxmox host — extract from USB
mkdir -p /rpool/data/MSDM
tar zxvf /media/usb/msdm-files.tar.gz -C /rpool/data/MSDM
```

**`dmidecode` not found on live ISO**  
```bash
apt-get install -y dmidecode   # Debian/Ubuntu live
```

---

## Notes on SLIC vs MSDM

| Feature | SLIC | MSDM |
|---------|------|------|
| Used for | Windows 7 / 8 OEM activation | Windows 8+ OEM activation |
| Size | ~374 bytes | ~55 bytes |
| Location | `/sys/firmware/acpi/tables/SLIC` | `/sys/firmware/acpi/tables/MSDM` |
| Contains | RSA public key + Windows marker | Product key embedded directly |
| Still valid? | Yes for Win 7/8 licences | Yes — current standard |

Modern OEM machines (post-2012) will typically have MSDM and no SLIC. Older machines may have SLIC only. Some machines have both. The import.sh script handles all three cases automatically.

---

*Internal Use Only — Network Engineering / Lab — jukebox.internal*
