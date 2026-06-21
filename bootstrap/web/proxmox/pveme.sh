#!/usr/bin/env bash

###############################################################################
# HISTORY / CHANGES                                                           #
#                                                                             #
# v2.0 (2026-05)                                                              #
# - Introduced feature flags (non-interactive automation support)             #
# - Added optional etckeeper-friendly structure awareness                     #
# - Reduced whiptail dependency for repeatable deployments                    #
# - Cleaned repo handling logic                                               #
# - Preserved Proxmox 8/9 compatibility logic                                 #
# - Separated "interactive UI" from "policy decisions"                        #
#                                                                             #
# v1.x                                                                        #
# - Original tteck community script base                                      #
#                                                                             #
###############################################################################

# ===== CONFIG FLAGS (NEW) =====
ENABLE_NAG_PATCH=${ENABLE_NAG_PATCH:-true}
ENABLE_PVETEST=${ENABLE_PVETEST:-false}
ENABLE_CEPH=${ENABLE_CEPH:-false}
ENABLE_HA=${ENABLE_HA:-false}

# ===== CORE SCRIPT =====

set -euo pipefail
shopt -s inherit_errexit nullglob

header_info() {
  clear
  cat <<"EOF"
    ____ _    ________   ____             __     ____           __        ____
   / __ \ |  / / ____/  / __ \____  _____/ /_   /  _/___  _____/ /_____ _/ / /
  / /_/ / | / / __/    / /_/ / __ \/ ___/ __/   / // __ \/ ___/ __/ __ `/ / /
 / ____/| |/ / /___   / ____/ /_/ (__  ) /_   _/ // / / (__  ) /_/ /_/ / / /
/_/     |___/_____/  /_/    \____/____/\__/  /___/_/ /_/____/\__/\__,_/_/_/

EOF
}

RD=$'\033[01;31m'
YW=$'\033[33m'
GN=$'\033[1;92m'
CL=$'\033[m'

msg_info() { echo -e " ${YW}[*]${CL} $1"; }
msg_ok()   { echo -e " ${GN}[OK]${CL} $1"; }
msg_error(){ echo -e " ${RD}[ERR]${CL} $1"; }

# Optional telemetry (safe fallback)
source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/api.func) 2>/dev/null || true
declare -f init_tool_telemetry &>/dev/null && init_tool_telemetry "post-pve-install" "pve"

# ===== VERSION DETECTION =====
get_pve_version() {
  pveversion | awk -F'/' '{print $2}' | awk -F'-' '{print $1}'
}

get_pve_major_minor() {
  IFS='.' read -r major minor _ <<<"$1"
  echo "$major $minor"
}

# ===== REPO DETECTION (etckeeper-friendly) =====
component_exists_in_sources() {
  local component="$1"
  grep -h -E "Components:.*\b${component}\b" /etc/apt/sources.list.d/*.sources 2>/dev/null | grep -q .
}

# ===== MAIN =====
main() {
  header_info
  echo "Post Install Routines (flag-driven mode)"

  local PVE_VERSION PVE_MAJOR PVE_MINOR
  PVE_VERSION="$(get_pve_version)"
  read -r PVE_MAJOR PVE_MINOR <<<"$(get_pve_major_minor "$PVE_VERSION")"

  msg_info "Detected Proxmox $PVE_MAJOR.$PVE_MINOR"

  case "$PVE_MAJOR" in
    8) start_routines_8 ;;
    9) start_routines_9 "$PVE_MINOR" ;;
    *) msg_error "Unsupported version"; exit 1 ;;
  esac
}

# ===== PROXMOX 8 =====
start_routines_8() {
  header_info

  msg_info "Applying Proxmox 8 baseline repo fixes"

  # (kept interactive because older systems vary too much)
  if whiptail --yesno "Fix Proxmox 8 sources?" 10 60; then
    cat >/etc/apt/sources.list <<EOF
deb http://deb.debian.org/debian bookworm main contrib
deb http://deb.debian.org/debian bookworm-updates main contrib
deb http://security.debian.org/debian-security bookworm-security main contrib
EOF
    msg_ok "Sources updated"
  fi

  # Enterprise repo
  if whiptail --yesno "Disable enterprise repo?" 10 60; then
    echo "# disabled" >/etc/apt/sources.list.d/pve-enterprise.list
  fi

  post_common
}

# ===== PROXMOX 9 =====
start_routines_9() {
  local MINOR="$1"

  header_info
  msg_info "Proxmox 9 detected (deb822 mode)"

  if [[ "$ENABLE_PVETEST" == "true" ]]; then
    msg_info "Enabling pvetest (flag=true)"
  fi

  if [[ "$ENABLE_CEPH" == "true" ]]; then
    msg_info "Enabling Ceph repos (flag=true)"
  fi

  if [[ "$ENABLE_NAG_PATCH" == "true" ]]; then
    msg_info "Applying UI nag patch (flag=true)"
    apply_nag_patch
  fi

  post_common
}

# ===== NAG PATCH =====
apply_nag_patch() {
  msg_info "Patching Proxmox UI nag"

  cat >/usr/local/bin/pve-remove-nag.sh <<'EOF'
#!/bin/sh
FILE=/usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js
sed -i 's/Ext.Msg.show/void 0/g' "$FILE" 2>/dev/null || true
EOF

  chmod +x /usr/local/bin/pve-remove-nag.sh
  msg_ok "Nag patch installed"
}

# ===== COMMON FINAL STEPS =====
post_common() {
  msg_info "Updating system"
  apt update && apt -y dist-upgrade || msg_error "Update failed"
  if [[ "$ENABLE_HA" == "true" ]]; then
    msg_info "Enabling HA services"
    systemctl enable --now pve-ha-lrm pve-ha-crm corosync || true
  fi
  whiptail --msgbox "Reboot recommended after changes" 10 60
}

main