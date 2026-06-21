## ============================================================
## ROCKY LINUX — install.ks
## ============================================================
## Save as: rockylinux/install.ks
##
## Version history:
##   v1.3 -- Remove deprecated 'install' directive (not valid in RHEL9 kickstart).
##            Remove unrecognised --createhome flag from user directive (home
##            directory is created by default in RHEL9; flag does not exist).
##   v1.2 -- Collapse two broken %pre blocks into one correct one.
##            Detect CPU arch via uname -m and write url= fragment
##            dynamically so arm64 and x86_64 both get the right
##            Rocky mirror path. Fix %include ordering (must come
##            after the %pre that writes the file).
##   v1.1 -- Add url repo directive so Anaconda knows where to pull
##            packages. Remove reliance on inst.stage2= (handled by
##            iPXE change) so the ramdisk is no longer flooded with a
##            700 MB install.img. Add %pre block + conditional
##            bootloader/partition layout to support both BIOS (MBR)
##            and UEFI (GPT + EFI partition) machines.
##   v1.0 -- Initial release
## ============================================================

#version=RHEL9

lang en_GB.UTF-8
keyboard uk
timezone Europe/London --isUtc

## DHCP but NO hostname (forces prompt)
network --bootproto=dhcp --device=link --activate

## Root account locked (forces you to care about access)
rootpw --lock

## Ansible user - NO password specified → installer WILL PROMPT
user --name=ansible --groups=wheel --shell=/bin/bash

## Security
firewall --enabled --service=ssh
selinux --enforcing

## Reboot after install
reboot

## ============================================================
## Pre-install detection
## Single %pre block — must all be in one so variables are set
## before anything is written.
##
## Writes two fragments read via %include below:
##   /tmp/ks-repo.cfg  -- url= line with correct arch mirror
##   /tmp/ks-disk.cfg  -- bootloader + partition layout
## ============================================================
%pre

## -- Arch detection -------------------------------------------------
## uname -m returns x86_64 or aarch64; Rocky mirror uses aarch64 path
ARCH=$(uname -m)
case "${ARCH}" in
  aarch64) ROCKY_ARCH="aarch64" ;;
  *)       ROCKY_ARCH="x86_64"  ;;
esac

ROCKY_URL="https://download.rockylinux.org/pub/rocky/9/BaseOS/${ROCKY_ARCH}/os/"

cat > /tmp/ks-repo.cfg <<EOF
url --url="${ROCKY_URL}"
EOF

## -- Firmware detection ---------------------------------------------
if [ -d /sys/firmware/efi ]; then
  FW="uefi"
else
  FW="bios"
fi

## -- Disk layout ----------------------------------------------------
if [ "${FW}" = "uefi" ]; then
  cat > /tmp/ks-disk.cfg <<'EOF'
bootloader --location=none --boot-drive=sda
clearpart --all --initlabel --disklabel=gpt

part /boot/efi --fstype="efi"  --size=512  --fsoptions="umask=0077,shortname=winnt"
part /boot     --fstype="xfs"  --size=1024
part pv.01     --size=1 --grow

volgroup vg0 pv.01

logvol /    --vgname=vg0 --name=root --fstype="xfs"  --size=8192 --grow
logvol swap --vgname=vg0 --name=swap --fstype="swap" --size=2048
EOF
else
  cat > /tmp/ks-disk.cfg <<'EOF'
bootloader --location=mbr --boot-drive=sda
clearpart --all --initlabel --disklabel=msdos

part /boot --fstype="xfs" --size=1024
part pv.01 --size=1 --grow

volgroup vg0 pv.01

logvol /    --vgname=vg0 --name=root --fstype="xfs"  --size=8192 --grow
logvol swap --vgname=vg0 --name=swap --fstype="swap" --size=2048
EOF
fi

%end

## ============================================================
## Includes — Anaconda reads these after %pre has run
## ============================================================
%include /tmp/ks-repo.cfg
%include /tmp/ks-disk.cfg

%packages
@^minimal-environment
openssh-server
sudo
vim-enhanced
net-tools
bash-completion
curl
%end

%post --log=/root/ks-post.log

ANSIBLE_USER="ansible"
SSH_KEY_URL="http://192.168.139.50/ansible_sshkey.pub"
HOME_DIR="/home/${ANSIBLE_USER}"

echo ">>> Post-install config"

## Enable SSH
systemctl enable sshd

## SSH key setup
mkdir -p ${HOME_DIR}/.ssh
curl -o ${HOME_DIR}/.ssh/authorized_keys ${SSH_KEY_URL}

chown -R ${ANSIBLE_USER}:${ANSIBLE_USER} ${HOME_DIR}
chmod 700 ${HOME_DIR}/.ssh
chmod 600 ${HOME_DIR}/.ssh/authorized_keys

## Vim config
cat > ${HOME_DIR}/.vimrc <<EOF
set ruler
set bg=dark
syntax on
EOF

chown ${ANSIBLE_USER}:${ANSIBLE_USER} ${HOME_DIR}/.vimrc

## Passwordless sudo
cat > /etc/sudoers.d/ansible <<EOF
ansible ALL=(ALL) NOPASSWD: ALL
EOF

chmod 0440 /etc/sudoers.d/ansible
visudo -c

echo ">>> Done"

%end
