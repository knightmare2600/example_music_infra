# Procedure: PBS NFS Datastore on QNAP & PVE Node Storage

## Changelog

| Date | Change |
|---|---|
| 2026-10-28 | Initial document — PBS NFS datastore on QNAP, connecting PVE nodes to PBS, local ZFS storage build on an ex-ESXi node (Robert) |
| 2026-10-29 | Sanitized for this repo — real hostnames/IPs replaced with FAL's real identifiers from `devices.csv` (`EXAPBSFAL001`/`EXANASFAL001`/`EXAPVEFAL001`, `192.168.76.0/24`), PBS cert fingerprint randomized |

## Overview

This procedure stores Proxmox Backup Server (PBS) backups on a QNAP NFS share, connects PVE nodes to PBS, and builds local ZFS storage on a PVE node that was previously an ESXi host. All example output below is real output from the FAL site build on 2026-10-26 to 2026-10-28.

| Host | Role | IP / detail |
| --- | --- | --- |
| EXAPBSFAL001 | PBS server | 192.168.76.14 |
| QNAP NAS (EXANASFAL001) | NFS storage for PBS | 192.168.76.19, share `VM_Backups` |
| the-old-node | Original PVE node (being replaced) | PBS storage ID `EXAPBSFAL001` |
| EXAPVEFAL001 | Replacement PVE node (ex-ESXi host) | ZFS pool `tank` |

| Name | Value |
| --- | --- |
| NFS mountpoint on PBS | `/mnt/nfs-EXANASFAL001` |
| PBS datastore | `EXANASFAL001` at `/mnt/nfs-EXANASFAL001/datastore` |
| PBS user / token | `pve-backup@pbs` / `pve-backup@pbs!pve` |
| PVE storage ID for PBS | `EXAPBSFAL001` |

Values in `<angle brackets>` are placeholders: replace them with your own. Run every command as root on the host named in the step.

## Part 1: Enable NFS on the QNAP

The QNAP must run the NFS service and allow PBS (192.168.76.14) read/write access to `VM_Backups` with no root squash.

1. Control Panel → Network & File Services → Win/Mac/NFS/WebDAV → **NFS Service** tab.
2. Tick **Enable NFS v2/v3 Service** and **Enable NFS v4 Service**, then Apply.
3. Control Panel → Shared Folders → tick `VM_Backups` → **Edit Shared Folder Permission**.
4. Set the permission type dropdown at the top to **NFS host access**, then set:
   - Access right: ticked
   - Host/IP: `192.168.76.14`
   - Permission: read/write
   - Squash option: **NO_ROOT_SQUASH**
5. Apply.

QNAP exports shares as `/<ShareName>` (here `/VM_Backups`). There is no `/export/` prefix.

Verify from PBS:

```
root@EXAPBSFAL001:~# showmount -e 192.168.76.19
Export list for 192.168.76.19:
/volume_1
/images
/homes
/backups
/Web
/VM_Backups
...
```

## Part 2: Mount the NFS share on PBS

Mount the share on the PBS host (EXAPBSFAL001), not on the PVE node. PVE only talks to PBS over HTTPS port 8007.

1. Install the NFS client and create the mountpoint:

```
apt install nfs-common
mkdir -p /mnt/nfs-EXANASFAL001
chattr +i /mnt/nfs-EXANASFAL001
```

`chattr +i` makes the empty local directory immutable, so PBS can never write backups to local disk if the NFS mount is missing.

2. Add the mount to `/etc/fstab`. Use `vers=3`: the QNAP does not support `vers=4.2`.

```
sed -i '/192.168.76.19/d' /etc/fstab
echo '192.168.76.19:/VM_Backups  /mnt/nfs-EXANASFAL001  nfs  hard,vers=3,_netdev,x-systemd.mount-timeout=30  0 0' >> /etc/fstab
```

Resulting `/etc/fstab`:

```
# <file system> <mount point> <type> <options> <dump> <pass>
/dev/pbs/root / ext4 errors=remount-ro 0 1
/dev/pbs/swap none swap sw 0 0
proc /proc proc defaults 0 0
192.168.76.19:/VM_Backups  /mnt/nfs-EXANASFAL001  nfs  hard,vers=3,_netdev,x-systemd.mount-timeout=30  0 0
```

Always use `hard`. A `soft` mount can silently corrupt chunks during a network blip.

3. Mount, set ownership and test write access as the `backup` user (uid 34):

```
systemctl daemon-reload
mount /mnt/nfs-EXANASFAL001
chown backup:backup /mnt/nfs-EXANASFAL001
sudo -u backup touch /mnt/nfs-EXANASFAL001/test && rm /mnt/nfs-EXANASFAL001/test
```

Run the `chown` only after the mount succeeds. Before that it hits the immutable local directory and fails with "Operation not permitted", which is expected.

## Part 3: Create the PBS datastore

Create one datastore directory for all backups. PBS sorts them itself into `vm/<vmid>` and `ct/<ctid>`, so there is no directory per VM. To separate sites or nodes later, use namespaces in the same datastore; that keeps deduplication across them.

```
mkdir /mnt/nfs-EXANASFAL001/datastore
chown backup:backup /mnt/nfs-EXANASFAL001/datastore
proxmox-backup-manager datastore create EXANASFAL001 /mnt/nfs-EXANASFAL001/datastore
```

Creation builds 65,536 chunk directories over NFS and takes several minutes. Example output, trimmed:

```
Chunkstore create: 1%
Chunkstore create: 2%
...
Chunkstore create: 99%
Access time update check successful.
TASK OK
```

"Access time update check successful" confirms the NFS share supports atime updates, which garbage collection needs.

## Part 4: Create the PBS user, API token and permissions

PVE authenticates to PBS with an API token. The token needs the DatastoreBackup role on the datastore, granted to both the user and the token, because a token's effective permissions are the intersection of the two.

1. Create the user and token on EXAPBSFAL001:

```
proxmox-backup-manager user create pve-backup@pbs
proxmox-backup-manager user generate-token pve-backup@pbs pve
```

Example output (secret redacted):

```
Result: {
  "tokenid": "pve-backup@pbs!pve",
  "value": "<token-secret>"
}
```

The secret is shown only once. Store it in the password manager immediately.

2. Grant permissions:

```
proxmox-backup-manager acl update /datastore/EXANASFAL001 DatastoreBackup --auth-id pve-backup@pbs
proxmox-backup-manager acl update /datastore/EXANASFAL001 DatastoreBackup --auth-id 'pve-backup@pbs!pve'
```

3. Get the PBS certificate fingerprint:

```
root@EXAPBSFAL001:~# proxmox-backup-manager cert info | grep Fingerprint
Fingerprint (sha256): 9c:fa:0a:08:2e:b5:3a:26:73:e7:18:dc:c6:89:62:6f:33:8c:92:83:1e:c9:9b:70:14:6a:a8:a0:0a:d0:c1:ea
```

## Part 5: Add PBS storage to a PVE node and create the backup job

Run this on the PVE node, with the token secret from Part 4:

```
pvesm add pbs EXAPBSFAL001 \
  --server 192.168.76.14 \
  --datastore EXANASFAL001 \
  --username 'pve-backup@pbs!pve' \
  --password '<token-secret>' \
  --fingerprint '9c:fa:0a:08:2e:b5:3a:26:73:e7:18:dc:c6:89:62:6f:33:8c:92:83:1e:c9:9b:70:14:6a:a8:a0:0a:d0:c1:ea'
pvesm status
```

Example output from the-old-node:

```
Name               Type     Status     Total (KiB)      Used (KiB) Available (KiB)        %
esxi               esxi   inactive               0               0               0    0.00%
local               dir     active        40516856        22984824        15441640   56.73%
local-lvm       lvmthin   inactive               0               0               0    0.00%
esxi-old             esxi     active               0               0               0    0.00%
EXAPBSFAL001         pbs     active      1921316736       860544384      1060772352   44.79%
temp_store      zfspool     active      5709725696      1709337392      4000388303   29.94%
```

`EXAPBSFAL001` showing as active confirms the connection. The total and used figures are for the whole QNAP volume, so other shares on it consume the same space.

Unused or broken storage entries can be disabled to stop the warnings:

```
pvesm set esxi --disable 1
pvesm set local-lvm --disable 1
```

Then create the backup job:

1. Datacenter → Backup → Add.
2. Storage: `EXAPBSFAL001`. Mode: Snapshot. Select the VMs and set a schedule.
3. Select the job → **Run now** to test it.
4. On PBS: Datastore → `EXANASFAL001` → Prune & GC. Add a prune job (for example keep-daily 7, keep-weekly 4) and schedule GC outside working hours. Keep retention on PBS only, not in the PVE job.

## Part 6: Add another or a replacement PVE node

Another PVE node (for example EXAPVEFAL001 replacing the-old-node) uses the same `pvesm add pbs` command from Part 5, unchanged. Nothing changes on PBS. Backup jobs live on the PVE node, so recreate the job there.

- **Migration path:** the new node sees all existing backups immediately. Restore VMs from the `EXAPBSFAL001` storage → Backups → Restore.
- **VMID collisions:** PBS groups backups by VMID, not by node. A VM that keeps its ID continues its existing backup history, which is usually what you want. If the new node runs *different* VMs on IDs that already exist, give it its own namespace (Datastore → `EXANASFAL001` → Content → Add Namespace) and add `--namespace <namespace>` to the `pvesm add` command.
- **Per-node token (optional):** to revoke one node independently, run `proxmox-backup-manager user generate-token pve-backup@pbs <token-name>` and repeat both ACL lines from Part 4 for that token.
- **Decommissioning the old node:** delete its backup job first. Its backups stay on PBS until prune removes them.

## Part 7: Build local storage on EXAPVEFAL001 (ex-ESXi)

EXAPVEFAL001's data disks are still VMFS-formatted from ESXi. They are wiped and rebuilt as a ZFS RAIDZ1 pool with the spare SSD as read cache. **Wiping destroys all data on the VMFS disks**: confirm nothing on them is still needed first.

1. Identify the disks:

```
root@EXAPVEFAL001:~# lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL
NAME                                SIZE TYPE FSTYPE             MOUNTPOINT MODEL
sda                                 3.6T disk                               WDC WD4003FFBX-68MU3N0
└─sda1                              3.6T part VMFS_volume_member
sdb                                 3.6T disk                               WDC WD4003FFBX-68MU3N0
└─sdb1                              3.6T part VMFS_volume_member
sdc                                 3.6T disk                               WDC WD4003FFBX-68MU3N0
└─sdc1                              3.6T part VMFS_volume_member
sdd                                 3.6T disk                               WDC WD4003FFBX-68MU3N0
└─sdd1                              3.6T part VMFS_volume_member
sde                               223.6G disk                               SSDSCKKB240G8R
├─sde1                             1007K part
├─sde2                                1G part vfat               /boot/efi
└─sde3                              222G part LVM2_member
  ├─pve-swap                          8G lvm  swap               [SWAP]
  ├─pve-root                       65.5G lvm  ext4               /
...
sdf                               223.6G disk                               SSDSCKKB240G8R
└─sdf1                            223.6G part VMFS_volume_member
sdg                                  15G disk                               UDisk
...
```

| Disk | Use |
| --- | --- |
| sda–sdd (4 × 4 TB WD) | ZFS RAIDZ1 pool |
| sde (240 GB SSD) | PVE boot disk. Do not touch |
| sdf (240 GB SSD) | ZFS cache (L2ARC) |
| sdg (15 GB USB) | Old PVE install (`pve-OLD-…`). Remove it so the host can't boot from it |

The disks appear individually, so there is no hardware RAID. Use ZFS rather than LVM-thin, which gives no redundancy across bare disks.

2. Wipe the VMFS disks:

```
for d in sda sdb sdc sdd sdf; do wipefs -a /dev/$d; sgdisk --zap-all /dev/$d; done
```

3. Create the pool in the GUI: EXAPVEFAL001 → Disks → ZFS → Create. Select sda–sdd, RAID level **RAIDZ1**, ashift 12, compression lz4, with "Add Storage" ticked. This gives about 10.9 TB usable and survives one disk failure.
4. Add the SSD as cache from the CLI, since the GUI cannot add one. Use the stable by-id name:

```
root@EXAPVEFAL001:~# ls -l /dev/disk/by-id/ | grep sdf$
lrwxrwxrwx 1 root root  9 Oct 28 15:07 ata-SSDSCKKB240G8R_PHYH023403ZP240J -> ../../sdf
lrwxrwxrwx 1 root root  9 Oct 28 15:07 wwn-0x55cd2e41525aa7ca -> ../../sdf

zpool add EXAPVEFAL001 cache /dev/disk/by-id/ata-SSDSCKKB240G8R_PHYH023403ZP240J
zpool status EXAPVEFAL001
```

A cache device (L2ARC) speeds up reads only. If sync-write latency becomes the problem, swap it for a SLOG with `zpool remove`, then `zpool add <pool> log <device>`. This Intel SSD has power-loss protection, which makes it safe for SLOG.

## Part 8: Rename the ZFS pool to tank

A pool is renamed by exporting it and importing it under the new name. Do this before any VMs are on it. The cache device moves with the pool.

1. Remove the PVE storage entry (this does not touch the data) and export the pool:

```
pvesm remove EXAPVEFAL001
zpool export EXAPVEFAL001
```

2. Import it under the new name. Pass `-d /dev/disk/by-id`: without it, the import didn't find the pool.

```
root@EXAPVEFAL001:~# zpool import -d /dev/disk/by-id
  pool: EXAPVEFAL001
    id: 10230455683552427656
 state: ONLINE
action: The pool can be imported using its name or numeric identifier.
...
root@EXAPVEFAL001:~# zpool import -d /dev/disk/by-id EXAPVEFAL001 tank
```

3. Update the cache file and the boot-time import unit, which PVE's GUI created under the old name, then re-add the storage:

```
zpool set cachefile=/etc/zfs/zpool.cache tank
systemctl disable zfs-import@EXAPVEFAL001.service
systemctl enable zfs-import@tank.service
pvesm add zfspool tank --pool tank --content images,rootdir
rmdir /EXAPVEFAL001 2>/dev/null
```

4. Verify:

```
root@EXAPVEFAL001:~# zpool status
  pool: tank
 state: ONLINE
config:

        NAME                                     STATE     READ WRITE CKSUM
        tank                                     ONLINE       0     0     0
          raidz1-0                               ONLINE       0     0     0
            ata-WDC_WD4003FFBX-68MU3N0_VBGDKXKF  ONLINE       0     0     0
            ata-WDC_WD4003FFBX-68MU3N0_VBGDHKWF  ONLINE       0     0     0
            ata-WDC_WD4003FFBX-68MU3N0_VBGD6TWF  ONLINE       0     0     0
            ata-WDC_WD4003FFBX-68MU3N0_VBGDE18F  ONLINE       0     0     0
        cache
          ata-SSDSCKKB240G8R_PHYH023403ZP240J    ONLINE       0     0     0

errors: No known data errors
```

Reboot once before putting VMs on the pool to confirm `tank` imports at boot.

## Troubleshooting

Every error below was hit during this build.

| Error | Cause | Fix |
| --- | --- | --- |
| `chown: changing ownership of '/mnt/nfs-EXANASFAL001': Operation not permitted` | `chattr +i` on the unmounted directory (expected) | Mount first, then `chown` |
| `mount.nfs: Connection refused for 192.168.76.14:...` | Wrong IP: pointed at PBS itself, not the QNAP | Use the QNAP IP, 192.168.76.19 |
| `clnt_create: RPC: Program not registered` (showmount) | NFS service off, or wrong host | Enable NFS on the QNAP (Part 1); check the IP |
| `mount.nfs: Protocol not supported` | `vers=4.2` in fstab; the QNAP doesn't support it | Use `vers=3` |
| `mount: ... can't find in /etc/fstab` | Mountpoint name differs from the fstab entry | Match the path exactly |
| `mount.nfs: access denied by server` | No NFS host access rule for PBS on the share | Add 192.168.76.14, read/write, NO_ROOT_SQUASH |
| Wrong export path (`/export/VM_Backups`) | QNAP exports as `/<ShareName>` | Use `/VM_Backups`; check with `showmount -e 192.168.76.19` |
| `cannot import 'EXAPVEFAL001': no such pool available` | Default device scan didn't find the pool | `zpool import -d /dev/disk/by-id` |

Useful diagnostics from PBS:

```
nc -zv 192.168.76.19 2049
showmount -e 192.168.76.19
rpcinfo -p 192.168.76.19
sudo -u backup touch /mnt/nfs-EXANASFAL001/test && rm /mnt/nfs-EXANASFAL001/test
```

## Post-setup checklist

- [ ] `showmount -e 192.168.76.19` lists `/VM_Backups`
- [ ] NFS share mounted on EXAPBSFAL001 and writable as `backup`
- [ ] Datastore `EXANASFAL001` created
- [ ] Token secret stored in the password manager
- [ ] `pvesm status` shows `EXAPBSFAL001` active on each PVE node
- [ ] Backup job created and tested with Run now
- [ ] Prune job and GC schedule set on PBS
- [ ] USB stick (old PVE install) removed from EXAPVEFAL001
- [ ] `tank` pool imports cleanly after a reboot of EXAPVEFAL001
- [ ] Old backup job deleted before the-old-node is decommissioned
