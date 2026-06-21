# Example Music Limited — Proxmox VE ZFS VM Placement Audit Setup

> **Classification:** Internal — Infrastructure
> **Applies to:** PVE nodes running Proxmox VE 9.x (Debian Trixie)
> **Skill level:** PFY-friendly
> **Estimated time:** 10 minutes per node
> **Rollback time:** 3 minutes (3 files deleted, timer disabled)
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Reference / Helpers

### Deployed File Locations

| File | Path | Purpose |
|------|------|---------|
| Audit script | `/usr/local/bin/proxmox-zfs-vm-audit.py` | Queries pvesm/pvesh/zpool, writes JSON report |
| JSON report | `/tmp/zfs-vm-audit.json` | Current placement state — overwritten every 10 min, lost on reboot |
| Service unit | `/etc/systemd/system/proxmox-zfs-vm-audit.service` | systemd oneshot service unit |
| Timer unit | `/etc/systemd/system/proxmox-zfs-vm-audit.timer` | Fires every 10 minutes, 5 min after boot |

> **Note:** The JSON report lives in `/tmp` deliberately. It is volatile between reboots. The timer fires 5 minutes after boot and regenerates it. Zabbix will alert on a missing file if it does not appear within 15 minutes of a reboot — this is expected and resolves automatically.

---

### What Gets Checked

| Guest type | What is checked | Source |
|------------|----------------|--------|
| QEMU VMs | All disk attachments (scsi, virtio, ide, sata, efidisk, tpmstate) | `pvesh get /nodes/{node}/qemu/{vmid}/config` |
| LXC containers | Root filesystem and mountpoints (rootfs, mp0…mpN) | `pvesh get /nodes/{node}/lxc/{vmid}/config` |

> **Per-node:** The script runs locally on each PVE node and reports only that node's guests. Each node in a cluster runs its own copy.

> **Passthrough devices** (raw `/dev/` paths with no colon-delimited storage prefix) are skipped — they are not ZFS-backed via pvesm.

> **System pool auto-detection:** The script detects the boot/system pool at runtime by finding which ZFS pool mounts `/`. This pool is always excluded regardless of any pattern configuration — no hardcoding required.

---

### Placement Logic

| Pool type | Behaviour |
|-----------|-----------|
| Any pool not matching an excluded pattern | Accepted — no alert |
| System/boot pool (auto-detected, mounts `/`) | Always excluded |
| Pool matching an excluded glob pattern | Flagged |

Exclusion patterns are **glob-based and case-insensitive** by default:

| Pattern | Matches |
|---------|---------|
| `rpool` | `rpool` exactly |
| `pve*` | `pve`, `pve-data`, `pvepool` |
| `pbs*` | `pbs`, `PBS`, `pbs-fast`, `PBS-BACKUPS` |
| `Backup*` | `Backups`, `backup-pool`, `BACKUP2` |

The default excluded pattern list is: `rpool, pve*, Backups*, PBS*, pbs*, backup*`

To use a custom list, pass `--excluded-pools` in the `ExecStart` line of the service unit (see Part 3).

---

### Severity

| Condition | Severity |
|-----------|----------|
| All disks on acceptable pools | OK |
| One or more disks on an excluded pool | FLAGGED |
| pvesh config query failed for this guest | UNKNOWN |

Severity is per guest. The report summary carries counts of flagged and unknown guests across the node.

---

### JSON Report Format

Example `/tmp/zfs-vm-audit.json`:

```json
{
  "generated_iso":  "2026-06-01T10:00:00+00:00",
  "generated_unix": 1748772000,
  "hostname":       "pve01",
  "case_sensitive": false,
  "summary": {
    "total_vms_checked":  8,
    "total_lxc_checked":  2,
    "total_checked":      10,
    "flagged_count":      1,
    "unknown_count":      0,
    "flagged_vmids":      [105],
    "flagged_detail": [
      {
        "vmid":          105,
        "name":          "db01",
        "flagged_disks": [
          { "disk": "scsi0", "pool": "rpool" }
        ]
      }
    ],
    "system_pool":        "rpool",
    "excluded_patterns":  ["rpool", "pve*", "Backups*", "PBS*", "pbs*", "backup*"]
  },
  "vms": [
    {
      "vmid":          105,
      "name":          "db01",
      "type":          "qemu",
      "status":        "running",
      "severity":      "FLAGGED",
      "severity_int":  1,
      "flagged":       true,
      "flagged_disks": [{ "disk": "scsi0", "pool": "rpool" }],
      "all_disks": [
        { "disk": "scsi0", "spec": "local-zfs:vm-105-disk-0", "pool": "rpool", "excluded_pool": true }
      ]
    }
  ],
  "lxc": []
}
```

`severity_int` values: `0` = OK, `1` = FLAGGED, `-1` = UNKNOWN.

---

<details>
<summary>💻 Quick Reference Commands (click to expand)</summary>

#### Check Current State

```bash
# Is the timer active?
systemctl status proxmox-zfs-vm-audit.timer

# When does it next fire?
systemctl list-timers proxmox-zfs-vm-audit.timer

# Read the current JSON report (pretty-printed)
python3 -m json.tool /tmp/zfs-vm-audit.json

# Quick summary only
python3 -c "import json; d=json.load(open('/tmp/zfs-vm-audit.json')); print(d['summary'])"

# List only flagged guests
python3 -c "
import json
d = json.load(open('/tmp/zfs-vm-audit.json'))
for g in d['vms'] + d['lxc']:
  if g['flagged']:
    for fd in g['flagged_disks']:
      print(f\"{g['type']:4} {g['vmid']:5} {g['name']:30} disk={fd['disk']} pool={fd['pool']}\")
"

# Show which pool was auto-detected as the system pool
python3 -c "import json; d=json.load(open('/tmp/zfs-vm-audit.json')); print('System pool:', d['summary']['system_pool'])"

# Show which exclusion patterns are active
python3 -c "import json; d=json.load(open('/tmp/zfs-vm-audit.json')); print('Excluded patterns:', d['summary']['excluded_patterns'])"
```

#### Check Logs

```bash
# Last run (full output including any errors)
journalctl -u proxmox-zfs-vm-audit.service -n 50

# All runs today
journalctl -u proxmox-zfs-vm-audit.service --since today
```

#### Run Manually

```bash
# Run immediately without waiting for the timer
/usr/local/bin/proxmox-zfs-vm-audit.py

# Run with custom excluded patterns
/usr/local/bin/proxmox-zfs-vm-audit.py --excluded-pools 'rpool,pve*,pbs*,MyBackupPool'

# Then read the result
python3 -m json.tool /tmp/zfs-vm-audit.json
```

#### Inspect Storage and Pools Directly

```bash
# Show all pvesm storages and their types
pvesm status

# Show the config (including pool name) for a specific storage
pvesm config local-zfs

# List all ZFS pools on this node
zpool list

# Show which pool mounts / (the system pool the script auto-detects)
zfs list -o name,mountpoint | grep ' /$'
```

</details>

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-01 | v1.0 — Initial release |

---

## ⚠️ Before You Start

| | What this monitoring does |
|-|--------------------------|
| ✅ | Reports ZFS pool placement for all QEMU VM and LXC container disks on this node |
| ✅ | Auto-detects the system/boot pool at runtime — no hardcoding |
| ✅ | Writes a JSON report to `/tmp` every 10 minutes |
| ✅ | Feeds Zabbix items and triggers via the report file |
| ❌ | Does **not** move, copy, or delete any VM disks |
| ❌ | Does **not** modify any VM or container configuration |
| ❌ | Does **not** interfere with PBS backups, snapshots, or live migrations |

**If you see a placement alert in Zabbix:** do not attempt to move VM disks without speaking to a senior admin. Confirm the target storage pool exists and has sufficient space before any migration.

---

## Part 1 — Deploy the Script

### Step 1 — Log In to the Proxmox Host

```bash
ssh root@<proxmox-ip>
pveversion
# Expected output includes: pve-manager/9.x and Debian trixie
```

If `pveversion` does not show 9.x / trixie, stop and contact your senior admin.

---

### Step 2 — Confirm Dependencies Are Available

```bash
python3 --version && pvesh get /version --output-format json && zpool list
```

Expected output: a Python 3.x version string, then PVE version JSON, then a table of ZFS pools. If any command fails, contact your senior admin — all three are present by default on a PVE 9.x node with ZFS storage.

---

### Step 3 — Deploy the Script

```bash
install -m 0750 -o root -g root /path/to/proxmox-zfs-vm-audit.py /usr/local/bin/proxmox-zfs-vm-audit.py
```

If copying from a workstation via SCP:

```bash
scp proxmox-zfs-vm-audit.py root@<proxmox-ip>:/usr/local/bin/
ssh root@<proxmox-ip> chmod 0750 /usr/local/bin/proxmox-zfs-vm-audit.py
```

Verify:

```bash
ls -lh /usr/local/bin/proxmox-zfs-vm-audit.py
# Expected: -rwxr-x--- 1 root root ...
```

---

## Part 2 — Deploy the systemd Units

### Step 4 — Deploy the Service and Timer Files

```bash
cp proxmox-zfs-vm-audit.service /etc/systemd/system/proxmox-zfs-vm-audit.service
cp proxmox-zfs-vm-audit.timer   /etc/systemd/system/proxmox-zfs-vm-audit.timer
chmod 644 /etc/systemd/system/proxmox-zfs-vm-audit.service
chmod 644 /etc/systemd/system/proxmox-zfs-vm-audit.timer
```

---

### Step 5 — (Optional) Customise Excluded Pool Patterns

If this node uses pool names not covered by the defaults, edit the service file before enabling it:

```bash
nano /etc/systemd/system/proxmox-zfs-vm-audit.service
```

Find the `ExecStart` line and add `--excluded-pools`:

```ini
ExecStart=/usr/local/bin/proxmox-zfs-vm-audit.py --excluded-pools 'rpool,pve*,pbs*,MyBackupPool,FastVMs'
```

Glob patterns are case-insensitive. The system pool is always excluded regardless of what is listed here.

---

### Step 6 — Reload systemd and Enable the Timer

```bash
systemctl daemon-reload
systemctl enable --now proxmox-zfs-vm-audit.timer
```

Verify the timer is active:

```bash
systemctl status proxmox-zfs-vm-audit.timer
```

Expected: `Active: active (waiting)` with a next trigger time shown.

---

## Part 3 — Verify the Script Runs Correctly

### Step 7 — Run Once Manually

```bash
/usr/local/bin/proxmox-zfs-vm-audit.py
```

Expected stderr output (printed to the terminal):

```
[INFO] System/boot pool detected as: 'rpool'
[INFO] Excluded pool patterns: ['rpool', 'pve*', 'Backups*', 'PBS*', 'pbs*', 'backup*']
[INFO] zfs-vm-audit starting on pve01
[INFO] Storage map: {'local-zfs': 'rpool', 'VirtualMachines': 'VirtualMachines'}
[INFO] Done — 8 VMs, 2 LXC checked. Flagged: 0. Report: /tmp/zfs-vm-audit.json
```

If you see `[ERROR] pvesh not found` or `[ERROR] pvesm status failed`, contact your senior admin.

---

### Step 8 — Verify the JSON Report

```bash
python3 -m json.tool /tmp/zfs-vm-audit.json
```

Confirm:

- `hostname` matches this node's short hostname.
- `summary.system_pool` shows the correct boot pool name.
- `summary.excluded_patterns` lists the patterns you expect.
- `summary.total_vms_checked` and `summary.total_lxc_checked` match the number of guests on this node.
- `summary.flagged_count` is 0 unless you have VMs genuinely on an excluded pool.

If `flagged_count` is unexpectedly non-zero, check the `summary.flagged_detail` block to see which VM and which disk is causing it:

```bash
python3 -c "
import json
d = json.load(open('/tmp/zfs-vm-audit.json'))
for item in d['summary']['flagged_detail']:
  print(f\"VMID {item['vmid']} ({item['name']}): {item['flagged_disks']}\")
"
```

---

## Part 4 — Zabbix Configuration

### Step 9 — Confirm the Zabbix Agent Can Read the Report File

From the Zabbix server or proxy, run a `zabbix_get` check:

```bash
zabbix_get -s <proxmox-ip> -k 'vfs.file.contents[/tmp/zfs-vm-audit.json]'
```

Expected: the full JSON blob returned to stdout. If you see `ZBX_NOTSUPPORTED`, check:

- The Zabbix agent is running: `systemctl status zabbix-agent`
- The file exists and is readable: `ls -lh /tmp/zfs-vm-audit.json`
- The agent `AllowKey` or `Server` configuration allows this key and this server.

---

### Step 10 — Add Items and Triggers to the Template

Using `ZABBIX-ZFS-VM-AUDIT-ITEMS-TRIGGERS.txt` as the reference, add the following to your existing Proxmox template in Zabbix:

| Item | Key | Purpose |
|------|-----|---------|
| Full report (master) | `vfs.file.contents[/tmp/zfs-vm-audit.json]` | Source for all dependent items |
| Flagged VM count | `pve.zfs.flagged.count` | Number of guests with disks on excluded pools |
| Flagged VM IDs | `pve.zfs.flagged.vmids` | Array of affected VMIDs — for alert context |
| Flagged VM detail | `pve.zfs.flagged.detail` | vmid, name, disk, pool — for alert context |
| Unknown count | `pve.zfs.unknown.count` | Guests pvesh could not query |
| Total VMs checked | `pve.zfs.total.vms.checked` | Sanity check — zero on a live node = script error |
| Total LXC checked | `pve.zfs.total.lxc.checked` | Sanity check |
| Excluded patterns | `pve.zfs.excluded.patterns` | Confirm service ExecStart is configured correctly |
| System pool | `pve.zfs.system.pool` | Confirm auto-detection worked on this node |
| Report timestamp | `pve.zfs.generated.unix` | Staleness detection |
| Script exists | `vfs.file.exists[/usr/local/bin/proxmox-zfs-vm-audit.py]` | Deployment integrity |
| Service file exists | `vfs.file.exists[/etc/systemd/system/proxmox-zfs-vm-audit.service]` | Deployment integrity |
| Timer file exists | `vfs.file.exists[/etc/systemd/system/proxmox-zfs-vm-audit.timer]` | Deployment integrity |
| Report file exists | `vfs.file.exists[/tmp/zfs-vm-audit.json]` | Post-reboot recovery check |

Add the host macro on the template (or override per host):

| Macro | Default | Description |
|-------|---------|-------------|
| `{$ZFS_AUDIT_STALE_SECONDS}` | `7200` | Seconds before the staleness trigger fires |

---

### Step 11 — Verify Items Are Receiving Data

In Zabbix go to **Monitoring → Latest data**, filter by this host and the tag `component:storage`. All items from Step 10 should show recent values.

Confirm:

- `pve.zfs.generated.unix` is a recent Unix timestamp (not 0).
- `pve.zfs.total.vms.checked` is non-zero if this node has VMs.
- `pve.zfs.system.pool` shows the correct pool name.
- No triggers are firing unexpectedly.

---

## Part 5 — Rollback

If you need to remove this monitoring entirely:

```bash
systemctl disable --now proxmox-zfs-vm-audit.timer
rm /etc/systemd/system/proxmox-zfs-vm-audit.service
rm /etc/systemd/system/proxmox-zfs-vm-audit.timer
rm /usr/local/bin/proxmox-zfs-vm-audit.py
rm -f /tmp/zfs-vm-audit.json
systemctl daemon-reload
```

Then remove the items and triggers from the Zabbix template.

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*