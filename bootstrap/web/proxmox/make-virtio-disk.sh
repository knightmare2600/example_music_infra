#!/usr/bin/env bash
# =============================================================================
# make-virtio-disk.sh — Build VirtIO driver disk image for Windows VMs
# Example Music Limited — Internal Infrastructure
#
# Extracts VirtIO drivers from virtio-win-gt-x64.msi and builds a small
# FAT32 raw disk image with the drivers laid out in the folder structure
# that drvload.exe expects inside PhoenixPE:
#
#   vioscsi/<osver>/amd64/vioscsi.inf   (+ .sys, .cat)
#   NetKVM/<osver>/amd64/netkvm.inf     (+ .sys, .cat)
#   etc.
#
# The MSI uses a flat naming convention:
#   FILE_<driver>_<osver>_<arch>.<ext>
# This script reconstructs the expected folder structure from those names.
#
# Usage:
#   ./make-virtio-disk.sh <virtio-win-gt-x64.msi> <output.img>
#
# Example:
#   ./make-virtio-disk.sh virtio-win-gt-x64.msi virtio-drivers.img
#
# Requirements:
#   apt install 7zip dosfstools mtools
#   (7zip provides /usr/bin/7za)
#
# Changelog:
#   2026-03-03  Initial script — MSI extraction via 7za, FAT32 image creation,
#               driver folder tree reconstruction from flat MSI naming
#   2026-03-03  Switched from ISO-based to MSI-based source
#   2026-03-03  LoadVirtIO.cmd added to image — auto drive detection,
#               OS version menu, errorlevel checking
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Colour output
# -----------------------------------------------------------------------------
R=$'\033[0;31m'; G=$'\033[0;32m'; Y=$'\033[1;33m'
CY=$'\033[0;36m'; W=$'\033[1;37m'; NC=$'\033[0m'

step()  { echo -e "${CY}  [*]${NC} $*"; }
ok()    { echo -e "${G}  [+]${NC} $*"; }
warn()  { echo -e "${Y}  [!]${NC} $*"; }
err()   { echo -e "${R}  [!]${NC} $*"; exit 1; }

# -----------------------------------------------------------------------------
# Arguments
# -----------------------------------------------------------------------------
if [[ $# -ne 2 ]]; then
    echo
    echo "  Usage: $0 <virtio-win-gt-x64.msi> <output.img>"
    echo
    echo "  Example:"
    echo "    $0 virtio-win-gt-x64.msi virtio-drivers.img"
    echo
    echo "  Requirements:"
    echo "    apt install 7zip dosfstools mtools"
    echo
    exit 1
fi

MSI="$1"
OUT="$2"
IMG_SIZE_MB=128
IMG_LABEL="VIRTIO"

# Drivers we care about:
# Key   = prefix as it appears in FILE_<key>_<osver>_<arch>.<ext>
# Value = folder name drvload expects on the disk image
declare -A DRIVER_MAP=(
    ["vioscsi"]="vioscsi"
    ["netkvm"]="NetKVM"
    ["balloon"]="Balloon"
    ["vioser"]="vioserial"
    ["vioinput"]="vioinput"
    ["pvpanic"]="pvpanic"
)

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
echo
echo -e "${CY}  +======================================================+${NC}"
echo -e "${CY}  |${W}  VirtIO Driver Disk Builder                         ${CY}|${NC}"
echo -e "${CY}  |${NC}  Example Music Limited                              ${CY}|${NC}"
echo -e "${CY}  +======================================================+${NC}"
echo

# -----------------------------------------------------------------------------
# Preflight checks
# -----------------------------------------------------------------------------
[[ ! -f "$MSI" ]] && err "MSI not found: $MSI"
[[ -f "$OUT" ]]   && warn "Output file already exists and will be overwritten: $OUT"

for cmd in 7za mkfs.fat mount umount dd; do
    command -v "$cmd" &>/dev/null || err "Required command not found: $cmd  (apt install 7zip dosfstools mtools)"
done

if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (needed for mount). Try: sudo $0 $*"
fi

# -----------------------------------------------------------------------------
# Temp dirs — cleaned up on exit
# -----------------------------------------------------------------------------
EXTRACT_DIR=$(mktemp -d /tmp/virtio-msi.XXXXXX)
MNT_IMG=$(mktemp -d /tmp/virtio-img.XXXXXX)

cleanup() {
    local exit_code=$?
    umount "$MNT_IMG"     2>/dev/null || true
    rm -rf "$EXTRACT_DIR" 2>/dev/null || true
    rmdir  "$MNT_IMG"     2>/dev/null || true
    if [[ $exit_code -ne 0 ]]; then
        echo
        warn "Build failed — removing partial output."
        rm -f "$OUT"
    fi
}
trap cleanup EXIT

# -----------------------------------------------------------------------------
# Extract MSI with 7za
# -----------------------------------------------------------------------------
step "Extracting MSI: $(basename "$MSI")"
7za x "$MSI" -o"$EXTRACT_DIR" -y > /dev/null
ok "Extracted to temp dir"

# Sanity check
ls "$EXTRACT_DIR"/FILE_vioscsi_* &>/dev/null \
    || err "No vioscsi files found after extraction — is this the virtio-win-gt-x64.msi?"

extracted_count=$(find "$EXTRACT_DIR" -name "FILE_*" | wc -l)
ok "$extracted_count driver files found in MSI"

# -----------------------------------------------------------------------------
# Create raw image
# -----------------------------------------------------------------------------
step "Creating ${IMG_SIZE_MB}MB FAT32 image: $OUT"
dd if=/dev/zero of="$OUT" bs=1M count="$IMG_SIZE_MB" status=none
mkfs.fat -F 32 -n "$IMG_LABEL" "$OUT" > /dev/null
ok "Image created and formatted"

# -----------------------------------------------------------------------------
# Mount image
# -----------------------------------------------------------------------------
step "Mounting image"
mount -o loop "$OUT" "$MNT_IMG"
ok "Mounted"

# -----------------------------------------------------------------------------
# Reconstruct folder structure and copy drivers
#
# MSI flat:   FILE_<driver>_<osver>_<arch>.<ext>
# Target:     <Driver>/<osver>/amd64/<driver>.<ext>
#
# Files without an extension (DLLs/EXEs stored without one) are skipped —
# they are not INF/SYS/CAT files and are not needed for drvload.
# Only amd64 files are processed.
# -----------------------------------------------------------------------------
step "Reconstructing driver folder structure..."
echo

copied_total=0

for msi_prefix in "${!DRIVER_MAP[@]}"; do
    folder_name="${DRIVER_MAP[$msi_prefix]}"
    driver_count=0

    while IFS= read -r filepath; do
        filename=$(basename "$filepath")

        # Strip FILE_ prefix and driver name prefix to get: <osver>_<arch>.<ext>
        remainder="${filename#FILE_${msi_prefix}_}"

        osver=$(echo "$remainder" | cut -d_ -f1)
        arch_ext=$(echo "$remainder" | cut -d_ -f2)

        # Skip extensionless files
        [[ "$arch_ext" != *.* ]] && continue

        arch=$(echo "$arch_ext" | cut -d. -f1)
        ext="${arch_ext##*.}"

        # amd64 only
        [[ "$arch" != "amd64" ]] && continue

        target_dir="$MNT_IMG/$folder_name/$osver/amd64"
        mkdir -p "$target_dir"
        cp "$filepath" "$target_dir/${msi_prefix}.${ext}"
        (( driver_count++ )) || true
        (( copied_total++ )) || true

    done < <(find "$EXTRACT_DIR" -maxdepth 1 -name "FILE_${msi_prefix}_*" | sort)

    if [[ $driver_count -gt 0 ]]; then
        os_versions=$(find "$MNT_IMG/$folder_name" -mindepth 1 -maxdepth 1 -type d \
                      | xargs -I{} basename {} | sort | tr '\n' ' ')
        ok "$folder_name — $driver_count files  [${os_versions% }]"
    else
        warn "$folder_name — no files found"
    fi

done

echo

# -----------------------------------------------------------------------------
# Write LoadVirtIO.cmd onto the image
# -----------------------------------------------------------------------------
cat > "$MNT_IMG/LoadVirtIO.cmd" << 'EOF'
:: =============================================================================
::
::  ██╗      ██████╗  █████╗ ██████╗ ██╗   ██╗██╗██████╗ ████████╗██╗ ██████╗
::  ██║     ██╔═══██╗██╔══██╗██╔══██╗██║   ██║██║██╔══██╗╚══██╔══╝██║██╔═══██╗
::  ██║     ██║   ██║███████║██║  ██║██║   ██║██║██████╔╝   ██║   ██║██║   ██║
::  ██║     ██║   ██║██╔══██║██║  ██║╚██╗ ██╔╝██║██╔══██╗   ██║   ██║██║   ██║
::  ███████╗╚██████╔╝██║  ██║██████╔╝ ╚████╔╝ ██║██║  ██║   ██║   ██║╚██████╔╝
::  ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝   ╚═══╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝ ╚═════╝
::
::  LoadVirtIO.cmd — VirtIO Driver Loader for PhoenixPE
::  Example Music Limited — Internal Infrastructure
::
::  Loads VirtIO SCSI and NIC drivers into the running WinPE environment
::  so the QEMU virtual disk and network become visible before Windows
::  installation begins.
::
::  Run this FIRST before attempting to access the disk or network.
::  The script detects its own drive letter automatically.
::
::  Changelog:
::    2026-03-03  Initial script — auto drive detection, OS version menu,
::                vioscsi + NetKVM drvload with errorlevel checking
:: =============================================================================
@echo off

:: Work out which drive this script is running from
set DRVDRV=%~d0

echo.
echo   +======================================================+
echo   ^|  VirtIO Driver Loader — Example Music Limited       ^|
echo   +======================================================+
echo.
echo   Driver disk detected at: %DRVDRV%
echo.

:: -----------------------------------------------------------------------------
:: Select OS version
:: -----------------------------------------------------------------------------
echo   Select the Windows version being INSTALLED (not this PE):
echo.
echo     1  ^>  Windows 10
echo     2  ^>  Windows 11
echo     3  ^>  Windows Server 2016
echo     4  ^>  Windows Server 2019
echo     5  ^>  Windows Server 2022
echo     6  ^>  Windows Server 2025
echo.
set /p OSSEL="  Enter number [5]: "
if "%OSSEL%"==""  set OSSEL=5
if "%OSSEL%"=="1" set OSVER=w10
if "%OSSEL%"=="2" set OSVER=w11
if "%OSSEL%"=="3" set OSVER=2k16
if "%OSSEL%"=="4" set OSVER=2k19
if "%OSSEL%"=="5" set OSVER=2k22
if "%OSSEL%"=="6" set OSVER=2k25

if not defined OSVER (
    echo   [!] Invalid selection. Defaulting to 2k22.
    set OSVER=2k22
)

echo.
echo   OS version: %OSVER%
echo.

:: -----------------------------------------------------------------------------
:: Load VirtIO SCSI — disk becomes visible after this
:: -----------------------------------------------------------------------------
echo   [*] Loading VirtIO SCSI controller...
drvload %DRVDRV%\vioscsi\%OSVER%\amd64\vioscsi.inf
if errorlevel 1 (
    echo   [!] vioscsi failed^^! Check OSVER folder exists on %DRVDRV%
    echo   [!] Expected: %DRVDRV%\vioscsi\%OSVER%\amd64\vioscsi.inf
    pause
    exit /b 1
)
echo   [+] VirtIO SCSI loaded — OS disk should now be visible in diskpart

echo.

:: -----------------------------------------------------------------------------
:: Load NetKVM NIC — network becomes available after this
:: -----------------------------------------------------------------------------
echo   [*] Loading NetKVM NIC driver...
drvload %DRVDRV%\NetKVM\%OSVER%\amd64\netkvm.inf
if errorlevel 1 (
    echo   [!] NetKVM failed^^! Check OSVER folder exists on %DRVDRV%
    echo   [!] Expected: %DRVDRV%\NetKVM\%OSVER%\amd64\netkvm.inf
    pause
    exit /b 1
)
echo   [+] NetKVM loaded — network adapter now available

echo.
echo   +======================================================+
echo   ^|  [+] VirtIO drivers loaded successfully              ^|
echo   ^|                                                      ^|
echo   ^|  Next steps:                                         ^|
echo   ^|    1. Run diskpart to verify disk is visible         ^|
echo   ^|    2. Configure network / map installer share        ^|
echo   ^|    3. Launch Windows Setup                           ^|
echo   +======================================================+
echo.
EOF

ok "LoadVirtIO.cmd written"

# -----------------------------------------------------------------------------
# Write README onto the image
# -----------------------------------------------------------------------------
cat > "$MNT_IMG/README.TXT" << 'EOF'
VirtIO Driver Disk — Example Music Limited
==========================================

QUICK START
-----------
Run LoadVirtIO.cmd from this drive. It will:
  1. Ask which Windows version you are installing
  2. Load the VirtIO SCSI driver  (disk becomes visible)
  3. Load the NetKVM NIC driver   (network becomes available)

CONTENTS
--------
LoadVirtIO.cmd  Run this first in PhoenixPE
vioscsi\        VirtIO SCSI controller
NetKVM\         VirtIO NIC
Balloon\        Memory balloon          (not needed in WinPE)
vioserial\      VirtIO serial           (not needed in WinPE)
vioinput\       VirtIO input devices    (not needed in WinPE)
pvpanic\        QEMU pvpanic            (not needed in WinPE)

OS VERSION FOLDERS
------------------
  w10  = Windows 10       w11  = Windows 11
  2k16 = Server 2016      2k19 = Server 2019
  2k22 = Server 2022      2k25 = Server 2025
EOF

ok "README.TXT written"

# -----------------------------------------------------------------------------
# Unmount and disarm trap
# -----------------------------------------------------------------------------
step "Unmounting..."
umount "$MNT_IMG"
rmdir  "$MNT_IMG"
rm -rf "$EXTRACT_DIR"
trap - EXIT

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
img_size=$(du -sh "$OUT" | cut -f1)
echo
echo -e "${G}  +======================================================+${NC}"
echo -e "${G}  |${W}  Build complete                                      ${G}|${NC}"
echo -e "${G}  +======================================================+${NC}"
echo
ok "Output  : $OUT  ($img_size)"
ok "Files   : $copied_total driver files copied"
echo
echo -e "  ${W}Deploy to Proxmox:${NC}"
echo -e "    ${CY}scp $OUT root@192.168.139.50:/var/lib/vz/template/iso/${NC}"
echo
