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
#   2026-07-08  SSH_KEY_URL was hardcoded to Edinburgh (192.168.139.50) -- did not account for the
#               Fredericia Havn provisioning server (172.16.124.1:8000, legal fiction, physically a
#               MacBook). Added the same gateway-detection late_command.sh/menu.ipxe already use, so
#               this fetch (and any future one added to this step) picks the right server.
#   2026-07-10  Trimmed again, to the "foot in the door" principle: this script now does ONLY what
#               must happen before Ansible can connect at all -- ensure sshd is present, create the
#               ansible user, install its SSH key, configure NOPASSWD sudoers. Everything else moved
#               to ansible/playbooks/proxmox/playbooks/ (which already runs immediately after this
#               script, via bootstrap-new-node.yml then site.yml): apt repo fixing + subscription-nag
#               removal + VMware guest-tools detection -> 10-packages.yml; kvm group membership ->
#               20-ansible-access.yml (was already redundant here); extra packages (net-tools,
#               molly-guard, vim, zsh, etc.) -> pve_packages in group_vars/pvenodes/main.yml;
#               .vimrc/.zshrc/zsh-as-shell -> playbooks/linux/tools.yml (already estate-wide, already
#               redundant here); /etc/.environment prompt -> 00-preflight.yml, matching the existing
#               firewallme/bind9-dns.yml pattern; single-disk ZFS warning -> 00-preflight.yml as an
#               explicit -e pve_acknowledge_single_disk=true gate instead of a console "type I
#               UNDERSTAND" prompt; dynamic MOTD -> 40-scripts.yml. The reboot prompt is dropped
#               entirely -- nothing left in this script touches anything that needs one.
#   2026-07-11  Fixed 3 bugs found running this for real against a disposable PVE node for the
#               first time (proxmox-first-boot-multi-user.service, no controlling TTY):
#               1) `clear` was the very first command under `set -e` -- with no TTY, $TERM is
#                  unset, `clear` exits non-zero, and the whole script died before Step 1 ever
#                  ran. Now `clear 2>/dev/null || true`.
#               2) CURRENT_IP (from `ip -4 addr show vmbr0`) kept its /24 CIDR suffix, which then
#                  landed straight in the printed `ansible-playbook -i "<ip>,"` next-step command
#                  -- not a valid inventory host pattern. Now stripped with `${CURRENT_IP%%/*}`.
#               3) The two summary printf lines embedded $W/$NC (escape-sequence variables) inside
#                  the %s-substituted arguments, not printf's own format string -- printf only
#                  expands backslash escapes that are literally present in the format string, so
#                  they printed as literal `\033[...m` text instead of colour. Every other message
#                  in this script uses `echo -e` (which does expand them). Switched these two lines
#                  to `echo -e` as well, keeping printf only for the `%-18s` label padding.
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
clear 2>/dev/null || true
echo
echo -e "${C}  +======================================================+${NC}"
echo -e "${C}  |${W}        PROXMOX VE - NODE PROVISIONING                ${C}|${NC}"
echo -e "${C}  |${D}              jukebox.internal                         ${C}|${NC}"
echo -e "${C}  +======================================================+${NC}"
echo

# ── Step 1: Ensure sshd is present ────────────────────────────────────────────
# PVE ISO installs include openssh-server/sudo by default -- this is defensive,
# not a real dependency-fix. Everything else the old script did here (repo
# fixing, subscription nag, VMware tools, /etc/.environment, extra packages)
# moved to ansible/playbooks/proxmox/playbooks/10-packages.yml -- none of it
# is needed before Ansible can get a foot in the door.
section "ENSURING SSH SERVER"

step "Installing openssh-server + sudo (if missing)..."
DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server sudo 2>&1 | \
grep -E "^(Setting up|Unpacking)" | sed 's/^/    /'
systemctl enable --now ssh 2>/dev/null || true
ok "sshd present and enabled"

# ── Step 4: Ansible user ──────────────────────────────────────────────────────
section "ANSIBLE USER SETUP"

## Detect boot server by gateway IP -- same logic as late_command.sh/menu.ipxe.
## To add a new environment: one elif block, nothing else changes.
GW=$(ip route | awk '/default/ {print $3}')
if [ "$GW" = "172.16.124.2" ]; then
  BOOT_SERVER="http://172.16.124.1:8000"
else
  BOOT_SERVER="http://192.168.139.50"
fi
info "Boot server detected: ${BOOT_SERVER} (gateway: ${GW})"

ANSIBLE_USER="ansible"
ANSIBLE_PASSWORD="Password1!"
SSH_KEY_URL="${BOOT_SERVER}/ansible_sshkey.pub"

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

# ── Summary ───────────────────────────────────────────────────────────────────
echo
echo -e "${G}  +======================================================+${NC}"
echo -e "${G}  |${W}  ANSIBLE-BOOTSTRAP COMPLETE                           ${G}|${NC}"
echo -e "${G}  +======================================================+${NC}"
echo
CURRENT_IP=$(ip -4 addr show vmbr0 2>/dev/null | awk '/inet /{print $2}' | head -1)
CURRENT_IP="${CURRENT_IP%%/*}"
CURRENT_IP="${CURRENT_IP:-unknown}"
SSH_KEY_COUNT=$(wc -l < /home/${ANSIBLE_USER}/.ssh/authorized_keys 2>/dev/null || echo 0)

echo -e "  ${G}[+]${NC}  $(printf '%-18s' 'Current IP :') ${W}${CURRENT_IP} (DHCP, provisioning network)${NC}"
echo -e "  ${G}[+]${NC}  $(printf '%-18s' 'Ansible user :') ${W}${ANSIBLE_USER} -- ${SSH_KEY_COUNT} SSH key(s)${NC}"
echo
echo -e "${C}  +------------------------------------------------------+${NC}"
echo -e "${C}  |  NEXT STEP: Ansible finishes this node's setup       |${NC}"
echo -e "${C}  |                                                       |${NC}"
echo -e "${C}  |  This node still has its installer placeholder       |${NC}"
echo -e "${C}  |  hostname and a DHCP IP -- that's expected. From      |${NC}"
echo -e "${C}  |  the Ansible control node, run:                      |${NC}"
echo -e "${C}  |                                                       |${NC}"
echo -e "${C}  |    ansible-playbook -i \"${CURRENT_IP},\" \\               |${NC}"
echo -e "${C}  |      -i configs/inventory \\                            |${NC}"
echo -e "${C}  |      -e target=\"${CURRENT_IP}\" \\                        |${NC}"
echo -e "${C}  |      playbooks/proxmox/bootstrap-new-node.yml         |${NC}"
echo -e "${C}  |                                                       |${NC}"
echo -e "${C}  |  You'll be prompted for this node's real hostname     |${NC}"
echo -e "${C}  |  (from your build sheet, e.g. EXAPVEKGE001) -- it     |${NC}"
echo -e "${C}  |  sets the real hostname/network, then continues       |${NC}"
echo -e "${C}  |  straight into the full site.yml chain (packages,     |${NC}"
echo -e "${C}  |  access, systemd units, etc.) in this same run.       |${NC}"
echo -e "${C}  |  One reboot at the very end applies it all -- the     |${NC}"
echo -e "${C}  |  SSH session on this DHCP IP will not survive that.   |${NC}"
echo -e "${C}  |  Reconnect via the new hostname/IP once it is back up.|${NC}"
echo -e "${C}  +------------------------------------------------------+${NC}"
echo
info "No reboot is required by this script -- nothing here needs one."
