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
#   2026-07-07  Trimmed to the ansible-bootstrap sliver + local-only convenience steps. Ansible now does the rest:
#               removed the interactive site/hostname/gateway/IP prompts and confirmation gate (was Step 2), removed
#               Step 7 (rename node + rewrite /etc/network/interfaces + hostnamectl + postfix + pvesh DNS) -- both are
#               now ansible/playbooks/proxmox/bootstrap-new-node.yml, run against this node's DHCP IP once this script
#               finishes. Also removed Steps 3b/3c/3d (V2V prereqs, VirtIO ISO, proxmoxbmc) and 3e/3f/3g (sites.csv
#               placement, BIOS ROM files, provisioning-script placement) plus the profile.d SITES_CSV export tied to
#               3e -- all of these already referenced an undefined $PROV_PKG_PATH (dead code, not working
#               functionality) and are being ported into ansible/playbooks/proxmox/playbooks/40-scripts.yml instead,
#               which can copy the provisioning scripts directly from the git checkout instead of an HTTP fetch. This
#               script no longer reads sites.csv at all -- removed load_sites_csv()/SITE_OCTET etc, and the now-unused
#               ip_in_use()/suggest_ip() helpers that only Step 2 called. The ansible-user/SSH-key step (Step 4) is
#               untouched -- that's the one thing that must still happen here, before Ansible can connect at all.
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

# ── Step 3: Install packages ──────────────────────────────────────────────────
section "INSTALLING PACKAGES"

step "Installing core packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server sudo net-tools bash-completion tree bc molly-guard arping nmap parted gdisk smartmontools vim zsh grc python3-proxmoxer python3-textual python3-requests python3-pbr python3-six w3m xxd jq 2>&1 | \
grep -E "^(Setting up|Unpacking)" | sed 's/^/    /'
ok "Core packages installed"
ok "molly-guard active -- protects against accidental reboots/shutdowns"

# ── Step 3b: Environment ──────────────────────────────────────────────────────
section "ENVIRONMENT"
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
  read -rp "$(echo -e "  Environment ((${W}p${NC})roduction, (${W}s${NC})taging, (${W}d${NC})evelopment) [default: production]: ")" ENV
  ENV="${ENV,,}"
  case "$ENV" in
    p) ENV_LONG="production" ;;
    s) ENV_LONG="staging" ;;
    d) ENV_LONG="development" ;;
    *) warn "Invalid or empty — defaulting to production"; ENV_LONG="production" ;;
  esac
  echo "$ENV_LONG" > /etc/.environment
  ok "Environment set to: ${ENV_LONG}"
fi

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
if [[ -f /etc/example-music/nodeinfo.json ]] && command -v jq &>/dev/null; then
  SITE=$(   jq -r '.site     // "UNKNOWN"'       /etc/example-music/nodeinfo.json)
  CITY=$(   jq -r '.city     // "Unknown"'       /etc/example-music/nodeinfo.json)
  COUNTRY=$(jq -r '.country  // "GB"'            /etc/example-music/nodeinfo.json)
  ENTITY=$( jq -r '.entity   // "Example Music"' /etc/example-music/nodeinfo.json)
  NODE_IP=$(jq -r '.node_ip  // "unknown"'       /etc/example-music/nodeinfo.json)
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

# ── Summary ───────────────────────────────────────────────────────────────────
echo
echo -e "${G}  +======================================================+${NC}"
echo -e "${G}  |${W}  ANSIBLE-BOOTSTRAP COMPLETE                           ${G}|${NC}"
echo -e "${G}  +======================================================+${NC}"
echo
CURRENT_IP=$(ip -4 addr show vmbr0 2>/dev/null | awk '/inet /{print $2}' | head -1)
CURRENT_IP="${CURRENT_IP:-unknown}"
SSH_KEY_COUNT=$(wc -l < /home/${ANSIBLE_USER}/.ssh/authorized_keys 2>/dev/null || echo 0)

printf "  ${G}[+]${NC}  %-18s %s\n" "Current IP :"   "${W}${CURRENT_IP} (DHCP, provisioning network)${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "Environment :"  "${W}${ENV_LONG}${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "Ansible user :" "${W}${ANSIBLE_USER} -- ${SSH_KEY_COUNT} SSH key(s)${NC}"
printf "  ${G}[+]${NC}  %-18s %s\n" "molly-guard :"  "${W}active${NC}"
echo
echo -e "${C}  +------------------------------------------------------+${NC}"
echo -e "${C}  |  NEXT STEP: Ansible finishes this node's setup       |${NC}"
echo -e "${C}  |                                                       |${NC}"
echo -e "${C}  |  This node still has its installer placeholder       |${NC}"
echo -e "${C}  |  hostname and a DHCP IP -- that's expected. From      |${NC}"
echo -e "${C}  |  the Ansible control node, run:                      |${NC}"
echo -e "${C}  |                                                       |${NC}"
echo -e "${C}  |    ansible-playbook -i \"${CURRENT_IP},\" \\               |${NC}"
echo -e "${C}  |      playbooks/proxmox/bootstrap-new-node.yml         |${NC}"
echo -e "${C}  |                                                       |${NC}"
echo -e "${C}  |  You'll be prompted for this node's real hostname     |${NC}"
echo -e "${C}  |  (from your build sheet, e.g. EXAPVEKGE001) -- it     |${NC}"
echo -e "${C}  |  sets the real hostname and static network config.    |${NC}"
echo -e "${C}  |  The SSH session on this DHCP IP will then drop --    |${NC}"
echo -e "${C}  |  reconnect via the new hostname/IP, add it to         |${NC}"
echo -e "${C}  |  configs/inventory/, then run proxmox/site.yml as     |${NC}"
echo -e "${C}  |  normal.                                              |${NC}"
echo -e "${C}  +------------------------------------------------------+${NC}"
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
info "No reboot is required by this script -- networking/hostname are unchanged."
info "A reboot is still fine if you want one for a clean state (e.g. after kernel updates)."
read -rp "$(echo -e "  ${Y}Reboot now? [y/N]: ${NC}")" REBOOT
if [[ "$REBOOT" =~ ^[Yy]$ ]]; then
  info "Rebooting in 5 seconds -- Ctrl-C to cancel"
  sleep 5
  reboot
else
  ok "Skipping reboot. Run 'ansible-playbook ... playbooks/proxmox/bootstrap-new-node.yml' next."
fi
