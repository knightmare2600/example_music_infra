#!/usr/bin/env bash
# ===============================================================
# Example Music Limited -- BIND9 DNS Server Setup Script
# Target host  : ${THIS_HOSTNAME} (Debian trixie)
# Zone served  : jukebox.internal
# Static IP    : 192.168.139.8/24  (provisioning network, CLD .8 -- DNS server)
# Reverse zones: one db.192.168.X per site (~44 files) + provisioning /24
#
# Zone file is generated at install time from sites.csv --
# same single source of truth used by firewallme.sh and
# site-inventory-audit.py.  Adding a site means editing
# sites.csv only; re-run or use the reload alias.
#
# Forward records generated per site:
#   .1   EXARTR    (hardware router)
#   .2   EXARAC    (BMC slot 1)
#   .3   EXARAC    (BMC slot 2)
#   .4   EXARAC    (BMC slot 3)
#   .5   EXAPVE    (Proxmox node 1)
#   .6   EXAPVE    (Proxmox node 2)
#   .7   EXAPVE    (Proxmox node 3)
#   .10  EXADCS    (DC primary)
#   .11  EXADCS    (DC secondary)
#   .48  EXASBC    (VOIP SBC)  -- CLD: EXAPBX
#   .250 EXASWI    (Switch 1)
#   .251 EXASWI    (Switch 2)
#   .252 EXASWI    (Switch 3)
#   .253 EXAFWL    (Debian firewall)
#
# Plus CLD ancillary hosts:
#   192.168.69.9     EXAANSCLD001       (Ansible management)
#   192.168.139.8    ${THIS_HOSTNAME}   (this DNS server)
#   192.168.139.50   EXAPRVCLD001       (provisioning / PXE)
#   192.168.139.69   EXAFWLCLD001       (CLD firewall — WAN face on vRACK)
#   192.168.139.254  DC provider router (vRACK gateway — not EXA kit)
# ===============================================================

set -euo pipefail

# Suppress all apt/dpkg interactive prompts
export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

# Changelog:
# 2026-03-29 Initial release: Static IP 192.168.139.10 on PROV/CLD net. Hostname ${THIS_HOSTNAME}
#            (EXA/SRV/CLD/001, .10 per SUFFIX_MAP). Zone jukebox.internal generated from sites.csv.
#            Reverse zones generated for ALL site /24 subnets (~44 files). Forwarders: 1.1.1.1
#            (Cloudflare) + 9.9.9.9 (Quad9). zsh + bash aliases: reloadbind, checkbind, editzone.
#            MOTD, sentinel file, final banner.
# 2026-06-14 Fix: load_sites_csv() while-read loop dropped last CSV line when file had no trailing
#            newline (read returns non-zero at EOF, loop exits before processing that iteration).
#            VIE is the last line in sites.csv and has no trailing newline, so it never loads into
#            SITE_OCTET[] — no A or PTR records were generated for Vienna, it was absent from all
#            zone files.  Fixed with || [[ -n "$site" ]] on the while condition.
#            Fix: warn() now writes to stderr (>&2) for consistency with firewallme.sh & to prevent
#            any future $() subshell captures picking up warning text as data.
#            Fix: existing syntax error on nmcli con add for prov/static profile; trailing space
#            after backslash continuation broke the && chain, causing bash to reject script at that
#            line. Reformatted as proper multi-line continuation.
#            Fix: THIS_HOSTNAME was hardcoded to "exasrvcld001" with no detection or prompting. Now
#            reads current hostname, normalises to uppercase per site convention, presents it as a
#            default, & prompts the operator to confirm or override.
#            Fix: setup_zsh_for() returned immediately if .zshrc exists, so BIND aliases were never
#            available, zsh does not source /etc/profile.d automatically unlike bash. If .zshrc
#            already exists, function appends a profile.d source stanza if one is not present
#            Feat: DHCP pool $GENERATE stanzas added to forward & reverse zones. Pool is .100-.199
#            (100 leases), forward: dhcp01.site - dhcp100.site IN A 192.168.x.100-199, reverse: PTR
#            dhcp01.site.jukebox.internal for each octet. Use $GENERATE convention from:
#            https://retrorabble.wordpress.com/2013/08/29/dns-zones-for-generation-x/. CLD (139) is
#            exempt -- no DHCP pool there.
#            Fix: checkbind & editzone were aliases hardcoded to db.jukebox.internal. Converted to
#            shell functions accepting an optional zone file argument (bare filename or full path),
#            default to db.jukebox.internal. Zone name is auto-derived from filename: db.192.168.78
#            becomes 78.168.192.in-addr.arpa. Validation checks the file exists & lists available
#            zone files if not, editzone guards against non-root & only reloads if named-checkzone
#            passes.
#            Fix: zone file comments used UTF-8 box-drawing character U+2500 (─) for decorative 
#            separators. BIND accepts, but non UTF-8 locales render as mojibake (â<94><80> etc). So
#            replaced with ASCII hyphens on all zones ; -- lines. Terminal banner & named.conf //
#            comments are unchanged (BIND ignores // comments entirely).
#            Fix: all generated hostnames in zone & PTR files were lowercased via ${site,,} for the
#            site portion but role prefix (exa{dcs|fwl|rac} etc,) remained lowercase. Full name now
#            uppercase at construction via ${hostname^^} giving EXA{DCS|FWL}{EDI|ODE}001, matches
#            deployment convention. Applies to forward A records and all PTR records.

# ---------------------------------------------------------------
# Colour helpers  (identical style to firewallme.sh)
# ---------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[*]${NC} $*"; }
success() { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*" >&2; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ---------------------------------------------------------------
# Site data -- loaded from sites.csv (single source of truth)
#
# Looks for sites.csv in:
#   1. $SITES_CSV environment variable (override)
#   2. Same directory as this script
#   3. /etc/example-music/sites.csv  (system-wide install)
# ---------------------------------------------------------------
declare -A SITE_OCTET SITE_CITY SITE_COUNTRY SITE_ENTITY SITE_SUBNET

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

  info "Loading site data from: ${csv_path}"
  local first=1
  # BUG FIX: `while read` silently drops the last line of a file with no
  # trailing newline — read returns non-zero at EOF so the loop exits without
  # processing that final iteration.  sites.csv has no trailing newline; VIE
  # is the last entry and was therefore never loaded, so no A/PTR records were
  # generated for Vienna and it was absent from all zone files.
  # Fixed with || [[ -n "$site" ]] on the while condition.
  while IFS=',' read -r site city country cc subnet gateway dc fw landline mobile tz ansible_region entity _rest \
      || [[ -n "$site" ]]; do
    [[ "${first}" -eq 1 ]] && { first=0; continue; }   # skip header row
    site="${site// /}"
    [[ -z "${site}" ]] && continue
    # Skip BRD -- legacy alias for BER, BER covers it
    [[ "${site}" == "BRD" ]] && continue
    local octet
    octet=$(echo "${subnet}" | awk -F'.' '{print $3}')
    [[ -z "${octet}" || "${octet}" == "N" ]] && continue  # skip N/A subnets
    SITE_OCTET["${site}"]="${octet}"
    SITE_CITY["${site}"]="${city}"
    SITE_COUNTRY["${site}"]="${country}"
    SITE_ENTITY["${site}"]="${entity}"
    SITE_SUBNET["${site}"]="${subnet}"
  done < "${csv_path}"

  success "Loaded ${#SITE_OCTET[@]} sites from CSV."
}

load_sites_csv

# Sort sites by octet for deterministic output (needed early)
mapfile -t SORTED_SITES < <(
  for site in "${!SITE_OCTET[@]}"; do
    echo "${SITE_OCTET[$site]} ${site}"
  done | sort -n | awk '{print $2}'
)

# ---------------------------------------------------------------
# IP collision detection  (lifted from firewallme.sh)
# ---------------------------------------------------------------
ip_in_use() {
  local ip="$1"
  if ping -c1 -W1 "$ip" &>/dev/null 2>&1; then
    return 0
  fi
  if command -v arping &>/dev/null; then
    local gw_iface
    gw_iface=$(ip route | awk '/default/{print $5}' | head -1)
    if [[ -n "${gw_iface}" ]] && arping -c1 -W1 -I "$gw_iface" "$ip" &>/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

# ---------------------------------------------------------------
# Must run as root
# ---------------------------------------------------------------
[[ $EUID -ne 0 ]] && die "Run this script with sudo or as root."

# ---------------------------------------------------------------
# Banner
# ---------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      Example Music: BIND9 DNS Server Setup           ║${NC}"
echo -e "${CYAN}║      EXASRVCLD001  --  jukebox.internal              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}  Running on hostname: ${GREEN}$(hostname)${NC}"
echo

# ---------------------------------------------------------------
# 0. Bootstrap packages
# ---------------------------------------------------------------
info "Bootstrapping required packages..."
apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true

BOOTSTRAP_PKGS=()
command -v named    &>/dev/null || BOOTSTRAP_PKGS+=(bind9 bind9utils)
command -v dig      &>/dev/null || BOOTSTRAP_PKGS+=(dnsutils)
command -v arping   &>/dev/null || BOOTSTRAP_PKGS+=(arping)
command -v ip       &>/dev/null || BOOTSTRAP_PKGS+=(iproute2)
command -v nmcli    &>/dev/null || BOOTSTRAP_PKGS+=(network-manager)
command -v vim      &>/dev/null || BOOTSTRAP_PKGS+=(vim)
command -v curl     &>/dev/null || BOOTSTRAP_PKGS+=(curl)
command -v tmux     &>/dev/null || BOOTSTRAP_PKGS+=(tmux)
command -v jq       &>/dev/null || BOOTSTRAP_PKGS+=(jq)
command -v grc      &>/dev/null || BOOTSTRAP_PKGS+=(grc)
command -v zsh      &>/dev/null || BOOTSTRAP_PKGS+=(zsh zsh-autosuggestions zsh-syntax-highlighting)
command -v bc       &>/dev/null || BOOTSTRAP_PKGS+=(bc)

if [[ ${#BOOTSTRAP_PKGS[@]} -gt 0 ]]; then
  info "Installing: ${BOOTSTRAP_PKGS[*]}"
  apt-get install -y -qq -o=Dpkg::Use-Pty=0 "${BOOTSTRAP_PKGS[@]}" > /dev/null
fi
success "Packages ready."

# ---------------------------------------------------------------
# Environment
# ---------------------------------------------------------------
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
    *) warn "Invalid or empty — defaulting to production"; ENV_LONG="production" ;;
  esac
  echo "$ENV_LONG" > /etc/.environment
  success "Environment set to: ${ENV_LONG}"
fi

# ---------------------------------------------------------------
# Purge unused locales
# ---------------------------------------------------------------
info "Stripping unused locales..."
debconf-set-selections <<'DEBCONF'
localepurge localepurge/nopurge multiselect en_GB.UTF-8, en_US.UTF-8
localepurge localepurge/verbose boolean false
localepurge localepurge/none_selected boolean false
localepurge localepurge/quickndirty boolean false
DEBCONF
apt-get install -y -qq -o=Dpkg::Use-Pty=0 localepurge > /dev/null
localepurge > /dev/null
success "Unused locales purged."

# ---------------------------------------------------------------
# zsh setup  (root + ansible users, same as firewallme.sh)
# ---------------------------------------------------------------
setup_zsh_for() {
  local user="$1"
  local home prompt_colour
  home=$(getent passwd "${user}" | cut -d: -f6)
  [[ -z "${home}" ]] && return

  info "Setting up zsh for ${user}..."
  prompt_colour="green"
  [[ "${user}" == "root" ]] && prompt_colour="red"

  if [[ ! -f "${home}/.zshrc" ]]; then
    cat > "${home}/.zshrc" <<ZSHRC
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
%F{${prompt_colour}}%m%f:%F{cyan}%~%f> '
alias ls='ls --color=auto'
alias ll='ls -lah'
alias grep='grep --color=auto'
if (( \$+commands[grc] )); then
  GRC_ALIASES=true
  [[ -f /etc/profile.d/grc.sh ]] && source /etc/profile.d/grc.sh
fi
# zsh does not source /etc/profile.d automatically unlike bash.
# Source it here so BIND aliases (and any other profile.d scripts) are available.
for _f in /etc/profile.d/*.sh; do [[ -r "\$_f" ]] && source "\$_f"; done
unset _f
ZSHRC
    chown "${user}:${user}" "${home}/.zshrc"
    chsh -s "$(command -v zsh)" "${user}"
    success "zsh .zshrc written for ${user}."
  else
    # BUG FIX: previously returned immediately here — BIND aliases were written
    # to /etc/profile.d/bind-aliases.sh but zsh does NOT source /etc/profile.d
    # automatically, so they were silently never available in zsh sessions.
    # If .zshrc already exists (from firewallme.sh / ansibleme.sh), append
    # the profile.d source stanza if it is not already present.
    if ! grep -q "profile.d" "${home}/.zshrc" 2>/dev/null; then
      cat >> "${home}/.zshrc" <<'ZSHRC_APPEND'

# Added by bindme.sh -- zsh does not source /etc/profile.d automatically.
# This ensures BIND aliases and other profile.d scripts are always available.
for _f in /etc/profile.d/*.sh; do [[ -r "$_f" ]] && source "$_f"; done
unset _f
ZSHRC_APPEND
      success "profile.d source stanza appended to ${user}'s existing .zshrc."
    else
      success "${user}'s .zshrc already sources profile.d -- no change needed."
    fi
    chsh -s "$(command -v zsh)" "${user}" 2>/dev/null || true
  fi
}

setup_zsh_for root
setup_zsh_for ansible

# ---------------------------------------------------------------
# bash aliases  (profile.d -- picked up by bash and dash)
# ---------------------------------------------------------------
info "Writing BIND management aliases to /etc/profile.d/bind-aliases.sh ..."
cat > /etc/profile.d/bind-aliases.sh <<'ALIASES'
# Example Music -- BIND9 management aliases and functions
# Written by bindme.sh  (auto-generated -- do not edit by hand)
# Works in bash and zsh (sourced via /etc/profile.d)

# Simple aliases -- no parameters needed
alias bindstatus='systemctl status named'
alias bindlog='journalctl -u named -f'
alias reloadbind='rndc reload jukebox.internal && echo "[+] Zone reloaded." || echo "[!] Reload failed -- check: journalctl -u named -n 20"'

# _bind_zonename FILE
# Derives the BIND zone name from a db file basename.
#   db.jukebox.internal  -> jukebox.internal
#   db.192.168.139       -> 139.168.192.in-addr.arpa
#   db.192.168.78        -> 78.168.192.in-addr.arpa
_bind_zonename() {
  local base="${1#/etc/bind/}"   # strip path if passed
  base="${base#db.}"             # strip leading db.
  # Detect reverse zone pattern: three dotted octets e.g. 192.168.78
  if [[ "$base" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    echo "${BASH_REMATCH[3]}.${BASH_REMATCH[2]}.${BASH_REMATCH[1]}.in-addr.arpa"
  else
    echo "$base"
  fi
}

# _bind_require_root
# Exits with a clear error if not running as root.
_bind_require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "[!] This command writes to /etc/bind/ and needs root. Re-run with sudo." >&2
    return 1
  fi
}

# checkbind [zone-file]
# Runs named-checkzone against a zone file.
# Defaults to db.jukebox.internal if no argument given.
# Accepts bare filename (db.192.168.78) or full path.
checkbind() {
  local file="${1:-db.jukebox.internal}"
  # Normalise: strip any path prefix so we always work from /etc/bind/
  local base="${file##*/}"
  local fullpath="/etc/bind/${base}"

  if [[ ! -f "$fullpath" ]]; then
    echo "[!] Zone file not found: ${fullpath}" >&2
    echo "    Available zone files:" >&2
    ls /etc/bind/db.* 2>/dev/null | sed 's|/etc/bind/||' | sed 's/^/      /' >&2
    return 1
  fi

  local zone
  zone=$(_bind_zonename "$base")
  echo "[*] Checking zone '${zone}' using ${fullpath}..."
  named-checkzone "$zone" "$fullpath"
}

# editzone [zone-file]
# Opens a zone file in vim, then validates it, then reloads if valid.
# Defaults to db.jukebox.internal if no argument given.
editzone() {
  _bind_require_root || return 1

  local file="${1:-db.jukebox.internal}"
  local base="${file##*/}"
  local fullpath="/etc/bind/${base}"

  if [[ ! -f "$fullpath" ]]; then
    echo "[!] Zone file not found: ${fullpath}" >&2
    echo "    Available zone files:" >&2
    ls /etc/bind/db.* 2>/dev/null | sed 's|/etc/bind/||' | sed 's/^/      /' >&2
    return 1
  fi

  local zone
  zone=$(_bind_zonename "$base")
  echo "[*] Editing zone '${zone}' -- ${fullpath}"

  vim "$fullpath"

  echo "[*] Validating..."
  if named-checkzone "$zone" "$fullpath"; then
    echo "[*] Reloading zone '${zone}'..."
    rndc reload "$zone" && echo "[+] Zone '${zone}' reloaded." || echo "[!] rndc reload failed -- check: journalctl -u named -n 20" >&2
  else
    echo "[!] Validation failed -- zone NOT reloaded. Fix errors and re-run checkbind ${base}" >&2
    return 1
  fi
}
ALIASES
chmod 0644 /etc/profile.d/bind-aliases.sh
success "BIND aliases written."

# ---------------------------------------------------------------
# 1. Network interface detection
# ---------------------------------------------------------------
PROV_NET_DEFAULT="192.168.139"

read -rp "Provisioning subnet [${PROV_NET_DEFAULT}]: " PROV_NET
PROV_NET="${PROV_NET:-${PROV_NET_DEFAULT}}"

read -rp "Provisioning Network gateway [${PROV_NET}.254]: " GW_OCTET
GW_OCTET="${GW_OCTET:-254}"
PROV_GW="${PROV_NET}.${GW_OCTET}"

read -rp "IP Address of tihs DNS server [${PROV_NET}.10]: " DNS_OCTET
DNS_OCTET="${DNS_OCTET:-10}"
DNS_IP="${PROV_NET}.${DNS_OCTET}"

info "Detecting interface on provisioning network (${PROV_NET}.x)..."
PROV_IFACE=""
for iface in $(ls /sys/class/net/); do
  [[ "$iface" == "lo" ]] && continue
  ip_addr=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP "(?<=inet\s)${PROV_NET//./\\.}\.\d+" | head -1)
  if [[ -n "$ip_addr" ]]; then
    PROV_IFACE="$iface"
    success "Detected provisioning interface: ${PROV_IFACE} (currently ${ip_addr})"
    break
  fi
done

if [[ -z "$PROV_IFACE" ]]; then
  warn "Could not auto-detect provisioning interface."
  AVAILABLE_IFACES=($(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | grep -v '@'))
  read -rp "Enter interface name (available: ${AVAILABLE_IFACES[*]}): " PROV_IFACE
  PROV_IFACE="${PROV_IFACE:-${AVAILABLE_IFACES[0]:-ens33}}"
fi


# ---------------------------------------------------------------
# 2. IP collision check
# ---------------------------------------------------------------
info "Checking whether ${DNS_IP} is already in use..."
if ip_in_use "${DNS_IP}"; then
  die "${DNS_IP} is already in use on the network. Resolve the conflict before continuing."
fi
success "${DNS_IP} is free -- proceeding."

# ---------------------------------------------------------------
# 3. Pin interface name via systemd .link (survives reboots)
# ---------------------------------------------------------------
PROV_MAC=$(cat "/sys/class/net/${PROV_IFACE}/address" 2>/dev/null)
info "Pinning ${PROV_IFACE} (MAC ${PROV_MAC}) via systemd .link..."
mkdir -p /etc/systemd/network
cat > /etc/systemd/network/10-prov.link <<EOF
# Example Music -- provisioning interface pin
# Written by bindme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# MAC: ${PROV_MAC}  was: ${PROV_IFACE}
[Match]
MACAddress=${PROV_MAC}
[Link]
Name=${PROV_IFACE}
EOF
success "Interface pin written."

# ---------------------------------------------------------------
# 4. Configure static IP via NetworkManager
#    IP does not need to be live during this run -- reboot applies it.
# ---------------------------------------------------------------
info "Configuring static IP via NetworkManager..."

# Mask ifupdown units so they don't fight NM over the interface
systemctl disable networking.service 2>/dev/null || true
systemctl mask    networking.service 2>/dev/null || true
systemctl mask    "ifup@${PROV_IFACE}.service" 2>/dev/null || true

# Remove interface from /etc/network/interfaces if present
if [[ -f /etc/network/interfaces ]]; then
  if grep -qE "^(auto|allow-|iface)\s+${PROV_IFACE}" /etc/network/interfaces 2>/dev/null; then
    warn "Removing ifupdown stanza for ${PROV_IFACE} from /etc/network/interfaces..."
    cp -n /etc/network/interfaces /etc/network/interfaces.bak
    sed -i "/^auto\s\+${PROV_IFACE}\b/d"     /etc/network/interfaces
    sed -i "/^allow-.*\s${PROV_IFACE}\b/d"    /etc/network/interfaces
    sed -i "/^iface\s\+${PROV_IFACE}\b/,/^[^[:space:]]/{ /^iface\s\+${PROV_IFACE}\b/d; /^[^[:space:]]/!d; }" /etc/network/interfaces
    success "Cleaned /etc/network/interfaces"
  fi
fi

# Critical: ensure NM is actually managing interfaces
# Debian ships with managed=false in the [ifupdown] section
NM_CONF="/etc/NetworkManager/NetworkManager.conf"
if grep -q "managed=false" "${NM_CONF}" 2>/dev/null; then
  warn "NetworkManager.conf has managed=false -- fixing..."
  sed -i "s/managed=false/managed=true/" "${NM_CONF}"
fi

systemctl restart NetworkManager
sleep 3

# Remove stale profiles
nmcli con delete "prov-static" 2>/dev/null || true
while IFS=: read -r profile device rest; do
  [[ -z "${profile}" ]] && continue
  if [[ "${device}" == "--" || "${profile}" == *"Wired connection"* || "${profile}" == *"Ifupdown"* ]]; then
    warn "Deleting stale NM profile: ${profile}"
    nmcli con delete "${profile}" 2>/dev/null || true
  fi
done < <(nmcli -t -f NAME,DEVICE con show)

# Create the static profile
nmcli con add type ethernet ifname "${PROV_IFACE}" con-name "prov-static" ipv4.method manual \
  ipv4.addresses "${DNS_IP}/24" ipv4.gateway "${PROV_GW}" ipv4.dns "127.0.0.1" \
  ipv4.dns-search "jukebox.internal" ipv6.method ignore \
  && success "NM profile prov-static written -- will apply on reboot." \
  || warn "nmcli con add returned non-zero -- check: nmcli connection show prov-static"

# ---------------------------------------------------------------
# 5. Hostname
# ---------------------------------------------------------------
# BUG FIX: previously hardcoded to "${THIS_HOSTNAME_LOWER}" — always overwrote
# whatever hostname was set, with no detection or prompting.
# Now: detect the EXA* convention from the current hostname (set during
# PXE/provisioning), confirm with the operator, fall back to a prompt
# if the hostname doesn't match the convention or needs changing.
info "Detecting hostname for this DNS server..."
CURRENT_HOSTNAME=$(hostname -s)
SUGGESTED_HOSTNAME=""

# Try to extract from current hostname if it matches EXA* convention
if [[ "${CURRENT_HOSTNAME}" =~ ^[Ee][Xx][Aa] ]]; then
  SUGGESTED_HOSTNAME="${CURRENT_HOSTNAME^^}"   # normalise to uppercase
  info "Detected EXA-convention hostname: ${SUGGESTED_HOSTNAME}"
else
  # Default suggestion for the DNS server role
  SUGGESTED_HOSTNAME="EXASRVCLD001"
  warn "Current hostname '${CURRENT_HOSTNAME}' does not match EXA* convention."
fi

read -rp "  Hostname for this DNS server [${SUGGESTED_HOSTNAME}]: " HOSTNAME_INPUT
THIS_HOSTNAME="${HOSTNAME_INPUT:-${SUGGESTED_HOSTNAME}}"
THIS_HOSTNAME="${THIS_HOSTNAME^^}"   # enforce uppercase per site convention

info "Setting hostname to ${THIS_HOSTNAME}..."
hostnamectl set-hostname "${THIS_HOSTNAME}"
grep -q "${THIS_HOSTNAME,,}" /etc/hosts 2>/dev/null || \
  echo "127.0.1.1  ${THIS_HOSTNAME,,}.jukebox.internal  ${THIS_HOSTNAME,,}" >> /etc/hosts
success "Hostname set to ${THIS_HOSTNAME}."

# Derive the lowercase FQDN form used in zone files (DNS is case-insensitive
# but conventional lowercase in zone files is fine; the hostname itself is
# stored uppercase in the sentinel and banners per your convention).
THIS_HOSTNAME_LOWER="${THIS_HOSTNAME,,}"

# ---------------------------------------------------------------
# 6. BIND9 named.conf.options
#    - Recursion allowed from provisioning net only
#    - Forwarders: 1.1.1.1 + 9.9.9.9
#    - DNSSEC validation auto
# ---------------------------------------------------------------
info "Writing /etc/bind/named.conf.options..."
cat > /etc/bind/named.conf.options <<NAMEDOPTS
// ============================================================
// named.conf.options -- Example Music Limited
// ${THIS_HOSTNAME}  --  jukebox.internal DNS
// Written by bindme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
//
// Recursion is permitted ONLY from the provisioning network
// (192.168.139.0/24).  All other clients get authoritative
// answers only -- no recursion, no forwarding.
// ============================================================

options {
  directory "/var/cache/bind";

  // ── Forwarders ────────────────────────────────────────────
  // Used for names outside jukebox.internal.
  // Only reached when the querying client is in allow-recursion.
  forwarders {
    1.1.1.1;    // Cloudflare
    9.9.9.9;    // Quad9
  };

  forward only;

  // ── Access control ────────────────────────────────────────
  // Queries accepted from anywhere (this is a split-horizon DNS
  // inside an isolated provisioning network so the exposure is
  // limited, but lock it down further here if needed).
  allow-query { any; };

  // Recursion only for provisioning network clients.
  // Spokes and site routers query for jukebox.internal names
  // only -- they do not need recursion.
  allow-recursion { 192.168.139.0/24; localhost; };

  // ── Listen ────────────────────────────────────────────────
  listen-on     { 127.0.0.1; 192.168.139.8; };
  listen-on-v6  { none; };

  // ── DNSSEC ────────────────────────────────────────────────
  dnssec-validation auto;

  // ── Misc ──────────────────────────────────────────────────
  auth-nxdomain no;    // RFC 2308 compliance
  version "not disclosed";
};
NAMEDOPTS
success "named.conf.options written."

# ---------------------------------------------------------------
# 7. named.conf.local  (zone declarations)
# ---------------------------------------------------------------
info "Writing /etc/bind/named.conf.local..."
cat > /etc/bind/named.conf.local <<NAMEDLOCAL
// ============================================================
// named.conf.local -- Example Music Limited
// ${THIS_HOSTNAME}  --  jukebox.internal DNS
// Written by bindme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
//
// Forward zone:
//   jukebox.internal         -- all sites, generated from sites.csv
//
// Reverse zones:
//   139.168.192.in-addr.arpa -- DEDICATED provisioning network zone.
//                               Contains ancillary hosts (.10 .50 .69)
//                               AND the FWL WAN addresses for every site.
//                               Each site firewall has a WAN interface on
//                               192.168.139.0/24 at 192.168.139.{octet}
//                               where {octet} is the site's /24 third octet.
//                               e.g. EDI = 192.168.131.0/24
//                                      -> FWL WAN = 192.168.139.131
//                               CLD's firewall lands at .139 (its own octet).
//                               This zone is NOT generated by the per-site
//                               loop -- it has its own dedicated section.
//
//   X.168.192.in-addr.arpa   -- One per site /24 (excluding CLD).
//                               Maps to /etc/bind/db.192.168.X
//                               PTR records for standard SUFFIX_MAP addresses.
//
// Adding a site: edit sites.csv and re-run bindme.sh (or regen-zone.sh).
// named.conf.local is fully regenerated so no manual editing is needed.
// ============================================================

// ── Forward zone: jukebox.internal ───────────────────────────
zone "jukebox.internal" {
  type master;
  file "/etc/bind/db.jukebox.internal";
  allow-query   { any; };
  allow-transfer { none; };   // add secondary IPs here if a slave is added
  notify no;
};

// ── Reverse zone: provisioning network 192.168.139.0/24 ──────
// Dedicated zone -- contains FWL WAN IPs for all sites + ancillary hosts.
// NOT generated by the per-site loop (CLD subnet would otherwise collide).
zone "139.168.192.in-addr.arpa" {
  type master;
  file "/etc/bind/db.192.168.139";
  allow-query   { any; };
  allow-transfer { none; };
  notify no;
};

NAMEDLOCAL

# Append a reverse zone stanza for every site EXCEPT CLD.
# CLD's subnet (192.168.139.0/24) is the provisioning network --
# it is covered by the dedicated 139 zone above.
for site in "${SORTED_SITES[@]}"; do
  [[ "${site}" == "CLD" ]] && continue
  octet="${SITE_OCTET[$site]}"
  cat >> /etc/bind/named.conf.local <<ZONE_STANZA
// ── Reverse zone: 192.168.${octet}.0/24  (${site} -- ${SITE_CITY[$site]}) ──
zone "${octet}.168.192.in-addr.arpa" {
  type master;
  file "/etc/bind/db.192.168.${octet}";
  allow-query   { any; };
  allow-transfer { none; };
  notify no;
};

ZONE_STANZA
done
non_cld_count=$(( ${#SITE_OCTET[@]} - 1 ))
success "named.conf.local written (1 forward + 1 provisioning + ${non_cld_count} site reverse zones)."

# ---------------------------------------------------------------
# 8. Generate forward zone: jukebox.internal
#
# SOA serial format: YYYYMMDDnn  (date-based, nn=00 on first run)
# TTL: 300s (5 minutes) -- short enough that re-runs propagate fast
#      on a provisioning network that changes frequently.
#
# Host naming follows the same SUFFIX_MAP as site-inventory-audit.py:
#   .1   EXARTR   .2/.3/.4  EXARAC   .5/.6/.7  EXAPVE
#   .10/.11 EXADCS  .48 EXASBC (EXAPBX for CLD)
#   .250/.251/.252 EXASWI  .253 EXAFWL
#
# CLD ancillary hosts are added explicitly after the generated block:
#   .10  ${THIS_HOSTNAME}   (this server)
#   .50  EXAPRVCLD001   (provisioning/PXE)
#   .9   EXAANSCLD001   (Ansible)
#
# NOTE: BRD is skipped (legacy alias for BER -- BER covers it).
# ---------------------------------------------------------------
ZONE_FILE="/etc/bind/db.jukebox.internal"
SERIAL=$(date -u +%Y%m%d)01

info "Generating forward zone file: ${ZONE_FILE}  (serial ${SERIAL})..."

cat > "${ZONE_FILE}" <<ZONE_HEADER
; ============================================================
; /etc/bind/db.jukebox.internal
; Example Music Limited -- jukebox.internal forward zone
;
; Authoritative DNS: ${THIS_HOSTNAME} (192.168.139.8)
; Zone:              jukebox.internal
; Generated by:      bindme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
;
; DO NOT EDIT BY HAND unless adding one-off records at the bottom.
; The bulk of this file is generated from sites.csv.
; To regenerate after a sites.csv change, re-run bindme.sh or use:
;   /usr/local/sbin/regen-zone.sh && reloadbind
;
; SOA serial format: YYYYMMDDnn
;   Increment nn (00-99) when making manual edits on the same day.
;   bindme.sh always writes nn=01 on a fresh run.
;
; TTL 300 (5 minutes) is intentional -- provisioning networks
; change frequently and a short TTL ensures propagation is fast.
;
; Reverse PTR records are only maintained for the provisioning
; subnet (192.168.139/24) in db.192.168.X per site.  No further
; reverse zones are out of scope for this server.
; ============================================================

\$ORIGIN jukebox.internal.
\$TTL 300

; -- SOA + NS -------------------------------------------------
@   IN  SOA  ${THIS_HOSTNAME_LOWER}.jukebox.internal.  hostmaster.jukebox.internal. (
              ${SERIAL}  ; serial   YYYYMMDDnn
              3600       ; refresh  1 hour
              900        ; retry    15 minutes
              604800     ; expire   1 week
              300        ; minimum  5 minutes
            )

@   IN  NS   ${THIS_HOSTNAME_LOWER}.jukebox.internal.

; -- DNS server itself -----------------------------------------
${THIS_HOSTNAME_LOWER}  IN  A  192.168.139.8

; -- CLD ancillary / provisioning infrastructure ---------------
; These are stable, hardcoded hosts in the provisioning subnet that are
; not generated by the per-site suffix_map loop below.
; (.10 EXADCSCLD001, .11 EXADCSCLD002, .12 EXARUDCLD001, .48 EXACLDPBX001
;  are generated by the suffix_map loop with CLD special-cases.)
exafwlcld001  IN  A  192.168.139.139  ; CLD firewall (WAN face on vRACK)
exasvrcld002  IN  A  192.168.139.20   ; Windows Admin Centre
exaprvcld001  IN  A  192.168.139.50   ; Provisioning server (PXE, HTTP, iPXE)
exaanscld001  IN  A  192.168.139.9   ; Ansible management node

; -- Firewall WAN addresses on provisioning network ------------
; Each site firewall (EXAFWL) has a WAN interface on 192.168.139.0/24.
; The host octet mirrors the site subnet third octet.
; e.g. EDI  192.168.131.0/24  ->  exafwledi001 IN A 192.168.139.131
; These A records allow name resolution of firewall WAN faces from
; the provisioning network without knowing each site octet by heart.
; Generated from sites.csv at install time.

ZONE_HEADER

# ----------- Per-site generated records ----------------------
# Suffix map matches site-inventory-audit.py SUFFIX_MAP exactly.
# Array of "suffix:prefix:seq" tuples.
declare -a SUFFIX_MAP=(
  "1:exartr:1"
  "2:exarac:1"
  "3:exarac:2"
  "4:exarac:3"
  "5:exapve:1"
  "6:exapve:2"
  "7:exapve:3"
  "10:exadcs:1"
  "11:exadcs:2"
  "12:exarry:1"
  "48:exasbc:1"
  "250:exaswi:1"
  "251:exaswi:2"
  "252:exaswi:3"
  "253:exafwl:1"
)

# Group records by role for readability
declare -A ROLE_COMMENT=(
  [exartr]="Routers / hardware gateways (unmanaged)"
  [exarac]="BMC / RAC (iDRAC, iLO, RAC emulators)"
  [exapve]="Proxmox VE nodes"
  [exadcs]="Domain Controllers"
  [exarry]="Rudder Relay nodes"
  [exarud]="Rudder Server (CLD)"
  [exasbc]="VOIP SBC nodes"
  [exaswi]="Switches (unmanaged)"
  [exafwl]="Firewalls (Debian FWL nodes)"
  [exapbx]="PBX (CLD provisioning network)"
)

# We'll write records role by role for a tidy zone file.
declare -a ROLE_ORDER=(exafwl exartr exadcs exapve exarac exaswi exarry exarud exasbc exapbx)

# Build an in-memory associative array: role -> list of "hostname IP" lines
declare -A ROLE_RECORDS
for r in "${ROLE_ORDER[@]}"; do ROLE_RECORDS["${r}"]=""; done

# Sort sites by octet for deterministic output
mapfile -t SORTED_SITES < <(
  for site in "${!SITE_OCTET[@]}"; do
    echo "${SITE_OCTET[$site]} ${site}"
  done | sort -n | awk '{print $2}'
)

for site in "${SORTED_SITES[@]}"; do
  octet="${SITE_OCTET[$site]}"
  base="192.168.${octet}"

  for entry in "${SUFFIX_MAP[@]}"; do
    suffix="${entry%%:*}"
    rest="${entry#*:}"
    prefix="${rest%%:*}"
    seq="${rest##*:}"

    ip="${base}.${suffix}"

    # CLD .12 is the Rudder Server (EXARUDCLD001), not a Relay (EXARRY)
    # CLD .48 is EXAPBX not EXASBC
    if [[ "${suffix}" == "12" && "${site}" == "CLD" ]]; then
      hostname="EXARUDCLD001"
      role="exarud"
    elif [[ "${suffix}" == "48" && "${site}" == "CLD" ]]; then
      hostname="EXAPBXCLD001"
      role="exapbx"
    else
      hostname="${prefix}${site}$(printf '%03d' "${seq}")"
      hostname="${hostname^^}"
      role="${prefix}"
    fi

    # Pad for alignment:  hostname (left, 45 chars)  IN  A  ip
    line=$(printf "%-45s IN  A  %s" "${hostname}" "${ip}")
    ROLE_RECORDS["${role}"]+="${line}"$'\n'
  done
done

# Write role sections to zone file
{
  for role in "${ROLE_ORDER[@]}"; do
    [[ -z "${ROLE_RECORDS[$role]:-}" ]] && continue
    comment="${ROLE_COMMENT[$role]:-${role}}"
    echo "; -- ${comment} $(printf '%*s' $((50 - ${#comment})) '' | tr ' ' '-')"
    echo "${ROLE_RECORDS[$role]}"
  done
} >> "${ZONE_FILE}"

# Append FWL WAN A records (192.168.139.{octet} per site)
{
  echo "; -- Firewall WAN addresses (192.168.139.{octet}) --------------"
  for site in "${SORTED_SITES[@]}"; do
    octet="${SITE_OCTET[$site]}"
    wan_ip="192.168.139.${octet}"
    # CLD FWL WAN is .139 -- still valid, include it
    hostname="EXAFWL${site}001"
    printf "%-45s IN  A  %s  ; %s WAN face on provisioning net\n" \
      "${hostname}-wan" "${wan_ip}" "${site}"
  done
  echo ""
} >> "${ZONE_FILE}"

# Append DHCP pool $GENERATE stanzas (per your 2013 convention):
#   .100 -> dhcp01.SITE, .101 -> dhcp02.SITE ... .199 -> dhcp100.SITE
# $GENERATE syntax: range  LHS  type  RHS
#   $ in LHS/RHS is replaced by the iterator value.
#   ${-99,2,d} subtracts 99 from $ and formats as 2-digit decimal.
# CLD is on the provisioning net (139) and is exempt -- no DHCP pool there.
{
  echo "; -- DHCP pool (\$GENERATE) ------------------------------------"
  echo "; .100-.199 per site: dhcp01.SITE through dhcp100.SITE"
  echo "; These are forward-only (PTR \$GENERATE is in each db.192.168.x file)."
  echo ""
  for site in "${SORTED_SITES[@]}"; do
    [[ "${site}" == "CLD" ]] && continue
    octet="${SITE_OCTET[$site]}"
    site_lower="${site,,}"
    echo "; ${site} -- 192.168.${octet}.100-199"
    echo "\$GENERATE 100-199 dhcp\${-99,2,d}.${site_lower} IN A 192.168.${octet}.\$"
    echo ""
  done
} >> "${ZONE_FILE}"

success "Forward zone file written ($(grep -c 'IN  A' "${ZONE_FILE}") A records + \$GENERATE blocks)."

# ---------------------------------------------------------------
# 9a. Generate dedicated provisioning reverse zone: db.192.168.139
#
# This zone covers 192.168.139.0/24 (the provisioning network).
# It contains two sets of records:
#
#   (i)  Ancillary hosts -- ${THIS_HOSTNAME} (.10), EXAPRVCLD001 (.50),
#        EXAANSCLD001 (.9)
#
#   (ii) FWL WAN PTR records -- every site firewall has a WAN
#        interface on this subnet.  The host octet equals the site
#        subnet's third octet.
#        e.g. EDI = 192.168.131.0/24  ->  .131  IN PTR exafwledi001-wan
#        CLD's firewall lands at .139 (its own octet).
#
# This file is written directly (not from the per-site loop) so
# that CLD's site subnet does not end up as a duplicate zone.
# ---------------------------------------------------------------
PROV_REV_FILE="/etc/bind/db.192.168.139"
info "Generating provisioning network reverse zone: ${PROV_REV_FILE}..."

cat > "${PROV_REV_FILE}" <<PROVREVHDR
; ============================================================
; /etc/bind/db.192.168.139
; Example Music Limited -- provisioning network reverse zone
;
; Zone:    139.168.192.in-addr.arpa
; Covers:  192.168.139.0/24  (provisioning network)
; Server:  ${THIS_HOSTNAME} (192.168.139.8)
; Generated by: bindme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
;
; PTR records:
;   .8   ${THIS_HOSTNAME}   -- DNS/BIND9 server
;   .12  EXARUDCLD001   -- Rudder Server
;   .20  EXASVRCLD002   -- Windows Admin Centre
;   .48  EXACLDPBX001   -- Central 3CX PBX
;   .50  EXAPRVCLD001   -- provisioning / PXE server
;   .9   EXAANSCLD001   -- Ansible management node
;   .X   EXAFWL{site}001-wan  -- firewall WAN face for each site
;        where X = the site's /24 third octet (from sites.csv)
;
; The -wan suffix distinguishes the firewall's provisioning-network
; address from its LAN address (EXAFWL{site}001 in its own subnet).
; ============================================================

\$ORIGIN 139.168.192.in-addr.arpa.
\$TTL 300

@   IN  SOA  ${THIS_HOSTNAME_LOWER}.jukebox.internal.  hostmaster.jukebox.internal. (
              ${SERIAL}  ; serial
              3600       ; refresh
              900        ; retry
              604800     ; expire
              300        ; minimum
            )

@   IN  NS   ${THIS_HOSTNAME_LOWER}.jukebox.internal.

; -- Ancillary / management hosts -----------------------------
8     IN PTR  ${THIS_HOSTNAME_LOWER}.jukebox.internal.     ; DNS/BIND9 server (this host)
10    IN  PTR  exadcscld001.jukebox.internal.               ; DC primary
11    IN  PTR  exadcscld002.jukebox.internal.               ; DC secondary
12    IN  PTR  exarudcld001.jukebox.internal.     ; Rudder Server
20    IN  PTR  exasvrcld002.jukebox.internal.     ; Windows Admin Centre
48    IN  PTR  exacldpbx001.jukebox.internal.     ; Central 3CX PBX
50    IN  PTR  exaprvcld001.jukebox.internal.     ; Provisioning / PXE
69    IN  PTR  exaanscld001.jukebox.internal.     ; Ansible management node

; -- Firewall WAN PTR records ----------------------------------
; 192.168.139.{octet}  ->  exafwl{site}001-wan.jukebox.internal.
; Sorted by octet ascending.
PROVREVHDR

for site in "${SORTED_SITES[@]}"; do
  octet="${SITE_OCTET[$site]}"
  wan_host="EXAFWL${site}001-wan.jukebox.internal."
  printf "%-5s IN  PTR  %-50s ; %s (%s)
"     "${octet}" "${wan_host}" "${site}" "${SITE_CITY[$site]}" >> "${PROV_REV_FILE}"
done

success "Provisioning reverse zone written."

# ---------------------------------------------------------------
# 9b. Generate per-site reverse zones: one db.192.168.X per site
#
# CLD is skipped -- its subnet (192.168.139.0/24) is handled by
# the dedicated provisioning zone above.
#
# Each /24 gets PTR records for the standard SUFFIX_MAP addresses:
#   .1 .2 .3 .4 .5 .6 .7 .10 .11 .48 .250 .251 .252 .253
#
# Zone names follow RFC 1035: X.168.192.in-addr.arpa
# Files: /etc/bind/db.192.168.X
# ---------------------------------------------------------------
info "Generating per-site reverse zone files..."

# Suffix → short hostname prefix + seq (mirrors SUFFIX_MAP above)
# Format: "suffix prefix seq"
declare -a REV_SUFFIX_MAP=(
  "1   exartr  1"
  "2   exarac  1"
  "3   exarac  2"
  "4   exarac  3"
  "5   exapve  1"
  "6   exapve  2"
  "7   exapve  3"
  "10  exadcs  1"
  "11  exadcs  2"
  "12  exarry  1"
  "48  exasbc  1"
  "250 exaswi  1"
  "251 exaswi  2"
  "252 exaswi  3"
  "253 exafwl  1"
)

rev_zone_count=0
for site in "${SORTED_SITES[@]}"; do
  # CLD's subnet is the provisioning network -- handled by 9a above
  [[ "${site}" == "CLD" ]] && continue

  octet="${SITE_OCTET[$site]}"
  city="${SITE_CITY[$site]}"
  rev_file="/etc/bind/db.192.168.${octet}"

  cat > "${rev_file}" <<REVHDR
; ============================================================
; /etc/bind/db.192.168.${octet}
; Example Music Limited -- reverse zone
;
; Zone:    ${octet}.168.192.in-addr.arpa
; Covers:  192.168.${octet}.0/24  (${site} -- ${city})
; Server:  ${THIS_HOSTNAME} (192.168.139.8)
; Generated by: bindme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
;
; PTR records cover the standard static SUFFIX_MAP addresses.
; DHCP pool .100-.199 PTR records are generated via \$GENERATE below.
; ============================================================

\$ORIGIN ${octet}.168.192.in-addr.arpa.
\$TTL 300

@   IN  SOA  ${THIS_HOSTNAME_LOWER}.jukebox.internal.  hostmaster.jukebox.internal. (
              ${SERIAL}  ; serial
              3600       ; refresh
              900        ; retry
              604800     ; expire
              300        ; minimum
            )

@   IN  NS   ${THIS_HOSTNAME_LOWER}.jukebox.internal.

; -- PTR records (192.168.${octet}.x) -------------------------
REVHDR

  for entry in "${REV_SUFFIX_MAP[@]}"; do
    read -r suffix prefix seq <<< "${entry}"
    hostname="${prefix}${site}$(printf '%03d' "${seq}").jukebox.internal."
    hostname="${hostname^^}"
    printf "%-5s IN  PTR  %s\n" "${suffix}" "${hostname}" >> "${rev_file}"
  done

  # DHCP pool $GENERATE: .100-.199 -> dhcp01.site.jukebox.internal. etc.
  # Mirrors the forward zone $GENERATE stanza.
  # Using echo rather than a heredoc so bash doesn't expand BIND's $ syntax.
  {
    echo ""
    echo "; -- DHCP pool PTR (\$GENERATE) ---------------------------------"
    echo "; .100 -> dhcp01.${site,,}.jukebox.internal."
    echo "; .199 -> dhcp100.${site,,}.jukebox.internal."
    echo "\$GENERATE 100-199 \$ IN PTR dhcp\${-99,2,d}.${site,,}.jukebox.internal."
  } >> "${rev_file}"

  rev_zone_count=$(( rev_zone_count + 1 ))
done

success "Per-site reverse zone files written: ${rev_zone_count} files."

# ---------------------------------------------------------------
# 10. Validate all zone files before restarting BIND
# ---------------------------------------------------------------
info "Validating named.conf..."
if ! named-checkconf /etc/bind/named.conf; then
  die "named.conf validation failed -- check output above."
fi
info "Validating forward zone..."
if ! named-checkzone jukebox.internal "${ZONE_FILE}"; then
  die "Forward zone validation failed -- check output above."
fi
info "Validating provisioning reverse zone (139)..."
if ! named-checkzone 139.168.192.in-addr.arpa "${PROV_REV_FILE}"; then
  die "Provisioning reverse zone validation failed -- check output above."
fi
info "Validating per-site reverse zones..."
rev_errors=0
for site in "${SORTED_SITES[@]}"; do
  [[ "${site}" == "CLD" ]] && continue
  octet="${SITE_OCTET[$site]}"
  rev_file="/etc/bind/db.192.168.${octet}"
  zone_name="${octet}.168.192.in-addr.arpa"
  if ! named-checkzone "${zone_name}" "${rev_file}" > /dev/null 2>&1; then
    warn "Reverse zone check FAILED: ${zone_name} (${rev_file})"
    named-checkzone "${zone_name}" "${rev_file}" || true
    rev_errors=$(( rev_errors + 1 ))
  fi
done
if [[ "${rev_errors}" -gt 0 ]]; then
  die "${rev_errors} reverse zone(s) failed validation -- check output above."
fi
success "All zone files validated OK."

# ---------------------------------------------------------------
# 11. Enable and start named
# ---------------------------------------------------------------
info "Enabling and starting named (BIND9)..."
systemctl enable named
systemctl restart named
sleep 2
if systemctl is-active --quiet named; then
  success "named is running."
else
  die "named failed to start.  Check: journalctl -u named -n 50"
fi

# ---------------------------------------------------------------
# 12. Quick self-test
# ---------------------------------------------------------------
info "Running self-test query: dig @127.0.0.1 ${THIS_HOSTNAME_LOWER}.jukebox.internal"
if dig @127.0.0.1 +short ${THIS_HOSTNAME_LOWER}.jukebox.internal | grep -q "192.168.139.8"; then
  success "DNS self-test passed."
else
  warn "Self-test query returned unexpected result -- check the zone file and named status."
fi

# ---------------------------------------------------------------
# 13. Zone regeneration helper script
#     /usr/local/sbin/regen-zone.sh  -- calls bindme.sh zone-only
#     Not a full re-run -- just regenerates the zone from sites.csv
#     and reloads.  For use after sites.csv changes.
# ---------------------------------------------------------------
info "Writing /usr/local/sbin/regen-zone.sh..."
cat > /usr/local/sbin/regen-zone.sh <<'REGEN'
#!/usr/bin/env bash
# ============================================================
# regen-zone.sh -- Example Music Limited
# Regenerate /etc/bind/db.jukebox.internal from sites.csv
# and reload the zone without a full bindme.sh re-run.
#
# Usage: sudo regen-zone.sh [/path/to/sites.csv]
# If no argument given, uses the same CSV search order as bindme.sh.
# ============================================================
set -euo pipefail
ZONE_FILE="/etc/bind/db.jukebox.internal"
SITES_CSV="${1:-}"

die()  { echo "[ERROR] $*" >&2; exit 1; }
info() { echo "[*] $*"; }

[[ $EUID -ne 0 ]] && die "Run as root."
[[ -f /usr/local/sbin/bindme.sh ]] || die "bindme.sh not found at /usr/local/sbin/bindme.sh -- cannot regenerate."

info "Backing up current zone to ${ZONE_FILE}.bak..."
cp "${ZONE_FILE}" "${ZONE_FILE}.bak"

info "Re-running bindme.sh zone generation step..."
# Source bindme.sh isn't practical -- re-run it with a zone-only flag.
# For now: named-checkzone before reload, fail loudly on error.
if [[ -n "${SITES_CSV}" ]]; then
  SITES_CSV="${SITES_CSV}" bash /usr/local/sbin/bindme.sh --zone-only
else
  bash /usr/local/sbin/bindme.sh --zone-only
fi

named-checkzone jukebox.internal "${ZONE_FILE}" || die "Zone check failed -- backup at ${ZONE_FILE}.bak"
rndc reload jukebox.internal && echo "[+] Zone reloaded." || die "rndc reload failed."
REGEN
chmod 0750 /usr/local/sbin/regen-zone.sh

# Copy bindme.sh itself to /usr/local/sbin for regen-zone.sh to reference
cp "${BASH_SOURCE[0]}" /usr/local/sbin/bindme.sh
chmod 0750 /usr/local/sbin/bindme.sh
success "Zone regen helper written."

# ---------------------------------------------------------------
# 14. Dynamic MOTD
# ---------------------------------------------------------------
info "Writing dynamic MOTD..."
mkdir -p /etc/update-motd.d
chmod 0755 /etc/update-motd.d

# Disable any existing MOTD scripts that produce noise
for f in /etc/update-motd.d/10-uname /etc/update-motd.d/50-motd-news; do
  [[ -f "$f" ]] && chmod -x "$f"
done

WH='\033[1;37m'; YL='\033[1;33m'; GR='\033[0;32m'; CY='\033[0;36m'; RS='\033[0m'

cat > /etc/update-motd.d/10-examplemusic <<'MOTD'
#!/usr/bin/env bash
WH='\033[1;37m'; YL='\033[1;33m'; GR='\033[0;32m'; CY='\033[0;36m'; RS='\033[0m'

HOSTNAME=$(hostname -s)
UPTIME=$(uptime -p 2>/dev/null || uptime)
LOAD=$(cat /proc/loadavg | awk '{print $1,$2,$3}')
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_USED=$(free -m  | awk '/^Mem:/{print $3}')
DISK=$(df -h / | awk 'NR==2{print $3" used of "$2" ("$5")"}')

DNS_IP=$(ip -4 addr show | awk '/inet /{print $2}' | grep '192\.168\.139\.' | cut -d/ -f1 | head -1)
ZONE_SERIAL=$(grep -oP '(?<=;\s)serial.*' /etc/bind/db.jukebox.internal 2>/dev/null | head -1 | awk '{print $1}') || true
NAMED_STATUS=$(systemctl is-active named 2>/dev/null || echo "unknown")
RECORD_COUNT=$(grep -c 'IN  A' /etc/bind/db.jukebox.internal 2>/dev/null || echo "?")

echo -e "
${WH}╔══════════════════════════════════════════════════════════════╗${RS}
${WH}║           EXAMPLE MUSIC LIMITED: $(printf '%-24s' "${HOSTNAME}")║${RS}
${WH}╚══════════════════════════════════════════════════════════════╝${RS}

  ${YL}Role     :${RS} DNS Server -- jukebox.internal
  ${YL}Zone     :${RS} jukebox.internal  (${RECORD_COUNT} A records, serial ${ZONE_SERIAL:-unknown})

  ${WH}── Network ──────────────────────────────────────────────────${RS}
    ${CY}DNS IP${RS}   : ${GR}${DNS_IP:-unknown}${RS}
    ${CY}BIND9${RS}    : ${GR}${NAMED_STATUS}${RS}

  ${WH}── System ───────────────────────────────────────────────────${RS}
    ${CY}Uptime${RS}   : ${GR}${UPTIME}${RS}
    ${CY}Load${RS}     : ${GR}${LOAD}${RS}
    ${CY}Memory${RS}   : ${GR}${MEM_USED}MB${RS} used of ${MEM_TOTAL}MB
    ${CY}Disk /  ${RS} : ${GR}${DISK}${RS}

  ${WH}── Management ───────────────────────────────────────────────${RS}
    ${CY}Aliases${RS}  : reloadbind  checkbind  editzone  bindstatus  bindlog
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

systemctl restart ssh
success "Dynamic MOTD configured."

# ---------------------------------------------------------------
# 15. Sentinel file
# ---------------------------------------------------------------
mkdir -p /etc/example-music
jq -n \
  --arg hostname       "$(hostname -s)" \
  --arg role           "dns" \
  --arg site           "CLD" \
  --arg city           "${SITE_CITY[CLD]:-Central}" \
  --arg country        "${SITE_COUNTRY[CLD]:-GB}" \
  --arg entity         "${SITE_ENTITY[CLD]:-Example Music}" \
  --arg bootstrapped_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg bootstrapped_by "bindme.sh" \
  --arg environment    "${ENV_LONG}" \
  --arg dns_ip         "${DNS_IP}" \
  --arg zone           "jukebox.internal" \
  --arg zone_serial    "${SERIAL}" \
  --arg interface      "${PROV_IFACE}" \
  --arg interface_mac  "${PROV_MAC}" \
  '{
    hostname:        $hostname,
    role:            $role,
    site:            $site,
    city:            $city,
    country:         $country,
    entity:          $entity,
    ansible_managed: false,
    bootstrapped_at: $bootstrapped_at,
    bootstrapped_by: $bootstrapped_by,
    environment:     $environment,
    dns_ip:          $dns_ip,
    zone:            $zone,
    zone_serial:     $zone_serial,
    interface:       $interface,
    interface_mac:   $interface_mac
  }' > /etc/example-music/nodeinfo.json
chmod 0444 /etc/example-music/nodeinfo.json
success "Node info written to /etc/example-music/nodeinfo.json"

# ---------------------------------------------------------------
# 16. Final banner
# ---------------------------------------------------------------
RECORD_COUNT=$(grep -c 'IN  A' "${ZONE_FILE}" || echo "?")
echo
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  SETUP COMPLETE -- ${THIS_HOSTNAME}${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "${CYAN}  Hostname      : $(hostname)${NC}"
echo -e "${CYAN}  DNS IP        : ${DNS_IP}/24  (${PROV_IFACE})${NC}"
echo -e "${CYAN}  Zone          : jukebox.internal${NC}"
echo -e "${CYAN}  A records     : ${RECORD_COUNT}${NC}"
echo -e "${CYAN}  Zone serial   : ${SERIAL}${NC}"
echo -e "${CYAN}  Forwarders    : 1.1.1.1, 9.9.9.9${NC}"
echo -e "${CYAN}  Reverse zones : 139.168.192.in-addr.arpa  (provisioning -- FWL WAN + ancillary)${NC}"
echo -e "${CYAN}                 + one X.168.192.in-addr.arpa per site (${non_cld_count} zones)${NC}"
echo
echo -e "${YELLOW}  Useful aliases and functions (bash + zsh):${NC}"
echo -e "${CYAN}    reloadbind                -- rndc reload jukebox.internal${NC}"
echo -e "${CYAN}    checkbind                 -- validate db.jukebox.internal (default)${NC}"
echo -e "${CYAN}    checkbind db.192.168.78   -- validate a specific zone file${NC}"
echo -e "${CYAN}    editzone                  -- vim + validate + reload (default zone)${NC}"
echo -e "${CYAN}    editzone db.192.168.139   -- edit a specific zone file (needs root)${NC}"
echo -e "${CYAN}    bindstatus                -- systemctl status named${NC}"
echo -e "${CYAN}    bindlog                   -- journalctl -u named -f${NC}"
echo
echo -e "${YELLOW}  Quick test:${NC}"
echo -e "${CYAN}    dig @${DNS_IP} ${THIS_HOSTNAME_LOWER}.jukebox.internal${NC}"
echo -e "${CYAN}    dig @${DNS_IP} EXAFWLGLA001.jukebox.internal${NC}"
echo -e "${CYAN}    dig @${DNS_IP} -x 192.168.139.8${NC}"
echo -e "${GREEN}============================================================${NC}"
echo

warn "A reboot is recommended to ensure NM profile and systemd .link take full effect."
echo
read -rp $'\e[1;33m[!]\e[0m Reboot now? [y/N] ' REBOOT_NOW
REBOOT_NOW="${REBOOT_NOW:-n}"
if [[ "${REBOOT_NOW,,}" == "y" ]]; then
  info "Rebooting in 5 seconds — press Ctrl-C to cancel..."
  sleep 5
  reboot
else
  warn "Remember to reboot before testing — NM static IP may not apply until then."
fi
