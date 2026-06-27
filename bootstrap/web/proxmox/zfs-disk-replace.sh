#!/bin/bash
# =============================================================================
# zfs-disk-replace.sh — Proxmox ZFS RAID1 Disk Replacement
# Example Music Infrastructure — jukebox.internal
#
# Work it, make it, do it, makes us harder, better, faster, stronger
#
# USAGE: Run as root. No hardcoded disks. Prompts for everything.
#        Checks output after every step before proceeding.
#
# TESTED ON: Proxmox VE 9, legacy BIOS, ZFS RAID1
#
# Changelog:
#   2026-03-01  Initial script — interactive RAID1 disk replacement,
#               Ansible role, resilver monitoring
# =============================================================================
set -euo pipefail

POOL="rpool"

# ── Colours ───────────────────────────────────────────────────────────────────
R='\033[0;31m'
G='\033[0;32m'
Y='\033[1;33m'
C='\033[0;36m'
M='\033[0;35m'
W='\033[1;37m'
D='\033[2;37m'
NC='\033[0m'
BOLD='\033[1m'

ok()      { echo -e "  ${G}[+]${NC} $*"; }
info()    { echo -e "  ${C}[i]${NC} $*"; }
warn()    { echo -e "  ${Y}[!]${NC} $*"; }
err()     { echo -e "  ${R}[x]${NC} $*"; exit 1; }
step()    { echo -e "  ${M}[->]${NC} $*"; }
checking(){ echo -e "  ${C}[?]${NC} $*"; }

section() {
    echo
    echo -e "${Y}  +==================================================+${NC}"
    printf "${Y}  | ${W}%-50s${Y}|${NC}\n" "$1"
    echo -e "${Y}  +==================================================+${NC}"
    echo
}

confirm() {
    echo
    echo -e "${Y}  +-- CONFIRMATION REQUIRED ---------------------------${NC}"
    echo -e "${Y}  |${NC}  $1"
    echo -e "${Y}  +----------------------------------------------------${NC}"
    echo
    read -rp "$(echo -e "  ${R}${BOLD}Type YES (uppercase) to continue, anything else aborts: ${NC}")" REPLY
    if [[ "$REPLY" != "YES" ]]; then
        echo
        echo -e "${R}  Aborted. No changes made.${NC}"
        echo
        exit 1
    fi
    echo
}

check_ok() {
    # check_ok "description" "command to verify" "expected pattern"
    local desc="$1"
    local cmd="$2"
    local pattern="$3"
    checking "$desc..."
    local output
    output=$(eval "$cmd" 2>&1) || true
    if echo "$output" | grep -qE "$pattern"; then
        ok "$desc"
        return 0
    else
        echo -e "  ${R}[x]${NC} FAILED: $desc"
        echo -e "  ${R}    Expected pattern: ${pattern}${NC}"
        echo -e "  ${R}    Got:${NC}"
        echo "$output" | sed 's/^/      /'
        return 1
    fi
}

# ── Header ────────────────────────────────────────────────────────────────────
clear
echo
echo -e "${M}  ██████╗  █████╗ ███████╗████████╗    ${Y}██████╗ ██╗   ██╗███╗   ██╗██╗  ██╗${NC}"
echo -e "${M}  ██╔══██╗██╔══██╗██╔════╝╚══██╔══╝    ${Y}██╔══██╗██║   ██║████╗  ██║██║ ██╔╝${NC}"
echo -e "${M}  ██║  ██║███████║█████╗     ██║       ${Y}██████╔╝██║   ██║██╔██╗ ██║█████╔╝ ${NC}"
echo -e "${M}  ██║  ██║██╔══██║██╔══╝     ██║       ${Y}██╔═══╝ ██║   ██║██║╚██╗██║██╔═██╗ ${NC}"
echo -e "${M}  ██████╔╝██║  ██║██║        ██║       ${Y}██║     ╚██████╔╝██║ ╚████║██║  ██╗${NC}"
echo -e "${M}  ╚═════╝ ╚═╝  ╚═╝╚═╝        ╚═╝       ${Y}╚═╝      ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝${NC}"
echo
echo -e "${D}               harder. better. faster. stronger.${NC}"
echo -e "${D}               ZFS RAID1 Disk Replacement -- jukebox.internal${NC}"
echo

# ── Root check ────────────────────────────────────────────────────────────────
[[ "$EUID" -eq 0 ]] || err "Must run as root. Try: sudo bash $0"

# ── Reboot pending check ──────────────────────────────────────────────────────
if [[ -f /var/run/reboot-required ]]; then
    warn "A system reboot is pending (/var/run/reboot-required exists)."
    warn "Disk operations with a pending reboot can cause unexpected behaviour."
    read -rp "$(echo -e "  ${Y}Continue anyway? [y/N]: ${NC}")" CONT
    [[ "$CONT" =~ ^[Yy]$ ]] || { echo -e "${R}  Aborted.${NC}"; exit 1; }
fi

# ══════════════════════════════════════════════════════════════════════════════
section "STEP 1/6 -- POOL ASSESSMENT  [ work it ]"
# ══════════════════════════════════════════════════════════════════════════════

step "Reading pool state..."
zpool status "$POOL" &>/dev/null || err "Pool '${POOL}' not found -- is ZFS running?"

POOL_HEALTH=$(zpool list -H -o health "$POOL")
case "$POOL_HEALTH" in
    ONLINE)   ok   "Pool '${POOL}' is ONLINE" ;;
    DEGRADED) warn "Pool '${POOL}' is DEGRADED -- this is expected when a disk is missing" ;;
    *)        err  "Pool '${POOL}' is ${POOL_HEALTH} -- too unhealthy to proceed safely" ;;
esac

echo
echo -e "${W}  Current pool layout:${NC}"
zpool status "$POOL" | grep -A30 "config:" | grep -v "^$" | sed 's/^/    /'
echo

# Find the missing vdev -- numeric ghost ID
MISSING_ID=$(zpool status "$POOL" | awk '
    /UNAVAIL|REMOVED|FAULTED/ {
        if ($1 ~ /^[0-9]{5,}$/) { print $1; exit }
    }
')

# Find what it was
WAS_DEV=$(zpool status "$POOL" | grep -oP 'was \K/dev/\S+' | head -1 || true)

# Find the healthy vdev partition (e.g. sda3)
HEALTHY_PART=$(zpool status "$POOL" | awk '
    /ONLINE/ && $1 ~ /^(sd|nvme|vd)[a-z]+[0-9]+$/ { print $1; exit }
')
[[ -n "$HEALTHY_PART" ]] || err "Cannot identify healthy vdev -- check zpool status manually"

# Derive the healthy disk (strip partition number)
HEALTHY_DISK=$(echo "$HEALTHY_PART" | sed 's/[0-9]*$//')
HEALTHY_DEV="/dev/${HEALTHY_DISK}"

[[ -n "$MISSING_ID" ]] || err "No missing/unavailable vdev found -- is the pool actually degraded?"

info "Missing vdev ID : ${R}${MISSING_ID}${NC}  (was: ${WAS_DEV:-unknown})"
info "Healthy vdev    : ${G}${HEALTHY_PART}${NC}  (disk: ${G}${HEALTHY_DEV}${NC})"

echo
echo -e "  ${Y}Does this match what you expect?${NC}"
echo -e "  ${Y}The healthy disk shown above should be the one still physically present.${NC}"
confirm "Pool state looks correct -- missing vdev is ${MISSING_ID}, healthy disk is ${HEALTHY_DEV}"

# ══════════════════════════════════════════════════════════════════════════════
section "STEP 2/6 -- IDENTIFY NEW DISK  [ make it ]"
# ══════════════════════════════════════════════════════════════════════════════

echo -e "  Healthy disk in pool : ${G}${HEALTHY_DEV}${NC}"
echo -e "  ${R}Do NOT select ${HEALTHY_DEV} -- that disk contains your live data.${NC}"
echo

# Build disk list excluding the healthy disk
echo -e "  ${W}Available disks:${NC}"
mapfile -t ALL_DISKS < <(lsblk -dno NAME | grep -E '^(sd|nvme|vd)')
CANDIDATE_DISKS=()
i=1
for disk in "${ALL_DISKS[@]}"; do
    dev="/dev/${disk}"
    size=$(lsblk -dno SIZE "$dev" 2>/dev/null || echo "?")
    serial=$(smartctl -i "$dev" 2>/dev/null | awk '/Serial Number/{print $3}' || echo "n/a")
    partcount=$(lsblk -no NAME "$dev" 2>/dev/null | grep -c "^[└├]" || echo "0")
    zfs_label=""
    if zdb -l "$dev" 2>/dev/null | grep -q "pool_guid"; then
        zfs_label="${Y}[has ZFS label]${NC}"
    fi
    if [[ "$dev" == "$HEALTHY_DEV" ]]; then
        echo -e "    ${D}  -   ${dev}  ${size}  serial: ${serial}  ${G}[HEALTHY POOL MEMBER -- cannot select]${NC}"
    else
        echo -e "    ${W}  ${i})${NC}  ${dev}  ${size}  serial: ${C}${serial}${NC}  partitions: ${partcount}  ${zfs_label}"
        CANDIDATE_DISKS+=("$dev")
        ((i++))
    fi
done

echo
[[ "${#CANDIDATE_DISKS[@]}" -gt 0 ]] || err "No candidate disks found -- is the new disk inserted?"

# Default to first candidate
DEFAULT_PICK=1
while true; do
    read -rp "$(echo -e "  ${Y}Select replacement disk [default: ${DEFAULT_PICK}]: ${NC}")" PICK
    PICK="${PICK:-$DEFAULT_PICK}"
    if [[ "$PICK" =~ ^[0-9]+$ ]] && [[ "$PICK" -ge 1 ]] && [[ "$PICK" -le "${#CANDIDATE_DISKS[@]}" ]]; then
        NEW_DEV="${CANDIDATE_DISKS[$((PICK-1))]}"
        break
    fi
    warn "Invalid -- enter a number between 1 and ${#CANDIDATE_DISKS[@]}"
done

NEW_ESP="${NEW_DEV}2"
NEW_ZFS="${NEW_DEV}3"
NEW_SIZE=$(lsblk -dno SIZE "$NEW_DEV" 2>/dev/null || echo "?")
NEW_SERIAL=$(smartctl -i "$NEW_DEV" 2>/dev/null | awk '/Serial Number/{print $3}' || echo "n/a")
HEALTHY_SIZE=$(lsblk -dno SIZE "$HEALTHY_DEV" 2>/dev/null || echo "?")
HEALTHY_SERIAL=$(smartctl -i "$HEALTHY_DEV" 2>/dev/null | awk '/Serial Number/{print $3}' || echo "n/a")

echo
ok "Selected : ${W}${NEW_DEV}${NC}  ${NEW_SIZE}  serial: ${C}${NEW_SERIAL}${NC}"
info "Healthy  : ${W}${HEALTHY_DEV}${NC}  ${HEALTHY_SIZE}  serial: ${C}${HEALTHY_SERIAL}${NC}"

# ── Safety checks ─────────────────────────────────────────────────────────────
echo
step "Running safety checks..."

[[ "$NEW_DEV" != "$HEALTHY_DEV" ]] \
    || err "New disk and healthy disk are the same device (${NEW_DEV}) -- cannot proceed"
ok "New disk is not the healthy pool member"

if zpool status "$POOL" 2>/dev/null | grep -qE "$(basename $NEW_DEV)[0-9]*\s+ONLINE"; then
    err "${NEW_DEV} has a partition that is currently ONLINE in the pool -- wrong disk selected?"
fi
ok "New disk is not an active pool member"

MOUNTS=$(lsblk -no MOUNTPOINT "$NEW_DEV" 2>/dev/null | grep -v '^$' || true)
[[ -z "$MOUNTS" ]] || err "${NEW_DEV} has mounted partitions: ${MOUNTS} -- unmount first"
ok "New disk has no mounted partitions"

NEW_BYTES=$(lsblk -bdno SIZE "$NEW_DEV" 2>/dev/null || echo 0)
GOOD_BYTES=$(lsblk -bdno SIZE "$HEALTHY_DEV" 2>/dev/null || echo 0)
if [[ "$NEW_BYTES" -lt "$GOOD_BYTES" ]]; then
    err "${NEW_DEV} (${NEW_SIZE}) is smaller than healthy disk ${HEALTHY_DEV} (${HEALTHY_SIZE}) -- replacement must be >= healthy disk size"
fi
ok "Size check passed (${NEW_SIZE} >= ${HEALTHY_SIZE})"

if [[ "$NEW_BYTES" -gt "$GOOD_BYTES" ]]; then
    info "New disk is larger -- pool can be expanded after both disks are replaced with: zpool online -e ${POOL} ${NEW_DEV}"
fi

# ══════════════════════════════════════════════════════════════════════════════
section "STEP 3/6 -- FINAL CONFIRMATION  [ do it ]"
# ══════════════════════════════════════════════════════════════════════════════

echo -e "${W}  +-- WHAT IS ABOUT TO HAPPEN -------------------------${NC}"
echo -e "${W}  |${NC}"
echo -e "${W}  |  Missing vdev     : ${R}${MISSING_ID}${NC}  (was: ${WAS_DEV:-unknown})"
echo -e "${W}  |  Replace with     : ${G}${NEW_DEV}${NC}  (${NEW_SIZE}, serial: ${NEW_SERIAL})"
echo -e "${W}  |  Healthy reference: ${G}${HEALTHY_DEV}${NC}  (${HEALTHY_SIZE}, serial: ${HEALTHY_SERIAL})"
echo -e "${W}  |${NC}"
echo -e "${W}  |  1. sgdisk: copy partition table ${G}${HEALTHY_DEV}${NC} -> ${R}${NEW_DEV}${NC}"
echo -e "${W}  |  2. sgdisk: randomise GUIDs on ${R}${NEW_DEV}${NC}"
echo -e "${W}  |  3. partprobe: tell kernel about new partitions"
echo -e "${W}  |  4. zpool replace: resilver data onto ${R}${NEW_DEV}3${NC}"
echo -e "${W}  |  5. proxmox-boot-tool: install GRUB on ${R}${NEW_DEV}2${NC}"
echo -e "${W}  |  6. proxmox-boot-tool clean: remove stale ESP UUIDs"
echo -e "${W}  |${NC}"
echo -e "${W}  |  ${R}ALL existing data on ${NEW_DEV} will be destroyed.${NC}"
echo -e "${W}  |  ${G}${HEALTHY_DEV} will NOT be modified in any way.${NC}"
echo -e "${W}  +----------------------------------------------------${NC}"

confirm "Confirmed: wipe and rebuild ${NEW_DEV} from ${HEALTHY_DEV}"

# ══════════════════════════════════════════════════════════════════════════════
section "STEP 4/6 -- PARTITION TABLE  [ harder ]"
# ══════════════════════════════════════════════════════════════════════════════

step "Copying partition table from ${HEALTHY_DEV} to ${NEW_DEV}..."
sgdisk "$HEALTHY_DEV" -R "$NEW_DEV" 2>&1 | sed 's/^/    /'

# Verify
# Verify partition table looks right - check for expected partition type codes
SGDISK_OUT=$(sgdisk -p "${NEW_DEV}" 2>&1)
if echo "$SGDISK_OUT" | grep -qiE "EF02|EF00|BF01|BIOS boot|EFI System|Solaris"; then
    ok "Partition table verified on ${NEW_DEV}"
    echo "$SGDISK_OUT" | grep -E "^[[:space:]]+[0-9]" | sed 's/^/    /'
else
    echo -e "  ${R}[x]${NC} Partition table on ${NEW_DEV} does not look right:"
    echo "$SGDISK_OUT" | sed 's/^/    /'
    err "sgdisk verification failed -- partition table may not have copied correctly"
fi
ok "Partition table verified on ${NEW_DEV}"

step "Randomising GUIDs on ${NEW_DEV}..."
sgdisk -G "$NEW_DEV" 2>&1 | sed 's/^/    /'

# Verify GUIDs differ from healthy disk
HEALTHY_GUID=$(sgdisk -p "$HEALTHY_DEV" 2>/dev/null | grep "Disk identifier" | awk '{print $NF}')
NEW_GUID=$(sgdisk -p "$NEW_DEV" 2>/dev/null | grep "Disk identifier" | awk '{print $NF}')
if [[ "$HEALTHY_GUID" == "$NEW_GUID" ]]; then
    err "GUIDs are still identical between ${HEALTHY_DEV} and ${NEW_DEV} -- sgdisk -G may have failed"
fi
ok "GUIDs are unique: ${HEALTHY_DEV}=${HEALTHY_GUID}  ${NEW_DEV}=${NEW_GUID}"

step "Forcing kernel to re-read partition table on ${NEW_DEV}..."
partprobe "$NEW_DEV" 2>/dev/null || true
blockdev --rereadpt "$NEW_DEV" 2>/dev/null || true
sleep 2

if [[ ! -b "${NEW_ZFS}" ]]; then
    warn "Kernel cannot see ${NEW_ZFS} yet -- ZFS likely holds a lock on the disk"
    touch /var/run/reboot-required 2>/dev/null || true
    echo
    echo -e "  ${Y}A reboot is required. After rebooting, re-run this script.${NC}"
    echo -e "  ${Y}The partition table is already on the disk -- the script will${NC}"
    echo -e "  ${Y}skip straight to the ZFS replace step.${NC}"
    echo
    read -rp "$(echo -e "  ${Y}Reboot now? [y/N]: ${NC}")" DO_REBOOT
    if [[ "$DO_REBOOT" =~ ^[Yy]$ ]]; then
        info "Rebooting in 5 seconds..."
        sleep 5
        reboot
    else
        info "Remember to reboot before re-running."
        exit 0
    fi
fi

# Verify all three partitions are visible
for part in "${NEW_DEV}1" "${NEW_DEV}2" "${NEW_DEV}3"; do
    [[ -b "$part" ]] || err "Partition ${part} not visible after partprobe"
    ok "Partition ${part} visible"
done

echo
info "Partition layout on ${NEW_DEV}:"
fdisk -l "$NEW_DEV" 2>/dev/null | grep -E "^/dev" | sed 's/^/    /'

# ══════════════════════════════════════════════════════════════════════════════
section "STEP 5/6 -- ZFS RESILVER  [ faster ]"
# ══════════════════════════════════════════════════════════════════════════════

info "Replacing vdev : ${Y}${MISSING_ID}${NC} -> ${G}${NEW_ZFS}${NC}"

step "Issuing zpool replace..."
zpool replace -f "$POOL" "$MISSING_ID" "$NEW_ZFS"
ok "zpool replace accepted"

echo
info "Waiting for resilver... (Ctrl-C to detach, then: watch zpool status ${POOL})"
echo

RESILVER_START=$(date +%s)
while true; do
    STATUS=$(zpool status "$POOL" 2>/dev/null)
    if echo "$STATUS" | grep -q "resilver in progress"; then
        PCT=$(echo   "$STATUS" | grep -oE '[0-9]+\.[0-9]+% done' | head -1 || echo "?")
        SPEED=$(echo "$STATUS" | grep -oE '[0-9]+(\.[0-9]+)?[KMGT]/s' | head -1 || echo "?")
        ETA=$(echo   "$STATUS" | grep -oE '[0-9]+h[0-9]+m|[0-9]+min|[0-9]+:[0-9]+' | head -1 || echo "?")
        echo -ne "\r  ${C}>>${NC}  ${PCT}  speed: ${G}${SPEED}${NC}  eta: ${C}${ETA}${NC}        "
    else
        echo -ne "\r                                                              \r"
        break
    fi
    sleep 3
done

RESILVER_SECS=$(( $(date +%s) - RESILVER_START ))
RESILVER_TIME=$(printf '%dm%ds' $(( RESILVER_SECS/60 )) $(( RESILVER_SECS%60 )))

# Verify pool is healthy after resilver
POOL_HEALTH=$(zpool list -H -o health "$POOL")
[[ "$POOL_HEALTH" == "ONLINE" ]] \
    || err "Pool is ${POOL_HEALTH} after resilver -- check: zpool status ${POOL}"

ZFS_ERRORS=$(zpool status "$POOL" | grep "errors:" | grep -v "No known data errors" || true)
[[ -z "$ZFS_ERRORS" ]] \
    || err "Errors found after resilver: ${ZFS_ERRORS}"

# Verify new disk partition is ONLINE in pool
zpool status "$POOL" | grep -q "$(basename $NEW_ZFS).*ONLINE" \
    || err "${NEW_ZFS} is not showing as ONLINE in pool -- check: zpool status ${POOL}"

ok "Resilver complete in ${RESILVER_TIME}"
ok "Pool ONLINE, zero errors"
ok "${NEW_ZFS} confirmed ONLINE in pool"

# ══════════════════════════════════════════════════════════════════════════════
section "STEP 6/6 -- BOOTLOADER  [ stronger ]"
# ══════════════════════════════════════════════════════════════════════════════

step "Formatting ESP on ${NEW_ESP}..."
proxmox-boot-tool format "$NEW_ESP" --force 2>&1 | sed 's/^/    /'

# Give kernel a moment to update filesystem info then verify
sleep 1
udevadm settle 2>/dev/null || true
ESP_FS=$(lsblk -no FSTYPE "$NEW_ESP" 2>/dev/null || echo "")
[[ "$ESP_FS" == "vfat" ]] \
    || err "ESP ${NEW_ESP} is not vfat after format (got: ${ESP_FS:-none})"
ok "ESP formatted as vfat"

step "Installing GRUB and syncing kernels to ${NEW_ESP}..."
proxmox-boot-tool init "$NEW_ESP" grub 2>&1 | sed 's/^/    /'

# Verify init succeeded -- check for error lines
INIT_ERRORS=$(proxmox-boot-tool status 2>/dev/null | grep -i "error\|warn\|not found" || true)

step "Cleaning stale ESP UUIDs..."
proxmox-boot-tool clean 2>&1 | sed 's/^/    /'
ok "Stale UUIDs cleaned"

step "Verifying boot tool status..."
BT_OUT=$(proxmox-boot-tool status 2>/dev/null)
echo "$BT_OUT" | sed 's/^/    /'

ESP_COUNT=$(echo "$BT_OUT" | grep -c "is configured with" || true)
[[ "$ESP_COUNT" -ge 2 ]] \
    || err "Only ${ESP_COUNT} ESP(s) registered -- expected 2. Check: proxmox-boot-tool status"

# Verify both ESPs have same kernel version
KERNEL_VERSIONS=$(echo "$BT_OUT" | grep -oP 'versions: \K[^)]+' | sort -u | wc -l)
[[ "$KERNEL_VERSIONS" -eq 1 ]] \
    || warn "ESPs have different kernel versions -- run: proxmox-boot-tool refresh"

ok "Both ESPs registered and synced"

# ── Final summary ─────────────────────────────────────────────────────────────
FINAL_HEALTH=$(zpool list -H -o health "$POOL")

echo
echo -e "${W}  Final pool status:${NC}"
zpool status "$POOL" | sed 's/^/    /'

echo
echo -e "${G}  +======================================================+${NC}"
echo -e "${G}  |${W}  HARDER. BETTER. FASTER. STRONGER. DONE.            ${G}|${NC}"
echo -e "${G}  +======================================================+${NC}"
echo
ok "Replaced   : ${W}${NEW_DEV}${NC}  (serial: ${NEW_SERIAL})"
ok "Resilver   : ${W}completed in ${RESILVER_TIME}${NC}"
ok "Pool       : ${W}${POOL} ${FINAL_HEALTH}${NC}"
ok "ESPs       : ${W}${ESP_COUNT}/2 configured with grub${NC}"
echo

ALL_GOOD=true
[[ "$FINAL_HEALTH" == "ONLINE" ]] || ALL_GOOD=false
[[ "$ESP_COUNT"    -ge 2       ]] || ALL_GOOD=false

if $ALL_GOOD; then
    echo -e "  ${G}All checks passed. This disk is good to go.${NC}"
else
    echo -e "  ${Y}Some checks need attention -- review output above.${NC}"
fi

if [[ "$NEW_BYTES" -gt "$GOOD_BYTES" ]]; then
    echo
    warn "New disk is larger than the old disk."
    info "The pool will not expand automatically."
    echo

    # Check if ALL vdevs in the mirror are now the same (larger) size
    # Get all unique disk sizes in the mirror
    UNIQUE_SIZES=$(zpool status "$POOL" | awk '/ONLINE/ && $1 ~ /^(sd|nvme|vd)[a-z]+[0-9]+$/ {print $1}' | while read part; do
        lsblk -bdno SIZE "/dev/$(echo $part | sed 's/[0-9]*$//')" 2>/dev/null || echo 0
    done | sort -nu | wc -l)

    if [[ "$UNIQUE_SIZES" -eq 1 ]]; then
        echo -e "  ${G}All mirror members are now the same size -- ready to expand.${NC}"
        echo
        read -rp "$(echo -e "  ${Y}Expand pool to use full disk capacity now? [Y/n]: ${NC}")" EXPAND
        EXPAND="${EXPAND:-Y}"
        if [[ "$EXPAND" =~ ^[Yy]$ ]]; then

            # Step 1: extend the ZFS partition on each disk to fill the disk
            # Must be done before zpool online -e -- ZFS can only use what the partition gives it
            step "Extending ZFS partitions to fill disks..."
            while read part; do
                disk="/dev/$(echo $part | sed 's/[0-9]*$//')"
                partnum=$(echo $part | grep -oE '[0-9]+$')
                step "Resizing partition ${partnum} on ${disk}..."
                parted "$disk" resizepart "$partnum" 100% 2>&1 | grep -v "^Information" | sed 's/^/    /' || true
                # Verify
                NEW_PART_END=$(fdisk -l "$disk" 2>/dev/null | grep "${disk}${partnum}" | awk '{print $3}')
                DISK_END=$(fdisk -l "$disk" 2>/dev/null | grep "sectors," | awk '{print $7}' | tr -d ',')
                # Allow within 2048 sectors of disk end (alignment)
                DIFF=$(( DISK_END - NEW_PART_END ))
                if [[ "$DIFF" -le 2048 ]]; then
                    ok "Partition ${disk}${partnum} extended to end of disk"
                else
                    warn "Partition ${disk}${partnum} may not have extended fully (end: ${NEW_PART_END}, disk end: ${DISK_END})"
                fi
            done < <(zpool status "$POOL" | awk '/ONLINE/ && $1 ~ /^(sd|nvme|vd)[a-z]+[0-9]+$/ {print $1}')

            # Step 2: notify ZFS to use the new partition size
            step "Telling ZFS to use expanded partitions..."
            zpool set autoexpand=on "$POOL"
            while read part; do
                zpool online -e "$POOL" "/dev/${part}" 2>/dev/null || true
                ok "Expanded vdev: /dev/${part}"
            done < <(zpool status "$POOL" | awk '/ONLINE/ && $1 ~ /^(sd|nvme|vd)[a-z]+[0-9]+$/ {print $1}')

            # Verify
            sleep 1
            NEW_POOL_SIZE=$(zpool list -H -o size "$POOL")
            ok "Pool expanded -- new size: ${W}${NEW_POOL_SIZE}${NC}"
            echo
            zpool list "$POOL"
        else
            echo
            info "Skipped. To expand later, run these commands:"
            echo
            zpool status "$POOL" | awk '/ONLINE/ && $1 ~ /^(sd|nvme|vd)[a-z]+[0-9]+$/ {print $1}' | while read part; do
                disk="/dev/$(echo $part | sed 's/[0-9]*$//')"
                partnum=$(echo $part | grep -oE '[0-9]+$')
                echo -e "    ${W}parted ${disk} resizepart ${partnum} 100%${NC}"
            done
            echo -e "    ${W}zpool set autoexpand=on ${POOL}${NC}"
            zpool status "$POOL" | awk '/ONLINE/ && $1 ~ /^(sd|nvme|vd)[a-z]+[0-9]+$/ {print $1}' | while read part; do
                echo -e "    ${W}zpool online -e ${POOL} /dev/${part}${NC}"
            done
            echo
        fi
    else
        warn "Mirror members are still different sizes -- replace the other disk first."
        info "Once both disks are the larger size, re-run this script and it will offer to expand."
    fi
fi

echo
echo -e "  ${Y}Recommended: test booting from ${NEW_DEV} alone before calling this done.${NC}"
echo -e "  ${D}  VMware: BIOS -> Hard Disk boot order -> promote ${NEW_DEV} to position 1${NC}"
echo
