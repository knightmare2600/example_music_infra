#!/bin/bash
# Retrofit MOTD script — paste and run on existing firewalls
# Usage: sudo bash retrofit_motd.sh

cat > /etc/update-motd.d/10-examplemusic <<'MOTD'
#!/bin/bash
# Example Music — dynamic login banner

# Colours
GR='\033[0;32m'   # green
CY='\033[0;36m'   # cyan
RD='\033[0;31m'   # red
YL='\033[0;33m'   # yellow
OR='\033[38;5;208m' # orange
WH='\033[1;37m'   # white bold
NC='\033[0m'      # reset

# Read node info
SITE="unknown"; WG_ROLE="none"; ENTITY=""; CITY=""; COUNTRY=""
if [[ -f /etc/example-music/nodeinfo.json ]] && command -v jq &>/dev/null; then
  SITE=$(   jq -r '.site    // "unknown"' /etc/example-music/nodeinfo.json)
  WG_ROLE=$(jq -r '.wg_role // "none"'   /etc/example-music/nodeinfo.json)
  ENTITY=$( jq -r '.entity  // ""'       /etc/example-music/nodeinfo.json)
  CITY=$(   jq -r '.city    // ""'       /etc/example-music/nodeinfo.json)
  COUNTRY=$(jq -r '.country // ""'       /etc/example-music/nodeinfo.json)
fi

# Collect interface info
WAN_INFO=""
LAN_INFO=""
WG_INFO=""

while IFS= read -r iface; do
  IP=$(ip -4 addr show "$iface" 2>/dev/null | awk '/inet /{print $2}' | head -1)
  [[ -z "$IP" ]] && IP="no IP"
  case "$iface" in
    wg*)  WG_INFO="${WG_INFO}    ${OR}WireGuard ${iface}${NC} : ${OR}${IP}${NC}\n" ;;
    lo)   continue ;;
    *)
      if ip route show dev "$iface" 2>/dev/null | grep -q "^default"; then
        WAN_INFO="${WAN_INFO}    ${RD}WAN  ${iface}${NC} : ${RD}${IP}${NC}\n"
      elif [[ -n "$IP" ]]; then
        LAN_INFO="${LAN_INFO}    ${GR}LAN  ${iface}${NC} : ${GR}${IP}${NC}\n"
      fi
      ;;
  esac
done < <(ip -o link show | awk -F': ' '{print $2}' | grep -v '@')

# WireGuard peer table
WG_PEERS=""
if command -v wg &>/dev/null && ip link show wg0 &>/dev/null 2>&1; then
  WG_PEERS="  ${WH}── WireGuard Peers ──────────────────────────────────────────${NC}\n"
  PEER_COUNT=0
  ACTIVE_COUNT=0
  NOW=$(date +%s)
  while IFS=$'\t' read -r PUBKEY PRESHARED ENDPOINT ALLOWED HANDSHAKE TX RX KEEPALIVE; do
    PEER_COUNT=$((PEER_COUNT + 1))

    PEER_NAME=$(awk -v pk="$PUBKEY" '
      /^#/ { comment = substr($0, 3) }
      /PublicKey/ && $3 == pk { print comment; exit }
    ' /etc/wireguard/wg0.conf 2>/dev/null)
    PEER_NAME="${PEER_NAME:-???}"

    EP_IP="${ENDPOINT%%:*}"
    [[ "$EP_IP" == "(none)" ]] && EP_IP="no endpoint"

    ALLOWED_DISP=$(echo "$ALLOWED" | cut -d',' -f1 | xargs)

    if [[ "$HANDSHAKE" == "0" ]]; then
      HS_STR="${RD}never${NC}"
      STATUS="${RD}✗${NC}"
    else
      AGE=$((NOW - HANDSHAKE))
      if   [[ $AGE -lt 60 ]];    then HS_STR="${GR}${AGE}s ago${NC}"
      elif [[ $AGE -lt 3600 ]];  then HS_STR="${GR}$((AGE/60))m ago${NC}"
      elif [[ $AGE -lt 86400 ]]; then HS_STR="${YL}$((AGE/3600))h ago${NC}"
      else                             HS_STR="${RD}$((AGE/86400))d ago${NC}"
      fi
      if [[ $AGE -lt 180 ]]; then
        STATUS="${GR}✓${NC}"
      else
        STATUS="${YL}~${NC}"
      fi
      ACTIVE_COUNT=$((ACTIVE_COUNT + 1))
    fi

    fmt_bytes() {
      local b=$1
      if   [[ $b -ge 1073741824 ]]; then printf "%.1fG" "$(echo "scale=1; $b/1073741824" | bc)"
      elif [[ $b -ge 1048576 ]];   then printf "%.1fM" "$(echo "scale=1; $b/1048576"   | bc)"
      elif [[ $b -ge 1024 ]];      then printf "%.1fK" "$(echo "scale=1; $b/1024"      | bc)"
      else printf "${b}B"; fi
    }
    TX_STR=$(fmt_bytes "$TX")
    RX_STR=$(fmt_bytes "$RX")

    WG_PEERS="${WG_PEERS}    ${STATUS} ${CY}$(printf '%-12s' "$PEER_NAME")${NC}"
    WG_PEERS="${WG_PEERS} ${GR}$(printf '%-18s' "$ALLOWED_DISP")${NC}"
    WG_PEERS="${WG_PEERS} ${WH}$(printf '%-18s' "$EP_IP")${NC}"
    WG_PEERS="${WG_PEERS} ${HS_STR}  ${YL}↑${TX_STR} ↓${RX_STR}${NC}\n"

  done < <(wg show wg0 dump 2>/dev/null | tail -n +2)

  WG_PEERS="${WG_PEERS}    ${CY}Total${NC}: ${GR}${ACTIVE_COUNT}${NC} active of ${PEER_COUNT} configured\n"
fi

# System info
UPTIME=$(uptime -p 2>/dev/null | sed 's/up //')
LOAD=$(cut -d' ' -f1-3 /proc/loadavg)
MEM_TOTAL=$(free -m | awk '/^Mem/{print $2}')
MEM_USED=$(free -m  | awk '/^Mem/{print $3}')
DISK=$(df -h / | awk 'NR==2{print $3 " used of " $2 " (" $5 ")"}')
LAN_IP=$(ip -4 addr show | awk '/inet /{print $2}' | grep -v '127\.' | grep -v '10\.0\.' | tail -1 | cut -d/ -f1)

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

${WH}╔══════════════════════════════════════════════════════════════╗${NC}
${WH}║              EXAMPLE MUSIC LIMITED: $(printf '%-24s' "${HOSTNAME}")║${NC}
${WH}╚══════════════════════════════════════════════════════════════╝${NC}

  ${YL}Site     :${NC} ${SITE}: ${CITY}, ${COUNTRY}
  ${YL}Entity   :${NC} ${ENTITY}
  ${YL}WG Role  :${NC} ${WG_ROLE}

  ${WH}── Network ──────────────────────────────────────────────────${NC}
$(echo -e "${WAN_INFO}${LAN_INFO}${WG_INFO}" | grep -v '^$')

$(echo -e "${WG_PEERS}" | grep -v '^$')

  ${WH}── System ───────────────────────────────────────────────────${NC}
    ${CY}Uptime${NC}   : ${GR}${UPTIME}${NC}
    ${CY}Load${NC}     : ${GR}${LOAD}${NC}
    ${CY}Memory${NC}   : ${GR}${MEM_USED}MB${NC} used of ${MEM_TOTAL}MB
    ${CY}Disk /   ${NC}: ${GR}${DISK}${NC}

  ${WH}── Management ───────────────────────────────────────────────${NC}
    ${CY}Cockpit${NC}  : ${GR}https://${LAN_IP}:9090${NC}
"
MOTD

chmod +x /etc/update-motd.d/10-examplemusic
echo "Done — testing MOTD:"
echo
run-parts /etc/update-motd.d/
