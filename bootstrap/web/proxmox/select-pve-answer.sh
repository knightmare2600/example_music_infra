#!/bin/sh
# ==============================================================================
# Example Music Limited -- select-pve-answer.sh
#
# Run this from Proxmox VE's own installer, at the root shell you land in when
# "Install Proxmox VE (Automated)" is picked with no fetch URL configured --
# that "failure" is the documented mechanism, not an error (see
# docs/bootstrap/bootstrapping.md 6.3 and docs/buildsheets/buildsheet-pve.md).
# This script exists purely to replace the manual wget step in that flow with
# something that can't pick the wrong file:
#
#   wget http://<provisioning-server>/proxmox/select-pve-answer.sh
#   sh select-pve-answer.sh
#   (follow the prompts)
#   exit
#
# That last `exit` is yours to type, deliberately -- this script never exits
# the shell on your behalf, it only gets the right file into place and tells
# you when it's safe to leave.
#
# Why this exists, in one line: an earlier attempt at fully unattended,
# zero-touch PVE installs (proxmox-auto-install-assistant prepare-iso
# --fetch-from http --pxe, BMC-mounted per-site/mode ISOs) was built,
# confirmed working in pieces, but failed its first real end-to-end boot test
# (2026-07-18 -- blank cursor, installer never picked up the mounted ISO the
# way a network-loaded one did). Given how rarely PVE nodes actually get
# built, scripting the ALREADY-DOCUMENTED manual wget step -- with an operator
# physically present at the console anyway -- is simpler and doesn't depend on
# an unconfirmed BMC/init-script interaction at all. See
# docs/proxmox/pxe-proxmox-autoinstall-build-log.md for the full history,
# including the abandoned approach.
#
# Written in POSIX sh, not bash -- this runs inside Proxmox's installer
# environment (BusyBox ash), which does not have bash. Deliberately avoids
# bash-only syntax (arrays, [[ ]], ${var:offset:length} substring extraction,
# `local`) in favour of portable constructs (case, cut, awk, printf) that are
# real BusyBox applets. Gateway/disk detection logic below was tested directly
# against a real `busybox ash` interpreter and real /proc/net/route,
# /sys/block content before being handed over -- not just reasoned about --
# but the actual wget fetch against a real Proxmox installer environment has
# NOT been tested live yet. Confirm that part on the next real boot.
#
# Version History
# ---------------
# 1.0.0   2026-07-19   Initial release
# ==============================================================================

# No `set -e` -- this is an interactive script meant to recover from a wrong
# guess (wrong gateway match, wrong disk count) via prompts, not abort on the
# first unexpected condition the way a fire-and-forget script should.

RD='\033[0;31m'
GN='\033[0;32m'
YW='\033[1;33m'
CY='\033[0;36m'
NC='\033[0m'

msg_info()  { printf "${CY}[*]${NC} %s\n" "$1"; }
msg_ok()    { printf "${GN}[+]${NC} %s\n" "$1"; }
msg_warn()  { printf "${YW}[!]${NC} %s\n" "$1"; }
msg_error() { printf "${RD}[x]${NC} %s\n" "$1"; }

printf "${CY}==============================================================${NC}\n"
printf "${CY} Example Music Limited -- Proxmox VE answer-file selector${NC}\n"
printf "${CY}==============================================================${NC}\n"
printf "\n"

# ------------------------------------------------------------------------------
# Detect the default gateway straight from /proc/net/route -- no dependency on
# `ip`/`route` being present or configured a particular way, just the kernel's
# own routing table, which always exists. The Gateway field is 8 hex chars,
# little-endian byte order (reversed vs a normal dotted-quad reading order).
# ------------------------------------------------------------------------------
detect_gateway() {
  gw_hex=$(awk '$2 == "00000000" {print $3; exit}' /proc/net/route 2>/dev/null)
  if [ -z "$gw_hex" ]; then
    return 1
  fi
  b1=$(printf '%d' "0x$(echo "$gw_hex" | cut -c7-8)")
  b2=$(printf '%d' "0x$(echo "$gw_hex" | cut -c5-6)")
  b3=$(printf '%d' "0x$(echo "$gw_hex" | cut -c3-4)")
  b4=$(printf '%d' "0x$(echo "$gw_hex" | cut -c1-2)")
  echo "$b1.$b2.$b3.$b4"
}

gateway=$(detect_gateway)

# Matches menu.ipxe's own gateway-detection iseq blocks exactly -- same two
# provisioning environments, same reasoning (see menu.ipxe's own comment block).
site_prefix=""
boot_url=""
if [ "$gateway" = "192.168.139.254" ]; then
  site_prefix="VRK"
  boot_url="http://192.168.139.50"
  msg_ok "Detected gateway ${gateway} -- Edinburgh (192.168.139.50)"
elif [ "$gateway" = "172.16.124.2" ]; then
  site_prefix="FRD"
  boot_url="http://172.16.124.1:8000"
  msg_ok "Detected gateway ${gateway} -- Fredericia Havn (172.16.124.1)"
else
  msg_warn "Gateway '${gateway:-<none detected>}' doesn't match a known provisioning network."
  printf "Enter site prefix manually [VRK/FRD]: "
  read -r manual_prefix
  case "$manual_prefix" in
    [Vv][Rr][Kk])
      site_prefix="VRK"
      boot_url="http://192.168.139.50"
      ;;
    [Ff][Rr][Dd])
      site_prefix="FRD"
      boot_url="http://172.16.124.1:8000"
      ;;
    *)
      msg_error "Unrecognised prefix '${manual_prefix}'. Aborting -- re-run once you know which provisioning network this is."
      exit 1
      ;;
  esac
fi

# ------------------------------------------------------------------------------
# Disk count, via /sys/block directly -- no lsblk/fdisk dependency. Excludes
# loopback, ramdisk, optical (sr*), floppy (fd*), AND device-mapper/LVM
# volumes (dm-*) -- the last one caught live testing this against a real
# busybox ash on a dev box that happens to run its own root on LVM: without
# the dm-* exclusion, a single physical disk (sda) counted as 3 (sda plus two
# dm-N logical volumes on top of it). A server being rebuilt with leftover
# LVM signatures on its physical disks would hit exactly the same
# overcounting bug if this weren't excluded. sr* also matters for a different
# reason in the real scenario this script runs in: the BMC-mounted Proxmox
# ISO itself shows up as a sr* optical device and must never be counted.
# ------------------------------------------------------------------------------
disk_count=0
disk_list=""
for d in /sys/block/*; do
  [ -e "$d" ] || continue
  name=$(basename "$d")
  case "$name" in
    loop*|ram*|sr*|fd*|dm-*) continue ;;
  esac
  disk_count=$((disk_count + 1))
  disk_list="${disk_list}${disk_list:+, }${name}"
done

printf "\n"
msg_info "Detected ${disk_count} disk(s): ${disk_list:-none}"

if [ "$disk_count" -ge 2 ]; then
  suggested="answer"
  msg_info "2+ disks detected -- suggesting the standard build (2-disk ZFS mirror)."
else
  suggested="degraded"
  msg_warn "Fewer than 2 disks detected -- suggesting the degraded build (single-disk, NOT production ready)."
fi

printf "\nUse the [%s] build? Press Enter to accept, or type 'answer' / 'degraded' to override: " "$suggested"
read -r variant_input
case "$variant_input" in
  "")
    variant="$suggested"
    ;;
  [Aa][Nn][Ss][Ww][Ee][Rr])
    variant="answer"
    ;;
  [Dd][Ee][Gg][Rr][Aa][Dd][Ee][Dd])
    variant="degraded"
    ;;
  *)
    msg_error "Unrecognised input '${variant_input}'. Aborting -- re-run and answer with Enter, 'answer', or 'degraded'."
    exit 1
    ;;
esac

toml_file="${site_prefix}-${variant}.toml"
toml_url="${boot_url}/proxmox/${toml_file}"
target="/run/automatic-installer-answers"

printf "\n"
msg_info "Fetching ${toml_url}"

if [ -f "$target" ]; then
  msg_warn "${target} already exists."
  printf "Overwrite it? [y/N]: "
  read -r overwrite_answer
  case "$overwrite_answer" in
    [Yy]*) : ;;
    *)
      msg_error "Aborted -- ${target} left untouched."
      exit 1
      ;;
  esac
fi

if ! wget -O "$target" "$toml_url"; then
  msg_error "wget failed fetching ${toml_url} -- check network/URL and try again."
  exit 1
fi

# ------------------------------------------------------------------------------
# Sanity check: a wrong URL can still return HTTP 200 with an HTML error page
# body (wget itself won't catch that -- it's still a "successful" transfer as
# far as wget is concerned). A non-empty file starting with a real TOML
# section header is a cheap, real guard against silently installing with
# garbage in /run/automatic-installer-answers.
# ------------------------------------------------------------------------------
if [ ! -s "$target" ]; then
  msg_error "${target} is empty after fetch -- something is wrong. Not safe to continue."
  rm -f "$target"
  exit 1
fi

if ! grep -q '^\[global\]' "$target"; then
  msg_error "${target} doesn't look like a real answer file (no [global] section found)."
  msg_error "First line fetched: $(head -n1 "$target")"
  msg_error "Not safe to continue -- check the URL above and try again."
  # Removed rather than left in place -- if this error scrolls past and the
  # operator types `exit` anyway without reading it, the installer must find
  # nothing at $target (dropping back to its own no-answer-file path) rather
  # than silently picking up whatever garbage got fetched here.
  rm -f "$target"
  exit 1
fi

msg_ok "${toml_file} fetched and verified at ${target} ($(wc -c < "$target") bytes)."
printf "\n"
printf "${GN}Ready. Type ${NC}exit${GN} now to hand back to the Proxmox installer.${NC}\n"
