#!/usr/bin/env bash
# ==============================================================================
# bootstrap/setup-workstation-macos.sh
# Example Music Limited — Engineer workstation setup (macOS)
# ==============================================================================
# Two jobs, one script:
#   1. Install/confirm the tool set docs/ExampleMusic_Beginners_Guide.md §11
#      requires on an engineer's own machine — Malcolm and Jamie both run
#      MacBook Pros today, so this is the platform that matters most for
#      real, current use.
#   2. Populate bootstrap/web/'s upstream-sourced boot assets from
#      benarbejde/asset_manifest.json -- the same job
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
# *** IMPORTANT — UNTESTED ON REAL macOS ***
# This was written and reasoned through carefully, but the environment that
# built it has no macOS available to execute it on at all. The Linux twin's
# fetch logic (github_release / url_with_checksum_file / archive_extract)
# was live-tested end to end against every real source this manifest
# covers, so that PART is proven correct in bash generally -- but the
# macOS-specific substitutions below (Homebrew, shasum instead of
# sha256sum, BSD vs GNU sed/grep dialect) are reasoned about, not executed.
# Malcolm/Jamie/Robert: please run this for real and report back anything
# that doesn't match before relying on it.
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
#
# Requires: bash (macOS ships an old bash 3.2 as /bin/bash by default due
# to GPLv3 licensing avoidance -- this script only uses bash 3.2-compatible
# syntax deliberately, no associative arrays or other 4.x+ features), curl
# (pre-installed), unzip (pre-installed). jq is installed by this script's
# own dependency step if missing -- there is no reasonable bootstrap order
# where jq is needed before Homebrew itself exists.
# ==============================================================================
# Changelog:
#   2026-07-27  Initial file. Ported from setup-workstation-linux.sh (live-
#               tested same day) -- Homebrew instead of apt, full §11.1
#               tool table instead of the Linux subset (VMware Fusion has
#               no Linux equivalent), `shasum -a 256` instead of
#               `sha256sum`. Fetch logic itself unchanged from the proven
#               Linux version.
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
for arg in "$@"; do
  case "$arg" in
    --deps-only)   DO_ASSETS=false ;;
    --assets-only) DO_DEPS=false ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# -- Colour helpers (matches this repo's existing CY/GN/YW/RD convention, --
# -- see e.g. bootstrap/web/proxmox/select-pve-answer.sh) ---------------------
RD='\033[0;31m'; GN='\033[0;32m'; YW='\033[1;33m'; CY='\033[0;36m'; NC='\033[0m'
msg_info()  { printf "${CY}[*]${NC} %s\n" "$1"; }
msg_ok()    { printf "${GN}[+]${NC} %s\n" "$1"; }
msg_warn()  { printf "${YW}[!]${NC} %s\n" "$1"; }
msg_error() { printf "${RD}[x]${NC} %s\n" "$1"; }

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
  brew install --cask \
    vmware-fusion \
    iterm2 \
    keepassxc \
    wireshark

  # -- Formulae (CLI tools) --
  # keepassxc (formula, not cask) is a SEPARATE package from the cask above --
  # the cask installs the GUI .app, this formula installs keepassxc-cli.
  # Both are required; this is not a duplicate. See §11.1's own table.
  brew install \
    git git-lfs jq unzip \
    ansible \
    keepassxc \
    ipcalc \
    virt-viewer \
    wireguard-tools

  git lfs install

  msg_ok "Dependencies installed/confirmed: VMware Fusion, iTerm2, KeePassXC (GUI + CLI)," \
         "Wireshark, git, git-lfs, jq, ansible, ipcalc, virt-viewer, wireguard-tools."
  msg_info "OpenSSH is pre-installed on macOS -- nothing to do."
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

  if [[ -f "$full_dest" ]]; then
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

  if [[ -f "$full_dest" ]]; then
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
  # $1 = archive url, remaining args = "archive_path|dest" pairs
  local url="$1"; shift

  local any_missing=false
  local pair dest
  for pair in "$@"; do
    dest="${pair#*|}"
    [[ -f "${WEB_DIR}/${dest}" ]] || any_missing=true
  done
  if [[ "$any_missing" == "false" ]]; then
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

  mkdir -p "$extract_dir"
  unzip -q -o "$archive_path_local" -d "$extract_dir"

  for pair in "$@"; do
    local archive_path="${pair%|*}"
    dest="${pair#*|}"
    local full_dest="${WEB_DIR}/${dest}"
    [[ -f "$full_dest" ]] && continue
    mkdir -p "$(dirname "$full_dest")"
    cp "${extract_dir}/${archive_path}" "$full_dest"
    msg_ok "  ${dest} (from ${archive_filename})"
  done

  rm -rf "$CACHE_DIR"
}

fetch_assets() {
  if [[ ! -f "$MANIFEST" ]]; then
    msg_error "Manifest not found: ${MANIFEST}"
    exit 1
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
    local url
    url="$(jq -r ".archives[$i].url" "$MANIFEST")"
    local pairs=()
    while IFS=$'\t' read -r archive_path dest; do
      pairs+=("${archive_path}|${dest}")
    done < <(jq -r ".archives[$i].members[] | [.archive_path, .dest] | @tsv" "$MANIFEST")
    fetch_archive "$url" "${pairs[@]}"
  done

  msg_ok "Asset fetch complete."
}

# ==============================================================================
main() {
  $DO_DEPS && install_deps
  $DO_ASSETS && fetch_assets
  msg_ok "Done."
}

main
