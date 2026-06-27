#!/usr/bin/env bash
# ==============================================================================
# Example Music Limited — Rudder Server Bootstrap Script
# EXASRVFAL002 (or CLD-hosted Rudder server)
#
# Mirrors the style and structure of ansibleme.sh:
#   - Interactive, idempotent, run as root
#   - Site-code-driven (subnet/inventory auto-derived from sites.csv)
#   - Prompts for hostname and static IP with CLD-aware checks
#   - Installs and configures the Rudder server
#   - Populates allowed-networks from all sites in sites.csv via Rudder API
#   - Sets up LDAP/AD config skeleton
#   - Sentinel file + dynamic MOTD
#
# -------------------------------------------------------------------------------------------------
# Version history
# -------------------------------------------------------------------------------------------------
# v1.0.0  2026-06-23  Initial release. Covers: hostname/IP setup with CLD checks,
#                     base packages, UFW, Rudder repository and install, initial
#                     admin user creation, allowed-networks population from
#                     sites.csv via Rudder API, LDAP config skeleton, Cockpit
#                     install, dynamic MOTD, sentinel file.
# -------------------------------------------------------------------------------------------------

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

# ------------------------------------------------------------------------------
# Colour helpers — identical to ansibleme.sh / firewallme.sh
# ------------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'
info()    { echo -e "${CYAN}[*]${NC} $*"; }
success() { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*" >&2; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
section() { echo; echo -e "${WHITE}── $* ──${NC}"; echo; }

# Checks whether an IP is already live on the network (ping + arping fallback)
# CLD nodes live on the cloud — arping may not work across provider boundaries,
# but we run it anyway as a best-effort check.
ip_in_use() {
  local ip="$1"
  if ping -c1 -W1 "$ip" &>/dev/null 2>&1; then
    return 0
  fi
  if command -v arping &>/dev/null; then
    local gw_iface
    gw_iface=$(ip route | awk '/default/{print $5}' | head -1)
    if [[ -n "${gw_iface}" ]] && arping -c1 -W1 -I "${gw_iface}" "$ip" &>/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

# ------------------------------------------------------------------------------
# Must run as root
# ------------------------------------------------------------------------------
[[ $EUID -ne 0 ]] && die "Run this script with sudo or as root."

# ------------------------------------------------------------------------------
# Site data — loaded from sites.csv (single source of truth)
# Looks for sites.csv in:
#   1. $SITES_CSV environment variable (override)
#   2. Same directory as this script
#   3. /etc/example-music/sites.csv (system-wide install)
# ------------------------------------------------------------------------------
declare -A SITE_OCTET SITE_CITY SITE_COUNTRY SITE_ENTITY SITE_DC SITE_FW

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
  # BUG NOTE (inherited from ansibleme.sh v1.2.0): 'while read' silently drops
  # the last line of a file with no trailing newline. The || [[ -n "$site" ]]
  # guard catches the partial read and processes it normally.
  while IFS=',' read -r site city country cc subnet gateway dc fw landline mobile tz ansible_region entity _rest \
      || [[ -n "$site" ]]; do
    [[ "${first}" -eq 1 ]] && { first=0; continue; }   # skip header
    site="${site// /}"
    [[ -z "${site}" ]] && continue
    local octet
    octet=$(echo "${subnet}" | awk -F'.' '{print $3}')
    SITE_OCTET["${site}"]="${octet}"
    SITE_CITY["${site}"]="${city}"
    SITE_COUNTRY["${site}"]="${country}"
    SITE_ENTITY["${site}"]="${entity}"
    SITE_DC["${site}"]="${dc}"
    SITE_FW["${site}"]="${fw}"
  done < "${csv_path}"
}

load_sites_csv

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
RUDDER_VERSION="8.x"
RUDDER_REPO_URL="https://repository.rudder.io/apt/${RUDDER_VERSION}/"
RUDDER_GPG_URL="https://repository.rudder.io/apt/rudder_apt_key.pub"
RUDDER_GPG_KEY="/usr/share/keyrings/rudder-archive-keyring.gpg"
RUDDER_ADMIN_USER="admin"
RUDDER_URL="https://localhost"
SENTINEL="/etc/.i_am_a_rudder_server"

# ------------------------------------------------------------------------------
# Banner
# ------------------------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            Example Music:- Rudder Server Bootstrap           ║${NC}"
echo -e "${CYAN}║                        rudderme.sh                           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}  Running on hostname: ${GREEN}$(hostname)${NC}"
echo

# ------------------------------------------------------------------------------
# Section 1 — Site / node identity
# ------------------------------------------------------------------------------
section "1. Node identity"

DETECTED_SITE=""
HOSTNAME_NOW=$(hostname)
if [[ "$HOSTNAME_NOW" =~ ^EXA[A-Z]{3}([A-Z]{3})[0-9]{3}$ ]]; then
  DETECTED_SITE="${BASH_REMATCH[1]}"
fi

echo -e "${CYAN}Known site codes:${NC}"
echo -e "${CYAN}  $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort | tr '\n' ' ')${NC}"
echo

SITE_CODE=""
while true; do
  if [[ -n "$DETECTED_SITE" && -v SITE_OCTET[$DETECTED_SITE] ]]; then
    read -rp "  Site code (detected from hostname: ${DETECTED_SITE}, Enter to accept): " SITE_INPUT
    SITE_INPUT="${SITE_INPUT:-${DETECTED_SITE}}"
  else
    read -rp "  Enter site code for this node (e.g. CLD, FAL): " SITE_INPUT
  fi
  SITE_CODE="${SITE_INPUT^^}"

  if [[ -v SITE_OCTET[$SITE_CODE] ]]; then
    WG_OCTET="${SITE_OCTET[$SITE_CODE]}"
    SUBNET="192.168.${WG_OCTET}"
    SITE_DISPLAY_CITY="${SITE_CITY[$SITE_CODE]:-${SITE_CODE}}"
    SITE_DISPLAY_COUNTRY="${SITE_COUNTRY[$SITE_CODE]:-Unknown}"
    SITE_DISPLAY_ENTITY="${SITE_ENTITY[$SITE_CODE]:-Example Music}"
    echo -e "  ${GREEN}→ ${SITE_CODE}: ${SITE_DISPLAY_CITY}, ${SITE_DISPLAY_COUNTRY} — ${SITE_DISPLAY_ENTITY}${NC}"
    echo -e "  ${GREEN}→ management subnet ${SUBNET}.0/24${NC}"
    break
  else
    warn "Unknown site code '${SITE_CODE}'. Try again."
  fi
done

# ------------------------------------------------------------------------------
# Section 2 — Hostname
# ------------------------------------------------------------------------------
section "2. Hostname"

info "Detecting hostname for this Rudder server..."
CURRENT_HOSTNAME=$(hostname -s)
SUGGESTED_HOSTNAME=""

if [[ "${CURRENT_HOSTNAME}" =~ ^[Ee][Xx][Aa] ]]; then
  SUGGESTED_HOSTNAME="${CURRENT_HOSTNAME^^}"
  info "Detected EXA-convention hostname: ${SUGGESTED_HOSTNAME}"
else
  SUGGESTED_HOSTNAME="EXASRVCLD001"
  warn "Current hostname '${CURRENT_HOSTNAME}' does not match EXA* convention."
fi

read -rp "  Hostname for this Rudder server [${SUGGESTED_HOSTNAME}]: " HOSTNAME_INPUT
THIS_HOSTNAME="${HOSTNAME_INPUT:-${SUGGESTED_HOSTNAME}}"
THIS_HOSTNAME="${THIS_HOSTNAME^^}"   # enforce uppercase per site convention

info "Setting hostname to ${THIS_HOSTNAME}..."
hostnamectl set-hostname "${THIS_HOSTNAME}"
grep -q "${THIS_HOSTNAME,,}" /etc/hosts 2>/dev/null || \
  echo "127.0.1.1  ${THIS_HOSTNAME,,}.jukebox.internal  ${THIS_HOSTNAME,,}" >> /etc/hosts
success "Hostname set to ${THIS_HOSTNAME}."

# ------------------------------------------------------------------------------
# Section 3 — Static IP configuration
# ------------------------------------------------------------------------------
section "3. Network / Static IP"

# CLD note: The Rudder server lives in the cloud. IP collision checks use
# ping + arping. If the cloud provider's network blocks ICMP from within the
# instance (common on some providers), the ping check may return false-negative
# (IP appears free even if it's in use). The script warns about this and
# prompts for confirmation before proceeding.

PROV_NET_DEFAULT="${SUBNET}"
info "Provisioning subnet for this site: ${PROV_NET_DEFAULT}.x"

read -rp "  Gateway last octet [1]: " GW_OCTET_INPUT
GW_OCTET="${GW_OCTET_INPUT:-1}"
PROV_GW="${PROV_NET_DEFAULT}.${GW_OCTET}"

read -rp "  Static IP for this Rudder server [${PROV_NET_DEFAULT}.12]: " NODE_IP_INPUT
NODE_STATIC_IP="${NODE_IP_INPUT:-${PROV_NET_DEFAULT}.12}"

info "Checking whether ${NODE_STATIC_IP} is already in use..."
warn "CLD note: ICMP may be filtered on the cloud provider's network."
warn "If ping does not return results, this check may not be reliable."

if ip_in_use "${NODE_STATIC_IP}"; then
  CURRENT_IPS=$(hostname -I)
  if echo "$CURRENT_IPS" | grep -qw "${NODE_STATIC_IP}"; then
    info "${NODE_STATIC_IP} is already assigned to this host — continuing."
  else
    die "${NODE_STATIC_IP} is already in use by another host. Resolve the conflict first."
  fi
else
  success "${NODE_STATIC_IP} appears free — proceeding."
fi

# Detect interface on the target subnet (or closest match)
info "Detecting network interface..."
PROV_IFACE=""
for iface in $(ls /sys/class/net/); do
  [[ "$iface" == "lo" ]] && continue
  ip_addr=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP "(?<=inet\s)\d+\.\d+\.\d+\.\d+" | head -1)
  if [[ -n "$ip_addr" ]]; then
    PROV_IFACE="$iface"
    success "Detected interface: ${PROV_IFACE} (currently ${ip_addr})"
    break
  fi
done

if [[ -z "$PROV_IFACE" ]]; then
  warn "Could not auto-detect interface."
  AVAILABLE_IFACES=($(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | grep -v '@'))
  read -rp "  Enter interface name (available: ${AVAILABLE_IFACES[*]}): " PROV_IFACE
  PROV_IFACE="${PROV_IFACE:-${AVAILABLE_IFACES[0]:-eth0}}"
fi

# Pin interface name via systemd .link
PROV_MAC=$(cat "/sys/class/net/${PROV_IFACE}/address" 2>/dev/null)
info "Pinning ${PROV_IFACE} (MAC ${PROV_MAC}) via systemd .link..."
mkdir -p /etc/systemd/network
cat > /etc/systemd/network/10-rudder-prov.link << EOF
# Example Music — Rudder server interface pin
# Written by rudderme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# MAC: ${PROV_MAC}  interface: ${PROV_IFACE}
[Match]
MACAddress=${PROV_MAC}
[Link]
Name=${PROV_IFACE}
EOF
success "Interface pin written."

# Configure static IP via NetworkManager
info "Configuring static IP via NetworkManager..."

systemctl disable networking.service 2>/dev/null || true
systemctl mask    networking.service 2>/dev/null || true

if [[ -f /etc/network/interfaces ]]; then
  if grep -qE "^(auto|allow-|iface)\s+${PROV_IFACE}" /etc/network/interfaces 2>/dev/null; then
    warn "Removing ifupdown stanza for ${PROV_IFACE} from /etc/network/interfaces..."
    cp -n /etc/network/interfaces /etc/network/interfaces.bak
    sed -i "/^auto\s\+${PROV_IFACE}\b/d"    /etc/network/interfaces
    sed -i "/^allow-.*\s${PROV_IFACE}\b/d"  /etc/network/interfaces
    success "Cleaned /etc/network/interfaces"
  fi
fi

NM_CONF="/etc/NetworkManager/NetworkManager.conf"
if grep -q "managed=false" "${NM_CONF}" 2>/dev/null; then
  warn "NetworkManager.conf has managed=false — fixing..."
  sed -i "s/managed=false/managed=true/" "${NM_CONF}"
fi

systemctl restart NetworkManager
sleep 3

nmcli con delete "rudder-static" 2>/dev/null || true

nmcli con add type ethernet ifname "${PROV_IFACE}" con-name "rudder-static" \
  ipv4.method manual \
  ipv4.addresses "${NODE_STATIC_IP}/24" \
  ipv4.gateway "${PROV_GW}" \
  ipv4.dns "${PROV_NET_DEFAULT}.10" \
  ipv4.dns-search "jukebox.internal" \
  ipv6.method ignore \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  && success "NM profile rudder-static written — will apply on reboot." \
  || warn "nmcli con add returned non-zero — check: nmcli connection show rudder-static"

# BUG FIX (from firewallme.sh / ansibleme.sh): restarting NM during an active
# SSH session drops the connection instantly. Static IP takes effect cleanly on
# next reboot. If at console, run: nmcli con up rudder-static
warn "Static IP will take full effect on reboot."
warn "If at local console (not SSH): nmcli con up rudder-static"

# ------------------------------------------------------------------------------
# Section 4 — Base packages
# ------------------------------------------------------------------------------
section "4. Base packages"

info "Updating package lists..."
apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true

BASE_PKGS=()
command -v curl   &>/dev/null || BASE_PKGS+=(curl)
command -v wget   &>/dev/null || BASE_PKGS+=(wget)
command -v git    &>/dev/null || BASE_PKGS+=(git)
command -v vim    &>/dev/null || BASE_PKGS+=(vim)
command -v htop   &>/dev/null || BASE_PKGS+=(htop)
command -v tree   &>/dev/null || BASE_PKGS+=(tree)
command -v jq     &>/dev/null || BASE_PKGS+=(jq)
command -v python3 &>/dev/null || BASE_PKGS+=(python3)
command -v arping  &>/dev/null || BASE_PKGS+=(arping)
command -v nmcli   &>/dev/null || BASE_PKGS+=(network-manager)
dpkg -s molly-guard &>/dev/null   || BASE_PKGS+=(molly-guard)
dpkg -s fail2ban    &>/dev/null   || BASE_PKGS+=(fail2ban)
dpkg -s ufw         &>/dev/null   || BASE_PKGS+=(ufw)
dpkg -s apache2-utils &>/dev/null || BASE_PKGS+=(apache2-utils)
dpkg -s ca-certificates &>/dev/null || BASE_PKGS+=(ca-certificates)
dpkg -s gnupg       &>/dev/null   || BASE_PKGS+=(gnupg)
dpkg -s lsb-release &>/dev/null   || BASE_PKGS+=(lsb-release)
dpkg -s apt-transport-https &>/dev/null || BASE_PKGS+=(apt-transport-https)

if [[ ${#BASE_PKGS[@]} -gt 0 ]]; then
  info "Installing: ${BASE_PKGS[*]}"
  APT_LOG=$(mktemp /tmp/rudderme-apt-XXXXXX.log)
  if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      -o Dpkg::Options::="--force-confold" \
      -o Dpkg::Options::="--force-confdef" \
      -o Dpkg::Use-Pty=0 \
      --no-install-recommends \
      "${BASE_PKGS[@]}" > "$APT_LOG" 2>&1; then
    success "Base packages installed."
    rm -f "$APT_LOG"
  else
    APT_RC=$?
    warn "apt-get install failed (exit ${APT_RC}) — last 20 lines of log:"
    tail -20 "$APT_LOG" >&2
    warn "Full log: ${APT_LOG}"
    die "Package installation failed. Fix the above and re-run."
  fi
else
  success "All base packages already present."
fi

# ------------------------------------------------------------------------------
# Section 5 — UFW firewall
# ------------------------------------------------------------------------------
section "5. Firewall (UFW)"

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment "SSH"
ufw allow 443/tcp  comment "Rudder HTTPS"
ufw allow 80/tcp   comment "Rudder HTTP redirect"
ufw allow 5309/tcp comment "Rudder CFEngine server-to-agent"
ufw allow 5310/tcp comment "Rudder relay"
ufw allow 9090/tcp comment "Cockpit web UI"

# Allow all site subnets to reach Rudder ports
# (belt-and-braces — the Rudder allowed-networks setting handles
# policy-level enforcement; UFW handles network-level enforcement)
for site_code in $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort); do
  oct="${SITE_OCTET[$site_code]}"
  [[ -z "$oct" ]] && continue
  ufw allow from "192.168.${oct}.0/24" to any port 443  proto tcp \
    comment "Rudder agents ${site_code}" 2>/dev/null || true
  ufw allow from "192.168.${oct}.0/24" to any port 5309 proto tcp \
    comment "Rudder CFEngine ${site_code}" 2>/dev/null || true
done

ufw --force enable
ufw status verbose
success "UFW configured."

# ------------------------------------------------------------------------------
# Section 6 — Rudder repository and server install
# ------------------------------------------------------------------------------
section "6. Rudder server install"

if ! dpkg -l rudder-server &>/dev/null 2>&1; then
  info "Adding Rudder ${RUDDER_VERSION} repository..."

  wget -qO - "${RUDDER_GPG_URL}" | gpg --dearmor > "${RUDDER_GPG_KEY}"

  echo "deb [signed-by=${RUDDER_GPG_KEY}] ${RUDDER_REPO_URL} $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/rudder.list

  apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true

  info "Installing rudder-server (this takes several minutes)..."
  info "Watch progress in another terminal: journalctl -fu rudder-server"

  APT_LOG=$(mktemp /tmp/rudderme-rudder-apt-XXXXXX.log)
  if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      -o Dpkg::Options::="--force-confold" \
      -o Dpkg::Options::="--force-confdef" \
      -o Dpkg::Use-Pty=0 \
      rudder-server > "$APT_LOG" 2>&1; then
    success "rudder-server installed."
    rm -f "$APT_LOG"
  else
    APT_RC=$?
    warn "rudder-server install failed (exit ${APT_RC}) — last 20 lines:"
    tail -20 "$APT_LOG" >&2
    warn "Full log: ${APT_LOG}"
    die "Rudder install failed. Fix the above and re-run."
  fi
else
  success "rudder-server already installed."
fi

# Enable and start
info "Enabling and starting rudder-server..."
systemctl enable rudder-server 2>/dev/null || true
systemctl start  rudder-server 2>/dev/null || true

# Wait for web UI to become available
info "Waiting for Rudder web UI to become available (up to 3 minutes)..."
RUDDER_READY=0
for i in $(seq 1 36); do
  if curl -sk "${RUDDER_URL}/rudder/api/info" 2>/dev/null | grep -q '"action"'; then
    RUDDER_READY=1
    break
  fi
  sleep 5
  printf "."
done
echo

if [[ "$RUDDER_READY" -eq 1 ]]; then
  success "Rudder web UI is available."
else
  warn "Rudder web UI did not respond within 3 minutes."
  warn "Check: journalctl -fu rudder-server"
  warn "The script will continue — some steps may fail until Rudder is ready."
fi

# Verify health
rudder server health 2>/dev/null && success "Rudder server health: OK" || warn "rudder server health returned non-zero — check manually."

# ------------------------------------------------------------------------------
# Section 7 — Initial Rudder configuration
# ------------------------------------------------------------------------------
section "7. Initial Rudder configuration"

# Set FQDN in Rudder
RUDDER_FQDN="${THIS_HOSTNAME,,}.jukebox.internal"
info "Setting Rudder server hostname to ${RUDDER_FQDN}..."
if [[ -f /opt/rudder/etc/rudder-web.properties ]]; then
  if grep -q "rudder.server.name" /opt/rudder/etc/rudder-web.properties; then
    sed -i "s|rudder.server.name=.*|rudder.server.name=${RUDDER_FQDN}|" \
      /opt/rudder/etc/rudder-web.properties
  else
    echo "rudder.server.name=${RUDDER_FQDN}" >> /opt/rudder/etc/rudder-web.properties
  fi
  success "Rudder server FQDN set to ${RUDDER_FQDN}"
else
  warn "/opt/rudder/etc/rudder-web.properties not found — set FQDN manually in the UI."
  warn "Administration → Settings → General → Rudder server hostname"
fi

# Create admin user
info "Creating Rudder admin user..."
echo
echo -e "${YELLOW}  You will be prompted to set a password for the Rudder admin user.${NC}"
echo -e "${YELLOW}  This is the web UI login — store it in your password manager.${NC}"
echo
rudder server create-user -u "${RUDDER_ADMIN_USER}" || warn "create-user returned non-zero — may already exist. Continuing."
success "Admin user '${RUDDER_ADMIN_USER}' configured."

# Store API token setup instructions
echo
echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}  ║   ACTION REQUIRED — CREATE AN API TOKEN                      ║${NC}"
echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "${YELLOW}  |${NC}"
echo -e "${YELLOW}  |${NC}  After logging in, create an API token for automation:"
echo -e "${YELLOW}  |${NC}    Administration → API accounts → New API account"
echo -e "${YELLOW}  |${NC}    Name: rudder-automation  Role: Read/Write"
echo -e "${YELLOW}  |${NC}"
echo -e "${YELLOW}  |${NC}  You need this token to populate allowed-networks below."
echo -e "${YELLOW}  |${NC}"
echo

read -rp "  Enter your Rudder API token (or press Enter to skip allowed-networks step): " RUDDER_TOKEN
RUDDER_TOKEN="${RUDDER_TOKEN// /}"   # strip whitespace

# ------------------------------------------------------------------------------
# Section 8 — Populate allowed-networks from sites.csv
# ------------------------------------------------------------------------------
section "8. Allowed networks — all site subnets"

echo -e "${CYAN}  Rudder needs to know which subnets agents are permitted to connect from.${NC}"
echo -e "${CYAN}  rudderme.sh will build this list from sites.csv automatically.${NC}"
echo

if [[ -z "${RUDDER_TOKEN}" ]]; then
  warn "No API token provided — skipping allowed-networks API call."
  warn "Add networks manually: Administration → Settings → General → Allowed Networks"
  warn "Or re-run this section after creating an API token."
else
  # Build subnets array from sites.csv
  declare -a ALL_SUBNETS=()
  for site_code in $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort); do
    oct="${SITE_OCTET[$site_code]}"
    city="${SITE_CITY[$site_code]:-${site_code}}"
    [[ -z "$oct" ]] && continue
    lan_subnet="192.168.${oct}.0/24"
    wg_subnet="10.0.${oct}.0/24"
    ALL_SUBNETS+=("${lan_subnet}")
    # Only add WireGuard subnets if we have octets configured
    ALL_SUBNETS+=("${wg_subnet}")
    echo -e "  ${CYAN}+${NC} ${lan_subnet}  (${site_code} — ${city} LAN)"
    echo -e "  ${CYAN}+${NC} ${wg_subnet}  (${site_code} — ${city} WireGuard)"
  done

  # Deduplicate
  mapfile -t UNIQUE_SUBNETS < <(printf '%s\n' "${ALL_SUBNETS[@]}" | sort -u)

  info "Building JSON payload with ${#UNIQUE_SUBNETS[@]} subnets..."

  # Build JSON array
  SUBNETS_JSON=$(printf '"%s",' "${UNIQUE_SUBNETS[@]}" | sed 's/,$//')
  PAYLOAD="{\"allowed_networks\": [${SUBNETS_JSON}]}"

  echo
  info "POSTing allowed-networks list to Rudder API..."
  HTTP_STATUS=$(curl -sk -o /tmp/rudder-an-response.json -w "%{http_code}" \
    -X POST \
    -H "X-API-Token: ${RUDDER_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${PAYLOAD}" \
    "${RUDDER_URL}/rudder/api/latest/settings/allowed_networks/root")

  if [[ "${HTTP_STATUS}" == "200" ]]; then
    success "Allowed networks updated successfully (HTTP ${HTTP_STATUS})."
    if command -v jq &>/dev/null; then
      jq -r '.data.settings.allowed_networks[]' /tmp/rudder-an-response.json 2>/dev/null | \
        while read -r net; do echo -e "    ${GREEN}✓${NC} ${net}"; done
    fi
  else
    warn "Allowed-networks API call returned HTTP ${HTTP_STATUS}."
    warn "Response: $(cat /tmp/rudder-an-response.json 2>/dev/null)"
    warn "Add networks manually: Administration → Settings → General → Allowed Networks"
  fi

  rm -f /tmp/rudder-an-response.json
fi

# ------------------------------------------------------------------------------
# Section 9 — LDAP / AD authentication skeleton
# ------------------------------------------------------------------------------
section "9. AD / LDAP authentication"

echo -e "${CYAN}  Setting up the LDAP authentication skeleton in rudder-users.xml.${NC}"
echo -e "${CYAN}  You will need to:${NC}"
echo -e "${CYAN}    1. Create the svc_rudder_ldap AD service account${NC}"
echo -e "${CYAN}    2. Create the GRP_Rudder_Admins AD group${NC}"
echo -e "${CYAN}    3. Generate a bcrypt hash for the local admin password${NC}"
echo -e "${CYAN}    4. Fill in the bind password in rudder-users.xml${NC}"
echo

RUDDER_USERS_XML="/opt/rudder/etc/rudder-users.xml"

if [[ ! -f "${RUDDER_USERS_XML}" ]]; then
  warn "${RUDDER_USERS_XML} not found — Rudder may not be fully initialised yet."
  warn "Create this file manually after Rudder is running, using the template below."
else
  # Only write the skeleton if it does not already have LDAP config
  if ! grep -q "<ldap>" "${RUDDER_USERS_XML}" 2>/dev/null; then
    info "Writing LDAP skeleton to ${RUDDER_USERS_XML}..."

    # Generate a placeholder bcrypt hash for the local admin account
    # The operator must replace this with a real hash
    PLACEHOLDER_HASH="\$2y\$12\$REPLACE_THIS_HASH_WITH_OUTPUT_OF_htpasswd_bnBC_12"

    cat > "${RUDDER_USERS_XML}" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<authentication hash="bcrypt">

  <!--
    Local fallback account — always keep this in case AD is unreachable.
    Generate the password hash with:
      htpasswd -bnBC 12 "" 'YourPassword' | tr -d ':\n'
    Then paste the result (starting with \$2y\$12\$...) below.
  -->
  <user name="admin"
        password="${PLACEHOLDER_HASH}"
        role="administrator"/>

  <!--
    Active Directory LDAP authentication.
    Prerequisites:
      - svc_rudder_ldap service account in AD (read-only)
      - GRP_Rudder_Admins security group in AD
    See: rudder-setup.md section 9 for full AD setup commands.
  -->
  <ldap>
    <connection url="ldap://${PROV_NET_DEFAULT}.10:389"
                bind-dn="CN=Rudder LDAP Bind,OU=Service Accounts,DC=jukebox,DC=example"
                bind-password="REPLACE_WITH_BIND_PASSWORD"/>

    <search base="DC=jukebox,DC=example"
            filter="(&amp;(objectClass=user)(sAMAccountName={0}))"
            returnedAttribute="sAMAccountName"/>

    <roleMapping>
      <!--
        Available roles: administrator, read_only, workflow, deployer,
                         configuration, validator, compliance
      -->
      <roleMap role="administrator"
               group="CN=GRP_Rudder_Admins,OU=IT Groups,DC=jukebox,DC=example"/>
    </roleMapping>
  </ldap>

</authentication>
EOF

    success "LDAP skeleton written to ${RUDDER_USERS_XML}"
    warn "ACTION REQUIRED: fill in the bind password and bcrypt hash before restarting."
    warn "Generate bcrypt hash: htpasswd -bnBC 12 \"\" 'YourPassword' | tr -d ':\\n'"
  else
    success "LDAP configuration already present in ${RUDDER_USERS_XML} — not overwriting."
  fi
fi

echo
echo -e "${CYAN}  After completing AD setup, restart Rudder to pick up the config:${NC}"
echo -e "${GREEN}    systemctl restart rudder-server${NC}"

# ------------------------------------------------------------------------------
# Section 10 — Cockpit
# ------------------------------------------------------------------------------
section "10. Cockpit"

if ! dpkg -l cockpit &>/dev/null 2>&1; then
  info "Installing Cockpit..."
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends cockpit cockpit-pcp
  systemctl enable --now cockpit.socket
  success "Cockpit installed and running."
  info "Cockpit available at: https://${NODE_STATIC_IP}:9090"
else
  success "Cockpit already installed."
  systemctl enable --now cockpit.socket 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# Section 11 — Dynamic MOTD
# ------------------------------------------------------------------------------
section "11. Dynamic MOTD"

cat > /etc/update-motd.d/10-examplemusic << MOTD
#!/usr/bin/env bash
WH='\033[1;37m'; YL='\033[1;33m'; GR='\033[0;32m'; CY='\033[0;36m'; NC='\033[0m'
UPTIME=\$(uptime -p)
LOAD=\$(cut -d' ' -f1-3 /proc/loadavg)
MEM_TOTAL=\$(awk '/MemTotal/{print int(\$2/1024)}' /proc/meminfo)
MEM_FREE=\$(awk '/MemAvailable/{print int(\$2/1024)}' /proc/meminfo)
MEM_USED=\$(( MEM_TOTAL - MEM_FREE ))
DISK=\$(df -h / | awk 'NR==2{print \$3" used of "\$2" ("\$5")"}')
RUDDER_VER=\$(rudder agent version 2>/dev/null | head -1 || echo "unknown")
NODE_COUNT=\$(curl -sk -H "X-API-Token: \${RUDDER_TOKEN:-unset}" \
  https://localhost/rudder/api/latest/nodes 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['total'])" 2>/dev/null || echo "?")
echo -e "
\${WH}╔══════════════════════════════════════════════════════════════╗\${NC}
\${WH}║     EXAMPLE MUSIC LIMITED: \$(printf '%-35s' "\${HOSTNAME}")║\${NC}
\${WH}╚══════════════════════════════════════════════════════════════╝\${NC}

  \${YL}Site     :\${NC} ${SITE_CODE}: ${SITE_DISPLAY_CITY}, ${SITE_DISPLAY_COUNTRY}
  \${YL}Entity   :\${NC} ${SITE_DISPLAY_ENTITY}
  \${YL}Role     :\${NC} Rudder configuration management server

  \${WH}── Rudder ────────────────────────────────────────────────────\${NC}
    \${CY}Version\${NC}    : \${GR}\${RUDDER_VER}\${NC}
    \${CY}Web UI\${NC}     : \${GR}https://${NODE_STATIC_IP}/rudder\${NC}
    \${CY}Cockpit\${NC}    : \${GR}https://${NODE_STATIC_IP}:9090\${NC}
    \${CY}Managed\${NC}    : \${GR}\${NODE_COUNT} node(s)\${NC}

  \${WH}── System ───────────────────────────────────────────────────\${NC}
    \${CY}Uptime\${NC}     : \${GR}\${UPTIME}\${NC}
    \${CY}Load\${NC}       : \${GR}\${LOAD}\${NC}
    \${CY}Memory\${NC}     : \${GR}\${MEM_USED}MB\${NC} used of \${MEM_TOTAL}MB
    \${CY}Disk /\${NC}     : \${GR}\${DISK}\${NC}

  \${WH}── Quick reference ──────────────────────────────────────────\${NC}
    \${CY}Health      :\${NC} rudder server health
    \${CY}Pending     :\${NC} curl -sk -H 'X-API-Token: TOKEN' https://localhost/rudder/api/latest/nodes/pending
    \${CY}Logs        :\${NC} tail -f /var/log/rudder/agent/agent.log
    \${CY}Restart     :\${NC} systemctl restart rudder-server
"
MOTD

chmod +x /etc/update-motd.d/10-examplemusic

if grep -q "^PrintMotd" /etc/ssh/sshd_config 2>/dev/null; then
  sed -i "s/^PrintMotd.*/PrintMotd yes/" /etc/ssh/sshd_config
else
  echo "PrintMotd yes" >> /etc/ssh/sshd_config
fi

cat > /etc/profile.d/motd.sh << 'EOF'
[[ -x /etc/update-motd.d/10-examplemusic ]] && /etc/update-motd.d/10-examplemusic
EOF

systemctl restart ssh 2>/dev/null || true
success "Dynamic MOTD configured."

# ------------------------------------------------------------------------------
# Section 12 — Sentinel file
# ------------------------------------------------------------------------------
{
  echo "Configured by Example Music rudderme.sh"
  echo "Site        : ${SITE_CODE}"
  echo "City        : ${SITE_DISPLAY_CITY}"
  echo "Country     : ${SITE_DISPLAY_COUNTRY}"
  echo "Entity      : ${SITE_DISPLAY_ENTITY}"
  echo "Hostname    : ${THIS_HOSTNAME}"
  echo "Static IP   : ${NODE_STATIC_IP}"
  echo "Rudder URL  : https://${NODE_STATIC_IP}/rudder"
  echo "Cockpit URL : https://${NODE_STATIC_IP}:9090"
  echo "Date        : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${SENTINEL}"
chmod 0444 "${SENTINEL}"
success "Sentinel file written to ${SENTINEL}"

# ------------------------------------------------------------------------------
# Final banner
# ------------------------------------------------------------------------------
echo
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  SETUP COMPLETE — ${THIS_HOSTNAME}${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "${CYAN}  Site        : ${SITE_CODE} — ${SITE_DISPLAY_CITY}, ${SITE_DISPLAY_COUNTRY}${NC}"
echo -e "${CYAN}  Hostname    : ${THIS_HOSTNAME}${NC}"
echo -e "${CYAN}  Static IP   : ${NODE_STATIC_IP} (takes effect on reboot)${NC}"
echo -e "${CYAN}  Rudder URL  : https://${NODE_STATIC_IP}/rudder${NC}"
echo -e "${CYAN}  Cockpit URL : https://${NODE_STATIC_IP}:9090${NC}"
echo

echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}  ║   REMAINING MANUAL STEPS                                     ║${NC}"
echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "  ${WHITE}1.${NC} Log in to Rudder web UI:"
echo -e "     ${GREEN}https://${NODE_STATIC_IP}/rudder${NC}  (admin / password you set above)"
echo
echo -e "  ${WHITE}2.${NC} Create an API token for automation:"
echo -e "     Administration → API accounts → New API account"
echo -e "     Name: rudder-automation  Role: Read/Write"
echo
if [[ -z "${RUDDER_TOKEN}" ]]; then
  echo -e "  ${WHITE}3.${NC} ${YELLOW}Re-run section 8 with your token to populate allowed-networks:${NC}"
  echo -e "     ${GREEN}RUDDER_TOKEN='your-token' bash rudderme.sh --allowed-networks-only${NC}"
  echo -e "     ${CYAN}Or add networks manually: Administration → Settings → General → Allowed Networks${NC}"
  echo
fi
echo -e "  ${WHITE}4.${NC} Complete LDAP setup in AD, then fill in ${RUDDER_USERS_XML}:"
echo -e "     ${CYAN}See rudder-setup.md section 9 for AD commands${NC}"
echo -e "     ${CYAN}Generate bcrypt hash: htpasswd -bnBC 12 \"\" 'Password' | tr -d ':\\n'${NC}"
echo -e "     ${CYAN}Then: systemctl restart rudder-server${NC}"
echo
echo -e "  ${WHITE}5.${NC} Install agents on managed nodes:"
echo -e "     ${CYAN}Linux:   see rudder-setup.md section 10${NC}"
echo -e "     ${CYAN}Windows: see rudder-setup.md section 11${NC}"
echo -e "     ${CYAN}Ansible: ansible-playbook playbooks/rudder/rudder_onboard.yml${NC}"
echo
echo -e "  ${WHITE}6.${NC} Accept pending nodes:"
echo -e "     ${CYAN}Node Management → Pending nodes → Accept${NC}"
echo -e "     ${CYAN}Or via API: see rudder-setup.md section 12${NC}"
echo
echo -e "${GREEN}============================================================${NC}"
echo
