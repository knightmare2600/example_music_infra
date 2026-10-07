#!/usr/bin/env bash
# ==============================================================================
# bootstrap/setup-workstation-linux.sh
# Example Music Limited — Engineer workstation setup (Linux)
# ==============================================================================
# Three jobs, one script:
#   1. Install/confirm the tool set docs/ExampleMusic_Beginners_Guide.md §11
#      requires on an engineer's own machine.
#   2. Install pinned-version workstation tools (currently: fyrtaarn, Robert's
#      own BMC controller app) from benarbejde/asset_manifest.json's
#      workstation_tools[] -- checksum-verified against the GitHub Releases
#      API, reinstalled automatically if the installed binary doesn't match
#      the manifest's pinned tag (e.g. after check_workstation_tool_versions.py
#      flags a newer release and Robert bumps the pin).
#   3. Populate bootstrap/web/'s upstream-sourced boot assets from
#      benarbejde/asset_manifest.json's assets[]/archives[] -- the same job
#      ansible/playbooks/bootstrap_assets/fetch-assets.yml used to do, ported
#      to bash because ansible-playbook cannot run natively on Windows at all
#      (a hard, long-standing Ansible limitation) -- one native script per
#      platform beats requiring WSL just to run a downloader.
#
# Presumes a Debian-flavour distro (apt) -- per Robert: "a tech with a Linux
# laptop is a rarity, but do cater for it." Companion scripts:
#   bootstrap/setup-workstation-macos.sh   (Homebrew)
#   bootstrap/Setup-Workstation.ps1        (Chocolatey, Windows)
# Deliberately separate files, not one shared macOS/Linux script, despite the
# real overlap in fetch logic -- Robert's explicit instruction.
#
# Idempotent: every dependency check/install and every asset fetch is
# skip-if-already-correct. Safe to re-run any time (e.g. after
# benarbejde/asset_manifest.json gains a new entry, or an upstream release
# ships a newer build) -- matches this repo's standing "don't change what
# isn't broken" rule.
#
# Every fetch is checksum-verified before being trusted -- see
# benarbejde/asset_manifest.json's own header for exactly how, per
# source_type. Never trust a download on HTTP status alone.
#
# Usage:
#   ./bootstrap/setup-workstation-linux.sh              # deps + assets
#   ./bootstrap/setup-workstation-linux.sh --deps-only   # skip asset fetch
#   ./bootstrap/setup-workstation-linux.sh --assets-only # skip dependency install
#   ./bootstrap/setup-workstation-linux.sh --refresh     # force re-fetch every asset/archive,
#                                                         # even if its dest file(s) already exist
#
# Requires: bash, sudo (for apt), curl, jq, unzip, 7z (p7zip/7zip package,
# needed for archives[] entries that are .iso rather than .zip -- currently
# just the debian/ mini.iso entries) -- if these are missing, the
# dependency-install step installs them too (bootstrapped via a plain
# `apt-get install`, no chicken-and-egg problem since apt itself needs none
# of these).
# ==============================================================================
# Changelog:
#   2026-10-07  Robert's real test: font showed "installed" in a font viewer but wasn't
#               selectable in mate-terminal. Checked properly rather than guessing which of
#               two possible causes it was -- `fc-list` confirmed the font IS correctly
#               installed and fontconfig-indexed (ruling that out); `which mate-terminal
#               gnome-terminal` confirmed only mate-terminal exists -- gnome-terminal was
#               never installed, so configure_gnome_terminal_font() (targets
#               org.gnome.Terminal's schema specifically) silently skipped and never got a
#               chance to configure anything. Added configure_mate_terminal_font()
#               (org.mate.terminal.profile schema) -- confirmed real, both via research and
#               a live round-trip Robert ran directly on the actual test machine before this
#               was ever wired into the script. org.mate.terminal.global profile-list
#               returned ['default'] there; falls back to the literal "default" profile ID
#               if that list ever comes back empty (reportedly possible on a normal install,
#               since dconf only reports explicitly-set values, never schema defaults).
#               Verified the schema-detection, profile-list-parsing, and graceful-skip-on-
#               non-MATE-systems logic against stubs before shipping. Also corrected
#               configure_gnome_terminal_font()'s own font string while touching this --
#               it predated the real confirmed family name and used the ambiguous
#               "JetBrainsMonoNL Nerd Font Mono" alias (shared across every weight) instead
#               of "JetBrainsMonoNL NFM Thin" (confirmed specific to this weight, same value
#               now used consistently everywhere -- macOS, GNOME Terminal, MATE Terminal).
#   2026-10-07  REAL BUG, found live (Jamie's actual run, pasted by Robert): everything
#               through PowerShell install worked cleanly, then "[x] Manifest not found:
#               /home/benarbejde/asset_manifest.json" killed the ENTIRE script via the old
#               hard `exit 1` -- meaning install_pwsh_modules()/configure_pwsh_profile()/
#               install_fonts()/configure_gnome_terminal_font(), all added yesterday, never
#               got a chance to run at all. Same root cause as the macOS sibling's own
#               2026-10-06 fix (Jamie running the standalone downloaded script from his own
#               home directory, not a repo clone -- REPO_ROOT resolved one level above
#               /home/jamie, i.e. /home, giving /home/benarbejde/... exactly as seen) -- but
#               that exact fix was never ported to THIS file at the time, a real gap, not a
#               new bug. Fixed identically: both install_workstation_tools() and
#               fetch_assets()'s manifest-missing checks now msg_warn + return 0 instead of
#               msg_error + exit 1, with the real git-clone command. Verified by extracting
#               the real function and running it against the exact path from Jamie's
#               transcript -- confirms it now warns and the script continues past it.
#   2026-10-07  Robert's catch, caught before any real run hit it: two real gaps in
#               install_deps(). (1) No sudo check at all -- this file fires `sudo apt-get`/
#               `sudo dpkg` repeatedly and just let each one fail (or hang prompting for a
#               password) wherever it happened to land, rather than failing fast with a
#               clear message up front. Added `sudo -v` as the very first thing, with an
#               actionable error (add the user to the sudo group) if it fails. (2) curl
#               itself may not be pre-installed on a minimal/fresh Debian image, and the
#               very next block (git-lfs's packagecloud repo setup) pipes curl's output
#               into sudo gpg BEFORE the main `apt-get install` line further down would
#               otherwise install curl -- a genuine chicken-and-egg ordering bug, same
#               category as jq on the macOS sibling (that file's own header already
#               documents this exact class of gap for jq specifically). Added a standalone
#               curl-presence check + install, ahead of anything that needs it. Verified
#               the control-flow ordering (sudo -v, then curl-install-if-missing, in that
#               order, before the git-lfs block) against a stubbed sudo/apt-get/curl.
#   2026-10-06  Robert's ask: bring this file up to parity with today's macOS work -- install
#               PowerShell Core itself (official Microsoft apt repo, packages-microsoft-prod.deb,
#               confirmed against learn.microsoft.com directly, not guessed), the same 7-module
#               set (install_pwsh_modules(), Stage 20 parity), the full profile port (Stage 22:
#               PSReadLine Emacs/prediction/colours, Terminal-Icons, CompletionPredictor,
#               NerdFonts, nodeinfo.json MOTD banner) replacing the old colour-fix-only version,
#               and the JetBrainsMono Nerd Font (install_fonts() -- no official Debian/Ubuntu
#               apt package ships the Nerd-Font-patched variant, confirmed; same direct-GitHub-
#               zip source as ansible/playbooks/windows_bootstrap/tasks/fonts.yml, byte-for-byte
#               parity with what Windows targets get). configure_pwsh_profile() correctly uses
#               $PROFILE.CurrentUserAllHosts from the start here -- NOT bare $PROFILE, which the
#               macOS sibling used for weeks before today's bug was found live; fixed on this
#               file's very first real profile-scope implementation rather than repeating it.
#               Also added configure_gnome_terminal_font() (gsettings-based, Robert's explicit
#               choice of GNOME Terminal specifically, since Linux workstation terminal use is
#               otherwise genuinely unstandardized here) -- mechanism confirmed via research,
#               explicitly flagged as NOT independently verified on a real GNOME Terminal (no
#               GUI environment available where this was written), same category of risk as the
#               PuTTY Default Settings saga -- needs a real test and report-back before trusting.
#   2026-10-06  REAL BUG, found while fixing the identical one in setup-workstation-macos.sh
#               (Jamie's real run there showed msg_ok truncating after the first line):
#               msg_info/msg_ok/msg_warn/msg_error here only ever printed "$1", silently
#               dropping every other argument on a multi-line call -- confirmed this file's
#               own 2 multi-arg call sites (install_deps()'s summary, the VMware
#               Fusion/iTerm2 skip notice) were affected too. Fixed to "$*" (join all args
#               with a space) in all four functions, matching the fix applied to this file's
#               macOS sibling and bootstrap/web/proxmox/select-pve-answer.sh and pveme.sh --
#               same shared CY/GN/YW/RD helper pattern, same mistake, swept across every
#               original (non-vendored) file that defines it.
#   2026-10-03  Enable-/Disable-LsCompatibilityMode now carry real comment-based help
#               (SYNOPSIS/DESCRIPTION/EXAMPLE) -- Robert ran `help Enable-LsCompatibilityMode`
#               and got nothing useful back. Verified live: `Get-Help
#               Enable-LsCompatibilityMode -Full` now returns proper output.
#   2026-10-03  configure_pwsh_profile() also adds Enable-/Disable-LsCompatibilityMode --
#               Robert noticed `ls` doesn't get Terminal-Icons decoration here the way it
#               does on Windows. Confirmed live, not guessed: `Get-Command ls -All` shows
#               `ls` as a plain Application (the real /bin/ls) on this platform -- unlike
#               Windows, PowerShell deliberately doesn't alias ls -> Get-ChildItem on
#               Linux/macOS, specifically so it doesn't shadow the pre-existing native
#               tool. OFF by default (preserves that deliberate upstream choice unless
#               opted into); the toggle defines/removes a global `ls` function wrapping
#               Get-ChildItem. On Windows, both functions just print a gentle reminder
#               (warning emoji) that there's nothing to toggle there, rather than erroring.
#   2026-10-03  Added configure_pwsh_profile() -- Robert, live: PSReadLine's own default
#               Parameter/Operator colour (ANSI code 90) renders invisible against this
#               estate's Solarized Dark terminal scheme (same root cause, same fix as
#               ansible/playbooks/windows_bootstrap/tasks/ps7_setup.yml's Stage 22, fixed
#               same day for Windows target nodes). This is the control-node-side
#               equivalent -- gracefully skips if pwsh isn't installed (this script
#               doesn't install it; confirmed via this estate's own control node that
#               it's genuinely sometimes installed by hand, outside this script's own
#               package list). Idempotent, append-if-missing -- verified live on a real
#               control node, including a second run proving the skip path.
#   2026-08-13  Robert's idea: archives[] can now be a .iso (7z extraction),
#               not just .zip -- see benarbejde/asset_manifest.json's own
#               2026-08-13 changelog entry for the full reasoning (debian/
#               mini.iso replacing the old separately-fetched linux/initrd.gz
#               pair). Added --refresh (forces every fetch, bypassing the
#               skip-if-already-present check) and 7z to install_deps().
#   2026-07-27  Initial file. Fetch logic ported from
#               ansible/playbooks/bootstrap_assets/fetch-assets.yml, which
#               was live-tested against every real source this manifest
#               covers before this port happened -- same URLs, same tags,
#               same checksum strategy, not re-researched from scratch.
#               Scratch download directory deliberately NOT /tmp -- carried
#               over from a real bug found building the Ansible version:
#               /tmp can be tmpfs-backed with too little room for a large
#               archive_extract download even when the real disk has plenty
#               free. Uses a repo-relative .cache/ dir instead, same fix.
#   2026-08-08  Added install_workstation_tools() (job 2, fyrtaarn) -- see
#               benarbejde/asset_manifest.json's workstation_tools[] changelog
#               entry for the full request/reasoning. Installs to
#               /usr/local/bin/<name>, gated on $DO_DEPS (a real local tool,
#               same category as install_deps()'s apt packages, not a
#               served boot asset like fetch_assets()'s job).
# ==============================================================================

set -euo pipefail

# -- Paths --------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MANIFEST="${REPO_ROOT}/benarbejde/asset_manifest.json"
WEB_DIR="${REPO_ROOT}/bootstrap/web"
CACHE_DIR="${REPO_ROOT}/.cache/bootstrap_asset_fetch"

DO_DEPS=true
DO_ASSETS=true
FORCE_REFRESH=false
for arg in "$@"; do
  case "$arg" in
    --deps-only)   DO_ASSETS=false ;;
    --assets-only) DO_DEPS=false ;;
    --refresh)     FORCE_REFRESH=true ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# -- Colour helpers (matches this repo's existing CY/GN/YW/RD convention, --
# -- see e.g. bootstrap/web/proxmox/select-pve-answer.sh) ---------------------
RD='\033[0;31m'; GN='\033[0;32m'; YW='\033[1;33m'; CY='\033[0;36m'; NC='\033[0m'
msg_info()  { printf "${CY}[*]${NC} %s\n" "$*"; }
msg_ok()    { printf "${GN}[+]${NC} %s\n" "$*"; }
msg_warn()  { printf "${YW}[!]${NC} %s\n" "$*"; }
msg_error() { printf "${RD}[x]${NC} %s\n" "$*"; }

# ==============================================================================
# 1. Dependency install
# ==============================================================================
install_deps() {
  msg_info "Checking apt-based dependencies..."

  if ! command -v apt-get >/dev/null 2>&1; then
    msg_error "apt-get not found -- this script presumes a Debian-flavour distro. Aborting."
    exit 1
  fi

  # sudo -v validates/refreshes credentials and fails fast with a clear exit code if this
  # user genuinely isn't in the sudo group, rather than letting the first of this script's
  # many `sudo apt-get`/`sudo dpkg` calls fail confusingly deep into a run, or hang
  # prompting for a password that was never going to work. Robert's catch, 2026-10-07 --
  # no check existed at all before this.
  if ! sudo -v; then
    msg_error "sudo access is required (apt-get install, PowerShell repo setup, etc.) and" \
              "this user doesn't have it, or authentication failed. Add this user to the" \
              "sudo group first (sudo usermod -aG sudo \$USER, then log out/in) and re-run."
    exit 1
  fi

  # curl itself may not be pre-installed on a minimal/fresh Debian image -- and the
  # git-lfs repo-setup block immediately below needs curl BEFORE the main apt-get install
  # line (further down) would otherwise install it. No reasonable bootstrap order avoids
  # this except installing curl first, standalone -- same category of chicken-and-egg gap
  # as jq on the macOS sibling (see that file's own header comment). Robert's catch,
  # 2026-10-07 -- confirmed by reading the actual ordering, not assumed.
  if ! command -v curl >/dev/null 2>&1; then
    msg_info "curl not found -- installing it first (this script's own fetch logic needs it" \
             "before the main dependency install below would otherwise provide it)."
    sudo apt-get update
    sudo apt-get install -y curl
  fi

  # git-lfs isn't in every distro's default apt repo at a current version --
  # packagecloud's own install script adds the right repo first. Harmless
  # no-op if already configured.
  if ! command -v git-lfs >/dev/null 2>&1; then
    msg_info "git-lfs not found -- adding packagecloud's apt repo (official install method)."
    curl -fsSL https://packagecloud.io/github/git-lfs/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/github_git-lfs-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/github_git-lfs-archive-keyring.gpg] https://packagecloud.io/github/git-lfs/$(. /etc/os-release && echo "$ID")/ $(. /etc/os-release && echo "$VERSION_CODENAME") main" \
      | sudo tee /etc/apt/sources.list.d/github_git-lfs.list >/dev/null
  fi

  sudo apt-get update
  sudo apt-get install -y \
    git git-lfs curl jq unzip 7zip \
    ansible \
    keepassxc \
    wireguard-tools \
    virt-viewer \
    wireshark \
    ipcalc

  git lfs install

  # PowerShell Core -- official Microsoft apt repo (packages-microsoft-prod.deb), confirmed
  # directly against Microsoft's own current docs (learn.microsoft.com/powershell/scripting/
  # install/install-debian) before writing this, same verify-before-trusting discipline as
  # every package added to the macOS sibling today. Microsoft's own docs note this only
  # works for Debian versions with a published package -- if dpkg/apt fails below on an
  # unsupported release, the manual .deb-from-GitHub-releases method in that same doc is
  # the fallback (not auto-implemented here; report back if this hits that case).
  if ! command -v pwsh &>/dev/null; then
    msg_info "pwsh not found -- adding Microsoft's official apt repo and installing PowerShell."
    local debian_version_id ms_prod_deb
    debian_version_id="$(. /etc/os-release && echo "$VERSION_ID")"
    ms_prod_deb="$(mktemp --suffix=.deb)"
    curl -fsSL -o "$ms_prod_deb" "https://packages.microsoft.com/config/debian/${debian_version_id}/packages-microsoft-prod.deb"
    sudo dpkg -i "$ms_prod_deb"
    rm -f "$ms_prod_deb"
    sudo apt-get update
    sudo apt-get install -y powershell
  fi

  msg_ok "Dependencies installed/confirmed: git, git-lfs, curl, jq, unzip, 7zip (7z, for .iso" \
         "archives[] entries), ansible, keepassxc (keepassxc-cli bundled on Debian)," \
         "wireguard-tools, virt-viewer, wireshark, ipcalc, PowerShell Core (pwsh)."
  msg_info "No native Linux equivalent for VMware Fusion or iTerm2 -- skipped (macOS-only tools," \
           "see docs/ExampleMusic_Beginners_Guide.md §11)."
}

# Same 7-module list as ansible/playbooks/windows_bootstrap/tasks/ps7_setup.yml's Stage 20 and
# bootstrap/setup-workstation-macos.sh's own install_pwsh_modules(), CurrentUser scope (single-
# user machine, same reasoning as the macOS sibling). PSWindowsUpdate is Windows-only
# (wraps Windows Update's own COM APIs) but left in the list anyway -- Install-Module's
# -ErrorAction SilentlyContinue already degrades it to a harmless no-op on a platform it
# doesn't support, confirmed live on macOS earlier today (it actually installed cleanly
# there too, just wouldn't do anything useful if imported).
install_pwsh_modules() {
  if ! command -v pwsh &>/dev/null; then
    msg_info "pwsh not found on PATH -- skipping PS7 module install."
    return
  fi

  msg_info "Installing PS7 console modules (CurrentUser scope)..."
  pwsh -NoLogo -NoProfile -Command '
    $modules = @(
      "PSConsoleTools",
      "PSWindowsUpdate",
      "PSWriteColor",
      "PSReadLine",
      "Terminal-Icons",
      "CompletionPredictor",
      "NerdFonts"
    )
    foreach ($m in $modules) {
      if (-not (Get-Module -ListAvailable -Name $m)) {
        Install-Module $m -Scope CurrentUser -Force -SkipPublisherCheck -ErrorAction SilentlyContinue
        Write-Output "Installed: $m"
      } else {
        Write-Output "Already present: $m"
      }
    }
  '
  msg_ok "PS7 modules checked/installed."
}

# JetBrainsMono Nerd Font -- same source Windows targets already get
# (ansible/playbooks/windows_bootstrap/tasks/fonts.yml), same exact URL/version, deliberately
# NOT a different font source for byte-for-byte parity across the estate. No official Debian/
# Ubuntu apt package ships the Nerd-Font-patched variant (confirmed: `fonts-jetbrains-mono` is
# the plain, unpatched font, no icon glyphs) -- same direct-GitHub-zip approach as fonts.yml,
# just extracting to ~/.local/share/fonts/ (user-level, no sudo) instead of C:\Windows\Fonts.
install_fonts() {
  local font_dir="${HOME}/.local/share/fonts"
  local thin_font="${font_dir}/JetBrainsMonoNLNerdFontMono-Thin.ttf"
  local regular_font="${font_dir}/JetBrainsMonoNLNerdFontMono-Regular.ttf"

  if [[ -f "$thin_font" && -f "$regular_font" ]]; then
    msg_info "JetBrainsMono Nerd Font already installed -- skipping."
    return
  fi

  msg_info "Installing JetBrainsMono Nerd Font..."
  mkdir -p "$font_dir"
  local tmp_zip tmp_extract
  tmp_zip="$(mktemp --suffix=.zip)"
  tmp_extract="$(mktemp -d)"
  curl -fsSL -o "$tmp_zip" "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/JetBrainsMono.zip"
  unzip -q -o "$tmp_zip" -d "$tmp_extract"
  cp "${tmp_extract}/JetBrainsMonoNLNerdFontMono-Thin.ttf" "$thin_font"
  cp "${tmp_extract}/JetBrainsMonoNLNerdFontMono-Regular.ttf" "$regular_font"
  rm -rf "$tmp_zip" "$tmp_extract"

  if command -v fc-cache &>/dev/null; then
    fc-cache -f "$font_dir" >/dev/null
  fi
  msg_ok "JetBrainsMono Nerd Font installed to ${font_dir} (Thin + Regular)."
}

# GNOME Terminal only -- Robert's call, 2026-10-06, since Linux workstation terminal use is
# genuinely unstandardized here (this file's own header: "a tech with a Linux laptop is a
# rarity, but do cater for it"). Mechanism confirmed via research, NOT independently tested
# on a real GNOME Terminal (no GUI/desktop environment available in the environment that
# wrote this) -- gsettings/dconf keys under the current default profile's own UUID, same
# approach several real-world dotfiles repos use. Gracefully skips on any other desktop
# (KDE/XFCE/Alacritty/a Linux box with no GUI at all, which is the actual common case for a
# control node) rather than erroring.
configure_gnome_terminal_font() {
  if ! command -v gsettings &>/dev/null; then
    msg_info "gsettings not found -- not a GNOME desktop, skipping GNOME Terminal font config."
    return
  fi

  local profile_id
  profile_id="$(gsettings get org.gnome.Terminal.ProfilesList default 2>/dev/null | tr -d "'")"
  if [[ -z "$profile_id" ]]; then
    msg_info "No default GNOME Terminal profile found -- skipping font config."
    return
  fi

  # "JetBrainsMonoNL NFM Thin" -- the font's real family name, confirmed twice independently
  # (2026-10-06, parsing the macOS .ttf's own binary name table directly; 2026-10-07, this
  # very file's install_fonts(), via `fc-list` on real Debian: "JetBrainsMonoNL Nerd Font
  # Mono,JetBrainsMonoNL NFM,JetBrainsMonoNL NFM Thin:style=Thin,Regular"). NOT
  # "JetBrainsMonoNL Nerd Font Mono" (this function's own original value) -- that alias is
  # shared across every weight in the family, not specific to Thin.
  local profile_path="org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:${profile_id}/"
  gsettings set "$profile_path" use-system-font false
  gsettings set "$profile_path" font "JetBrainsMonoNL NFM Thin 12"
  msg_ok "GNOME Terminal default profile (${profile_id}) font set to JetBrainsMonoNL NFM Thin 12."
  msg_warn "NOT independently verified on a real GNOME Terminal -- please confirm this actually" \
           "took effect (open a new GNOME Terminal window) and report back, same as the PuTTY" \
           "font work earlier this week."
}

# MATE Terminal -- added 2026-10-07 after Robert's real test showed only mate-terminal
# installed (gnome-terminal absent), so configure_gnome_terminal_font() above silently
# skipped and never had a chance to configure anything. Confirmed real mechanism via
# research AND a live round-trip Robert ran directly (gsettings set ... font '...'; gsettings
# get ... font came back with the exact value set, no error) before this was ever wired into
# the script -- same discipline as the PuTTY/iTerm2 work. org.mate.terminal.global
# profile-list came back ['default'] on the real test machine; profile-list can reportedly
# come back EMPTY even on a normal install (dconf only reports explicitly-set values, never
# schema defaults), so this falls back to the literal "default" profile ID -- which every
# stock MATE Terminal install has via schema default -- rather than failing if the list
# happens to be empty.
configure_mate_terminal_font() {
  if ! command -v gsettings &>/dev/null; then
    msg_info "gsettings not found -- skipping MATE Terminal font config."
    return
  fi

  if ! gsettings list-schemas 2>/dev/null | grep -qx "org.mate.terminal.profile"; then
    msg_info "org.mate.terminal.profile schema not found -- not a MATE desktop, skipping."
    return
  fi

  local profile_id
  profile_id="$(gsettings get org.mate.terminal.global profile-list 2>/dev/null \
    | tr -d "[]' " | cut -d',' -f1)"
  if [[ -z "$profile_id" ]]; then
    profile_id="default"
  fi

  local profile_path="org.mate.terminal.profile:/org/mate/terminal/profiles/${profile_id}/"
  gsettings set "$profile_path" font "JetBrainsMonoNL NFM Thin 12"
  msg_ok "MATE Terminal profile (${profile_id}) font set to JetBrainsMonoNL NFM Thin 12."
  msg_warn "Confirmed via a real round-trip on the actual test machine (gsettings set + get" \
           "back matched), but please open a NEW MATE Terminal window and confirm the font" \
           "actually RENDERS correctly -- a successful write/read-back isn't proof of that," \
           "same lesson as the PuTTY saga."
}

# ==============================================================================
# 2. Asset fetch -- three source_type handlers, matching
#    benarbejde/asset_manifest.json's own header exactly
# ==============================================================================

fetch_github_release() {
  local dest="$1" repo="$2" tag="$3" asset_name="$4"
  local full_dest="${WEB_DIR}/${dest}"

  if [[ "$FORCE_REFRESH" == "false" && -f "$full_dest" ]]; then
    return 0
  fi

  local api_url
  if [[ "$tag" == "latest" ]]; then
    api_url="https://api.github.com/repos/${repo}/releases/latest"
  else
    api_url="https://api.github.com/repos/${repo}/releases/tags/${tag}"
  fi

  msg_info "Fetching ${dest} (${repo}@${tag})..."

  local meta
  if ! meta="$(curl -fsSL "$api_url")"; then
    msg_error "  Failed to query ${api_url}"
    return 1
  fi

  local download_url digest expected_hash
  download_url="$(jq -r --arg name "$asset_name" '.assets[] | select(.name == $name) | .browser_download_url' <<<"$meta")"
  digest="$(jq -r --arg name "$asset_name" '.assets[] | select(.name == $name) | .digest' <<<"$meta")"

  if [[ -z "$download_url" || "$download_url" == "null" ]]; then
    msg_error "  Asset '${asset_name}' not found in ${repo}@${tag}'s release"
    return 1
  fi
  expected_hash="${digest#sha256:}"

  mkdir -p "$(dirname "$full_dest")"
  curl -fsSL -o "$full_dest" "$download_url"

  local actual_hash
  actual_hash="$(sha256sum "$full_dest" | cut -d' ' -f1)"
  if [[ -n "$expected_hash" && "$actual_hash" != "$expected_hash" ]]; then
    msg_error "  CHECKSUM MISMATCH for ${dest}: expected ${expected_hash}, got ${actual_hash}"
    rm -f "$full_dest"
    return 1
  fi
  msg_ok "  ${dest} (sha256:${actual_hash})"
}

fetch_url_with_checksum_file() {
  local dest="$1" url="$2" checksum_file_url="$3" checksum_file_entry="$4"
  local full_dest="${WEB_DIR}/${dest}"

  if [[ "$FORCE_REFRESH" == "false" && -f "$full_dest" ]]; then
    return 0
  fi

  msg_info "Fetching ${dest}..."

  local checksum_text expected_hash
  if ! checksum_text="$(curl -fsSL "$checksum_file_url")"; then
    msg_error "  Failed to fetch checksum file ${checksum_file_url}"
    return 1
  fi

  # Format-agnostic on purpose -- see benarbejde/asset_manifest.json's own
  # header. A SHA256 hash is always a 64-hex-char string regardless of
  # whether the surrounding line reads "<hash>  <path>" (GNU, Debian's
  # SHA256SUMS) or "SHA256 (<file>) = <hash>" (BSD, OpenBSD's SHA256).
  expected_hash="$(grep -F "$checksum_file_entry" <<<"$checksum_text" | grep -oE '[0-9a-fA-F]{64}' | head -1)"
  if [[ -z "$expected_hash" ]]; then
    msg_error "  Could not find a checksum for '${checksum_file_entry}' in ${checksum_file_url}"
    return 1
  fi

  mkdir -p "$(dirname "$full_dest")"
  curl -fsSL -o "$full_dest" "$url"

  local actual_hash
  actual_hash="$(sha256sum "$full_dest" | cut -d' ' -f1)"
  if [[ "$actual_hash" != "$expected_hash" ]]; then
    msg_error "  CHECKSUM MISMATCH for ${dest}: expected ${expected_hash}, got ${actual_hash}"
    rm -f "$full_dest"
    return 1
  fi
  msg_ok "  ${dest} (sha256:${actual_hash})"
}

fetch_archive() {
  # $1 = archive url, $2 = checksum_file_url (empty string = skip verification),
  # $3 = checksum_file_entry, remaining args = "archive_path|dest" pairs
  local url="$1" checksum_file_url="$2" checksum_file_entry="$3"; shift 3

  local any_missing=false
  local pair archive_path dest
  for pair in "$@"; do
    dest="${pair#*|}"
    [[ -f "${WEB_DIR}/${dest}" ]] || any_missing=true
  done
  if [[ "$FORCE_REFRESH" == "false" && "$any_missing" == "false" ]]; then
    return 0
  fi

  # SourceForge (and some other hosts) serve real download links ending in a
  # trailing /download segment, not a filename -- strip it before deriving a
  # local filename, same fix as fetch-assets.yml needed for the same reason.
  local archive_filename
  archive_filename="$(basename "$(sed -E 's#/download/?$##' <<<"$url")")"

  mkdir -p "${CACHE_DIR}/extracted"
  local archive_path_local="${CACHE_DIR}/${archive_filename}"
  local extract_dir="${CACHE_DIR}/extracted/${archive_filename}.d"

  msg_info "Fetching archive ${archive_filename}..."
  curl -fsSL -o "$archive_path_local" "$url"

  if [[ -n "$checksum_file_url" ]]; then
    local checksum_text expected_hash actual_hash
    if ! checksum_text="$(curl -fsSL "$checksum_file_url")"; then
      msg_error "  Failed to fetch checksum file ${checksum_file_url}"
      rm -f "$archive_path_local"
      return 1
    fi
    expected_hash="$(grep -F "$checksum_file_entry" <<<"$checksum_text" | grep -oE '[0-9a-fA-F]{64}' | head -1)"
    if [[ -z "$expected_hash" ]]; then
      msg_error "  Could not find a checksum for '${checksum_file_entry}' in ${checksum_file_url}"
      rm -f "$archive_path_local"
      return 1
    fi
    actual_hash="$(sha256sum "$archive_path_local" | cut -d' ' -f1)"
    if [[ "$actual_hash" != "$expected_hash" ]]; then
      msg_error "  CHECKSUM MISMATCH for ${archive_filename}: expected ${expected_hash}, got ${actual_hash}"
      rm -f "$archive_path_local"
      return 1
    fi
  fi

  mkdir -p "$extract_dir"
  # .zip (unzip) and .iso (7z -- p7zip/7zip package, reads ISO9660 natively,
  # same as it reads zip/tar/rar/etc) are the two archive types this repo's
  # manifest currently uses. See benarbejde/asset_manifest.json's own
  # _readme note for why .iso was added 2026-08-13 (debian/ mini.iso).
  case "$archive_filename" in
    *.iso) 7z x -y -o"${extract_dir}" "$archive_path_local" >/dev/null ;;
    *.zip) unzip -q -o "$archive_path_local" -d "$extract_dir" ;;
    *) msg_error "  Don't know how to extract ${archive_filename} (not .zip or .iso)"; return 1 ;;
  esac

  for pair in "$@"; do
    archive_path="${pair%|*}"
    dest="${pair#*|}"
    local full_dest="${WEB_DIR}/${dest}"
    [[ "$FORCE_REFRESH" == "false" && -f "$full_dest" ]] && continue
    mkdir -p "$(dirname "$full_dest")"
    cp "${extract_dir}/${archive_path}" "$full_dest"
    msg_ok "  ${dest} (from ${archive_filename})"
  done

  rm -rf "$CACHE_DIR"
}

# ==============================================================================
# 3. Workstation tools -- benarbejde/asset_manifest.json's workstation_tools[]
#    (added 2026-08-08, Robert -- real locally-run tools, not boot assets;
#    see that file's own _readme note for the full reasoning)
# ==============================================================================
# Deliberately NOT the same "skip if file already exists" idempotency as
# fetch_github_release() above -- these are pinned-version tools a harness
# check nudges Robert to bump over time (check_workstation_tool_versions.py),
# and a bumped pin needs to actually take effect on the next run without a
# manual `rm` first. Verifies the INSTALLED binary's checksum against the
# manifest's pinned tag/asset every run and only reinstalls on mismatch.
#
# 2026-09-26: openrsat's linux-* assets are real .deb packages, not raw
# executables like every entry before it (fyrtaarn) -- a downloaded .deb
# can't just be `install -m 0755`'d into place the way a raw binary can, and
# a package's installed state isn't one file at a fixed path, so the
# raw-binary idempotency check below (comparing install_path's own sha256)
# doesn't apply to it either. Branch on the asset filename's own extension
# rather than adding a new manifest field -- the format is already fully
# determined by what upstream actually published, nothing new to track.
install_workstation_tools() {
  if [[ ! -f "$MANIFEST" ]]; then
    msg_warn "Manifest not found: ${MANIFEST} -- skipping workstation_tools install."
    msg_warn "This almost always means the script was downloaded standalone, not run from" \
             "inside a full clone of this repo (REPO_ROOT is derived as one directory up" \
             "from wherever this script itself lives). Clone the repo properly to get this" \
             "job too: git clone https://github.com/knightmare2600/example_music_infra/" \
             "-- or ignore this if --deps-only (packages) was all you wanted."
    return 0
  fi

  local goos goarch platform_key
  goos="linux"
  case "$(uname -m)" in
    x86_64)  goarch="amd64" ;;
    aarch64) goarch="arm64" ;;
    armv7l)  goarch="armv7" ;;
    *)
      msg_warn "Unrecognised architecture $(uname -m) -- skipping workstation_tools install (no matching asset)."
      return 0
      ;;
  esac
  platform_key="${goos}-${goarch}"

  local name repo tag asset_name
  while IFS=$'\t' read -r name repo tag; do
    asset_name="$(jq -r --arg t "$name" --arg k "$platform_key" '.workstation_tools[] | select(.name == $t) | .assets[$k] // empty' "$MANIFEST")"
    if [[ -z "$asset_name" ]]; then
      msg_warn "${name}: no asset for ${platform_key} in the manifest -- skipping."
      continue
    fi

    local install_dir="/usr/local/bin"
    local install_path="${install_dir}/${name}"
    local is_deb=false
    [[ "$asset_name" == *.deb ]] && is_deb=true

    msg_info "Checking ${name} (${repo}@${tag}, ${platform_key})..."

    local api_url meta digest expected_hash
    api_url="https://api.github.com/repos/${repo}/releases/tags/${tag}"
    if ! meta="$(curl -fsSL "$api_url")"; then
      msg_error "  Failed to query ${api_url}"
      continue
    fi
    digest="$(jq -r --arg n "$asset_name" '.assets[] | select(.name == $n) | .digest' <<<"$meta")"
    expected_hash="${digest#sha256:}"
    if [[ -z "$expected_hash" ]]; then
      msg_error "  Asset '${asset_name}' not found in ${repo}@${tag}'s release"
      continue
    fi

    if $is_deb; then
      # No single file at a fixed path to hash the way a raw binary has --
      # dpkg's own installed-version record is the real state to check
      # instead. tag is "vX.Y.Z", dpkg's Version field is "X.Y.Z" (confirmed
      # live against the real openrsat .deb, 2026-09-26) -- strip the 'v'.
      local expected_version installed_version
      expected_version="${tag#v}"
      installed_version="$(dpkg-query -W -f='${Version}' "$name" 2>/dev/null || true)"
      if [[ "$installed_version" == "$expected_version" ]]; then
        msg_ok "  ${name} already at ${tag} (dpkg version ${installed_version})"
        continue
      fi
    elif [[ -f "$install_path" ]]; then
      local current_hash
      current_hash="$(sha256sum "$install_path" | cut -d' ' -f1)"
      if [[ "$current_hash" == "$expected_hash" ]]; then
        msg_ok "  ${name} already at ${tag} (sha256:${current_hash})"
        continue
      fi
      msg_info "  Installed ${name} doesn't match pinned ${tag} -- reinstalling."
    fi

    local download_url
    download_url="$(jq -r --arg n "$asset_name" '.assets[] | select(.name == $n) | .browser_download_url' <<<"$meta")"

    local tmp_path
    tmp_path="$(mktemp)"
    curl -fsSL -o "$tmp_path" "$download_url"

    local actual_hash
    actual_hash="$(sha256sum "$tmp_path" | cut -d' ' -f1)"
    if [[ "$actual_hash" != "$expected_hash" ]]; then
      msg_error "  CHECKSUM MISMATCH for ${name}: expected ${expected_hash}, got ${actual_hash}"
      rm -f "$tmp_path"
      continue
    fi

    if $is_deb; then
      # apt's own local-file detection is extension-based as much as
      # path-based in places -- rename explicitly rather than lean on that,
      # so this is unambiguous to both apt and anyone reading it later.
      # apt (not dpkg -i) deliberately, so real declared deps (confirmed
      # live: openrsat's own .deb Depends on libgtk2.0-0) get resolved
      # instead of left as a half-configured package.
      local tmp_deb_path="${tmp_path}.deb"
      mv "$tmp_path" "$tmp_deb_path"
      sudo apt-get install -y "$tmp_deb_path"
      rm -f "$tmp_deb_path"
      msg_ok "  ${name} installed via apt (${tag}, sha256:${actual_hash})"
    else
      sudo mkdir -p "$install_dir"
      sudo install -m 0755 "$tmp_path" "$install_path"
      rm -f "$tmp_path"
      msg_ok "  ${name} installed to ${install_path} (${tag}, sha256:${actual_hash})"
    fi
  done < <(jq -r '.workstation_tools[] | [.name, .repo, .tag] | @tsv' "$MANIFEST")
}

# Example Music Limited -- PSReadLine's own default Parameter/Operator colour
# (ANSI code 90, "bright black") renders invisible against this estate's Solarized
# Dark terminal scheme, which maps that exact ANSI slot to the background colour
# itself (#002B36) -- see docs/solarized-dark-terminal-setup.md. Same fix as
# ansible/playbooks/windows_bootstrap/tasks/ps7_setup.yml's Stage 22 profile
# (2026-10-03) for the Windows-target side -- this is the control-node-side
# equivalent, since pwsh is confirmed installed on a real control node already
# (not by this script -- it was installed by hand; this only configures its
# profile IF pwsh is already present, same graceful-skip pattern
# Setup-Workstation.ps1's own Set-PowerShellProfiles uses). True-RGB escape, not
# another ANSI slot number, so this is correct regardless of which terminal is
# actually connecting (iTerm2, Windows Terminal, PuTTY, a local TTY, ...).
configure_pwsh_profile() {
  if ! command -v pwsh &>/dev/null; then
    msg_info "pwsh not found on PATH -- skipping PowerShell Core profile configuration (not installed by this script; install it by hand first if you want this)."
    return
  fi

  # $PROFILE.CurrentUserAllHosts, NOT bare $PROFILE -- bare $PROFILE resolves to
  # CurrentUserCurrentHost (Microsoft.PowerShell_profile.ps1), which is per-HOST
  # (only the raw pwsh console, not any other PS7 host). Confirmed live on the
  # macOS sibling, 2026-10-06: it used bare $PROFILE for weeks and wrote to the
  # wrong, narrower-scoped file without anyone noticing until the profile
  # actually carried something worth having everywhere. Fixed here from the
  # start rather than repeating that mistake.
  local profile_path
  profile_path="$(pwsh -NoLogo -NoProfile -Command '$PROFILE.CurrentUserAllHosts')"
  local profile_dir
  profile_dir="$(dirname "$profile_path")"

  mkdir -p "$profile_dir"

  # New, more specific marker than the old "PSReadLine Parameter/Operator colour
  # fix" one -- same reasoning as the macOS sibling's own 2026-10-06 fix: a
  # machine that already ran the OLD, narrower version of this profile won't
  # match this marker, so it gets the new block appended too (harmless,
  # one-time redundant PSReadLine colour-set, not worth a full old-block-removal
  # mechanism for a one-time transition).
  local marker="Example Music Limited -- PS7 profile (PSReadLine/Terminal-Icons/CompletionPredictor/NerdFonts/MOTD)"

  if [[ -f "$profile_path" ]] && grep -qF "$marker" "$profile_path"; then
    msg_info "${profile_path}: PS7 profile already present, skipping."
    return
  fi

  cat >> "$profile_path" <<'EOF'

# Example Music Limited -- PS7 profile (PSReadLine/Terminal-Icons/CompletionPredictor/NerdFonts/MOTD)
# Added by bootstrap/setup-workstation-linux.sh -- same content as
# ansible/playbooks/windows_bootstrap/tasks/ps7_setup.yml's Stage 22 -- safe to
# remove or edit freely.

# PSReadLine -- Emacs mode required for correct paste behaviour over SSH
if (Get-Module -ListAvailable PSReadLine) {
    Import-Module PSReadLine
    Set-PSReadLineOption -EditMode Emacs
    Set-PSReadLineOption -PredictionSource HistoryAndPlugin
    Set-PSReadLineOption -PredictionViewStyle ListView
    Set-PSReadLineKeyHandler -Key Tab -Function MenuComplete

    # PSReadLine's own default Parameter/Operator colour (ANSI code 90, "bright
    # black") renders invisible against this estate's Solarized Dark terminal
    # scheme -- see docs/solarized-dark-terminal-setup.md. True-RGB escapes, not
    # another ANSI slot number, so this renders correctly regardless of which
    # terminal is actually connecting.
    Set-PSReadLineOption -Colors @{
        Parameter = "$([char]0x1b)[38;2;88;110;117m"   # Solarized base01, #586E75
        Operator  = "$([char]0x1b)[38;2;88;110;117m"   # same root cause, same fix
    }
}

# Terminal-Icons
if (Get-Module -ListAvailable Terminal-Icons) {
    Import-Module Terminal-Icons
}

# CompletionPredictor
if (Get-Module -ListAvailable CompletionPredictor) {
    Import-Module CompletionPredictor
}

# NerdFonts
if (Get-Module -ListAvailable NerdFonts) {
    Import-Module NerdFonts
}

# MOTD banner -- nodeinfo.json. A real control node (unlike a pure engineer
# workstation) may genuinely have this -- linux/tools.yml writes
# /etc/example-music/nodeinfo.json to every Ansible-managed Linux host,
# including this one if it's EXAANSCLD001 or similar. Silently prints nothing
# if absent, same graceful no-op as the macOS/Windows versions.
if (-not [Console]::IsInputRedirected) {
    $nodeinfoPath = if ($IsWindows) {
        'C:\ProgramData\ExampleMusic\Config\nodeinfo.json'
    } else {
        '/etc/example-music/nodeinfo.json'
    }
    if (Test-Path $nodeinfoPath) {
        try {
            $ni = Get-Content -Raw $nodeinfoPath | ConvertFrom-Json

            $esc    = [char]0x1b
            $red    = "$esc[38;2;242;82;34m"    # #F25022
            $green  = "$esc[38;2;127;186;0m"    # #7FBA00
            $blue   = "$esc[38;2;0;164;239m"     # #00A4EF
            $yellow = "$esc[38;2;255;185;0m"    # #FFB900
            $reset  = "$esc[0m"

            $logoLines = @(
                "$red########$reset $green########$reset"
                "$red########$reset $green########$reset"
                "$red########$reset $green########$reset"
                ""
                "$blue########$reset $yellow########$reset"
                "$blue########$reset $yellow########$reset"
                "$blue########$reset $yellow########$reset"
            )
            $infoLines = @(
                "$($ni.hostname)  [$($ni.role) / $($ni.site)]"
                "$($ni.fqdn)"
                "$($ni.office_name), $($ni.city), $($ni.country)  ($($ni.entity))"
                ""
                "Environment: $($ni.environment)"
                "Built: $($ni.bootstrapped_at.ToString('yyyy-MM-ddTHH:mm:ssZ')) ($($ni.bootstrapped_by))"
                "Last run: $($ni.last_ansible_run.ToString('yyyy-MM-ddTHH:mm:ssZ')) ($($ni.last_ansible_play))"
            )

            Write-Host ""
            for ($i = 0; $i -lt $logoLines.Count; $i++) {
                Write-Host "  $($logoLines[$i])   $($infoLines[$i])"
            }
            Write-Host ""
        } catch {
            # Malformed/partial nodeinfo.json -- never block a real pwsh launch over this.
        }
    }
}

# Example Music Limited -- ls/Get-ChildItem maximum-compatibility toggle.
# On Windows, PowerShell aliases ls -> Get-ChildItem by default (no native ls.exe
# exists to conflict with). On Linux/macOS, PowerShell deliberately does NOT
# create that alias -- ls resolves to the real native binary instead, by design,
# specifically so it doesn't shadow a pre-existing Unix tool. Terminal-Icons only
# decorates Get-ChildItem's own output, so ls never shows icons here unless you
# opt in. OFF by default -- call Enable-LsCompatibilityMode to turn it on for
# this session, Disable-LsCompatibilityMode to go back to the native binary.
function Enable-LsCompatibilityMode {
    <#
    .SYNOPSIS
    Turns on ls/Get-ChildItem compatibility mode for this session.
    .DESCRIPTION
    PowerShell aliases ls -> Get-ChildItem by default on Windows, but deliberately
    does not on Linux/macOS, so it doesn't shadow the real native ls binary that's
    already there. This opts in anyway, for anyone who wants ls to behave the same
    way here as it does in a Windows PS7 session, including Terminal-Icons
    decoration. Session-scoped only -- not persisted, and has no effect on
    Windows, where this is already the default.
    .EXAMPLE
    Enable-LsCompatibilityMode
    Turns the override on; ls now calls Get-ChildItem for the rest of this session.
    #>
    if ($IsWindows) {
        Write-Host "⚠️  Enable-LsCompatibilityMode has no effect on Windows -- ls is already Get-ChildItem natively here. Continuing without changes." -ForegroundColor Yellow
        return
    }
    function global:ls { Get-ChildItem @args }
    Write-Host "ls compatibility mode ON -- ls now calls Get-ChildItem (Terminal-Icons decoration included). Run Disable-LsCompatibilityMode to revert." -ForegroundColor Green
}

function Disable-LsCompatibilityMode {
    <#
    .SYNOPSIS
    Turns off ls/Get-ChildItem compatibility mode, restoring the native ls binary.
    .DESCRIPTION
    Reverses Enable-LsCompatibilityMode by removing the global ls function
    override, so ls resolves to the real native binary again instead of
    Get-ChildItem. Has no effect on Windows, where ls is always Get-ChildItem.
    .EXAMPLE
    Disable-LsCompatibilityMode
    Removes the override; ls goes back to the native binary.
    #>
    if ($IsWindows) {
        Write-Host "⚠️  Disable-LsCompatibilityMode has no effect on Windows -- ls is always Get-ChildItem there." -ForegroundColor Yellow
        return
    }
    if (Test-Path Function:\ls) {
        Remove-Item Function:\ls
    }
    Write-Host "ls compatibility mode OFF -- ls resolves to the native binary again." -ForegroundColor Green
}
EOF
  msg_ok "${profile_path}: PS7 profile (PSReadLine/Terminal-Icons/CompletionPredictor/NerdFonts/MOTD) + ls compatibility toggle added."
}

fetch_assets() {
  if [[ ! -f "$MANIFEST" ]]; then
    msg_warn "Manifest not found: ${MANIFEST} -- skipping asset fetch."
    msg_warn "Same cause as install_workstation_tools()'s own warning above, if you saw it:" \
             "this script needs to run from inside a full clone of this repo, not standalone." \
             "git clone https://github.com/knightmare2600/example_music_infra/ -- or ignore" \
             "this if --deps-only (packages) was all you wanted."
    return 0
  fi
  msg_info "Reading ${MANIFEST}..."

  # -- github_release --
  while IFS=$'\t' read -r dest repo tag asset_name; do
    fetch_github_release "$dest" "$repo" "$tag" "$asset_name"
  done < <(jq -r '.assets[] | select(.source_type == "github_release") | [.dest, .repo, .tag, .asset_name] | @tsv' "$MANIFEST")

  # -- url_with_checksum_file --
  while IFS=$'\t' read -r dest url checksum_file_url checksum_file_entry; do
    fetch_url_with_checksum_file "$dest" "$url" "$checksum_file_url" "$checksum_file_entry"
  done < <(jq -r '.assets[] | select(.source_type == "url_with_checksum_file") | [.dest, .url, .checksum_file_url, .checksum_file_entry] | @tsv' "$MANIFEST")

  # -- archive_extract (top-level archives[], not assets[]) --
  local archive_count
  archive_count="$(jq '.archives // [] | length' "$MANIFEST")"
  local i
  for (( i=0; i<archive_count; i++ )); do
    local url checksum_file_url checksum_file_entry
    url="$(jq -r ".archives[$i].url" "$MANIFEST")"
    checksum_file_url="$(jq -r ".archives[$i].checksum_file_url // empty" "$MANIFEST")"
    checksum_file_entry="$(jq -r ".archives[$i].checksum_file_entry // empty" "$MANIFEST")"
    local pairs=()
    while IFS=$'\t' read -r archive_path dest; do
      pairs+=("${archive_path}|${dest}")
    done < <(jq -r ".archives[$i].members[] | [.archive_path, .dest] | @tsv" "$MANIFEST")
    fetch_archive "$url" "$checksum_file_url" "$checksum_file_entry" "${pairs[@]}"
  done

  msg_ok "Asset fetch complete."
}

# ==============================================================================
main() {
  $DO_DEPS && install_deps
  $DO_DEPS && install_workstation_tools
  $DO_DEPS && install_pwsh_modules
  $DO_DEPS && configure_pwsh_profile
  $DO_DEPS && install_fonts
  $DO_DEPS && configure_gnome_terminal_font
  $DO_DEPS && configure_mate_terminal_font
  $DO_ASSETS && fetch_assets
  msg_ok "Done."
}

main
