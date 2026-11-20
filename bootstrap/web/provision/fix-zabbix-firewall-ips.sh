#!/usr/bin/env bash
# ==============================================================================
# Example Music Limited — Correct a firewall's Zabbix interface IP (LAN, not WAN)
# Run on EXAZABCLD001 (or any Zabbix server), as a user with API-admin credentials
# ==============================================================================
# Mirrors the style and structure of ansibleme.sh/firewallme.sh/zabbixme.sh —
# interactive, idempotent, site-code-driven (reads /etc/example-music/sites.csv,
# same source of truth every other script in this family uses, not a second
# hand-maintained host list) — but this one is a FIX tool, not a bootstrap tool:
# it corrects already-registered Zabbix hosts, it doesn't provision anything.
#
# BACKGROUND (INC-2026-11-20-FWL-WAN-TRUST, see docs/INCIDENT-LOG.md): every
# firewall's Zabbix host interface was registered against
# ansible_default_ipv4.address, which on a firewall always resolves to the WAN
# NIC (that's where the default route lives) — not the LAN IP. That's wrong on
# its own (monitoring traffic should stay on the tunnel like every other
# internal-LAN path), and it was *also* the reason a risky WireGuard
# AllowedIPs workaround existed at all. ansible/tasks/zabbix_agent_onboard.yml
# now fixes this going forward for any host that runs linux/tools.yml again —
# this script exists for the same correction without waiting for that, e.g.
# while a firewall's own Ansible access is still broken (the exact situation
# that incident started in) or for a quick one-shot pass across the whole
# estate.
#
# What it does: for every real firewall site in sites.csv (same exclusions as
# heal-hub-allowedips.yml: skip BRD and any row with Subnet=N/A), checks
# EXAFWL<SITE>001's registered Zabbix interface IP; if it's not already the
# site's real LAN IP (192.168.<site-octet>.253, the fixed convention), corrects
# it via hostinterface.update. Already-correct and not-yet-registered hosts
# are reported and skipped, never written to.
#
# Needs: jq (JSON parsing), curl, and a Zabbix user with API access (the
# dedicated automation token used elsewhere in this repo is deliberately NOT
# reused here — this is a human-run, one-off correction tool, not something
# the Ansible/Zabbix integration itself calls).
#
# Usage:
#   ./fix-zabbix-firewall-ips.sh
#   SITES_CSV=/path/to/sites.csv ./fix-zabbix-firewall-ips.sh   # override path
#
# -------------------------------------------------------------------------------------------------
# Version history
# -------------------------------------------------------------------------------------------------
# v1.0.0  2026-11-20  Initial release. Robert's ask, same day as
#                     INC-2026-11-20-FWL-WAN-TRUST — promoted from an ad-hoc
#                     script (hardcoded host list) into this repo's official
#                     break-glass family, now sites.csv-driven instead of a
#                     hand-maintained list that would go stale as sites are
#                     added or removed.
# ==============================================================================

set -euo pipefail

ZABBIX_URL="${ZABBIX_URL:-http://localhost/zabbix/api_jsonrpc.php}"
ZABBIX_USER="${ZABBIX_USER:-Admin}"
SITES_CSV="${SITES_CSV:-/etc/example-music/sites.csv}"

if [[ ! -r "$SITES_CSV" ]]; then
  echo "ERROR: can't read $SITES_CSV -- same manual-wget pattern as zabbixme.sh applies:" >&2
  echo "  wget http://<provisioning-server>/sites.csv -O /etc/example-music/sites.csv" >&2
  echo "or override the path: SITES_CSV=/path/to/sites.csv $0" >&2
  exit 1
fi

read -r -s -p "Zabbix password for ${ZABBIX_USER}: " ZABBIX_PASS; echo

TOKEN=$(curl -s "$ZABBIX_URL" -H 'Content-Type: application/json-rpc' -d @- <<EOF | jq -r '.result'
{"jsonrpc":"2.0","method":"user.login","params":{"username":"$ZABBIX_USER","password":"$ZABBIX_PASS"},"id":1}
EOF
)

if [[ "$TOKEN" == "null" || -z "$TOKEN" ]]; then
  echo "Login failed, check username/password." >&2
  exit 1
fi

# Site,City,Country,CountryCode,Province,OfficeName,Street,PostalCode,Subnet,... --
# only Site (col 1) and Subnet (col 9) are needed; same exclusions
# heal-hub-allowedips.yml already uses (skip BRD, skip any N/A-subnet row).
while IFS=, read -r site _city _country _cc _province _office _street _postal subnet _rest; do
  [[ "$site" == "Site" ]] && continue   # header
  [[ "$site" == "BRD" ]] && continue
  [[ "$subnet" == "N/A" ]] && continue

  octet="$(echo "$subnet" | cut -d. -f3)"
  [[ -z "$octet" ]] && continue

  host="EXAFWL${site}001"
  lan_ip="192.168.${octet}.253"

  result=$(curl -s "$ZABBIX_URL" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json-rpc' -d @- <<EOF
{"jsonrpc":"2.0","method":"host.get","params":{"filter":{"host":["$host"]},"selectInterfaces":["interfaceid","ip"]},"id":1}
EOF
)

  iface_id=$(echo "$result" | jq -r '.result[0].interfaces[0].interfaceid // empty')
  current_ip=$(echo "$result" | jq -r '.result[0].interfaces[0].ip // empty')

  if [[ -z "$iface_id" ]]; then
    echo "$host: not found in Zabbix, skipping"
    continue
  fi

  if [[ "$current_ip" == "$lan_ip" ]]; then
    echo "$host: already correct ($lan_ip)"
    continue
  fi

  curl -s "$ZABBIX_URL" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json-rpc' -d @- <<EOF >/dev/null
{"jsonrpc":"2.0","method":"hostinterface.update","params":{"interfaceid":"$iface_id","ip":"$lan_ip"},"id":1}
EOF
  echo "$host: $current_ip -> $lan_ip"
done < "$SITES_CSV"
