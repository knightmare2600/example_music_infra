#!/usr/bin/env bash
# ==============================================================================
# Example Music Limited — Ansible Node Bootstrap Script
# EXAANSCLD001 (or any site's ansible/management node)
#
# Mirrors the style of firewallme.sh:
#   - Interactive, idempotent, run as root
#   - Site-code-driven (subnet/inventory auto-derived)
#   - Self-bootstraps all dependencies
#   - Generates SSH keypair for ansible user
#   - Writes ansible.cfg, inventory, group_vars scaffolding
#   - Fixes known first-run issues (sudoers path, etc.)
#   - Onboards PVE nodes via pve_onboard.yml
#   - Tests connectivity with ansible ping
#   - Sentinel file + dynamic MOTD
#
# -------------------------------------------------------------------------------------------------
# Version history
# -------------------------------------------------------------------------------------------------
# v1.0.0  2025-??-??  Initial release
# v1.1.0  2025-??-??  Fix mkdir brace expansion fail inside double quotes; expand to explicit paths
#                     Fix apt hung on interactive prompts (libguestfs-tools kernel selection) or
#                     cause OOM by adding recommended pkgs; remove -qq add --force-confold/confdef,
#                     --no-install-recommends
#                     
# v1.2.0  2026-06-14  Fix: load_sites_csv() while-read loop dropped last CSV line when file had no
#                     trailing newline (read returns non-zero at EOF, loop exited before processing
#                     that iteration). VIE is the last line in sites.csv & has no trailing newline,
#                     so never loaded into  SITE_OCTET[]; "Unknown site code 'VIE'" at runtime. Fix
#                     with || [[ -n "$site" ]] on the while condition, warn() now writes to stderr
#                     (>&2) for consistency with firewallme.sh and to prevent future $() subshell
#                     captures picking up warning text as data.
# v1.4.0  2026-06-14  Fix authorized_keys missing \n between entries. If file had no trailing \n,
#                     appended keys ran together on one line breaking both. Use printf & checks for
#                     trailing newline before appending.
#                     Fix inventory self-entry hostname -I (old/prov IP) instead of canonical .10
#                     management IP from SITE_DC[$SITE_CODE] in the CSV.
#                     Fix ansible.cfg stdout_callback updated to ansible.builtin.default (correct
#                     for ansible-core 2.19+; bare 'yaml' is a result_format value, not a callback
#                     name). Added result_format = yaml explicitly. StrictHostKeyChecking changed
#                     from 'no' to 'accept-new' accepts new host keys on first connect but rejects
#                     changed keys, which 'no' does not. Fix sudoers drop-in now validated (visudo
#                     -cf) & permissions enforced on this host directly, not only copied to files/
#                     for playbook distribution.
# v1.11.0 2026-06-18  Section 1b added: static IP configuration transplanted
#                     from bindme.sh. Detects provisioning interface, checks
#                     target IP is free (ping + arping), pins interface name via
#                     systemd .link, strips ifupdown stanzas, fixes NM managed=
#                     false, removes stale profiles, writes ansible-static NM
#                     profile with autoconnect yes + priority 100. NM restart
#                     deferred (same SSH-safety fix as firewallme.sh). ip_in_use()
#                     helper added. arping and network-manager added to BOOTSTRAP_PKGS.
#                     Section 1c added: hostname prompt matching bindme.sh pattern.
#                     Detects EXA* convention hostname, normalises to uppercase,
#                     defaults to EXASVRCLD001 if convention not matched. Sets
#                     hostname via hostnamectl and adds /etc/hosts entry.
# v1.10.0 2026-06-17  Section 6 (SSH keypair) now offers a choice: generate a new keypair on host
#                     (unchanged default), or paste an existing PUBLIC key only. Private keys are
#                     never accepted via paste- pasting a private key into a terminal/script means
#                     it travelled through clipboard & shell history, which we will not do. Paste
#                     mode writes only ansible-id_rsa.pub & prints an orange-bordered warning box
#                     with the exact path the matching private key must be copied to (scp example
#                     included), plus chown/chmod instructions. A second reminder appears at the
#                     end of the run if the private key still isn't present, & section 8 (discovery
#                     scan) now warns up front that the SSH scan will fail every host until the key
#                     is placed. Fix missing space in the final banner pve_onboard.yml command.
# v1.9.0  2026-06-17  Fix "Host key verification failed" on first ansible run against IPs reused
#                     from a previous build (e.g. this very ansible node rebuilding at the same
#                     provisioning IP).
#                     accept-new correctly REJECTS changed host key as a MITM safeguard — but stale
#                     fingerprint from a node's prior incarnation triggered exactly that rejection
#                     on healthy hosts, with no clear cause in the error message. Section 7B clears
#                     known_hosts entries (both the ansible user's own & /etc/ssh/ssh_known_hosts)
#                     for every CSV-derived IP (.5/.6/.10/.253 per site) plus, this node's own prov
#                     IP BEFORE discovery scan runs, so scan isn't confused by stale fingerprints.
#                     Add section 10B: final catch-all pass over actual written inventory, covering
#                     custom subnets/manually added groups that a CSV-only sweep would not "see".
#                     Both passes use ssh-keygen -R (idempotent, silent if no entry exists) accept-
#                     new then trusts the current key on next connect with no security regression.
# v1.8.0  2026-06-16  ansible.cfg updated to match hand-crafted version: host_key_checking = True
#                     (was False — accept-new handles new hosts; True catches changed fingerprints
#                     correctly). Added forks = 50, timeout = 5, connect_timeout = 5. Added
#                     [persistent_connection] section (command_timeout=30, connect_retry_timeout=15).
#                     Full inline comment blocks & recommended playbook settings added to config.
# v1.7.0  2026-06-16  Section 7 rewritten: PVE nodes auto-populated from CSV at .5 (primary) and .6
#                     (secondary) for all sites. Operator only prompted for additional nodes not in
#                     CSV. CSV-only mode deduplicates entries by IP so BRD/BER (both 192.168.113.x)
#                     produce one merged comment not duplicates. All inventory IP entries padded to
#                     15 chars before # for consistent column alignment (max IPv4 is 15 chars).
#                     CSV-only success message now lists all groups built ansiblehosts, pvenodes,
#                     dcs, firewalls. [pvenodes] always written to inventory; entries pre-populated
#                     from CSV are always present.
# v1.6.0  2026-06-16  Fix ansible listed twice in BOOTSTRAP_PKGS, once via early command -v check &
#                     again in Debian version block. On fresh install apt downloads twice, causing
#                     OOM pressure. Removed early unconditional check; version block handles it.
#                     Fix apt install redirected to /dev/null so OOM kills were completely silent
#                     (just "Killed" with no context). Now logs to a mktemp file; on failure prints
#                     last 20 lines & preserves the log for inspection. Fix: memory check added
#                     before apt install; warns if less than 512MB available as ansible unpacked
#                     needs ~400MB and the OOM killer hits silently below that.
# v1.5.0  2026-06-15  Section 8 rewritten as infrastructure discovery. Choose: A) SSH subnet scan,
#                     B) CSV-only fill, or C) skip. Scan mode prompts for which subnets to cover:
#                     PROV (139), all site LANs via CSV, WireGuard tunnels (10.0.x.0/24), or custom.
#                     Each reachable host is classified by last octet (10/11 DCs, 253 FWLs, 48 PBX)
#                     & provisioning-net position (139.10 ANS). DNS PTR lookup labels each entry.
#                     Unknowns appear as a commented-out [unknowns] stanza in the inventory for
#                     operator review.  CSV-only mode pre-fills [dcs] & [firewalls] from SITE_DC[]/
#                     SITE_FW[] without scanning. Additional groups can be added manually after
#                     either mode. Inventory write updated to consume DISC_HOSTS_BY_GROUP.
# v1.13.0 2026-06-26  Section 5b added: data file bootstrap. devices.csv and sites.csv are
#                     canonical at /etc/example-music/ (placed by preseed late_command).
#                     Script now checks for both and downloads from the provisioning server
#                     (192.168.PROV.50/proxmox/) if either is missing. devices.csv is also
#                     copied to ansible/files/ for the bind9-dns.yml playbook. bind9-dns.yml
#                     devices_csv_path default updated to /etc/example-music/devices.csv.
#
# v1.12.0 2026-06-25  configs/inventory is now a directory, not a flat file. Ansible merges all
#                     .ini files in the directory automatically, so per-site and per-service
#                     inventory files (cld.ini, kge.ini, fal.ini, rudder.ini, etc.) can live
#                     alongside the generated main.ini without polluting it. INVENTORY_FILE now
#                     points to configs/inventory/main.ini (the generated file); ansible.cfg and
#                     all ansible commands reference configs/inventory (the directory). Section 10b
#                     now greps all *.ini files in the directory instead of just main.ini.
#                     group_vars/firewalls/main.yml added for WireGuard hub reference data.
#
# v1.3.0  2026-06-14  Quieten apt output: -qq + stdout to /dev/null on install line; errors still
#                     surface on stderr. Section 8 (additional managed hosts): smart CSV-fill mode.
#                     Recognises group names dc/dcs & firewalls/fw & offers to auto-build IPs from
#                     SITE_DC[]/SITE_FW[] loaded from sites.csv. Operator can select all sites or a
#                     subset by code. Falls back to manual for unrecognised group names or when CSV
#                     offer declined. PVE nodes explicitly excluded from smart-fill (kept as-is).
#                     SITE_DC and SITE_FW arrays added to load_sites_csv().
#
# =================================================================================================

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

# ------------------------------------------------------------------------------
# Colour helpers  (identical to firewallme.sh)
# ------------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'
info()    { echo -e "${CYAN}[*]${NC} $*"; }
success() { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*" >&2; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
section() { echo; echo -e "${WHITE}── $* ──${NC}"; echo; }

# Checks whether an IP is already live on the network (ping + arping fallback)
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

# ------------------------------------------------------------------------------
# Must run as root
# ------------------------------------------------------------------------------
[[ $EUID -ne 0 ]] && die "Run this script with sudo or as root."

# ------------------------------------------------------------------------------
# Site data -- loaded from sites.csv (single source of truth)
# To add or change a site, edit sites.csv -- no code changes needed.
#
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
  # BUG FIX: `while read` silently drops the last line of a file with no trailing
  # newline — read returns non-zero at EOF so the loop exits without processing
  # that final iteration.  sites.csv has no trailing newline; VIE is the last
  # entry and was therefore never loaded.  The || [[ -n "$site" ]] guard catches
  # the partial read and processes it normally.
  while IFS=',' read -r site city country cc subnet gateway dc fw landline mobile tz ansible_region entity _rest \
      || [[ -n "$site" ]]; do
    [[ "${first}" -eq 1 ]] && { first=0; continue; }   # skip header row
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
ANSIBLE_USER="ansible"
ANSIBLE_HOME="/home/ansible"
ANSIBLE_DIR="${ANSIBLE_HOME}/ansible"
CONFIGS_DIR="${ANSIBLE_DIR}/configs"
PLAYBOOKS_DIR="${ANSIBLE_DIR}/playbooks"
FILES_DIR="${ANSIBLE_DIR}/files"
KEY_FILE="${CONFIGS_DIR}/ansible-id_rsa"
KEY_PUB="${CONFIGS_DIR}/ansible-id_rsa.pub"
INVENTORY_FILE="${CONFIGS_DIR}/inventory/main.ini"
ANSIBLE_CFG="${ANSIBLE_DIR}/ansible.cfg"
SENTINEL="/etc/.i_am_an_ansible_node"

# ------------------------------------------------------------------------------
# Banner
# ------------------------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            Example Music:- Ansible Node Bootstrap            ║${NC}"
echo -e "${CYAN}║                         ansibleme.sh                         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}  Running on hostname: ${GREEN}$(hostname)${NC}"
echo

# ------------------------------------------------------------------------------
# 1. Bootstrap packages
# ------------------------------------------------------------------------------
section "1. Installing dependencies"
info "Updating package lists..."
apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true

BOOTSTRAP_PKGS=()
# ansible is handled separately below (version strategy varies by Debian release)
command -v git          &>/dev/null || BOOTSTRAP_PKGS+=(git)
command -v ssh          &>/dev/null || BOOTSTRAP_PKGS+=(openssh-client)
command -v sshpass      &>/dev/null || BOOTSTRAP_PKGS+=(sshpass)
command -v python3      &>/dev/null || BOOTSTRAP_PKGS+=(python3)
command -v pip3         &>/dev/null || BOOTSTRAP_PKGS+=(python3-pip)
command -v curl         &>/dev/null || BOOTSTRAP_PKGS+=(curl)
command -v wget         &>/dev/null || BOOTSTRAP_PKGS+=(wget)
command -v vim          &>/dev/null || BOOTSTRAP_PKGS+=(vim)
command -v tmux         &>/dev/null || BOOTSTRAP_PKGS+=(tmux)
command -v tree         &>/dev/null || BOOTSTRAP_PKGS+=(tree)
command -v grc          &>/dev/null || BOOTSTRAP_PKGS+=(grc)
command -v zsh          &>/dev/null || BOOTSTRAP_PKGS+=(zsh)
command -v yamllint     &>/dev/null || BOOTSTRAP_PKGS+=(yamllint)
command -v gpg          &>/dev/null || BOOTSTRAP_PKGS+=(gpg)
command -v arping       &>/dev/null || BOOTSTRAP_PKGS+=(arping)
command -v nmcli        &>/dev/null || BOOTSTRAP_PKGS+=(network-manager)
# Python libs for Proxmox API and virt tools
dpkg -s python3-proxmoxer  &>/dev/null || BOOTSTRAP_PKGS+=(python3-proxmoxer)
dpkg -s python3-requests    &>/dev/null || BOOTSTRAP_PKGS+=(python3-requests)
dpkg -s python3-virtualenv  &>/dev/null || BOOTSTRAP_PKGS+=(python3-virtualenv)

# NB: libguestfs-tools is intentionally NOT installed on the ansible node. It is
# only needed on PVE nodes, and is deployed there via the pve_onboard.yml and
# cloud_templates.yml playbooks. Installing here pulls in the full qemu/kvm pkgs
# (100s of MB, kernel images) which can cause OOM on small nodes.

# Ansible package strategy:
#   Debian 13 (trixie) — ships ansible 12.0.0 / ansible-core 2.19 in main repo. No PPA needed.
#   Debian 12 (bookworm) — ships ansible-core 2.14 which is too old; add Ubuntu jammy PPA.
#   Anything else — attempt main repo; warn if version is old.
DEBIAN_VERSION=$(. /etc/os-release && echo "${VERSION_ID:-0}")

if [[ "$DEBIAN_VERSION" -ge 13 ]] 2>/dev/null; then
  info "Debian ${DEBIAN_VERSION} (trixie+): ansible available in main repo — no PPA needed."
  BOOTSTRAP_PKGS+=(ansible)
elif [[ "$DEBIAN_VERSION" == "12" ]]; then
  info "Debian 12 (bookworm): adding Ubuntu jammy PPA for a current ansible version..."
  if [[ ! -f /usr/share/keyrings/ansible-archive-keyring.gpg ]]; then
    wget -q -O /tmp/ansible.gpg "https://keyserver.ubuntu.com/pks/lookup?fingerprint=on&op=get&search=0x6125E2A8C77F2818FB7BD15B93C4A3FD7BB9C367"
    gpg --dearmour -o /usr/share/keyrings/ansible-archive-keyring.gpg /tmp/ansible.gpg
    rm -f /tmp/ansible.gpg
  fi
  if [[ ! -f /etc/apt/sources.list.d/ansible.list ]]; then
    echo "deb [signed-by=/usr/share/keyrings/ansible-archive-keyring.gpg] http://ppa.launchpad.net/ansible/ansible/ubuntu jammy main" > /etc/apt/sources.list.d/ansible.list
    apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true
  fi
  BOOTSTRAP_PKGS+=(ansible)
else
  warn "Unknown Debian version '${DEBIAN_VERSION}'. Will attempt to install ansible from main repo."
  BOOTSTRAP_PKGS+=(ansible)
fi

if [[ ${#BOOTSTRAP_PKGS[@]} -gt 0 ]]; then
  info "Installing: ${BOOTSTRAP_PKGS[*]}"

  # Memory check — apt+ansible unpacked needs ~400MB.  Warn if available RAM
  # is below 512MB; the OOM killer will silently kill apt otherwise.
  MEM_AVAIL_KB=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [[ -n "$MEM_AVAIL_KB" && "$MEM_AVAIL_KB" -lt 524288 ]]; then
    warn "Only $(( MEM_AVAIL_KB / 1024 ))MB RAM available — ansible install needs ~400MB."
    warn "If apt gets killed (OOM), free memory and re-run the script."
  fi

  APT_LOG=$(mktemp /tmp/ansibleme-apt-XXXXXX.log)
  # -qq suppresses progress/info lines; log to file not /dev/null so OOM kills
  # are diagnosable.  Errors still surface on stderr.
  if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      -o Dpkg::Options::="--force-confold" \
      -o Dpkg::Options::="--force-confdef" \
      -o Dpkg::Use-Pty=0 \
      --no-install-recommends \
      "${BOOTSTRAP_PKGS[@]}" > "$APT_LOG" 2>&1; then
    success "Packages installed."
    rm -f "$APT_LOG"
  else
    APT_RC=$?
    warn "apt-get install failed (exit ${APT_RC}) -- last 20 lines of log:"
    tail -20 "$APT_LOG" >&2
    warn "Full log: ${APT_LOG}"
    die "Package installation failed. Fix the above and re-run."
  fi
else
  success "All required packages already present."
fi


# ------------------------------------------------------------------------------
# 1b. Static IP and network configuration
# ------------------------------------------------------------------------------
# Mirrors the network section from bindme.sh — detect provisioning interface,
# check the target IP is free, pin the interface name via systemd .link, and
# configure a static NM profile. The profile applies on reboot; the current
# session can keep whatever DHCP address it has.
# ------------------------------------------------------------------------------
section "1b. Network configuration"

PROV_NET_DEFAULT="192.168.139"

read -rp "  Provisioning subnet [${PROV_NET_DEFAULT}]: " PROV_NET_INPUT
PROV_NET="${PROV_NET_INPUT:-${PROV_NET_DEFAULT}}"

read -rp "  Gateway last octet [1]: " GW_OCTET_INPUT
GW_OCTET="${GW_OCTET_INPUT:-1}"
PROV_GW="${PROV_NET}.${GW_OCTET}"

# Ansible/management node uses .10 as its canonical DC address from the CSV.
# We derive this from the site code entered in section 3 — but section 3 runs
# after this. So we prompt here with a sensible default; section 3 will confirm.
read -rp "  Static IP for this node [${PROV_NET}.10]: " NODE_IP_INPUT
NODE_STATIC_IP="${NODE_IP_INPUT:-${PROV_NET}.10}"

# Detect which interface is on the provisioning subnet
info "Detecting interface on provisioning network (${PROV_NET}.x)..."
PROV_IFACE=""
for iface in $(ls /sys/class/net/); do
  [[ "$iface" == "lo" ]] && continue
  ip_addr=$(ip -4 addr show "$iface" 2>/dev/null \
    | grep -oP "(?<=inet\s)${PROV_NET//./\\.}\.\d+" | head -1)
  if [[ -n "$ip_addr" ]]; then
    PROV_IFACE="$iface"
    success "Detected provisioning interface: ${PROV_IFACE} (currently ${ip_addr})"
    break
  fi
done

if [[ -z "$PROV_IFACE" ]]; then
  warn "Could not auto-detect provisioning interface."
  AVAILABLE_IFACES=($(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | grep -v '@'))
  read -rp "  Enter interface name (available: ${AVAILABLE_IFACES[*]}): " PROV_IFACE
  PROV_IFACE="${PROV_IFACE:-${AVAILABLE_IFACES[0]:-ens33}}"
fi

# IP collision check — don't stomp on something already live
info "Checking whether ${NODE_STATIC_IP} is already in use..."
if ip_in_use "${NODE_STATIC_IP}"; then
  # Could be ourselves (we might already have this IP via DHCP or prior config)
  CURRENT_IPS=$(hostname -I)
  if echo "$CURRENT_IPS" | grep -qw "${NODE_STATIC_IP}"; then
    info "${NODE_STATIC_IP} is already assigned to this host — continuing."
  else
    die "${NODE_STATIC_IP} is already in use by another host. Resolve the conflict first."
  fi
else
  success "${NODE_STATIC_IP} is free — proceeding."
fi

# Pin interface name via systemd .link so renames survive reboots
PROV_MAC=$(cat "/sys/class/net/${PROV_IFACE}/address" 2>/dev/null)
info "Pinning ${PROV_IFACE} (MAC ${PROV_MAC}) via systemd .link..."
mkdir -p /etc/systemd/network
cat > /etc/systemd/network/10-ansible-prov.link <<EOF
# Example Music -- provisioning interface pin
# Written by ansibleme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# MAC: ${PROV_MAC}  interface: ${PROV_IFACE}
[Match]
MACAddress=${PROV_MAC}
[Link]
Name=${PROV_IFACE}
EOF
success "Interface pin written."

# Configure static IP via NetworkManager
info "Configuring static IP via NetworkManager..."

# Mask ifupdown so it doesn't fight NM
systemctl disable networking.service 2>/dev/null || true
systemctl mask    networking.service 2>/dev/null || true
systemctl mask    "ifup@${PROV_IFACE}.service" 2>/dev/null || true

# Remove interface from /etc/network/interfaces if present
if [[ -f /etc/network/interfaces ]]; then
  if grep -qE "^(auto|allow-|iface)\s+${PROV_IFACE}" /etc/network/interfaces 2>/dev/null; then
    warn "Removing ifupdown stanza for ${PROV_IFACE} from /etc/network/interfaces..."
    cp -n /etc/network/interfaces /etc/network/interfaces.bak
    sed -i "/^auto\s\+${PROV_IFACE}\b/d"    /etc/network/interfaces
    sed -i "/^allow-.*\s${PROV_IFACE}\b/d"  /etc/network/interfaces
    sed -i "/^iface\s\+${PROV_IFACE}\b/,/^[^[:space:]]/{ /^iface\s\+${PROV_IFACE}\b/d; /^[^[:space:]]/!d; }" \
      /etc/network/interfaces
    success "Cleaned /etc/network/interfaces"
  fi
fi

# Ensure NM is actually managing interfaces (Debian ships managed=false)
NM_CONF="/etc/NetworkManager/NetworkManager.conf"
if grep -q "managed=false" "${NM_CONF}" 2>/dev/null; then
  warn "NetworkManager.conf has managed=false -- fixing..."
  sed -i "s/managed=false/managed=true/" "${NM_CONF}"
fi

systemctl restart NetworkManager
sleep 3

# Remove stale NM profiles before creating the new one
nmcli con delete "ansible-static" 2>/dev/null || true
while IFS=: read -r profile device rest; do
  [[ -z "${profile}" ]] && continue
  if [[ "${device}" == "--" || "${profile}" == *"Wired connection"* || "${profile}" == *"Ifupdown"* ]]; then
    warn "Deleting stale NM profile: ${profile}"
    nmcli con delete "${profile}" 2>/dev/null || true
  fi
done < <(nmcli -t -f NAME,DEVICE con show)

# Create the static profile (ansible node uses its own .10 IP, not a DNS server IP)
nmcli con add type ethernet ifname "${PROV_IFACE}" con-name "ansible-static" \
  ipv4.method manual \
  ipv4.addresses "${NODE_STATIC_IP}/24" \
  ipv4.gateway "${PROV_GW}" \
  ipv4.dns "192.168.139.10" \
  ipv4.dns-search "jukebox.internal" \
  ipv6.method ignore \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  && success "NM profile ansible-static written — will apply on reboot." \
  || warn "nmcli con add returned non-zero — check: nmcli connection show ansible-static"

# BUG FIX (from firewallme.sh): NM_RESTART is deliberately deferred — restarting
# NM during an active SSH session drops the connection instantly. The static IP
# takes effect cleanly on next reboot. If at console, run:
#   nmcli con up ansible-static
warn "Static IP will take full effect on reboot."
warn "If at local console (not SSH): nmcli con up ansible-static"

# ------------------------------------------------------------------------------
# 1c. Hostname
# ------------------------------------------------------------------------------
section "1c. Hostname"

# Same pattern as bindme.sh: detect current hostname, normalise to uppercase if
# it already matches EXA* convention, otherwise suggest the ansible node default.
# Site code is not known yet (section 3) so we use a generic default; the
# operator can override to match their exact hostname convention.
info "Detecting hostname for this ansible node..."
CURRENT_HOSTNAME=$(hostname -s)
SUGGESTED_HOSTNAME=""

if [[ "${CURRENT_HOSTNAME}" =~ ^[Ee][Xx][Aa] ]]; then
  SUGGESTED_HOSTNAME="${CURRENT_HOSTNAME^^}"
  info "Detected EXA-convention hostname: ${SUGGESTED_HOSTNAME}"
else
  SUGGESTED_HOSTNAME="EXASVRCLD001"
  warn "Current hostname '${CURRENT_HOSTNAME}' does not match EXA* convention."
fi

read -rp "  Hostname for this ansible node [${SUGGESTED_HOSTNAME}]: " HOSTNAME_INPUT
THIS_HOSTNAME="${HOSTNAME_INPUT:-${SUGGESTED_HOSTNAME}}"
THIS_HOSTNAME="${THIS_HOSTNAME^^}"   # enforce uppercase per site convention

info "Setting hostname to ${THIS_HOSTNAME}..."
hostnamectl set-hostname "${THIS_HOSTNAME}"
grep -q "${THIS_HOSTNAME,,}" /etc/hosts 2>/dev/null || \
  echo "127.0.1.1  ${THIS_HOSTNAME,,}.jukebox.internal  ${THIS_HOSTNAME,,}" >> /etc/hosts
success "Hostname set to ${THIS_HOSTNAME}."


section "2. Shell environment"

if id "$ANSIBLE_USER" &>/dev/null && [[ ! -f "${ANSIBLE_HOME}/.zshrc" ]]; then
  info "Setting up zsh for ${ANSIBLE_USER} user..."
  cat > "${ANSIBLE_HOME}/.zshrc" <<'ZSHRC'
export TERM=xterm-256color
export EDITOR=vim
export VISUAL=vim
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt appendhistory autocd extendedglob notify interactivecomments
setopt AUTO_CONTINUE LONG_LIST_JOBS
bindkey -e
autoload -Uz compinit && compinit
autoload -Uz colors && colors
bindkey "\e[1~" beginning-of-line;  bindkey "\e[4~" end-of-line
bindkey "\e[H"  beginning-of-line;  bindkey "\e[F"  end-of-line
bindkey "\eOH"  beginning-of-line;  bindkey "\eOF"  end-of-line
bindkey "\e[1;5C" forward-word;     bindkey "\e[1;5D" backward-word
bindkey "\e[5C"   forward-word;     bindkey "\e[5D"   backward-word
bindkey "\e\e[C"  forward-word;     bindkey "\e\e[D"  backward-word
bindkey "\e[3~" delete-char
PROMPT='
%F{green}%m%f:%F{cyan}%~%f> '
alias ls='ls --color=auto'
alias ll='ls -lah'
alias grep='grep --color=auto'
alias ap='ansible-playbook'
alias ai='ansible-inventory'
alias ag='ansible-galaxy'
if (( $+commands[grc] )); then
  GRC_ALIASES=true
  [[ -f /etc/profile.d/grc.sh ]] && source /etc/profile.d/grc.sh
fi
ZSHRC
  chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "${ANSIBLE_HOME}/.zshrc"
  chsh -s "$(command -v zsh)" "$ANSIBLE_USER"
  success "zsh configured for ${ANSIBLE_USER}."
fi

if [[ ! -f /root/.zshrc ]]; then
  info "Setting up zsh for root..."
  cat > /root/.zshrc <<'ZSHRC'
export TERM=xterm-256color
export EDITOR=vim
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt appendhistory autocd extendedglob notify interactivecomments
setopt AUTO_CONTINUE LONG_LIST_JOBS
bindkey -e
autoload -Uz compinit && compinit
autoload -Uz colors && colors
bindkey "\e[1~" beginning-of-line;  bindkey "\e[4~" end-of-line
bindkey "\e[H"  beginning-of-line;  bindkey "\e[F"  end-of-line
bindkey "\eOH"  beginning-of-line;  bindkey "\eOF"  end-of-line
bindkey "\e[3~" delete-char
PROMPT='
%F{red}%m%f:%F{cyan}%~%f# '
alias ls='ls --color=auto'
alias ll='ls -lah'
alias grep='grep --color=auto'
alias ap='ansible-playbook'
if (( $+commands[grc] )); then
  GRC_ALIASES=true
  [[ -f /etc/profile.d/grc.sh ]] && source /etc/profile.d/grc.sh
fi
ZSHRC
  chsh -s "$(command -v zsh)" root
  success "zsh configured for root."
fi

# ------------------------------------------------------------------------------
# 3. Site / node identity
# ------------------------------------------------------------------------------
section "3. Node identity"

# Try to auto-detect site from hostname (EXAANSCLD001 → CLD)
DETECTED_SITE=""
HOSTNAME_NOW=$(hostname)
if [[ "$HOSTNAME_NOW" =~ ^EXA[A-Z]{3}([A-Z]{3})[0-9]{3}$ ]]; then
  DETECTED_SITE="${BASH_REMATCH[1]}"
fi

echo -e "${CYAN}Known site codes:${NC}"
echo -e "${CYAN}  $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort | tr '\n' ' ')${NC}"
echo

SITE_CODE=""
SUBNET=""
while true; do
  if [[ -n "$DETECTED_SITE" && -v SITE_OCTET[$DETECTED_SITE] ]]; then
    read -rp "Site code (detected from hostname: ${DETECTED_SITE}, press Enter to accept): " SITE_INPUT
    SITE_INPUT="${SITE_INPUT:-${DETECTED_SITE}}"
  else
    read -rp "Enter site code for this node (e.g. CLD, FAL): " SITE_INPUT
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
# 4. ansible user
# ------------------------------------------------------------------------------
section "4. Ansible user"

if ! id "$ANSIBLE_USER" &>/dev/null; then
  info "Creating ${ANSIBLE_USER} user..."
  useradd --create-home --shell "$(command -v zsh)" "$ANSIBLE_USER"
  success "User ${ANSIBLE_USER} created."
else
  success "User ${ANSIBLE_USER} already exists."
fi

# Ensure kvm group membership (needed for virt-customize)
if getent group kvm &>/dev/null; then
  if ! id -nG "$ANSIBLE_USER" | grep -qw kvm; then
    usermod -a -G kvm "$ANSIBLE_USER"
    info "Added ${ANSIBLE_USER} to kvm group."
  fi
fi

# sudoers drop-in
SUDOERS_FILE="/etc/sudoers.d/ansible"
if [[ ! -f "$SUDOERS_FILE" ]]; then
  echo "ansible ALL=(ALL) NOPASSWD: ALL" > "$SUDOERS_FILE"
  chmod 0440 "$SUDOERS_FILE"
  success "sudoers drop-in written."
else
  success "sudoers drop-in already present."
fi

# ------------------------------------------------------------------------------
# 5. Directory scaffold
# ------------------------------------------------------------------------------
section "5. Directory scaffold"

info "Creating ansible directory tree under ${ANSIBLE_DIR}..."
# FIX v1.1.0: brace expansion (e.g. {linux,windows}) does NOT work inside double
# quotes — bash treats the braces as literals. Each path is now explicit.
mkdir -p "${CONFIGS_DIR}/inventory" "${PLAYBOOKS_DIR}/proxmox" "${PLAYBOOKS_DIR}/linux" "${PLAYBOOKS_DIR}/windows" "${FILES_DIR}" "${ANSIBLE_DIR}/group_vars/all" "${ANSIBLE_DIR}/group_vars/pvenodes" "${ANSIBLE_DIR}/host_vars"
chown -R "${ANSIBLE_USER}:${ANSIBLE_USER}" "${ANSIBLE_DIR}"
success "Directory tree created."

# ------------------------------------------------------------------------------
# 5b. Data files — sites.csv and devices.csv
# ------------------------------------------------------------------------------
# Canonical location for both files is /etc/example-music/ — placed there by
# the Debian preseed late_command. This section ensures they are present,
# downloading from the provisioning server (192.168.PROV.50) if missing.
# The ansible/files/ copy of devices.csv (used by bind9-dns.yml) is populated
# here; sites.csv was already loaded above from its canonical path.
# ------------------------------------------------------------------------------
section "5b. Data files"

PROV_SERVER="${PROV_NET}.50"
CANONICAL_DIR="/etc/example-music"
mkdir -p "${CANONICAL_DIR}"

# ── devices.csv ──────────────────────────────────────────────────────────────
DEVICES_CANONICAL="${CANONICAL_DIR}/devices.csv"
DEVICES_LOCAL="${FILES_DIR}/devices.csv"
DEVICES_URL="http://${PROV_SERVER}/proxmox/devices.csv"

if [[ -f "${DEVICES_CANONICAL}" ]]; then
  success "devices.csv found at ${DEVICES_CANONICAL}"
  cp "${DEVICES_CANONICAL}" "${DEVICES_LOCAL}"
  chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "${DEVICES_LOCAL}"
  success "Copied to ${DEVICES_LOCAL} for Ansible playbooks."
else
  info "devices.csv not found at ${DEVICES_CANONICAL} — fetching from ${DEVICES_URL}..."
  if wget -q --timeout=15 -O "${DEVICES_LOCAL}" "${DEVICES_URL}" 2>/dev/null; then
    cp "${DEVICES_LOCAL}" "${DEVICES_CANONICAL}"
    chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "${DEVICES_LOCAL}"
    success "Downloaded and installed to ${DEVICES_CANONICAL} and ${DEVICES_LOCAL}."
  else
    warn "Could not download devices.csv from ${DEVICES_URL}."
    warn "Place devices.csv at ${DEVICES_CANONICAL} before running bind9-dns.yml."
    warn "Source: bootstrap/web/proxmox/devices.csv in the infrastructure repo."
  fi
fi

# ── sites.csv local copy ──────────────────────────────────────────────────────
# sites.csv was already loaded from its canonical path at script start.
# Ensure the canonical file is present for other tools (bind9, firewallme, etc.)
# that expect it there. If it came from $SITES_CSV override, install it now.
SITES_CANONICAL="${CANONICAL_DIR}/sites.csv"
if [[ ! -f "${SITES_CANONICAL}" ]]; then
  if [[ -n "${SITES_CSV:-}" && -f "${SITES_CSV}" ]]; then
    cp "${SITES_CSV}" "${SITES_CANONICAL}"
    success "Installed sites.csv to ${SITES_CANONICAL} from ${SITES_CSV}."
  else
    info "Fetching sites.csv from provisioning server..."
    SITES_URL="http://${PROV_SERVER}/proxmox/sites.csv"
    if wget -q --timeout=15 -O "${SITES_CANONICAL}" "${SITES_URL}" 2>/dev/null; then
      success "Downloaded sites.csv to ${SITES_CANONICAL}."
    else
      warn "Could not download sites.csv from ${SITES_URL} — already loaded from ${SITES_CSV:-/etc/example-music/sites.csv}."
    fi
  fi
fi

# ------------------------------------------------------------------------------
# 6. SSH keypair
# ------------------------------------------------------------------------------
section "6. SSH keypair"

if [[ -f "$KEY_FILE" ]]; then
  EXISTING_PUB=$(cat "$KEY_PUB" 2>/dev/null || true)
  success "SSH key already exists at ${KEY_FILE}"
  echo -e "  ${CYAN}Public key: ${NC}${EXISTING_PUB}"
  read -rp "Replace the existing keypair? [y/N] " REGEN_KEY
  if [[ "${REGEN_KEY,,}" != "y" ]]; then
    info "Keeping existing key."
    ANSIBLE_PUBKEY="$EXISTING_PUB"
  else
    rm -f "$KEY_FILE" "$KEY_PUB"
    ANSIBLE_PUBKEY=""
  fi
else
  ANSIBLE_PUBKEY=""
fi

if [[ -z "$ANSIBLE_PUBKEY" ]]; then
  echo
  echo -e "${CYAN}  How should the ansible SSH key be set up?${NC}"
  echo -e "  ${WHITE}1)${NC} Generate a new keypair on this host (default)"
  echo -e "  ${WHITE}2)${NC} Use an existing key — paste in the public key only"
  echo
  read -rp "  Choice [1/2, default: 1]: " KEY_CHOICE
  KEY_CHOICE="${KEY_CHOICE:-1}"

  if [[ "$KEY_CHOICE" == "2" ]]; then
    # --------------------------------------------------------------------
    # Paste-in mode: only the PUBLIC key is ever entered here. The private
    # key half must be placed on this host manually by the operator — we
    # never accept a pasted private key, since that would mean it travelled
    # through a terminal/clipboard/history rather than being generated or
    # transferred securely.
    # --------------------------------------------------------------------
    echo
    echo -e "${YELLOW}  Paste the PUBLIC key only (single line, e.g. ssh-rsa AAAA... or ssh-ed25519 AAAA...):${NC}"
    read -rp "  Public key: " PASTED_PUBKEY

    if [[ ! "$PASTED_PUBKEY" =~ ^(ssh-rsa|ssh-ed25519|ecdsa-sha2-|sk-ssh-) ]]; then
      die "That doesn't look like a valid SSH public key (expected ssh-rsa / ssh-ed25519 / ecdsa-sha2-* / sk-ssh-*). Aborting."
    fi

    echo "$PASTED_PUBKEY" > "$KEY_PUB"
    chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "$KEY_PUB"
    chmod 644 "$KEY_PUB"
    ANSIBLE_PUBKEY="$PASTED_PUBKEY"

    # No private key file exists yet — KEY_FILE stays referenced by
    # ansible.cfg's private_key_file, but the operator must place it there.
    rm -f "$KEY_FILE"

    echo
    echo -e "${YELLOW}  +==========================================================================================================+${NC}"
    echo -e "${YELLOW}  |  ACTION REQUIRED — PRIVATE KEY MUST BE COPIED TO THIS HOST                                               |${NC}"
    echo -e "${YELLOW}  +==========================================================================================================+${NC}"
    echo -e "${YELLOW}  |                                                                                                          |${NC}"
    echo -e "${YELLOW}  |${NC}  Only the public key was entered. ansible.cfg expects the matching PRIVATE key at:                       ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |                                                                                                          ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |${NC}    ${WHITE}${KEY_FILE}${NC}                                                          ${YELLOW}| ${NC}"
    echo -e "${YELLOW}  |                                                                                                          ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |${NC}  You must copy it there yourself, e.g. from your workstation:                                            ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |                                                                                                          ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |${NC}    ${WHITE}scp ~/.ssh/id_rsa ${ANSIBLE_USER}@$(hostname -I | awk '{print $1}'):${KEY_FILE}                 ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |                                                                                                          ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |${NC}  Then set the correct ownership and permissions:                                                         |${NC}"
    echo -e "${YELLOW}  |                                                                                                          ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |${NC}    ${WHITE}chown ${ANSIBLE_USER}:${ANSIBLE_USER} ${KEY_FILE}                                    ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |${NC}    ${WHITE}chmod 600 ${KEY_FILE}                                                ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |                                                                                                          |${NC}"
    echo -e "${YELLOW}  |${NC}  ${RED}Never paste a private key into this script or any terminal prompt. Transfer it via scp/sftp over SSH    ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |${NC}  ${RED}instead.                                                                                                ${YELLOW}|${NC}"
    echo -e "${YELLOW}  |                                                                                                          |${NC}"
    echo -e "${YELLOW}  +==========================================================================================================+${NC}"
    echo

    read -rp "  Press Enter once you understand and will complete this step manually... " _ACK
    warn "Continuing setup. ansible-playbook and ansible ad-hoc runs will NOT work"
    warn "until ${KEY_FILE} is in place with the correct permissions."
  else
    info "Generating SSH keypair for ansible user..."
    sudo -u "$ANSIBLE_USER" ssh-keygen -t rsa -b 4096 -C "${ANSIBLE_USER}@$(hostname)" -f "$KEY_FILE" -N ""
    chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "$KEY_FILE" "$KEY_PUB"
    chmod 600 "$KEY_FILE"
    chmod 644 "$KEY_PUB"
    ANSIBLE_PUBKEY=$(cat "$KEY_PUB")
    success "Keypair generated."
  fi
fi

echo
echo -e "${YELLOW}  ╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}  ║    ANSIBLE PUBLIC KEY — distribute to managed hosts   ║${NC}"
echo -e "${YELLOW}  ╚═══════════════════════════════════════════════════════╝${NC}"
echo -e "${GREEN}${ANSIBLE_PUBKEY}${NC}"
echo -e "${CYAN}  (also saved at ${KEY_PUB})${NC}"
echo

# Ensure the ansible user's own ~/.ssh has this key (for looping back / self-management)
ANSIBLE_SSH_DIR="${ANSIBLE_HOME}/.ssh"
mkdir -p "$ANSIBLE_SSH_DIR"
if ! grep -qF "$ANSIBLE_PUBKEY" "${ANSIBLE_SSH_DIR}/authorized_keys" 2>/dev/null; then
  # BUG FIX: echo appends the key but if the file already exists without a
  # trailing newline the new key runs directly onto the previous one, breaking
  # both entries.  printf ensures the file ends with \n before appending.
  [[ -s "${ANSIBLE_SSH_DIR}/authorized_keys" ]] && \
    tail -c1 "${ANSIBLE_SSH_DIR}/authorized_keys" | grep -qP '[^\n]' && \
    printf '\n' >> "${ANSIBLE_SSH_DIR}/authorized_keys"
  printf '%s\n' "$ANSIBLE_PUBKEY" >> "${ANSIBLE_SSH_DIR}/authorized_keys"
fi
chmod 700 "$ANSIBLE_SSH_DIR"
chmod 600 "${ANSIBLE_SSH_DIR}/authorized_keys"
chown -R "${ANSIBLE_USER}:${ANSIBLE_USER}" "$ANSIBLE_SSH_DIR"
success "Public key installed in ${ANSIBLE_USER}'s authorized_keys."

# Keep a copy of the sudoers file in files/ so playbooks can distribute it.
# Also explicitly apply it to this host — the drop-in was written above but
# only if it didn't exist; this ensures permissions are always correct.
cp "$SUDOERS_FILE" "${FILES_DIR}/sudoer_ansible"
chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "${FILES_DIR}/sudoer_ansible"
# Validate and install sudoers on this node
if visudo -cf "$SUDOERS_FILE" &>/dev/null; then
  chmod 0440 "$SUDOERS_FILE"
  chown root:root "$SUDOERS_FILE"
  success "sudoers drop-in validated and applied to this host."
else
  warn "sudoers validation failed — check ${SUDOERS_FILE} manually."
fi

# ------------------------------------------------------------------------------
# 7. PVE node discovery
# ------------------------------------------------------------------------------
section "7. PVE node discovery"

echo -e "${CYAN}  PVE nodes follow the standard octet convention:${NC}"
echo -e "${CYAN}    .5 = primary PVE node    (EXAPVE{SITE}001)${NC}"
echo -e "${CYAN}    .6 = secondary PVE node  (EXAPVE{SITE}002)${NC}"
echo -e "${CYAN}  All sites from the CSV will be pre-populated into [pvenodes].${NC}"
echo -e "${CYAN}  You will be asked for any additional nodes not covered by the CSV.${NC}"
echo

PVE_NODES=()

# Auto-populate .5 and .6 for every site from CSV
for site_code in $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort); do
  oct="${SITE_OCTET[$site_code]}"
  city="${SITE_CITY[$site_code]:-$site_code}"
  [[ -z "$oct" ]] && continue
  PVE_NODES+=("192.168.${oct}.5   # ${site_code} -- ${city} (primary)")
  PVE_NODES+=("192.168.${oct}.6   # ${site_code} -- ${city} (secondary)")
done

success "Pre-populated ${#SITE_OCTET[@]} sites x 2 nodes = $((${#SITE_OCTET[@]} * 2)) PVE entries from CSV."
echo -e "${CYAN}  These cover 192.168.x.5 and .6 for every site.${NC}"
echo -e "${CYAN}  Not all sites will have physical PVE nodes -- comment out entries as needed.${NC}"
echo

echo -e "${CYAN}  Enter any additional PVE node IPs not in the CSV (e.g. a DR host or${NC}"
echo -e "${CYAN}  a node on a non-standard octet). Blank to skip.${NC}"
echo

while true; do
  read -rp "  Additional PVE node IP (blank to finish): " PVE_INPUT
  [[ -z "$PVE_INPUT" ]] && break
  PVE_NODES+=("$PVE_INPUT")
  success "Added: ${PVE_INPUT}"
done

# ------------------------------------------------------------------------------
# 7b. Clear stale known_hosts entries before any SSH activity
# ------------------------------------------------------------------------------
# BUG FIX: this environment frequently rebuilds nodes at the same IP — including
# this very ansible node reusing its own provisioning IP from a prior build.
# Each rebuild generates a new host key. StrictHostKeyChecking=accept-new
# (used deliberately instead of 'no' as a MITM safeguard) will REJECT a host
# whose key has changed, which is exactly what happens when known_hosts still
# holds a fingerprint from the box's previous incarnation. Without this fix,
# both the discovery scan below AND the first ansible-playbook run can report
# "Host key verification failed" for hosts that are actually fine — the key
# just changed because the host was rebuilt, not because of an attack.
#
# This runs BEFORE the discovery scan (section 8) so the scan itself is not
# fooled by stale fingerprints. We clear keys for every IP this script knows
# about from the CSV (each site's .5, .6, .10, .253) plus this node's own
# provisioning IP — i.e. every address we are about to touch via SSH.
section "7b. Clearing stale SSH host keys"

ANSIBLE_KNOWN_HOSTS="${ANSIBLE_HOME}/.ssh/known_hosts"
mkdir -p "${ANSIBLE_HOME}/.ssh"
touch "$ANSIBLE_KNOWN_HOSTS"
chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "$ANSIBLE_KNOWN_HOSTS"
chmod 644 "$ANSIBLE_KNOWN_HOSTS"

PRESCAN_IPS=()
for site_code in "${!SITE_OCTET[@]}"; do
  oct="${SITE_OCTET[$site_code]}"
  [[ -z "$oct" ]] && continue
  PRESCAN_IPS+=("192.168.${oct}.5" "192.168.${oct}.6")
  [[ -n "${SITE_DC[$site_code]:-}" ]] && PRESCAN_IPS+=("${SITE_DC[$site_code]}")
  [[ -n "${SITE_FW[$site_code]:-}" ]] && PRESCAN_IPS+=("${SITE_FW[$site_code]}")
done
# This node's own provisioning-net IP, whichever it currently is.
PRESCAN_IPS+=("$(hostname -I | awk '{print $1}')")

CLEARED=0
for ip in "${PRESCAN_IPS[@]}"; do
  [[ -z "$ip" ]] && continue
  if ssh-keygen -R "$ip" -f "$ANSIBLE_KNOWN_HOSTS" &>/dev/null; then
    (( CLEARED++ )) || true
  fi
  if [[ -f /etc/ssh/ssh_known_hosts ]]; then
    ssh-keygen -R "$ip" -f /etc/ssh/ssh_known_hosts &>/dev/null || true
  fi
done
success "Checked ${#PRESCAN_IPS[@]} known address(es) for stale host keys."
info "accept-new will trust each host's current key on first connect from here on."

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# 8. Infrastructure discovery
# ------------------------------------------------------------------------------
section "8. Infrastructure discovery"

if [[ ! -f "$KEY_FILE" ]]; then
  warn "No private key found at ${KEY_FILE} yet."
  warn "An SSH subnet scan (option A below) will fail to reach any host until"
  warn "the private key is placed there. Either skip the scan and choose B or C,"
  warn "or place the private key now in another terminal before continuing."
  echo
fi

echo -e "${CYAN}  The inventory can be populated two ways:${NC}"
echo -e "${CYAN}  A) SSH subnet scan  — discovers live hosts, classifies by role, builds groups${NC}"
echo -e "${CYAN}  B) CSV-only fill    — builds inventory from sites.csv without scanning${NC}"
echo -e "${CYAN}  C) Skip             — leave inventory empty (fill manually later)${NC}"
echo
read -rp "  Choose [A/b/c]: " DISC_MODE
DISC_MODE="${DISC_MODE,,}"

# Known role octets (last octet → group name)
# .10  → dcs        (Domain Controllers / site servers)
# .253 → firewalls  (FWL LAN face)
# .254 → gateways   (router — usually not managed by ansible, but noted)
# .48  → pbx        (EXAPBX — telephony)
# .139.10 → ansible/srv nodes on provisioning net
declare -A DISC_HOSTS_BY_GROUP   # group → newline-separated "IP  # HOSTNAME ROLE"
DISC_UNKNOWNS=""                  # IP entries that didn't classify

_classify_host() {
  # Given an IP, PTR name, and the CSV data, return the inventory group name.
  local ip="$1" ptr="$2"
  local last_octet="${ip##*.}"
  local third_octet
  third_octet=$(echo "$ip" | awk -F. '{print $3}')

  # Provisioning net (.139.x) — ansible/DNS/srv nodes
  if [[ "$third_octet" == "139" ]]; then
    case "$last_octet" in
      10)  echo "ansiblehosts" ; return ;;
      *)   echo "srvnodes"     ; return ;;
    esac
  fi

  case "$last_octet" in
    10|11) echo "dcs"       ; return ;;
    253)   echo "firewalls" ; return ;;
    48)    echo "pbx"       ; return ;;
  esac

  echo "unknowns"
}

_scan_subnet() {
  local subnet="$1"
  local key="$2"

  if ! command -v prips &>/dev/null; then
    warn "prips not found — installing..."
    apt-get install -y -qq prips > /dev/null
  fi

  echo -e "  ${CYAN}Scanning ${subnet} ...${NC}"
  local found=0

  for ip in $(prips "$subnet"); do
    # Skip network and broadcast
    [[ "$ip" =~ \.(0|255)$ ]] && continue

    printf '    [*] %-17s ' "$ip"
    output=$(ssh -o BatchMode=yes \
                 -o ConnectTimeout=2 \
                 -o StrictHostKeyChecking=accept-new \
                 -o UserKnownHostsFile="${ANSIBLE_HOME}/.ssh/known_hosts" \
                 -i "$KEY_FILE" \
                 "ansible@${ip}" true 2>&1)
    rc=$?

    if [[ $rc -eq 0 ]]; then
      ptr=$(host "$ip" 2>/dev/null | awk '/pointer/ {print $NF}' | sed 's/\.$//')
      [[ -z "$ptr" ]] && ptr="(no PTR)"
      group=$(_classify_host "$ip" "$ptr")
      label="${ip}  # ${ptr}"
      printf "${GREEN}%-20s${NC} → [%s]\n" "UP" "$group"
      DISC_HOSTS_BY_GROUP[$group]+="${label}"$'\n'
      (( found++ )) || true
    else
      if echo "$output" | grep -qi "permission denied"; then
        printf "${YELLOW}AUTH FAIL${NC}\n"
        DISC_UNKNOWNS+="${ip}  # AUTH FAILED — key not deployed yet"$'\n'
      elif echo "$output" | grep -qi "connection refused"; then
        printf "REFUSED\n"
      elif echo "$output" | grep -qi "no route\|Network unreachable"; then
        printf "NO ROUTE\n"
      else
        printf "DOWN\n"
      fi
    fi
  done

  echo -e "  ${GREEN}Scan of ${subnet} complete — ${found} host(s) reachable via ansible key.${NC}"
}

if [[ "$DISC_MODE" != "b" && "$DISC_MODE" != "c" ]]; then
  # --- Mode A: SSH scan ---
  echo
  echo -e "${CYAN}  Which subnets to scan? (select all that apply)${NC}"
  echo -e "${CYAN}  Note: WireGuard tunnel subnets (10.0.x.0/24) only work if WG is already up.${NC}"
  echo -e "${CYAN}  Note: Site LAN subnets (192.168.x.0/24) only reachable if routing exists.${NC}"
  echo
  echo -e "  ${WHITE}1)${NC} Provisioning network only     (192.168.139.0/24)"
  echo -e "  ${WHITE}2)${NC} All site LAN subnets from CSV (192.168.x.0/24 — one per site, ~48 scans)"
  echo -e "  ${WHITE}3)${NC} WireGuard tunnel subnets      (10.0.x.0/24 — requires WG up)"
  echo -e "  ${WHITE}4)${NC} Custom subnet(s)              (you specify)"
  echo
  read -rp "  Enter choices space-separated [e.g. 1 3, default: 1]: " SCAN_CHOICE
  SCAN_CHOICE="${SCAN_CHOICE:-1}"

  SUBNETS_TO_SCAN=()

  for choice in $SCAN_CHOICE; do
    case "$choice" in
      1)
        SUBNETS_TO_SCAN+=("192.168.139.0/24")
        ;;
      2)
        echo -e "  ${CYAN}Adding all ${#SITE_OCTET[@]} site LAN subnets from CSV...${NC}"
        for site_code in $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort); do
          oct="${SITE_OCTET[$site_code]}"
          [[ -n "$oct" ]] && SUBNETS_TO_SCAN+=("192.168.${oct}.0/24")
        done
        ;;
      3)
        echo -e "  ${CYAN}Adding WireGuard tunnel subnets (10.0.x.0/24)...${NC}"
        for site_code in $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort); do
          oct="${SITE_OCTET[$site_code]}"
          [[ -n "$oct" ]] && SUBNETS_TO_SCAN+=("10.0.${oct}.0/24")
        done
        ;;
      4)
        echo -e "  ${CYAN}Enter custom subnets, one per line (blank to finish):${NC}"
        while true; do
          read -rp "    Subnet (e.g. 10.10.0.0/24): " CUSTOM_SUBNET
          [[ -z "$CUSTOM_SUBNET" ]] && break
          SUBNETS_TO_SCAN+=("$CUSTOM_SUBNET")
        done
        ;;
      *)
        warn "Unknown choice '$choice' — skipping."
        ;;
    esac
  done

  if [[ ${#SUBNETS_TO_SCAN[@]} -eq 0 ]]; then
    warn "No subnets selected — skipping scan."
  else
    echo
    echo -e "${CYAN}  Subnets to scan:${NC}"
    for s in "${SUBNETS_TO_SCAN[@]}"; do
      echo -e "    ${CYAN}•${NC} $s"
    done
    echo
    read -rp "  Proceed with scan? [Y/n]: " CONFIRM_SCAN
    if [[ "${CONFIRM_SCAN,,}" != "n" ]]; then
      for subnet in "${SUBNETS_TO_SCAN[@]}"; do
        _scan_subnet "$subnet" "$KEY_FILE"
        echo
      done

      # Summary
      echo -e "${GREEN}  ── Discovery summary ──────────────────────────────────────${NC}"
      for grp in "${!DISC_HOSTS_BY_GROUP[@]}"; do
        count=$(echo "${DISC_HOSTS_BY_GROUP[$grp]}" | grep -c '\.' || true)
        echo -e "    ${GREEN}[${grp}]${NC}: ${count} host(s)"
      done
      if [[ -n "$DISC_UNKNOWNS" ]]; then
        unknown_count=$(echo "$DISC_UNKNOWNS" | grep -c '\.' || true)
        warn "${unknown_count} unclassified host(s) — will appear in [unknowns] (commented out)"
      fi
      echo
    else
      info "Scan cancelled."
    fi
  fi
fi

if [[ "$DISC_MODE" == "b" ]]; then
  # --- Mode B: CSV-only fill ---
  echo -e "${CYAN}  Building inventory groups from CSV data (no scan)...${NC}"

  # Track seen IPs to avoid duplicates (e.g. BRD and BER share 192.168.113.x)
  declare -A _SEEN_DC _SEEN_FW

  for site_code in $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort); do
    dc_ip="${SITE_DC[$site_code]:-}"
    fw_ip="${SITE_FW[$site_code]:-}"
    city="${SITE_CITY[$site_code]:-$site_code}"

    if [[ -n "$dc_ip" ]]; then
      if [[ -n "${_SEEN_DC[$dc_ip]:-}" ]]; then
        # Duplicate IP — append site code to the existing comment
        DISC_HOSTS_BY_GROUP[dcs]="${DISC_HOSTS_BY_GROUP[dcs]//${dc_ip}  # ${_SEEN_DC[$dc_ip]}/${dc_ip}  # ${_SEEN_DC[$dc_ip]}/${site_code}}"
      else
        _SEEN_DC[$dc_ip]="${site_code} — ${city}"
        # Pad IP to 15 chars for alignment
        printf -v _entry "%-15s # %s — %s" "$dc_ip" "$site_code" "$city"
        DISC_HOSTS_BY_GROUP[dcs]+="${_entry}"$'\n'
      fi
    fi

    if [[ -n "$fw_ip" ]]; then
      if [[ -n "${_SEEN_FW[$fw_ip]:-}" ]]; then
        DISC_HOSTS_BY_GROUP[firewalls]="${DISC_HOSTS_BY_GROUP[firewalls]//${fw_ip}  # ${_SEEN_FW[$fw_ip]}/${fw_ip}  # ${_SEEN_FW[$fw_ip]}/${site_code}}"
      else
        _SEEN_FW[$fw_ip]="${site_code} — ${city}"
        printf -v _entry "%-15s # %s — %s" "$fw_ip" "$site_code" "$city"
        DISC_HOSTS_BY_GROUP[firewalls]+="${_entry}"$'\n'
      fi
    fi
  done

  success "CSV-derived groups built: [dcs] and [firewalls]."
  info  "[ansiblehosts] will contain this node (${SITE_DC[$SITE_CODE]:-$(hostname -I | awk '{print $1}')})."
  info  "[pvenodes] has been pre-populated with .5 and .6 for all ${#SITE_OCTET[@]} sites."
fi

# Allow operator to add extra groups on top of whatever was discovered
if [[ "$DISC_MODE" != "c" ]]; then
  echo
  echo -e "${CYAN}  Add any additional groups not covered above (e.g. switches, printers)?${NC}"
  echo -e "${CYAN}  Press Enter on blank group name to finish.${NC}"
  echo

  while true; do
    read -rp "  Extra group name (blank to finish): " GROUP_INPUT
    [[ -z "$GROUP_INPUT" ]] && break
    CURRENT_GROUP="${GROUP_INPUT,,}"
    [[ -z "${DISC_HOSTS_BY_GROUP[$CURRENT_GROUP]+x}" ]] && DISC_HOSTS_BY_GROUP[$CURRENT_GROUP]=""
    echo -e "  ${CYAN}Enter IPs/hostnames for [${CURRENT_GROUP}], blank to move on:${NC}"
    while true; do
      read -rp "    Host: " HOST_INPUT
      [[ -z "$HOST_INPUT" ]] && break
      DISC_HOSTS_BY_GROUP[$CURRENT_GROUP]+="${HOST_INPUT}"$'\n'
    done
  done
fi

# ------------------------------------------------------------------------------
# 9. Write ansible.cfg
# ------------------------------------------------------------------------------
section "9. Writing ansible.cfg"

cat > "$ANSIBLE_CFG" <<EOF
# =================================================================================================
# Ansible Configuration
#
# Purpose:
#   Central configuration for Example Music infrastructure automation.
#
# Used for:
#   - Initial host onboarding / bootstrap
#   - Inventory-driven configuration management
#   - Ongoing estate administration
#
# Environment assumptions:
#   - Hosts may be powered off at any time
#   - Inventory may be generated dynamically
#   - DNS may not exist during bootstrap
#   - SSH keys are distributed before Ansible runs
#
# Notes:
#   - Unreachable hosts are NOT ignored via ansible.cfg. That behaviour must be configured in
#     playbooks using:
#
#       ignore_unreachable: true
#
#     or handled explicitly with tasks/meta directives.
# =================================================================================================
[defaults]
# Automatically discover correct Python interpreter on remote systems sans warnings.
interpreter_python = auto_silent
host_key_checking  = True
# Primary inventory location.
inventory = ${CONFIGS_DIR}/inventory
# Default SSH user.
remote_user = ${ANSIBLE_USER}
# SSH private key used for authentication.
private_key_file = ${KEY_FILE}
# Human-readable task output.
stdout_callback = ansible.builtin.default
result_format = yaml
# Enable callback plugins.
bin_ansible_callbacks = True
# Number of parallel worker processes. Default is 5. Increasing improves performance when managing
# large numbers of hosts.
forks = 50
# SSH connection timeout (seconds). Important when hosts may be powered off. Prevents long waits
# for unreachable systems.
timeout = 5
# Retry files record failed hosts and can be useful for rerunning failed operations. Store them in
# /tmp rather than cluttering working directories.
retry_files_enabled = True
retry_files_save_path = /tmp

[privilege_escalation]
# Standard privilege escalation settings.
become = True
become_method = sudo
become_user = root

[ssh_connection]
# SSH connection settings.
#
# ControlMaster=auto                Reuse existing SSH sessions where possible.
# ControlPersist=60s                Keep SSH control connections alive for 60 seconds.
# StrictHostKeyChecking=accept-new  Automatically trust new, while detecting changed fingerprints.
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=accept-new
# Enable SSH pipelining. Reduces the number of SSH operations required & can significantly improve
# execution speed.
pipelining = True
# Fail quickly when a host is unavailable.
connect_timeout = 5

[persistent_connection]
# Settings used by persistent SSH connections. Useful for larger environments and network modules.
# Maximum command runtime.
command_timeout = 30
# Time spent retrying persistent connections.
connect_retry_timeout = 15
# =================================================================================================
# RECOMMENDED PLAYBOOK SETTINGS FOR INTERMITTENT HOSTS
# =================================================================================================
#
# Example:
#
# - hosts: all
#   gather_facts: false
#   ignore_unreachable: true
#   strategy: free
#
# Explanation:
#
# gather_facts: false         Avoid immediate failures during fact gathering.
# ignore_unreachable: true    Continue processing remaining hosts even if some nodes are offline.
# strategy: free              Allows hosts to progress independently instead of waiting for the
#                             slowest host.
# =================================================================================================
EOF

chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "$ANSIBLE_CFG"
success "ansible.cfg written."

# ------------------------------------------------------------------------------
# 10. Write inventory
# ------------------------------------------------------------------------------
section "10. Writing inventory"

{
  echo "# Ansible inventory — generated by ansibleme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "# Host: $(hostname)  Site: ${SITE_CODE}"
  echo
  echo "[ansiblehosts]"
  # Use SITE_DC for this node's own IP — canonical .10 management address.
  # Falls back to hostname -I only if the site code has no DC entry in CSV.
  THIS_MGMT_IP="${SITE_DC[$SITE_CODE]:-$(hostname -I | awk '{print $1}')}"
  printf "%-15s # %s\n" "${THIS_MGMT_IP}" "$(hostname)"
  echo

  # [pvenodes] is always written — pre-populated from CSV .5/.6 per site.
  # Entries not physically present can be commented out manually afterwards.
  echo "[pvenodes]"
  for node in "${PVE_NODES[@]}"; do
    # Entries from CSV auto-fill already have the comment; pad IP portion only
    # if this looks like a bare IP (no # already present).
    if [[ "$node" == *"#"* ]]; then
      ip_part="${node%%#*}"
      comment_part="# ${node#*# }"
      printf "%-15s %s\n" "${ip_part%% }" "${comment_part}"
    else
      printf "%-15s\n" "$node"
    fi
  done
  echo

  for grp in $(echo "${!DISC_HOSTS_BY_GROUP[@]}" | tr ' ' '\n' | sort); do
    [[ "$grp" == "unknowns" ]] && continue   # handled separately below
    [[ -z "${DISC_HOSTS_BY_GROUP[$grp]}" ]] && continue
    echo "[${grp}]"
    echo -n "${DISC_HOSTS_BY_GROUP[$grp]}"
    echo
  done

  # Unknowns — commented out so the file is valid but prompts the operator
  if [[ -n "${DISC_HOSTS_BY_GROUP[unknowns]:-}" || -n "$DISC_UNKNOWNS" ]]; then
    echo "# ── Unclassified hosts ────────────────────────────────────────────"
    echo "# These hosts responded but could not be automatically classified."
    echo "# Uncomment and move to the correct group, or investigate manually."
    echo "#"
    echo "# [unknowns]"
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      echo "# ${line}"
    done <<< "${DISC_HOSTS_BY_GROUP[unknowns]:-}${DISC_UNKNOWNS}"
    echo
  fi

  # Convenience meta-group: everything we manage
  echo "[managed:children]"
  [[ ${#PVE_NODES[@]} -gt 0 ]] && echo "pvenodes"
  for grp in $(echo "${!DISC_HOSTS_BY_GROUP[@]}" | tr ' ' '\n' | sort); do
    [[ "$grp" == "unknowns" ]] && continue
    [[ -z "${DISC_HOSTS_BY_GROUP[$grp]}" ]] && continue
    echo "$grp"
  done

} > "$INVENTORY_FILE"

chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "$INVENTORY_FILE"
success "Inventory written to ${INVENTORY_FILE}"

# ------------------------------------------------------------------------------
# 10b. Final pass: clear stale known_hosts for the actual written inventory
# ------------------------------------------------------------------------------
# Section 7b already cleared stale keys for every CSV-derived IP (.5/.6/.10/.253
# for all sites) before the discovery scan ran. This second pass is a cheap
# catch-all over the FINAL inventory file, covering anything 7b's CSV-only
# sweep could not know about yet: custom subnets entered in discovery mode A
# choice 4, or extra groups added manually at the end of section 8. Both
# passes use the same accept-new-safe approach — see 7b for the full rationale.
section "10b. Clearing stale SSH host keys for managed IPs"

ANSIBLE_KNOWN_HOSTS="${ANSIBLE_HOME}/.ssh/known_hosts"
mkdir -p "${ANSIBLE_HOME}/.ssh"
touch "$ANSIBLE_KNOWN_HOSTS"
chown "${ANSIBLE_USER}:${ANSIBLE_USER}" "$ANSIBLE_KNOWN_HOSTS"
chmod 644 "$ANSIBLE_KNOWN_HOSTS"

# Extract every IP address that appears in the inventory directory (first column
# of any non-comment, non-group-header, non-blank line across all .ini files).
mapfile -t MANAGED_IPS < <(
  grep -hE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' "${CONFIGS_DIR}/inventory/"*.ini 2>/dev/null \
    | awk '{print $1}' | sort -u
)

if [[ ${#MANAGED_IPS[@]} -eq 0 ]]; then
  info "No IPs found in inventory yet — nothing to clear."
else
  CLEARED=0
  for ip in "${MANAGED_IPS[@]}"; do
    # ssh-keygen -R is idempotent and silent if no entry exists.
    if ssh-keygen -R "$ip" -f "$ANSIBLE_KNOWN_HOSTS" &>/dev/null; then
      (( CLEARED++ )) || true
    fi
    # Also clear the system-wide file in case a previous manual SSH (e.g. as
    # root or another user) cached a stale key there.
    if [[ -f /etc/ssh/ssh_known_hosts ]]; then
      ssh-keygen -R "$ip" -f /etc/ssh/ssh_known_hosts &>/dev/null || true
    fi
  done
  success "Checked ${#MANAGED_IPS[@]} managed IP(s); cleared any stale host key entries."
  info "accept-new will silently trust each host's current key on first connect."
fi

# ------------------------------------------------------------------------------
# 11. group_vars scaffolding

# ------------------------------------------------------------------------------
section "11. group_vars scaffolding"

# all — vars that apply to every managed host
cat > "${ANSIBLE_DIR}/group_vars/all/main.yml" <<EOF
---
# group_vars/all/main.yml
# Generated by ansibleme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)

ansible_user:        ${ANSIBLE_USER}
ansible_become:      true
ansible_become_method: sudo

# Common packages deployed to every Linux host
common_packages:
  - curl
  - dnsutils
  - net-tools
  - nmap
  - tree
  - vim
  - wget
  - grc
  - zsh
  - yamllint
EOF

# pvenodes — PVE-specific vars
cat > "${ANSIBLE_DIR}/group_vars/pvenodes/main.yml" <<EOF
---
# group_vars/pvenodes/main.yml
# Proxmox-specific variables

pve_packages:
  - libguestfs-tools
  - python3-proxmoxer
  - python3-requests
  - python3-virtualenv
  - sudo

# Cloud image template IDs (update after first run)
template_ubuntu_noble:    1000
template_debian_trixie:   1001

# Default storage pool for new VMs
pve_default_storage: local-lvm
EOF

chown -R "${ANSIBLE_USER}:${ANSIBLE_USER}" "${ANSIBLE_DIR}/group_vars"
success "group_vars scaffolding written."

# ------------------------------------------------------------------------------
# 12. Write playbooks
# ------------------------------------------------------------------------------
section "12. Writing playbooks"

cat > "${PLAYBOOKS_DIR}/proxmox/pve_onboard.yml" <<'EOF'
---
# pve_onboard.yml
# Verify and complete Ansible management setup on a Proxmox VE node.
#
# Our PXE/first-boot installer creates the ansible user, but we trust-but-verify:
#   - ansible user exists and has the right shell
#   - SSH key is authorised
#   - sudoers drop-in is present and correct
#   - management packages installed
#
# Run once per new PVE node, as root via SSH password:
#   ansible-playbook playbooks/proxmox/pve_onboard.yml \
#     -i configs/inventory --user=root -k
#
# After this runs once, all subsequent playbooks authenticate as ansible (key-based).

- hosts: pvenodes
  become: true
  vars_files:
    - ../../group_vars/pvenodes/main.yml

  tasks:

    - name: Install management packages
      apt:
        name: "{{ pve_packages }}"
        update_cache: yes
        cache_valid_time: 3600
        state: latest

    - name: Verify ansible user exists (created by PXE installer; created here if missing)
      user:
        name: ansible
        shell: /bin/bash
        create_home: yes
        state: present

    - name: Ensure ansible SSH public key is authorised
      authorized_key:
        user: ansible
        key: "{{ lookup('file', '../../configs/ansible-id_rsa.pub') }}"
        state: present

    - name: Deploy sudoers drop-in (validate before placing)
      copy:
        src: ../../files/sudoer_ansible
        dest: /etc/sudoers.d/ansible
        owner: root
        group: root
        mode: '0440'
        validate: /usr/sbin/visudo -cf %s

    - name: Ensure ansible is in kvm group (needed for virt-customize)
      user:
        name: ansible
        groups: kvm
        append: yes

EOF

# ── linux/tools.yml ──────────────────────────────────────────
cat > "${PLAYBOOKS_DIR}/linux/tools.yml" <<'EOF'
---
# linux/tools.yml
# Deploy common tools to all Linux hosts.
#   ansible-playbook playbooks/linux/tools.yml -i configs/inventory

- name: Deploy common tools
  hosts: all
  become: true
  vars_files:
    - ../../group_vars/all/main.yml

  tasks:

    - name: Install common packages
      apt:
        name: "{{ common_packages }}"
        state: latest
        update_cache: true
        cache_valid_time: 3600

    - name: Set default shell to zsh for ansible user
      user:
        name: ansible
        shell: /bin/zsh

EOF

# ── proxmox/cloud_templates.yml ──────────────────────────────
cat > "${PLAYBOOKS_DIR}/proxmox/cloud_templates.yml" <<'EOF'
---
# proxmox/cloud_templates.yml
# Build Ubuntu Noble and Debian Trixie cloud-init templates.
# Must run on a PVE node as ansible (has kvm group, sudo).
#   ansible-playbook playbooks/proxmox/cloud_templates.yml \
#     -i configs/inventory --limit pvenodes
#
# Idempotent: skips download/build if template ID already exists.
# TODO: extend for Windows template (separate task file)

- name: Build cloud-init VM templates
  hosts: pvenodes
  become: true
  vars_files:
    - ../../group_vars/pvenodes/main.yml

  vars:
    images:
      - name: ubuntu-noble-2404-cloudinit-template
        vmid: "{{ template_ubuntu_noble }}"
        url: https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
        dest: /home/ansible/noble-server-cloudimg-amd64.img

      - name: debian-trixie-13-cloudinit-template
        vmid: "{{ template_debian_trixie }}"
        url: https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2
        dest: /home/ansible/debian-13-genericcloud-amd64.qcow2

  tasks:

    - name: Check which templates already exist
      command: qm list
      register: qm_list_out
      changed_when: false

    - name: Download cloud image (if template does not exist)
      get_url:
        url: "{{ item.url }}"
        dest: "{{ item.dest }}"
        mode: '0644'
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Update packages in cloud image
      command: virt-customize -a {{ item.dest }} --update
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Install tools in cloud image
      command: >
        virt-customize -a {{ item.dest }}
        --install net-tools,qemu-guest-agent,vim,grc,curl
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Add ansible user in cloud image
      command: >
        virt-customize -a {{ item.dest }}
        --run-command 'useradd --shell /bin/bash ansible'
        --run-command 'mkdir -p /home/ansible/.ssh'
        --run-command 'chown -R ansible:ansible /home/ansible'
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Inject ansible SSH key into cloud image
      command: >
        virt-customize -a {{ item.dest }}
        --ssh-inject ansible:file:/home/ansible/.ssh/authorized_keys
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Inject sudoers file into cloud image
      command: >
        virt-customize -a {{ item.dest }}
        --upload /etc/sudoers.d/ansible:/etc/sudoers.d/ansible
        --run-command 'chmod 0440 /etc/sudoers.d/ansible'
        --run-command 'chown root:root /etc/sudoers.d/ansible'
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Blank machine-id in cloud image
      command: >
        virt-customize -a {{ item.dest }}
        --run-command 'echo -n >/etc/machine-id'
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Create VM from cloud image
      command: >
        /usr/sbin/qm create {{ item.vmid }}
        --name "{{ item.name }}"
        --memory 2048
        --cores 2
        --net0 virtio,bridge=vmbr0
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Import disk
      command: >
        /usr/sbin/qm importdisk {{ item.vmid }} {{ item.dest }} {{ pve_default_storage }}
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Attach disk and configure VM
      shell: |
        /usr/sbin/qm set {{ item.vmid }} --scsihw virtio-scsi-pci --scsi0 {{ pve_default_storage }}:vm-{{ item.vmid }}-disk-0
        /usr/sbin/qm set {{ item.vmid }} --boot c --bootdisk scsi0
        /usr/sbin/qm set {{ item.vmid }} --ide2 {{ pve_default_storage }}:cloudinit
        /usr/sbin/qm set {{ item.vmid }} --serial0 socket --vga serial0
        /usr/sbin/qm set {{ item.vmid }} --agent enabled=1
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Convert to template
      command: /usr/sbin/qm template {{ item.vmid }}
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

    - name: Remove downloaded image (clean up)
      file:
        path: "{{ item.dest }}"
        state: absent
      loop: "{{ images }}"
      when: item.vmid | string not in qm_list_out.stdout

EOF

chown -R "${ANSIBLE_USER}:${ANSIBLE_USER}" "${PLAYBOOKS_DIR}"
success "Playbooks written."

# ------------------------------------------------------------------------------
# 13. Connectivity test (optional)
# ------------------------------------------------------------------------------
section "13. Connectivity test"

RUN_PING="n"
if [[ ${#PVE_NODES[@]} -gt 0 ]]; then
  echo -e "${CYAN}  PVE nodes have been configured in the inventory.${NC}"
  echo -e "${CYAN}  The ansible user should already exist on each node (created by the PXE installer).${NC}"
  echo
  read -rp "  Run SSH connectivity test to PVE nodes now? [y/N] " RUN_PING
fi

if [[ "${RUN_PING,,}" == "y" ]]; then
  echo
  echo -e "${CYAN}  Testing SSH connectivity (ansible ping) to [pvenodes]...${NC}"
  echo -e "${CYAN}  Hosts not yet fully onboarded may show UNREACHABLE — that's expected.${NC}"
  echo

  PING_OUT=$(sudo -u "$ANSIBLE_USER" \
    ansible pvenodes -i "${CONFIGS_DIR}/inventory" -m ping 2>&1 || true)

  echo "$PING_OUT"
  echo

  UNREACHABLE=$(echo "$PING_OUT" | grep -c "UNREACHABLE" || true)
  FAILED=$(echo "$PING_OUT" | grep -c "FAILED" || true)
  SUCCESS_COUNT=$(echo "$PING_OUT" | grep -c "pong" || true)

  if [[ $SUCCESS_COUNT -gt 0 ]]; then
    success "${SUCCESS_COUNT} node(s) responded to ping."
  fi
  if [[ $UNREACHABLE -gt 0 || $FAILED -gt 0 ]]; then
    warn "${UNREACHABLE} unreachable / ${FAILED} failed."
    warn "Run pve_onboard.yml as root to complete setup:"
    warn "  ansible-playbook ${PLAYBOOKS_DIR}/proxmox/pve_onboard.yml -i ${CONFIGS_DIR}/inventory --user=root -k"
  fi
else
  info "Skipping connectivity test."
  if [[ ${#PVE_NODES[@]} -gt 0 ]]; then
    info "Run manually any time: ansible pvenodes -i ${CONFIGS_DIR}/inventory -m ping"
  fi
fi

# ------------------------------------------------------------------------------
# 14. Dynamic MOTD
# ------------------------------------------------------------------------------
section "14. Dynamic MOTD"

CITY="${SITE_DISPLAY_CITY:-${SITE_CODE}}"
COUNTRY="${SITE_DISPLAY_COUNTRY:-Unknown}"
ENTITY="${SITE_DISPLAY_ENTITY:-Example Music}"

cat > /etc/update-motd.d/10-examplemusic <<MOTD
#!/usr/bin/env bash
WH='\033[1;37m'; YL='\033[1;33m'; GR='\033[0;32m'; CY='\033[0;36m'; NC='\033[0m'
UPTIME=\$(uptime -p)
LOAD=\$(cut -d' ' -f1-3 /proc/loadavg)
MEM_TOTAL=\$(awk '/MemTotal/{print int(\$2/1024)}' /proc/meminfo)
MEM_FREE=\$(awk '/MemAvailable/{print int(\$2/1024)}' /proc/meminfo)
MEM_USED=\$(( MEM_TOTAL - MEM_FREE ))
DISK=\$(df -h / | awk 'NR==2{print \$3" used of "\$2" ("\$5")"}')
ANSIBLE_VER=\$(ansible --version 2>/dev/null | head -1 || echo "not found")
INV_HOSTS=\$(ansible all -i ${CONFIGS_DIR}/inventory --list-hosts 2>/dev/null | tail -n +2 | wc -l || echo "?")
echo -e "
\${WH}╔══════════════════════════════════════════════════════════════╗\${NC}
\${WH}║     EXAMPLE MUSIC LIMITED: \$(printf '%-35s' "\${HOSTNAME}")║\${NC}
\${WH}╚══════════════════════════════════════════════════════════════╝\${NC}

  \${YL}Site     :\${NC} ${SITE_CODE}: ${CITY}, ${COUNTRY}
  \${YL}Entity   :\${NC} ${ENTITY}
  \${YL}Role     :\${NC} Ansible management node

  \${WH}── Ansible ───────────────────────────────────────────────────\${NC}
    \${CY}Version\${NC}  : \${GR}\${ANSIBLE_VER}\${NC}
    \${CY}Inventory\${NC}: \${GR}${CONFIGS_DIR}/inventory\${NC}
    \${CY}Hosts\${NC}    : \${GR}\${INV_HOSTS} managed host(s)\${NC}

  \${WH}── System ────────────────────────────────────────────────────\${NC}
    \${CY}Uptime\${NC}   : \${GR}\${UPTIME}\${NC}
    \${CY}Load\${NC}     : \${GR}\${LOAD}\${NC}
    \${CY}Memory\${NC}   : \${GR}\${MEM_USED}MB\${NC} used of \${MEM_TOTAL}MB
    \${CY}Disk /\${NC}   : \${GR}\${DISK}\${NC}

  \${WH}── Quick reference ───────────────────────────────────────────\${NC}
    \${CY}Onboard PVE :\${NC} ansible-playbook ${PLAYBOOKS_DIR}/proxmox/pve_onboard.yml -i ${CONFIGS_DIR}/inventory --user=root -k
    \${CY}Ping all    :\${NC} ansible all -i ${CONFIGS_DIR}/inventory -m ping
    \${CY}Templates   :\${NC} ansible-playbook ${PLAYBOOKS_DIR}/proxmox/cloud_templates.yml
"
MOTD

chmod +x /etc/update-motd.d/10-examplemusic

if grep -q "^PrintMotd" /etc/ssh/sshd_config 2>/dev/null; then
  sed -i "s/^PrintMotd.*/PrintMotd yes/" /etc/ssh/sshd_config
else
  echo "PrintMotd yes" >> /etc/ssh/sshd_config
fi

cat > /etc/profile.d/motd.sh <<'EOF'
[[ -x /etc/update-motd.d/10-examplemusic ]] && /etc/update-motd.d/10-examplemusic
EOF

systemctl restart ssh 2>/dev/null || true
success "Dynamic MOTD configured."

# ------------------------------------------------------------------------------
# 15. Sentinel file
# ------------------------------------------------------------------------------
{
  echo "Configured by Example Music ansibleme.sh"
  echo "Site        : ${SITE_CODE}"
  echo "City        : ${SITE_DISPLAY_CITY}"
  echo "Country     : ${SITE_DISPLAY_COUNTRY}"
  echo "Entity      : ${SITE_DISPLAY_ENTITY}"
  echo "Ansible dir : ${ANSIBLE_DIR}"
  echo "Inventory   : ${CONFIGS_DIR}/inventory"
  echo "SSH key     : ${KEY_FILE}"
  echo "PVE nodes   : ${PVE_NODES[*]:-none}"
  echo "Date        : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$SENTINEL"
chmod 0444 "$SENTINEL"
success "Sentinel file written to ${SENTINEL}"

# ------------------------------------------------------------------------------
# 16. Final banner
# ------------------------------------------------------------------------------
echo
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  SETUP COMPLETE — $(hostname)${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "${CYAN}  Site          : ${SITE_CODE} — ${SITE_DISPLAY_CITY}, ${SITE_DISPLAY_COUNTRY}${NC}"
echo -e "${CYAN}  Ansible dir   : ${ANSIBLE_DIR}${NC}"
echo -e "${CYAN}  Inventory     : ${CONFIGS_DIR}/inventory${NC}"
echo -e "${CYAN}  SSH key       : ${KEY_FILE}${NC}"
echo -e "${CYAN}  ansible.cfg   : ${ANSIBLE_CFG}${NC}"
echo

if [[ ! -f "$KEY_FILE" ]]; then
  echo -e "${YELLOW}  +==================================================================+${NC}"
  echo -e "${YELLOW}  |  REMINDER — PRIVATE KEY NOT YET PLACED ON THIS HOST              |${NC}"
  echo -e "${YELLOW}  +==================================================================+${NC}"
  echo -e "${YELLOW}  |${NC}  No ansible-playbook or ad-hoc run will succeed until the"
  echo -e "${YELLOW}  |${NC}  matching private key is copied to:"
  echo -e "${YELLOW}  |${NC}"
  echo -e "${YELLOW}  |${NC}    ${WHITE}${KEY_FILE}${NC}  ${YELLOW}(chown ${ANSIBLE_USER}:${ANSIBLE_USER}, chmod 600)${NC}"
  echo -e "${YELLOW}  +==================================================================+${NC}"
  echo
fi

if [[ ${#PVE_NODES[@]} -gt 0 ]]; then
  echo -e "${CYAN}  PVE nodes     :${NC}"
  if [[ ${#PVE_NODES[@]} -gt 0 ]]; then
    i=0
    for node in "${PVE_NODES[@]}"; do
      ## Strip the trailing (primary)/(secondary) tag for the compact summary
      short="${node%% (*}"
      printf "    %-26s" "$short"
      (( i++ ))
      (( i % 3 == 0 )) && echo
    done
    (( i % 3 != 0 )) && echo
  fi

  echo
  echo -e "${YELLOW}  ╔═══════════════════════════════════════════════════════╗${NC}"
  echo -e "${YELLOW}  ║   NEXT STEP: onboard each PVE node                    ║${NC}"
  echo -e "${YELLOW}  ╚═══════════════════════════════════════════════════════╝${NC}"
  echo
  echo -e "${GREEN}  ansible-playbook ${PLAYBOOKS_DIR}/proxmox/pve_onboard.yml -i ${CONFIGS_DIR}/inventory --user=root -k${NC}"
  echo
  echo -e "${CYAN}  This deploys the ansible user + key + sudoers to each PVE node.${NC}"
  echo -e "${CYAN}  After that, all subsequent playbooks run passwordless.${NC}"
fi
echo
echo -e "${YELLOW}  Public key (distribute to any host not yet onboarded):${NC}"
echo -e "${GREEN}  $(cat "$KEY_PUB")${NC}"
echo
echo -e "${GREEN}============================================================${NC}"
echo
