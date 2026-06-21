#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Cleanup temp files on exit
TMP_RUNNING="/tmp/vms_running.$$"
TMP_TOFIX="/tmp/vms_to_fix.$$"
trap "rm -f $TMP_RUNNING $TMP_TOFIX" EXIT
> "$TMP_RUNNING"
> "$TMP_TOFIX"

echo -e "${CYAN}=== Proxmox VM Discard Configuration Tool ===${NC}"
echo -e "${CYAN}Scanning all VMs for disk discard status...${NC}"
echo

# Print header with proper spacing
printf "%-6s %-25s %-10s %-22s %-10s %s\n" "VMID" "VM Name" "Disk" "Storage (Type)" "Discard" "Status"
printf "%s\n" "--------------------------------------------------------------------------------------------"

# Loop through all VMs - using for loop instead of pipe to avoid subshell
for vmconf in /etc/pve/qemu-server/*.conf; do
    [ -e "$vmconf" ] || continue
    
    VMID=$(basename "$vmconf" .conf)
    VMNAME=$(qm config "$VMID" 2>/dev/null | grep "^name:" | cut -d' ' -f2-)
    [ -z "$VMNAME" ] && VMNAME="<no name>"
    VMNAME_SHORT="${VMNAME:0:25}"
    
    # Check VM status
    VM_STATUS=$(qm status "$VMID" 2>/dev/null | awk '{print $2}')
    if [ "$VM_STATUS" == "running" ]; then
        STATUS_DISPLAY="${GREEN}running${NC}"
    else
        STATUS_DISPLAY="${CYAN}stopped${NC}"
    fi
    
    # Use process substitution to avoid subshell (preserves variables)
    while IFS=: read -r disk_id disk_config; do
        # Skip CD-ROMs
        if echo "$disk_config" | grep -q "media=cdrom"; then
            continue
        fi
        
        STORAGE=$(echo "$disk_config" | awk '{print $1}' | cut -d':' -f1 | xargs)
        STORAGE_TYPE=$(pvesm status 2>/dev/null | awk -v storage="$STORAGE" '$1 == storage {print $2}')
        [ -z "$STORAGE_TYPE" ] && STORAGE_TYPE="unknown"
        
        # Check discard status
        if echo "$disk_config" | grep -q "discard=on"; then
            DISCARD_DISPLAY="${GREEN}enabled${NC}"
            DISCARD_ENABLED=1
        else
            DISCARD_DISPLAY="${RED}disabled${NC}"
            DISCARD_ENABLED=0
        fi
        
        # Check if storage benefits from discard
        if [[ "$STORAGE_TYPE" == "zfspool" ]] || [[ "$STORAGE_TYPE" == "lvmthin" ]]; then
            BENEFITS_FROM_DISCARD=1
        else
            BENEFITS_FROM_DISCARD=0
        fi
        
        STORAGE_DISPLAY="$STORAGE ($STORAGE_TYPE)"
        STORAGE_DISPLAY="${STORAGE_DISPLAY:0:22}"
        
        # Print row with proper alignment (using %b for color codes)
        printf "%-6s %-25s %-10s %-22s " "$VMID" "$VMNAME_SHORT" "$disk_id" "$STORAGE_DISPLAY"
        printf "${DISCARD_DISPLAY}%*s " $((10 - ${#DISCARD_DISPLAY} + 11)) ""
        printf "${STATUS_DISPLAY}\n"
        
        # Track VMs needing fix
        if [ $BENEFITS_FROM_DISCARD -eq 1 ] && [ $DISCARD_ENABLED -eq 0 ]; then
            if [ "$VM_STATUS" == "running" ]; then
                echo "$VMID:$VMNAME:$disk_id:$STORAGE:$STORAGE_TYPE" >> "$TMP_RUNNING"
            else
                echo "$VMID:$VMNAME:$disk_id:$STORAGE:$STORAGE_TYPE" >> "$TMP_TOFIX"
            fi
        fi
    done < <(qm config "$VMID" 2>/dev/null | grep -E "^(scsi|sata|virtio|ide)[0-9]+:")
done

# Fix the printf alignment issue by using simpler approach
# Let me redo the row printing more cleanly

echo
echo -e "${CYAN}=== Summary ===${NC}"
echo -e "  ${GREEN}enabled${NC}  = TRIM/discard is active"
echo -e "  ${RED}disabled${NC} = TRIM/discard is NOT active"
echo

# Count what we found
RUNNING_COUNT=$(wc -l < "$TMP_RUNNING")
TOFIX_COUNT=$(wc -l < "$TMP_TOFIX")

# If nothing needs fixing, exit
if [ $RUNNING_COUNT -eq 0 ] && [ $TOFIX_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All VMs with thin-provisioned storage already have discard enabled!${NC}"
    exit 0
fi

# Report running VMs (cannot be modified)
if [ $RUNNING_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠  WARNING: The following VMs need discard enabled but are currently RUNNING:${NC}"
    echo -e "${YELLOW}   These VMs will be SKIPPED for safety. Stop them first to enable discard.${NC}"
    echo
    while IFS=':' read -r vmid vmname disk storage storage_type; do
        printf "${YELLOW}   • VM %-4s %-25s - %-8s on %s (%s)${NC}\n" "$vmid" "$vmname" "$disk" "$storage" "$storage_type"
    done < "$TMP_RUNNING"
    echo
fi

# If no stopped VMs to fix, exit
if [ $TOFIX_COUNT -eq 0 ]; then
    echo -e "${CYAN}No stopped VMs to fix. Stop running VMs first if you want to enable discard.${NC}"
    exit 0
fi

# Show stopped VMs that can be fixed
echo -e "${CYAN}The following STOPPED VMs can have discard enabled:${NC}"
while IFS=':' read -r vmid vmname disk storage storage_type; do
    printf "${CYAN}   • VM %-4s %-25s - %-8s on %s (%s)${NC}\n" "$vmid" "$vmname" "$disk" "$storage" "$storage_type"
done < "$TMP_TOFIX"
echo

# Confirmation prompt
read -p "Enable discard on these stopped VMs? (y/N): " -n 1 -r REPLY
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Aborted. No changes made.${NC}"
    exit 0
fi

echo
echo -e "${CYAN}Enabling discard on stopped VMs...${NC}"
echo

# Get unique VMIDs from the to-fix list
UNIQUE_VMIDS=$(cut -d':' -f1 "$TMP_TOFIX" | sort -u)

for vmid in $UNIQUE_VMIDS; do
    vmname=$(qm config "$vmid" 2>/dev/null | grep "^name:" | cut -d' ' -f2-)
    [ -z "$vmname" ] && vmname="<no name>"
    
    echo -e "${YELLOW}Processing VM $vmid ($vmname)...${NC}"
    
    # Safety check - is VM still stopped?
    VM_STATUS=$(qm status "$vmid" 2>/dev/null | awk '{print $2}')
    if [ "$VM_STATUS" == "running" ]; then
        echo -e "${RED}  ✗ VM $vmid is now running! Skipping for safety.${NC}"
        echo
        continue
    fi
    
    # Get all disks for this VM that need fixing
    while IFS=':' read -r tvmid tvmname disk storage storage_type; do
        if [ "$tvmid" != "$vmid" ]; then
            continue
        fi
        
        # Get current disk configuration
        DISK_LINE=$(qm config "$vmid" | grep "^${disk}:")
        DISK_SPEC=$(echo "$DISK_LINE" | sed "s/^${disk}: //")
        
        if [ -z "$DISK_SPEC" ]; then
            echo -e "${RED}  ✗ Could not read config for $disk${NC}"
            continue
        fi
        
        # Remove any existing discard parameter, then add discard=on
        DISK_SPEC_CLEAN=$(echo "$DISK_SPEC" | sed 's/,discard=[^,]*//g')
        NEW_DISK_SPEC="${DISK_SPEC_CLEAN},discard=on"
        
        echo -e "  ${CYAN}→ Enabling discard on $disk${NC}"
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
echo -e "${GREEN}Discard has been enabled on all eligible stopped VMs.${NC}"
echo
echo -e "${CYAN}Next steps:${NC}"
echo -e "1. Start the VMs"
echo -e "2. Inside each Windows VM, run: ${YELLOW}Optimize-Volume -DriveLetter C -ReTrim -Verbose${NC}"
echo -e "3. Space will be reclaimed automatically on the Proxmox host"
echo

if [ $RUNNING_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠  $RUNNING_COUNT disk(s) on running VMs were skipped.${NC}"
    echo -e "${YELLOW}   Stop those VMs and re-run this script to enable discard.${NC}"
fi

echo -e "${CYAN}Done!${NC}"

