#!/usr/bin/env bash
# ===============================================================
# Debian VMware Router Setup Script
# - LAN/WAN NM profiles
# - DHCP with dnsmasq (iPXE vendor class tagging)
# - NAT + forwarding via nftables
# - Cockpit (latest, via cockpit-project repo) bound to LAN only
# - WireGuard hub-primary / hub-regional / spoke setup
# - Site code lookup for automatic subnet assignment
# ===============================================================

set -euo pipefail

# Suppress all apt/dpkg interactive prompts
export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

# Changelog:
#  2026-03-28  WAN mode prompt added -- DHCP (default) or static. WAN IP derived from site CSV
#              octet (192.168.139.<octet>). ip_in_use() collision check from first-boot.sh. NM
#              connection creation updated to handle both modes.
#  2026-03-28  BRK placeholder added -- HUB_KNOWN_PUBKEY[BRK] and HUB_WAN_IP[BRK] marked as TODO,
#              populate after BRK build (week of 2026-04-07).
#  2026-03-28  AllowedIPs now topology-aware; spokes get full cross-hub subnet list, wg-quick adds
#              correct kernel routes at boot. Add hub topology map (FAL/ODE/BRK & spokes). BRK
#              added to HUB_KNOWN_PUBKEY & HUB_WAN_IP tables. ODE WAN IP fix to 192.168.139.126.
#  2026-03-01  Load site data from sites.csv instead of hardcoded arrays. Place CSV alongside this
#              script or set SITES_CSV=/path/to/sites.csv
#  2026-04-17  NetworkManager activation sequence hardened: replaced multiple nmcli con up calls
#              with explicit wait logic to prevent DHCP race conditions on WAN. WAN now brought up
#              first & polled for carrier & IP before LAN activation. Reduces intermittent flub if
#              LAN starts before WAN DHCP completes.
#  2026-04-24  Brockville, Ontario, Canada Wireguard key added
#  2026-04-25  Fix SITE_DISPLAY_* uninitialised in manual site path. Remove stale DEBUG log line in
#              load_sites_csv(). Fix NM activation order: wait_for_wan() now called before LAN is
#              brought up, not after. Fix WG_BACKUP_PEERS[@] expansion under set -u use parameter
#              expansion guard instead of invalid :- on array. Fix zsh plugin presence checks: use
#              dpkg -s, not command -v, as they are files not executables. Fix WAN_IP re-assignment
#              in spoke banner block; reuse WAN_IP_CURRENT consistency. Add WAN activation prompt
#              (default N), running via SSH can skip nmcli con up wan & avoid dropping the session.
#  2026-05-21  Hardening pass brings deferred execution for SSH inpacting reloads. nmcli, nftables,
#              dnsmasq & Cockpit start/restart are now gated via WAN activation state.
#              Removed instant nmcli restart from ifupdown cleanup, WAN reconfig blocks replaced by
#              NM_RESTART_REQUIRED/NM_PENDING deferred apply flags, nftables guarded against SSH
#              session drop, checking current interface before restart; commit is deferred if WAN
#              policy conflicts with active SSH session, dnsmasq/systemd-resolved restart decoupled
#              from config write, avoids DNS/DHCP disruption during interface transition. defer
#              cockpit socket binding until network ready, avoids bind to unstable/non-existent LAN
#              IP. SSH banner now skips SSH restart. Sentinel file fix. Add ENV_LONG for full env
#              traceability across script runs.
#  2026-06-14  A number of produciton-tested bug fixes:
#              1. load_sites_csv() while-read loop dropped the last CSV line when the file had no
#                 trailing newline (read returns non-zero on EOF without \n, so loop exited before
#                 processing that iteration). VIE is the last line in sites.csv & has no trailing
#                 newline, so never loads into SITE_OCTET[] causing "Unknown site code VIE" at run.
#                 Fixed with || [[ -n "$site" ]] on the while condition.
#              2. warn() writes to stderr (>&2). Previously warn() wrote to stdout, warn() calls
#                 inside $() subshell, e.g. build_allowed_ips had output captured into the vars &
#                 written into wg0.conf. This Is the root cause of 'Vienna has no subnet' issue.
#                 appearing inside [Peer] blocks — the warn text was the AllowedIPs value.
#              3. Ansible user is created before zsh block; useradd -m -s /bin/bash -G sudo ansible
#                 is run idempotently (guarded by id -u). Previously getent was empty, ANSIBLE_HOME
#                 wass unset & the entire zsh block silently skipped, so chsh was never called.
#              4. chsh for ansible user moved outside the .zshrc-existence guard so the login shell
#                 is always set to zsh even on re-runs where .zshrc already exists.
#              5. nmcli con add calls for both wan & lan now include connection.autoconnect yes &
#                 connection.autoconnect-priority 100. Without these, NM can silently skip profiles
#                 on boot or bring up a stale unconfigured profile instead.
#              6. NM_RESTART_REQUIRED set when managed=false was fixed, but never consumed — NM was
#                 never restarted so profile changes were not applied to the live daemon & didn't
#                 survive reboots. Flag now consumed after nmcli con up lan via systemctl restart &
#                 re-raise, ONLY if WAN_ACTIVATE=true. On SSH (WAN_ACTIVATE=false), defer restart &
#                 console instruction printed instead: NM restarts via SSH drop session instantly.
#              7. wg-quick@wg0 systemd drop-in addition: Wants=network-online.target. The shipped
#                 unit only has After=network.target which is satisfied before any interface has an
#                 IP, causing wg-quick to fail endpoint resolution on boot.

# -------------------------------------------------------------------------------------------------
# Colour helpers
# -------------------------------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; ORANGE='\033[38;5;208m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[*]${NC} $*"; }
success() { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*" >&2; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
step()    { echo -e "${CYAN}[→]${NC} $*"; }

# -------------------------------------------------------------------------------------------------
# Site data -- loaded from sites.csv (single source of truth). To add or change a site, edit
# sites.csv -- no code changes needed.
#
# Looks for sites.csv in:
#   1. $SITES_CSV environment variable (override)
#   2. Same directory as this script
#   3. /etc/example-music/sites.csv (system-wide install)
# -------------------------------------------------------------------------------------------------
declare -A SITE_OCTET SITE_CITY SITE_COUNTRY SITE_ENTITY SITE_DEFAULT_ROLE

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

  # BUG FIX: `while read` silently drops the last line of a file that has no trailing newline (read
  # returns non-zero so the loop exits before processing that iteration). The || [[ -n "$site" ]]
  # guard catches that final partial read and processes it normally.
  while IFS=',' read -r site city country cc subnet gateway dc fw landline mobile tz ansible_region entity rest || [[ -n "$site" ]]; do
    [[ "${first}" -eq 1 ]] && { first=0; continue; }

    site="${site// /}"
    [[ -z "${site}" ]] && continue

    ## FIX: handle commas inside Entity field
    if [[ -n "$rest" ]]; then
      entity="${entity},${rest}"
    fi

    local octet
    octet=$(echo "${subnet}" | awk -F'.' '{print $3}')

    SITE_OCTET["${site}"]="${octet}"
    SITE_CITY["${site}"]="${city}"
    SITE_COUNTRY["${site}"]="${country}"
    SITE_ENTITY["${site}"]="${entity}"
  done < "${csv_path}"


}

load_sites_csv

# Known hub public keys and endpoints — used for verification ONLY, never written to configs
# directly. The script always fetches live from the hub & asks the user to confirm. These are a
# last-resort fallback reference.
declare -A HUB_KNOWN_PUBKEY=(
  [FAL]="yxYnCsZwxDmv6WrduGTC7pnW3sUxob1GGYpttPfGbmk="
  [ODE]="gFK4oQNKN/a2UZvoil43OvOcjp2B6gT4YQ8IUqWrZ1o="
  [BRK]="CSpL1NJl4jgeJDf6TccixMGv8JOSH7XS7pErjKSuoT4="
)
declare -A HUB_WAN_IP=(
  [FAL]="192.168.139.76"
  [ODE]="192.168.139.126"
  [BRK]="192.168.139.136"
)

# -------------------------------------------------------------------------------------------------
# Hub topology -- which spokes belong to which hub. Used to build topology-aware AllowedIPs so
# wg-quick injects correct kernel routes for all cross-hub destinations at boot.
# -------------------------------------------------------------------------------------------------
# UK spokes -- connect directly to FAL
HUB_FAL_SPOKES=(ABD BIR CLY COV DUN EDI GLA HAL HUL LIV LND MCR NEW PER SHE)
# EU spokes -- connect directly to ODE
HUB_ODE_SPOKES=(AMS BON CPH FAX GOT KGE KOR MIL MUN OSL VIE)
# AMAPAC spokes -- connect directly to BRK
HUB_BRK_SPOKES=(ATL CHI LAX MIA MTL NJC NYC TOR AKL MEL SYD)

# Build comma-separated AllowedIPs for a list of site codes
# Usage: build_allowed_ips SITE1 SITE2 ...
# Returns: "10.0.X.0/24, 192.168.X.0/24, 10.0.Y.0/24, ..." (no trailing comma)
build_allowed_ips() {
  local result=""
  for code in "$@"; do
    local octet="${SITE_OCTET[$code]:-}"
    [[ -z "$octet" ]] && warn "Missing octet for site ${code}"
    [[ -z "$octet" ]] && continue
    [[ -n "$result" ]] && result+=", "
    result+="10.0.${octet}.0/24, 192.168.${octet}.0/24"
  done
  echo "$result"
}

spoke_allowed_ips_for_hub() {
  local hub="$1"
  local parts=()
  local tmp

  case "$hub" in
    FAL)
      # Via FAL: FAL + UK + ODE + EU + BRK + AMAPAC
      tmp=$(build_allowed_ips FAL "${HUB_FAL_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")

      tmp=$(build_allowed_ips ODE "${HUB_ODE_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")

      tmp=$(build_allowed_ips BRK "${HUB_BRK_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")
      ;;

    ODE)
      # Via ODE: ODE + EU + FAL + UK + BRK + AMAPAC
      tmp=$(build_allowed_ips ODE "${HUB_ODE_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")

      tmp=$(build_allowed_ips FAL "${HUB_FAL_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")

      tmp=$(build_allowed_ips BRK "${HUB_BRK_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")
      ;;

    BRK)
      # Via BRK: BRK + AMAPAC + FAL + UK + ODE + EU
      tmp=$(build_allowed_ips BRK "${HUB_BRK_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")

      tmp=$(build_allowed_ips FAL "${HUB_FAL_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")

      tmp=$(build_allowed_ips ODE "${HUB_ODE_SPOKES[@]}")
      [[ -n "$tmp" ]] && parts+=("$tmp")
      ;;

    *)
      # Unknown hub — fall back to just the hub's own subnets
      local octet="${SITE_OCTET[$hub]:-}"
      [[ -n "$octet" ]] && echo "10.0.${octet}.0/24, 192.168.${octet}.0/24"
      return
      ;;
  esac

  # Join parts cleanly
  local joined=""
  for part in "${parts[@]}"; do
    [[ -z "$part" ]] && continue
    [[ -n "$joined" ]] && joined+=", "
    joined+="$part"
  done

  echo "$joined"
}

# -------------------------------------------------------------------------------------------------
# Ensure correct environment. Default to production if unsure
# -------------------------------------------------------------------------------------------------
ENV_LONG=""

if [[ -s /etc/.environment ]]; then
  ENV_LONG="$(cat /etc/.environment)"

  if [[ -z "$ENV_LONG" ]]; then
    warn "/etc/.environment is empty — defaulting to production"
    ENV_LONG="production"
  else
    info "Environment loaded from file: ${ENV_LONG}"
  fi

else
  read -rp "Environment ((p)roduction, (s)taging, (d)evelopment) [default: production]: " ENV
  ENV="${ENV,,}"

  case "$ENV" in
    p) ENV_LONG="production" ;;
    s) ENV_LONG="staging" ;;
    d) ENV_LONG="development" ;;
    "" | * )
      warn "Invalid or empty input — defaulting to production"
      ENV_LONG="production"
      ;;
  esac

  echo "$ENV_LONG" > /etc/.environment
  success "Environment set to: ${ENV_LONG}"
fi

# -------------------------------------------------------------------------------------------------
# IP collision detection (lifted from first-boot.sh)
# -------------------------------------------------------------------------------------------------
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

# -------------------------------------------------------------------------------------------------
# Avoid nmcli and DHCP having fisticuffs
# -------------------------------------------------------------------------------------------------
wait_for_wan() {
  local iface="$1"
  local timeout=30
  local i ip

  info "Waiting for ${iface} to be fully online..."

  for ((i=1; i<=timeout; i++)); do
    ip=$(nmcli -g IP4.ADDRESS dev show "$iface" | head -1 | cut -d/ -f1)

    # Must have:
    # 1. IP address
    # 2. Default route via this iface
    # 3. Device state = connected
    if [[ -n "$ip" ]] \
       && ip route | grep -q "^default .* ${iface}" \
       && nmcli -t -f DEVICE,STATE dev | grep -q "^${iface}:connected"; then

      success "${iface} is up with IP ${ip}"
      return 0
    fi

    sleep 1
  done

  warn "${iface} did not come fully online in time"
  return 1
}

# -------------------------------------------------------------------------------------------------
# Must run as root
# -------------------------------------------------------------------------------------------------
[[ $EUID -ne 0 ]] && die "Run this script with sudo or as root."

# -------------------------------------------------------------------------------------------------
# Bootstrap
# -------------------------------------------------------------------------------------------------
info "Bootstrapping required tools..."
apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true
BOOTSTRAP_PKGS=()
command -v nmcli       &>/dev/null || BOOTSTRAP_PKGS+=(network-manager)
command -v nft         &>/dev/null || BOOTSTRAP_PKGS+=(nftables)
command -v ip          &>/dev/null || BOOTSTRAP_PKGS+=(iproute2)
command -v sysctl      &>/dev/null || BOOTSTRAP_PKGS+=(procps)
command -v conntrack   &>/dev/null || BOOTSTRAP_PKGS+=(conntrack)
command -v ifconfig    &>/dev/null || BOOTSTRAP_PKGS+=(net-tools)
command -v tmux        &>/dev/null || BOOTSTRAP_PKGS+=(tmux)
command -v dnsmasq     &>/dev/null || BOOTSTRAP_PKGS+=(dnsmasq)
command -v curl        &>/dev/null || BOOTSTRAP_PKGS+=(curl)
command -v wget        &>/dev/null || BOOTSTRAP_PKGS+=(wget)
command -v wg          &>/dev/null || BOOTSTRAP_PKGS+=(wireguard)
command -v grc         &>/dev/null || BOOTSTRAP_PKGS+=(grc)
command -v gpm         &>/dev/null || BOOTSTRAP_PKGS+=(gpm)
command -v nmap        &>/dev/null || BOOTSTRAP_PKGS+=(nmap)
command -v tcpdump     &>/dev/null || BOOTSTRAP_PKGS+=(tcpdump)
command -v bc          &>/dev/null || BOOTSTRAP_PKGS+=(bc)
command -v vim         &>/dev/null || BOOTSTRAP_PKGS+=(vim)
command -v bash-completion &>/dev/null || BOOTSTRAP_PKGS+=(bash-completion)
command -v zsh         &>/dev/null || BOOTSTRAP_PKGS+=(zsh)
# BUG FIX: zsh-autosuggestions and zsh-syntax-highlighting are shell plugin
# files, not executables -- command -v will never find them regardless of
# whether they are installed. Use dpkg -s instead.
dpkg -s zsh-autosuggestions     &>/dev/null || BOOTSTRAP_PKGS+=(zsh-autosuggestions)
dpkg -s zsh-syntax-highlighting &>/dev/null || BOOTSTRAP_PKGS+=(zsh-syntax-highlighting)
BOOTSTRAP_PKGS+=(cockpit cockpit-networkmanager)

if [[ ${#BOOTSTRAP_PKGS[@]} -gt 0 ]]; then
  info "Installing: ${BOOTSTRAP_PKGS[*]}"
  apt-get install -y -qq -o=Dpkg::Use-Pty=0 "${BOOTSTRAP_PKGS[@]}" > /dev/null
fi

info "Installing Cockpit Navigator..."
NAVIGATOR_DEB="/tmp/cockpit-navigator.deb"
if wget -q --timeout=30 -O "${NAVIGATOR_DEB}" https://github.com/45Drives/cockpit-navigator/releases/download/v0.5.10/cockpit-navigator_0.5.10-1focal_all.deb; then
  apt-get install -y -qq -o=Dpkg::Use-Pty=0 "${NAVIGATOR_DEB}" > /dev/null
  rm -f "${NAVIGATOR_DEB}"
  success "Cockpit Navigator installed."
else
  warn "Cockpit Navigator download failed — skipping. Install manually later."
  rm -f "${NAVIGATOR_DEB}"
fi

# -------------------------------------------------------------------------------------------------
# Purge unused locales
# -------------------------------------------------------------------------------------------------
info "Installing localepurge and stripping unused locales..."
debconf-set-selections << 'DEBCONF'
localepurge localepurge/nopurge multiselect en_GB.UTF-8, en_US.UTF-8
localepurge localepurge/verbose boolean false
localepurge localepurge/none_selected boolean false
localepurge localepurge/quickndirty boolean false
DEBCONF
apt-get install -y -qq -o=Dpkg::Use-Pty=0 localepurge > /dev/null
localepurge > /dev/null
success "Unused locales purged."

# -------------------------------------------------------------------------------------------------
# Slim down initramfs
# -------------------------------------------------------------------------------------------------
info "Configuring lean initramfs (VM firewall profile)..."
cat > /etc/initramfs-tools/conf.d/firewall.conf << 'EOF'
# Example Music — VM firewall initramfs profile
EOF

cat > /etc/modprobe.d/firewall-blacklist.conf << 'EOF'
blacklist snd
blacklist snd_pcm
blacklist snd_timer
blacklist soundcore
blacklist ac97_bus
blacklist ath9k
blacklist ath10k_core
blacklist brcmfmac
blacklist iwlwifi
blacklist rtl8xxxu
blacklist mt76
blacklist bluetooth
blacklist btusb
blacklist nouveau
blacklist radeon
blacklist amdgpu
blacklist i915
blacklist uvcvideo
blacklist pcspkr
EOF

KVER=$(uname -r)
info "Regenerating initramfs for kernel ${KVER}..."
update-initramfs -u -k "${KVER}" > /dev/null 2>&1
success "Lean initramfs generated."

# -------------------------------------------------------------------------------------------------
# Ansible user
# -------------------------------------------------------------------------------------------------
# BUG FIX: the ansible user was never created. getent returned empty so the entire zsh block was
# silently skipped & chsh was never called. Use id -u to check idempotently; create with a locked
# password so only key/sudo auth works. Shell is set to bash at creation; zsh is applied below.
if ! id -u ansible &>/dev/null; then
  info "Creating ansible system user..."
  useradd -m -s /bin/bash -G sudo ansible
  passwd -l ansible
  success "ansible user created."
else
  info "ansible user already exists — skipping creation."
fi

# -------------------------------------------------------------------------------------------------
# zsh setup
# -------------------------------------------------------------------------------------------------
ANSIBLE_HOME=$(getent passwd ansible | cut -d: -f6)
if [[ -n "$ANSIBLE_HOME" && ! -f "${ANSIBLE_HOME}/.zshrc" ]]; then
  info "Setting up zsh for ansible user..."
  cat > "${ANSIBLE_HOME}/.zshrc" <<'ZSHRC'
export TERM=xterm-256color
export EDITOR=vim
export VISUAL=vim
export SUDO_EDITOR=vim
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt appendhistory autocd extendedglob notify interactivecomments
setopt AUTO_CONTINUE
setopt LONG_LIST_JOBS
bindkey -e
autoload -Uz compinit && compinit
autoload -Uz colors && colors
bindkey "\e[1~"  beginning-of-line
bindkey "\e[4~"  end-of-line
bindkey "\e[H"   beginning-of-line
bindkey "\e[F"   end-of-line
bindkey "\eOH"   beginning-of-line
bindkey "\eOF"   end-of-line
bindkey "\e[1;5C" forward-word
bindkey "\e[1;5D" backward-word
bindkey "\e[5C"  forward-word
bindkey "\e[5D"  backward-word
bindkey "\e\e[C" forward-word
bindkey "\e\e[D" backward-word
bindkey "\e[3~"  delete-char
PROMPT='
%F{green}%m%f:%F{cyan}%~%f> '
alias ls='ls --color=auto'
alias ll='ls -lah'
alias grep='grep --color=auto'
if (( $+commands[grc] )); then
  GRC_ALIASES=true
  [[ -f /etc/profile.d/grc.sh ]] && source /etc/profile.d/grc.sh
fi
if [[ -f /usr/local/bin/server-prompts.zsh ]]; then
  source /usr/local/bin/server-prompts.zsh
fi
ZSHRC
  chown ansible:ansible "${ANSIBLE_HOME}/.zshrc"
  success "zsh .zshrc written for ansible user."
fi
# BUG FIX: chsh was inside the .zshrc-existence guard, if .zshrc already existed (e.g. re-run) the
# shell was never set. Run unconditionally with a valid home dir; chsh -s is idempotent.
if [[ -n "$ANSIBLE_HOME" ]]; then
  chsh -s "$(command -v zsh)" ansible
  success "ansible login shell set to zsh."
fi

if [[ ! -f /root/.zshrc ]]; then
  info "Setting up zsh for root..."
  cat > /root/.zshrc <<'ZSHRC'
export TERM=xterm-256color
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
export EDITOR=vim
export VISUAL=vim
export SUDO_EDITOR=vim
setopt appendhistory autocd extendedglob notify interactivecomments
setopt AUTO_CONTINUE
setopt LONG_LIST_JOBS
bindkey -e
autoload -Uz compinit && compinit
autoload -Uz colors && colors
bindkey "\e[1~"  beginning-of-line
bindkey "\e[4~"  end-of-line
bindkey "\e[H"   beginning-of-line
bindkey "\e[F"   end-of-line
bindkey "\eOH"   beginning-of-line
bindkey "\eOF"   end-of-line
bindkey "\e[1;5C" forward-word
bindkey "\e[1;5D" backward-word
bindkey "\e[5C"  forward-word
bindkey "\e[5D"  backward-word
bindkey "\e\e[C" forward-word
bindkey "\e\e[D" backward-word
bindkey "\e[3~"  delete-char
PROMPT='
%F{red}%m%f:%F{cyan}%~%f# '
alias ls='ls --color=auto'
alias ll='ls -lah'
alias grep='grep --color=auto'
if (( $+commands[grc] )); then
  GRC_ALIASES=true
  [[ -f /etc/profile.d/grc.sh ]] && source /etc/profile.d/grc.sh
fi
ZSHRC
  chsh -s "$(command -v zsh)" root
  success "zsh configured for root."
fi

# -------------------------------------------------------------------------------------------------
# 1. Interactive prompts
# -------------------------------------------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Example Music: Firewall/Router Setup         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}  Running on hostname: ${GREEN}$(hostname)${NC}"
echo

# ------------------------------------------------------------------------------------------------
# Interface detection — identify WAN by 192.168.139.x DHCP lease, write systemd .link files to pin
# names before NM takes over
# -------------------------------------------------------------------------------------------------
info "Detecting network interfaces..."

WAN_IFACE=""
WAN_MAC=""
LAN_IFACE=""
LAN_MAC=""

echo -e "${CYAN}Scanning interfaces for provisioning network (192.168.139.x)...${NC}"
for iface in $(ls /sys/class/net/); do
  [[ "$iface" == "lo" ]] && continue
  ip_addr=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet\s)192\.168\.139\.\d+' | head -1)
  if [[ -n "$ip_addr" ]]; then
    WAN_IFACE="$iface"
    WAN_MAC=$(cat "/sys/class/net/${iface}/address" 2>/dev/null)
    success "WAN interface detected: ${WAN_IFACE} (${ip_addr}, MAC: ${WAN_MAC})"
    break
  fi
done

echo -e "${CYAN}Available network interfaces:${NC}"
echo -e "${CYAN}──────────────────────────────────────────────────────────────${NC}"
for iface in $(ls /sys/class/net/); do
  [[ "$iface" == "lo" ]] && continue
  mac=$(cat "/sys/class/net/${iface}/address" 2>/dev/null) || mac="??:??:??:??:??:??"
  ip_addr=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}/\d+' | head -1) || ip_addr=""
  state=$(cat "/sys/class/net/${iface}/operstate" 2>/dev/null) || state="unknown"
  if [[ "$iface" == "$WAN_IFACE" ]]; then
    printf "  ${RED}%-14s${NC}  MAC: %s   IP: %-22s [%s] ← WAN\n" "$iface" "$mac" "${ip_addr:-(no address)}" "$state"
  elif [[ -n "$ip_addr" ]]; then
    printf "  ${GREEN}%-14s${NC}  MAC: %s   IP: %-22s [%s]\n" "$iface" "$mac" "$ip_addr" "$state"
  else
    printf "  ${YELLOW}%-14s${NC}  MAC: %s   IP: %-22s [%s]\n" "$iface" "$mac" "(no address)" "$state"
  fi
done
echo -e "${CYAN}──────────────────────────────────────────────────────────────${NC}"
echo

AVAILABLE_IFACES=($(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | grep -v '@'))

if [[ -z "$WAN_IFACE" ]]; then
  warn "Could not auto-detect WAN interface (no 192.168.139.x address found)."
  warn "This may mean the provisioning network is not reachable, or DHCP hasn't completed."
  while true; do
    read -rp "Enter the WAN interface name (default: ${AVAILABLE_IFACES[0]:-ens33}): " WAN_IFACE
    WAN_IFACE="${WAN_IFACE:-${AVAILABLE_IFACES[0]:-ens33}}"
    if ip link show "$WAN_IFACE" &>/dev/null; then
      WAN_MAC=$(cat "/sys/class/net/${WAN_IFACE}/address" 2>/dev/null)
      break
    fi
    warn "Interface '$WAN_IFACE' not found — available: ${AVAILABLE_IFACES[*]}"
  done
else
  read -rp "WAN interface is ${WAN_IFACE} — press Enter to confirm or type a different name: " WAN_OVERRIDE
  if [[ -n "$WAN_OVERRIDE" ]]; then
    if ip link show "$WAN_OVERRIDE" &>/dev/null; then
      WAN_IFACE="$WAN_OVERRIDE"
      WAN_MAC=$(cat "/sys/class/net/${WAN_IFACE}/address" 2>/dev/null)
    else
      warn "Interface '$WAN_OVERRIDE' not found — keeping ${WAN_IFACE}"
    fi
  fi
fi

[[ ${#AVAILABLE_IFACES[@]} -eq 0 ]] && die "No network interfaces detected."

LAN_CANDIDATES=($(printf '%s\n' "${AVAILABLE_IFACES[@]}" | grep -v "^${WAN_IFACE}$"))
LAN_DEFAULT="${LAN_CANDIDATES[0]:-ens34}"

echo
info "Remaining interfaces for LAN (WAN ${WAN_IFACE} excluded):"
for iface in "${LAN_CANDIDATES[@]}"; do
  IP=$(ip -4 addr show "$iface" 2>/dev/null | awk '/inet /{print $2}' | head -1)
  echo -e "    ${CYAN}${iface}${NC}  ${IP:-no IP}"
done
echo
read -rp "Enter the LAN interface name (default: ${LAN_DEFAULT}): " LAN_IFACE
LAN_IFACE="${LAN_IFACE:-${LAN_DEFAULT}}"
if [[ "$LAN_IFACE" == "$WAN_IFACE" ]]; then
  die "LAN and WAN cannot be the same interface."
fi
LAN_MAC=$(cat "/sys/class/net/${LAN_IFACE}/address" 2>/dev/null)

# -------------------------------------------------------------------------------------------------
# Write systemd .link files to pin NIC names by MAC. Survives reboots & VMware PCI bus shuffles
# -------------------------------------------------------------------------------------------------
info "Writing systemd .link files to pin interface names by MAC..."
mkdir -p /etc/systemd/network

cat > /etc/systemd/network/10-wan.link <<EOF
# Example Music — WAN interface pin
# Written by firewallme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# MAC: ${WAN_MAC}  was: ${WAN_IFACE}
[Match]
MACAddress=${WAN_MAC}
[Link]
Name=${WAN_IFACE}
EOF

cat > /etc/systemd/network/10-lan.link <<EOF
# Example Music — LAN interface pin
# Written by firewallme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# MAC: ${LAN_MAC}  was: ${LAN_IFACE}
[Match]
MACAddress=${LAN_MAC}
[Link]
Name=${LAN_IFACE}
EOF

success "Interface names pinned: WAN=${WAN_IFACE} (${WAN_MAC}), LAN=${LAN_IFACE} (${LAN_MAC})"

# -------------------------------------------------------------------------------------------------
# Site code lookup
# -------------------------------------------------------------------------------------------------
echo -e "${CYAN}Known site codes:${NC}"
echo -e "${CYAN}  $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort | tr '\n' ' ')${NC}"
echo

SITE_CODE=""
SUBNET=""
WG_OCTET=""

# Initialise SITE_DISPLAY_* here so they are always set regardless of
# which branch below the user takes (manual vs CSV lookup).
SITE_DISPLAY_ENTITY="Example Music"
SITE_DISPLAY_CITY=""
SITE_DISPLAY_COUNTRY="Unknown"

while true; do
  read -rp "Enter site code (e.g. CPH, FAL) or 'manual' to enter subnet manually: " SITE_INPUT
  SITE_CODE="${SITE_INPUT^^}"

  if [[ "$SITE_CODE" == "MANUAL" ]]; then
    read -rp "Enter site name: " SITE
    read -rp "Enter LAN subnet prefix (e.g. 192.168.76): " SUBNET
    [[ "$SUBNET" =~ ^([0-9]{1,3}\.){2}[0-9]{1,3}$ ]] || die "Subnet prefix must be in format X.X.X"
    WG_OCTET=$(echo "$SUBNET" | awk -F. '{print $3}')
    # BUG FIX: SITE_DISPLAY_* were never set in the manual path, leaving
    # them unbound for the sentinel file, SSH banner, and final output.
    SITE_DISPLAY_ENTITY="${SITE_ENTITY[$SITE_CODE]:-Example Music}"
    SITE_DISPLAY_CITY="${SITE_CODE}"
    SITE_DISPLAY_COUNTRY="Unknown"
    break
  elif [[ -v SITE_OCTET[$SITE_CODE] ]]; then
    WG_OCTET="${SITE_OCTET[$SITE_CODE]}"
    SUBNET="192.168.${WG_OCTET}"
    SITE="$SITE_CODE"
    SITE_DISPLAY_ENTITY="${SITE_ENTITY[$SITE_CODE]:-Example Music}"
    SITE_DISPLAY_CITY="${SITE_CITY[$SITE_CODE]:-${SITE_CODE}}"
    SITE_DISPLAY_COUNTRY="${SITE_COUNTRY[$SITE_CODE]:-Unknown}"
    echo -e "  ${GREEN}→ ${SITE_CODE}: ${SITE_DISPLAY_CITY}, ${SITE_DISPLAY_COUNTRY} — ${SITE_DISPLAY_ENTITY}${NC}"
    echo -e "  ${GREEN}→ subnet ${SUBNET}.0/24, WG tunnel 10.0.${WG_OCTET}.0/24${NC}"
    break
  else
    warn "Unknown site code '${SITE_CODE}'. Try again or type 'manual'."
  fi
done

WG_TUNNEL_NET="10.0.${WG_OCTET}.0/24"
WG_HUB_DEFAULT_IP="10.0.${WG_OCTET}.1"
WG_SPOKE_DEFAULT_IP="10.0.${WG_OCTET}.2"

# -------------------------------------------------------------------------------------------------
# WAN mode — DHCP (default) or static
# Static WAN IP is derived from the site code: 192.168.139.<octet>
# matching the convention used across the estate (FAL=.76, ODE=.126 etc.)
# -------------------------------------------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              WAN Interface Configuration             ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo
echo -e "  ${CYAN}WAN IP convention: 192.168.139.<site-octet>${NC}"
echo -e "  ${CYAN}Derived for ${SITE}: ${GREEN}192.168.139.${WG_OCTET}${NC}"
echo -e "  ${CYAN}Default: DHCP (use static if this node has a reserved provisioning IP)${NC}"
echo

WAN_MODE="dhcp"
read -rp "WAN mode — DHCP or static? [DHCP/static] (default: DHCP): " WAN_MODE_INPUT
if [[ "${WAN_MODE_INPUT,,}" == "static" ]]; then
  WAN_MODE="static"
  WAN_STATIC_IP="192.168.139.${WG_OCTET}"
  WAN_STATIC_GW="192.168.139.254"
  WAN_STATIC_PREFIX="24"

  info "Derived static WAN IP: ${WAN_STATIC_IP}/24 gw ${WAN_STATIC_GW}"
  echo
  step "Checking ${WAN_STATIC_IP} is not already in use on the provisioning network..."
  if ip_in_use "${WAN_STATIC_IP}"; then
    warn "${WAN_STATIC_IP} is already responding on the network."
    warn "This is expected if this node already has this IP (e.g. re-running firewallme.sh)."
    warn "If this is a NEW node, the IP is taken -- check the provisioning network."
    read -rp "  Use ${WAN_STATIC_IP} anyway? [y/N]: " WAN_FORCE
    if [[ "${WAN_FORCE,,}" != "y" ]]; then
      warn "Falling back to DHCP. Edit wg0.conf Endpoint manually after setup."
      WAN_MODE="dhcp"
      WAN_STATIC_IP=""
      WAN_STATIC_GW=""
    else
      success "${WAN_STATIC_IP} accepted (in-use, forced by operator)."
    fi
  else
    success "${WAN_STATIC_IP} is free."
  fi

  if [[ "$WAN_MODE" == "static" ]]; then
    # Allow override in case the operator knows better
    read -rp "  WAN IP [${WAN_STATIC_IP}]: " WAN_IP_OVERRIDE
    if [[ -n "$WAN_IP_OVERRIDE" ]]; then
      WAN_STATIC_IP="$WAN_IP_OVERRIDE"
      info "WAN IP overridden to: ${WAN_STATIC_IP}"
    fi
    read -rp "  WAN gateway [${WAN_STATIC_GW}]: " WAN_GW_OVERRIDE
    [[ -n "$WAN_GW_OVERRIDE" ]] && WAN_STATIC_GW="$WAN_GW_OVERRIDE"
    success "WAN: static ${WAN_STATIC_IP}/24 gw ${WAN_STATIC_GW}"
  fi
else
  success "WAN: DHCP"
fi

while true; do
  read -rp "Use .1 or .253 for LAN IP? " LANIP_OCTET
  [[ "$LANIP_OCTET" == "1" || "$LANIP_OCTET" == "253" ]] && break
  warn "Invalid choice. Enter 1 or 253."
done

LAN_IP="${SUBNET}.${LANIP_OCTET}"
DHCP_START="${SUBNET}.150"
DHCP_END="${SUBNET}.250"

while true; do
  read -rp "Enter Ansible/provisioning server last octet (default: 15): " ANSIBLE_OCTET
  ANSIBLE_OCTET="${ANSIBLE_OCTET:-15}"
  ANSIBLE_OCTET="${ANSIBLE_OCTET#.}"
  if [[ "$ANSIBLE_OCTET" =~ ^[0-9]{1,3}$ ]] && [[ "$ANSIBLE_OCTET" -ge 1 ]] && [[ "$ANSIBLE_OCTET" -le 254 ]]; then
    break
  fi
  warn "Ansible octet must be a whole number between 1 and 254 (you entered: '${ANSIBLE_OCTET}')"
done
ANSIBLE_IP="${SUBNET}.${ANSIBLE_OCTET}"

while true; do
  read -rp "Enter internal DNS server IP or last octet (e.g. 10 → ${SUBNET}.10 — leave blank to skip): " INTERNAL_DNS
  [[ -z "$INTERNAL_DNS" ]] && break
  if [[ "$INTERNAL_DNS" =~ ^[0-9]{1,3}$ ]] && [[ "$INTERNAL_DNS" -ge 1 ]] && [[ "$INTERNAL_DNS" -le 254 ]]; then
    INTERNAL_DNS="${SUBNET}.${INTERNAL_DNS}"
    info "Expanded to ${INTERNAL_DNS}"
    break
  fi
  if [[ "$INTERNAL_DNS" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    break
  fi
  warn "Enter a full IP (e.g. 192.168.76.10) or just the last octet (e.g. 10)"
done

echo
warn "SSH on WAN (port 22 open to the internet) is a security risk."
warn "LAN SSH is always enabled. WAN SSH defaults to OFF."
read -rp "Enable SSH on WAN interface? [y/N] " WAN_SSH_ANSWER
WAN_SSH=false
WAN_SSH_SRC=""
if [[ "${WAN_SSH_ANSWER,,}" == "y" ]]; then
  WAN_SSH=true
  read -rp "Restrict WAN SSH to a specific source IP? (leave blank to allow all): " WAN_SSH_SRC
fi

# -------------------------------------------------------------------------------------------------
# WAN activation prompt
# Running over SSH means bringing up (or reconfiguring) WAN interface can drop the session. This
# prompt lets operators skip the nmcli con up wan call and bring it up manually later, while still
# writing all configs so everything is ready on next boot. Default is N (safe for SSH sessions).
# -------------------------------------------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              WAN Activation                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo
warn "If you are connected via SSH over the WAN interface, bringing it"
warn "up via nmcli mid-run may drop your session."
warn "All configs will be written regardless. If you say N, bring the"
warn "WAN up yourself afterwards with:  nmcli con up wan"
echo
read -rp "Activate WAN interface now? [y/N] " WAN_ACTIVATE_ANSWER
WAN_ACTIVATE=false
if [[ "${WAN_ACTIVATE_ANSWER,,}" == "y" ]]; then
  WAN_ACTIVATE=true
  success "WAN will be activated during setup."
else
  warn "WAN activation skipped — bring it up manually after the script completes."
fi

# -------------------------------------------------------------------------------------------------
# WireGuard role prompt
# -------------------------------------------------------------------------------------------------
DEFAULT_ROLE="${SITE_DEFAULT_ROLE[$SITE_CODE]:-spoke}"

echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║               WireGuard Configuration                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo
echo -e "  ${CYAN}Configuring WireGuard on   : ${GREEN}$(hostname)${NC}"
echo -e "  ${CYAN}Auto-derived tunnel subnet : ${ORANGE}${WG_TUNNEL_NET}${NC}"
echo -e "  ${CYAN}Suggested default role     : ${GREEN}${DEFAULT_ROLE}${NC}"
echo
echo -e "  ${CYAN}Roles:${NC}"
echo -e "    ${CYAN}hub-primary   — top-level hub (FAL)${NC}"
echo -e "    ${CYAN}hub-regional  — regional hub (ODE, BRK)${NC}"
echo -e "    ${CYAN}spoke         — satellite office${NC}"
echo -e "    ${CYAN}none          — no WireGuard${NC}"
echo

WG_ROLE=""
WG_TUNNEL_IP=""
WG_PORT=51820
WG_HUB_PUBKEY=""
WG_HUB_ENDPOINT=""
WG_HUB_LAN=""
WG_HUB_TUNNEL=""
WG_BACKUP_PEERS=()

while true; do
  read -rp "WireGuard role [hub-primary/hub-regional/spoke/none] (default: ${DEFAULT_ROLE}): " WG_ROLE_INPUT
  WG_ROLE="${WG_ROLE_INPUT:-${DEFAULT_ROLE}}"
  [[ "$WG_ROLE" == "hub-primary" || "$WG_ROLE" == "hub-regional" || "$WG_ROLE" == "spoke" || "$WG_ROLE" == "none" ]] && break
  warn "Please enter hub-primary, hub-regional, spoke, or none."
done

# -------------------------------------------------------------------------------------------------
# Hub pubkey fetch + verification helper
# Usage: fetch_and_verify_hub_pubkey <HUB_SITE_CODE> <HUB_WAN_IP>
# Sets global HUB_VERIFIED_PUBKEY on success
# -------------------------------------------------------------------------------------------------
HUB_VERIFIED_PUBKEY=""
fetch_and_verify_hub_pubkey() {
  local hub_code="${1^^}"
  local hub_ip="$2"

  echo
  echo -e "${CYAN}  ── Hub key verification ────────────────────────────────────${NC}"
  echo -e "  ${CYAN}Fetching live pubkey from ${hub_code} hub (${hub_ip})...${NC}"
  echo -e "  ${CYAN}Command: ssh ansible@${hub_ip} 'cat /etc/wireguard/public.key'${NC}"
  echo

  local live_pubkey=""
  if live_pubkey=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes "ansible@${hub_ip}" 'cat /etc/wireguard/public.key' 2>/dev/null); then
    live_pubkey=$(echo "$live_pubkey" | tr -d '[:space:]')
    if [[ "$live_pubkey" =~ ^[A-Za-z0-9+/]{43}=$ ]]; then
      success "Fetched live pubkey from ${hub_code}: ${live_pubkey}"

      # Cross-check against known value if we have one
      if [[ -v HUB_KNOWN_PUBKEY[$hub_code] ]]; then
        if [[ "$live_pubkey" == "${HUB_KNOWN_PUBKEY[$hub_code]}" ]]; then
          success "Matches known good key for ${hub_code} ✓"
        else
          warn "LIVE KEY DIFFERS FROM KNOWN GOOD KEY FOR ${hub_code}!"
          warn "  Known  : ${HUB_KNOWN_PUBKEY[$hub_code]}"
          warn "  Live   : ${live_pubkey}"
          warn "This may mean ${hub_code} was rebuilt. Verify before continuing."
          read -rp "  Accept the live key anyway? [y/N] " ACCEPT_NEW
          [[ "${ACCEPT_NEW,,}" != "y" ]] && die "Aborted — resolve hub key mismatch before retrying."
        fi
      fi

      HUB_VERIFIED_PUBKEY="$live_pubkey"
      return 0
    else
      warn "SSH succeeded but returned an invalid key: '${live_pubkey}'"
    fi
  else
    warn "Could not SSH to ${hub_code} at ${hub_ip} to fetch pubkey automatically."
  fi

  # SSH failed or returned garbage — fall back to manual entry with validation
  echo
  echo -e "${YELLOW}  Manual key entry required.${NC}"
  echo -e "${CYAN}  To get the hub's public key, run on ${hub_code} (${hub_ip}):${NC}"
  echo -e "${GREEN}    cat /etc/wireguard/public.key${NC}"
  echo -e "${CYAN}  Or derive it from the private key:${NC}"
  echo -e "${GREEN}    cat /etc/wireguard/private.key | wg pubkey${NC}"
  echo -e "${CYAN}  Both will give the same result. Paste it below.${NC}"
  echo

  # Show known key as reference if available
  if [[ -v HUB_KNOWN_PUBKEY[$hub_code] ]]; then
    echo -e "${CYAN}  Last known good key for ${hub_code}: ${YELLOW}${HUB_KNOWN_PUBKEY[$hub_code]}${NC}"
    echo -e "${CYAN}  (If ${hub_code} has not been rebuilt, this will still be correct)${NC}"
    echo
  fi

  while true; do
    read -rp "  Paste ${hub_code} public key: " PASTED_KEY
    PASTED_KEY=$(printf '%s' "$PASTED_KEY" | tr -d '[:space:]')
    if [[ "$PASTED_KEY" =~ ^[A-Za-z0-9+/]{43}=$ ]]; then
      success "Key format valid (44-char base64)."

      # Cross-check against known if available
      if [[ -v HUB_KNOWN_PUBKEY[$hub_code] ]]; then
        if [[ "$PASTED_KEY" == "${HUB_KNOWN_PUBKEY[$hub_code]}" ]]; then
          success "Matches known good key for ${hub_code} ✓"
        else
          warn "This key does NOT match the last known good key for ${hub_code}."
          warn "  Known  : ${HUB_KNOWN_PUBKEY[$hub_code]}"
          warn "  Entered: ${PASTED_KEY}"
          warn "If ${hub_code} was recently rebuilt this may be correct."
          read -rp "  Accept this key? [y/N] " ACCEPT_MANUAL
          [[ "${ACCEPT_MANUAL,,}" != "y" ]] && continue
        fi
      fi

      HUB_VERIFIED_PUBKEY="$PASTED_KEY"
      return 0
    fi
    warn "Invalid key — expected 44 base64 characters ending in =. Try again."
    warn "(Tip: use printf '%s' to avoid newline issues when copying)"
  done
}

# Helper: prompt for a WireGuard public key (paste or file)
read_wg_pubkey() {
  local prompt="$1"
  local result=""
  while true; do
    echo -e "  ${CYAN}${prompt} — paste key or enter file path:${NC}" >&2
    read -rp "  > " KEY_INPUT
    if [[ -f "$KEY_INPUT" ]]; then
      result=$(cat "$KEY_INPUT" | tr -d '[:space:]')
      echo -e "${GREEN}[+]${NC} Read key from file." >&2
    else
      result=$(printf '%s' "$KEY_INPUT" | tr -d '[:space:]')
    fi
    if [[ "$result" =~ ^[A-Za-z0-9+/]{43}=$ ]]; then
      echo "$result"
      return 0
    fi
    echo -e "${YELLOW}[!]${NC} Invalid WireGuard key (expected 44 base64 chars) — try again." >&2
  done
}

if [[ "$WG_ROLE" == "hub-primary" || "$WG_ROLE" == "hub-regional" ]]; then
  while true; do
    read -rp "Hub tunnel IP (default: ${WG_HUB_DEFAULT_IP}): " WG_IP_INPUT
    WG_TUNNEL_IP="${WG_IP_INPUT:-${WG_HUB_DEFAULT_IP}}"
    [[ "$WG_TUNNEL_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] && break
    warn "Invalid tunnel IP '${WG_TUNNEL_IP}' — enter a valid IPv4 address"
  done
  read -rp "WireGuard listen port (default: 51820): " WG_PORT_INPUT
  WG_PORT="${WG_PORT_INPUT:-51820}"

  if [[ "$WG_ROLE" == "hub-regional" ]]; then
    echo
    echo -e "${CYAN}  Regional hubs must peer with FAL (hub-primary).${NC}"
    echo -e "${CYAN}  FAL WAN IP: ${HUB_WAN_IP[FAL]}${NC}"
    echo
    read -rp "  FAL WAN endpoint (default: ${HUB_WAN_IP[FAL]}:51820): " FAL_ENDPOINT_INPUT
    FAL_ENDPOINT="${FAL_ENDPOINT_INPUT:-${HUB_WAN_IP[FAL]}:51820}"

    # Fetch and verify FAL's pubkey
    FAL_IP="${FAL_ENDPOINT%%:*}"
    fetch_and_verify_hub_pubkey "FAL" "$FAL_IP"
    FAL_PUBKEY="$HUB_VERIFIED_PUBKEY"

    WG_BACKUP_PEERS+=("${FAL_ENDPOINT}|${FAL_PUBKEY}|10.0.76.0/24,192.168.76.0/24|FAL-primary")
    echo
    info "You can also peer with other regional hubs (e.g. BRK↔ODE). Add them now or skip."
    while true; do
      read -rp "  Add another hub peer? (leave blank to skip): " HUB_PEER_NAME
      [[ -z "$HUB_PEER_NAME" ]] && break
      HP_CODE="${HUB_PEER_NAME^^}"
      HP_DEFAULT_IP="${HUB_WAN_IP[$HP_CODE]:-}"
      [[ -n "$HP_DEFAULT_IP" ]] && echo -e "  ${CYAN}Known WAN IP for ${HP_CODE}: ${HP_DEFAULT_IP}${NC}"
      read -rp "  ${HUB_PEER_NAME} WAN endpoint (IP:port): " HP_ENDPOINT
      HP_IP="${HP_ENDPOINT%%:*}"
      fetch_and_verify_hub_pubkey "$HP_CODE" "$HP_IP"
      HP_PUBKEY="$HUB_VERIFIED_PUBKEY"
      read -rp "  ${HUB_PEER_NAME} allowed subnets (comma-separated, e.g. 10.0.126.0/24,192.168.126.0/24): " HP_ALLOWED
      WG_BACKUP_PEERS+=("${HP_ENDPOINT}|${HP_PUBKEY}|${HP_ALLOWED}|${HP_CODE}")
    done
  fi

elif [[ "$WG_ROLE" == "spoke" ]]; then
  while true; do
    read -rp "Spoke tunnel IP (default: ${WG_SPOKE_DEFAULT_IP}): " WG_IP_INPUT
    WG_TUNNEL_IP="${WG_IP_INPUT:-${WG_SPOKE_DEFAULT_IP}}"
    [[ "$WG_TUNNEL_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] && break
    warn "Invalid tunnel IP '${WG_TUNNEL_IP}' — enter a valid IPv4 address"
  done

  echo
  echo -e "${CYAN}  Primary hub connection:${NC}"
  echo -e "${CYAN}  Known hubs:${NC}"
  for hub_code in "${!HUB_WAN_IP[@]}"; do
    echo -e "    ${GREEN}${hub_code}${NC} — ${HUB_WAN_IP[$hub_code]}:51820"
  done
  echo

  read -rp "  Primary hub site code (e.g. FAL, ODE): " HUB_SITE_INPUT
  HUB_SITE="${HUB_SITE_INPUT^^}"

  # Derive endpoint from known IPs if available
  if [[ -v HUB_WAN_IP[$HUB_SITE] ]]; then
    DEFAULT_HUB_ENDPOINT="${HUB_WAN_IP[$HUB_SITE]}:51820"
    read -rp "  Primary hub WAN endpoint (default: ${DEFAULT_HUB_ENDPOINT}): " HUB_EP_INPUT
    WG_HUB_ENDPOINT="${HUB_EP_INPUT:-${DEFAULT_HUB_ENDPOINT}}"
  else
    read -rp "  Primary hub WAN endpoint (IP:port): " WG_HUB_ENDPOINT
  fi

  # Fetch and verify hub pubkey
  HUB_IP="${WG_HUB_ENDPOINT%%:*}"
  fetch_and_verify_hub_pubkey "$HUB_SITE" "$HUB_IP"
  WG_HUB_PUBKEY="$HUB_VERIFIED_PUBKEY"

  # Auto-derive hub subnets from site code
  if [[ -v SITE_OCTET[$HUB_SITE] ]]; then
    WG_HUB_LAN="192.168.${SITE_OCTET[$HUB_SITE]}.0/24"
    WG_HUB_TUNNEL="10.0.${SITE_OCTET[$HUB_SITE]}.0/24"
    echo -e "  ${GREEN}→ Hub LAN subnet: ${WG_HUB_LAN}, hub tunnel: ${WG_HUB_TUNNEL}${NC}"
  else
    while true; do
      read -rp "  Primary hub LAN subnet (e.g. 192.168.76.0/24): " WG_HUB_LAN
      [[ "$WG_HUB_LAN" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$ ]] && break
      warn "Invalid subnet — enter in CIDR format e.g. 192.168.76.0/24"
    done
    while true; do
      read -rp "  Primary hub tunnel subnet (e.g. 10.0.76.0/24): " WG_HUB_TUNNEL
      [[ "$WG_HUB_TUNNEL" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$ ]] && break
      warn "Invalid subnet — enter in CIDR format e.g. 10.0.76.0/24"
    done
  fi

  echo
  info "You can add backup hub peers (e.g. FAL as backup for ODE spokes). Leave blank to skip."
  while true; do
    read -rp "  Add backup hub peer? Site code or leave blank to finish: " BP_NAME
    [[ -z "$BP_NAME" ]] && break
    BP_CODE="${BP_NAME^^}"
    BP_DEFAULT_IP="${HUB_WAN_IP[$BP_CODE]:-}"
    [[ -n "$BP_DEFAULT_IP" ]] && echo -e "  ${CYAN}Known WAN IP for ${BP_CODE}: ${BP_DEFAULT_IP}${NC}"

    if [[ -v HUB_WAN_IP[$BP_CODE] ]]; then
      DEFAULT_BP_ENDPOINT="${HUB_WAN_IP[$BP_CODE]}:51820"
      read -rp "  ${BP_CODE} WAN endpoint (default: ${DEFAULT_BP_ENDPOINT}): " BP_EP_INPUT
      BP_ENDPOINT="${BP_EP_INPUT:-${DEFAULT_BP_ENDPOINT}}"
    else
      read -rp "  ${BP_CODE} WAN endpoint (IP:port): " BP_ENDPOINT
    fi

    BP_IP="${BP_ENDPOINT%%:*}"
    fetch_and_verify_hub_pubkey "$BP_CODE" "$BP_IP"
    BP_PUBKEY="$HUB_VERIFIED_PUBKEY"

    if [[ -v SITE_OCTET[$BP_CODE] ]]; then
      BP_ALLOWED="10.0.${SITE_OCTET[$BP_CODE]}.0/24,192.168.${SITE_OCTET[$BP_CODE]}.0/24"
      echo -e "  ${GREEN}→ Auto-derived allowed subnets: ${BP_ALLOWED}${NC}"
    else
      while true; do
        read -rp "  ${BP_CODE} allowed subnets (e.g. 10.0.76.0/24,192.168.76.0/24): " BP_ALLOWED
        [[ -n "$BP_ALLOWED" ]] && break
        warn "Cannot be blank."
      done
    fi
    WG_BACKUP_PEERS+=("${BP_ENDPOINT}|${BP_PUBKEY}|${BP_ALLOWED}|${BP_CODE}")
  done
fi

# -------------------------------------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                       Summary                        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo -e "${CYAN}  Hostname      : $(hostname)${NC}"
echo -e "${CYAN}  Site          : ${SITE}${NC}"
echo -e "${YELLOW}  Environment   : ${ENV_LONG}${NC}"
echo -e "${RED}  WAN iface     : ${WAN_IFACE} (MAC: ${WAN_MAC})${NC}"
if [[ "$WAN_MODE" == "static" ]]; then
  echo -e "${RED}  WAN IP        : ${WAN_STATIC_IP}/24 gw ${WAN_STATIC_GW} (static)${NC}"
else
  echo -e "${CYAN}  WAN IP        : DHCP${NC}"
fi
if [[ "$WAN_ACTIVATE" == "true" ]]; then
  echo -e "${CYAN}  WAN activate  : yes (will be brought up during setup)${NC}"
else
  echo -e "${YELLOW}  WAN activate  : NO — bring up manually afterwards: nmcli con up wan${NC}"
fi
echo -e "${GREEN}  LAN iface     : ${LAN_IFACE} (MAC: ${LAN_MAC})${NC}"
echo -e "${GREEN}  LAN IP        : ${LAN_IP}/24${NC}"
echo -e "${CYAN}  DHCP          : ${DHCP_START} - ${DHCP_END}${NC}"
echo -e "${CYAN}  Ansible IP    : ${ANSIBLE_IP}${NC}"
if [[ -n "$INTERNAL_DNS" ]]; then
  echo -e "${GREEN}  Int. DNS      : ${INTERNAL_DNS}, 1.1.1.1, 9.9.9.9${NC}"
else
  echo -e "${GREEN}  DNS           : 1.1.1.1, 9.9.9.9${NC}"
fi
if [[ "$WAN_SSH" == "true" ]]; then
  [[ -n "${WAN_SSH_SRC:-}" ]] && echo -e "  WAN SSH       : ${RED}ENABLED (restricted to ${WAN_SSH_SRC})${NC}" || echo -e "  WAN SSH       : ${RED}ENABLED (open to all - be careful)${NC}"
else
  echo -e "  WAN SSH       : ${YELLOW}disabled (LAN only)${NC}"
fi
case "$WG_ROLE" in
  hub-primary)
    echo -e "  WireGuard     : ${ORANGE}HUB PRIMARY — ${WG_TUNNEL_IP}/24 (${WG_TUNNEL_NET}), port ${WG_PORT}${NC}"
    ;;
  hub-regional)
    echo -e "  WireGuard     : ${ORANGE}HUB REGIONAL — ${WG_TUNNEL_IP}/24 (${WG_TUNNEL_NET}), port ${WG_PORT}${NC}"
    echo -e "  WG hub peers  : ${GREEN}${#WG_BACKUP_PEERS[@]} hub peer(s) configured${NC}"
    ;;
  spoke)
    echo -e "  WireGuard     : ${ORANGE}SPOKE — ${WG_TUNNEL_IP}/24 → ${WG_HUB_ENDPOINT}${NC}"
    echo -e "  WG hub pubkey : ${GREEN}${WG_HUB_PUBKEY}${NC}"
    [[ ${#WG_BACKUP_PEERS[@]} -gt 0 ]] && echo -e "  WG backups    : ${GREEN}${#WG_BACKUP_PEERS[@]} backup hub(s) configured${NC}"
    ;;
  none)
    echo -e "  WireGuard     : ${YELLOW}not configured${NC}"
    ;;
esac
echo
read -rp "Proceed? [y/N] " CONFIRM
[[ "${CONFIRM,,}" == "y" ]] || die "Aborted by user."

# -------------------------------------------------------------------------------------------------
# 2. Remove stale NetworkManager profiles
# -------------------------------------------------------------------------------------------------
info "Removing stale NetworkManager profiles..."
while IFS=: read -r profile device rest; do
  [[ -z "$profile" ]] && continue
  if [[ "$device" == "--" || "$profile" == *"Wired connection"* || "$profile" == *"Ifupdown"* ]]; then
    warn "Deleting stale profile: $profile"
    nmcli con delete "$profile" || true
  fi
done < <(nmcli -t -f NAME,DEVICE con show)

# -------------------------------------------------------------------------------------------------
# Allow mouse control for pasting those WireGuard keys
# -------------------------------------------------------------------------------------------------
systemctl restart gpm.service 2>/dev/null || true

# -------------------------------------------------------------------------------------------------
# 3. Disable ifupdown udev integration
# -------------------------------------------------------------------------------------------------
warn "Masking ifupdown units to hand full control to NetworkManager..."
systemctl disable networking.service 2>/dev/null || true
systemctl mask networking.service 2>/dev/null || true
systemctl mask "ifup@${WAN_IFACE}.service" 2>/dev/null || true
systemctl mask "ifup@${LAN_IFACE}.service" 2>/dev/null || true
success "ifupdown units masked."

# safety marker only — do NOT assume networking is stable yet
IFUPDOWN_MASKED=1

# -------------------------------------------------------------------------------------------------
# 4. Enable IP forwarding
# -------------------------------------------------------------------------------------------------
info "Enabling IPv4 forwarding..."
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-router.conf
sysctl -p /etc/sysctl.d/99-router.conf
success "IP forwarding enabled."

# -------------------------------------------------------------------------------------------------
# 5. Release interfaces from ifupdown
# -------------------------------------------------------------------------------------------------
info "Checking /etc/network/interfaces..."
if [[ -f /etc/network/interfaces ]]; then
  cp -n /etc/network/interfaces /etc/network/interfaces.bak
  CHANGED=0
  for IFACE in "$WAN_IFACE" "$LAN_IFACE"; do
    if grep -qE "^(auto|allow-|iface)\s+${IFACE}" /etc/network/interfaces 2>/dev/null; then
      warn "Removing ifupdown stanza for ${IFACE}"
      sed -i "/^auto\s\+${IFACE}\b/d"      /etc/network/interfaces
      sed -i "/^allow-.*\s${IFACE}\b/d"     /etc/network/interfaces
      sed -i "/^iface[[:space:]]\+${IFACE}\b/,/^[^[:space:]]/d" /etc/network/interfaces
      CHANGED=1
    fi
  done
  if [[ $CHANGED -eq 1 ]]; then
    success "Cleaned /etc/network/interfaces"
    warn "ifupdown changes applied — NetworkManager restart required later"
    NM_RESTART_REQUIRED=1
  fi
fi

# -------------------------------------------------------------------------------------------------
# 6. NetworkManager - WAN (DHCP or static) + LAN (static)
# -------------------------------------------------------------------------------------------------
info "Recreating WAN and LAN NetworkManager connections..."
nmcli con delete lan 2>/dev/null || true
nmcli con delete wan 2>/dev/null || true

if [[ "$WAN_MODE" == "static" ]]; then
  info "WAN: static ${WAN_STATIC_IP}/24 gw ${WAN_STATIC_GW}"
  # BUG FIX: missing connection.autoconnect yes + autoconnect-priority meant NM
  # could silently skip this profile on boot.  Priority 100 ensures WAN wins
  # over any leftover unconfigured profile NM might auto-generate.
  nmcli con add type ethernet ifname "$WAN_IFACE" con-name wan \
    ipv4.method manual ipv4.addresses "${WAN_STATIC_IP}/${WAN_STATIC_PREFIX}" \
    ipv4.gateway "${WAN_STATIC_GW}" ipv4.dns "1.1.1.1 9.9.9.9" ipv6.method ignore \
    connection.autoconnect yes connection.autoconnect-priority 100
else
  info "WAN: DHCP"
  nmcli con add type ethernet ifname "$WAN_IFACE" con-name wan \
    ipv4.method auto ipv6.method ignore \
    connection.autoconnect yes connection.autoconnect-priority 100
fi

# BUG FIX: same missing autoconnect flags on LAN profile.
nmcli con add type ethernet ifname "$LAN_IFACE" con-name lan \
  ipv4.method manual ipv4.addresses "${LAN_IP}/24" ipv4.gateway "" ipv6.method ignore \
  connection.autoconnect yes connection.autoconnect-priority 100

NM_CONF="/etc/NetworkManager/NetworkManager.conf"
if grep -q "managed=false" "$NM_CONF" 2>/dev/null; then
  warn "NetworkManager.conf has managed=false - fixing..."
  sed -i "s/managed=false/managed=true/" "$NM_CONF"
  warn "NetworkManager config adjusted — restart required later"
  NM_RESTART_REQUIRED=1
fi

# BUG FIX: original code brought LAN up before calling wait_for_wan, which defeated the purpose of
# the sequencing guard entirely. BUG FIX: added WAN_ACTIVATE gate so operators on SSH can skip the
# WAN activation and avoid dropping their session mid-run.
if [[ "$WAN_ACTIVATE" == "true" ]]; then
  nmcli con up wan || die "Failed to bring up WAN connection"
  # BUG FIX: wait_for_wan must complete before LAN is brought up, not after.
  wait_for_wan "$WAN_IFACE" || die "WAN failed to come fully online"
else
  warn "Skipping WAN activation as requested."
  warn "Run 'nmcli con up wan' manually when ready."
fi

nmcli con up lan || die "Failed to bring up LAN connection"
success "NM connections configured${WAN_ACTIVATE:+ and WAN brought up}."

# BUG FIX: NM_RESTART_REQUIRED was set (when managed=false was corrected or ifupdown stanzas were
# removed) but was NEVER consumed. Without restarting NetworkManager the daemon kept stale state &
# profiles did not reliably come up on subsequent boots. SAFETY: systemctl restart NetworkManager
# tears down ALL connections instantly, which kills active SSH session. Guard behind WAN_ACTIVATE-
# the same gate used throughout this script to protect in-session runs. If deferred, a reboot must
# be executed later, or the command run from the console.
if [[ "${NM_RESTART_REQUIRED:-0}" -eq 1 ]]; then
  if [[ "$WAN_ACTIVATE" == "true" ]]; then
    info "Restarting NetworkManager to apply config changes..."
    systemctl restart NetworkManager
    sleep 2
    # Re-raise both connections after the daemon restart.
    nmcli con up wan 2>/dev/null || true
    nmcli con up lan 2>/dev/null || true
    success "NetworkManager restarted and connections re-raised."
  else
    warn "NM config changes require a NetworkManager restart to take full effect."
    warn "Skipped — WAN_ACTIVATE=false implies you are on an active SSH session."
    warn "Either reboot (recommended) or run from local console:"
    warn "  systemctl restart NetworkManager && nmcli con up wan && nmcli con up lan"
  fi
fi

# -------------------------------------------------------------------------------------------------
# 7. nftables
# -------------------------------------------------------------------------------------------------
info "Configuring nftables..."

WG_FORWARD_RULES=""
WG_INPUT_RULES=""
WG_SERVICES_RULES=""
if [[ "$WG_ROLE" != "none" ]]; then
  WG_FORWARD_RULES="    # WireGuard — full bidirectional forwarding between wg0, LAN, and WAN
    iifname \"wg0\" oifname \"${LAN_IFACE}\" accept
    iifname \"wg0\" oifname \"${WAN_IFACE}\" accept
    iifname \"${LAN_IFACE}\" oifname \"wg0\" accept
    iifname \"${WAN_IFACE}\" oifname \"wg0\" ct state related,established accept
    oifname \"wg0\" ct state related,established accept"
  WG_SERVICES_RULES="    # WireGuard tunnel — accept all TCP and UDP from wg0 (all ports)
    iifname \"wg0\" tcp dport 1-65535 accept
    iifname \"wg0\" udp dport 1-65535 accept"
fi
if [[ "$WG_ROLE" == "hub-primary" || "$WG_ROLE" == "hub-regional" ]]; then
  WG_INPUT_RULES="    # WireGuard — inbound on WAN
    iifname \"${WAN_IFACE}\" udp dport ${WG_PORT} accept"
fi

WAN_SSH_RULE_LINE=""
if [[ "$WAN_SSH" == "true" ]]; then
  if [[ -n "${WAN_SSH_SRC:-}" ]]; then
    WAN_SSH_RULE_LINE="    ip saddr ${WAN_SSH_SRC} iifname \"${WAN_IFACE}\" tcp dport 22 accept"
  else
    WAN_SSH_RULE_LINE="    iifname \"${WAN_IFACE}\" tcp dport 22 accept"
  fi
fi

cat > /etc/nftables.conf <<EOF
#!/usr/sbin/nft -f
flush ruleset

table ip nat {
  chain POSTROUTING {
    type nat hook postrouting priority 100; policy accept;
    oifname "${WAN_IFACE}" masquerade
  }
}

table ip filter {
  chain FORWARD {
    type filter hook forward priority 0; policy drop;
    iifname "${LAN_IFACE}" oifname "${LAN_IFACE}" accept
    iifname "${LAN_IFACE}" oifname "${WAN_IFACE}" accept
    iifname "${WAN_IFACE}" oifname "${LAN_IFACE}" ct state related,established accept
${WG_FORWARD_RULES}
  }

  chain INPUT {
    type filter hook input priority 0; policy drop;
    ct state related,established accept
    iifname "lo" accept
    ip protocol icmp accept
    iifname "${LAN_IFACE}" tcp dport 22 accept
${WAN_SSH_RULE_LINE}
    iifname "${LAN_IFACE}" tcp dport 9090 accept
    iifname "${LAN_IFACE}" udp dport 53 accept
    iifname "${LAN_IFACE}" tcp dport 53 accept
    iifname "${LAN_IFACE}" udp dport 67 accept
    iifname "${LAN_IFACE}" udp dport 69 accept
    iifname "${LAN_IFACE}" tcp dport 80 accept
${WG_SERVICES_RULES}
${WG_INPUT_RULES}
  }
}
EOF

# Safety: detect if current session could be impacted
CURRENT_IFACE="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}')"

if [[ "$CURRENT_IFACE" == "$WAN_IFACE" && "$WAN_SSH" != "true" ]]; then
  warn "You are currently connected via WAN (${WAN_IFACE}) but WAN SSH is disabled."
  warn "Skipping nftables apply to avoid locking out current session."
  NFT_PENDING=1
else
  nft -f /etc/nftables.conf
  systemctl enable --now nftables
  success "nftables rules applied."
fi

# -------------------------------------------------------------------------------------------------
# 8. dnsmasq
# -------------------------------------------------------------------------------------------------
info "Configuring dnsmasq..."
if systemctl is-active --quiet systemd-resolved; then
  warn "Disabling systemd-resolved stub listener..."
  mkdir -p /etc/systemd/resolved.conf.d
  printf '[Resolve]\nDNSStubListener=no\n' > /etc/systemd/resolved.conf.d/no-stub.conf
  systemctl restart systemd-resolved
  RESOLVED_RESTARTED=1
  warn "systemd-resolved restarted (DNS may briefly interrupt resolution)"
fi

[[ -f /etc/dnsmasq.conf ]] && cp -n /etc/dnsmasq.conf /etc/dnsmasq.conf.bak

cat > /etc/dnsmasq.d/lan.conf <<EOF
# Example Music LAN DHCP/DNS - Site: ${SITE}
interface=${LAN_IFACE}
bind-interfaces
domain-needed
bogus-priv
no-resolv

$([ -n "${INTERNAL_DNS}" ] && echo "server=${INTERNAL_DNS}")
server=1.1.1.1
server=9.9.9.9

dhcp-range=${DHCP_START},${DHCP_END},12h
dhcp-option=3,${LAN_IP}
$([ -n "${INTERNAL_DNS}" ] && echo "dhcp-option=6,${INTERNAL_DNS},1.1.1.1,9.9.9.9" || echo "dhcp-option=6,1.1.1.1,9.9.9.9")
dhcp-option=15,jukebox.internal

dhcp-vendorclass=set:ipxe-client,iPXE
dhcp-option=tag:ipxe-client,6,${LAN_IP}
dhcp-option=tag:ipxe-client,67,http://${ANSIBLE_IP}/bootstrap.ipxe
EOF

cat > /etc/dnsmasq.d/local-records.conf <<EOF
# Example Music local DNS - Site: ${SITE}
address=/ansible.jukebox.internal/${ANSIBLE_IP}
cname=www.jukebox.internal,ansible.jukebox.internal
cname=tftp.jukebox.internal,ansible.jukebox.internal
cname=provisioning.jukebox.internal,ansible.jukebox.internal
cname=preseed.jukebox.internal,ansible.jukebox.internal
EOF

info "Add extra local DNS records now, or leave blank to skip."
while true; do
  read -rp "  hostname (blank to finish): " DNS_NAME
  [[ -z "$DNS_NAME" ]] && break
  read -rp "  IP for ${DNS_NAME}: " DNS_IP
  if ! [[ "$DNS_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    warn "Invalid IP, skipping."; continue
  fi
  echo "address=/${DNS_NAME}/${DNS_IP}" >> /etc/dnsmasq.d/local-records.conf
  success "Added ${DNS_NAME} -> ${DNS_IP}"
done

mkdir -p /etc/systemd/system/dnsmasq.service.d
cat > /etc/systemd/system/dnsmasq.service.d/wait-for-lan.conf <<EOF
[Unit]
After=network-online.target sys-subsystem-net-devices-${LAN_IFACE}.device
Wants=network-online.target sys-subsystem-net-devices-${LAN_IFACE}.device
EOF

if [[ "${WAN_ACTIVATE:-false}" == true ]]; then
  systemctl enable --now dnsmasq
  systemctl restart dnsmasq
  success "dnsmasq configured."
else
  warn "dnsmasq not started yet (WAN not active) — service enabled but deferred"
  DNSMASQ_PENDING=1
fi

# -------------------------------------------------------------------------------------------------
# 9. Cockpit
# -------------------------------------------------------------------------------------------------
info "Binding Cockpit to LAN (${LAN_IP})..."
systemctl enable NetworkManager-wait-online.service

mkdir -p /etc/systemd/system/cockpit.socket.d
cat > /etc/systemd/system/cockpit.socket.d/override.conf <<EOF
[Unit]
After=network-online.target
Wants=network-online.target

[Socket]
ListenStream=
ListenStream=${LAN_IP}:9090
Restart=on-failure
RestartSec=5s
EOF

rm -f /etc/systemd/system/cockpit.service.d/override.conf
systemctl daemon-reload
systemctl enable cockpit.socket

if [[ "${NETWORK_READY:-false}" == true ]]; then
  systemctl restart cockpit.socket
  success "Cockpit bound to ${LAN_IP}:9090."
else
  warn "Cockpit socket configured but not started (network not ready)"
  COCKPIT_PENDING=1
fi

# -------------------------------------------------------------------------------------------------
# 10. WireGuard
# -------------------------------------------------------------------------------------------------
if [[ "$WG_ROLE" != "none" ]]; then
  info "Setting up WireGuard (${WG_ROLE})..."
  mkdir -p /etc/wireguard
  chmod 700 /etc/wireguard

  WG_PRIVKEY_FILE="/etc/wireguard/private.key"
  WG_PUBKEY_FILE="/etc/wireguard/public.key"
  wg genkey | tee "${WG_PRIVKEY_FILE}" | wg pubkey > "${WG_PUBKEY_FILE}"
  chmod 600 "${WG_PRIVKEY_FILE}"
  THIS_PRIVKEY=$(cat "${WG_PRIVKEY_FILE}")
  THIS_PUBKEY=$(cat "${WG_PUBKEY_FILE}")

  # Verify keypair is internally consistent before writing anything
  DERIVED_PUBKEY=$(printf '%s' "${THIS_PRIVKEY}" | wg pubkey)
  if [[ "$DERIVED_PUBKEY" != "$THIS_PUBKEY" ]]; then
    die "Keypair verification failed — derived pubkey does not match public.key. Aborting."
  fi
  success "Keypair verified: private key correctly derives public key (${THIS_PUBKEY})"

  cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = ${WG_TUNNEL_IP}/24
PrivateKey = ${THIS_PRIVKEY}
EOF

  if [[ "$WG_ROLE" == "hub-primary" || "$WG_ROLE" == "hub-regional" ]]; then
    echo "ListenPort = ${WG_PORT}" >> /etc/wireguard/wg0.conf
  fi

  if [[ "$WG_ROLE" == "hub-primary" || "$WG_ROLE" == "hub-regional" ]]; then

    # BUG FIX: "${WG_BACKUP_PEERS[@]:-}" is not valid bash -- the :- default
    # operator only works on scalar variables, not arrays. Under set -u an
    # empty array expansion errors out. Use the standard guard instead.
    for peer_entry in "${WG_BACKUP_PEERS[@]+"${WG_BACKUP_PEERS[@]}"}"; do
      [[ -z "$peer_entry" ]] && continue
      IFS='|' read -r P_ENDPOINT P_PUBKEY P_ALLOWED P_NAME <<< "$peer_entry"
      cat >> /etc/wireguard/wg0.conf <<EOF

# ${P_NAME}
[Peer]
PublicKey = ${P_PUBKEY}
Endpoint = ${P_ENDPOINT}
AllowedIPs = ${P_ALLOWED}
PersistentKeepalive = 25
EOF
    done

    echo
    info "Add spoke peers now, or skip and edit /etc/wireguard/wg0.conf later."
    cat >> /etc/wireguard/wg0.conf <<EOF

# -------------------------------------------------------------------------------------------------
# Spoke peers — add below
# [Peer]
# # <site-code>
# PublicKey = <spoke-public-key>
# AllowedIPs = <spoke-tunnel-ip>/32, <spoke-lan-subnet>/24
# -------------------------------------------------------------------------------------------------
EOF

    SPOKE_TUNNEL_OCTET=2
    while true; do
      read -rp "  Add spoke peer? (leave blank to finish): " SP_NAME
      [[ -z "$SP_NAME" ]] && break
      read -rp "  ${SP_NAME} tunnel octet (default: ${SPOKE_TUNNEL_OCTET}): " SP_OCTET_INPUT
      SP_OCTET="${SP_OCTET_INPUT:-${SPOKE_TUNNEL_OCTET}}"
      SP_TUNNEL="${WG_TUNNEL_IP%.*}.${SP_OCTET}"

      SP_CODE="${SP_NAME^^}"
      if [[ -v SITE_OCTET[$SP_CODE] ]]; then
        SP_LAN_DEFAULT="192.168.${SITE_OCTET[$SP_CODE]}.0/24"
        read -rp "  ${SP_NAME} LAN subnet (default: ${SP_LAN_DEFAULT}): " SP_LAN_INPUT
        SP_LAN="${SP_LAN_INPUT:-${SP_LAN_DEFAULT}}"
      else
        read -rp "  ${SP_NAME} LAN subnet (e.g. 192.168.231.0/24): " SP_LAN
      fi

      SP_PUBKEY=$(read_wg_pubkey "${SP_NAME} public key")

      if [[ -v SITE_DEFAULT_ROLE[$SP_CODE] && "${SITE_DEFAULT_ROLE[$SP_CODE]}" == "hub-regional" ]]; then
        SP_TUNNEL_ALLOWED="10.0.${SITE_OCTET[$SP_CODE]}.0/24"
        SP_KEEPALIVE="PersistentKeepalive = 25"
        info "${SP_NAME} is a hub-regional — using tunnel /24 and keepalive"
      else
        SP_TUNNEL_ALLOWED="${SP_TUNNEL}/32"
        SP_KEEPALIVE=""
      fi

      cat >> /etc/wireguard/wg0.conf <<EOF

# ${SP_NAME}
[Peer]
PublicKey = ${SP_PUBKEY}
AllowedIPs = ${SP_TUNNEL_ALLOWED}, ${SP_LAN}
${SP_KEEPALIVE}
EOF
      success "Added peer ${SP_NAME}: tunnel ${SP_TUNNEL_ALLOWED}, LAN ${SP_LAN}"
      (( SPOKE_TUNNEL_OCTET++ )) || true
    done

  elif [[ "$WG_ROLE" == "spoke" ]]; then
    # Build topology-aware AllowedIPs for the primary hub peer.
    # This ensures wg-quick injects kernel routes for ALL cross-hub
    # destinations at boot -- not just the direct hub's subnets.
    FULL_HUB_ALLOWED="$(spoke_allowed_ips_for_hub "${HUB_SITE}")"
    if [[ -z "$FULL_HUB_ALLOWED" ]]; then
      # Fallback for unknown hubs -- just use the hub's own subnets
      FULL_HUB_ALLOWED="${WG_HUB_TUNNEL}, ${WG_HUB_LAN}"
      warn "Hub ${HUB_SITE} not in topology map -- using direct subnets only."
      warn "Edit AllowedIPs in /etc/wireguard/wg0.conf manually if cross-hub routing is needed."
    else
      info "AllowedIPs includes all cross-hub subnets reachable via ${HUB_SITE}."
    fi

    cat >> /etc/wireguard/wg0.conf <<EOF

## Primary hub: ${HUB_SITE}
[Peer]
PublicKey = ${WG_HUB_PUBKEY}
Endpoint = ${WG_HUB_ENDPOINT}
AllowedIPs = ${FULL_HUB_ALLOWED}
PersistentKeepalive = 25
EOF

    # BUG FIX: same array expansion guard as the hub branch above.
    for peer_entry in "${WG_BACKUP_PEERS[@]+"${WG_BACKUP_PEERS[@]}"}"; do
      [[ -z "$peer_entry" ]] && continue
      IFS='|' read -r P_ENDPOINT P_PUBKEY P_ALLOWED P_NAME <<< "$peer_entry"
      # Backup hub peers use the full topology list for their hub too
      BACKUP_FULL_ALLOWED="$(spoke_allowed_ips_for_hub "${P_NAME}")"
      [[ -z "$BACKUP_FULL_ALLOWED" ]] && BACKUP_FULL_ALLOWED="${P_ALLOWED}"
      cat >> /etc/wireguard/wg0.conf <<EOF

## Backup hub: ${P_NAME}
[Peer]
PublicKey = ${P_PUBKEY}
Endpoint = ${P_ENDPOINT}
AllowedIPs = ${BACKUP_FULL_ALLOWED}
PersistentKeepalive = 25
EOF
    done
  fi

  chmod 600 /etc/wireguard/wg0.conf

  # BUG FIX: wg-quick@.service ships with After=network.target which is satisfied the moment the
  # network subsystem initialises; long before any interface actually has an IP. On boot, wg-quick
  # then tries to resolve the hub Endpoint, fails, & leaves wg0 down. Fix: install a drop-in that
  # adds After=network-online.target so systemd waits for NM (& NetworkManager-wait-online.service)
  # reports that at least one interface is fully online before starting WireGuard.
  info "Installing wg-quick@wg0 drop-in to wait for network-online.target..."
  mkdir -p /etc/systemd/system/wg-quick@wg0.service.d
  cat > /etc/systemd/system/wg-quick@wg0.service.d/wait-online.conf <<'DROPIN'
[Unit]
After=network-online.target
Wants=network-online.target
DROPIN
  systemctl daemon-reload
  success "wg-quick@wg0 will now wait for network-online.target before starting."

  if [[ "$WAN_ACTIVATE" == true ]]; then
    systemctl enable --now wg-quick@wg0
    if systemctl is-active --quiet wg-quick@wg0; then
      bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)' 2>/dev/null || true
    fi
  else
    warn "WAN not activated — skipping WireGuard start (wg0 remains configured but stopped)."
  fi


  # Post-config verification
  echo
  info "Post-configuration WireGuard verification..."
  RUNNING_PUBKEY=$(wg show wg0 public\ key 2>/dev/null || true)
  if [[ "$RUNNING_PUBKEY" == "$THIS_PUBKEY" ]]; then
    success "wg0 is running with the correct public key: ${THIS_PUBKEY}"
  else
    warn "wg0 public key mismatch!"
    warn "  Expected : ${THIS_PUBKEY}"
    warn "  Running  : ${RUNNING_PUBKEY:-not running}"
    warn "Check /etc/wireguard/wg0.conf and restart wg-quick@wg0 manually."
  fi

  success "WireGuard wg0 configured and started."
fi

# -------------------------------------------------------------------------------------------------
# 11. SSH banner
# -------------------------------------------------------------------------------------------------
info "Configuring SSH login banner..."

SITE_DISPLAY_ENTITY="${SITE_DISPLAY_ENTITY}" \
SITE="${SITE}" \
SITE_DISPLAY_CITY="${SITE_DISPLAY_CITY}" \
SITE_DISPLAY_COUNTRY="${SITE_DISPLAY_COUNTRY}" \
HOSTNAME="$(hostname)" \
python3 - <<'PYEOF' > /etc/ssh/banner
import os

def clean(value):
    return str(value).replace("\r", "").strip()

entity = clean(os.environ.get("SITE_DISPLAY_ENTITY", ""))

site = clean(
    f"{os.environ.get('SITE','')} — "
    f"{os.environ.get('SITE_DISPLAY_CITY','')}, "
    f"{os.environ.get('SITE_DISPLAY_COUNTRY','')}"
)

host = clean(os.environ.get("HOSTNAME", ""))
W = 80

def dlen(s):
    # crude but effective: treat wide chars properly
    import unicodedata
    width = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            width += 2
        else:
            width += 1
    return width

def row(text=""):
    pad = W - dlen(text)
    if dlen(text) > W:
        text = text[:W-3] + "..."
        pad = 0
    left = pad // 2
    right = pad - left
    return f"*{' '*left}{text}{' '*right}*"

def lrow(label, value):
    inner_width = W - 5
    text = f"{clean(label)}: {clean(value)}"
    return f"*   {text:<{inner_width}}*"

print()
print("*" * (W+2))
print(row())
print(row("EXAMPLE MUSIC LIMITED"))
print(row("AUTHORISED ACCESS ONLY"))
print(row())
print(lrow("Property of", entity))
print(f"*   {'Unauthorised access or use is strictly prohibited and may be':<{W-3}}*")
print(f"*   {'subject to civil and criminal prosecution.':<{W-3}}*")
print(row())
print(f"*   {'All activity on this system is monitored and logged.':<{W-3}}*")
print(row())
print(lrow("Entity", entity))
print(lrow("Site", site))
print(lrow("Hostname", host))
print(row())
print("*" * (W+2))
print()
PYEOF

## strip Windows line endings just in case
sed -i 's/\r$//' /etc/ssh/banner

## match up both banners
tee -a /etc/issue /etc/issue.net < /etc/ssh/banner > /dev/null

if grep -q "^Banner" /etc/ssh/sshd_config 2>/dev/null; then
  sed -i "s|^Banner.*|Banner /etc/ssh/banner|" /etc/ssh/sshd_config
else
  echo "Banner /etc/ssh/banner" >> /etc/ssh/sshd_config
fi
systemctl reload ssh 2>/dev/null || systemctl restart ssh
success "SSH banner configured."

# -------------------------------------------------------------------------------------------------
# 12. Dynamic MOTD
# -------------------------------------------------------------------------------------------------
info "Configuring dynamic MOTD..."
chmod -x /etc/update-motd.d/* 2>/dev/null || true

cat > /etc/update-motd.d/10-examplemusic <<'MOTD'
#!/bin/bash
GR='\033[0;32m'; CY='\033[0;36m'; RD='\033[0;31m'; YL='\033[0;33m'
OR='\033[38;5;208m'; WH='\033[1;37m'; NC='\033[0m'

SITE="unknown"; WG_ROLE="none"; ENTITY=""; CITY=""; COUNTRY=""
if [[ -f /etc/.i_am_a_firewall ]]; then
  SITE=$(grep    "^Site"    /etc/.i_am_a_firewall | awk -F': ' '{print $2}' | xargs)
  WG_ROLE=$(grep "^WG Role" /etc/.i_am_a_firewall | awk -F': ' '{print $2}' | xargs)
  ENTITY=$(grep  "^Entity"  /etc/.i_am_a_firewall | awk -F': ' '{print $2}' | xargs)
  CITY=$(grep    "^City"    /etc/.i_am_a_firewall | awk -F': ' '{print $2}' | xargs)
  COUNTRY=$(grep "^Country" /etc/.i_am_a_firewall | awk -F': ' '{print $2}' | xargs)
fi

WAN_INFO=""; LAN_INFO=""; WG_INFO=""; OTHER_INFO=""
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

WG_PEERS=""
if command -v wg &>/dev/null && ip link show wg0 &>/dev/null 2>&1; then
  WG_PEERS="  ${WH}── WireGuard Peers ──────────────────────────────────────────${NC}\n"
  PEER_COUNT=0; ACTIVE_COUNT=0; NOW=$(date +%s)
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
      HS_STR="${RD}never${NC}"; STATUS="${RD}✗${NC}"
    else
      AGE=$((NOW - HANDSHAKE))
      if [[ $AGE -lt 60 ]]; then HS_STR="${GR}${AGE}s ago${NC}"
      elif [[ $AGE -lt 3600 ]]; then HS_STR="${GR}$((AGE/60))m ago${NC}"
      elif [[ $AGE -lt 86400 ]]; then HS_STR="${YL}$((AGE/3600))h ago${NC}"
      else HS_STR="${RD}$((AGE/86400))d ago${NC}"; fi
      if [[ $AGE -lt 180 ]]; then STATUS="${GR}✓${NC}"; ACTIVE_COUNT=$((ACTIVE_COUNT + 1))
      else STATUS="${YL}~${NC}"; ACTIVE_COUNT=$((ACTIVE_COUNT + 1)); fi
    fi
    fmt_bytes() {
      local b=$1
      if [[ $b -ge 1073741824 ]]; then printf "%.1fG" "$(echo "scale=1; $b/1073741824" | bc)"
      elif [[ $b -ge 1048576 ]];   then printf "%.1fM" "$(echo "scale=1; $b/1048576"   | bc)"
      elif [[ $b -ge 1024 ]];      then printf "%.1fK" "$(echo "scale=1; $b/1024"      | bc)"
      else printf "${b}B"; fi
    }
    TX_STR=$(fmt_bytes "$TX"); RX_STR=$(fmt_bytes "$RX")
    WG_PEERS="${WG_PEERS}    ${STATUS} ${CY}$(printf '%-12s' "$PEER_NAME")${NC}"
    WG_PEERS="${WG_PEERS} ${GR}$(printf '%-18s' "$ALLOWED_DISP")${NC}"
    WG_PEERS="${WG_PEERS} ${WH}$(printf '%-18s' "$EP_IP")${NC}"
    WG_PEERS="${WG_PEERS} ${HS_STR}  ${YL}↑${TX_STR} ↓${RX_STR}${NC}\n"
  done < <(wg show wg0 dump 2>/dev/null | tail -n +2)
  WG_PEERS="${WG_PEERS}    ${CY}Total${NC}: ${GR}${ACTIVE_COUNT}${NC} active of ${PEER_COUNT} configured\n"
fi

UPTIME=$(uptime -p 2>/dev/null | sed 's/up //')
LOAD=$(cut -d' ' -f1-3 /proc/loadavg)
MEM_TOTAL=$(free -m | awk '/^Mem/{print $2}')
MEM_USED=$(free -m  | awk '/^Mem/{print $3}')
DISK=$(df -h / | awk 'NR==2{print $3 " used of " $2 " (" $5 ")"}')

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
    ${CY}Disk /  ${NC} : ${GR}${DISK}${NC}

  ${WH}── Management ───────────────────────────────────────────────${NC}
    ${CY}Cockpit${NC}  : ${GR}https://$(ip -4 addr show | awk '/inet /{print $2}' | grep -v '127\.' | grep -v '10\.0\.' | tail -1 | cut -d/ -f1):9090${NC}
"
MOTD

chmod +x /etc/update-motd.d/10-examplemusic

if grep -q "^PrintMotd" /etc/ssh/sshd_config; then
  sed -i "s/^PrintMotd.*/PrintMotd yes/" /etc/ssh/sshd_config
else
  echo "PrintMotd yes" >> /etc/ssh/sshd_config
fi

cat > /etc/profile.d/motd.sh <<'EOF'
[[ -x /etc/update-motd.d/10-examplemusic ]] && /etc/update-motd.d/10-examplemusic
EOF

systemctl reload ssh 2>/dev/null || systemctl restart ssh
success "Dynamic MOTD configured."

# -------------------------------------------------------------------------------------------------
# 13. Sentinel file
# -------------------------------------------------------------------------------------------------
{
  echo "Configured by Example Music setup script"
  echo "Site        : ${SITE}"
  echo "City        : ${SITE_DISPLAY_CITY}"
  echo "Country     : ${SITE_DISPLAY_COUNTRY}"
  echo "Entity      : ${SITE_DISPLAY_ENTITY}"
  echo "Environment : ${ENV_LONG}"
  echo "LAN IP      : ${LAN_IP}"
  echo "Ansible IP  : ${ANSIBLE_IP}"
  echo "WG Role     : ${WG_ROLE}"
  [[ "$WG_ROLE" != "none" ]] && echo "WG Tunnel   : ${WG_TUNNEL_IP}/24"
  [[ "$WG_ROLE" == "hub-primary" || "$WG_ROLE" == "hub-regional" ]] && echo "WG Port     : ${WG_PORT}"
  [[ "$WG_ROLE" == "spoke" ]] && echo "WG Hub      : ${WG_HUB_ENDPOINT}"
  echo "WAN iface   : ${WAN_IFACE} (${WAN_MAC})"
  echo "WAN mode    : ${WAN_MODE}"
  [[ "$WAN_MODE" == "static" ]] && echo "WAN IP      : ${WAN_STATIC_IP}/24 gw ${WAN_STATIC_GW}"
  echo "LAN iface   : ${LAN_IFACE} (${LAN_MAC})"
  echo "Date        : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > /etc/.i_am_a_firewall
chmod 0444 /etc/.i_am_a_firewall
success "Sentinel file written."

# -------------------------------------------------------------------------------------------------
# 14. Final banner
# -------------------------------------------------------------------------------------------------
if [[ "$WAN_MODE" == "static" ]]; then
  WAN_IP_CURRENT="${WAN_STATIC_IP}"
else
  WAN_IP_CURRENT=$(ip -4 addr show "$WAN_IFACE" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || echo "DHCP pending — run: nmcli con up wan")
fi

echo
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  SETUP COMPLETE - ${SITE}${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "${CYAN}  Hostname      : $(hostname)${NC}"
echo -e "${CYAN}  WAN Interface : ${WAN_IFACE} (${WAN_MAC})  →  ${WAN_IP_CURRENT}${NC}"
echo -e "${CYAN}  LAN Interface : ${LAN_IFACE} (${LAN_MAC})  →  ${LAN_IP}/24${NC}"
echo -e "${CYAN}  DHCP Range    : ${DHCP_START} - ${DHCP_END}${NC}"
echo -e "${CYAN}  Ansible/PXE   : ${ANSIBLE_IP} (ansible.jukebox.internal)${NC}"
echo -e "${CYAN}  Cockpit URL   : https://${LAN_IP}:9090${NC}"
if [[ "$WAN_SSH" == "true" ]]; then
  [[ -n "${WAN_SSH_SRC:-}" ]] \
    && echo -e "${RED}  WAN SSH       : enabled (restricted to ${WAN_SSH_SRC})${NC}" \
    || echo -e "${RED}  WAN SSH       : enabled (open to all)${NC}"
else
  echo -e "${YELLOW}  WAN SSH       : disabled (LAN only)${NC}"
fi

if [[ "$WAN_ACTIVATE" == "false" ]]; then
  echo
  echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════╗${NC}"
  echo -e "${YELLOW}  ║  WAN was NOT activated — bring it up when ready:     ║${NC}"
  echo -e "${YELLOW}  ║    nmcli con up wan                                  ║${NC}"
  echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════╝${NC}"
fi

if [[ "$WG_ROLE" != "none" ]]; then
  echo

  if [[ "$WG_ROLE" == "hub-primary" || "$WG_ROLE" == "hub-regional" ]]; then
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}  WIREGUARD ${WG_ROLE^^} - ${SITE}${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${ORANGE}  Tunnel IP     : ${WG_TUNNEL_IP}/24${NC}"
    echo -e "${ORANGE}  Tunnel net    : ${WG_TUNNEL_NET}${NC}"
    echo -e "${ORANGE}  Listen port   : ${WG_PORT}${NC}"
    echo -e "${ORANGE}  WAN endpoint  : ${WAN_IP_CURRENT}:${WG_PORT}${NC}"
    echo -e "${ORANGE}  Public key    : ${THIS_PUBKEY}${NC}"
    echo -e "${ORANGE}  Saved at      : /etc/wireguard/public.key${NC}"
    echo
    echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}  ║     PASTE THIS STANZA INTO EACH PEER'S wg0.conf      ║${NC}"
    echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${GREEN}# ${SITE}${NC}"
    echo -e "${GREEN}[Peer]${NC}"
    echo -e "${GREEN}PublicKey = ${THIS_PUBKEY}${NC}"
    echo -e "${GREEN}Endpoint = ${WAN_IP_CURRENT}:${WG_PORT}${NC}"
    echo -e "${GREEN}AllowedIPs = ${WG_TUNNEL_NET}, ${SUBNET}.0/24${NC}"
    echo -e "${CYAN}  (Hub's wg0.conf needs ONLY this spoke's subnets in its peer block)${NC}"
    echo -e "${CYAN}  (The spoke's wg0.conf carries the full topology-aware AllowedIPs)${NC}"
    echo -e "${GREEN}PersistentKeepalive = 25${NC}"
    echo
    echo -e "${CYAN}  After pasting on the peer, apply live:${NC}"
    echo -e "${CYAN}  sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'${NC}"
    echo -e "${CYAN}  Then verify: sudo wg show${NC}"

  elif [[ "$WG_ROLE" == "spoke" ]]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}  WIREGUARD SPOKE - ${SITE}${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${ORANGE}  Tunnel IP     : ${WG_TUNNEL_IP}/24${NC}"
    echo -e "${ORANGE}  Primary hub   : ${WG_HUB_ENDPOINT}${NC}"
    [[ ${#WG_BACKUP_PEERS[@]} -gt 0 ]] && echo -e "${CYAN}  Backup hubs   : ${#WG_BACKUP_PEERS[@]} configured${NC}"
    echo -e "${ORANGE}  Public key    : ${THIS_PUBKEY}${NC}"
    echo -e "${ORANGE}  Saved at      : /etc/wireguard/public.key${NC}"
    echo
    echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}  ║      PASTE THIS STANZA INTO THE HUB'S wg0.conf       ║${NC}"
    echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════╝${NC}"
    echo
    # BUG FIX: original code re-ran `ip addr` and re-assigned WAN_IP here,
    # shadowing the variable set at the top of the final banner block and
    # being inconsistent with the hub path which used WAN_IP_CURRENT.
    echo -e "${GREEN}# ${SITE}${NC}"
    echo -e "${GREEN}[Peer]${NC}"
    echo -e "${GREEN}PublicKey = ${THIS_PUBKEY}${NC}"
    echo -e "${GREEN}Endpoint = ${WAN_IP_CURRENT}:51820${NC}"
    echo -e "${GREEN}AllowedIPs = ${WG_TUNNEL_NET}, ${SUBNET}.0/24${NC}"
    echo -e "${CYAN}  (Hub's wg0.conf needs ONLY this spoke's subnets in its peer block)${NC}"
    echo -e "${CYAN}  (The spoke's wg0.conf carries the full topology-aware AllowedIPs)${NC}"
    echo -e "${GREEN}PersistentKeepalive = 25${NC}"
    echo
    echo -e "${CYAN}  After pasting on the hub, apply live:${NC}"
    echo -e "${CYAN}  sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'${NC}"
    echo -e "${CYAN}  Then verify: sudo wg show${NC}"
    echo
    echo -e "${YELLOW}  Always retrievable: sudo cat /etc/wireguard/public.key${NC}"
  fi
fi

echo -e "${GREEN}============================================================${NC}"
echo
success "Firewall/router is live. DHCP: ${DHCP_START}-${DHCP_END}"
echo -e "${CYAN}  iPXE: DNS → ${LAN_IP}, boot → http://${ANSIBLE_IP}/bootstrap.ipxe${NC}"
echo

# -------------------------------------------------------------------------------------------------
# Reboot prompt
# -------------------------------------------------------------------------------------------------
echo
warn "A reboot is recommended to ensure all changes take full effect."
warn "This is especially important for NM profiles, sysctl, and WireGuard."
echo
read -rp $'\e[1;33m[!]\e[0m Reboot now? [y/N] ' REBOOT_NOW
REBOOT_NOW="${REBOOT_NOW:-n}"
if [[ "${REBOOT_NOW,,}" == "y" ]]; then
  info "Rebooting in 5 seconds — press Ctrl-C to cancel..."
  sleep 5
  reboot
else
  warn "Remember to reboot before testing — things may not work correctly until you do."
fi