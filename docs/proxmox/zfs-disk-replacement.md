# ZFS RAID1 Disk Replacement & Pool Expansion

## Changelog

| Date | Change |
|---|---|
| 2026-03-01 | Initial document — ZFS RAID1 disk replacement procedure, Ansible role |

## Example Music Infrastructure — jukebox.internal

Replacing SATA HDDs in a Proxmox VE node running ZFS RAID1, without data loss or reinstalling Proxmox.

**Tested on:** Proxmox VE 9, legacy BIOS, ZFS RAID1, VMware.
**Source:** Proxmox official docs + verified in the field Feb 2026.

---

## How Proxmox Manages Booting

Proxmox uses `proxmox-boot-tool` to manage bootloaders. On legacy BIOS it installs GRUB into the EFI System Partition (`sdX2`) as a carrier — even though you're not booting via EFI. This means:

- `proxmox-boot-tool` is always the right tool — never raw `grub-install`
- Both disks need their ESP (`sdX2`) registered and synced
- `proxmox-boot-tool status` is the ground truth

```bash
proxmox-boot-tool status
```

Healthy output on legacy BIOS:
```
System currently booted with legacy bios
XXXX-XXXX is configured with: grub (versions: 6.17.2-1-pve)
YYYY-YYYY is configured with: grub (versions: 6.17.2-1-pve)
```

---

## The Replacement Script

Use `zfs-disk-replace.sh` — it's fully interactive, detects pool state automatically, and verifies output after every step.

```bash
sudo bash zfs-disk-replace.sh
```

No hardcoded disk names. It figures out which disk is missing, which is healthy, presents a numbered list of candidates, runs safety checks, and walks you through confirmation at each destructive step.

---

## Manual Procedure (for reference / recovery)

If the script fails at any point, here are the exact commands in order. Substitute `sda`/`sdb` for your actual disks.

### Before touching anything

```bash
zpool status rpool                  # confirm pool state and identify missing vdev ID
proxmox-boot-tool status            # confirm current ESP state
lsblk -o NAME,SIZE,MODEL            # confirm which disk is which
```

### Replace the disk

```bash
# 1. Copy partition table from healthy disk to new disk
sgdisk /dev/sdb -R /dev/sda

# 2. Randomise GUIDs on new disk -- critical, must not share GUIDs
sgdisk -G /dev/sda

# 3. Tell kernel about new partitions
partprobe /dev/sda
ls /dev/sda*                        # verify sda1, sda2, sda3 are visible

# 4. Replace the missing vdev (use numeric ID shown in zpool status)
zpool replace -f rpool <NUMERIC_ID> /dev/sda3

# 5. Wait for resilver
watch zpool status rpool            # wait for ONLINE + 0 errors

# 6. Format and initialise ESP on new disk
proxmox-boot-tool format /dev/sda2 --force
proxmox-boot-tool init /dev/sda2 grub

# 7. Clean stale UUIDs -- always needed after replacing a disk
proxmox-boot-tool clean

# 8. Verify
proxmox-boot-tool status            # must show 2 ESPs with grub
zpool status rpool                  # must show ONLINE, 0 errors
```

### Expand pool to use larger disks

If the new disks are larger than the old ones, the pool will NOT expand automatically. Two things are required:

**First — the partition must be extended to fill the disk.** ZFS can only use what the partition gives it. Even with `autoexpand=on`, if the partition ends at the old disk boundary, ZFS sees no extra space.

```bash
# Extend the ZFS partition on each disk to fill the disk
parted /dev/sda resizepart 3 100%
parted /dev/sdb resizepart 3 100%

# Verify partitions now reach end of disk
fdisk -l /dev/sda | grep sda3
fdisk -l /dev/sdb | grep sdb3
```

**Then — tell ZFS to use the new partition size:**

```bash
zpool set autoexpand=on rpool
zpool online -e rpool /dev/sda3
zpool online -e rpool /dev/sdb3

# Verify
zpool list rpool                    # SIZE should now reflect new disk capacity
```

No reboot required. Takes effect immediately.

---

## VMware-Specific Notes

VMware has a **separate HDD boot priority list** inside the BIOS, independent of the top-level boot order. To test booting from a specific disk you must change the HDD priority list specifically — changing the top-level order (HDD before CD) is not enough.

To test each disk boots independently:
1. VMware BIOS → Hard Disk boot order → promote disk to position 1
2. Boot and confirm system comes up
3. Return HDD order to normal
4. Repeat for the other disk

---

## Recovery — Unbootable Node

Boot from the **Proxmox VE ISO** (rescue mode). The Proxmox ISO has `zpool`
available. A Debian rescue environment does not — you'd need:
`apt-get install zfsutils-linux` first.

```bash
zpool import -f rpool
proxmox-boot-tool format /dev/sda2 --force
proxmox-boot-tool init /dev/sda2 grub
proxmox-boot-tool format /dev/sdb2 --force
proxmox-boot-tool init /dev/sdb2 grub
proxmox-boot-tool clean
zpool export rpool
reboot
```

---

## Lessons Learned (Feb 2026)

**`sgdisk` copies the partition layout, not the partition sizes.** If you copy from a 40G disk to a 60G disk, the partitions on the 60G disk will still end at the 40G boundary. `parted resizepart 3 100%` is required before `zpool online -e` will see any extra space.

**`zpool online -e` needs the partition, not the disk.** Use `/dev/sda3` not `/dev/sda`.

**`autoexpand=off` by default.** Must explicitly set `zpool set autoexpand=on rpool` before `zpool online -e` will work.

**`proxmox-boot-tool clean` is mandatory after every disk replacement.**
Every swap leaves a stale UUID in `/etc/kernel/proxmox-boot-uuids` that must be cleaned or `proxmox-boot-tool refresh` will warn and skip it.

**Proxmox ISO rescue environment has `zpool`.** Debian rescue does not. Always boot from the Proxmox ISO when recovering a broken node.

**VMware's HDD boot priority is separate from the main boot order.** Easy to miss, costs 20 minutes of frustration.

---

*Example Music Infrastructure — jukebox.internal*
*Verified Feb 2026 — Proxmox VE 9, legacy BIOS, ZFS RAID1*
*Source: https://pve.proxmox.com/wiki/ZFS_on_Linux*
