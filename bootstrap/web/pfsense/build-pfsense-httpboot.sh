#!/usr/bin/env bash
# build-pfsense-httpboot.sh
#
# Stages a pfSense CE 2.7.2 HTTP boot tree: loose loader/kernel files, one small root image,
# and the installer payload (base.txz + MANIFEST) served separately.
#
# Version history (append only, never delete entries):
#   0.1.0  2026-11-01  First draft. UEFI leg only. Untested.
#
# Usage (run as root so ownership and setuid bits survive extraction):
#   build-pfsense-httpboot.sh <pfSense-CE-2.7.2-RELEASE-amd64.iso> <web-root> <http-base-url>
#
# Example:
#   build-pfsense-httpboot.sh pfSense-CE-2.7.2-RELEASE-amd64.iso /srv/web http://web.example
#
# Result:
#   <web-root>/pfsense/2.7.2-CE/boot/    loader.efi, loader.conf, loader.conf.local, lua/, kernel/, root.img
#   <web-root>/pfsense/2.7.2-CE/dist/    base.txz, MANIFEST

set -euo pipefail

USAGE="usage: $0 <iso> <web-root> <http-base-url>"
ISO="${1:?${USAGE}}"
WEBROOT="${2:?${USAGE}}"
BASEURL="${3:?${USAGE}}"

NAME="pfsense/2.7.2-CE"
OUT="${WEBROOT}/${NAME}"
STAGE="$(mktemp -d)"

trap 'rm -rf -- "${STAGE:?}"' EXIT

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

chmod -R a+rX "${OUT}"

log "done. sizes:"
du -h "${OUT}/boot/root.img" "${OUT}/boot/kernel/kernel" "${OUT}/dist/base.txz"
log "test from the iPXE shell (UEFI):  chain ${BASEURL}/${NAME}/boot/loader.efi"
