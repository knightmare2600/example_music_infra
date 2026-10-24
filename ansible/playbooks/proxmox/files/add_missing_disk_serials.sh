#!/bin/bash
# =============================================================================
# add_missing_disk_serials.sh
# Example Music Limited — retrofit disk serial= onto existing VMs
# =============================================================================
# create-vm.py/create-vm-tui.py (2026-10-24) now generate a random serial= for
# every disk a NEW VM gets -- QEMU/KVM virtual disks report no serial at all by
# default, and every disk on a VM shares the same null value, which TrueNAS's own
# ZFS pool-creation validation rejects outright ("Disks have duplicate serial
# numbers: None") since it can't tell them apart. That fix only ever applies going
# forward, to disks created from that point on -- every VM built before it still has
# no serial on any disk. This script finds and fixes those, one PVE node at a time.
#
# Format matches create-vm.py exactly: secrets.token_hex(2)-secrets.token_hex(2) in
# Python is 4 lowercase hex chars, a literal hyphen, 4 more hex chars (XXXX-XXXX) --
# here via /dev/urandom + od, same shape, same alphabet.
#
# Modelled directly on enable_vm_trim_discard.sh's own conventions (same colour
# vars, same /etc/pve/qemu-server/*.conf loop, same running-vs-stopped safety split,
# same confirm-before-changing prompt) -- not a new pattern invented for this one
# script.
#
# Usage: run directly on a PVE node (needs qm, which only exists there):
#   ./add_missing_disk_serials.sh
# =============================================================================
# Changelog:
#   2026-10-24  Initial script. Robert's ask: a shell script, same shape as
#               enable_vm_trim_discard.sh, to retrofit serial= onto every disk of
#               every existing VM that doesn't already have one.
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

TMP_RUNNING="/tmp/vm_serials_running.$$"
TMP_TOFIX="/tmp/vm_serials_to_fix.$$"
trap "rm -f $TMP_RUNNING $TMP_TOFIX" EXIT
> "$TMP_RUNNING"
> "$TMP_TOFIX"

random_serial() {
    printf '%s-%s' "$(od -An -tx1 -N2 /dev/urandom | tr -d ' ')" "$(od -An -tx1 -N2 /dev/urandom | tr -d ' ')"
}

echo -e "${CYAN}=== Proxmox Disk Serial Retrofit Tool ===${NC}"
echo -e "${CYAN}Scanning all VMs for disks missing serial=...${NC}"
echo

printf "%-6s %-25s %-10s %-10s %s\n" "VMID" "VM Name" "Disk" "Serial" "Status"
printf "%s\n" "--------------------------------------------------------------------------------"

for vmconf in /etc/pve/qemu-server/*.conf; do
    [ -e "$vmconf" ] || continue

    VMID=$(basename "$vmconf" .conf)
    VMNAME=$(qm config "$VMID" 2>/dev/null | grep "^name:" | cut -d' ' -f2-)
    [ -z "$VMNAME" ] && VMNAME="<no name>"
    VMNAME_SHORT="${VMNAME:0:25}"

    VM_STATUS=$(qm status "$VMID" 2>/dev/null | awk '{print $2}')
    if [ "$VM_STATUS" == "running" ]; then
        STATUS_DISPLAY="${GREEN}running${NC}"
    else
        STATUS_DISPLAY="${CYAN}stopped${NC}"
    fi

    while IFS=: read -r disk_id disk_config; do
        # Skip CD-ROMs and cloud-init drives -- neither is a real data/boot disk,
        # neither benefits from a serial, and cloudinit specs don't take one at all.
        if echo "$disk_config" | grep -qE "media=cdrom|cloudinit"; then
            continue
        fi

        if echo "$disk_config" | grep -q "serial="; then
            SERIAL_DISPLAY="${GREEN}present${NC}"
            HAS_SERIAL=1
        else
            SERIAL_DISPLAY="${RED}missing${NC}"
            HAS_SERIAL=0
        fi

        printf "%-6s %-25s %-10s " "$VMID" "$VMNAME_SHORT" "$disk_id"
        printf "${SERIAL_DISPLAY}%*s " $((10 - ${#SERIAL_DISPLAY} + 11)) ""
        printf "${STATUS_DISPLAY}\n"

        if [ $HAS_SERIAL -eq 0 ]; then
            if [ "$VM_STATUS" == "running" ]; then
                echo "$VMID:$VMNAME:$disk_id" >> "$TMP_RUNNING"
            else
                echo "$VMID:$VMNAME:$disk_id" >> "$TMP_TOFIX"
            fi
        fi
    done < <(qm config "$VMID" 2>/dev/null | grep -E "^(scsi|sata|virtio|ide)[0-9]+:")
done

echo
echo -e "${CYAN}=== Summary ===${NC}"
echo -e "  ${GREEN}present${NC} = disk already has a serial"
echo -e "  ${RED}missing${NC} = disk has no serial (TrueNAS/ZFS pool creation would reject it)"
echo

RUNNING_COUNT=$(wc -l < "$TMP_RUNNING")
TOFIX_COUNT=$(wc -l < "$TMP_TOFIX")

if [ $RUNNING_COUNT -eq 0 ] && [ $TOFIX_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ Every disk on every VM already has a serial!${NC}"
    exit 0
fi

if [ $RUNNING_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠  WARNING: The following disks are missing a serial but their VM is currently RUNNING:${NC}"
    echo -e "${YELLOW}   These will be SKIPPED for safety -- the serial is presented to the guest at boot,${NC}"
    echo -e "${YELLOW}   so changing it live wouldn't actually reach the running guest OS anyway.${NC}"
    echo
    while IFS=':' read -r vmid vmname disk; do
        printf "${YELLOW}   • VM %-4s %-25s - %s${NC}\n" "$vmid" "$vmname" "$disk"
    done < "$TMP_RUNNING"
    echo
fi

if [ $TOFIX_COUNT -eq 0 ]; then
    echo -e "${CYAN}No stopped VMs to fix. Stop running VMs first if you want to retrofit their disks too.${NC}"
    exit 0
fi

echo -e "${CYAN}The following STOPPED VMs have disks missing a serial:${NC}"
while IFS=':' read -r vmid vmname disk; do
    printf "${CYAN}   • VM %-4s %-25s - %s${NC}\n" "$vmid" "$vmname" "$disk"
done < "$TMP_TOFIX"
echo

read -p "Add a random serial to these disks? (y/N): " -n 1 -r REPLY
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Aborted. No changes made.${NC}"
    exit 0
fi

echo
echo -e "${CYAN}Adding serials to stopped VMs' disks...${NC}"
echo

UNIQUE_VMIDS=$(cut -d':' -f1 "$TMP_TOFIX" | sort -u)

for vmid in $UNIQUE_VMIDS; do
    vmname=$(qm config "$vmid" 2>/dev/null | grep "^name:" | cut -d' ' -f2-)
    [ -z "$vmname" ] && vmname="<no name>"

    echo -e "${YELLOW}Processing VM $vmid ($vmname)...${NC}"

    VM_STATUS=$(qm status "$vmid" 2>/dev/null | awk '{print $2}')
    if [ "$VM_STATUS" == "running" ]; then
        echo -e "${RED}  ✗ VM $vmid is now running! Skipping for safety.${NC}"
        echo
        continue
    fi

    while IFS=':' read -r tvmid tvmname disk; do
        if [ "$tvmid" != "$vmid" ]; then
            continue
        fi

        DISK_LINE=$(qm config "$vmid" | grep "^${disk}:")
        DISK_SPEC=$(echo "$DISK_LINE" | sed "s/^${disk}: //")

        if [ -z "$DISK_SPEC" ]; then
            echo -e "${RED}  ✗ Could not read config for $disk${NC}"
            continue
        fi

        # Already has one (e.g. changed since the scan above) -- never overwrite a
        # real existing serial, only ever fill in a genuinely missing one.
        if echo "$DISK_SPEC" | grep -q "serial="; then
            echo -e "  ${CYAN}→ $disk already has a serial, skipping${NC}"
            continue
        fi

        NEW_SERIAL=$(random_serial)
        NEW_DISK_SPEC="${DISK_SPEC},serial=${NEW_SERIAL}"

        echo -e "  ${CYAN}→ Adding serial=${NEW_SERIAL} to $disk${NC}"
        echo -e "    ${CYAN}Old: ${NC}$DISK_SPEC"
        echo -e "    ${CYAN}New: ${NC}$NEW_DISK_SPEC"

        if qm set "$vmid" "-${disk}" "$NEW_DISK_SPEC" >/dev/null 2>&1; then
            echo -e "  ${GREEN}✓ $disk updated successfully${NC}"
        else
            echo -e "  ${RED}✗ Failed to update $disk${NC}"
        fi
    done < "$TMP_TOFIX"

    echo
done

echo -e "${CYAN}=== All Done! ===${NC}"
echo -e "${GREEN}Serials have been added to all eligible stopped VMs' disks.${NC}"
echo

if [ $RUNNING_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠  $RUNNING_COUNT disk(s) on running VMs were skipped.${NC}"
    echo -e "${YELLOW}   Stop those VMs and re-run this script to retrofit them too.${NC}"
fi

echo -e "${CYAN}Done!${NC}"
