# Proxmox VE Storage — ZFS RAID1 Operations

## Changelog

| Date | Change |
|---|---|
| 2026-03-01 | Initial document — ZFS RAID1 operations, disk replacement, pool expansion |

## Example Music Infrastructure

---

## Why ZFS RAID1 over mdadm

Proxmox VE is a first-class ZFS citizen. The installer handles everything natively and the web UI exposes pool health directly. Compared to mdadm:

| | mdadm + LVM | ZFS RAID1 |
|---|---|---|
| OS support | Bolted on post-install | Native, baked in at install |
| Health visibility | `/proc/mdstat` only | Proxmox web UI + `zpool status` |
| Silent corruption detection | No | Yes (checksumming) |
| Disk replacement | Multi-step, manual | One command |
| Pool expansion | resize PV → LV → FS | One command |
| initramfs fiddling | Required | Not required |

---

## answer.toml Configuration

ZFS RAID1 is configured in the automated installer answer file:

```toml
[disk-setup]
filesystem = "zfs"
zfs.raid = "raid1"
disk-list = ["sda", "sdb"]
```

This mirrors the OS across both disks at install time. No post-install surgery required.

---

## Day-to-Day Commands

### Check pool health

```bash
zpool status
```

Healthy output:
```
  pool: rpool
 state: ONLINE
  scan: scrub repaired 0B in 00:00:01 with 0 errors on Sun Feb 25 00:24:02 2026
config:

        NAME        STATE     READ WRITE CKSUM
        rpool       ONLINE       0     0     0
          mirror-0  ONLINE       0     0     0
            sda     ONLINE       0     0     0
            sdb     ONLINE       0     0     0
```

Degraded (one disk failed):
```
        NAME        STATE     READ WRITE CKSUM
        rpool       DEGRADED     0     0     0
          mirror-0  DEGRADED     0     0     0
            sda     FAULTED      0     0     0  too many errors
            sdb     ONLINE       0     0     0
```

The pool keeps running in degraded state. VMs keep running. Nothing catches fire.

### Run a scrub (integrity check)

```bash
zpool scrub rpool
zpool status          # check progress
```

Run monthly. Proxmox schedules this automatically.

---

## Replacing a Failed Disk

### 1. Identify the failed disk

```bash
zpool status
```

Note which device is `FAULTED` — e.g. `/dev/sda`.

### 2. Power down and swap the disk

Shut the node down cleanly:

```bash
# Check no VMs are running first
qm list
pct list

# Shut down
shutdown -h now
```

Physically swap the failed disk for a replacement of equal or greater size.

### 3. Power back up and replace in the pool

```bash
# ZFS may auto-detect — check status first
zpool status

# If not auto-replaced, replace explicitly
zpool replace rpool /dev/sda /dev/sda
# (same device path — ZFS sees it as a new disk)
```

### 4. Watch the resilver

```bash
watch zpool status
```

You'll see:
```
scan: resilver in progress since Wed Feb 25 17:30:01 2026
      1.23G scanned at 412M/s, 622M issued at 207M/s, 19.5G total
      0B resilvered, 3.19% done, 00:01:31 to go
```

When it shows `resilvered` with 0 errors and both members `ONLINE` — done.

---

## Expanding a Pool (Upgrading to Larger Disks)

Example: upgrading from 1TB to 2TB HDDs.

**Rule: the pool stays at the smaller size until ALL members are replaced.**

### Step 1 — Replace first disk

Power down, swap `sda` for the 2TB disk, power back up:

```bash
zpool replace rpool /dev/sda /dev/sda
watch zpool status    # wait for resilver to complete and show [ONLINE]
```

Pool is still 1TB at this point — correct, `sdb` is still 1TB.

### Step 2 — Replace second disk

Power down, swap `sdb` for the 2TB disk, power back up:

```bash
zpool replace rpool /dev/sdb /dev/sdb
watch zpool status    # wait for resilver to complete
```

### Step 3 — Expand the pool

Both disks are now 2TB. Tell ZFS to use the full size:

```bash
zpool online -e rpool /dev/sda
```

That's it. The pool expands automatically — no `pvresize`, no `lvextend`, no `resize2fs`. ZFS handles everything.

Verify:
```bash
zpool list
```

```
NAME    SIZE  ALLOC   FREE  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
rpool  1.98T   142G  1.84T         -     4%     7%  1.00x    ONLINE  -
```

---

## Additional VM Storage (Adding a Third Disk)

If you add a dedicated VM storage disk later (e.g. `/dev/sdc`), you have two sensible options:

### Option A — Simple LVM (recommended for a single disk)

```bash
pvcreate /dev/sdc
vgcreate vmdata /dev/sdc
lvcreate -l 100%FREE -n vmstore vmdata
mkfs.ext4 /dev/vmdata/vmstore
mkdir -p /mnt/vmstore
echo "/dev/vmdata/vmstore /mnt/vmstore ext4 defaults 0 2" >> /etc/fstab
mount /mnt/vmstore
pvesm add dir vmstore --path /mnt/vmstore --content images,iso,backup,snippets
```

### Option B — Add as a ZFS mirror (if you have two matching disks)

```bash
# Add sdc+sdd as a second mirror vdev to rpool
zpool add rpool mirror /dev/sdc /dev/sdd
```

The pool now spans both mirror vdevs — total usable = sum of both mirrors.

---

## Useful Reference

| Command | Purpose |
|---|---|
| `zpool status` | Pool health, resilver/scrub progress |
| `zpool list` | Pool sizes and usage |
| `zpool scrub rpool` | Start integrity check |
| `zpool replace rpool /dev/sdX /dev/sdX` | Replace a disk |
| `zpool online -e rpool /dev/sdX` | Expand pool after disk upgrade |
| `zfs list` | List datasets and usage |
| `zfs get all rpool` | All ZFS properties |
| `pveversion` | Proxmox version |
| `pvesm status` | Storage status (Proxmox view) |

---

## Sentinel File

Every provisioned PVE node has `/etc/.i_am_a_pve_node` (read-only):

```
Configured by Example Music provisioning script
Hostname    : EXAFALP VE001
FQDN        : EXAFALPVE001.jukebox.internal
Site        : FAL
City        : Falkirk
Country     : Scotland
Entity      : Example Music (Scotland) Ltd
Node IP     : 192.168.76.5
Date        : 2026-02-25T17:00:00Z
```

Ansible playbooks check for this file before running any destructive operations — prevents accidentally running hypervisor playbooks on routers or workstations.

---

*Example Music Infrastructure — jukebox.internal*
