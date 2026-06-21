#!/bin/bash
# =============================================================================
# first-boot.sh — Proxmox VE Node Provisioning
# Example Music Limited — Internal Infrastructure
#
# Run manually as root after first boot:
#   bash /var/lib/proxmox-first-boot/proxmox-first-boot
#
# Changelog:
#   2026-03-01  Initial script — node provisioning, site lookup tables, ansible user, SSH keys, subscription nag removal
#   2026-03-01  Added CLD site (192.168.139.0/24 provisioning network)
#   2026-03-01  Added Let's Encrypt reminder to summary output
#   2026-03-03  BRD renamed to BER (West Berlin) in all lookup tables
#   2026-03-03  TOR (Toronto) added — octet 146 — all lookup tables
#   2026-03-07  virt-v2v Windows V2V prerequisites added (Step 3b): virtio-win ISO download, pvvxsvc.exe extraction into
#               /usr/share/virt-tools/ — required for Windows guest conversion. Absence of this file causes virt-v2v to
#               abort with "rhsrvany.exe or pvvxsvc.exe is missing" before it even touches the disk, regardless of NTFS
#               volume state.
#   2026-03-22  Steps 3b+3c wrapped in optional V2V prompt (default Y).
#               Step 3e added -- sites.csv download + mkdir -p (default Y).
#               Step 3f added -- BIOS ROM files from prov server (default Y).
#               Step 3g added -- provisioning scripts to /usr/local/bin/ (default Y).
#               Step 3h added -- /etc/profile.d/example-music.sh for PATH.
#               Symlinks into /usr/local/bin removed (profile.d is the correct approach).
#               Ansible and root zshrc both source profile.d for PATH + SITES_CSV.
#               Summary rewritten: proper column alignment, BMC token reprinted.
#   2026-03-19  proxmoxbmc optional install added (Step 3d) -- installs proxmoxbmc via pip, creates API token, enables
#               systemd service.
#   2026-03-19  Site data moved to sites.csv (single source of truth). Place sites.csv alongside this script or set
#               SITES_CSV=
#   2026-03-07  VirtIO drivers ISO added (Step 3c): downloads virtio-win.iso to /var/lib/vz/template/iso/ (for CDROM
#               attachment to VMs) AND extracts it to /usr/share/virtio-win/ so virt-v2v can auto-inject vioscsi/
#               NetKVM/balloon drivers during Windows V2V conversion. Without extraction, virt-v2v falls back to the
#               emulated IDE/RTL8139 and converted VMs risk INACCESSIBLE_BOOT_DEVICE. Extraction uses p7zip-full (apt).
# =============================================================================
set -e

# ── Colours ───────────────────────────────────────────────────────────────────
R='\033[0;31m'
G='\033[0;32m'
Y='\033[1;33m'
C='\033[0;36m'
M='\033[0;35m'
W='\033[1;37m'
D='\033[2;37m'
NC='\033[0m'

ok()      { echo -e "  ${G}[+]${NC} $1"; }
info()    { echo -e "  ${C}[i]${NC} $1"; }
warn()    { echo -e "  ${Y}[!]${NC} $1"; }
err()     { echo -e "  ${R}[X]${NC} $1"; exit 1; }
step()    { echo -e "  ${M}[->]${NC} $1"; }
section() {
    echo
    echo -e "${Y}  ================================================${NC}"
    echo -e "${W}  $1${NC}"
    echo -e "${Y}  ================================================${NC}"
    echo
}
# ---------------------------------------------------------------
# Site data -- loaded from sites.csv (single source of truth)
# To add or change a site, edit sites.csv -- no code changes needed.
#
# Looks for sites.csv in:
#   1. $SITES_CSV environment variable (override)
#   2. Same directory as this script
#   3. /etc/example-music/sites.csv (system-wide install)
# ---------------------------------------------------------------
declare -A SITE_OCTET SITE_CITY SITE_COUNTRY SITE_ENTITY

load_sites_csv() {
  local csv_path=""

  if [[ -n "${SITES_CSV:-}" && -f "${SITES_CSV}" ]]; then
    csv_path="${SITES_CSV}"
  else
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "${script_dir}/sites.csv" ]]; then
      csv_path="${script_dir}/sites.csv"
    elif [[ -f "/etc/example-music/sites.csv" ]]; then
      csv_path="/etc/example-music/sites.csv"
    fi
  fi

  if [[ -z "${csv_path}" ]]; then
    echo -e "\033[0;31m[ERROR]\033[0m sites.csv not found." >&2
    echo -e "  Looked in: same directory as script, /etc/example-music/sites.csv" >&2
    echo -e "  Set SITES_CSV=/path/to/sites.csv to override." >&2
    exit 1
  fi

  local first=1
  while IFS=',' read -r site city country cc subnet gateway dc fw landline mobile tz ansible_region entity _rest; do
    [[ "${first}" -eq 1 ]] && { first=0; continue; }   # skip header row
    site="${site// /}"
    [[ -z "${site}" ]] && continue
    local octet
    octet=$(echo "${subnet}" | awk -F'.' '{print $3}')
    SITE_OCTET["${site}"]="${octet}"
    SITE_CITY["${site}"]="${city}"
    SITE_COUNTRY["${site}"]="${country}"
    SITE_ENTITY["${site}"]="${entity}"
  done < "${csv_path}"
}

load_sites_csv

# ── IP collision detection ────────────────────────────────────────────────────
ip_in_use() {
  local ip="$1"
  if ping -c1 -W1 "$ip" &>/dev/null 2>&1; then
    return 0
  fi
  if command -v arping &>/dev/null; then
    local gw_iface
    gw_iface=$(ip route | awk '/default/{print $5}' | head -1)
    if arping -c1 -W1 -I "$gw_iface" "$ip" &>/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

suggest_ip() {
  local subnet="$1"
  for octet in $(seq 5 10); do
    local candidate="${subnet}.${octet}"
    if ! ip_in_use "$candidate"; then
      echo "$candidate"
      return 0
    fi
  done
  echo ""
}

# ── Header ────────────────────────────────────────────────────────────────────
clear
echo
echo -e "${C}  +======================================================+${NC}"
echo -e "${C}  |${W}        PROXMOX VE - NODE PROVISIONING                ${C}|${NC}"
echo -e "${C}  |${D}              jukebox.internal                         ${C}|${NC}"
echo -e "${C}  +======================================================+${NC}"
echo

# ── Step 1: Fix repos BEFORE anything touches apt ────────────────────────────
section "FIXING APT REPOSITORIES"

step "Disabling Proxmox enterprise repos (require paid subscription)..."

# Handle legacy .list format
for f in /etc/apt/sources.list.d/pve-enterprise.list /etc/apt/sources.list.d/ceph.list; do
  if [ -f "$f" ]; then
    sed -i 's|^deb |#deb |g' "$f"
    ok "Disabled: $(basename $f)"
  fi
done

# Handle DEB822 .sources format (PVE 9)
for f in /etc/apt/sources.list.d/pve-enterprise.sources /etc/apt/sources.list.d/ceph.sources; do
  if [ -f "$f" ]; then
    mv "$f" "${f}.disabled"
    ok "Disabled: $(basename $f) -> $(basename $f).disabled"
  fi
done

step "Adding Proxmox no-subscription community repo..."
cat > /etc/apt/sources.list.d/pve-no-subscription.list <<REPOEOF
# Proxmox VE no-subscription repository - added by provisioning script
deb http://download.proxmox.com/debian/pve trixie pve-no-subscription
REPOEOF
ok "No-subscription repo added"

step "Running apt update..."
apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true
ok "Repositories updated"

# ── Step 1b: Remove subscription nag ─────────────────────────────────────────
section "REMOVING SUBSCRIPTION NAG"

PVE_JS="/usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js"
if [[ -f "$PVE_JS" ]]; then
  if grep -q 'Ext.Msg.show({' "$PVE_JS"; then
    step "Patching proxmoxlib.js..."
    cp "${PVE_JS}" "${PVE_JS}.bak"
    sed -i 's/Ext.Msg.show({/void({/g' "$PVE_JS"
    ok "Subscription nag removed"
    ok "Backup saved: ${PVE_JS}.bak"
    step "Restarting pveproxy..."
    systemctl restart pveproxy
    ok "pveproxy restarted -- hard-refresh browser (Ctrl+Shift+R)"
    warn "Note: this patch will be re-applied automatically on each run of this script."
    warn "If an apt upgrade restores the nag, re-run: bash /var/lib/proxmox-first-boot/proxmox-first-boot"
  else
    info "proxmoxlib.js already patched -- skipping"
  fi
else
  warn "proxmoxlib.js not found at expected path -- skipping nag removal"
fi

# ── Step 2: Gather node configuration ────────────────────────────────────────
section "NODE CONFIGURATION"

echo -e "  ${W}Known site codes:${NC}"
echo -e "  ${C}  $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort | tr '\n' ' ')${NC}"
echo

SITE_CODE=""
SUBNET=""
SITE_CITY_VAL=""
SITE_COUNTRY_VAL=""
SITE_ENTITY_VAL=""

while true; do
  read -rp "$(echo -e "  ${W}Site code${NC} (e.g. FAL, MCR, GLA): ")" SITE_INPUT
  SITE_CODE="${SITE_INPUT^^}"
  if [[ -v "SITE_OCTET[$SITE_CODE]" ]]; then
    OCTET="${SITE_OCTET[$SITE_CODE]}"
    SUBNET="192.168.${OCTET}"
    SITE_CITY_VAL="${SITE_CITY[$SITE_CODE]:-$SITE_CODE}"
    SITE_COUNTRY_VAL="${SITE_COUNTRY[$SITE_CODE]:-Unknown}"
    SITE_ENTITY_VAL="${SITE_ENTITY[$SITE_CODE]:-Example Music}"
    ok "Site   : ${SITE_CODE} -- ${SITE_CITY_VAL}, ${SITE_COUNTRY_VAL}"
    ok "Entity : ${SITE_ENTITY_VAL}"
    ok "Subnet : ${SUBNET}.0/24"
    break
  else
    warn "Unknown site code '${SITE_CODE}' -- see list above."
  fi
done

# Hostname
while true; do
  read -rp "$(echo -e "  ${W}Hostname${NC} (short, e.g. EXA${SITE_CODE}PVE001): ")" HOSTNAME
  [[ -n "$HOSTNAME" ]] && break
  warn "Hostname cannot be empty."
done

# Gateway
while true; do
  # CLD uses .1 as gateway -- hardcoded, not prompted
  if [[ "$SITE_CODE" == "CLD" ]]; then
    GATEWAY="${SUBNET}.1"
    ok "Gateway: ${GATEWAY} (provisioning network -- hardcoded to .1)"
    break
  fi
  read -rp "$(echo -e "  ${W}Gateway last octet${NC} (e.g. 253 -> ${SUBNET}.253): ")" GW_OCTET
  if [[ "$GW_OCTET" =~ ^[0-9]{1,3}$ ]] && [[ "$GW_OCTET" -ge 1 ]] && [[ "$GW_OCTET" -le 254 ]]; then
    GATEWAY="${SUBNET}.${GW_OCTET}"
    ok "Gateway: ${GATEWAY}"
    break
  fi
  warn "Enter a number between 1 and 254."
done

# IP -- scan .5-.10, suggest first free, block collisions
echo
step "Scanning ${SUBNET}.5-10 for available IPs..."
SUGGESTED_IP=$(suggest_ip "$SUBNET")

if [[ -n "$SUGGESTED_IP" ]]; then
  ok "Suggested: ${W}${SUGGESTED_IP}${NC} (first free in .5-.10 range)"
else
  warn "All IPs in .5-.10 appear to be in use -- enter one manually"
  SUGGESTED_IP="${SUBNET}.5"
fi

NODE_IP=""
while true; do
  read -rp "$(echo -e "  ${W}IP Address${NC} [${SUGGESTED_IP}]: ")" NODE_IP_INPUT
  NODE_IP="${NODE_IP_INPUT:-$SUGGESTED_IP}"

  if [[ ! "$NODE_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    warn "Invalid IP address format."
    continue
  fi

  step "Checking ${NODE_IP} is not already in use..."
  if ip_in_use "$NODE_IP"; then
    warn "${NODE_IP} is already responding on the network -- choose another."
    echo -e "  ${C}  Availability of ${SUBNET}.5-10:${NC}"
    for octet in $(seq 5 10); do
      cand="${SUBNET}.${octet}"
      if ip_in_use "$cand"; then
        echo -e "  ${R}    ${cand}  IN USE${NC}"
      else
        echo -e "  ${G}    ${cand}  free${NC}"
      fi
    done
    continue
  fi
  ok "${NODE_IP} is free"
  break
done

FQDN="${HOSTNAME}.jukebox.internal"

echo
info "Hostname : ${W}${FQDN}${NC}"
info "IP       : ${W}${NODE_IP}/24${NC}"
info "Gateway  : ${W}${GATEWAY}${NC}"
info "Site     : ${W}${SITE_CODE} -- ${SITE_CITY_VAL}, ${SITE_COUNTRY_VAL}${NC}"
info "Entity   : ${W}${SITE_ENTITY_VAL}${NC}"
echo
read -rp "$(echo -e "  ${Y}Proceed with these settings? [y/N]: ${NC}")" CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || err "Aborted by user."

# ── Step 3: Install packages ──────────────────────────────────────────────────
section "INSTALLING PACKAGES"

step "Installing core packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server sudo net-tools bash-completion tree bc molly-guard arping nmap parted gdisk smartmontools vim zsh grc python3-proxmoxer python3-textual python3-requests python3-pbr python3-six w3m xxd 2>&1 | \
grep -E "^(Setting up|Unpacking)" | sed 's/^/    /'
ok "Core packages installed"
ok "molly-guard active -- protects against accidental reboots/shutdowns"

# VMware tools -- only install if running inside a VMware VM
step "Checking hypervisor type..."
VIRT_TYPE=$(systemd-detect-virt 2>/dev/null || echo "unknown")
info "Detected virtualisation: ${VIRT_TYPE}"
if [[ "$VIRT_TYPE" == "vmware" ]]; then
  step "VMware VM detected -- installing open-vm-tools..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y open-vm-tools 2>&1 | grep -E "^(Setting up|Unpacking)" | sed 's/^/    /'
  systemctl enable --now open-vm-tools 2>/dev/null || true
  ok "open-vm-tools installed and enabled"
else
  info "Not a VMware VM (${VIRT_TYPE}) -- skipping open-vm-tools"
fi

# ── Step 3b+3c: virt-v2v Windows V2V prerequisites and VirtIO drivers ────────
section "VIRT-V2V / WINDOWS CONVERSION TOOLS (OPTIONAL)"

echo -e "  ${C}virt-v2v converts VMware/Hyper-V VMs to Proxmox.${NC}"
echo -e "  ${C}This step installs:${NC}"
echo -e "  ${C}  - pvvxsvc.exe / rhsrvany.exe  (required for Windows guest conversion)${NC}"
echo -e "  ${C}  - VirtIO drivers ISO + extraction  (prevents BSOD on converted Windows VMs)${NC}"
echo -e "  ${D}  Skip only if this node will never run virt-v2v conversions.${NC}"
echo
INSTALL_V2V=true
read -rp "$(echo -e "  ${Y}Set up virt-v2v / Windows conversion tools? [Y/n]: ${NC}")" V2V_INPUT
if [[ "${V2V_INPUT,,}" == "n" || "${V2V_INPUT,,}" == "no" ]]; then
  INSTALL_V2V=false
  info "Skipping virt-v2v setup."
fi

if [[ "${INSTALL_V2V}" == "true" ]]; then

section "VIRT-V2V WINDOWS CONVERSION PREREQUISITES"

# Background: virt-v2v requires pvvxsvc.exe (or rhsrvany.exe) in
# /usr/share/virt-tools/ to inject Windows firstboot scripts during
# conversion. Without these files, virt-v2v aborts immediately with:
#
#   "One of rhsrvany.exe or pvvxsvc.exe is missing in /usr/share/virt-tools"
#
# This error fires BEFORE virt-v2v mounts the guest disk -- NTFS dirty/clean
# state is completely irrelevant. The files are not in any Proxmox/Debian repo.
#
# The virtio-win ISO does NOT contain these files despite what the docs imply.
#
# Verified working method: extract from the Fedora mingw32-srvany RPM using
# rpm2cpio + cpio (both available in Debian repos, no RPM runtime needed).
# Source RPM: https://kojipkgs.fedoraproject.org//packages/mingw-srvany/1.1/4.fc38/noarch/

V2V_TOOLS_DIR="/usr/share/virt-tools"
SRVANY_RPM="/tmp/srvany.rpm"
SRVANY_URL="https://kojipkgs.fedoraproject.org//packages/mingw-srvany/1.1/4.fc38/noarch/mingw32-srvany-1.1-4.fc38.noarch.rpm"

step "Checking for existing virt-tools exes..."
if [[ -f "${V2V_TOOLS_DIR}/pvvxsvc.exe" ]] || [[ -f "${V2V_TOOLS_DIR}/rhsrvany.exe" ]]; then
  ok "virt-tools exes already present in ${V2V_TOOLS_DIR}/ -- skipping"
  ls -lh "${V2V_TOOLS_DIR}/"*.exe 2>/dev/null | sed 's/^/    /'
else
  warn "No helper exes found in ${V2V_TOOLS_DIR}/"
  warn "Windows V2V conversion will fail without them."
  echo
  step "Installing rpm2cpio and cpio (needed to extract from RPM without RPM runtime)..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y rpm2cpio cpio 2>&1 | grep -E "^(Setting up|Unpacking)" | sed 's/^/    /'
  ok "rpm2cpio + cpio installed"

  step "Downloading mingw32-srvany RPM from Fedora Koji..."
  step "  URL: ${SRVANY_URL}"
  if wget -q -O "${SRVANY_RPM}" "${SRVANY_URL}"; then
    RPM_SIZE=$(du -sh "${SRVANY_RPM}" 2>/dev/null | cut -f1)
    ok "Downloaded srvany.rpm (${RPM_SIZE})"
  else
    warn "Download failed -- check network connectivity"
    warn "Manual fix after provisioning:"
    warn "  apt install -y rpm2cpio cpio"
    warn "  wget -O /tmp/srvany.rpm '${SRVANY_URL}'"
    warn "  cd /tmp && rpm2cpio /tmp/srvany.rpm | cpio -idmv"
    warn "  mkdir -p ${V2V_TOOLS_DIR}"
    warn "  mv /tmp/usr/i686-w64-mingw32/sys-root/mingw/bin/*.exe ${V2V_TOOLS_DIR}/"
    warn "Windows V2V conversion will fail until this is resolved."
  fi

  if [[ -f "${SRVANY_RPM}" ]] && [[ -s "${SRVANY_RPM}" ]]; then
    step "Extracting exes from RPM (rpm2cpio | cpio)..."
    EXTRACT_DIR=$(mktemp -d /tmp/srvany-extract.XXXXXX)
    pushd "${EXTRACT_DIR}" > /dev/null
    rpm2cpio "${SRVANY_RPM}" | cpio -idmv 2>&1 | grep '\.exe' | sed 's/^/    /'
    popd > /dev/null

    step "Installing exes to ${V2V_TOOLS_DIR}/..."
    mkdir -p "${V2V_TOOLS_DIR}"
    EXE_COUNT=0
    while IFS= read -r -d '' exe; do
      cp "${exe}" "${V2V_TOOLS_DIR}/"
      ok "Installed: $(basename ${exe}) → ${V2V_TOOLS_DIR}/"
      (( EXE_COUNT++ )) || true
      done < <(find "${EXTRACT_DIR}/usr/i686-w64-mingw32/sys-root/mingw/bin/" -name "*.exe" -print0 2>/dev/null)

      if [[ "${EXE_COUNT}" -eq 0 ]]; then
        warn "No .exe files found at expected path in extracted RPM"
        warn "Contents of extract dir:"
        find "${EXTRACT_DIR}" -name "*.exe" 2>/dev/null | sed 's/^/    /' || true
      fi

      step "Cleaning up..."
      rm -rf "${EXTRACT_DIR}" "${SRVANY_RPM}"
      ok "Temporary files removed"
    fi

    # Final status
    echo
    if [[ -f "${V2V_TOOLS_DIR}/rhsrvany.exe" ]] || [[ -f "${V2V_TOOLS_DIR}/pvvxsvc.exe" ]]; then
      ok "Windows V2V prerequisites ready:"
      ls -lh "${V2V_TOOLS_DIR}/"*.exe 2>/dev/null | sed 's/^/    /'
    else
      warn "Windows V2V NOT ready -- no .exe files in ${V2V_TOOLS_DIR}/"
      warn "virt-v2v will refuse to convert Windows guests until this is resolved."
    fi
fi

step "Verifying virt-v2v install..."
if command -v virt-v2v &>/dev/null; then
  V2V_VER=$(virt-v2v --version 2>&1 | head -1)
  ok "virt-v2v: ${V2V_VER}"
else
  info "virt-v2v not installed on this node -- install when needed:"
  info "  apt install virt-v2v libguestfs-tools"
fi

# ── Step 3c: VirtIO drivers ISO -- extract for virt-v2v auto-injection ────────
section "VIRTIO DRIVERS ISO (virt-v2v driver injection)"

# Background: virt-v2v can automatically inject VirtIO drivers (vioscsi,
# NetKVM, balloon, etc.) into Windows guests during conversion IF the drivers
# are present at /usr/share/virtio-win/ as extracted files.
#
# Why this matters vs just attaching the ISO as a CDROM:
#   - When the extracted drivers ARE present, virt-v2v injects them into the
#     Windows registry during conversion. The guest boots directly with VirtIO
#     storage and NIC -- no INACCESSIBLE_BOOT_DEVICE, no driver installation
#     needed post-boot, no Secure Boot dance.
#   - When they are NOT present, virt-v2v falls back to emulated IDE/RTL8139
#     and you must inject drivers yourself (offline DISM from recovery console,
#     or online install after boot with Secure Boot / driver signing disabled).
#
# The VirtIO ISO is also kept as an ISO at /var/lib/vz/template/iso/ so it
# can be attached as a CDROM drive to any Windows VM via Proxmox UI or the
# create-vm.py / convert-v2v.py scripts -- useful for new VM builds and as
# a fallback for manual driver install if the virt-v2v injection fails.
#
# Extraction uses p7zip -- the ISO contains directories per driver/arch/OS
# that virt-v2v scans at conversion time. No repackaging needed.

VIRTIO_ISO_URL="https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso"
VIRTIO_ISO_DEST="/var/lib/vz/template/iso/virtio-win.iso"
VIRTIO_EXTRACT_DIR="/usr/share/virtio-win"

step "Checking for existing VirtIO driver extraction..."
VIRTIO_READY=false
if [[ -d "${VIRTIO_EXTRACT_DIR}" ]] && [[ -d "${VIRTIO_EXTRACT_DIR}/vioscsi" ]]; then
  ok "VirtIO drivers already extracted at ${VIRTIO_EXTRACT_DIR}/ -- skipping download"
  DRIVER_COUNT=$(find "${VIRTIO_EXTRACT_DIR}" -name "*.inf" 2>/dev/null | wc -l)
  ok "  ${DRIVER_COUNT} driver .inf files present"
  VIRTIO_READY=true
else
  warn "VirtIO drivers not extracted -- Windows V2V conversion will use slow emulated devices"
  warn "and may hit INACCESSIBLE_BOOT_DEVICE without manual driver injection post-conversion."
  echo
  step "Installing p7zip (needed to extract VirtIO ISO)..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y p7zip-full 2>&1 | grep -E "^(Setting up|Unpacking)" | sed 's/^/    /'
  ok "p7zip-full installed"

  # Download ISO if not already present
  if [[ -f "${VIRTIO_ISO_DEST}" ]] && [[ -s "${VIRTIO_ISO_DEST}" ]]; then
    ISO_SIZE=$(du -sh "${VIRTIO_ISO_DEST}" | cut -f1)
    ok "VirtIO ISO already present: ${VIRTIO_ISO_DEST} (${ISO_SIZE})"
  else
    step "Downloading VirtIO ISO (~500MB) from Fedora..."
    step "  URL: ${VIRTIO_ISO_URL}"
    step "  Dest: ${VIRTIO_ISO_DEST}"
    mkdir -p /var/lib/vz/template/iso
    if wget -q --show-progress -O "${VIRTIO_ISO_DEST}" "${VIRTIO_ISO_URL}" 2>&1; then
      ISO_SIZE=$(du -sh "${VIRTIO_ISO_DEST}" | cut -f1)
      ok "Downloaded virtio-win.iso (${ISO_SIZE})"
    else
      warn "Download failed -- check network connectivity"
      warn "Manual fix after provisioning:"
      warn "  mkdir -p /var/lib/vz/template/iso"
      warn "  wget -O ${VIRTIO_ISO_DEST} '${VIRTIO_ISO_URL}'"
      warn "  mkdir -p ${VIRTIO_EXTRACT_DIR}"
      warn "  7z x ${VIRTIO_ISO_DEST} -o${VIRTIO_EXTRACT_DIR}"
      warn "VirtIO driver injection will not work until this is resolved."
    fi
  fi

  # Extract if ISO is present
  if [[ -f "${VIRTIO_ISO_DEST}" ]] && [[ -s "${VIRTIO_ISO_DEST}" ]]; then
    step "Extracting VirtIO ISO to ${VIRTIO_EXTRACT_DIR}/ ..."
    step "  (virt-v2v scans this directory tree at conversion time)"
    mkdir -p "${VIRTIO_EXTRACT_DIR}"
    if 7z x "${VIRTIO_ISO_DEST}" -o"${VIRTIO_EXTRACT_DIR}" -y 2>&1 | grep -E "^(Extracting|Error)" | sed 's/^/    /' ; then
      DRIVER_COUNT=$(find "${VIRTIO_EXTRACT_DIR}" -name "*.inf" 2>/dev/null | wc -l)
      ok "Extraction complete -- ${DRIVER_COUNT} driver .inf files"
      ok "Key drivers present:"
      for drv in vioscsi NetKVM balloon viostor qemufwcfg; do
      if [[ -d "${VIRTIO_EXTRACT_DIR}/${drv}" ]]; then
        ok "  ${drv}"
      else
        warn "  ${drv} -- NOT FOUND (may be under a different name)"
      fi
        done
        VIRTIO_READY=true
      else
        warn "Extraction failed or incomplete"
        warn "Run manually: 7z x ${VIRTIO_ISO_DEST} -o${VIRTIO_EXTRACT_DIR}"
    fi
  fi
fi

# ISO also needs to be in the template store for CDROM attachment
if [[ ! -f "${VIRTIO_ISO_DEST}" ]]; then
  warn "VirtIO ISO not present at ${VIRTIO_ISO_DEST}"
  warn "Windows VMs created via create-vm.py will not be offered a VirtIO CDROM."
  warn "Download it manually: wget -O ${VIRTIO_ISO_DEST} '${VIRTIO_ISO_URL}'"
else
  ok "VirtIO ISO available for CDROM attachment: ${VIRTIO_ISO_DEST}"
fi

echo
if [[ "${VIRTIO_READY}" == "true" ]]; then
  ok "virt-v2v will auto-inject VirtIO drivers into Windows guests during conversion."
  ok "Windows VMs should boot directly with VirtIO storage + NIC -- no manual driver"
  ok "install needed unless virt-v2v reports drivers not found at conversion time."
else
  warn "VirtIO driver extraction incomplete -- see warnings above."
  warn "Without extracted drivers, converted Windows VMs will:"
  warn "  - Boot with slow emulated IDE disk and RTL8139 NIC"
  warn "  - Require manual driver injection before switching to VirtIO"
  warn "  - Risk INACCESSIBLE_BOOT_DEVICE if scsi controller is changed before drivers"
fi

# ── Step 3d: proxmoxbmc (optional) ──────────────────────────────────────────
section "PROXMOXBMC SETUP (OPTIONAL)"

echo -e "  ${C}proxmoxbmc gives each VM with BMC emulation a real IPMI endpoint${NC}"
echo -e "  ${C}over the network. Technicians can use ipmitool for power control,${NC}"
echo -e "  ${C}boot device selection, and SOL serial console.${NC}"
echo -e "  ${D}See: proxmoxbmc-setup.md for full usage instructions${NC}"
echo

INSTALL_PROXMOXBMC=false
read -rp "$(echo -e "  ${Y}Install proxmoxbmc? [y/N]: ${NC}")" PBMC_INPUT
if [[ "${PBMC_INPUT,,}" == "y" || "${PBMC_INPUT,,}" == "yes" ]]; then
  INSTALL_PROXMOXBMC=true
fi

PBMC_API_TOKEN_NAME=""
PBMC_API_TOKEN_VALUE=""

if [[ "${INSTALL_PROXMOXBMC}" == "true" ]]; then
  step "Installing proxmoxbmc dependencies..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y --quiet     python3-proxmoxer python3-pyghmi python3-cliff     python3-zmq python3-pbr python3-requests 2>&1 |     grep -E "^(Setting up|already)" | sed 's/^/    /' || true
  ok "proxmoxbmc apt dependencies installed"

  step "Fetching proxmoxbmc .deb from provisioning server..."
  PBMC_DEB_URL="${PROV_PKG_PATH}/python3-proxmoxbmc_1.0.1-2_all.deb"
  PBMC_DEB_TMP="/tmp/python3-proxmoxbmc.deb"
  if wget -q -O "${PBMC_DEB_TMP}" "${PBMC_DEB_URL}"; then
    ok "Downloaded: ${PBMC_DEB_URL}"
    step "Installing proxmoxbmc .deb..."
    dpkg -i "${PBMC_DEB_TMP}" 2>&1 | sed 's/^/    /'
    rm -f "${PBMC_DEB_TMP}"
    ok "proxmoxbmc installed from .deb (no pip, no venv)"
  else
    warn "Could not fetch .deb from ${PBMC_DEB_URL}"
    warn "Install manually: wget -O /tmp/proxmoxbmc.deb ${PBMC_DEB_URL} && dpkg -i /tmp/proxmoxbmc.deb"
    INSTALL_PROXMOXBMC=false
  fi

  # ── Create Proxmox API token for proxmoxbmc ──────────────────────────────
  step "Creating Proxmox API token for proxmoxbmc..."
  # Token is created without privilege separation (proxmoxbmc needs full access)
  TOKEN_OUTPUT=$(pveum user token add root@pam proxmoxbmc --privsep=0 --output-format=json 2>/dev/null || true)
  if [[ -n "${TOKEN_OUTPUT}" ]]; then
    PBMC_API_TOKEN_NAME="proxmoxbmc"
    PBMC_API_TOKEN_VALUE=$(echo "${TOKEN_OUTPUT}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('value',''))" 2>/dev/null || echo "")
    if [[ -n "${PBMC_API_TOKEN_VALUE}" ]]; then
      ok "API token created: root@pam!proxmoxbmc"
      warn "Token value (save this -- shown only once):"
      echo -e "  ${W}${PBMC_API_TOKEN_VALUE}${NC}"
    else
      warn "Could not parse token value from pveum output -- create manually:"
      warn "  pveum user token add root@pam proxmoxbmc --privsep=0"
    fi
  else
    warn "pveum token creation failed (token may already exist)"
    warn "If the token exists, retrieve its value from Datacenter -> Permissions -> API Tokens"
  fi

  # ── Ensure service is enabled and running ───────────────────────────────
  # The .deb postinst enables and starts the service automatically.
  # We explicitly enable+restart here to cover: already-installed deb,
  # failed postinst, or service not yet started.
  step "Enabling and starting proxmoxbmc service..."
  systemctl daemon-reload
  systemctl enable proxmoxbmc
  systemctl restart proxmoxbmc
  sleep 2
  if systemctl is-active --quiet proxmoxbmc; then
    ok "proxmoxbmc service running"
  else
    warn "proxmoxbmc service failed to start -- check: journalctl -u proxmoxbmc"
  fi

  # ── Port convention reminder ──────────────────────────────────────────────
  echo
  info "Port convention: 6000 + VMID (e.g. VMID 1021 -> port 7021)"
  info "To register a VM after creation:"
  info "  pbmc add --username admin --password <bmc-pass> --port \$((6000 + VMID))"
  info "    --proxmox-address ${NODE_IP} --token-user root@pam"
  if [[ -n "${PBMC_API_TOKEN_VALUE}" ]]; then
    info "    --token-name proxmoxbmc --token-value ${PBMC_API_TOKEN_VALUE} <VMID>"
  else
    info "    --token-name proxmoxbmc --token-value <token-value> <VMID>"
  fi
  info "  pbmc start <VMID>"
  info "See proxmoxbmc-setup.md for ipmitool usage and SOL console setup"
else
  info "Skipping proxmoxbmc installation"
fi

fi  # end INSTALL_V2V

# ── Step 3e: sites.csv placement ─────────────────────────────────────────────
section "SITES.CSV PLACEMENT"

echo -e "  ${C}sites.csv is the single source of truth for site codes, subnets,${NC}"
echo -e "  ${C}gateways, DC/FW IPs, timezones, entities and Ansible regions.${NC}"
echo -e "  ${C}All provisioning scripts (create-vm.py, convert-v2v.py, etc.) read it.${NC}"
echo -e "  ${D}  Source: ${PROV_PKG_PATH}/sites.csv${NC}"
echo

INSTALL_SITES_CSV=true
read -rp "$(echo -e "  ${Y}Download and place sites.csv? [Y/n]: ${NC}")" SITES_INPUT
if [[ "${SITES_INPUT,,}" == "n" || "${SITES_INPUT,,}" == "no" ]]; then
  INSTALL_SITES_CSV=false
  info "Skipping sites.csv placement."
fi

SITES_CSV_PATH=""
if [[ "${INSTALL_SITES_CSV}" == "true" ]]; then
  read -rp "$(echo -e "  ${C}[?]${NC} Install sites.csv to directory [/etc/example-music]: ")" SITES_DIR_INPUT
  SITES_DIR="${SITES_DIR_INPUT:-/etc/example-music}"

  step "Creating directory ${SITES_DIR} ..."
  mkdir -p "${SITES_DIR}"
  ok "Directory ready: ${SITES_DIR}"

  SITES_CSV_DEST="${SITES_DIR}/sites.csv"
  SITES_CSV_URL="${PROV_PKG_PATH}/sites.csv"

  step "Downloading sites.csv from ${SITES_CSV_URL} ..."
  if wget -q -O "${SITES_CSV_DEST}" "${SITES_CSV_URL}"; then
    SITE_COUNT=$(tail -n +2 "${SITES_CSV_DEST}" | wc -l)
    ok "sites.csv installed: ${SITES_CSV_DEST} (${SITE_COUNT} sites)"
    SITES_CSV_PATH="${SITES_CSV_DEST}"
    # Export for any scripts run later in this session
    export SITES_CSV="${SITES_CSV_DEST}"
  else
    warn "Could not fetch sites.csv from ${SITES_CSV_URL}"
    warn "Place manually: wget -O ${SITES_CSV_DEST} ${SITES_CSV_URL}"
    INSTALL_SITES_CSV=false
  fi
fi

# ── Step 3f: BIOS ROM files ───────────────────────────────────────────────────
section "CUSTOM BIOS ROM FILES"

echo -e "  ${C}Custom BIOS ROM files allow VMs to use modded SeaBIOS or UEFI firmware${NC}"
echo -e "  ${C}with SLIC/SLP activation baked in (e.g. Dell SLIC 2.7 for Windows Server).${NC}"
echo -e "  ${C}create-vm.py and convert-v2v.py enumerate these from /usr/share/kvm/.${NC}"
echo -e "  ${D}  Source: ${PROV_PKG_PATH}/usr/share/kvm/${NC}"
echo

INSTALL_BIOS_ROMS=true
read -rp "$(echo -e "  ${Y}Download BIOS ROM files to /usr/share/kvm/? [Y/n]: ${NC}")" BIOS_INPUT
if [[ "${BIOS_INPUT,,}" == "n" || "${BIOS_INPUT,,}" == "no" ]]; then
  INSTALL_BIOS_ROMS=false
  info "Skipping BIOS ROM files."
fi

BIOS_ROMS_INSTALLED=0
if [[ "${INSTALL_BIOS_ROMS}" == "true" ]]; then
  mkdir -p /usr/share/kvm
  BIOS_ROMS=(
    "WORKSTATION_25H2_DELL2.7_BIOS.440.ROM"
    "WORKSTATION_25H2_DELL2.7_EFI20-64.ROM"
    "WORKSTATION_25H2_DELL2.7_EFI64.ROM"
    "BIOS.440.ROM"
    "EFI20-64.ROM"
    "EFI64.ROM"
  )
  for rom in "${BIOS_ROMS[@]}"; do
    ROM_URL="${PROV_PKG_PATH}/usr/share/kvm/${rom}"
    ROM_DEST="/usr/share/kvm/${rom}"
    if [[ -f "${ROM_DEST}" ]]; then
      ok "Already present: ${rom}"
      (( BIOS_ROMS_INSTALLED++ )) || true
    else
      if wget -q -O "${ROM_DEST}" "${ROM_URL}"; then
        ok "Downloaded: ${rom}"
        (( BIOS_ROMS_INSTALLED++ )) || true
      else
        warn "Failed to download: ${rom}"
        warn "  URL: ${ROM_URL}"
      fi
    fi
  done
  ok "${BIOS_ROMS_INSTALLED}/${#BIOS_ROMS[@]} BIOS ROM files in /usr/share/kvm/"
fi

# ── Step 3g: Provisioning scripts ────────────────────────────────────────────
section "PROVISIONING SCRIPTS"

echo -e "  ${C}Infrastructure management scripts from the provisioning server.${NC}"
echo -e "  ${C}Installed directly to /usr/local/bin/ -- on PATH immediately, no setup needed.${NC}"
echo -e "  ${D}  Source: ${PROV_PKG_PATH}/${NC}"
echo -e "  ${D}  Scripts: create-vm.py  convert-v2v.py  manage-pool.py${NC}"
echo -e "  ${D}           site-inventory-audit.py  bulk_iso_upload.py${NC}"
echo -e "  ${D}           pve-bootorder.py  virt-v2v-vmdp.sh${NC}"
echo

INSTALL_SCRIPTS=true
read -rp "$(echo -e "  ${Y}Download provisioning scripts to /usr/local/bin/? [Y/n]: ${NC}")" SCRIPTS_INPUT
if [[ "${SCRIPTS_INPUT,,}" == "n" || "${SCRIPTS_INPUT,,}" == "no" ]]; then
  INSTALL_SCRIPTS=false
  info "Skipping provisioning scripts."
fi

SCRIPTS_INSTALLED=0
if [[ "${INSTALL_SCRIPTS}" == "true" ]]; then
  SCRIPTS=(
    "create-vm.py"
    "convert-v2v.py"
    "manage-pool.py"
    "site-inventory-audit.py"
    "bulk_iso_upload.py"
    "pve-bootorder.py"
    "virt-v2v-vmdp.sh"
  )

  for script in "${SCRIPTS[@]}"; do
    SCRIPT_DEST="/usr/local/bin/${script}"
    if wget -q -O "${SCRIPT_DEST}" "${PROV_PKG_PATH}/${script}"; then
      chmod +x "${SCRIPT_DEST}"
      ok "Downloaded: ${script} → ${SCRIPT_DEST}"
      (( SCRIPTS_INSTALLED++ )) || true
    else
      warn "Failed to download: ${script} from ${PROV_PKG_PATH}/${script}"
    fi
  done

  ok "${SCRIPTS_INSTALLED}/${#SCRIPTS[@]} scripts installed to /usr/local/bin/"
fi

# Drop a profile.d file to export SITES_CSV so scripts find sites.csv
# without needing --sites-csv on every invocation.
if [[ -f /etc/example-music/sites.csv ]]; then
  cat > /etc/profile.d/example-music.sh << 'PROFEOF'
# Example Music -- export SITES_CSV so provisioning scripts find sites.csv
if [ -f /etc/example-music/sites.csv ]; then
  export SITES_CSV=/etc/example-music/sites.csv
fi
PROFEOF
  chmod 644 /etc/profile.d/example-music.sh
  ok "SITES_CSV export written: /etc/profile.d/example-music.sh"
fi

# ── Step 4: Ansible user ──────────────────────────────────────────────────────
section "ANSIBLE USER SETUP"

ANSIBLE_USER="ansible"
ANSIBLE_PASSWORD="Password1!"
SSH_KEY_URL="http://192.168.139.50/ansible_sshkey.pub"

step "Creating ansible user..."
if id "$ANSIBLE_USER" &>/dev/null; then
  warn "User ${ANSIBLE_USER} already exists -- updating password"
else
  useradd -m -s /bin/bash "$ANSIBLE_USER"
  ok "User ${ANSIBLE_USER} created"
fi

step "Setting password..."
echo "${ANSIBLE_USER}:${ANSIBLE_PASSWORD}" | chpasswd
ok "Password set to ${ANSIBLE_PASSWORD}"

step "Fetching SSH public key..."
mkdir -p /home/${ANSIBLE_USER}/.ssh
wget -q -O /home/${ANSIBLE_USER}/.ssh/authorized_keys "$SSH_KEY_URL" && ok "SSH key installed" || err "Failed to fetch SSH key from ${SSH_KEY_URL}"

step "Setting permissions..."
chown -R ${ANSIBLE_USER}:${ANSIBLE_USER} /home/${ANSIBLE_USER}
chmod 700 /home/${ANSIBLE_USER}/.ssh
chmod 600 /home/${ANSIBLE_USER}/.ssh/authorized_keys
ok "Permissions set"

step "Configuring NOPASSWD sudo..."
cat > /etc/sudoers.d/ansible <<SUDOEOF
# Ansible automation -- full passwordless sudo
ansible ALL=(ALL) NOPASSWD: ALL
SUDOEOF
chmod 0440 /etc/sudoers.d/ansible
visudo -c -f /etc/sudoers.d/ansible || {
  rm -f /etc/sudoers.d/ansible
  err "sudoers syntax check failed -- file removed"
}
ok "Sudoers configured"

step "Adding ansible user to kvm group (required for virt-v2v / libguestfs performance)..."
if getent group kvm &>/dev/null; then
  usermod -aG kvm "${ANSIBLE_USER}"
  ok "ansible added to kvm group -- /dev/kvm accessible without sudo"
else
  warn "kvm group does not exist on this system -- skipping"
  warn "If virt-v2v runs slowly, check: ls -la /dev/kvm"
fi

step "Writing .vimrc..."
printf 'set ruler\nset bg=dark\nsyntax on\n' > /home/${ANSIBLE_USER}/.vimrc
chown ${ANSIBLE_USER}:${ANSIBLE_USER} /home/${ANSIBLE_USER}/.vimrc
ok ".vimrc written"

step "Configuring zsh for ansible user..."
cat > /home/${ANSIBLE_USER}/.zshrc <<'ZSHRC'
# Example Music -- ansible user zshrc
export TERM=xterm-256color
export EDITOR=vim
export VISUAL=vim
export SUDO_EDITOR=vim
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt appendhistory autocd extendedglob notify interactivecomments
setopt AUTO_CONTINUE LONG_LIST_JOBS
bindkey -e

autoload -Uz compinit && compinit
autoload -Uz colors && colors

# Key bindings
bindkey "\e[1~"   beginning-of-line
bindkey "\e[4~"   end-of-line
bindkey "\e[H"    beginning-of-line
bindkey "\e[F"    end-of-line
bindkey "\eOH"    beginning-of-line
bindkey "\eOF"    end-of-line
bindkey "\e[1;5C" forward-word
bindkey "\e[1;5D" backward-word
bindkey "\e[5C"   forward-word
bindkey "\e[5D"   backward-word
bindkey "\e\e[C" forward-word
bindkey "\e\e[D" backward-word
bindkey "\e[3~"   delete-char

# Green prompt for non-root: username@hostname:dir>
PROMPT='
%F{green}%n@%m%f:%F{cyan}%~%f> '

alias ls='ls --color=auto'
alias ll='ls -lah'
alias grep='grep --color=auto'

# Example Music provisioning scripts
[[ -f /etc/profile.d/example-music.sh ]] && source /etc/profile.d/example-music.sh

# grc -- colourised output for common commands
if (( $+commands[grc] )); then
  GRC_ALIASES=true
  [[ -f /etc/profile.d/grc.sh ]] && source /etc/profile.d/grc.sh
fi
ZSHRC
chown ${ANSIBLE_USER}:${ANSIBLE_USER} /home/${ANSIBLE_USER}/.zshrc
chsh -s "$(command -v zsh)" ${ANSIBLE_USER}
ok "zsh configured for ansible user (green prompt)"

step "Configuring zsh for root..."
cat > /root/.zshrc <<'ZSHRC'
# Example Music -- root zshrc
export TERM=xterm-256color
export EDITOR=vim
export VISUAL=vim
export SUDO_EDITOR=vim
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt appendhistory autocd extendedglob notify interactivecomments
setopt AUTO_CONTINUE LONG_LIST_JOBS
bindkey -e

autoload -Uz compinit && compinit
autoload -Uz colors && colors

# Key bindings
bindkey "\e[1~"   beginning-of-line
bindkey "\e[4~"   end-of-line
bindkey "\e[H"    beginning-of-line
bindkey "\e[F"    end-of-line
bindkey "\eOH"    beginning-of-line
bindkey "\eOF"    end-of-line
bindkey "\e[1;5C" forward-word
bindkey "\e[1;5D" backward-word
bindkey "\e[5C"   forward-word
bindkey "\e[5D"   backward-word
bindkey "\e\e[C" forward-word
bindkey "\e\e[D" backward-word
bindkey "\e[3~"   delete-char

# Red prompt for root: username@hostname:dir#
PROMPT='
%F{red}%n@%m%f:%F{cyan}%~%f# '

alias ls='ls --color=auto'
alias ll='ls -lah'
alias grep='grep --color=auto'

# Example Music provisioning scripts
[[ -f /etc/profile.d/example-music.sh ]] && source /etc/profile.d/example-music.sh

# grc -- colourised output for common commands
if (( $+commands[grc] )); then
  GRC_ALIASES=true
  [[ -f /etc/profile.d/grc.sh ]] && source /etc/profile.d/grc.sh
fi
ZSHRC
chsh -s "$(command -v zsh)" root
ok "zsh configured for root (red prompt)"

# ── Step 5: Sentinel file ─────────────────────────────────────────────────────
section "WRITING SENTINEL FILE"

cat > /etc/.i_am_a_pve_node <<SENTINELEOF
Configured by Example Music provisioning script
Hostname    : ${HOSTNAME}
FQDN        : ${FQDN}
Site        : ${SITE_CODE}
City        : ${SITE_CITY_VAL}
Country     : ${SITE_COUNTRY_VAL}
Entity      : ${SITE_ENTITY_VAL}
Node IP     : ${NODE_IP}
Gateway     : ${GATEWAY}
Date        : $(date -u +%Y-%m-%dT%H:%M:%SZ)
SENTINELEOF
chmod 0444 /etc/.i_am_a_pve_node
ok "Sentinel written -> /etc/.i_am_a_pve_node"

# ── Step 6: Dynamic MOTD ──────────────────────────────────────────────────────
section "CONFIGURING DYNAMIC MOTD"

chmod -x /etc/update-motd.d/* 2>/dev/null || true

cat > /etc/update-motd.d/10-pve <<'MOTD'
#!/bin/bash
GR='\033[0;32m'
CY='\033[0;36m'
YL='\033[0;33m'
WH='\033[1;37m'
NC='\033[0m'

HOSTNAME_S=$(hostname -s)
FQDN_S=$(hostname -f 2>/dev/null || echo "$HOSTNAME_S")
SITE="UNKNOWN"; CITY="Unknown"; COUNTRY="GB"
ENTITY="Example Music"; NODE_IP="unknown"
if [[ -f /etc/.i_am_a_pve_node ]]; then
  SITE=$(   grep "^Site"    /etc/.i_am_a_pve_node | awk -F': ' '{print $2}' | xargs)
  CITY=$(   grep "^City"    /etc/.i_am_a_pve_node | awk -F': ' '{print $2}' | xargs)
  COUNTRY=$(grep "^Country" /etc/.i_am_a_pve_node | awk -F': ' '{print $2}' | xargs)
  ENTITY=$( grep "^Entity"  /etc/.i_am_a_pve_node | awk -F': ' '{print $2}' | xargs)
  NODE_IP=$(grep "^Node IP" /etc/.i_am_a_pve_node | awk -F': ' '{print $2}' | xargs)
fi

LAN_INFO=""
while IFS= read -r iface; do
  [[ "$iface" == "lo" ]] && continue
  IP=$(ip -4 addr show "$iface" 2>/dev/null | awk '/inet /{print $2}' | head -1)
  [[ -z "$IP" ]] && continue
  LAN_INFO="${LAN_INFO}    ${GR}${iface}${NC} : ${GR}${IP}${NC}\n"
done < <(ip -o link show | awk -F': ' '{print $2}' | grep -v '@')

VM_COUNT=0; CT_COUNT=0; VM_RUNNING=0; CT_RUNNING=0
if command -v qm &>/dev/null; then
  VM_COUNT=$(qm list 2>/dev/null | tail -n +2 | wc -l)
  VM_RUNNING=$(qm list 2>/dev/null | tail -n +2 | grep -c "running" || true)
fi
if command -v pct &>/dev/null; then
  CT_COUNT=$(pct list 2>/dev/null | tail -n +2 | wc -l)
  CT_RUNNING=$(pct list 2>/dev/null | tail -n +2 | grep -c "running" || true)
fi

STORAGE_INFO=""
if command -v pvesm &>/dev/null; then
  while IFS= read -r line; do
    STORAGE_INFO="${STORAGE_INFO}    ${CY}${line}${NC}\n"
  done < <(pvesm status 2>/dev/null | tail -n +2 | awk '{printf "%-20s %s used of %s (%s%%)\n", $1, $4, $3, $6}' || true)
fi

UPTIME=$(uptime -p 2>/dev/null | sed 's/up //')
LOAD=$(cut -d' ' -f1-3 /proc/loadavg)
MEM_TOTAL=$(free -m | awk '/^Mem/{print $2}')
MEM_USED=$(free -m  | awk '/^Mem/{print $3}')
DISK=$(df -h / | awk 'NR==2{print $3 " used of " $2 " (" $5 ")"}')
PVE_VER=$(pveversion 2>/dev/null | head -1 || echo "unknown")
ZFS_STATUS=$(zpool status -x 2>/dev/null || echo "ZFS unavailable")

echo -e "
${GR}⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⠤⠤⣄⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠞⠉⢀⣀⣀⣿⣧⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣾⠁⣠⠖⠉⢀⣀⣧⣈⣧⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣀⣷⣄⠀⠀⠀⠀⠀⠀⣠⢾⠛⣿⡁⣠⠞⠉⢀⣯⣀⣈⣇⠀
⠀⠀⠀⠀⠀⢀⣼⣿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⠞⠉⠀⣀⣘⣏⠛⣷⢤⣀⣀⡤⠞⠁⣸⠟⠀⡷⠃⣠⣶⣟⣏⣀⣀⣘⣆
⠀⠀⠀⠀⠀⣾⡿⠛⢻⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠞⠀⣠⠖⠉⠉⠉⣏⠙⡿⢾⣄⣀⣀⣠⣼⣽⣠⠞⠀⡰⠃⢨⠟⠋⠀⠀⠀⠉
⠀⠀⠀⠀⢰⣿⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡏⢠⠞⠁⣠⣴⣾⣿⠏⠉⠓⢾⣦⣀⡀⢻⡿⠟⠁⢀⠞⠁⡴⠃⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠸⡇⠀⢀⣾⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣆⠀⡸⢀⠏⢠⠞⠁⣨⠟⠋⠉⠉⠉⢻⡧⢤⣈⣁⣀⣠⠖⠋⢀⡞⠁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣿⣤⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠛⢳⡇⡸⢠⠏⢠⠞⠁⣠⠔⠊⠉⠉⢻⠗⠦⣄⣀⠀⢀⣠⠔⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣠⣾⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢠⣀⣀⣤⠀⠀⠀⠀⠀⠀⢸⣀⡞⣷⠇⡜⢠⠏⢀⡞⠁⠀⠀⣰⢞⣻⠇⠀⠀⠀⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⣠⣾⣿⡿⣏⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡐⠦⠤⢤⡈⣻⢿⡖⠦⠤⣀⣠⣴⠏⢘⡟⢀⠃⡜⢠⠏⠀⠀⠀⠀⠛⠛⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⣴⣿⡿⠋⠀⢻⡉⠀⠀⠀⠀⠀⠀⠀⠀⠑⠒⠢⠄⢤⣀⣏⠙⢻⠲⠤⢿⣿⣋⠤⠊⢀⣾⣠⠃⡜⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢰⣿⡟⠀⢀⣴⣿⣿⣿⣿⣦⠀⠀⠀⠀⠀⠒⠒⠲⠤⣤⡀⣯⣉⠛⠒⠦⠤⣀⣀⣀⡤⠚⢹⣿⣰⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢸⡿⠀⠀⣿⠟⠛⣿⠟⠛⣿⣧⠀⠀⠀⠐⠐⠒⠒⠰⣹⠷⣯⣈⡉⠑⠒⠦⠤⣀⣀⣀⡤⢿⢀⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠘⣿⡀⠀⢿⡀⠀⢻⣤⠖⢻⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠓⠲⠤⢄⣀⣀⣀⣼⠟⣸⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠘⢷⣄⠈⠙⠦⠸⡇⢀⡾⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⣿⡿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠙⠛⠶⠤⠶⣿⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢹⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⢀⣴⣾⣿⣆⠀⠈⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠈⣿⣿⡿⠃⠀⣰⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠈⣙⠓⠒⠚⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀${NC}

${WH}+================================================================+${NC}
${WH}| EXAMPLE MUSIC LIMITED: $(printf '%-38s' "${HOSTNAME_S}")|${NC}
${WH}+================================================================+${NC}

  ${YL}Site     :${NC} ${SITE} -- ${CITY}, ${COUNTRY}
  ${YL}Entity   :${NC} ${ENTITY}
  ${YL}PVE      :${NC} ${PVE_VER}
  ${YL}FQDN     :${NC} ${FQDN_S}

  ${WH}-- Network --------------------------------------------------${NC}
$(echo -e "${LAN_INFO}" | grep -v '^$')

  ${WH}-- Guests ---------------------------------------------------${NC}
    ${CY}VMs${NC}        : ${GR}${VM_RUNNING}${NC} running of ${VM_COUNT} defined
    ${CY}Containers${NC} : ${GR}${CT_RUNNING}${NC} running of ${CT_COUNT} defined

  ${WH}-- Storage --------------------------------------------------${NC}
$(echo -e "${STORAGE_INFO:-    ${CY}(pvesm not available)${NC}}" | grep -v '^$')

  ${WH}-- ZFS -------------------------------------------------------${NC}
    ${CY}${ZFS_STATUS}${NC}

  ${WH}-- System ---------------------------------------------------${NC}
    ${CY}Uptime${NC}   : ${GR}${UPTIME}${NC}
    ${CY}Load${NC}     : ${GR}${LOAD}${NC}
    ${CY}Memory${NC}   : ${GR}${MEM_USED}MB${NC} used of ${MEM_TOTAL}MB
    ${CY}Disk /  ${NC} : ${GR}${DISK}${NC}

  ${WH}-- Management -----------------------------------------------${NC}
    ${CY}Web UI${NC}   : ${GR}https://${NODE_IP}:8006${NC}

"
MOTD

chmod +x /etc/update-motd.d/10-pve
ok "MOTD written"

if grep -q "^PrintMotd" /etc/ssh/sshd_config; then
  sed -i "s/^PrintMotd.*/PrintMotd yes/" /etc/ssh/sshd_config
else
  echo "PrintMotd yes" >> /etc/ssh/sshd_config
fi
cat > /etc/profile.d/motd.sh <<'PROFEOF'
[[ -x /etc/update-motd.d/10-pve ]] && /etc/update-motd.d/10-pve
PROFEOF
systemctl restart ssh 2>/dev/null || true
ok "MOTD configured -- shows on SSH login and console"

# ── Step 7: Rename node and fix network (LAST -- session drops on reboot) ───────────────────────────────────────
section "RENAMING NODE AND FIXING NETWORK"

step "Setting /etc/hostname..."
echo "$HOSTNAME" > /etc/hostname
ok "/etc/hostname -> ${HOSTNAME}"

step "Updating /etc/hosts..."
# Replace any existing 127.0.1.1 line
sed -i "s/127\.0\.1\.1.*/127.0.1.1\t${FQDN}\t${HOSTNAME}/" /etc/hosts
# Remove any stale lines with the old node IP (pve-install default)
sed -i "/^192\.168\.[0-9]\+\.[0-9]\+\s/d" /etc/hosts
# Add the new node IP
echo -e "${NODE_IP}\t${FQDN}\t${HOSTNAME}" >> /etc/hosts
ok "/etc/hosts updated"

step "Fixing /etc/network/interfaces..."
# The PVE installer creates vmbr0 bridging over the physical NIC.
# The physical NIC is listed as bridge-ports and has no IP (inet manual).
# Read it directly from the current interfaces file -- most reliable source.
PHYS_NIC=$(awk '/bridge-ports/{print $2}' /etc/network/interfaces 2>/dev/null | head -1)
if [[ -z "$PHYS_NIC" ]]; then
  # Fallback: first non-virtual interface from ip link
  PHYS_NIC=$(ip -o link show | awk -F': ' '{print $2}' | grep -vE '^(lo|vmbr|fwbr|fwpr|fwln|tap|veth|bond|docker|br-)' | head -1)
fi
PHYS_NIC="${PHYS_NIC:-ens32}"
ok "Physical NIC: ${PHYS_NIC}"

cat > /etc/network/interfaces <<NETEOF
auto lo
iface lo inet loopback

iface ${PHYS_NIC} inet manual

auto vmbr0
iface vmbr0 inet static
    address ${NODE_IP}/24
    gateway ${GATEWAY}
    bridge-ports ${PHYS_NIC}
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes

source /etc/network/interfaces.d/*
NETEOF
ok "/etc/network/interfaces written (${NODE_IP}/24 gw ${GATEWAY} via ${PHYS_NIC})"

step "Applying hostname to running system..."
hostnamectl set-hostname "$HOSTNAME"
ok "Hostname: $(hostname)"

if [ -f /etc/postfix/main.cf ]; then
  step "Updating postfix..."
  sed -i "s/^myhostname\s*=.*/myhostname = ${FQDN}/" /etc/postfix/main.cf
  ok "Postfix myhostname -> ${FQDN}"
fi

step "Setting persistent DNS via PVE..."
pvesh set /nodes/$(hostname)/dns     --dns1 1.1.1.1     --dns2 9.9.9.9     --search jukebox.internal 2>&1 | sed 's/^/    /'
ok "DNS: 1.1.1.1 (Cloudflare) + 9.9.9.9 (Quad9) -- search: jukebox.internal"

# Verify resolv.conf was updated
DNS_CHECK=$(grep -c "nameserver" /etc/resolv.conf 2>/dev/null || echo "0")
if [[ "$DNS_CHECK" -ge 1 ]]; then
  ok "resolv.conf updated:"
  grep -E "nameserver|search" /etc/resolv.conf | sed 's/^/    /'
else
  warn "resolv.conf may not have updated -- check manually after reboot"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo
echo -e "${G}  +======================================================+${NC}"
echo -e "${G}  |${W}  PROVISIONING COMPLETE                                ${G}|${NC}"
echo -e "${G}  +======================================================+${NC}"
echo
CURRENT_IP=$(ip -4 addr show vmbr0 2>/dev/null | awk '/inet /{print $2}' | head -1)
CURRENT_IP="${CURRENT_IP:-unknown}"
SSH_KEY_COUNT=$(wc -l < /home/${ANSIBLE_USER}/.ssh/authorized_keys 2>/dev/null || echo 0)

printf "  ${G}[+]${NC}  %-18s %s\n" "Hostname :"   "${W}${FQDN}${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "IP address :"  "${W}${NODE_IP}/24  gw ${GATEWAY}${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "Site :"        "${W}${SITE_CODE} -- ${SITE_CITY_VAL}, ${SITE_COUNTRY_VAL}${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "Entity :"      "${W}${SITE_ENTITY_VAL}${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "Web UI :"      "${W}https://${NODE_IP}:8006${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "Ansible user :" "${W}${ANSIBLE_USER} -- ${SSH_KEY_COUNT} SSH key(s)${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "Sentinel :"    "${W}/etc/.i_am_a_pve_node${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "molly-guard :" "${W}active${NC}"
echo

# V2V status
if [[ "${INSTALL_V2V}" == "true" ]]; then
  if [[ "${VIRTIO_READY}" == "true" ]]; then
    printf "  ${G}[+]${NC}  %-18s %s\n" "virt-v2v :" "${W}ready -- VirtIO drivers extracted, helper exes present${NC}"
  else
    printf "  ${Y}[!]${NC}  %-18s %s\n" "virt-v2v :" "${Y}partial -- check warnings above${NC}"
  fi
else
  printf "  ${C}[i]${NC}  %-18s %s\n" "virt-v2v :" "${D}skipped${NC}"
fi

# sites.csv status
if [[ "${INSTALL_SITES_CSV}" == "true" ]] && [[ -n "${SITES_CSV_PATH}" ]]; then
  printf "  ${G}[+]${NC}  %-18s %s\n" "sites.csv :" "${W}${SITES_CSV_PATH}${NC}"
else
  printf "  ${C}[i]${NC}  %-18s %s\n" "sites.csv :" "${D}skipped${NC}"
fi

# BIOS ROMs status
if [[ "${INSTALL_BIOS_ROMS}" == "true" ]]; then
  printf "  ${G}[+]${NC}  %-18s %s\n" "BIOS ROMs :" "${W}${BIOS_ROMS_INSTALLED} files in /usr/share/kvm/${NC}"
else
  printf "  ${C}[i]${NC}  %-18s %s\n" "BIOS ROMs :" "${D}skipped${NC}"
fi

# Scripts status
if [[ "${INSTALL_SCRIPTS}" == "true" ]]; then
  printf "  ${G}[+]${NC}  %-18s %s\n" "Scripts :" "${W}${SCRIPTS_INSTALLED} scripts in /usr/local/bin/${NC}"
else
  printf "  ${C}[i]${NC}  %-18s %s\n" "Scripts :" "${D}skipped${NC}"
fi

# proxmoxbmc status -- print token value here so it is in one place
if [[ "${INSTALL_PROXMOXBMC}" == "true" ]]; then
  printf "  ${G}[+]${NC}  %-18s %s\n" "proxmoxbmc :" "${W}installed and running  (port = 6000 + VMID)${NC}"
  if [[ -n "${PBMC_API_TOKEN_VALUE}" ]]; then
    printf "  ${G}[+]${NC}  %-18s %s\n" "BMC API token :" "${W}root@pam!proxmoxbmc${NC}"
    echo
    echo -e "  ${Y}+-- BMC API TOKEN (save this now -- it will not be shown again) ----+${NC}"
    echo -e "  ${Y}|${NC}  Token name  : root@pam!proxmoxbmc                               ${Y}|${NC}"
    echo -e "  ${Y}|${NC}  Token value : ${W}${PBMC_API_TOKEN_VALUE}${NC}$(printf '%*s' $((40 - ${#PBMC_API_TOKEN_VALUE})) '')${Y}|${NC}"
    echo -e "  ${Y}|${NC}                                                                   ${Y}|${NC}"
    echo -e "  ${Y}|${NC}  Store in password manager. Used in pbmc add --token-value        ${Y}|${NC}"
    echo -e "  ${Y}+-------------------------------------------------------------------+${NC}"
    echo
  else
    printf "  ${Y}[!]${NC}  %-18s %s\n" "BMC API token :" "${Y}could not auto-create -- create manually (see above)${NC}"
  fi
else
  printf "  ${C}[i]${NC}  %-18s %s\n" "proxmoxbmc :" "${D}skipped${NC}"
fi
echo
echo -e "${C}  +------------------------------------------------------+${NC}"
echo -e "${C}  |  POST-PROVISIONING: LET'S ENCRYPT WILDCARD CERT     |${NC}"
echo -e "${C}  |                                                       |${NC}"
echo -e "${C}  |  1. Datacenter → ACME → Accounts → Add              |${NC}"
echo -e "${C}  |     (register letsencrypt account)                   |${NC}"
echo -e "${C}  |  2. Datacenter → ACME → DNS Plugins → Add           |${NC}"
echo -e "${C}  |     (configure your DNS provider API credentials)    |${NC}"
echo -e "${C}  |  3. Node → Certificates → ACME → Add                |${NC}"
echo -e "${C}  |     (add *.yourdomain.com + yourdomain.com)          |${NC}"
echo -e "${C}  |  4. Node → Certificates → Order Certificates Now    |${NC}"
echo -e "${C}  |                                                       |${NC}"
echo -e "${C}  |  See: docs/pve-letsencrypt.md for full procedure    |${NC}"
echo -e "${C}  +------------------------------------------------------+${NC}"
echo
echo -e "${Y}  +------------------------------------------------------+${NC}"
echo -e "${Y}  |  NETWORK MIGRATION ON REBOOT                         |${NC}"
echo -e "${Y}  |                                                       |${NC}"
echo -e "${Y}  |  Current (provisioning) : ${R}${CURRENT_IP}$(printf '%*s' $((24 - ${#CURRENT_IP})) '')${Y}|${NC}"
echo -e "${Y}  |  After reboot (site LAN): ${G}${NODE_IP}/24$(printf '%*s' $((21 - ${#NODE_IP})) '')${Y}|${NC}"
echo -e "${Y}  |                                                       |${NC}"
echo -e "${Y}  |  This SSH session will DROP on reboot.                |${NC}"
echo -e "${Y}  |  Reconnect on the site LAN to ${NODE_IP}              |${NC}"
echo -e "${Y}  +------------------------------------------------------+${NC}"

# ── Single disk warning ───────────────────────────────────────────────────────
VDEV_COUNT=$(zpool status rpool 2>/dev/null | grep -cE '^\s+(sd|nvme|vd)[a-z]+[0-9]+\s+ONLINE' || true)
if [[ "$VDEV_COUNT" -lt 2 ]]; then
    echo
    echo -e "${R}  +======================================================+${NC}"
    echo -e "${R}  |                                                      |${NC}"
    echo -e "${R}  |  WARNING  WARNING  WARNING  WARNING  WARNING         |${NC}"
    echo -e "${R}  |                                                      |${NC}"
    echo -e "${R}  |      THIS NODE HAS NO DISK REDUNDANCY                |${NC}"
    echo -e "${R}  |                                                      |${NC}"
    echo -e "${R}  |  Only 1 disk detected in ZFS pool rpool              |${NC}"
    echo -e "${R}  |  This node WILL lose ALL data if this disk fails     |${NC}"
    echo -e "${R}  |                                                      |${NC}"
    echo -e "${R}  |  When the second disk arrives:                       |${NC}"
    echo -e "${R}  |    Follow zfs-raid0-to-raid1.md to upgrade to        |${NC}"
    echo -e "${R}  |    a full RAID1 mirror before production use         |${NC}"
    echo -e "${R}  |                                                      |${NC}"
    echo -e "${R}  |  DO NOT put this node into production as-is          |${NC}"
    echo -e "${R}  |                                                      |${NC}"
    echo -e "${R}  +======================================================+${NC}"
    echo
    while true; do
      read -rp "$(echo -e "  ${R}Type 'I UNDERSTAND' to confirm you have read this warning: ${NC}")" DISK_WARNING_ACK
      if [[ "$DISK_WARNING_ACK" == "I UNDERSTAND" ]]; then
        warn "Acknowledged. Do not forget -- add the second disk before production."
        break
      else
        echo -e "  ${R}You must type exactly: I UNDERSTAND${NC}"
      fi
    done
    echo
fi

echo
read -rp "$(echo -e "  ${Y}Reboot now? [y/N]: ${NC}")" REBOOT
if [[ "$REBOOT" =~ ^[Yy]$ ]]; then
  info "Rebooting in 5 seconds -- Ctrl-C to cancel"
  info "Reconnect after reboot: ssh root@${NODE_IP}"
  sleep 5
  reboot
else
  info "Skipped -- run: ifreload -a   to apply network without reboot"
fi
echo
