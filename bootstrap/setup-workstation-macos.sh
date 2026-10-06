#!/usr/bin/env bash
# ==============================================================================
# bootstrap/setup-workstation-macos.sh
# Example Music Limited — Engineer workstation setup (macOS)
# ==============================================================================
# Three jobs, one script:
#   1. Install/confirm the tool set docs/ExampleMusic_Beginners_Guide.md §11
#      requires on an engineer's own machine — Malcolm and Jamie both run
#      MacBook Pros today, so this is the platform that matters most for
#      real, current use.
#   2. Install pinned-version workstation tools (currently: fyrtaarn, Robert's
#      own BMC controller app) from benarbejde/asset_manifest.json's
#      workstation_tools[] -- checksum-verified against the GitHub Releases
#      API, reinstalled automatically if the installed binary doesn't match
#      the manifest's pinned tag.
#   3. Populate bootstrap/web/'s upstream-sourced boot assets from
#      benarbejde/asset_manifest.json's assets[]/archives[] -- the same job
#      ansible/playbooks/bootstrap_assets/fetch-assets.yml used to do, ported
#      to bash because ansible-playbook cannot run natively on Windows at
#      all (a hard, long-standing Ansible limitation) -- one native script
#      per platform beats requiring WSL just to run a downloader.
#
# Ported directly from the already-live-tested bootstrap/setup-workstation-
# linux.sh (same fetch logic, same three checksum-verified strategies) --
# NOT redesigned from scratch. Companion scripts:
#   bootstrap/setup-workstation-linux.sh   (apt, live-tested)
#   bootstrap/Setup-Workstation.ps1        (Chocolatey, Windows)
# Deliberately separate files, not one shared macOS/Linux script, despite
# the real overlap in fetch logic -- Robert's explicit instruction.
#
# *** STATUS, 2026-10-06: Job 1 LIVE-CONFIRMED on real macOS. Jobs 2/3 still not. ***
# Job 1 (dependency install) has now run for real, twice, on a real macOS VM (Jamie,
# pasted by Robert) -- every cask and formula installed correctly, and that testing
# found and fixed 4 real bugs along the way (the dead vmware-fusion cask, the
# pre-existing virt-viewer-never-in-Homebrew bug, a repo-wide message-truncation bug,
# and a PowerShell profile-scope bug). This environment originally had no macOS
# available to execute any of it on at all -- that's no longer true for job 1.
#
# Jobs 2 and 3 (install_workstation_tools/fetch_assets -- the checksum-verified fyrtaarn
# install and the whole asset-fetch pipeline) have NOT been exercised on real macOS yet.
# Both real runs so far used a standalone-downloaded copy of this one file, not a full
# repo clone, so benarbejde/asset_manifest.json was never present and both jobs skipped
# themselves (gracefully, as of today's fix) before ever reaching their own logic. The
# macOS-specific substitutions those jobs rely on (shasum -a 256 instead of sha256sum,
# BSD vs GNU sed/grep dialect) are still reasoned about, not executed -- same original
# caveat, just narrower in scope than before. Malcolm/Jamie/Robert: run this from inside
# a real clone of the repo to exercise jobs 2/3 for the first time, and report back
# anything that doesn't match.
#
# Real, known macOS differences from the Linux version, handled below:
#   - macOS has no `sha256sum` by default at all (that's a GNU coreutils
#     command). Uses `shasum -a 256` instead, macOS's own native tool.
#   - `sed -E` / `grep -oE` are BSD sed/grep here, not GNU -- the specific
#     patterns used (interval quantifiers `{64}`, `?`, anchors) are POSIX
#     ERE and should work identically under BSD's -E mode, but this
#     specific claim is reasoned, not verified against a real macOS shell.
#
# Idempotent: every dependency check/install and every asset fetch is
# skip-if-already-correct. Safe to re-run any time.
#
# Every fetch is checksum-verified before being trusted -- see
# benarbejde/asset_manifest.json's own header for exactly how, per
# source_type. Never trust a download on HTTP status alone.
#
# Usage:
#   ./bootstrap/setup-workstation-macos.sh              # deps + assets
#   ./bootstrap/setup-workstation-macos.sh --deps-only   # skip asset fetch
#   ./bootstrap/setup-workstation-macos.sh --assets-only # skip dependency install
#   ./bootstrap/setup-workstation-macos.sh --refresh     # force re-fetch every asset/archive,
#                                                         # even if its dest file(s) already exist
#
# Requires: bash (macOS ships an old bash 3.2 as /bin/bash by default due
# to GPLv3 licensing avoidance -- this script only uses bash 3.2-compatible
# syntax deliberately, no associative arrays or other 4.x+ features), curl
# (pre-installed), unzip (pre-installed). jq is installed by this script's
# own dependency step if missing -- there is no reasonable bootstrap order
# where jq is needed before Homebrew itself exists. 7z (p7zip formula) is
# also installed by this script -- needed for archives[] entries that are
# .iso rather than .zip (currently just the debian/ mini.iso entries).
# ==============================================================================
# Changelog:
#   2026-10-06  Robert's catch: install_deps() called `brew install`/`brew install --cask`
#               unconditionally on the full package list every run, and `brew tap
#               perkons/sshpass` unconditionally too -- none of these fail when already
#               installed/tapped, but none are no-ops either: every re-run printed a full
#               "Warning: Not upgrading X, the latest version is already installed" (or
#               "X is already installed and up-to-date") block per package, plus the whole
#               "taps are not trusted" advisory again for the tap -- confirmed directly in
#               Jamie's second real run, ~35 lines of pure noise on an otherwise-clean
#               re-run. Filtered every cask/formula through `brew list --cask`/`brew list
#               --formula` first and only call `brew install` with what's actually missing
#               (skips the call entirely if nothing is); `brew tap` (no args, lists current
#               taps) gates the sshpass tap the same way. Branches on a plain integer
#               counter, not `${#missing_casks[@]}`, specifically because macOS's stock
#               bash 3.2 (this file's own stated target) has a known bug where expanding an
#               empty array under `set -u` throws "unbound variable", not fixed until bash
#               4.4 -- no real bash 3.2 available to confirm the exact failure mode
#               directly, so sidestepped the question entirely rather than risk it.
#               Verified the whole filtering logic (both the already-tapped and
#               not-yet-tapped cases) against a stubbed `brew` before shipping -- confirmed
#               only genuinely-missing packages ever reach a real `brew install` call.
#               Homebrew's own existence check (`command -v brew`) deliberately left as-is
#               -- that's the right tool for "is this binary on PATH," `brew list` is the
#               right tool for "is this specific package installed via brew"; conflating
#               the two would be circular (brew list can't answer anything if brew itself
#               isn't installed yet) and isn't actually what was broken here.
#   2026-10-06  REAL BUG, found live (Jamie's second run, pasted by Robert): the profile got
#               written to ~/.config/powershell/Microsoft.PowerShell_profile.ps1, not
#               profile.ps1. Root cause confirmed directly against pwsh: bare $PROFILE
#               resolves to CurrentUserCurrentHost, which is per-HOST (only the raw pwsh
#               console, not VS Code's integrated terminal or any other PS7 host) -- this
#               function has used bare $PROFILE since it was first written 2026-08-08, so
#               the bug predates today, just never mattered until the profile actually
#               carried something worth having everywhere. Fixed to
#               $PROFILE.CurrentUserAllHosts, the actually-intended broader scope (same one
#               already correctly used for local testing on the Linux control node days
#               earlier). Added a one-time cleanup: if the old wrong-scope file exists and
#               carries this script's own "Added by bootstrap/setup-workstation-macos.sh"
#               marker (so a genuine Jamie customisation is never touched), it's removed --
#               otherwise both files would load on every pwsh start, doubling the MOTD
#               banner and module imports. Verified end-to-end: recreated Jamie's exact
#               stray-file scenario locally, confirmed the real extracted function detects
#               and removes it, writes the correct file, and a second run is a clean no-op.
#   2026-10-06  REAL BUG, found live (Jamie's actual run, previously-pushed version, pasted by
#               Robert): "Manifest not found: /Users/jamie/benarbejde/asset_manifest.json" --
#               hard `exit 1` killed the whole script after install_deps() finished cleanly.
#               Root cause, confirmed by tracing the path derivation, not guessed: Jamie
#               downloaded just this standalone .sh file into ~/Downloads rather than cloning
#               the full repo first (the doc says to clone, but grabbing one script is a
#               completely natural thing to do) -- REPO_ROOT derives as one directory up from
#               wherever the script itself lives, landing on /Users/jamie, so benarbejde/ was
#               never going to be found there regardless. This would ALSO have silently
#               prevented today's new install_pwsh_modules()/configure_pwsh_profile() work
#               from ever running, since install_workstation_tools() sits before them in
#               main() and `exit 1` kills the whole script, not just that one function.
#               Changed both this and fetch_assets()'s identical check from a hard exit to a
#               graceful msg_warn + return 0, with an actionable message (clone the repo, or
#               ignore if --deps-only was all that was wanted) -- same real failure mode, now
#               a warning instead of a crash, and no longer blocks anything after it in main().
#               Everything else in that same run was a clean pass: all 9 casks + 21 formulae
#               installed correctly, sshpass via the perkons tap worked (Homebrew's newer
#               "tap trust" warning fired but didn't actually block the install -- genuinely
#               new behaviour, not a failure, nothing to fix there).
#   2026-10-06  Robert's ask: install PowerShell Core itself (job 1 never did -- the existing
#               configure_pwsh_profile() only ever configured pwsh IF something else had
#               already installed it by hand) and deploy the same profile/plugins built for
#               Windows (ps7_setup.yml Stage 20/22) rather than just the narrower colour-fix-
#               only version this file already had. `brew install --cask powershell` (every
#               older guide's answer) is dead -- deprecated+disabled 2026-09-01, fails
#               Gatekeeper; the tap that superseded it is ALSO dead now. Confirmed directly
#               against formulae.brew.sh: PowerShell is a plain homebrew-core FORMULA now,
#               `brew install powershell`. Third time today this exact mistake class
#               surfaced (vmware-fusion, virt-viewer, now this). Added install_pwsh_modules()
#               (same 7-module list as Stage 20, CurrentUser scope not AllUsers -- single-user
#               machine) and replaced configure_pwsh_profile()'s content with Stage 22's full
#               profile verbatim (PSReadLine Emacs/prediction/colours, Terminal-Icons,
#               CompletionPredictor, NerdFonts, nodeinfo.json MOTD banner), keeping the
#               ls-compatibility-toggle functions already here (deliberately absent from the
#               Windows version, see that file's own 2026-10-03 entry). New, more specific
#               idempotency marker -- a machine that already had the old narrower profile gets
#               the new block appended too (one-time harmless redundant colour-set, not worth
#               an old-block-removal mechanism for a single transition). Flagged honestly, not
#               silently: the MOTD banner reads nodeinfo.json, which Ansible writes to MANAGED
#               hosts it provisions, never to an engineer's own laptop -- on a real Mac this
#               prints nothing, same graceful no-op the code already has for "ran before
#               nodeinfo.json exists yet." setup-workstation-linux.sh has the identical
#               narrower gap (colour-fix-only profile, same day's fix) -- not touched here,
#               flagged to Robert rather than silently left behind or silently expanded into.
#   2026-10-06  Jamie's first real run on a vanilla macOS VM (pasted transcript, Robert):
#               two real bugs found. (1) `-h`/`--help` both gave "Unknown argument" and
#               exited 2 -- this file documented a Usage: block in its own header comment
#               but never actually implemented it; added a real usage() + -h/--help case.
#               (2) `brew install --cask vmware-fusion` failed outright ("No Cask with this
#               name exists") -- confirmed via research, not guessed: Homebrew disabled this
#               cask 2025-06-23 because Broadcom now gates the VMware Fusion download behind
#               an authenticated account, which a cask can't automate. Removed from the
#               scripted install, replaced with a msg_warn pointing at the real manual
#               download path. While fixing that, swept for the same mistake class
#               elsewhere in this file per standing practice and found a SECOND, pre-existing
#               instance: `virt-viewer` was never actually in official Homebrew either (only
#               via third-party taps) -- this had been silently broken the whole time, not
#               something Jamie's run happened to hit. Robert's call: drop virt-viewer rather
#               than add a tap for it (Proxmox web UI's own console covers the same need).
#               Also added every formula/cask Robert asked for from the same session, each
#               name verified against formulae.brew.sh directly rather than typed from memory
#               (midnight-commander, htop, minicom, fastfetch, tree, wget, w3m, links, tmux,
#               zsh-autocomplete, zsh-autosuggestions, zsh-completions, zsh-syntax-highlighting,
#               sublime-text, shottr, zettlr, utm, google-chrome, mucommander, vlc, xquartz,
#               adobe-acrobat-reader). jq and ipcalc were already present -- not duplicated.
#               curl and whois are both macOS-native, no brew install needed for either --
#               noted explicitly rather than silently adding a redundant formula. sshpass is
#               deliberately excluded from homebrew-core (Homebrew's own security-policy
#               stance), added via the still-actively-maintained perkons/homebrew-sshpass tap
#               (the other commonly-cited one, hudochenkov's, was archived by its owner in
#               2020 -- checked before picking either).
#   2026-10-03  Enable-/Disable-LsCompatibilityMode now carry real comment-based help
#               (SYNOPSIS/DESCRIPTION/EXAMPLE) -- Robert ran `help Enable-LsCompatibilityMode`
#               and got nothing useful back. Verified live: `Get-Help
#               Enable-LsCompatibilityMode -Full` now returns proper output.
#   2026-10-03  configure_pwsh_profile() also adds Enable-/Disable-LsCompatibilityMode --
#               same real finding and fix as setup-workstation-linux.sh's own, same day
#               (`Get-Command ls -All` confirmed `ls` resolves to the native binary here
#               too, not the Get-ChildItem alias Windows gets by default). OFF by default,
#               gentle Windows no-op reminder included, same as the Linux sibling.
#   2026-10-03  Added configure_pwsh_profile() -- same PSReadLine Parameter/Operator
#               colour fix as setup-workstation-linux.sh's own (same day) -- this
#               script had no profile-writing logic at all before now, not just a
#               missing colour fix. Gracefully skips if pwsh isn't installed, same
#               pattern as the Linux sibling.
#   2026-08-13  Robert's idea: archives[] can now be a .iso (7z extraction),
#               not just .zip -- see benarbejde/asset_manifest.json's own
#               2026-08-13 changelog entry for the full reasoning (debian/
#               mini.iso replacing the old separately-fetched linux/initrd.gz
#               pair). Added --refresh (forces every fetch, bypassing the
#               skip-if-already-present check) and p7zip to install_deps().
#               Same "reasoned, not yet executed on real macOS" caveat as
#               the rest of this file.
#   2026-07-27  Initial file. Ported from setup-workstation-linux.sh (live-
#               tested same day) -- Homebrew instead of apt, full §11.1
#               tool table instead of the Linux subset (VMware Fusion has
#               no Linux equivalent), `shasum -a 256` instead of
#               `sha256sum`. Fetch logic itself unchanged from the proven
#               Linux version.
#   2026-08-08  Added install_workstation_tools() (job 2, fyrtaarn) -- ported
#               from setup-workstation-linux.sh, sha256sum -> sha256_of()
#               like the rest of this file. Also handles /usr/local/bin's
#               inconsistent ownership across Intel/Apple Silicon Homebrew
#               installs (detects writability, uses sudo only if needed)
#               rather than assuming either way -- a real macOS-specific
#               difference from the Linux version, same "reasoned, not yet
#               executed on real macOS" caveat as the rest of this file.
# ==============================================================================

set -euo pipefail

# -- Paths --------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MANIFEST="${REPO_ROOT}/benarbejde/asset_manifest.json"
WEB_DIR="${REPO_ROOT}/bootstrap/web"
CACHE_DIR="${REPO_ROOT}/.cache/bootstrap_asset_fetch"

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [--deps-only] [--assets-only] [--refresh] [-h|--help]

  --deps-only    Install/confirm Homebrew-based dependencies only, skip asset fetch.
  --assets-only  Fetch bootstrap/web/ assets only, skip dependency install.
  --refresh      Force re-fetch every asset/archive, even if its dest file(s) already exist.
  -h, --help     Show this help and exit.

With no arguments, does both: deps + assets. See this file's own header comment for full detail.
EOF
}

DO_DEPS=true
DO_ASSETS=true
FORCE_REFRESH=false
for arg in "$@"; do
  case "$arg" in
    --deps-only)   DO_ASSETS=false ;;
    --assets-only) DO_DEPS=false ;;
    --refresh)     FORCE_REFRESH=true ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; usage >&2; exit 2 ;;
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
  msg_info "Checking Homebrew-based dependencies..."

  if ! command -v brew >/dev/null 2>&1; then
    msg_info "Homebrew not found -- installing (official install script)."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Apple Silicon Homebrew installs to /opt/homebrew, not /usr/local -- the
    # official installer prints the exact eval line needed but doesn't run
    # it for you in a non-interactive script context.
    if [[ -x /opt/homebrew/bin/brew ]]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
      eval "$(/usr/local/bin/brew shellenv)"
    fi
  fi

  # -- Casks (GUI apps) -- matches docs/ExampleMusic_Beginners_Guide.md §11.1
  # vmware-fusion deliberately NOT here -- see msg_warn below, it can't be scripted any more.
  # Checked via `brew list --cask` first and filtered down to only what's actually missing --
  # Robert's catch, 2026-10-06: calling `brew install --cask` unconditionally on something
  # already installed doesn't fail, but it's not a no-op either -- it prints a full
  # "Warning: Not upgrading X, the latest version is already installed" block every single
  # re-run, for every package, which is real noise on an idempotent "safe to re-run" script.
  local all_casks=(
    iterm2 keepassxc wireshark sublime-text shottr zettlr utm google-chrome
    mucommander vlc xquartz adobe-acrobat-reader
  )
  # Counted separately rather than relying on ${#missing_casks[@]} under `set -u` --
  # macOS's stock bash 3.2 (this file's own stated target) has a known bug where
  # expanding an empty array under nounset throws "unbound variable", fixed only in
  # bash 4.4+. Branching on a plain integer sidesteps the question entirely: by the
  # time "${missing_casks[@]}" is ever expanded below, missing_count already
  # guarantees it's non-empty.
  local missing_casks=()
  local missing_count=0
  local c
  for c in "${all_casks[@]}"; do
    if ! brew list --cask "$c" &>/dev/null; then
      missing_casks+=("$c")
      missing_count=$((missing_count + 1))
    fi
  done
  if [[ $missing_count -gt 0 ]]; then
    brew install --cask "${missing_casks[@]}"
  else
    msg_info "All casks already installed -- skipping."
  fi

  # -- Formulae (CLI tools) --
  # keepassxc (formula, not cask) is a SEPARATE package from the cask above --
  # the cask installs the GUI .app, this formula installs keepassxc-cli.
  # Both are required; this is not a duplicate. See §11.1's own table.
  # NOTE: midnight-commander is the real formula name -- `mc` is just the binary
  # it installs, `brew install mc` fails. Confirmed directly against
  # formulae.brew.sh before writing this, same mistake class as vmware-fusion
  # below and virt-viewer's own removal (see 2026-10-06 changelog entry).
  # Same check-first-and-filter treatment as the casks above, same reason.
  local all_formulae=(
    git git-lfs jq unzip p7zip ansible keepassxc ipcalc wireguard-tools
    midnight-commander htop minicom fastfetch tree wget w3m links tmux
    zsh-autocomplete zsh-autosuggestions zsh-completions zsh-syntax-highlighting
  )
  local missing_formulae=()
  local missing_formula_count=0
  local f
  for f in "${all_formulae[@]}"; do
    if ! brew list --formula "$f" &>/dev/null; then
      missing_formulae+=("$f")
      missing_formula_count=$((missing_formula_count + 1))
    fi
  done
  if [[ $missing_formula_count -gt 0 ]]; then
    brew install "${missing_formulae[@]}"
  else
    msg_info "All formulae already installed -- skipping."
  fi

  # sshpass is deliberately excluded from homebrew-core (Homebrew's own stated
  # policy: it makes scripted password-based SSH too easy to misuse) -- needs a
  # third-party tap. perkons/homebrew-sshpass confirmed still actively
  # maintained; hudochenkov/homebrew-sshpass (the other commonly-cited one) was
  # archived by its own owner in 2020 and is not used here for that reason.
  # Both the tap and the install are check-first -- re-tapping an already-tapped
  # repo re-prints the same "taps are not trusted" advisory every run otherwise.
  if ! brew tap | grep -qx "perkons/sshpass"; then
    brew tap perkons/sshpass
  fi
  brew list --formula sshpass &>/dev/null || brew install sshpass

  # PowerShell Core -- a FORMULA, not a cask. `brew install --cask powershell`
  # (what every older guide says) was deprecated and disabled 2026-09-01 --
  # fails macOS Gatekeeper. The homebrew/tap/powershell-lts tap that superseded
  # it is now ALSO dead (same confusion shows up across search results). Current
  # reality, confirmed directly against formulae.brew.sh: PowerShell is
  # published straight to homebrew-core now, plain `brew install powershell`
  # (7.6.6 at last check). Third time today this exact mistake class has
  # surfaced (vmware-fusion, virt-viewer, now this) -- always verify the
  # package/cask split against the real source, never assume either way.
  brew list --formula powershell &>/dev/null || brew install powershell

  git lfs install

  msg_ok "Dependencies installed/confirmed: iTerm2, KeePassXC (GUI + CLI), Wireshark," \
         "Sublime Text, Shottr, Zettlr, UTM, Google Chrome, muCommander, VLC, XQuartz," \
         "Adobe Acrobat Reader, git, git-lfs, jq, unzip, p7zip (7z, for .iso archives[] entries)," \
         "ansible, ipcalc, wireguard-tools, mc, htop, minicom, fastfetch, tree, wget, w3m, links," \
         "tmux, zsh-autocomplete, zsh-autosuggestions, zsh-completions, zsh-syntax-highlighting," \
         "sshpass (via perkons/homebrew-sshpass tap), PowerShell Core (pwsh)."
  msg_info "OpenSSH is pre-installed on macOS -- nothing to do."
  msg_info "curl and whois are also pre-installed on macOS -- nothing to do for either."
  msg_warn "VMware Fusion can no longer be installed via Homebrew -- its cask was disabled" \
           "2025-06-23 because Broadcom now gates the download behind an authenticated account," \
           "which a cask can't automate. Download manually (free personal/commercial use):" \
           "https://support.broadcom.com/group/ecx/free-downloads -- My Downloads > Free" \
           "Downloads > VMware Fusion. See docs/ExampleMusic_Beginners_Guide.md §11.4."
  msg_warn "virt-viewer is NOT available in official Homebrew either (confirmed -- this was a" \
           "pre-existing bug in this script, same mistake class as vmware-fusion, found while" \
           "fixing that) -- only via third-party taps (e.g. vanhecke/virt-manager). Not installed" \
           "here; Robert's call 2026-10-06 was to skip the tap rather than add it. Use the" \
           "Proxmox web UI's own noVNC/SPICE console instead, or add the tap by hand if you" \
           "specifically need a native SPICE client."
  msg_info "WinSCP has no macOS build at all (Windows-only) -- use the built-in scp/sftp CLI," \
           "or 'brew install --cask filezilla'/'cyberduck' if a GUI SFTP client is wanted."
}

# ==============================================================================
# 2. Asset fetch -- three source_type handlers, matching
#    benarbejde/asset_manifest.json's own header exactly. Logic identical to
#    setup-workstation-linux.sh except sha256sum -> shasum -a 256 (macOS has
#    no sha256sum by default at all).
# ==============================================================================

sha256_of() {
  shasum -a 256 "$1" | cut -d' ' -f1
}

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
  actual_hash="$(sha256_of "$full_dest")"
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
  actual_hash="$(sha256_of "$full_dest")"
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
  local pair dest
  for pair in "$@"; do
    dest="${pair#*|}"
    [[ -f "${WEB_DIR}/${dest}" ]] || any_missing=true
  done
  if [[ "$FORCE_REFRESH" == "false" && "$any_missing" == "false" ]]; then
    return 0
  fi

  # SourceForge (and some other hosts) serve real download links ending in a
  # trailing /download segment, not a filename -- strip it before deriving a
  # local filename. The ACTUAL curl request below still uses the real,
  # unmodified $url -- SourceForge genuinely needs that suffix to serve the
  # file at all, stripping it there would break the real download.
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
    actual_hash="$(sha256_of "$archive_path_local")"
    if [[ "$actual_hash" != "$expected_hash" ]]; then
      msg_error "  CHECKSUM MISMATCH for ${archive_filename}: expected ${expected_hash}, got ${actual_hash}"
      rm -f "$archive_path_local"
      return 1
    fi
  fi

  mkdir -p "$extract_dir"
  # .zip (unzip) and .iso (7z -- Homebrew's p7zip formula, reads ISO9660
  # natively, same as it reads zip/tar/rar/etc) are the two archive types
  # this repo's manifest currently uses. See benarbejde/asset_manifest.json's
  # own _readme note for why .iso was added 2026-08-13 (debian/ mini.iso).
  case "$archive_filename" in
    *.iso) 7z x -y -o"${extract_dir}" "$archive_path_local" >/dev/null ;;
    *.zip) unzip -q -o "$archive_path_local" -d "$extract_dir" ;;
    *) msg_error "  Don't know how to extract ${archive_filename} (not .zip or .iso)"; return 1 ;;
  esac

  for pair in "$@"; do
    local archive_path="${pair%|*}"
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
#    see that file's own _readme note for the full reasoning). Logic
#    identical to setup-workstation-linux.sh except sha256sum -> sha256_of().
# ==============================================================================
# Deliberately NOT the same "skip if file already exists" idempotency as
# fetch_github_release() above -- these are pinned-version tools a harness
# check nudges Robert to bump over time (check_workstation_tool_versions.py),
# and a bumped pin needs to actually take effect on the next run without a
# manual `rm` first. Verifies the INSTALLED binary's checksum against the
# manifest's pinned tag/asset every run and only reinstalls on mismatch.
#
# 2026-09-26: openrsat's darwin-* assets are real .dmg disk images, not raw
# executables like every entry before it (fyrtaarn) -- installing means
# mounting, copying the .app bundle to /Applications, and unmounting, not a
# plain `install -m 0755`. Branch on the asset filename's own extension
# rather than adding a new manifest field -- same reasoning as the Linux
# script's .deb branch (see that file's own 2026-09-26 comment). Checked
# live before writing this: OpenRSAT's own Info.plist hardcodes
# CFBundleShortVersionString to "0.0.0" regardless of the real release
# version, so unlike Linux's dpkg-version check, this can only be an
# existence check -- a genuine upstream limitation, not a gap worth closing
# by hashing the whole .app bundle on every run.
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
  goos="darwin"
  case "$(uname -m)" in
    x86_64) goarch="amd64" ;;
    arm64)  goarch="arm64" ;;
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
    local is_dmg=false
    [[ "$asset_name" == *.dmg ]] && is_dmg=true

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

    if $is_dmg; then
      # No pinned-version signal available -- OpenRSAT's own Info.plist
      # hardcodes CFBundleShortVersionString to "0.0.0" regardless of the
      # real release version (confirmed live, 2026-09-26), so this can only
      # be an existence check, not the version-drift check the raw-binary
      # and .deb paths both get. Bundle name is discovered from the mounted
      # volume rather than assumed, in case a future .dmg entry's app name
      # doesn't match its manifest "name" field's casing.
      local existing_app
      existing_app="$(find /Applications -maxdepth 1 -iname "*${name}*.app" 2>/dev/null | head -1)"
      if [[ -n "$existing_app" ]]; then
        msg_ok "  ${name} already installed (${existing_app}) -- pinned-version drift can't be detected for this tool, see comment above."
        continue
      fi
    elif [[ -f "$install_path" ]]; then
      local current_hash
      current_hash="$(sha256_of "$install_path")"
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
    actual_hash="$(sha256_of "$tmp_path")"
    if [[ "$actual_hash" != "$expected_hash" ]]; then
      msg_error "  CHECKSUM MISMATCH for ${name}: expected ${expected_hash}, got ${actual_hash}"
      rm -f "$tmp_path"
      continue
    fi

    if $is_dmg; then
      local mount_point app_path
      mount_point="$(mktemp -d)"
      hdiutil attach "$tmp_path" -mountpoint "$mount_point" -nobrowse -quiet
      app_path="$(find "$mount_point" -maxdepth 1 -iname '*.app' | head -1)"
      if [[ -z "$app_path" ]]; then
        msg_error "  No .app bundle found in ${asset_name} -- skipping install."
        hdiutil detach "$mount_point" -quiet || true
        rm -f "$tmp_path"
        rmdir "$mount_point" 2>/dev/null || true
        continue
      fi
      cp -R "$app_path" /Applications/
      hdiutil detach "$mount_point" -quiet
      rmdir "$mount_point" 2>/dev/null || true
      rm -f "$tmp_path"
      msg_ok "  ${name} installed to /Applications/$(basename "$app_path") (${tag}, sha256:${actual_hash})"
    else
      # /usr/local/bin's ownership is inconsistent across Macs, unlike Linux
      # (always root-owned there): Homebrew on Intel chowns it to the current
      # user so `brew install` never needs sudo; Homebrew on Apple Silicon
      # uses /opt/homebrew instead and leaves /usr/local/bin root-owned.
      # Detect rather than assume either way.
      local use_sudo=""
      if [[ ! -d "$install_dir" ]] || [[ ! -w "$install_dir" ]]; then
        use_sudo="sudo"
      fi
      $use_sudo mkdir -p "$install_dir"
      $use_sudo install -m 0755 "$tmp_path" "$install_path"
      rm -f "$tmp_path"
      msg_ok "  ${name} installed to ${install_path} (${tag}, sha256:${actual_hash})"
    fi
  done < <(jq -r '.workstation_tools[] | [.name, .repo, .tag] | @tsv' "$MANIFEST")
}

# Same module set as ansible/playbooks/windows_bootstrap/tasks/ps7_setup.yml's
# Stage 20 (AllUsers scope there; this is a single-user machine, so plain
# CurrentUser scope here is the equivalent, not a deliberate difference).
# PSWindowsUpdate is Windows-only (wraps Windows Update's own COM APIs) -- left
# in the list anyway rather than special-cased out, because Install-Module's
# existing -ErrorAction SilentlyContinue already degrades it to a harmless no-op
# on a platform it doesn't support; same mechanism, no new logic needed.
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

# Example Music Limited -- full PS7 profile parity with
# ansible/playbooks/windows_bootstrap/tasks/ps7_setup.yml's Stage 22 (PSReadLine
# Emacs mode + Solarized Parameter/Operator colours, Terminal-Icons,
# CompletionPredictor, NerdFonts, and the nodeinfo.json MOTD banner -- see that
# file's own 2026-10-03/2026-10-04 changelog entries for the full history of
# each). Robert's ask, 2026-10-06: "deploy that profile and those plugins...
# we worked on before" -- this is the same content, not a re-derived summary of
# it, copied from the one real source (ps7_setup.yml) rather than retyped by
# hand. Plus the ls/Get-ChildItem compatibility toggle below, which is
# deliberately NOT in the Windows version (Windows already aliases ls natively,
# see that file's own 2026-10-03 entry) -- this macOS-only addition predates
# today's change and is kept as-is.
#
# One real caveat, not swept under the rug: the MOTD banner reads
# /etc/example-music/nodeinfo.json (the $IsWindows/$IsLinux branch's "else" --
# $IsMacOS falls into it too, same path). That file is written by Ansible to
# MANAGED hosts it provisions (DCs, firewalls, Proxmox nodes, etc.) -- never to
# an engineer's own laptop. So on a real Mac this banner block will find
# nothing there and silently print nothing, same graceful no-op already built
# in for "ran mid-bootstrap before nodeinfo.json exists yet." Not an error,
# just worth knowing the banner itself has nothing to show here currently.
configure_pwsh_profile() {
  if ! command -v pwsh &>/dev/null; then
    msg_info "pwsh not found on PATH -- skipping PowerShell Core profile configuration (not installed by this script; install it by hand first if you want this)."
    return
  fi

  # Bare $PROFILE resolves to CurrentUserCurrentHost (Microsoft.PowerShell_profile.ps1),
  # which is per-HOST -- only the raw pwsh console, not VS Code's integrated terminal or
  # any other PS7 host. $PROFILE.CurrentUserAllHosts (profile.ps1) is the broader, actually-
  # intended scope -- confirmed live, 2026-10-06: Jamie's run wrote to
  # Microsoft.PowerShell_profile.ps1, not profile.ps1, exactly this bug.
  local profile_path
  profile_path="$(pwsh -NoLogo -NoProfile -Command '$PROFILE.CurrentUserAllHosts')"
  local profile_dir
  profile_dir="$(dirname "$profile_path")"

  # Clean up a stray file from the bare-$PROFILE bug above, if a previous run of
  # THIS script (not a Jamie customisation -- only removed if it carries one of
  # our own markers) already wrote the wrong-scope CurrentUserCurrentHost file.
  local old_wrong_scope_path
  old_wrong_scope_path="$(pwsh -NoLogo -NoProfile -Command '$PROFILE.CurrentUserCurrentHost')"
  # "Added by bootstrap/setup-workstation-macos.sh" is in both the old (pre-2026-10-06,
  # colour-fix-only) and new content -- catches either version, not just today's.
  if [[ -f "$old_wrong_scope_path" ]] && grep -qF "Added by bootstrap/setup-workstation-macos.sh" "$old_wrong_scope_path" 2>/dev/null; then
    rm -f "$old_wrong_scope_path"
    msg_info "Removed stray profile at ${old_wrong_scope_path} (wrong-scope CurrentUserCurrentHost -- a previous run's bug, fixed 2026-10-06; this script now correctly uses CurrentUserAllHosts instead)."
  fi

  # New, more specific marker than the old "PSReadLine Parameter/Operator colour
  # fix" one -- deliberate: a machine that already ran the OLD, narrower version
  # of this profile won't match this marker, so it gets the new block appended
  # too (a harmless, one-time redundant PSReadLine colour-set, not a conflict --
  # not worth a full old-block-removal mechanism for a one-time transition).
  local marker="Example Music Limited -- PS7 profile (PSReadLine/Terminal-Icons/CompletionPredictor/NerdFonts/MOTD)"

  mkdir -p "$profile_dir"

  if [[ -f "$profile_path" ]] && grep -qF "$marker" "$profile_path"; then
    msg_info "${profile_path}: PS7 profile already present, skipping."
    return
  fi

  cat >> "$profile_path" <<'EOF'

# Example Music Limited -- PS7 profile (PSReadLine/Terminal-Icons/CompletionPredictor/NerdFonts/MOTD)
# Added by bootstrap/setup-workstation-macos.sh -- same content as
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

# MOTD banner -- nodeinfo.json. On a real workstation this is usually absent
# (nodeinfo.json is written by Ansible to MANAGED hosts it provisions, not to
# an engineer's own laptop) -- this silently prints nothing in that case, same
# as the "ran before nodeinfo.json exists yet" case on a managed host.
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
# exists to conflict with). On Linux/macOS (this is the macOS case -- iTerm2's own
# Solarized scheme is where this was first noticed), PowerShell deliberately does
# NOT create that alias -- ls resolves to the real native binary instead, by
# design, specifically so it doesn't shadow a pre-existing Unix tool.
# Terminal-Icons only decorates Get-ChildItem's own output, so ls never shows
# icons here unless you opt in. OFF by default -- call Enable-LsCompatibilityMode
# to turn it on for this session, Disable-LsCompatibilityMode to revert.
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
  $DO_ASSETS && fetch_assets
  msg_ok "Done."
}

main
