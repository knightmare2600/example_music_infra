#!/bin/sh
# =============================================================================
# Preseed late_command script
# Runs in the installer environment (busybox sh - NO bash, NO arrays, NO [[]])
# Uses in-target to run commands inside the installed system chroot
#
# Boot server detection mirrors bootstrap.ipxe and the preseed files:
#   Gateway 172.16.124.2 -> Fredericia (EXAPRVFRD001, MacBook/Fusion NAT)
#   Anything else        -> Edinburgh  (EXAPRVVRK001, 192.168.139.50)
#
# SSH key is fetched from whichever server is active.
# To add a new environment: one if/elif block, nothing else changes.
#
# Version history:
#   v1.0  Original version
#   v1.1  IP-agnostic boot server detect via gateway IP, same as bootstrap.ipxe
#         & preseed files. Removes hardcoded 192.168.128.113:8000 SSH Key URL.
#   v1.2  Add safety dance shell prompts, rework variables to be cleaner, stop
#         re-adding LVM2 kernel modules, use echo '' instead of "" per POSIX.
#   v1.3  Create the example-music folder and drop a copy of sites.csv in place
#   v1.4  Also download devices.csv to /etc/example-music/ alongside sites.csv
#   v1.5  Also download begyndelse.json (well-known service addresses -- provisioning/DNS/
#         Ansible/PBX/Rudder/WAC) to /etc/example-music/, so bindme.sh/ansibleme.sh/
#         firewallme.sh can jq it instead of hardcoding those IPs.
#   v1.6  Dropped sites.csv/devices.csv fetch -- ansible/playbooks/linux/tools.yml now
#         deploys both (and address_policy.json/ad_forest.json/ad_*.json) to every
#         Ansible-managed Linux host, so pre-staging them here was pure duplicate work by
#         the time any node is actually under management. bindme.sh/firewallme.sh/
#         rudderme.sh's own documented "expected, supported path" for the pre-Ansible
#         break-glass case is a manual wget anyway (see each script's own header) -- this
#         pre-staged copy was never their primary path, just a convenience fallback.
#         begyndelse.json is kept -- nothing else (no Ansible playbook) ever deploys it,
#         so it remains the one file only late_command.sh makes available before Ansible
#         exists on the box at all.
# =============================================================================
set -e

## Detect boot server by gateway IP
## Same logic as bootstrap.ipxe and partman/early_command in the seed files
GW=$(ip route | awk '/default/ {print $3}')
if [ "$GW" = "172.16.124.2" ]; then
  BOOT_SERVER="http://172.16.124.1:8000"
else
  BOOT_SERVER="http://192.168.139.50"
fi
echo " >>> Boot server detected: ${BOOT_SERVER} (gateway: ${GW})"

# Some constant variables
SSH_KEY_URL="${BOOT_SERVER}/ansible_sshkey.pub"
ZSH_SAFETY_URL="${BOOT_SERVER}/server-prompts.zsh"
BASH_SAFETY_URL="${BOOT_SERVER}/server-prompts.sh"
ANSIBLE_USER="ansible"
HOME_DIR="/home/${ANSIBLE_USER}"
BEGYNDELSE_JSON="${BOOT_SERVER}/proxmox/begyndelse.json"

## now created in the preseed file
echo ' >>> Creating ansible user...'
#in-target useradd --create-home --home-dir "${HOME_DIR}" --shell /bin/bash --comment "Ansible automation user" "${ANSIBLE_USER}"

echo ' >>> Adding ansible to sudo group...'
in-target usermod -aG sudo "${ANSIBLE_USER}"

echo ' >>> Installing openssh-server...'
in-target apt-get install -y openssh-server sudo net-tools bash-completion

echo ' >>> Creating /etc/example-music directory and fetching begyndelse.json...'
mkdir -p /target/etc/example-music
wget -O /target/etc/example-music/begyndelse.json "${BEGYNDELSE_JSON}"

echo ' >>> Creating .ssh directory...'
mkdir -p /target${HOME_DIR}/.ssh

echo ' >>> Fetching SSH public key...'
# wget is busybox wget - no --output-document flag, use -O
wget -O /target${HOME_DIR}/.ssh/authorized_keys "${SSH_KEY_URL}"

# Drop the safety dance zsh and bash scripts in
echo ' >>> Adding safety dance scripts...'
wget -O /target/usr/local/bin/server-prompts.zsh "${ZSH_SAFETY_URL}"
wget -O /target/usr/local/bin/server-prompts.sh "${BASH_SAFETY_URL}"
chmod 755 /target/usr/local/bin/server-prompts.zsh
chmod 755 /target/usr/local/bin/server-prompts.sh

echo ' >>> Configuring /etc/zsh/zshrc prompt integration...'
printf '%s\n' '' 'if [[ -f /usr/local/bin/server-prompts.zsh ]]; then' '  source /usr/local/bin/server-prompts.zsh' 'fi' >> /target/etc/zsh/zshrc

echo ' >>> Configuring /etc/bash.bashrc prompt integration...'
printf '%s\n' '' 'if [[ -f /usr/local/bin/server-prompts.sh ]]; then' '  source /usr/local/bin/server-prompts.sh' 'fi' >> /target/etc/bash.bashrc

echo ' >>> Setting up .vimrc for better hallway vision...'
printf 'set ruler\nset bg=dark\nsyntax on\n' > /target${HOME_DIR}/.vimrc

echo ' >>> Setting ownership and permissions...'
# Must use numeric UID/GID since we're outside the chroot here.
# Get the UID/GID that useradd just assigned inside the target.
ANSIBLE_UID=$(grep "^${ANSIBLE_USER}:" /target/etc/passwd | cut -d: -f3)
ANSIBLE_GID=$(grep "^${ANSIBLE_USER}:" /target/etc/passwd | cut -d: -f4)
if [ -z "$ANSIBLE_UID" ] || [ -z "$ANSIBLE_GID" ]; then
  echo "ERROR: Could not determine UID/GID for ${ANSIBLE_USER} - check /target/etc/passwd"
  exit 1
fi
chown -R "${ANSIBLE_UID}:${ANSIBLE_GID}" /target${HOME_DIR}
chmod 700 /target${HOME_DIR}/.ssh
chmod 600 /target${HOME_DIR}/.ssh/authorized_keys

echo ' >>> Configuring NOPASSWD sudo for ansible user...'
# Drop-in file is safer than editing /etc/sudoers directly.
# visudo -c validates syntax; if it fails we remove the bad file rather than
# leaving the system with a broken sudoers config.
cat > /target/etc/sudoers.d/ansible <<EOF
# Ansible automation - full passwordless sudo
ansible ALL=(ALL) NOPASSWD: ALL
EOF
chmod 0440 /target/etc/sudoers.d/ansible
in-target visudo -c -f /etc/sudoers.d/ansible || {
  echo "ERROR: sudoers syntax check failed - removing bad file"
  rm -f /target/etc/sudoers.d/ansible
  exit 1
}

## no locking ansible users just yet
#echo ' >>> Locking ansible password (SSH key only)...'
#in-target passwd -l "${ANSIBLE_USER}"

echo ' >>> Verifying...'
echo '--- /target/etc/passwd entry:'
grep "^${ANSIBLE_USER}:" /target/etc/passwd
echo '--- authorized_keys content:'
cat /target${HOME_DIR}/.ssh/authorized_keys
echo '--- /etc/example-music contents:'
ls -la /target/etc/example-music/
echo '--- Permissions:'
ls -la /target${HOME_DIR}/
ls -la /target${HOME_DIR}/.ssh/

echo ' >>> late_command.sh v1.6 complete.'
