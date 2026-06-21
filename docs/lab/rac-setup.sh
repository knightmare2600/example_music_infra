#!/usr/bin/env bash
# ============================================================
# rac-setup.sh — jukebox.internal RAC (iLO/Redfish) Emulator
# Sets up HPE iLO Redfish emulator as a persistent service
# on a dedicated Debian VM (EXARAC<SITE>001)
# ============================================================

set -euo pipefail

# ── Colour helpers ───────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
ok()      { echo -e "${GREEN}[ OK ]${RESET}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
err()     { echo -e "${RED}[ERR ]${RESET}  $*"; exit 1; }
heading() { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}\n"; }

# ── Must run as root ─────────────────────────────────────────
[[ $EUID -eq 0 ]] || err "Run as root (sudo $0)"

# ════════════════════════════════════════════════════════════
# 1. Node identity
# ════════════════════════════════════════════════════════════
heading "Node Identity"

# Derive site code from hostname if already set, otherwise ask
CURRENT_HOST=$(hostname -s 2>/dev/null || echo "")
SUGGESTED_SITE=""
if [[ "$CURRENT_HOST" =~ ^EXARAC([A-Z]{3})[0-9]{3}$ ]]; then
    SUGGESTED_SITE="${BASH_REMATCH[1]}"
fi

echo "Hostname convention: EXARAC<SITE>001"
echo "Example: EXARACFAL001, EXARACBDE001, EXARACODE001"
echo ""

if [[ -n "$SUGGESTED_SITE" ]]; then
    read -rp "Site code [${SUGGESTED_SITE}]: " SITE_CODE
    SITE_CODE="${SITE_CODE:-$SUGGESTED_SITE}"
else
    read -rp "Site code (3 letters, e.g. FAL): " SITE_CODE
fi

SITE_CODE="${SITE_CODE^^}"
[[ "$SITE_CODE" =~ ^[A-Z]{3}$ ]] || err "Site code must be exactly 3 letters"

# Instance number
read -rp "Instance number [001]: " INSTANCE
INSTANCE="${INSTANCE:-001}"
[[ "$INSTANCE" =~ ^[0-9]{3}$ ]] || err "Instance must be 3 digits (e.g. 001)"

NODE_NAME="EXARAC${SITE_CODE}${INSTANCE}"
FQDN="${NODE_NAME}.jukebox.internal"

info "Node name: ${BOLD}${NODE_NAME}${RESET}"
info "FQDN:      ${BOLD}${FQDN}${RESET}"

# Set hostname
hostnamectl set-hostname "$NODE_NAME"
ok "Hostname set to $NODE_NAME"

# ════════════════════════════════════════════════════════════
# 2. Network
# ════════════════════════════════════════════════════════════
heading "Network Configuration"

# Derive site octet from network-inventory.md convention
# Each site has a /24: 192.168.<octet>.0
read -rp "Site LAN octet (e.g. 76 for FAL 192.168.76.0/24): " OCTET
[[ "$OCTET" =~ ^[0-9]{1,3}$ ]] || err "Invalid octet"

GATEWAY="192.168.${OCTET}.1"
DNS="192.168.${OCTET}.10"

# ── BMC pool allocation (.2, .3, .4) ────────────────────────
# .2/.3/.4 are a shared pool for physical DRAC/iLO BMCs and
# the RAC emulator VM. Physical PVE node BMCs consume from .2
# upward. RAC takes the next free slot.
#
# Typical spoke site (1 PVE node):
#   .2 = PVE node 1 BMC  →  RAC gets .3
# Hub site (2 PVE nodes):
#   .2 = PVE node 1 BMC, .3 = PVE node 2 BMC  →  RAC gets .4
# Three-node site:
#   Pool fully consumed by physical BMCs — RAC cannot use this
#   pool. Script will warn and ask for a manual address.

echo ""
echo "BMC pool: 192.168.${OCTET}.2 / .3 / .4"
echo "Physical PVE node BMCs consume from .2 upward."
echo "How many physical PVE nodes are at this site?"
read -rp "Physical PVE node count [1]: " PVE_COUNT
PVE_COUNT="${PVE_COUNT:-1}"
[[ "$PVE_COUNT" =~ ^[1-3]$ ]] || err "Expected 1, 2, or 3"

NEXT_BMC_SLOT=$(( PVE_COUNT + 2 ))   # .2=first, so n nodes uses .2...(n+1)

if [[ $NEXT_BMC_SLOT -gt 4 ]]; then
    warn "BMC pool (.2/.3/.4) fully consumed by $PVE_COUNT physical PVE nodes."
    warn "RAC VM cannot use the BMC pool at this site."
    read -rp "Enter a manual IP address for the RAC VM: " RAC_IP
    [[ "$RAC_IP" =~ ^192\.168\.[0-9]+\.[0-9]+$ ]] || err "Invalid IP: $RAC_IP"
else
    RAC_IP="192.168.${OCTET}.${NEXT_BMC_SLOT}"
    info "Physical BMCs occupy .2–.$(( NEXT_BMC_SLOT - 1 ))"
    info "RAC VM assigned next free slot: ${BOLD}${RAC_IP}${RESET}"
fi

info "RAC IP:  $RAC_IP"
info "Gateway: $GATEWAY"
info "DNS:     $DNS"

read -rp "Confirm network settings? [Y/n]: " CONFIRM
[[ "${CONFIRM:-Y}" =~ ^[Yy]$ ]] || err "Aborted"

# Update /etc/hosts
cat > /etc/hosts << EOF
127.0.0.1       localhost
127.0.1.1       ${FQDN} ${NODE_NAME}
${RAC_IP}       ${FQDN} ${NODE_NAME}
${DNS}          EXADCS${SITE_CODE}001.jukebox.internal EXADCS${SITE_CODE}001
EOF
ok "/etc/hosts updated"

# Update /etc/resolv.conf
cat > /etc/resolv.conf << EOF
domain jukebox.internal
search jukebox.internal
nameserver ${DNS}
EOF

# Prevent dhclient overwriting resolv.conf
mkdir -p /etc/dhcp/dhclient-enter-hooks.d
echo 'make_resolv_conf() { :; }' > /etc/dhcp/dhclient-enter-hooks.d/nodnsupdate
chmod +x /etc/dhcp/dhclient-enter-hooks.d/nodnsupdate
ok "DNS configured → $DNS"

# ════════════════════════════════════════════════════════════
# 3. BMC profile selection
# ════════════════════════════════════════════════════════════
heading "BMC Profile Selection"

echo "Available mockup profiles:"
echo ""
echo "  1) DL360           — ProLiant DL360 Gen10 Plus"
echo "  2) DL380a          — ProLiant DL380a Gen11 (2x Nvidia H100 NVL)"
echo "  3) DL380a_Gen12    — ProLiant DL380 Gen12 (4x Nvidia H200 NVL)"
echo "  4) DL360_Gen12     — ProLiant DL360 Gen12"
echo "  5) DL365_Gen10Plus — ProLiant DL365 Gen10 Plus (w/ HBA)"
echo "  6) DL325_Gen10Plus_FC — ProLiant DL325 Gen10 Plus (w/ FC)"
echo ""
read -rp "Select profile [1-6]: " PROFILE_CHOICE

case "$PROFILE_CHOICE" in
    1) MOCKUP_FOLDER="DL360" ;;
    2) MOCKUP_FOLDER="DL380a" ;;
    3) MOCKUP_FOLDER="DL380a_Gen12" ;;
    4) MOCKUP_FOLDER="DL360_Gen12" ;;
    5) MOCKUP_FOLDER="DL365_Gen10Plus" ;;
    6) MOCKUP_FOLDER="DL325_Gen10Plus_FC" ;;
    *) err "Invalid selection" ;;
esac

ok "Profile: $MOCKUP_FOLDER"

# ════════════════════════════════════════════════════════════
# 4. Install dependencies
# ════════════════════════════════════════════════════════════
heading "Installing Dependencies"

apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl \
    wget \
    openssl \
    ca-certificates \
    ufw \
    molly-guard

ok "System packages installed"

# Ansible user
if ! id ansible &>/dev/null; then
    useradd -m -s /bin/bash ansible
    echo "ansible ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ansible
    chmod 0440 /etc/sudoers.d/ansible
fi

mkdir -p /home/ansible/.ssh
chmod 700 /home/ansible/.ssh
wget -qO - http://192.168.139.50/ansible_sshkey.pub \
    >> /home/ansible/.ssh/authorized_keys
chmod 600 /home/ansible/.ssh/authorized_keys
chown -R ansible:ansible /home/ansible/.ssh
ok "Ansible user configured"

# ════════════════════════════════════════════════════════════
# 5. Clone and install emulator
# ════════════════════════════════════════════════════════════
heading "Installing iLO Redfish Emulator"

INSTALL_DIR="/opt/rac-emulator"
REPO_URL="https://github.com/HewlettPackard/ilo-redfish-emulator"

if [[ -d "$INSTALL_DIR" ]]; then
    warn "$INSTALL_DIR exists — pulling latest"
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

ok "Repository at $INSTALL_DIR"

# Create virtualenv and install Python deps
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r "$INSTALL_DIR/src/requirements.txt" \
    2>/dev/null || \
"$INSTALL_DIR/venv/bin/pip" install --quiet flask flask-restful

ok "Python virtualenv ready"

# ════════════════════════════════════════════════════════════
# 6. TLS certificate (self-signed, matching iLO behaviour)
# ════════════════════════════════════════════════════════════
heading "TLS Certificate"

CERT_DIR="/opt/rac-emulator/certs"
mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$CERT_DIR/rac.key" \
    -out    "$CERT_DIR/rac.crt" \
    -days   3650 \
    -subj   "/C=GB/ST=Scotland/L=Falkirk/O=Example Music Group/CN=${FQDN}" \
    -addext "subjectAltName=DNS:${FQDN},DNS:${NODE_NAME},IP:${RAC_IP}" \
    2>/dev/null

chmod 600 "$CERT_DIR/rac.key"
ok "Self-signed certificate generated for $FQDN"

# ════════════════════════════════════════════════════════════
# 7. Per-site config file
# ════════════════════════════════════════════════════════════
heading "Generating Per-Site Config"

CONFIG_FILE="/opt/rac-emulator/rac-${SITE_CODE}.conf"

cat > "$CONFIG_FILE" << EOF
# RAC Emulator Configuration — ${NODE_NAME}
# Generated by rac-setup.sh on $(date +%Y-%m-%d)
# Do not edit manually — re-run rac-setup.sh to regenerate

NODE_NAME=${NODE_NAME}
FQDN=${FQDN}
SITE_CODE=${SITE_CODE}
SITE_OCTET=${OCTET}
RAC_IP=${RAC_IP}
MOCKUP_FOLDER=${MOCKUP_FOLDER}
EXTERNAL_PORT=443
CERT_DIR=${CERT_DIR}
INSTALL_DIR=${INSTALL_DIR}
EOF

ok "Config written to $CONFIG_FILE"

# ════════════════════════════════════════════════════════════
# 8. Systemd service
# ════════════════════════════════════════════════════════════
heading "Creating systemd Service"

SERVICE_FILE="/etc/systemd/system/rac-emulator.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=jukebox.internal RAC Emulator (${NODE_NAME})
Documentation=https://github.com/HewlettPackard/ilo-redfish-emulator
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/src
EnvironmentFile=${CONFIG_FILE}
Environment="MOCKUP_FOLDER=${MOCKUP_FOLDER}"
Environment="EXTERNAL_PORT=443"
ExecStart=${INSTALL_DIR}/venv/bin/python3 emulator.py \
    --ssl-cert ${CERT_DIR}/rac.crt \
    --ssl-key  ${CERT_DIR}/rac.key
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=rac-emulator

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable rac-emulator
systemctl start  rac-emulator

sleep 2

if systemctl is-active --quiet rac-emulator; then
    ok "rac-emulator service running"
else
    warn "Service may not have started — check: journalctl -u rac-emulator -n 50"
fi

# ════════════════════════════════════════════════════════════
# 9. Firewall
# ════════════════════════════════════════════════════════════
heading "Configuring Firewall"

ufw --force reset > /dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment "SSH"
ufw allow 443/tcp  comment "iLO Redfish HTTPS"
ufw --force enable
ok "UFW configured — ports 22 and 443 open"

# ════════════════════════════════════════════════════════════
# 10. Summary
# ════════════════════════════════════════════════════════════
heading "Setup Complete"

echo -e "  ${BOLD}Node:${RESET}        $NODE_NAME"
echo -e "  ${BOLD}FQDN:${RESET}        $FQDN"
echo -e "  ${BOLD}IP:${RESET}          $RAC_IP (next free BMC pool slot)"
echo -e "  ${BOLD}Profile:${RESET}     $MOCKUP_FOLDER"
echo -e "  ${BOLD}Web UI:${RESET}      https://${RAC_IP}/redfish/v1/"
echo -e "  ${BOLD}Credentials:${RESET} root / root_password"
echo -e "  ${BOLD}Config:${RESET}      $CONFIG_FILE"
echo -e "  ${BOLD}Service:${RESET}     systemctl status rac-emulator"
echo ""
echo -e "${YELLOW}Network inventory note:${RESET}"
echo -e "  Add ${RAC_IP} as ${NODE_NAME} in network-inventory.md"
echo -e "  BMC pool convention: .2/.3/.4 shared between physical BMCs and RAC VM"
echo -e "  RAC takes next free slot after physical PVE node BMCs"
echo ""
echo -e "${YELLOW}Quick test:${RESET}"
echo -e "  curl -sk https://${RAC_IP}/redfish/v1/ | python3 -m json.tool | head -20"
echo ""
ok "EXARAC${SITE_CODE}${INSTANCE} is ready"
