#!/usr/bin/env bash
# build-pfsense-httpboot.sh
#
# Stages a pfSense CE 2.7.2 HTTP boot tree: loose loader/kernel files, one small root image,
# and the installer payload (base.txz + MANIFEST) served separately.
#
# Version history (append only, never delete entries):
#   0.1.0  2026-11-01  First draft. UEFI leg only. Untested.
#   0.2.0  2026-11-01  Build a small bootable boot.iso (the boot/ tree only, dist/ excluded)
#                       and sanboot that, instead of chain-ing loader.efi as a single bare
#                       HTTP file. Live-tested reasoning: chain gives loader.efi no filesystem
#                       of its own, so it can never find /boot/lua/loader.lua -- confirmed live,
#                       "Failed to find bootable partition". sanboot-ing the full vendor ISO
#                       directly was also tried and rejected: the kernel's cd9660 auto-mount
#                       (the real ISO's own loader.conf expects /dev/iso9660/PFSENSE) only
#                       engages for a device BIOS/the kernel sees as CD-ROM type, and iPXE's
#                       SAN layer presents an HTTP-backed image as a plain disk regardless of
#                       --drive range chosen (confirmed live: lsdev -v showed disk0, not cd0,
#                       even at --drive 0xe0, the conventional first-CD-ROM BIOS drive number).
#                       root.img via rootimg_load/md_image sidesteps this entirely -- md(4)
#                       never goes through BIOS/EDD device typing at all. UEFI leg only, still
#                       untested end to end (this fixes the earlier failure mode, not yet
#                       confirmed to reach a working install).
#
# Usage (run as root so ownership and setuid bits survive extraction):
#   build-pfsense-httpboot.sh <pfSense-CE-2.7.2-RELEASE-amd64.iso> <web-root> <http-base-url>
#
# Example:
#   build-pfsense-httpboot.sh pfSense-CE-2.7.2-RELEASE-amd64.iso /srv/web http://web.example
#
# Result:
#   <web-root>/pfsense/2.7.2-CE/boot.iso  sanboot this -- loader.efi, lua/, kernel/, root.img,
#                                         no dist/ (installer payload stays HTTP-fetched)
#   <web-root>/pfsense/2.7.2-CE/boot/    same content, unpacked (kept for reference/manual poking)
#   <web-root>/pfsense/2.7.2-CE/dist/    base.txz, MANIFEST

set -euo pipefail

USAGE="usage: $0 <iso> <web-root> <http-base-url>"
ISO="${1:?${USAGE}}"
WEBROOT="${2:?${USAGE}}"
BASEURL="${3:?${USAGE}}"

NAME="pfsense/2.7.2-CE"
OUT="${WEBROOT}/${NAME}"
STAGE="$(mktemp -d)"
BOOTISO_STAGE="$(mktemp -d)"

trap 'rm -rf -- "${STAGE:?}" "${BOOTISO_STAGE:?}"' EXIT

log() {
  printf '%s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

[ "$(id -u)" -eq 0 ] || die "run as root so ownership and setuid bits are preserved"
[ -f "${ISO}" ] || die "ISO not found: ${ISO}"
[ -e "${OUT}" ] && die "${OUT} already exists, refusing to touch it"

for tool in bsdtar xorriso; do
  command -v "${tool}" > /dev/null || die "missing tool: ${tool}"
done

log "checking the ISO has the paths this script presumes"
bsdtar -tf "${ISO}" | grep -qx 'usr/freebsd-dist/base.txz' || die "usr/freebsd-dist/base.txz not found in ISO listing"
bsdtar -tf "${ISO}" | grep -qx 'boot/loader.efi' || die "boot/loader.efi not found in ISO listing"

mkdir -p "${OUT}/boot/kernel" "${OUT}/dist"

log "extracting the ISO without base.txz (Rock Ridge names are honoured by bsdtar)"
bsdtar -xpf "${ISO}" -C "${STAGE}" --exclude 'usr/freebsd-dist/base.txz'

log "extracting the installer payload"
bsdtar -xOf "${ISO}" usr/freebsd-dist/base.txz > "${OUT}/dist/base.txz"
bsdtar -xOf "${ISO}" usr/freebsd-dist/MANIFEST > "${OUT}/dist/MANIFEST"

log "copying the loose files the UEFI loader fetches over HTTP"
cp -a "${STAGE}/boot/loader.efi" "${STAGE}/boot/loader.conf" "${STAGE}/boot/device.hints" "${OUT}/boot/"
cp -a "${STAGE}/boot/defaults" "${STAGE}/boot/lua" "${OUT}/boot/"
for f in kernel linker.hints zfs.ko opensolaris.ko; do
  cp -a "${STAGE}/boot/kernel/${f}" "${OUT}/boot/kernel/"
done

log "writing boot/loader.conf.local"
cat > "${OUT}/boot/loader.conf.local" <<'EOF'
# pfsense-httpboot 0.1.0 (UEFI). Read after loader.conf, so these override it.
boot_serial="YES"
boot_multicons="YES"
console="efi,comconsole"
comconsole_speed="115200"
hw.uart.console="io:0x3f8,br:115200"
rootimg_load="YES"
rootimg_type="md_image"
rootimg_name="/boot/root.img"
vfs.root.mountfrom="cd9660:/dev/md0"
vfs.root.mountfrom.options="ro"
EOF

log "pointing the installer at the HTTP dist directory (appended, existing lines untouched)"
for profile in "${STAGE}/.profile" "${STAGE}/root/.profile"; do
  if [ -f "${profile}" ]; then
    cat >> "${profile}" <<EOF

# --- pfsense-httpboot 0.1.0: fetch distribution files over HTTP ---
export BSDINSTALL_DISTDIR=/tmp/dist
export BSDINSTALL_DISTSITE=${BASEURL}/${NAME}/dist/
EOF
  fi
done

log "building the root image (cd9660, label PFSENSE, Rock Ridge)"
xorriso -as mkisofs -R -V PFSENSE -o "${OUT}/boot/root.img" "${STAGE}"

log "building the sanboot image (boot/ tree only, dist/ excluded -- this way loader.efi finds"
log "its own /boot/* on the device it was booted from, unlike chaining a single bare HTTP file)"
xorriso -as mkisofs -R -V PFSENSE-BOOT -o "${BOOTISO_STAGE}/boot.iso" \
  -e boot/loader.efi -no-emul-boot -m dist "${OUT}"
mv "${BOOTISO_STAGE}/boot.iso" "${OUT}/boot.iso"

chmod -R a+rX "${OUT}"

log "done. sizes:"
du -h "${OUT}/boot.iso" "${OUT}/boot/root.img" "${OUT}/boot/kernel/kernel" "${OUT}/dist/base.txz"
log "test from the iPXE shell:  sanboot --no-describe ${BASEURL}/${NAME}/boot.iso"
