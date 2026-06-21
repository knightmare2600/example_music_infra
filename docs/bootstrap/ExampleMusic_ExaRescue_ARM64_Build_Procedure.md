# Example Music Limited — ExaRescue arm64 Live Image Build Procedure

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-09 | Initial document |
| 2026-03-10 | Replaced XFCE with Fluxbox; replaced mousepad with Featherpad; removed Firefox |

---

## 1. Overview

ExaRescue is a custom Debian-based arm64 live image providing a minimal Fluxbox desktop environment with GParted, network tools, and a curated shell environment. It is built using Debian's official `live-build` toolchain and served over PXE from `EXAPROVCLD001` (`192.168.139.50`).

The image is intended as the arm64 counterpart to GParted Live (which is x86_64 only). It provides the same core functionality — graphical disk management, network diagnostics, and a capable shell environment — in a bootable image suitable for ARM-based infrastructure including Apple Silicon Macs running VMware Fusion and Proxmox arm64 VMs.

Fluxbox is used in preference to a full desktop environment such as XFCE in order to minimise image size. Fluxbox is a bare window manager with no panel ecosystem, compositor, or settings infrastructure — it simply manages windows. The resulting `filesystem.squashfs` is significantly smaller (~700–900MB vs ~1.5GB for XFCE), reducing PXE boot time over HTTP.

> **NB:** This build procedure is intended to be run on one of two platforms:
>
> - **A Proxmox arm64 VM** — a dedicated Debian Trixie VM on a Proxmox node with an arm64 host (e.g. Ampere, Graviton, or Apple Silicon Proxmox node). This is the preferred production build environment.
> - **A MacBook M4 running VMware Fusion** — a Debian Trixie arm64 guest VM running natively under VMware Fusion on Apple Silicon. This is the likely day-to-day development and rebuild environment.
>
> In both cases the guest must be **Debian Trixie arm64** running **natively** (not emulated). Cross-compilation via QEMU is explicitly **not** covered by this procedure. The build machine does not need to be on the production network — it simply needs internet access to pull Debian packages.

---

## 2. Scope

### 2.1 In Scope

- Installing and configuring `live-build` on a Debian Trixie arm64 build machine
- Configuring the package list, custom dotfiles, and hooks
- Building the ISO
- Extracting PXE boot files (`vmlinuz`, `initrd.img`, `filesystem.squashfs`) from the ISO
- Deploying PXE files to `EXAPROVCLD001`
- Updating `bootstrap.ipxe` to serve the arm64 GParted menu entry

### 2.2 Out of Scope

- Cross-compilation or QEMU-based builds
- x86_64 GParted Live (served separately under `gparted/x86_64/`)
- Customisation of the Fluxbox desktop beyond what is documented here
- Persistent live image configuration (image is stateless/live only)

---

## 3. Infrastructure Reference

### 3.1 Servers / Devices Involved

| Hostname | IP | Site | Role |
|----------|----|------|------|
| `EXAPROVCLD001` | `192.168.139.50` | CLD | Provisioning server — serves PXE files over HTTP |
| Build VM (Proxmox) | DHCP / as assigned | Any | Debian Trixie arm64 build machine — temporary |
| MacBook M4 (VMware Fusion guest) | DHCP / as assigned | FAL or local | Debian Trixie arm64 build machine — development |

### 3.2 Directory Layout on Provisioning Server

```bash
/srv/www/
└── gparted/
    ├── x86_64/
    │   ├── vmlinuz
    │   ├── initrd.img
    │   └── filesystem.squashfs
    └── arm64/
        ├── vmlinuz
        ├── initrd.img
        └── filesystem.squashfs
```

---

## 4. Prerequisites

1. Debian Trixie arm64 VM is provisioned and running (native arm64, not emulated)
2. VM has internet access (to pull packages from Debian mirrors)
3. VM has at least **20 GB** free disk space for the build
4. VM has at least **4 GB** RAM (8 GB recommended)
5. SSH access to `EXAPROVCLD001` from the build machine, or a method to transfer files (SCP/SFTP)
6. `bootstrap.ipxe` on `EXAPROVCLD001` is the current version with `${arch}` support

### 4.1 VMware Fusion — Guest Setup Notes

When creating the Debian Trixie arm64 VM in VMware Fusion on an M4 MacBook:

- Select **Debian 12.x ARM 64-bit** as the guest OS type (Debian Trixie will work fine with this profile)
- Allocate at least **4 vCPU**, **8 GB RAM**, **25 GB disk**
- Use the Debian Trixie arm64 netboot or full ISO
- Install as a standard minimal Debian system — no desktop environment needed on the build machine itself
- VMware Tools (open-vm-tools) will be installed as part of the ExaRescue package list, not on the build machine

### 4.2 Proxmox arm64 VM — Guest Setup Notes

- Create a standard Debian Trixie arm64 VM on the Proxmox node
- Minimum **4 vCPU**, **8 GB RAM**, **25 GB disk**
- QEMU Guest Agent (`qemu-guest-agent`) will be installed as part of the ExaRescue package list, not on the build machine
- Use VirtIO SCSI disk and VirtIO network adapter

---

## 5. Procedure

### 5.1 Prepare the Build Machine

Update the system and install `live-build`:

```bash
apt update && apt upgrade -y
apt install -y live-build git curl
```

Verify `live-build` is installed:

```bash
lb --version
```

---

### 5.2 Create the Build Directory

```bash
mkdir -p ~/exarescue && cd ~/exarescue
```

All subsequent commands in this procedure are run from `~/exarescue` unless stated otherwise.

---

### 5.3 Configure the Build

Run `lb config` to initialise the build configuration:

```bash
lb config --architectures arm64 --distribution trixie --image-name exarescue-arm64 --debian-installer none --archive-areas "main contrib non-free non-free-firmware" \ --desktop none --bootloaders grub-efi --uefi-secure-boot disable --memtest none --win32-loader false --debootstrap-options "--variant=minbase"
```

This creates a `config/` directory tree. Do not edit files inside `config/` directly except as documented in the sections below — all customisation is done by adding files to the correct subdirectories.

> ℹ
> `--debian-installer none` omits the Debian installer entirely — the image is live-only.
> `--desktop none` tells `live-build` not to pull in any desktop metapackage — Fluxbox and Xorg are added explicitly in the package list instead, giving full control over what is installed.
> `--bootloaders grub-efi` is correct for arm64 UEFI boot. 
> `--debootstrap-options "--variant=minbase"` starts the bootstrap from a truly minimal base rather than the standard Debian base install, saving ~50–100MB before any other packages are added.

---

### 5.4 Package List

Create the package list file. This is the complete list of packages that will be installed into the live image beyond the base XFCE desktop:

```bash
cat > config/package-lists/exa.list.chroot << 'EOF'
# Window manager and X11
fluxbox
xorg
xterm
xinit
x11-utils
x11-xserver-utils

# Disk management
gparted
parted
gdisk
testdisk

# Filesystem support — ZFS, LVM, NTFS, btrfs
zfsutils-linux
lvm2
ntfs-3g
btrfs-progs
dosfstools
e2fsprogs
xfsprogs

# Terminal
xfce4-terminal
tmux

# Shell
zsh
zsh-syntax-highlighting
zsh-autosuggestions

# Text editors
vim
featherpad

# Browser / web
w3m

# Network tools
curl
wget
nmap
netcat-openbsd
net-tools
iputils-ping
traceroute
dnsutils
openssh-client

# Developer tools
git

# System tools
htop
lsof
rsync
pciutils
usbutils

# Locale support
locales

# Virtualisation guest agents
qemu-guest-agent
open-vm-tools
open-vm-tools-desktop
EOF
```

> ℹ Filesystem support packages are explicit to ensure ZFS (`zfsutils-linux`), LVM (`lvm2`), NTFS (`ntfs-3g`), btrfs (`btrfs-progs`), FAT (`dosfstools`), ext2/3/4 (`e2fsprogs`) and XFS (`xfsprogs`) are all available. GParted will use these automatically when it detects the relevant filesystem type. `testdisk` and `gdisk` are included as useful companions for partition recovery and GPT manipulation.

> ℹ `pciutils` and `usbutils` (`lspci`, `lsusb`) are useful in a rescue context for hardware identification.

> ℹ `featherpad` is a lightweight Qt5 text editor — it pulls in Qt5 base libraries but these are significantly smaller than a full XFCE or GNOME dependency tree. Actively maintained and in the Trixie repos.

> ℹ `open-vm-tools-desktop` is included alongside `open-vm-tools` to enable clipboard sharing and display auto-resize when running under VMware Fusion. Both are harmless on non-VMware hypervisors. `qemu-guest-agent` is similarly harmless on non-QEMU hosts.

> ℹ `zsh-autosuggestions` is included alongside `zsh-syntax-highlighting` — it is the natural companion package and adds fish-style command history suggestions.

---

### 5.5 Custom Dotfiles and Shell Configuration

`live-build` supports injecting files directly into the live filesystem via `config/includes.chroot/`. Files placed here are copied verbatim into the root of the live filesystem at build time.

The default user in a Debian live image is `user` with home directory `/home/user`. The root user home is `/root`. We populate both.

#### 5.5.1 Create the directory structure

```bash
mkdir -p config/includes.chroot/home/user
mkdir -p config/includes.chroot/root
```

#### 5.5.2 .vimrc

Create a `.vimrc` that will be used by both `user` and `root`. Write it once, then copy:

```bash
cat > /tmp/vimrc << 'EOF'
" ============================================================
" ExaRescue — vimrc
" Example Music Limited
" ============================================================

set nocompatible
filetype off

" --- General ---
set number
set relativenumber
set cursorline
set showcmd
set showmatch
set wildmenu
set lazyredraw

" --- Indentation ---
set tabstop=4
set shiftwidth=4
set expandtab
set smartindent
set autoindent

" --- Search ---
set incsearch
set hlsearch
set ignorecase
set smartcase

" --- Appearance ---
set background=dark
set laststatus=2
set ruler
set scrolloff=8
set sidescrolloff=8

" --- Files ---
set nobackup
set noswapfile
set encoding=utf-8
set fileencoding=utf-8

" --- Behaviour ---
set backspace=indent,eol,start
set mouse=a
set clipboard=unnamedplus
set hidden

" --- Syntax ---
syntax enable
filetype plugin indent on

" --- Key mappings ---
let mapleader = ","

" Clear search highlight
nnoremap <leader><space> :nohlsearch<CR>

" Quick save
nnoremap <leader>w :w<CR>

" Split navigation
nnoremap <C-h> <C-w>h
nnoremap <C-j> <C-w>j
nnoremap <C-k> <C-w>k
nnoremap <C-l> <C-w>l

" Buffer navigation
nnoremap <leader>n :bnext<CR>
nnoremap <leader>p :bprevious<CR>
EOF

cp /tmp/vimrc config/includes.chroot/home/user/.vimrc
cp /tmp/vimrc config/includes.chroot/root/.vimrc
```

#### 5.5.3 .vim directory

Create a minimal `.vim` directory structure. The colour scheme and autoload directories are created so vim does not complain about missing paths:

```bash
mkdir -p config/includes.chroot/home/user/.vim/{colors,autoload,backup,swap,undo}
mkdir -p config/includes.chroot/root/.vim/{colors,autoload,backup,swap,undo}
```

#### 5.5.4 .tmux.conf

```bash
cat > /tmp/tmux.conf << 'EOF'
# ============================================================
# ExaRescue — tmux.conf
# Example Music Limited
# ============================================================

# --- Prefix ---
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# --- General ---
set -g default-terminal "screen-256color"
set -g history-limit 10000
set -g base-index 1
setw -g pane-base-index 1
set -g renumber-windows on
set -sg escape-time 0

# --- Mouse ---
set -g mouse on

# --- Status bar ---
set -g status-position bottom
set -g status-bg colour234
set -g status-fg colour137
set -g status-left ''
set -g status-right '#[fg=colour233,bg=colour241,bold] %d/%m #[fg=colour233,bg=colour245,bold] %H:%M:%S '
set -g status-right-length 50
set -g status-left-length 20

# --- Window status ---
setw -g window-status-current-format ' #I#[fg=colour250]:#[fg=colour255]#W#[fg=colour50]#F '
setw -g window-status-format ' #I#[fg=colour237]:#[fg=colour250]#W#[fg=colour244]#F '

# --- Pane splitting ---
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"
unbind '"'
unbind %

# --- Pane navigation (vim-style) ---
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# --- Pane resizing ---
bind -r H resize-pane -L 5
bind -r J resize-pane -D 5
bind -r K resize-pane -U 5
bind -r L resize-pane -R 5

# --- Reload config ---
bind r source-file ~/.tmux.conf \; display "Config reloaded"

# --- Copy mode (vi) ---
setw -g mode-keys vi
bind -T copy-mode-vi v send-keys -X begin-selection
bind -T copy-mode-vi y send-keys -X copy-selection-and-cancel
EOF

cp /tmp/tmux.conf config/includes.chroot/home/user/.tmux.conf
cp /tmp/tmux.conf config/includes.chroot/root/.tmux.conf
```

#### 5.5.5 .zshrc

The `.zshrc` is the main customisation point for the shell. A sensible default is provided, but it is designed to be overridden — see **section 5.5.6** for how to substitute your own.

```bash
cat > /tmp/zshrc << 'EOF'
# ============================================================
# ExaRescue — zshrc
# Example Music Limited
# ============================================================

# --- History ---
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt SHARE_HISTORY
setopt APPEND_HISTORY

# --- Options ---
setopt AUTO_CD
setopt CORRECT
setopt COMPLETE_IN_WORD
setopt NO_BEEP

# --- Completion ---
autoload -Uz compinit && compinit
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'

# --- Prompt ---
autoload -Uz vcs_info
precmd() { vcs_info }
zstyle ':vcs_info:git:*' formats ' (%b)'
setopt PROMPT_SUBST
PROMPT='%F{cyan}%n@%m%f %F{yellow}%~%f%F{green}${vcs_info_msg_0_}%f %# '

# --- Syntax highlighting ---
# Debian package installs to /usr/share/zsh-syntax-highlighting/
if [[ -f /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]]; then
  source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi

# --- Autosuggestions ---
if [[ -f /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]]; then
  source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
fi

# --- Aliases ---
alias ll='ls -lah --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'
alias grep='grep --color=auto'
alias df='df -h'
alias du='du -h'
alias free='free -h'
alias vi='vim'
alias ..='cd ..'
alias ...='cd ../..'

# --- Network aliases ---
alias myip='curl -s ifconfig.me'
alias ports='ss -tulnp'
alias nmap-quick='nmap -T4 -F'
alias nmap-full='nmap -T4 -A -v'

# --- Disk aliases ---
alias lsblk='lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL,UUID'
alias parted='parted -l'

# --- Editor ---
export EDITOR=vim
export VISUAL=vim

# --- Path ---
export PATH="$HOME/.local/bin:$PATH"
EOF

cp /tmp/zshrc config/includes.chroot/home/user/.zshrc
cp /tmp/zshrc config/includes.chroot/root/.zshrc
```

#### 5.5.6 Substituting a Custom .zshrc

If you want to use your own `.zshrc` instead of (or in addition to) the default above, simply overwrite the file before running `lb build`:

```bash
# Replace user zshrc with your own
cp /path/to/your/.zshrc config/includes.chroot/home/user/.zshrc

# Replace root zshrc with your own
cp /path/to/your/.zshrc config/includes.chroot/root/.zshrc
```

You can also maintain separate `.zshrc` files for `user` and `root` if preferred — the two paths are independent.

> ℹ The `config/includes.chroot/` tree is not cleaned by `lb clean --stage` — only by `lb clean --all`. Your custom dotfiles will survive a partial clean and rebuild.

---

### 5.6 Fluxbox Autostart Configuration

Fluxbox reads `~/.fluxbox/startup` on launch. We configure it to autostart GParted and `xfce4-terminal` automatically so the image is immediately useful on boot without requiring the user to navigate menus.

```bash
mkdir -p config/includes.chroot/home/user/.fluxbox
mkdir -p config/includes.chroot/root/.fluxbox

cat > /tmp/fluxbox-startup << 'EOF'
#!/bin/bash
# ============================================================
# ExaRescue — Fluxbox startup
# Example Music Limited
# ============================================================

# Set wallpaper colour (solid dark grey — no wallpaper package needed)
xsetroot -solid "#2b2b2b" &

# Launch terminal
xfce4-terminal &

# Launch GParted
gparted &

# Start Fluxbox
exec fluxbox
EOF

cp /tmp/fluxbox-startup config/includes.chroot/home/user/.fluxbox/startup
cp /tmp/fluxbox-startup config/includes.chroot/root/.fluxbox/startup
chmod +x config/includes.chroot/home/user/.fluxbox/startup
chmod +x config/includes.chroot/root/.fluxbox/startup
```

We also need a hook to configure the live session to start X automatically on login:

```bash
mkdir -p config/hooks/live

cat > config/hooks/live/0050-configure-xinitrc.hook.chroot << 'EOF'
#!/bin/bash
set -e

# Write .xinitrc for user
cat > /home/user/.xinitrc << 'XINITRC'
exec /home/user/.fluxbox/startup
XINITRC

# Write .xinitrc for root
cat > /root/.xinitrc << 'XINITRC'
exec /root/.fluxbox/startup
XINITRC

# Configure autologin and startx for the live user
# live-build handles autologin via live-config; we just ensure startx runs
cat >> /home/user/.bash_profile << 'PROFILE'
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  startx
fi
PROFILE

cat >> /home/user/.zprofile << 'PROFILE'
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
  startx
fi
PROFILE

chmod +x /home/user/.xinitrc
chmod +x /root/.xinitrc
EOF

chmod +x config/hooks/live/0050-configure-xinitrc.hook.chroot
```

> ℹ The Debian live system (`live-config`) handles autologin to tty1 for the `user` account automatically. The `.zprofile` and `.bash_profile` additions above ensure `startx` is called as soon as that autologin occurs, launching Fluxbox.

---

### 5.7 Set zsh as the Default Shell — Hook

`live-build` hooks allow you to run arbitrary commands inside the chroot during the build. We use a hook to set `zsh` as the default shell for both `user` and `root`:

```bash
mkdir -p config/hooks/live

cat > config/hooks/live/0100-set-zsh-default-shell.hook.chroot << 'EOF'
#!/bin/bash
set -e
chsh -s /usr/bin/zsh user
chsh -s /usr/bin/zsh root
EOF

chmod +x config/hooks/live/0100-set-zsh-default-shell.hook.chroot
```

> ℹ Hooks in `config/hooks/live/` run inside the chroot after package installation. The `0100-` prefix controls execution order — lower numbers run first.

---

### 5.8 Fix Permissions — Hook

File ownership can get lost when copying dotfiles via `config/includes.chroot/`. A second hook corrects ownership:

```bash
cat > config/hooks/live/0200-fix-home-permissions.hook.chroot << 'EOF'
#!/bin/bash
set -e
chown -R user:user /home/user
chmod 700 /home/user
find /home/user -name ".*" -maxdepth 1 -exec chmod 600 {} \;
chmod 700 /home/user/.vim 2>/dev/null || true
chmod 700 /home/user/.fluxbox 2>/dev/null || true
chmod +x /home/user/.fluxbox/startup 2>/dev/null || true
chmod +x /home/user/.xinitrc 2>/dev/null || true
EOF

chmod +x config/hooks/live/0200-fix-home-permissions.hook.chroot
```

---

### 5.9 Image Cleanup — Hook

This hook runs last (prefix `0900`) and handles all size reduction in one place: apt cache, locale pruning, doc/man removal, and selective firmware stripping. It is the most impactful single step for reducing the final squashfs size.

```bash
cat > config/hooks/live/0900-cleanup.hook.chroot << 'EOF'
#!/bin/bash
set -e

echo "=== ExaRescue cleanup hook ==="

# ========================================================================================================================
# 1. APT CACHE Remove downloaded .deb files — not needed in the live image
# ========================================================================================================================
echo "--- Cleaning apt cache ---"
apt-get clean
apt-get autoremove --purge -y
rm -rf /var/lib/apt/lists/*

# ========================================================================================================================
# 2. LOCALE PURGE
# Keep: en_GB, en_US, da (Danish), de (German), it (Italian) Remove everything else including locale-specific LC_* dirs
# ========================================================================================================================
echo "--- Purging unwanted locales ---"
apt-get install -y localepurge

cat > /etc/locale.nopurge << 'LOCALES'
MANDELETE
DONTBOTHERNEWLOCALE
SHOWFREEDSPACE
da
da_DK
da_DK.UTF-8
de
de_DE
de_DE.UTF-8
de_AT
de_AT.UTF-8
de_CH
de_CH.UTF-8
en
en_GB
en_GB.UTF-8
en_US
en_US.UTF-8
it
it_IT
it_IT.UTF-8
LOCALES

localepurge

# ========================================================================================================================
# 3. DOCUMENTATION
# Remove /usr/share/doc and /usr/share/info — not useful in a rescue environment. Preserve /usr/share/man — kept as it has
# legitimate rescue utility (man gparted etc.)
# ========================================================================================================================
echo "--- Removing documentation ---"
rm -rf /usr/share/doc/*
rm -rf /usr/share/info/*
rm -rf /usr/share/linda 2>/dev/null || true
rm -rf /usr/share/lintian 2>/dev/null || true
rm -rf /usr/share/common-licenses 2>/dev/null || true

# ========================================================================================================================
# 4. FIRMWARE STRIPPING
# Remove firmware blobs for hardware irrelevant in VM/server environments. Explicitly PRESERVE anything storage-related.
#
# PRESERVED (do not remove):
#   - firmware-linux (generic, may be needed)
#   - Any scsi/sas/nvme firmware
#   - ZFS-related modules (in kernel, not firmware)
#
# REMOVED:
#   - WiFi firmware (Broadcom, Realtek, Atheros, Intel WiFi)
#   - Bluetooth firmware
#   - GPU firmware (AMD, NVIDIA, Intel graphics)
#   - DVB/TV tuner firmware
#   - Sound card firmware
# ========================================================================================================================
echo "--- Stripping irrelevant firmware ---"

# WiFi
rm -rf /lib/firmware/brcm          2>/dev/null || true   # Broadcom WiFi
rm -rf /lib/firmware/rtlwifi       2>/dev/null || true   # Realtek WiFi
rm -rf /lib/firmware/ath*          2>/dev/null || true   # Atheros WiFi
rm -rf /lib/firmware/iwlwifi*      2>/dev/null || true   # Intel WiFi
rm -rf /lib/firmware/mwifiex       2>/dev/null || true   # Marvell WiFi
rm -rf /lib/firmware/libertas      2>/dev/null || true   # Marvell libertas
rm -rf /lib/firmware/wil6210*      2>/dev/null || true   # Wilocity 60GHz

# Bluetooth
rm -rf /lib/firmware/qca           2>/dev/null || true   # Qualcomm BT
rm -rf /lib/firmware/intel/ibt*    2>/dev/null || true   # Intel Bluetooth

# GPU / graphics
rm -rf /lib/firmware/amdgpu        2>/dev/null || true   # AMD GPU
rm -rf /lib/firmware/radeon        2>/dev/null || true   # AMD Radeon legacy
rm -rf /lib/firmware/nvidia        2>/dev/null || true   # NVIDIA
rm -rf /lib/firmware/i915          2>/dev/null || true   # Intel graphics

# DVB / media
rm -rf /lib/firmware/dvb*          2>/dev/null || true
rm -rf /lib/firmware/v4l*          2>/dev/null || true

# Sound
rm -rf /lib/firmware/cirrus        2>/dev/null || true
rm -rf /lib/firmware/cs46xx*       2>/dev/null || true

# ========================================================================================================================
# 5. MISC CLEANUP
# ========================================================================================================================
echo "--- Miscellaneous cleanup ---"

# Python cache files
find / -name "*.pyc" -delete 2>/dev/null || true
find / -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Temp files
rm -rf /tmp/* /var/tmp/* 2>/dev/null || true

# Bash history
rm -f /root/.bash_history /home/user/.bash_history 2>/dev/null || true

echo "=== Cleanup complete ==="
EOF

chmod +x config/hooks/live/0900-cleanup.hook.chroot
```

> ⚠ The firmware removal list uses `2>/dev/null || true` throughout — if a firmware directory does not exist (which will often be the case since not all firmware packages are installed) the hook will not fail. It is safe to add further paths to this list.

> ℹ `/usr/share/man` is deliberately **not** removed. In a rescue context `man parted`, `man zfs`, `man lvm` etc. have genuine utility and the space cost is modest (~30MB).

> ℹ The locale configuration keeps full regional variants for German (`de_DE`, `de_AT`, `de_CH`) since Example Music has sites in both Germany and Austria. Italian is kept for the Milan (`MIL`) site.

---

### 5.10 Build the Image

With configuration complete, run the build:

```bash
lb build 2>&1 | tee build.log
```

This will:

1. Bootstrap a minimal Debian Trixie arm64 chroot
2. Install all packages from the package list
3. Copy in all files from `config/includes.chroot/`
4. Run all hooks
5. Bundle the chroot into a `filesystem.squashfs`
6. Build a GRUB EFI bootloader
7. Assemble the final ISO

The build takes approximately **20–40 minutes** on a modern machine, depending on download speed and CPU. The majority of the time is downloading packages.

On completion, the following files will be present in `~/exarescue/`:

```
exarescue-arm64.iso          ← complete bootable ISO (~1.5–2GB)
exarescue-arm64.contents     ← package manifest
build.log                    ← full build log
```

> ⚠ If the build fails, check `build.log` for the error. Common causes are network timeouts (re-run `lb build` — it will resume), and hook permission errors (ensure hook files are `chmod +x`).

> ℹ To rebuild from scratch after a failure or after changing configuration: `lb clean --all && lb build 2>&1 | tee build.log`. To rebuild after only changing dotfiles or hooks (without re-downloading packages): `lb clean --stage && lb build 2>&1 | tee build.log`.

---

### 5.11 Extract PXE Boot Files from the ISO

The ISO contains a `live/` directory with the three files needed for PXE booting. Mount the ISO and extract them:

```bash
mkdir -p /mnt/exarescue
mount -o loop exarescue-arm64.iso /mnt/exarescue

ls /mnt/exarescue/live/
# Expected output: filesystem.squashfs  initrd.img  vmlinuz  (and possibly others)
```

Copy the three PXE files:

```bash
mkdir -p /tmp/exarescue-pxe
cp /mnt/exarescue/live/vmlinuz           /tmp/exarescue-pxe/vmlinuz
cp /mnt/exarescue/live/initrd.img        /tmp/exarescue-pxe/initrd.img
cp /mnt/exarescue/live/filesystem.squashfs /tmp/exarescue-pxe/filesystem.squashfs

umount /mnt/exarescue
```

**What these files are:**

| File | Description |
|------|-------------|
| `vmlinuz` | The Linux kernel — loaded by iPXE and handed to the boot environment |
| `initrd.img` | Initial RAM disk — contains the early userspace needed to mount the squashfs |
| `filesystem.squashfs` | The compressed root filesystem — the entire live OS, fetched over HTTP by the live boot process and mounted read-only in RAM |

> ℹ The `filesystem.squashfs` is typically the largest file (~1–1.5 GB). It is fetched by the booting client over HTTP from the provisioning server — ensure the provisioning server has sufficient bandwidth and that HTTP serving is working before testing PXE boot.

---

### 5.12 Deploy to Provisioning Server

Copy the three PXE files to `EXAPROVCLD001`:

```bash
scp /tmp/exarescue-pxe/vmlinuz           ansible@192.168.139.50:/srv/www/gparted/arm64/vmlinuz
scp /tmp/exarescue-pxe/initrd.img        ansible@192.168.139.50:/srv/www/gparted/arm64/initrd.img
scp /tmp/exarescue-pxe/filesystem.squashfs ansible@192.168.139.50:/srv/www/gparted/arm64/filesystem.squashfs
```

> ⚠ The `filesystem.squashfs` transfer will take several minutes depending on network speed. Do not interrupt it.

Verify the files are accessible over HTTP from another machine on the provisioning network:

```bash
curl -I http://192.168.139.50/gparted/arm64/vmlinuz
curl -I http://192.168.139.50/gparted/arm64/initrd.img
curl -I http://192.168.139.50/gparted/arm64/filesystem.squashfs
```

All three should return `HTTP/1.1 200 OK`.

---

### 5.13 iPXE Boot Entry

The `bootstrap.ipxe` GParted entry already uses `${arch}` for path selection. The arm64 entry resolves to:

```ipxe
:gparted
kernel ${boot-url}/gparted/${arch}/vmlinuz boot=live components fetch=${boot-url}/gparted/${arch}/filesystem.squashfs
initrd ${boot-url}/gparted/${arch}/initrd.img
boot
```

No changes to `bootstrap.ipxe` are required once the files are deployed to the correct path.

---

## 6. Verification

### 6.1 Verify Files on Provisioning Server

```bash
ls -lh /srv/www/gparted/arm64/
```

Expected:

```
vmlinuz          ~10–15 MB
initrd.img       ~80–150 MB
filesystem.squashfs  ~500–800 MB
```

### 6.2 Test PXE Boot

1. Boot an arm64 VM (Proxmox or VMware Fusion) from the network
2. At the iPXE menu, select **GParted Live**
3. The kernel and initrd will load immediately; `filesystem.squashfs` will fetch over HTTP — this takes 1–2 minutes depending on network speed
4. Fluxbox desktop should appear with GParted and a terminal already open

### 6.3 Verify Shell Environment

Once booted, open a terminal and verify:

```bash
echo $SHELL          # should return /usr/bin/zsh
vim --version        # should return 9.x
tmux -V              # should return tmux 3.x
gparted --version    # should return gparted 1.x
```

---

## 7. Rebuilding

### 7.1 After Changing Packages Only

```bash
cd ~/exarescue
lb clean --all
lb build 2>&1 | tee build.log
```

### 7.2 After Changing Dotfiles or Hooks Only (Fast Rebuild)

A stage clean skips re-downloading packages and only re-runs the chroot customisation and image assembly phases:

```bash
cd ~/exarescue
lb clean --stage
lb build 2>&1 | tee build.log
```

> ℹ A stage clean rebuild typically takes 5–10 minutes rather than 20–40.

### 7.3 After Changing the .zshrc Only (Fastest)

If you only changed dotfiles in `config/includes.chroot/`:

```bash
cd ~/exarescue
lb clean --stage
lb build 2>&1 | tee build.log
```

Same as above — a stage clean is sufficient and fastest for dotfile-only changes.

---

## 8. Troubleshooting

### 8.1 Build Fails with Network Timeout

Re-run `lb build` — `live-build` caches downloaded packages in `cache/` and will resume from where it left off. Intermittent network failures during package download are the most common cause of build failures.

### 8.2 Hook Fails — Permission Denied

Ensure all hook files are executable:

```bash
chmod +x config/hooks/live/*.hook.chroot
```

Then re-run `lb clean --stage && lb build`.

### 8.3 filesystem.squashfs Not Found at Boot

The live boot system fetches `filesystem.squashfs` over HTTP using the URL passed in the `fetch=` kernel parameter. Verify:

- The file exists on `EXAPROVCLD001` at the correct path
- The HTTP server is running and serving the file (`curl -I` test from section 6.1)
- The booting client can reach `192.168.139.50` (check DHCP/routing)

### 8.4 zsh Not Set as Default Shell

If the shell hook did not run, set it manually inside the live image via a terminal:

```bash
sudo chsh -s /usr/bin/zsh user
```

Then investigate `build.log` for the hook failure.

### 8.5 VMware Fusion — Display Not Auto-Resizing

Ensure `open-vm-tools-desktop` is installed in the image. Verify:

```bash
dpkg -l | grep open-vm-tools-desktop
```

If missing, add it to `config/package-lists/exa.list.chroot` and rebuild.

### 8.6 GParted Shows No Disks

The booting VM must have at least one disk attached. In VMware Fusion, ensure a virtual disk is present. In Proxmox, ensure at least one disk is attached to the VM even if it is empty — GParted requires a block device to operate.

### 8.7 Locale Errors at Boot — Missing Locale

If the live image boots with locale warnings such as `locale: Cannot set LC_ALL`, it means a locale that is referenced somewhere in the system was purged. Add the missing locale code to `/etc/locale.nopurge` in the cleanup hook and rebuild with `lb clean --stage`.

The locales kept by default are: `en_GB.UTF-8`, `en_US.UTF-8`, `da_DK.UTF-8`, `de_DE.UTF-8`, `de_AT.UTF-8`, `de_CH.UTF-8`, `it_IT.UTF-8`.

### 8.8 ZFS Volumes Not Visible in GParted

ZFS pools are not standard partitions and GParted may not display them as mountable volumes — this is expected. Use the terminal and `zpool import` / `zfs list` to work with ZFS pools directly. GParted will correctly show the underlying block devices (disks/partitions).

---

## 9. Checklist

| # | Task | Done |
|---|------|------|
| 1 | Build machine is Debian Trixie arm64 (native, not emulated) | ☐ |
| 2 | Build machine has 20 GB free disk and 4 GB RAM | ☐ |
| 3 | `live-build` installed and `lb --version` returns successfully | ☐ |
| 4 | `lb config` run successfully with `--debootstrap-options "--variant=minbase"` | ☐ |
| 5 | Package list created at `config/package-lists/exa.list.chroot` | ☐ |
| 6 | `.vimrc` created in both `home/user` and `root` includes paths | ☐ |
| 7 | `.vim/` directory structure created in both includes paths | ☐ |
| 8 | `.tmux.conf` created in both includes paths | ☐ |
| 9 | `.zshrc` created (or custom `.zshrc` substituted) in both includes paths | ☐ |
| 10 | Fluxbox startup script created in both includes paths and `chmod +x` | ☐ |
| 11 | xinitrc / zprofile hook (`0050`) created and `chmod +x` | ☐ |
| 12 | zsh default shell hook (`0100`) created and `chmod +x` | ☐ |
| 13 | Permissions fix hook (`0200`) created and `chmod +x` | ☐ |
| 14 | Cleanup hook (`0900`) created and `chmod +x` | ☐ |
| 15 | `lb build` completed without errors | ☐ |
| 16 | ISO file present: `exarescue-arm64.iso` | ☐ |
| 17 | ISO mounted and `live/` directory contains `vmlinuz`, `initrd.img`, `filesystem.squashfs` | ☐ |
| 18 | `filesystem.squashfs` is under 1 GB | ☐ |
| 19 | Three PXE files copied to `/tmp/exarescue-pxe/` | ☐ |
| 20 | Three PXE files SCP'd to `EXAPROVCLD001:/srv/www/gparted/arm64/` | ☐ |
| 21 | HTTP availability verified for all three files (`curl -I`) | ☐ |
| 22 | arm64 VM boots successfully from PXE and reaches Fluxbox desktop | ☐ |
| 23 | GParted launches and displays disks | ☐ |
| 24 | ZFS/LVM/NTFS tools verified: `zpool version`, `lvs`, `ntfsfix --version` | ☐ |
| 25 | Shell environment verified: zsh, vim, tmux all functional | ☐ |

---

## Naming Convention Reference

| Prefix | Role | Example |
|--------|------|---------|
| `EXAFWL` | Firewall | `EXAFWLFAL001` |
| `EXAPVE` | Proxmox VE node | `EXAPVEFAL001` |
| `EXADCS` | Domain Controller | `EXADCSFAL001` |
| `EXAPRV` | Provisioning server | `EXAPRVFAL001` |
| `EXAMBP` | MacBook Pro | `EXAMBPFAL001` |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
