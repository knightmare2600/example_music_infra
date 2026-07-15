#!/bin/bash
# =============================================================================
# Proxmox VE Monthly Hoover Script
# Version History:
#   1.0.0 - YYYY-MM-DD - Initial release
#   1.1.0 - 2026-05-27 - Journal retention 14d/500MB; Proxmox kernel cleanup added
#   1.2.0 - 2026-06-09 - PVE 9.x package naming: pve-kernel-* -> proxmox-kernel-*-signed
#                        Removed stale pve-headers-* removal code (no separate header
#                        packages in PVE 9.x). proxmox-kernel-helper excluded by pattern.
# =============================================================================
set -e
SCRIPT_NAME="pve-monthly-hoover"
LOG_TAG="$SCRIPT_NAME"

log_info() { echo "$1" | logger -t "$LOG_TAG" -p user.info;    echo "[INFO] $1"; }
log_warn() { echo "$1" | logger -t "$LOG_TAG" -p user.warning; echo "[WARN] $1"; }
log_error(){ echo "$1" | logger -t "$LOG_TAG" -p user.err;     echo "[ERROR] $1"; }

log_info "=== Proxmox VE Monthly Hoover Started ==="
log_info "Disk usage before hoovering:"
log_info "$(df -h / | tail -1 | awk '{print "Root: " $2 " total, " $3 " used, " $4 " available"}')"

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

log_info "Hoovering old Proxmox kernels..."
RUNNING_KERNEL=$(uname -r)
# uname -r returns e.g. 6.17.4-2-pve; the dpkg package name is proxmox-kernel-6.17.4-2-pve-signed
RUNNING_KERNEL_PKG="proxmox-kernel-${RUNNING_KERNEL}-signed"
# Query only versioned signed packages. This pattern automatically excludes:
#   - meta packages        (e.g. proxmox-kernel-6.17, proxmox-kernel-6.8)
#   - proxmox-kernel-helper  (must never be removed — excluded by pattern)
INSTALLED_PROXMOX_KERNELS=$(dpkg -l 'proxmox-kernel-*.*.*-*-pve-signed' 2>/dev/null | awk '/^ii/ {print $2}' | sort -V)
KERNEL_COUNT=$(echo "$INSTALLED_PROXMOX_KERNELS" | grep -c '[^[:space:]]' 2>/dev/null || echo 0)
if [ "$KERNEL_COUNT" -le 2 ]; then
  log_info "Only $KERNEL_COUNT versioned Proxmox kernel(s) installed — nothing to remove"
else
  if ! echo "$INSTALLED_PROXMOX_KERNELS" | grep -qx "$RUNNING_KERNEL_PKG"; then
    log_warn "Running kernel package $RUNNING_KERNEL_PKG not in dpkg list — skipping kernel cleanup"
  else
    LATEST_KERNEL=$(echo "$INSTALLED_PROXMOX_KERNELS" | tail -1)
    log_info "Running Proxmox kernel : $RUNNING_KERNEL_PKG"
    log_info "Latest Proxmox kernel  : $LATEST_KERNEL"
    KERNELS_TO_REMOVE=()
    while IFS= read -r kernel; do
      if [ "$kernel" != "$LATEST_KERNEL" ] && [ "$kernel" != "$RUNNING_KERNEL_PKG" ]; then
        KERNELS_TO_REMOVE+=("$kernel")
      fi
    done <<< "$INSTALLED_PROXMOX_KERNELS"
    if [ ${#KERNELS_TO_REMOVE[@]} -eq 0 ]; then
      log_info "Only running and latest Proxmox kernels present — nothing to remove"
    else
      log_info "Removing ${#KERNELS_TO_REMOVE[@]} old Proxmox kernel(s): ${KERNELS_TO_REMOVE[*]}"
      apt-get remove --purge -y "${KERNELS_TO_REMOVE[@]}" \
        > /dev/null 2>&1 \
        || log_warn "Some Proxmox kernel packages could not be removed — check manually"
      apt-get autoremove -y > /dev/null 2>&1 || true
      log_info "Proxmox kernel hoovering complete"
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
log_info "$(df -h / | tail -1 | awk '{print "Root: " $2 " total, " $3 " used, " $4 " available"}')"
log_info "=== Proxmox VE Monthly Hoover Completed Successfully ==="
exit 0
