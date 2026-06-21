#!/bin/bash
# =============================================================================
# Arch Linux PXE Auto-Install Bootstrap
# Example Music Limited
#
# Fetched and run by the archiso live environment after network comes up.
# Drops a systemd service that runs archinstall with config from the
# provisioning server.
#
# Provisioning server: http://192.168.139.50
# Config:  http://192.168.139.50/arch/archinstall-config.json
#
# This script is referenced by the arch-autoinstall systemd service which
# is injected via the archiso copytoram mechanism.
# =============================================================================
set -euo pipefail

PROV="http://192.168.139.50"
CONFIG_URL="${PROV}/arch/archinstall-config.json"
WORK_DIR="/root/archinstall-work"

echo "============================================"
echo "  Example Music -- Arch Linux Auto-Install"
echo "============================================"
echo ""

mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

echo "[*] Fetching archinstall config..."
curl -fsSL -o config.json "${CONFIG_URL}" || {
  echo "[X] Failed to fetch config from ${CONFIG_URL}"
  echo "    Check provisioning server is reachable."
  exit 1
}

echo "[*] Fetching archinstall credentials..."
echo "[+] Config fetched."
echo ""
echo "[*] Starting archinstall..."
echo "    You will be prompted for:"
echo "      - Hostname"
echo "      - Ansible user password"
echo "      - Root password"
echo ""

archinstall --config "${WORK_DIR}/config.json"

echo ""
echo "[+] archinstall complete."

# Shred credentials from RAM before reboot

echo "[*] Rebooting in 10 seconds..."
sleep 10
reboot
