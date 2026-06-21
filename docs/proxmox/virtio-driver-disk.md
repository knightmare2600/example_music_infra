# VirtIO Driver Disk — Build Runbook

**Example Music Limited — Internal Infrastructure**

This runbook covers building a small FAT32 raw disk image containing unpacked VirtIO drivers for use with PhoenixPE during Windows VM installation. The image is attached to Windows VMs as `scsi1` by `create-vm.py` and appears as drive `D:` (or similar) inside WinPE.

---

## Background

Windows VMs on Proxmox use paravirtualised VirtIO devices for disk and network. WinPE has no inbox drivers for these, so before it can see the SCSI disk or the NIC it needs the drivers loaded at runtime using `drvload.exe`.

Rather than mounting the full VirtIO ISO (which is ~500MB and changes with every release), we maintain a small, version-pinned raw disk image containing only the driver INF/SYS/CAT files needed by `drvload`. This image is built once, stored on Proxmox storage, and attached to every Windows VM at creation time.

### What goes in the image

Only the files needed for `drvload` in WinPE — no MSIs, no installer, just the raw driver files. All supported OS version subfolders are included so the same
disk works regardless of which Windows version is being installed.

| Driver | Purpose | Required in PE |
|---|---|---|
| `vioscsi` | VirtIO SCSI controller | ✅ Yes — disk invisible without this |
| `NetKVM` | VirtIO NIC | ✅ Yes — network invisible without this |
| `Balloon` | Memory balloon | ❌ No — not needed in PE |
| `vioserial` | VirtIO serial port | ❌ No — not needed in PE |

We include Balloon and vioserial anyway as they add negligible size and make the disk useful for post-install driver staging if needed.

---

## Prerequisites

Run on a Linux machine (or directly on a Proxmox node). Requires:

```bash
# Debian/Ubuntu/Proxmox
apt install dosfstools mtools

# Verify
mkfs.fat --version
```

You also need the VirtIO ISO from Fedora:

```bash
wget https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/latest-virtio/virtio-win-gt-x64.msi
```

> **Version pinning:** Note the exact version you download. The image filename should include the version, e.g. `virtio-drivers-0.1.271.img`. Check the
> downloaded ISO version with:
> 
> ```bash
> isoinfo -d -i virtio-win.iso | grep "Volume id"
> ```

---

## Building the Image

The `make-virtio-disk.sh` script automates this. Run it once per VirtIO release.

```bash
chmod +x make-virtio-disk.sh
./make-virtio-disk.sh virtio-win-gt-x64.msi virtio-drivers.img
```

See the script for details. When complete, copy the image to Proxmox storage:

```bash
scp virtio-drivers.img root@192.168.139.50:/var/lib/vz/images/virtio-drivers.img
```

---

## Manual Build Steps

If you need to build without the script, or want to understand what it does:

### 1 — Extract the MSI with 7za

```bash
mkdir -p /tmp/virtio-extracted
7za x virtio-win-gt-x64.msi -o/tmp/virtio-extracted/
```

The MSI extracts to a flat directory with files named:

```
FILE_<driver>_<osver>_<arch>.<ext>
```

For example:
```
FILE_vioscsi_2k22_amd64.inf
FILE_vioscsi_2k22_amd64.sys
FILE_vioscsi_2k22_amd64.cat
FILE_netkvm_2k22_amd64.inf
...
```

### 2 — Create a blank raw image

```bash
dd if=/dev/zero of=virtio-drivers.img bs=1M count=128
mkfs.fat -F 32 -n VIRTIO virtio-drivers.img
```

### 3 — Mount the image

```bash
mkdir -p /mnt/virtioimg
mount -o loop virtio-drivers.img /mnt/virtioimg
```

### 4 — Reconstruct the folder structure

`drvload` expects `<driver>/<osver>/amd64/<driver>.<ext>`. Recreate this from the flat MSI naming manually or with a loop. Example for vioscsi on 2k22:

```bash
mkdir -p /mnt/virtioimg/vioscsi/2k22/amd64
cp /tmp/virtio-extracted/FILE_vioscsi_2k22_amd64.inf /mnt/virtioimg/vioscsi/2k22/amd64/vioscsi.inf
cp /tmp/virtio-extracted/FILE_vioscsi_2k22_amd64.sys /mnt/virtioimg/vioscsi/2k22/amd64/vioscsi.sys
cp /tmp/virtio-extracted/FILE_vioscsi_2k22_amd64.cat /mnt/virtioimg/vioscsi/2k22/amd64/vioscsi.cat
```

Repeat for each driver and OS version. The script does this automatically for all drivers and all OS versions found in the MSI.

### 5 — Unmount

```bash
umount /mnt/virtioimg
rm -rf /tmp/virtio-extracted
```

---

## Deploying to Proxmox

Copy to the Proxmox node. The image lives alongside ISO templates so `create-vm.py` can enumerate and attach it:

```bash
scp virtio-drivers.img root@192.168.139.50:/var/lib/vz/template/iso/virtio-drivers.img
```

> **Note:** Proxmox storage technically expects ISOs in `template/iso/` and disk images in `images/<vmid>/`. Storing it in `template/iso/` is a pragmatic
> workaround — it makes the image enumerable by the API without being tied to a specific VM. When `create-vm.py` attaches it as `scsi1` using the storage API, Proxmox will copy it to the correct location for that VM automatically.

---

## Using the Disk in PhoenixPE

When a Windows VM boots PhoenixPE, the driver disk will appear as a drive (typically `D:` if the boot media is `X:` or `C:`). Load drivers with `drvload.exe` before attempting to access the SCSI disk or network.

### Selecting the right OS version folder

Use the folder matching the **target Windows version being installed**, not the PE version. If you are installing Windows Server 2022, use `2k22`. If installing
Windows 11, use `w11`.

| Target OS | Folder |
|---|---|
| Windows 10 | `w10` |
| Windows 11 / Server 2025 | `w11` or `2k25` |
| Windows Server 2019 | `2k19` |
| Windows Server 2022 | `2k22` |

### drvload commands

Adjust the drive letter and OS version folder as appropriate:

```cmd
:: Load SCSI driver first — the OS disk becomes visible after this
drvload D:\vioscsi\2k22\amd64\vioscsi.inf

:: Load NIC driver
drvload D:\NetKVM\2k22\amd64\netkvm.inf
```

After `drvload vioscsi`, the `scsi0` disk (where Windows will be installed) should appear in Disk Management / `diskpart`. After `drvload NetKVM`, the network adapter becomes available and you can map your share.

### Suggested PhoenixPE startup script

```cmd
@echo off
:: VirtIO driver loader — runs at PhoenixPE startup
:: Adjust OSVER and DRVDRV as needed

set OSVER=2k22
set DRVDRV=D:

echo Loading VirtIO SCSI driver...
drvload %DRVDRV%\vioscsi\%OSVER%\amd64\vioscsi.inf
if errorlevel 1 (
  echo [!] vioscsi failed — check drive letter and OS version folder
  pause
)

echo Loading VirtIO NIC driver...
drvload %DRVDRV%\NetKVM\%OSVER%\amd64\netkvm.inf
if errorlevel 1 (
  echo [!] NetKVM failed — check drive letter and OS version folder
  pause
)

echo VirtIO drivers loaded.
echo You can now access the SCSI disk and network.
```

---

## Updating the Image

When a new VirtIO release is available:

1. Download the new ISO from Fedora
2. Run `make-virtio-disk.sh` with a versioned output filename:
   ```bash
   ./make-virtio-disk.sh virtio-win-0.1.280.iso virtio-drivers-0.1.280.img
   ```
3. Copy to Proxmox storage
4. At VM creation time, `create-vm.py` presents the image selection menu —
   select the new version

Old images can be retained or deleted from `/var/lib/vz/template/iso/` as preferred. Existing VMs are not affected by adding or removing images from storage.

---

## Troubleshooting

### drvload fails — "The system cannot find the path specified"

Check the drive letter. In PhoenixPE the driver disk may not always be `D:`.
Run `diskpart` → `list volume` to find the correct letter.

### drvload fails — "The INF file is not valid"

Wrong OS version folder. Try `w11` instead of `2k22` or vice versa — the underlying driver is often the same but Windows is strict about the folder match.

### SCSI disk still not visible after loading vioscsi

Verify the VM's disk controller is set to `VirtIO SCSI` (not IDE or SATA) in the Proxmox VM hardware config. `create-vm.py` sets `scsihw=virtio-scsi-pci` by default.

### Image not appearing in create-vm.py selection menu

Verify the image is in `/var/lib/vz/template/iso/` on the target node and the storage is accessible. Check with:
```bash
pvesm list local | grep virtio
```
