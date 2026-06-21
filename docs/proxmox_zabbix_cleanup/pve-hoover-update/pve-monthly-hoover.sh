#!/bin/bash
# =============================================================================
# Proxmox VE Monthly Hoover Script
# Cleans: PVE kernels (running + latest kept, rest purged), systemd journals,
#         temporary files, coredumps, apt cache
# Logs to syslog for audit trail
# Safe for clustering — local disk only, no shared-storage writes
#
# Version History:
#   1.0.0 - YYYY-MM-DD - Initial release
#   1.1.0 - 2026-05-27 - Journal retention reduced to 14d/500MB to prevent
#                        node instability from oversized journals.
#                        Added PVE kernel cleanup: keeps running kernel and
#                        latest installed kernel, purges all older
#                        pve-kernel-* and matching pve-headers-* packages.
#                        Fixed --vacuum flag syntax (long form).
#                        Fixed ProtectSystem incompatibility (see .service).
# =============================================================================

set -e

SCRIPT_NAME="pve-monthly-hoover"
LOG_TAG="$SCRIPT_NAME"

log_info() {
  echo "$1" | logger -t "$LOG_TAG" -p user.info
  echo "[INFO] $1"
}

log_warn() {
  echo "$1" | logger -t "$LOG_TAG" -p user.warning
  echo "[WARN] $1"
}

log_error() {
  echo "$1" | logger -t "$LOG_TAG" -p user.err
  echo "[ERROR] $1"
}

# Start
log_info "=== Proxmox VE Monthly Hoover Started ==="
log_info "Disk usage before hoovering:"
df -h / | tail -1 | awk '{print "Root: " $2 " total, " $3 " used, " $4 " available"}' | xargs log_info

# ============================================================================
# 1. JOURNAL HOOVERING
#    14 days OR 500MB — whichever limit is reached first.
#    Rationale: oversized journals have been observed to cause PVE node
#    instability. 14 days is sufficient for operational debugging; 500MB
#    prevents runaway growth on busy hosts.
# ============================================================================

log_info "Hoovering systemd journals..."

JOURNALCTL_SIZE_BEFORE=$(du -sh /var/log/journal 2>/dev/null | awk '{print $1}' || echo "0B")

journalctl --vacuum-time=14d  > /dev/null 2>&1 || true
journalctl --vacuum-size=500M > /dev/null 2>&1 || true

JOURNALCTL_SIZE_AFTER=$(du -sh /var/log/journal 2>/dev/null | awk '{print $1}' || echo "0B")

log_info "Journals hoovered: $JOURNALCTL_SIZE_AFTER (was ~$JOURNALCTL_SIZE_BEFORE)"

# ============================================================================
# 2. TEMPORARY FILES HOOVERING
# ============================================================================

log_info "Hoovering temporary files..."

TEMP_FILES_REMOVED=0

if [ -d /tmp ]; then
  TEMP_FILES_REMOVED=$((TEMP_FILES_REMOVED + $(find /tmp -type f -atime +7 -delete 2>/dev/null | wc -l || echo 0)))
fi

if [ -d /var/tmp ]; then
  TEMP_FILES_REMOVED=$((TEMP_FILES_REMOVED + $(find /var/tmp -type f -atime +7 -delete 2>/dev/null | wc -l || echo 0)))
fi

log_info "Temporary files removed: $TEMP_FILES_REMOVED files older than 7 days"

# ============================================================================
# 3. COREDUMP HOOVERING
# ============================================================================

log_info "Hoovering coredumps..."

COREDUMP_DIR="/var/lib/systemd/coredump"

if [ -d "$COREDUMP_DIR" ]; then
  COREDUMP_COUNT_BEFORE=$(find "$COREDUMP_DIR" -type f 2>/dev/null | wc -l)
  find "$COREDUMP_DIR" -type f -mtime +7 -delete 2>/dev/null || true
  COREDUMP_COUNT_AFTER=$(find "$COREDUMP_DIR" -type f 2>/dev/null | wc -l)
  COREDUMPS_REMOVED=$((COREDUMP_COUNT_BEFORE - COREDUMP_COUNT_AFTER))
  log_info "Coredumps hoovered: removed $COREDUMPS_REMOVED (now $COREDUMP_COUNT_AFTER remaining)"
else
  log_warn "Coredump directory not found: $COREDUMP_DIR"
fi

# ============================================================================
# 4. APT CACHE HOOVERING
# ============================================================================

log_info "Hoovering apt cache..."

APT_CACHE_BEFORE=$(du -sh /var/cache/apt/archives 2>/dev/null | awk '{print $1}' || echo "0B")
apt-get clean     > /dev/null 2>&1 || true
apt-get autoclean > /dev/null 2>&1 || true
APT_CACHE_AFTER=$(du -sh /var/cache/apt/archives 2>/dev/null | awk '{print $1}' || echo "0B")

log_info "Apt cache hoovered: $APT_CACHE_AFTER (was $APT_CACHE_BEFORE)"

# ============================================================================
# 5. PVE KERNEL HOOVERING
#    PVE nodes are not rebooted frequently, so the running kernel and the
#    latest installed kernel may differ. Both are preserved to allow a clean
#    rollback path after the next scheduled maintenance reboot.
#    All other pve-kernel-* and matching pve-headers-* packages are purged.
#
#    What is kept:
#      - pve-kernel-$(uname -r)   — the kernel currently loaded
#      - latest pve-kernel-*      — the newest version installed (by version sort)
#
#    What is removed:
#      - all other pve-kernel-[0-9]* packages
#      - matching pve-headers-[0-9]* packages for removed kernels
# ============================================================================

log_info "Hoovering old PVE kernels..."

RUNNING_KERNEL=$(uname -r)
RUNNING_KERNEL_PKG="pve-kernel-${RUNNING_KERNEL}"

# Collect installed pve-kernel packages matching versioned name pattern
# (excludes meta-packages such as pve-kernel-helper, pve-kernel-libc-dev)
INSTALLED_PVE_KERNELS=$(dpkg -l 'pve-kernel-[0-9]*' 2>/dev/null \
  | awk '/^ii/ {print $2}' | sort -V)

KERNEL_COUNT=$(echo "$INSTALLED_PVE_KERNELS" | grep -c '[^[:space:]]' 2>/dev/null || echo 0)

if [ "$KERNEL_COUNT" -le 2 ]; then
  log_info "Only $KERNEL_COUNT PVE kernel(s) installed — nothing to remove"
else
  # Sanity check: confirm running kernel appears in the installed list
  if ! echo "$INSTALLED_PVE_KERNELS" | grep -qx "$RUNNING_KERNEL_PKG"; then
    log_warn "Running kernel package $RUNNING_KERNEL_PKG not found in dpkg list — skipping kernel cleanup"
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
      log_info "Removing ${#KERNELS_TO_REMOVE[@]} old PVE kernel package(s): ${KERNELS_TO_REMOVE[*]}"

      # Collect matching header packages for kernels being removed
      HEADERS_TO_REMOVE=()
      for k in "${KERNELS_TO_REMOVE[@]}"; do
        h="${k/pve-kernel-/pve-headers-}"
        if dpkg -l "$h" > /dev/null 2>&1; then
          HEADERS_TO_REMOVE+=("$h")
        fi
      done

      apt-get remove --purge -y "${KERNELS_TO_REMOVE[@]}" "${HEADERS_TO_REMOVE[@]}" \
        > /dev/null 2>&1 \
        || log_warn "Some PVE kernel packages could not be removed — check manually"

      apt-get autoremove -y > /dev/null 2>&1 || true

      log_info "PVE kernel hoovering complete"
    fi
  fi
fi

# ============================================================================
# 6. MAIL SPOOL CHECK (monitoring only — no auto-delete)
# ============================================================================

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

# ============================================================================
# 7. FINAL REPORT
# ============================================================================

log_info "Disk usage after hoovering:"
df -h / | tail -1 | awk '{print "Root: " $2 " total, " $3 " used, " $4 " available"}' | xargs log_info

log_info "=== Proxmox VE Monthly Hoover Completed Successfully ==="

exit 0
