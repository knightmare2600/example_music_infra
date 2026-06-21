#!/bin/sh
# =============================================================================
# Preseed late_command script
# Runs in the installer environment (busybox sh - NO bash, NO arrays, NO [[]])
# Uses in-target to run commands inside the installed system chroot
# =============================================================================

set -e

ANSIBLE_USER="ansible"
SSH_KEY_URL="http://192.168.139.50/ansible_sshkey.pub"
HOME_DIR="/home/${ANSIBLE_USER}"

## Fore LVM to be baked into the kernel
echo " >>> Forcing LVM2 into the kernel..."
in-target sh -c 'printf "dm_mod\ndm_snapshot\ndm_mirror\n" >> /etc/initramfs-tools/modules'
in-target update-initramfs -u -k all

## now created in the preseed file
echo " >>> Creating ansible user..."
#in-target useradd --create-home --home-dir "${HOME_DIR}" --shell /bin/bash --comment "Ansible automation user" "${ANSIBLE_USER}"

echo " >>> Adding ansible to sudo group..."
in-target usermod -aG sudo "${ANSIBLE_USER}"

echo " >>> Installing openssh-server..."
in-target apt-get install -y openssh-server sudo net-tools bash-completion

echo " >>> Creating .ssh directory..."
# in-target chroots to /target, so we create the dir from outside
# to avoid any dependency on the target's tools for mkdir
mkdir -p /target${HOME_DIR}/.ssh

echo " >>> Fetching SSH public key..."
# wget is busybox wget - no --output-document flag, use -O
wget -O /target${HOME_DIR}/.ssh/authorized_keys "${SSH_KEY_URL}"

echo " >>> Setting up .vimrc for better hallway vision..."
printf 'set ruler\nset bg=dark\nsyntax on\n' > /target${HOME_DIR}/.vimrc

echo " >>> Setting ownership and permissions..."
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

echo ">>> Configuring NOPASSWD sudo for ansible user..."
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


## no locking nasible users just yet
#echo " >>> Locking ansible password (SSH key only)..."
#in-target passwd -l "${ANSIBLE_USER}"

echo " >>> Verifying..."
echo "--- /target/etc/passwd entry:"
grep "^${ANSIBLE_USER}:" /target/etc/passwd

echo "--- authorized_keys content:"
cat /target${HOME_DIR}/.ssh/authorized_keys

echo "--- Permissions:"
ls -la /target${HOME_DIR}/
ls -la /target${HOME_DIR}/.ssh/
echo "--- Directory Tree:"
/target/usr/bin/tree -a /target/home/ansible

echo " >>> latecommand.sh complete."
