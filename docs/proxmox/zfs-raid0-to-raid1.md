# ZFS Single Disk to RAID1 Mirror Upgrade

## Changelog

| Date | Change |
|---|---|
| 2026-03-01 | Initial document — single disk to RAID1 mirror upgrade procedure |

## Example Music Infrastructure — jukebox.internal

Scenario: A Proxmox VE node was provisioned with a single disk (ZFS RAID0) due to shipping delays. The second disk has now arrived and we are upgrading
to a full ZFS RAID1 mirror without reinstalling or losing data.

**Tested on:** Proxmox VE 9, legacy BIOS, VMware.

---

## When to Use This Procedure

The Proxmox automated installer requires two disks for `zfs.raid = "raid1"`. When only one disk is available at install time, use the degraded install path instead:

```bash
http://192.168.139.50/proxmox/degraded.toml
```

This installs Proxmox with `zfs.raid = "raid0"` on a single disk. The node comes up fully functional — first-boot runs, Ansible user is configured,
node info file is written to `/etc/example-music/nodeinfo.json`, everything is ready. The node simply has no redundancy until the second disk is added.

**Do not put the node into production until this upgrade procedure has been completed and both disks boot independently.**

---

## Prerequisites

The following packages must be present (installed by first-boot.sh):

- `gdisk` — provides `sgdisk`
- `parted` — provides `partprobe`
- `smartmontools` — provides `smartctl`

If running on a node provisioned before these were added to first-boot.sh:

```bash
apt-get install -y gdisk parted smartmontools
```

---

## Procedure

### Step 1 — Confirm new disk is visible

```bash
lsblk -o NAME,SIZE,MODEL
```

Expected output:
```
NAME    SIZE MODEL
sda      20G VMware Virtual S
├─sda1 1007K
├─sda2  512M
└─sda3 19.5G
sdb      20G VMware Virtual S
sr0     1.7G VMware Virtual IDE CDROM Drive
```

`sdb` should be visible with no partitions. If it is not visible:

```bash
# Rescan SCSI buses (VMware hot-add)
echo "- - -" > /sys/class/scsi_host/host0/scan
echo "- - -" > /sys/class/scsi_host/host1/scan
echo "- - -" > /sys/class/scsi_host/host2/scan
udevadm settle
lsblk
```

If still not visible, check the hypervisor/hardware — the disk may not have
been committed to the VM configuration.

### Step 2 — Copy partition table from sda to sdb

```bash
sgdisk /dev/sda -R /dev/sdb
```

Expected output:
```
The operation has completed successfully.
```

### Step 3 — Randomise GUIDs on sdb

Critical — both disks must not share partition GUIDs.

```bash
sgdisk -G /dev/sdb
```

Expected output:
```
The operation has completed successfully.
```

### Step 4 — Tell kernel about new partitions

```bash
partprobe /dev/sdb && ls /dev/sdb*
```

Expected output:
```
/dev/sdb  /dev/sdb1  /dev/sdb2  /dev/sdb3
```

All three partitions must be visible before continuing.

### Step 5 — Attach sdb to the ZFS pool as second mirror leg

This is `zpool attach` not `zpool replace` — we are adding a new leg to the pool, not replacing a failed one.

```bash
zpool attach rpool /dev/sda3 /dev/sdb3
```

No output means success. ZFS begins resilvering immediately.

### Step 6 — Verify resilver completed

```bash
zpool status rpool
```

Expected output:
```
  pool: rpool
 state: ONLINE
  scan: resilvered 2.06G in 00:00:06 with 0 errors on Fri Feb 27 09:46:29 2026
config:

        NAME        STATE     READ WRITE CKSUM
        rpool       ONLINE       0     0     0
          mirror-0  ONLINE       0     0     0
            sda3    ONLINE       0     0     0
            sdb3    ONLINE       0     0     0

errors: No known data errors
```

Pool must show `mirror-0` with both members `ONLINE` and zero errors before continuing. If resilver is still in progress, wait.

### Step 7 — Format ESP on sdb

```bash
proxmox-boot-tool format /dev/sdb2 --force
```

Expected output:
```
UUID="" SIZE="536870912" FSTYPE="" PARTTYPE="c12a7328-..." PKNAME="sdb" MOUNTPOINT=""
Formatting '/dev/sdb2' as vfat..
mkfs.fat 4.2 (2021-01-31)
Done.
```

### Step 8 — Install GRUB and sync kernels to sdb

```bash
proxmox-boot-tool init /dev/sdb2 grub
```

Expected output (abridged):
```
Installing grub i386-pc target..
Installing for i386-pc platform.
Installation finished. No error reported.
...
Copying and configuring kernels on /dev/disk/by-uuid/2F7A-2067
        Copying kernel 6.17.2-1-pve
...
Copying and configuring kernels on /dev/disk/by-uuid/D3D8-B702
        Copying kernel 6.17.2-1-pve
...
done
```

Both ESP UUIDs should appear — no `WARN` lines expected on a fresh install.

### Step 9 — Clean and verify

```bash
proxmox-boot-tool clean && proxmox-boot-tool status
```

Expected output:
```
Checking whether ESP '2F7A-2067' exists.. Found!
Checking whether ESP 'D3D8-B702' exists.. Found!
Sorting and removing duplicate ESPs..
Re-executing '/usr/sbin/proxmox-boot-tool' in new private mount namespace..
System currently booted with legacy bios
2F7A-2067 is configured with: grub (versions: 6.17.2-1-pve)
D3D8-B702 is configured with: grub (versions: 6.17.2-1-pve)
```

Both ESPs must be `Found` and both must show `grub` with the same kernel version.

### Step 10 — Final pool check

```bash
zpool status rpool
```

Must show `ONLINE`, `mirror-0`, both members, zero errors.

---

## Test Independent Boot

Before considering this node production-ready, verify each disk boots alone.

**VMware:** BIOS → Hard Disk boot order → promote `sdb` to position 1 → boot → confirm → restore order → repeat with `sda`.

Both disks must boot independently. If either fails, re-run `proxmox-boot-tool init /dev/sdX2 grub` on the failing disk.

---

## Cheat Sheet

```bash
# Confirm new disk visible
lsblk -o NAME,SIZE,MODEL

# Partition
sgdisk /dev/sda -R /dev/sdb
sgdisk -G /dev/sdb
partprobe /dev/sdb && ls /dev/sdb*

# Add to pool
zpool attach rpool /dev/sda3 /dev/sdb3
zpool status rpool                          # wait for ONLINE + 0 errors

# Bootloader
proxmox-boot-tool format /dev/sdb2 --force
proxmox-boot-tool init /dev/sdb2 grub
proxmox-boot-tool clean
proxmox-boot-tool status                    # both ESPs with grub
```

---

## Notes

**`zpool attach` vs `zpool replace`**
- `zpool attach` — adds a new disk to an existing vdev, converting a stripe to a mirror. Use this when going from single disk to RAID1.
- `zpool replace` — replaces a failed/missing member of an existing mirror. Use this for the standard disk replacement procedure.

**No WARN lines on fresh install**
When adding a second disk to a node that has never had one, there are no stale ESP UUIDs to clean. `proxmox-boot-tool clean` is still good practice but will not remove anything.

**Pool shows ONLINE not DEGRADED**
Unlike a replacement scenario where the pool is DEGRADED before you start, a single-disk RAID0 pool is ONLINE — it has no failed members, just no redundancy. After `zpool attach` and resilver, it becomes a proper RAID1 mirror, still ONLINE throughout.

---

*Example Music Infrastructure — jukebox.internal*
*Verified Feb 2026 — Proxmox VE 9, legacy BIOS*
*Single disk install: http://192.168.139.50/proxmox/degraded.toml*
