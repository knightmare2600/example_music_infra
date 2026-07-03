# Example Music Limited — Proxmox VE Snapshot Monitoring Setup

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
| Snapshot check script | `/usr/local/bin/pve-snapshot-check.py` | Queries pvesh, writes JSON report |
| JSON report | `/tmp/pve-snapshot-check.json` | Current snapshot state — overwritten hourly, lost on reboot |
| Snapshot service | `/etc/systemd/system/pve-snapshot-check.service` | systemd oneshot service unit |
| Snapshot timer | `/etc/systemd/system/pve-snapshot-check.timer` | Fires hourly, 10 min after boot |

> **Note:** The JSON report lives in `/tmp` deliberately. It is volatile between reboots. The timer fires 10 minutes after boot and regenerates it. Zabbix will alert on a missing file if it does not appear within 15 minutes of a reboot — this is expected and resolves automatically.

---

### What Gets Checked

| Guest type | What is checked | Source |
|------------|----------------|--------|
| QEMU VMs | All snapshots on all VMs on this node | `pvesh get /nodes/{node}/qemu/{vmid}/snapshot` |
| LXC containers | All snapshots on all containers on this node | `pvesh get /nodes/{node}/lxc/{vmid}/snapshot` |

> **Per-node:** The script runs locally on each PVE node and reports only that node's guests. Each node in a cluster runs its own copy.

> **PBS backups** do not create PVE snapshots and are not affected by or reported by this script.

> **`current` entry:** pvesh always returns an entry named `current` (the live-state pointer). This is filtered out — it is not a snapshot.

---

### Severity Matrix

| Condition | Severity |
|-----------|----------|
| No snapshots | OK |
| Any snapshot present | WARNING |
| 2 or more snapshots | HIGH |
| 2+ snapshots AND any ≥ 5 days old | CRITICAL |
| Any snapshot ≥ 7 days old (single or multiple) | CRITICAL |

Severities are per guest. The report summary carries the **worst** severity across all guests on the node.

---

### JSON Report Format

Example `/tmp/pve-snapshot-check.json`:

```json
{
  "generated_iso":  "2026-05-27T02:01:03+00:00",
  "generated_unix": 1748307663,
  "hostname":       "pve01",
  "summary": {
    "total_vms_checked":   8,
    "total_lxc_checked":   2,
    "vms_with_snapshots":  2,
    "lxc_with_snapshots":  0,
    "critical_count":      1,
    "high_count":          0,
    "warning_count":       1,
    "unknown_count":       0,
    "worst_severity":      "CRITICAL",
    "worst_severity_int":  3
  },
  "vms": [
    {
      "vmid":                 101,
      "name":                 "web01",
      "type":                 "qemu",
      "status":               "running",
      "severity":             "CRITICAL",
      "severity_int":         3,
      "snapshot_count":       2,
      "oldest_snapshot_days": 8.3,
      "newest_snapshot_days": 1.1,
      "snapshots": [
        {
          "name":        "pre-upgrade",
          "description": "Before kernel upgrade",
          "age_days":    8.3,
          "parent":      null,
          "children":    ["post-check"]
        },
        {
          "name":        "post-check",
          "description": "",
          "age_days":    1.1,
          "parent":      "pre-upgrade",
          "children":    []
        }
      ]
    }
  ],
  "lxc": []
}
```

Snapshots within each guest are listed oldest-first.
`severity_int` values: 0=OK, 1=WARNING, 2=HIGH, 3=CRITICAL, -1=UNKNOWN.

---

<details>
<summary>💻 Quick Reference Commands (click to expand)</summary>

#### Check Current State

```bash
# Is the timer active?
systemctl status pve-snapshot-check.timer

# When does it next fire?
systemctl list-timers pve-snapshot-check.timer

# Read the current JSON report (pretty-printed)
python3 -m json.tool /tmp/pve-snapshot-check.json

# Quick severity summary only
python3 -c "import json; d=json.load(open('/tmp/pve-snapshot-check.json')); print(d['summary'])"

# List only guests with snapshots
python3 -c "
import json
d = json.load(open('/tmp/pve-snapshot-check.json'))
for g in d['vms'] + d['lxc']:
  if g['snapshot_count'] > 0:
    print(f\"{g['type']:4} {g['vmid']:5} {g['name']:30} snaps={g['snapshot_count']} severity={g['severity']} oldest={g['oldest_snapshot_days']}d\")
"
```

#### Check Logs

```bash
# Last run (full output including any errors)
journalctl -u pve-snapshot-check.service -n 50

# All runs today
journalctl -u pve-snapshot-check.service --since today
```

#### Run Manually

```bash
# Run immediately without waiting for the timer
/usr/local/bin/pve-snapshot-check.py

# Then read the result
python3 -m json.tool /tmp/pve-snapshot-check.json
```

#### Inspect a Specific VM's Snapshots via pvesh

```bash
# Replace 101 with the VMID
pvesh get /nodes/$(hostname -s)/qemu/101/snapshot --output-format json | python3 -m json.tool

# LXC equivalent
pvesh get /nodes/$(hostname -s)/lxc/101/snapshot --output-format json | python3 -m json.tool
```

</details>

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-27 | v1.0 — Initial release |

---

## ⚠️ Before You Start

| | What this monitoring does |
|-|--------------------------|
| ✅ | Reports snapshot state for all QEMU VMs and LXC containers on this node |
| ✅ | Writes a JSON report to `/tmp` hourly |
| ✅ | Feeds Zabbix items and triggers via the report file |
| ❌ | Does **not** remove any snapshots under any circumstances |
| ❌ | Does **not** modify any VM or container configuration |
| ❌ | Does **not** interfere with PBS backups or live migrations |

**If you see a snapshot alert in Zabbix:** do not remove snapshots without speaking to a senior admin. Snapshots may be protecting an in-progress migration or a deliberate rollback point.

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

### Step 2 — Confirm python3 and pvesh Are Available

```bash
python3 --version && pvesh get /version --output-format json
```

Expected output: a Python 3.x version string, then JSON showing the PVE version. If either command fails, contact your senior admin — both are installed by default on PVE 9.x.

---

### Step 3 — Deploy the Script

Copy and paste the entire block below in one go. The heredoc writes the full script to disk:

```bash
cat > /usr/local/bin/pve-snapshot-check.py << 'PYEOF'
#!/usr/bin/env python3
# =============================================================================
# Proxmox VE Snapshot Check
#
# Version History:
#   1.0.0 - 2026-05-27 - Initial release
# =============================================================================

import json
import subprocess
import sys
import os
from datetime import datetime, timezone

LOG_FILE = "/tmp/pve-snapshot-check.json"

CRITICAL_AGE_DAYS       = 7
CRITICAL_MULTI_AGE_DAYS = 5
HIGH_MULTI_COUNT        = 2

SEVERITY_RANK = {"OK": 0, "WARNING": 1, "HIGH": 2, "CRITICAL": 3}


def pvesh_get(path):
  try:
    result = subprocess.run(
      ["pvesh", "get", path, "--output-format", "json"],
      capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
      print(f"[ERROR] pvesh get {path} failed (rc={result.returncode}): {result.stderr.strip()}", file=sys.stderr)
      return None
    return json.loads(result.stdout)
  except subprocess.TimeoutExpired:
    print(f"[ERROR] pvesh get {path} timed out", file=sys.stderr)
    return None
  except json.JSONDecodeError as exc:
    print(f"[ERROR] pvesh get {path} returned non-JSON: {exc}", file=sys.stderr)
    return None
  except FileNotFoundError:
    print("[ERROR] pvesh not found — is this a Proxmox VE node?", file=sys.stderr)
    sys.exit(1)


def get_node_name():
  return subprocess.run(["hostname", "-s"], capture_output=True, text=True).stdout.strip()


def build_snapshot_list(raw_snaps, now_ts):
  snaps = {}
  for s in raw_snaps:
    if s.get("name") == "current":
      continue
    name = s.get("name", "unknown")
    snaptime = s.get("snaptime", 0)
    age_days = round((now_ts - snaptime) / 86400, 1) if snaptime else 0.0
    snaps[name] = {
      "name":        name,
      "description": s.get("description", "").strip(),
      "age_days":    age_days,
      "parent":      s.get("parent", None),
      "children":    [],
    }
  for name, snap in snaps.items():
    parent = snap["parent"]
    if parent and parent in snaps:
      snaps[parent]["children"].append(name)
  return sorted(snaps.values(), key=lambda x: x["age_days"], reverse=True)


def calculate_severity(snapshots):
  if not snapshots:
    return "OK"
  count   = len(snapshots)
  max_age = max(s["age_days"] for s in snapshots)
  if max_age >= CRITICAL_AGE_DAYS:
    return "CRITICAL"
  if count >= HIGH_MULTI_COUNT and max_age >= CRITICAL_MULTI_AGE_DAYS:
    return "CRITICAL"
  if count >= HIGH_MULTI_COUNT:
    return "HIGH"
  return "WARNING"


def check_guests(node, guest_type, now_ts):
  guests_raw = pvesh_get(f"/nodes/{node}/{guest_type}")
  if guests_raw is None:
    print(f"[WARN] Could not enumerate {guest_type} guests on {node}", file=sys.stderr)
    return []
  results = []
  for guest in sorted(guests_raw, key=lambda x: x.get("vmid", 0)):
    vmid   = guest.get("vmid")
    name   = guest.get("name", f"{guest_type}-{vmid}")
    status = guest.get("status", "unknown")
    snaps_raw = pvesh_get(f"/nodes/{node}/{guest_type}/{vmid}/snapshot")
    if snaps_raw is None:
      results.append({
        "vmid": vmid, "name": name, "type": guest_type, "status": status,
        "severity": "UNKNOWN", "severity_int": -1,
        "snapshot_count": -1, "oldest_snapshot_days": -1, "newest_snapshot_days": -1,
        "snapshots": [], "error": "pvesh snapshot query failed",
      })
      continue
    snapshots = build_snapshot_list(snaps_raw, now_ts)
    severity  = calculate_severity(snapshots)
    oldest = max((s["age_days"] for s in snapshots), default=0.0)
    newest = min((s["age_days"] for s in snapshots), default=0.0)
    results.append({
      "vmid": vmid, "name": name, "type": guest_type, "status": status,
      "severity": severity, "severity_int": SEVERITY_RANK.get(severity, -1),
      "snapshot_count": len(snapshots),
      "oldest_snapshot_days": oldest, "newest_snapshot_days": newest,
      "snapshots": snapshots,
    })
  return results


def build_summary(vms, lxcs):
  all_guests = vms + lxcs
  worst_int = max((g["severity_int"] for g in all_guests if g["severity_int"] >= 0), default=0)
  worst     = {v: k for k, v in SEVERITY_RANK.items()}.get(worst_int, "OK")
  return {
    "total_vms_checked":  len(vms),
    "total_lxc_checked":  len(lxcs),
    "vms_with_snapshots": sum(1 for g in vms  if g["snapshot_count"] > 0),
    "lxc_with_snapshots": sum(1 for g in lxcs if g["snapshot_count"] > 0),
    "critical_count":     sum(1 for g in all_guests if g["severity"] == "CRITICAL"),
    "high_count":         sum(1 for g in all_guests if g["severity"] == "HIGH"),
    "warning_count":      sum(1 for g in all_guests if g["severity"] == "WARNING"),
    "unknown_count":      sum(1 for g in all_guests if g["severity"] == "UNKNOWN"),
    "worst_severity":     worst,
    "worst_severity_int": worst_int,
  }


def main():
  now_ts  = datetime.now(timezone.utc).timestamp()
  now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
  node    = get_node_name()
  print(f"[INFO] pve-snapshot-check starting on {node}", file=sys.stderr)
  vms  = check_guests(node, "qemu", now_ts)
  lxcs = check_guests(node, "lxc",  now_ts)
  summary = build_summary(vms, lxcs)
  report = {
    "generated_iso":  now_iso,
    "generated_unix": int(now_ts),
    "hostname":       node,
    "summary":        summary,
    "vms":            vms,
    "lxc":            lxcs,
  }
  try:
    with open(LOG_FILE, "w", encoding="utf-8") as fh:
      json.dump(report, fh, indent=2)
    os.chmod(LOG_FILE, 0o644)
  except OSError as exc:
    print(f"[ERROR] Could not write {LOG_FILE}: {exc}", file=sys.stderr)
    sys.exit(1)
  print(
    f"[INFO] Done — {summary['total_vms_checked']} VMs, "
    f"{summary['total_lxc_checked']} LXC checked. "
    f"Worst severity: {summary['worst_severity']}. "
    f"Report: {LOG_FILE}",
    file=sys.stderr,
  )


if __name__ == "__main__":
  main()
PYEOF
```

Make it executable and run a first test:

```bash
chmod 755 /usr/local/bin/pve-snapshot-check.py
/usr/local/bin/pve-snapshot-check.py
```

Expected output (stderr, also visible in the terminal):
```
[INFO] pve-snapshot-check starting on pve01
[INFO] Done — 8 VMs, 2 LXC checked. Worst severity: OK. Report: /tmp/pve-snapshot-check.json
```

If you see `[ERROR]` lines, stop and contact your senior admin.

---

### Step 4 — Verify the Report Was Written

```bash
python3 -m json.tool /tmp/pve-snapshot-check.json
```

You should see the full JSON report. Confirm `hostname` matches this node and `generated_iso` is recent.

---

### Step 5 — Check the Summary for Any Existing Snapshots

```bash
python3 -c "import json; d=json.load(open('/tmp/pve-snapshot-check.json')); print(d['summary'])"
```

If `worst_severity` is anything other than `OK`, record what you find in your ticket and notify your senior admin **before continuing**. Do not remove any snapshots yourself.

---

## Part 2 — Deploy the systemd Service and Timer

### Step 6 — Deploy the Service File

```bash
tee /etc/systemd/system/pve-snapshot-check.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Proxmox VE Snapshot Check - Report VM and LXC snapshot state to JSON
Documentation=man:pvesh(1)
After=pve-cluster.service pveproxy.service
Wants=pve-cluster.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/pve-snapshot-check.py
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pve-snapshot-check
User=root
Group=root

PrivateTmp=no
ProtectSystem=strict
ReadWritePaths=/tmp
ProtectHome=yes
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
SERVICE_EOF
```

---

### Step 7 — Deploy the Timer File

```bash
tee /etc/systemd/system/pve-snapshot-check.timer > /dev/null << 'TIMER_EOF'
[Unit]
Description=Proxmox VE Snapshot Check Timer — hourly
Documentation=man:systemd.timer(5)
Requires=pve-snapshot-check.service

[Timer]
OnCalendar=hourly
Persistent=true
Accuracy=1min
OnBootSec=10min
RandomizedDelaySec=3min

[Install]
WantedBy=timers.target
TIMER_EOF
```

---

### Step 8 — Enable and Start the Timer

```bash
systemctl daemon-reload
systemctl enable pve-snapshot-check.timer
systemctl start pve-snapshot-check.timer
```

---

### Step 9 — Verify the Timer Is Active

```bash
systemctl status pve-snapshot-check.timer
systemctl list-timers pve-snapshot-check.timer
```

Expected: `active (waiting)` and a next-run time approximately 1 hour from now (or at next full hour mark).

---

### Step 10 — Record Completion in Your Ticket

```
COMPLETED: PVE snapshot monitoring — $(hostname) — $(date)

Files deployed:
  /usr/local/bin/pve-snapshot-check.py
  /etc/systemd/system/pve-snapshot-check.service
  /etc/systemd/system/pve-snapshot-check.timer

Timer: pve-snapshot-check.timer — hourly, 10 min after boot

Snapshot state at time of setup:
$(python3 -c "import json; d=json.load(open('/tmp/pve-snapshot-check.json')); print(d['summary'])")

Next steps:
  - Configure Zabbix monitoring using ZABBIX-SNAPSHOT-ITEMS-TRIGGERS.txt
  - Verify Zabbix receives data within 10 minutes of Zabbix agent restart
```

---

## ✅ Verification Checklist

- [ ] `/usr/local/bin/pve-snapshot-check.py` exists and is executable (`-rwxr-xr-x`)
- [ ] Manual run completed without `[ERROR]` output
- [ ] `/tmp/pve-snapshot-check.json` exists and contains valid JSON
- [ ] `hostname` in report matches this node
- [ ] Any existing snapshots noted in ticket and reported to senior admin
- [ ] `/etc/systemd/system/pve-snapshot-check.service` exists
- [ ] `/etc/systemd/system/pve-snapshot-check.timer` exists
- [ ] `systemctl status pve-snapshot-check.timer` shows `active (waiting)`
- [ ] (Optional) Zabbix monitoring configured per `ZABBIX-SNAPSHOT-ITEMS-TRIGGERS.txt`

---

## 🔁 Rollback

```bash
systemctl stop pve-snapshot-check.timer && systemctl disable pve-snapshot-check.timer
rm -f /etc/systemd/system/pve-snapshot-check.service
rm -f /etc/systemd/system/pve-snapshot-check.timer
rm -f /usr/local/bin/pve-snapshot-check.py
rm -f /tmp/pve-snapshot-check.json
systemctl daemon-reload

# Verify clean
systemctl status pve-snapshot-check.timer
# Expected: Unit pve-snapshot-check.timer could not be found
```

No VM, container, snapshot, or cluster state is modified by this rollback.

---

## 🚨 Troubleshooting

<details>
<summary>The report file is missing or empty</summary>

```bash
# Run manually and watch for errors
/usr/local/bin/pve-snapshot-check.py

# Check last service run
journalctl -u pve-snapshot-check.service -n 30
```

If the error is `pvesh not found`, this is not a PVE node or pveproxy is not installed.
If the error is `Could not write /tmp/pve-snapshot-check.json`, check permissions on `/tmp`.

</details>

<details>
<summary>The timer is not firing</summary>

```bash
systemctl enable pve-snapshot-check.timer
systemctl start pve-snapshot-check.timer
systemctl list-timers pve-snapshot-check.timer
```

</details>

<details>
<summary>Zabbix shows the report as stale</summary>

The `generated_unix` field has not advanced in over 2 hours. Check:

```bash
systemctl status pve-snapshot-check.timer
journalctl -u pve-snapshot-check.service -n 30
```

Also confirm the Zabbix agent can read `/tmp/pve-snapshot-check.json`:

```bash
ls -l /tmp/pve-snapshot-check.json
# Expected: -rw-r--r-- root root
sudo -u zabbix cat /tmp/pve-snapshot-check.json | head -5
```

</details>

<details>
<summary>pvesh returns errors for some VMs</summary>

If `unknown_count > 0` in the report, pvesh failed to query snapshot state for at least one guest. This may happen if a VM is mid-migration or in a locked state. Check:

```bash
journalctl -u pve-snapshot-check.service -n 50 | grep ERROR
```

If the error is transient (migration in progress), it resolves on the next hourly run.
If persistent, contact your senior admin.

</details>

<details>
<summary>Zabbix is showing WARNING/HIGH/CRITICAL but there are no problem snapshots</summary>

The report may be from before the snapshots were removed. Run manually to regenerate:

```bash
/usr/local/bin/pve-snapshot-check.py
python3 -c "import json; d=json.load(open('/tmp/pve-snapshot-check.json')); print(d['summary'])"
```

Zabbix picks up the new file on its next poll (within 5 minutes).

</details>

---

## ❓ FAQ

**Will this script slow down my VMs or affect performance?**
No. It calls `pvesh get` which reads metadata from the PVE API. No VM disk or memory operations are performed.

**Does it run on every node in a cluster?**
Yes — deploy it on each node individually. Each node reports only the guests it hosts. This is correct: a VM can only be snapshotted from the node it is running on.

**What if a VM is migrated to another node between runs?**
On the next hourly run, the source node stops reporting it and the destination node starts reporting it. There is a window of up to one hour where the VM appears on neither node's report. This is expected.

**Why is the file in `/tmp` and not `/var/log`?**
Deliberate. The report is a current-state snapshot, not a log. It is regenerated fresh every hour. Keeping it in `/tmp` avoids log rotation concerns and makes it clear this is volatile operational data, not an audit trail. The Zabbix stale trigger handles the case where it stops being updated.

**Can I run this more frequently than hourly?**
Yes — change `OnCalendar=hourly` in the timer to e.g. `OnCalendar=*:0/30` for every 30 minutes. Discuss with your senior admin first as it increases pvesh API load slightly on large nodes.

**Why no `PrivateTmp=yes` in the service?**
`PrivateTmp=yes` gives the service its own private `/tmp` namespace, invisible to all other processes. The Zabbix agent needs to read the file, so the report must land in the real `/tmp`.

---

## 🔍 Zabbix Monitoring

Configure monitoring

```
cat ZABBIX-SNAPSHOT-ITEMS-TRIGGERS.txt
# Zabbix 7.0 Monitoring Configuration — PVE Snapshot Check
#
# Architecture:
#   One master item reads /tmp/pve-snapshot-check.json via vfs.file.contents.
#   All other items are Dependent Items using JSONPath preprocessing.
#   No agent scripts required.
#
# Severity integer mapping (used in trigger expressions):
#   0 = OK
#   1 = WARNING  (any snapshot present)
#   2 = HIGH     (2+ snapshots)
#   3 = CRITICAL (2+ snaps >= 5 days old, OR any snap >= 7 days old)
#  -1 = UNKNOWN  (pvesh query failed for that guest)
#
# Stale file alert: if generated_unix has not been updated in 2 hours,
# the timer or script has failed and Zabbix alerts on that independently.
#
# ============================================================================
# MASTER ITEM
# ============================================================================

Name: PVE - Snapshot Check Report (master)
Type: Zabbix agent
Key: vfs.file.contents[/tmp/pve-snapshot-check.json]
Type of information: Text
Update interval: 5m
History: 7d
Description: >
  Reads the full JSON report written by pve-snapshot-check.py.
  All other snapshot items depend on this master item.
  Script runs hourly; Zabbix polls every 5 minutes — any given
  poll reads the most recent run's output.

---

# ============================================================================
# DEPENDENT ITEMS  (all depend on the master item above)
# Preprocessing type: JSONPath
# ============================================================================

Name: PVE - Snapshot Worst Severity (integer)
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.worst.severity.int
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.summary.worst_severity_int
Description: >
  Numeric worst severity across all VMs and LXC on this node.
  0=OK, 1=WARNING, 2=HIGH, 3=CRITICAL.
  Use this item in trigger expressions.

---

Name: PVE - Snapshot Worst Severity (text)
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.worst.severity.text
Type of information: Text
Preprocessing: JSONPath  $.summary.worst_severity
Description: Human-readable worst severity. For display only — use the integer item in triggers.

---

Name: PVE - Snapshot CRITICAL Count
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.critical.count
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.summary.critical_count
Description: Number of VMs or LXC containers at CRITICAL severity.

---

Name: PVE - Snapshot HIGH Count
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.high.count
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.summary.high_count
Description: Number of VMs or LXC containers at HIGH severity.

---

Name: PVE - Snapshot WARNING Count
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.warning.count
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.summary.warning_count
Description: Number of VMs or LXC containers at WARNING severity.

---

Name: PVE - Snapshot UNKNOWN Count
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.unknown.count
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.summary.unknown_count
Description: Number of guests where pvesh query failed. Non-zero indicates a problem querying the API.

---

Name: PVE - VMs With Snapshots
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.vms.with.snapshots
Type of information: Text (Was: Numeric (unsigned))
Preprocessing: JSONPath  $.summary.vms_with_snapshots
Description: Count of QEMU VMs with at least one snapshot.

---

Name: PVE - LXC With Snapshots
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.lxc.with.snapshots
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.summary.lxc_with_snapshots
Description: Count of LXC containers with at least one snapshot.


---
* **Name:** PVE - LXC containers with snapshots detected
Expression: {host:pve.snapshot.lxc.with.snapshots.last()}>0

* **Severity:** Warning (or Average, depending on your preference)

* **Description:** {HOST.NAME} has {ITEM.LASTVALUE} LXC containers with snapshots

* **Enabled:** Yes


---

Name: PVE - Snapshot Report Generated (Unix timestamp)
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.generated.unix
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.generated_unix
Description: >
  Unix timestamp of when the report was generated.
  Used to detect a stale report (timer or script failure).
  Trigger fires if this has not advanced in 2 hours.

---

Name: PVE - Total VMs Checked
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.total.vms.checked
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.summary.total_vms_checked
Description: Total QEMU VMs enumerated on this node during last check.

---

Name: PVE - Total LXC Checked
Type: Dependent item
Master item: vfs.file.contents[/tmp/pve-snapshot-check.json]
Key: pve.snapshot.total.lxc.checked
Type of information: Numeric (unsigned)
Preprocessing: JSONPath  $.summary.total_lxc_checked
Description: Total LXC containers enumerated on this node during last check.

---

# ============================================================================
# TRIGGERS
# ============================================================================
# Host macro used: {$PVE_SNAPSHOT_STALE_SECONDS} — default 7200 (2 hours)
# Set this macro on the host or template if you want a different stale window.
# ============================================================================

Name: PVE - CRITICAL snapshot state on {HOST.NAME}
Expression: last(/pve-host/pve.snapshot.worst.severity.int) >= 3
Severity: High
Manual close: Yes
Description: >
  One or more VMs or LXC containers on {HOST.NAME} is in a CRITICAL snapshot state.
  This means: a snapshot >= 7 days old exists, OR multiple snapshots exist
  with at least one >= 5 days old.
  Review /tmp/pve-snapshot-check.json on the host for the full list.
  DO NOT auto-remove snapshots — check with a senior admin first.
  Snapshots may be protecting an in-progress migration or backup job.

---

Name: PVE - HIGH snapshot state on {HOST.NAME}
Expression: last(/pve-host/pve.snapshot.worst.severity.int) = 2
Severity: Average
Manual close: Yes
Description: >
  One or more VMs or LXC containers on {HOST.NAME} has multiple snapshots.
  Multiple snapshots consume significant disk space and can cause unexpected
  behaviour during live migration.
  Review /tmp/pve-snapshot-check.json on the host.
  DO NOT auto-remove snapshots without authorisation.

---

Name: PVE - WARNING snapshot state on {HOST.NAME}
Expression: last(/pve-host/pve.snapshot.worst.severity.int) = 1
Severity: Warning
Manual close: Yes
Description: >
  One or more VMs or LXC containers on {HOST.NAME} has at least one snapshot.
  Snapshots are not inherently a problem but forgotten ones consume disk space
  and can grow over time.
  Review /tmp/pve-snapshot-check.json on the host.

---

Name: PVE - Snapshot check report is stale on {HOST.NAME}
Expression: (now() - last(/pve-host/pve.snapshot.generated.unix)) > 7200
Severity: High
Manual close: No
Description: >
  The snapshot report on {HOST.NAME} has not been updated in over 2 hours.
  This means pve-snapshot-check.timer has likely failed, or the script
  crashed without writing output.
  Check: systemctl status pve-snapshot-check.timer
  Check: journalctl -u pve-snapshot-check.service -n 30

---

Name: PVE - Snapshot check has UNKNOWN guests on {HOST.NAME}
Expression: last(/pve-host/pve.snapshot.unknown.count) > 0
Severity: Average
Manual close: Yes
Description: >
  One or more guests on {HOST.NAME} could not be queried by pvesh.
  This may indicate pveproxy is down, a guest is in an inconsistent state,
  or the script does not have sufficient permissions.
  Check: journalctl -u pve-snapshot-check.service -n 50

---

Name: PVE - Snapshot report file missing on {HOST.NAME}
Expression: vfs.file.exists[/tmp/pve-snapshot-check.json] = 0
Severity: High
Manual close: No
Description: >
  /tmp/pve-snapshot-check.json does not exist on {HOST.NAME}.
  This is normal immediately after a reboot (file is in /tmp — volatile)
  and resolves once the timer fires (10 minutes after boot).
  If this persists beyond 15 minutes post-boot, investigate:
  Check: systemctl status pve-snapshot-check.timer
  Check: journalctl -u pve-snapshot-check.service -n 30

---

# ============================================================================
# ADDITIONAL FILE EXISTENCE CHECKS (match style of hoover monitoring)
# ============================================================================

Name: PVE - Snapshot Check Script Exists
Type: Zabbix agent
Key: vfs.file.exists[/usr/local/bin/pve-snapshot-check.py]
Type of information: Numeric (unsigned)
Update interval: 1h
Description: 1 = script present, 0 = missing

---

Name: PVE - Snapshot Check Service File Exists
Type: Zabbix agent
Key: vfs.file.exists[/etc/systemd/system/pve-snapshot-check.service]
Type of information: Numeric (unsigned)
Update interval: 1h
Description: 1 = service file present, 0 = missing

---

Name: PVE - Snapshot Check Timer File Exists
Type: Zabbix agent
Key: vfs.file.exists[/etc/systemd/system/pve-snapshot-check.timer]
Type of information: Numeric (unsigned)
Update interval: 1h
Description: 1 = timer file present, 0 = missing

---

Name: PVE - Snapshot Check Timer Status
Type: Zabbix agent (script)
Key: pve.snapshot.timer.status
Type of information: Text
Update interval: 30m
Description: Returns OK_ENABLED_ACTIVE if timer is healthy, otherwise a fault string.

Script/Command:
```bash
#!/bin/bash
STATUS=$(systemctl is-enabled pve-snapshot-check.timer 2>/dev/null)
ACTIVE=$(systemctl is-active pve-snapshot-check.timer 2>/dev/null)
if [ "$STATUS" = "enabled" ] && [ "$ACTIVE" = "active" ]; then
  echo "OK_ENABLED_ACTIVE"
  exit 0
elif [ "$STATUS" = "enabled" ] && [ "$ACTIVE" = "inactive" ]; then
  echo "ENABLED_BUT_INACTIVE"
  exit 1
elif [ "$STATUS" != "enabled" ]; then
  echo "DISABLED"
  exit 1
else
  echo "UNKNOWN"
  exit 1
fi
```

^– wrong copy the correct one on Monday

---

Name: PVE - Snapshot Check Script Missing
Expression: last(/pve-host/vfs.file.exists[/usr/local/bin/pve-snapshot-check.py]) = 0
Severity: High
Description: The snapshot check script has been removed from this host.

---

Name: PVE - Snapshot Check Timer Not Active
Expression: last(/pve-host/pve.snapshot.timer.status) <> "OK_ENABLED_ACTIVE"
Severity: High
Description: The snapshot check timer is not enabled or active.

---
```

using `ZABBIX-SNAPSHOT-ITEMS-TRIGGERS.txt`. Summary of what is monitored:

| Item | Key | Purpose |
|------|-----|---------|
| Full report (master) | `vfs.file.contents[/tmp/pve-snapshot-check.json]` | Source for all dependent items |
| Worst severity int | `pve.snapshot.worst.severity.int` | Used in trigger expressions |
| Worst severity text | `pve.snapshot.worst.severity.text` | Display |
| CRITICAL count | `pve.snapshot.critical.count` | How many guests are CRITICAL |
| HIGH count | `pve.snapshot.high.count` | How many guests are HIGH |
| WARNING count | `pve.snapshot.warning.count` | How many guests are WARNING |
| UNKNOWN count | `pve.snapshot.unknown.count` | How many guests pvesh could not query |
| VMs with snapshots | `pve.snapshot.vms.with.snapshots` | |
| LXC with snapshots | `pve.snapshot.lxc.with.snapshots` | |
| Report age | `pve.snapshot.generated.unix` | Stale detection — alerts if not updated in 2 hours |
| Script exists | `vfs.file.exists[...]` | Deployment integrity |
| Timer status | `pve.snapshot.timer.status` | Operational check |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
