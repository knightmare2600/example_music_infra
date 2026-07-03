# Example Music Limited — Proxmox VE Maintenance Automation Setup

> **Classification:** Internal — Infrastructure
> **Applies to:** PVE nodes running Proxmox VE 9.x (Debian Trixie)
> **Skill level:** PFY-friendly
> **Estimated time:** 15 minutes per node
> **Rollback time:** 5 minutes (3 files deleted, 2 timers disabled)
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Reference / Helpers

### Deployed File Locations

| File | Path | Purpose |
|------|------|---------|
| Kernel cleanup config | `/etc/apt/apt.conf.d/52unattended-upgrades-pve` | Controls unattended-upgrades behaviour |
| Hoover script | `/usr/local/bin/pve-monthly-hoover.sh` | Monthly cleanup — journals, temps, coredumps, old PVE kernels |
| Hoover service | `/etc/systemd/system/pve-monthly-hoover.service` | systemd oneshot service unit |
| Hoover timer | `/etc/systemd/system/pve-monthly-hoover.timer` | Fires 1st of month at 02:00 (± 15 min jitter) |
| Upgrade logs | `/var/log/unattended-upgrades/` | Debian security patch activity |
| Syslog | `/var/log/syslog` | Hoover run output (tag: `pve-monthly-hoover`) |

---

### What This Procedure Does

| Task | Mechanism | Frequency |
|------|-----------|-----------|
| Debian security patches | `unattended-upgrades` + `apt-daily-upgrade.timer` | Nightly |
| Old Debian kernel cleanup | `unattended-upgrades` (`Remove-Unused-Kernel-Packages`) | After each patch run |
| Old PVE kernel cleanup | `pve-monthly-hoover.sh` (section 5) | 1st of month |
| systemd journal trim | `pve-monthly-hoover.sh` (14 days / 500 MB) | 1st of month |
| Temp files & coredumps | `pve-monthly-hoover.sh` (7 days) | 1st of month |
| apt cache cleanup | `pve-monthly-hoover.sh` | 1st of month |

> **PVE kernel policy:** The hoover script keeps the **running kernel** and the **latest installed kernel**. All older `pve-kernel-*` and matching `pve-headers-*` packages are purged. Both are preserved because PVE nodes are rarely rebooted — keeping the latest allows a rollback path after the next maintenance window.

> **PVE package upgrades (pve-manager, pve-cluster, etc.) remain manual** — they require cluster coordination and are not touched by any automated process here.

---

<details>
<summary>💻 Quick Reference Commands (click to expand)</summary>

#### Check Current State

```bash
# Verify both timers are active
systemctl list-timers apt-daily-upgrade.timer pve-monthly-hoover.timer

# How many PVE kernels are installed?
dpkg -l 'pve-kernel-[0-9]*' | awk '/^ii/ {print $2}' | sort -V

# Which kernel is running?
uname -r

# Journal size
du -sh /var/log/journal

# Disk usage
df -h /
```

#### Check Logs

```bash
# Last hoover run (full output)
journalctl -u pve-monthly-hoover.service -n 50

# Hoover events in syslog
grep pve-monthly-hoover /var/log/syslog | tail -30

# Last unattended-upgrades run
tail -50 /var/log/unattended-upgrades/unattended-upgrades.log

# See what next unattended-upgrades run would do (dry run)
unattended-upgrade --debug --dry-run 2>&1 | head -100
```

#### Run Manually

```bash
# Run hoover immediately (do not wait for the 1st of month)
/usr/local/bin/pve-monthly-hoover.sh

# When is hoover next scheduled?
systemctl list-timers pve-monthly-hoover.timer
```

</details>

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-27 | v1.1 — Corrected kernel cleanup documentation: PVE kernel cleanup is handled by the hoover script (keep running + latest, purge rest), not by unattended-upgrades. Journal retention reduced to 14 days / 500 MB to prevent node instability. Fixed `ProtectSystem=strict` bug in service file (was silently preventing all writes to `/var`). |
| YYYY-MM-DD | v1.0 — Initial document |

---

## ⚠️ Before You Start

Read this before touching anything:

| | What the automation does |
|-|--------------------------|
| ✅ | Installs Debian security patches nightly via `unattended-upgrades` |
| ✅ | Cleans up old **Debian** kernels after patches (handled by unattended-upgrades) |
| ✅ | Cleans up old **PVE kernels** monthly (handled by hoover script — keeps running + latest) |
| ✅ | Cleans journals, temp files, coredumps, apt cache monthly |
| ✅ | Senior admins can still use the Proxmox GUI for all manual updates |
| ❌ | Does **not** automatically upgrade PVE packages (`pve-manager`, `pve-cluster`, etc.) |
| ❌ | Does **not** automatically reboot the node for any reason |

**If anything goes wrong:** call your senior admin. The rollback at the bottom of this document takes under 5 minutes.

---

## Part 1 — Kernel Cleanup (unattended-upgrades)

### Step 1 — Log In to the Proxmox Host

```bash
ssh root@<proxmox-ip>
pveversion
# Expected output includes: pve-manager/9.x and Debian trixie
```

If `pveversion` does not show 9.x / trixie, stop and contact your senior admin. This procedure is only validated for PVE 9.x on Trixie.

---

### Step 2 — Check Whether unattended-upgrades Is Installed

```bash
dpkg -l | grep unattended-upgrades
```

If you see a line starting with `ii  unattended-upgrades` → skip to **Step 4**.  
If you see nothing → continue to **Step 3**.

---

### Step 3 — Install unattended-upgrades (if needed)

```bash
apt update && apt install -y unattended-upgrades apt-listchanges
```

Wait for `Setting up unattended-upgrades...` before continuing.

---

### Step 4 — Create the Configuration File

Copy and paste the entire block below in one go:

```bash
tee /etc/apt/apt.conf.d/52unattended-upgrades-pve > /dev/null << 'EOF'
# Example Music Limited — Proxmox VE 9.x Unattended-Upgrades Configuration
# Scope: Debian security patches and old Debian kernel cleanup only.
# All PVE packages (pve-manager, pve-cluster, pve-kernel-*, etc.) are
# blacklisted — upgrades for these remain a manual, coordinated operation.
# Old PVE kernel cleanup is handled separately by pve-monthly-hoover.sh.

Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=${distro_codename}-security";
    "origin=Proxmox,label=Proxmox Debian Repository";
};

Unattended-Upgrade::Package-Blacklist {
    "proxmox-ve";
    "pve-kernel.*";
    "pve-headers.*";
    "pve-manager";
    "pve-qemu-kvm";
    "qemu-server";
    "pve-container";
    "pve-ha-manager";
    "pve-cluster";
};

Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "root";
Unattended-Upgrade::MailReport "on-change";
Unattended-Upgrade::Verbose "true";
EOF
```

---

### Step 5 — Verify the Configuration Was Written

```bash
cat /etc/apt/apt.conf.d/52unattended-upgrades-pve
```

The full configuration block should print. If the file is empty or missing, contact your senior admin.

---

### Step 6 — Dry-Run Test (Important)

```bash
unattended-upgrade --dry-run 2>&1 | head -60
```

**You should see:** `Checking:` lines — possibly some Debian security packages.  
**You must not see:** `proxmox-ve`, `pve-kernel`, `pve-manager`, or any other Proxmox package.

If any Proxmox package appears in the output, stop immediately and contact your senior admin.

---

### Step 7 — Enable the Service

```bash
systemctl enable apt-daily-upgrade.timer && systemctl start apt-daily-upgrade.timer
```

---

### Step 8 — Verify the Timer Is Active

```bash
systemctl status apt-daily-upgrade.timer
```

Expected output includes `active (waiting)`. If it shows `inactive` or `disabled`, run Step 7 again.

---

### Step 9 — Record the Current Kernel State

```bash
echo "=== Kernel baseline $(hostname) $(date) ===" && \
dpkg -l | grep 'linux-image' | wc -l && \
dpkg -l 'pve-kernel-[0-9]*' | awk '/^ii/ {print $2}' | sort -V && \
uname -r && \
df -h /boot
```

Write this down in your ticket. Check again in two weeks to confirm old Debian kernels are being removed.

---

## Part 2 — Monthly Hoover Setup

The hoover script runs on the 1st of each month at 02:00 and performs:

- **systemd journal cleanup** — vacuums to 14 days and 500 MB (whichever is reached first)
- **Temporary file cleanup** — removes `/tmp` and `/var/tmp` files older than 7 days
- **Coredump cleanup** — removes coredumps older than 7 days
- **apt cache cleanup** — `apt-get clean` and `apt-get autoclean`
- **PVE kernel cleanup** — purges old `pve-kernel-*` and `pve-headers-*` packages, keeping the running kernel and the latest installed kernel

---

### Step 10 — Deploy the Hoover Script

```bash
tee /usr/local/bin/pve-monthly-hoover.sh > /dev/null << 'SCRIPT_EOF'
#!/bin/bash
# =============================================================================
# Proxmox VE Monthly Hoover Script
# Version History:
#   1.0.0 - YYYY-MM-DD - Initial release
#   1.1.0 - 2026-05-27 - Journal retention 14d/500MB; PVE kernel cleanup added
# =============================================================================
set -e
SCRIPT_NAME="pve-monthly-hoover"
LOG_TAG="$SCRIPT_NAME"

log_info() { echo "$1" | logger -t "$LOG_TAG" -p user.info;    echo "[INFO] $1"; }
log_warn() { echo "$1" | logger -t "$LOG_TAG" -p user.warning; echo "[WARN] $1"; }
log_error(){ echo "$1" | logger -t "$LOG_TAG" -p user.err;     echo "[ERROR] $1"; }

log_info "=== Proxmox VE Monthly Hoover Started ==="
log_info "Disk usage before hoovering:"
df -h / | tail -1 | awk '{print "Root: " $2 " total, " $3 " used, " $4 " available"}' | xargs log_info

log_info "Hoovering systemd journals..."
JOURNALCTL_SIZE_BEFORE=$(du -sh /var/log/journal 2>/dev/null | awk '{print $1}' || echo "0B")
journalctl --vacuum-time=14d  > /dev/null 2>&1 || true
journalctl --vacuum-size=500M > /dev/null 2>&1 || true
JOURNALCTL_SIZE_AFTER=$(du -sh /var/log/journal 2>/dev/null | awk '{print $1}' || echo "0B")
log_info "Journals hoovered: $JOURNALCTL_SIZE_AFTER (was ~$JOURNALCTL_SIZE_BEFORE)"

log_info "Hoovering temporary files..."
find /tmp     -type f -atime +7 -delete 2>/dev/null || true
find /var/tmp -type f -atime +7 -delete 2>/dev/null || true
log_info "Temporary files older than 7 days removed"

log_info "Hoovering coredumps..."
COREDUMP_DIR="/var/lib/systemd/coredump"
if [ -d "$COREDUMP_DIR" ]; then
  BEFORE=$(find "$COREDUMP_DIR" -type f 2>/dev/null | wc -l)
  find "$COREDUMP_DIR" -type f -mtime +7 -delete 2>/dev/null || true
  AFTER=$(find "$COREDUMP_DIR" -type f 2>/dev/null | wc -l)
  log_info "Coredumps hoovered: removed $((BEFORE - AFTER)) (now $AFTER remaining)"
else
  log_warn "Coredump directory not found: $COREDUMP_DIR"
fi

log_info "Hoovering apt cache..."
APT_CACHE_BEFORE=$(du -sh /var/cache/apt/archives 2>/dev/null | awk '{print $1}' || echo "0B")
apt-get clean     > /dev/null 2>&1 || true
apt-get autoclean > /dev/null 2>&1 || true
APT_CACHE_AFTER=$(du -sh /var/cache/apt/archives 2>/dev/null | awk '{print $1}' || echo "0B")
log_info "Apt cache hoovered: $APT_CACHE_AFTER (was $APT_CACHE_BEFORE)"

log_info "Hoovering old PVE kernels..."
RUNNING_KERNEL=$(uname -r)
RUNNING_KERNEL_PKG="pve-kernel-${RUNNING_KERNEL}"
INSTALLED_PVE_KERNELS=$(dpkg -l 'pve-kernel-[0-9]*' 2>/dev/null | awk '/^ii/ {print $2}' | sort -V)
KERNEL_COUNT=$(echo "$INSTALLED_PVE_KERNELS" | grep -c '[^[:space:]]' 2>/dev/null || echo 0)
if [ "$KERNEL_COUNT" -le 2 ]; then
  log_info "Only $KERNEL_COUNT PVE kernel(s) installed — nothing to remove"
else
  if ! echo "$INSTALLED_PVE_KERNELS" | grep -qx "$RUNNING_KERNEL_PKG"; then
    log_warn "Running kernel $RUNNING_KERNEL_PKG not in dpkg list — skipping kernel cleanup"
  else
    LATEST_KERNEL=$(echo "$INSTALLED_PVE_KERNELS" | tail -1)
    log_info "Running PVE kernel : $RUNNING_KERNEL_PKG"
    log_info "Latest PVE kernel  : $LATEST_KERNEL"
    KERNELS_TO_REMOVE=()
    while IFS= read -r kernel; do
      if [ "$kernel" != "$LATEST_KERNEL" ] && [ "$kernel" != "$RUNNING_KERNEL_PKG" ]; then
        KERNELS_TO_REMOVE+=("$kernel")
      fi
    done <<< "$INSTALLED_PVE_KERNELS"
    if [ ${#KERNELS_TO_REMOVE[@]} -eq 0 ]; then
      log_info "Only running and latest PVE kernels present — nothing to remove"
    else
      log_info "Removing ${#KERNELS_TO_REMOVE[@]} old PVE kernel(s): ${KERNELS_TO_REMOVE[*]}"
      HEADERS_TO_REMOVE=()
      for k in "${KERNELS_TO_REMOVE[@]}"; do
        h="${k/pve-kernel-/pve-headers-}"
        if dpkg -l "$h" > /dev/null 2>&1; then HEADERS_TO_REMOVE+=("$h"); fi
      done
      apt-get remove --purge -y "${KERNELS_TO_REMOVE[@]}" "${HEADERS_TO_REMOVE[@]}" \
        > /dev/null 2>&1 \
        || log_warn "Some PVE kernel packages could not be removed — check manually"
      apt-get autoremove -y > /dev/null 2>&1 || true
      log_info "PVE kernel hoovering complete"
    fi
  fi
fi

log_info "Checking mail spools..."
MAIL_SPOOL_DIR="/var/mail"
if [ -d "$MAIL_SPOOL_DIR" ]; then
  MAIL_SIZE=$(du -sh "$MAIL_SPOOL_DIR" 2>/dev/null | awk '{print $1}' || echo "0B")
  log_info "Mail spool size: $MAIL_SIZE"
  MAIL_SIZE_KB=$(du -s "$MAIL_SPOOL_DIR" 2>/dev/null | awk '{print $1}' || echo "0")
  if [ "$MAIL_SIZE_KB" -gt 102400 ]; then
    log_warn "Mail spool exceeds 100MB ($MAIL_SIZE) — review /var/mail contents"
  fi
else
  log_info "Mail spool directory not found (OK)"
fi

log_info "Disk usage after hoovering:"
df -h / | tail -1 | awk '{print "Root: " $2 " total, " $3 " used, " $4 " available"}' | xargs log_info
log_info "=== Proxmox VE Monthly Hoover Completed Successfully ==="
exit 0
SCRIPT_EOF
```

Make it executable and test it:

```bash
chmod 755 /usr/local/bin/pve-monthly-hoover.sh
/usr/local/bin/pve-monthly-hoover.sh
```

Expected output ends with:
```
[INFO] === Proxmox VE Monthly Hoover Completed Successfully ===
```

If you see any `[ERROR]` lines, stop and contact your senior admin.

---

### Step 11 — Deploy the systemd Service File

```bash
tee /etc/systemd/system/pve-monthly-hoover.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Proxmox VE Monthly Hoover - Clean Journals, Temps, Coredumps, Old PVE Kernels
Documentation=man:journalctl(1) man:systemd-journal(8) man:apt-get(8)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/pve-monthly-hoover.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pve-monthly-hoover
User=root
Group=root

ProtectSystem=full
ProtectHome=yes
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
SERVICE_EOF
```

---

### Step 12 — Deploy the systemd Timer File

```bash
tee /etc/systemd/system/pve-monthly-hoover.timer > /dev/null << 'TIMER_EOF'
[Unit]
Description=Proxmox VE Monthly Hoover Timer
Documentation=man:systemd.timer(5)
Requires=pve-monthly-hoover.service

[Timer]
OnCalendar=*-*-01 02:00:00
Persistent=true
Accuracy=1h
OnBootSec=10min
RandomizedDelaySec=15min

[Install]
WantedBy=timers.target
TIMER_EOF
```

---

### Step 13 — Enable and Start the Timer

```bash
systemctl daemon-reload
systemctl enable pve-monthly-hoover.timer
systemctl start pve-monthly-hoover.timer
```

---

### Step 14 — Verify the Timer Is Active

```bash
systemctl status pve-monthly-hoover.timer
```

Expected output includes `active (waiting)`. If it shows `inactive` or `disabled`, re-run Step 13.

---

### Step 15 — Record Completion in Your Ticket

```
COMPLETED: PVE maintenance automation — $(hostname) — $(date)

Files deployed:
  /etc/apt/apt.conf.d/52unattended-upgrades-pve
  /usr/local/bin/pve-monthly-hoover.sh
  /etc/systemd/system/pve-monthly-hoover.service
  /etc/systemd/system/pve-monthly-hoover.timer

Timers running:
  apt-daily-upgrade.timer      — nightly Debian security patches + Debian kernel cleanup
  pve-monthly-hoover.timer     — 1st of month, 02:00, disk cleanup + old PVE kernel cleanup

PVE kernel state at time of setup:
  Running : $(uname -r)
  Installed:
$(dpkg -l 'pve-kernel-[0-9]*' | awk '/^ii/ {print "    " $2}' | sort -V)

Next steps:
  - In 2 weeks: verify old kernels are being cleaned (dpkg -l 'pve-kernel-[0-9]*' | wc -l)
  - Monthly: check logs — grep pve-monthly-hoover /var/log/syslog
  - Optional: configure Zabbix monitoring using ZABBIX-MONITORING-ITEMS-TRIGGERS.txt
```

---

## ✅ Verification Checklist

Before marking the ticket done, confirm each item:

**Part 1 — Kernel Cleanup:**
- [ ] `/etc/apt/apt.conf.d/52unattended-upgrades-pve` exists and `cat` shows the full config
- [ ] Dry-run (`unattended-upgrade --dry-run`) shows no Proxmox packages
- [ ] `systemctl status apt-daily-upgrade.timer` shows `active (waiting)`
- [ ] Baseline kernel count recorded in ticket

**Part 2 — Monthly Hoover:**
- [ ] `/usr/local/bin/pve-monthly-hoover.sh` is executable (`ls -l` shows `-rwxr-xr-x`)
- [ ] Script test run completed without `[ERROR]` output
- [ ] `/etc/systemd/system/pve-monthly-hoover.service` exists
- [ ] `/etc/systemd/system/pve-monthly-hoover.timer` exists
- [ ] `systemctl status pve-monthly-hoover.timer` shows `active (waiting)`

**Overall:**
- [ ] Completion recorded in ticketing system
- [ ] Senior admin notified
- [ ] (Optional) Zabbix monitoring configured

---

## 🔁 Rollback

To undo everything in under 5 minutes:

```bash
# Part 1 — kernel cleanup
rm -f /etc/apt/apt.conf.d/52unattended-upgrades-pve
systemctl stop apt-daily-upgrade.timer && systemctl disable apt-daily-upgrade.timer

# Part 2 — monthly hoover
systemctl stop pve-monthly-hoover.timer  && systemctl disable pve-monthly-hoover.timer
rm -f /etc/systemd/system/pve-monthly-hoover.service
rm -f /etc/systemd/system/pve-monthly-hoover.timer
rm -f /usr/local/bin/pve-monthly-hoover.sh
systemctl daemon-reload

# Verify clean
systemctl status pve-monthly-hoover.timer
# Expected: Unit pve-monthly-hoover.timer could not be found
```

No VM files, cluster state, or Proxmox configuration is touched by this rollback.

---

## 🚨 Troubleshooting

<details>
<summary>The hoover timer is not running</summary>

```bash
systemctl status pve-monthly-hoover.timer
systemctl enable pve-monthly-hoover.timer
systemctl start pve-monthly-hoover.timer
systemctl status pve-monthly-hoover.timer
```

</details>

<details>
<summary>The hoover script failed</summary>

```bash
# Check service journal output
journalctl -u pve-monthly-hoover.service -n 30

# Or check syslog
grep pve-monthly-hoover /var/log/syslog | tail -30

# Try running manually to see live output
/usr/local/bin/pve-monthly-hoover.sh
```

If the manual run succeeds, the script itself is fine — wait for next scheduled run or re-run manually after investigating the journal.

</details>

<details>
<summary>The unattended-upgrades dry-run shows Proxmox packages</summary>

The blacklist in the config is not matching correctly. Verify the file contents:

```bash
cat /etc/apt/apt.conf.d/52unattended-upgrades-pve
```

Confirm `pve-kernel.*` and `pve-manager` appear in `Package-Blacklist`. If the file is missing or truncated, re-run Step 4. Contact your senior admin if the problem persists.

</details>

<details>
<summary>The apt-daily-upgrade timer is not active</summary>

```bash
systemctl enable apt-daily-upgrade.timer
systemctl start apt-daily-upgrade.timer
systemctl status apt-daily-upgrade.timer
```

</details>

<details>
<summary>A PVE kernel was removed that should not have been</summary>

Check what is currently installed and running:

```bash
uname -r
dpkg -l 'pve-kernel-[0-9]*' | awk '/^ii/ {print $2}' | sort -V
```

If the running kernel package is missing from dpkg, the system is in an inconsistent state — contact your senior admin immediately. Do not reboot until this is resolved.

If only an older kernel you do not need was removed, this is expected behaviour.

</details>

<details>
<summary>A config file was deleted or corrupted</summary>

Re-deploy from the relevant step in this procedure, or ask your senior admin to re-deploy from the repository.

</details>

---

## ❓ FAQ

**Will this break my VMs?**  
No. The hoover script only touches logs, temp files, coredumps, apt cache, and old kernel packages. Running VMs are not affected.

**Can senior admins still use the Proxmox GUI for updates?**  
Yes. The blacklist only applies to the automated `unattended-upgrades` process. Manual GUI updates work normally.

**What if hoover runs whilst VMs are active?**  
Safe. It only cleans up files and removes unused kernel packages. No running processes or VM state is touched.

**Why not auto-update PVE packages?**  
PVE kernel and manager updates may require a reboot and need to be coordinated across a cluster. These remain a manual, scheduled operation.

**Can I change when the hoover runs?**  
Yes — edit `OnCalendar=` in `/etc/systemd/system/pve-monthly-hoover.timer` then run `systemctl daemon-reload`. Check with your senior admin before changing.

**The disk is already full — will hoover help?**  
It will reclaim space, but you may need to free a small amount manually first to allow apt to run. Ask your senior admin.

**Why 14 days and 500 MB for journals?**  
Journals that grow without bound have been observed to cause instability on PVE nodes. 14 days covers normal debugging needs; 500 MB prevents runaway growth on busy hosts with many services. Both limits are applied — whichever is reached first.

---

## 🔍 Optional — Zabbix Monitoring

If your environment uses Zabbix, the file `ZABBIX-MONITORING-ITEMS-TRIGGERS.txt` provides items and triggers to monitor:

- Existence of all deployed files
- Content validation (required configuration lines present)
- Both timer states (enabled and active)
- Alert if hoover has not run in over 35 days

Ask your senior admin to apply the template. If Zabbix is not in use, check the logs manually on a monthly basis.

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
