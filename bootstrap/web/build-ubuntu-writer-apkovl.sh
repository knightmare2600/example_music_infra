#!/bin/sh
# ===========================================================================
# build-ubuntu-writer-apkovl.sh
# Example Music Limited
#
# Builds ubuntu-writer.apkovl.tar.gz for serving at:
#   http://192.168.139.50/alpine/ubuntu-writer.apkovl.tar.gz
#
# Run this once on any Linux machine. Copy the resulting .tar.gz to your
# provisioning server. Requires: tar, mkdir, chmod (all standard).
#
# What the apkovl contains:
#   /etc/apk/world                   -- tells Alpine to install wget on boot
#   /etc/apk/repositories            -- pinned to Alpine v3.23
#   /etc/keymap/                     -- GB keymap config
#   /etc/local.d/00-keymap.start     -- sets GB keyboard before writer runs
#   /etc/local.d/write-ubuntu.start  -- dd-writer script
#   /etc/runlevels/default/local     -- symlink enabling the local service
#
# The write-ubuntu.start script:
#   1. Mounts the modloop (already done by initramfs) and runs depmod -a
#      against the running kernel to index the .ko.gz files already present.
#      This avoids apk add linux-virt which triggers mkinitfs and fails with
#      "no space left on device" in a diskless RAM environment.
#   2. Loads disk drivers for VMware and Proxmox
#   3. Detects the largest block device dynamically (minimum 8 GB safety check)
#   4. wget-pipes the Ubuntu minimal .img directly into dd (never fully
#      buffered -- streamed straight through to disk)
#   5. Grows the last partition to fill the disk
#   6. Reboots into the written Ubuntu image
#
# Netboot files must come from Alpine v3.23 release:
#   https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/x86_64/netboot/
#   https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/aarch64/netboot/
# Files needed: vmlinuz-virt, initramfs-virt, modloop-virt
#
# Ref -- apkovl format:
#   https://wiki.alpinelinux.org/wiki/Alpine_local_backup
# Ref -- /etc/local.d/ scripts:
#   https://wiki.alpinelinux.org/wiki/Local_runscripts
# Ref -- Alpine PXE boot:
#   https://wiki.alpinelinux.org/wiki/PXE_boot
# Ref -- depmod man page:
#   https://linux.die.net/man/8/depmod
#
# Version history:
#   v1.3 -- Replace apk add linux-virt with depmod -a against already-present
#            modloop .ko.gz files. apk add triggers mkinitfs which fails with
#            no space left on device in a diskless RAM environment.
#            Add GB keymap via /etc/local.d/00-keymap.start (runs before
#            write-ubuntu.start due to lexical ordering).
#            Fix rm -rf of WORK dir to unlink symlink first before removing,
#            avoiding silent rm -rf of symlink target.
#            Note iPXE entry uses vmlinuz-lts not vmlinuz-virt per operator
#            preference -- lts netboot files also from v3.23/releases/.
#   v1.2 -- Pin Alpine repo to v3.23 in apkovl repositories file.
#   v1.1 -- Add explicit modprobe for VMware and Proxmox disk drivers.
#   v1.0 -- Initial release
# ===========================================================================

set -e

WORK=$(mktemp -d)
OUT="ubuntu-writer.apkovl.tar.gz"

echo "[*] Building apkovl in ${WORK}"

# ---------------------------------------------------------------------------
# /etc/apk/world
# ---------------------------------------------------------------------------
mkdir -p "${WORK}/etc/apk"
cat > "${WORK}/etc/apk/world" <<'EOF'
alpine-base
wget
EOF

# ---------------------------------------------------------------------------
# /etc/apk/repositories -- pinned to v3.23
# ---------------------------------------------------------------------------
cat > "${WORK}/etc/apk/repositories" <<'EOF'
https://dl-cdn.alpinelinux.org/alpine/v3.23/main
https://dl-cdn.alpinelinux.org/alpine/v3.23/community
EOF

# ---------------------------------------------------------------------------
# /etc/local.d/00-keymap.start -- GB keyboard
# Prefixed 00- so it runs before write-ubuntu.start (lexical order).
# setup-keymap is part of alpine-setup-scripts, present in alpine-base.
# Ref: https://wiki.alpinelinux.org/wiki/Keyboard_layout
# ---------------------------------------------------------------------------
mkdir -p "${WORK}/etc/local.d"
cat > "${WORK}/etc/local.d/00-keymap.start" <<'EOF'
#!/bin/sh
setup-keymap gb gb
EOF
chmod 755 "${WORK}/etc/local.d/00-keymap.start"

# ---------------------------------------------------------------------------
# /etc/local.d/write-ubuntu.start
# ---------------------------------------------------------------------------
cat > "${WORK}/etc/local.d/write-ubuntu.start" <<'SCRIPT'
#!/bin/sh
# Ubuntu minimal cloud image writer
# Runs once at Alpine boot, writes Ubuntu to disk, reboots.

BOOT_SERVER="http://192.168.139.50"
LOG="/var/log/write-ubuntu.log"

exec > "${LOG}" 2>&1
echo "=== Ubuntu image writer starting ==="
date

# -- Index kernel modules ---------------------------------------------------
# The modloop is already mounted by the initramfs at /lib/modules.
# We run depmod -a to build the module dependency index against the .ko.gz
# files already present -- no apk install needed, no disk writes beyond tmpfs.
#
# We do NOT use apk add linux-virt here. That triggers mkinitfs which tries
# to write a new initramfs to disk and fails with ENOSPC in a diskless RAM
# environment (tmpfs fills up at ~94% with just the base system).
#
# Ref: https://linux.die.net/man/8/depmod
KVER=$(uname -r)
echo "Running depmod for ${KVER}..."
depmod -a "${KVER}"

# -- Load disk controller drivers -------------------------------------------
# VMware Workstation / Fusion : mptspi (LSI Logic emulated SCSI)
# Proxmox virtio-scsi         : virtio_scsi
# Proxmox virtio-blk          : virtio_blk
# Proxmox/VMware IDE fallback : ata_piix
echo "Loading disk controller modules..."
modprobe mptspi      2>/dev/null || true
modprobe virtio_scsi 2>/dev/null || true
modprobe virtio_blk  2>/dev/null || true
modprobe ata_piix    2>/dev/null || true

# Give udev a moment to create block device nodes after module load
sleep 2
echo "Block devices visible after module load:"
ls /sys/class/block/

# -- Detect arch ------------------------------------------------------------
ARCH=$(uname -m)
case "${ARCH}" in
  aarch64) IMG_ARCH="arm64" ;;
  *)       IMG_ARCH="amd64" ;;
esac
IMG_URL="${BOOT_SERVER}/ubuntu/ubuntu-24.04-minimal-cloudimg-${IMG_ARCH}.img"
echo "Architecture: ${ARCH} -> image: ${IMG_URL}"

# -- Detect target disk -----------------------------------------------------
# Find all block devices, exclude ram/loop/sr/fd, pick largest by sectors.
TARGET=""
LARGEST=0

for DEV in /sys/class/block/*/; do
  NAME=$(basename "${DEV}")
  case "${NAME}" in
    ram*|loop*|sr*|fd*) continue ;;
  esac
  [ -f "${DEV}/partition" ] && continue
  SIZE=$(cat "${DEV}/size" 2>/dev/null || echo 0)
  if [ "${SIZE}" -gt "${LARGEST}" ]; then
    LARGEST="${SIZE}"
    TARGET="${NAME}"
  fi
done

if [ -z "${TARGET}" ]; then
  echo "ERROR: No suitable target disk found. Dropping to shell."
  exit 1
fi

TARGET_DEV="/dev/${TARGET}"
TARGET_GB=$(( LARGEST * 512 / 1024 / 1024 / 1024 ))
echo "Target disk: ${TARGET_DEV} (${TARGET_GB} GB)"

# -- Safety check -----------------------------------------------------------
if [ "${TARGET_GB}" -lt 8 ]; then
  echo "ERROR: ${TARGET_DEV} is only ${TARGET_GB} GB -- too small, refusing."
  exit 1
fi

# -- Write image ------------------------------------------------------------
echo "Streaming ${IMG_URL} -> ${TARGET_DEV} ..."
wget -O - "${IMG_URL}" | dd of="${TARGET_DEV}" bs=4M conv=fsync status=progress
echo "Write complete."

# -- Resize partition to fill disk ------------------------------------------
apk add --quiet e2fsprogs parted
parted -s "${TARGET_DEV}" resizepart 1 100%
LAST_PART=$(ls "${TARGET_DEV}"* 2>/dev/null | grep -E "${TARGET}p?[0-9]+$" | sort -V | tail -1)
if [ -n "${LAST_PART}" ]; then
  echo "Resizing filesystem on ${LAST_PART}..."
  e2fsck -f -y "${LAST_PART}" || true
  resize2fs "${LAST_PART}"
fi

echo "=== Done. Rebooting into Ubuntu in 3 seconds ==="
sleep 3
reboot
SCRIPT

chmod 755 "${WORK}/etc/local.d/write-ubuntu.start"

# ---------------------------------------------------------------------------
# /etc/runlevels/default/local -- enable the local service
# ---------------------------------------------------------------------------
mkdir -p "${WORK}/etc/runlevels/default"
ln -s /etc/init.d/local "${WORK}/etc/runlevels/default/local"

# ---------------------------------------------------------------------------
# Pack the tarball
# ---------------------------------------------------------------------------
echo "[*] Packing ${OUT}"
tar -czf "${OUT}" \
  --owner=root --group=root \
  -C "${WORK}" \
  etc

# ---------------------------------------------------------------------------
# Cleanup -- unlink the symlink explicitly before rm -rf to avoid rm
# following it and deleting the symlink target (/etc/init.d/local on the
# build machine). rm -rf does not follow symlinks on Linux but unlink is
# belt-and-braces correct practice.
# ---------------------------------------------------------------------------
unlink "${WORK}/etc/runlevels/default/local"
rm -rf "${WORK}"

echo "[+] Done: ${OUT}"
echo "    Copy to your provisioning server:"
echo "    scp ${OUT} user@192.168.139.50:/var/www/html/alpine/"
