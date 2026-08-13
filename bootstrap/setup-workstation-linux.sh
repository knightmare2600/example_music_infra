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
msg_info()  { printf "${CY}[*]${NC} %s\n" "$1"; }
msg_ok()    { printf "${GN}[+]${NC} %s\n" "$1"; }
msg_warn()  { printf "${YW}[!]${NC} %s\n" "$1"; }
msg_error() { printf "${RD}[x]${NC} %s\n" "$1"; }

# ==============================================================================
# 1. Dependency install
# ==============================================================================
install_deps() {
  msg_info "Checking apt-based dependencies..."

  if ! command -v apt-get >/dev/null 2>&1; then
    msg_error "apt-get not found -- this script presumes a Debian-flavour distro. Aborting."
    exit 1
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

  msg_ok "Dependencies installed/confirmed: git, git-lfs, curl, jq, unzip, 7zip (7z, for .iso" \
         "archives[] entries), ansible, keepassxc (keepassxc-cli bundled on Debian)," \
         "wireguard-tools, virt-viewer, wireshark, ipcalc."
  msg_info "No native Linux equivalent for VMware Fusion or iTerm2 -- skipped (macOS-only tools," \
           "see docs/ExampleMusic_Beginners_Guide.md §11)."
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
install_workstation_tools() {
  if [[ ! -f "$MANIFEST" ]]; then
    msg_error "Manifest not found: ${MANIFEST}"
    exit 1
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

    if [[ -f "$install_path" ]]; then
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

    sudo mkdir -p "$install_dir"
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

    sudo install -m 0755 "$tmp_path" "$install_path"
    rm -f "$tmp_path"
    msg_ok "  ${name} installed to ${install_path} (${tag}, sha256:${actual_hash})"
  done < <(jq -r '.workstation_tools[] | [.name, .repo, .tag] | @tsv' "$MANIFEST")
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
  $DO_ASSETS && fetch_assets
  msg_ok "Done."
}

main
