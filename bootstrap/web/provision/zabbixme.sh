#!/usr/bin/env bash
# ==============================================================================
# Example Music Limited — Zabbix Server Bootstrap Script
# EXAZBXCLD001 (or any site's Zabbix monitoring server — CLD only for now)
#
# Mirrors the style and structure of rudderme.sh/ansibleme.sh/firewallme.sh:
#   - Interactive, idempotent, run as root
#   - Site-code-driven (subnet/inventory auto-derived from sites.csv)
#   - Prompts for hostname and static IP
#   - Installs and configures Zabbix server (MariaDB backend, Apache frontend)
#   - Populates auto-registration group + IP-restricted API access from
#     sites.csv + begyndelse.json (VRK/FRD/every site subnet)
#   - Sentinel file + dynamic MOTD
#
# SCOPE (Robert, 2026-09-01): this script covers the Zabbix SERVER only.
# Agent deployment (Linux via Ansible, Windows via Salt) is explicitly
# deferred to separate follow-up work — see the two TODO markers below
# (EnableRemoteCommands / curl+wget-on-every-device) for exactly what's
# NOT this script's job. "Not an exhaustive list" was Robert's own framing
# of his brief — treat every section below as a first cut, not gospel;
# several judgement calls are flagged explicitly where made.
#
# BREAK-GLASS TOOL, same posture as rudderme.sh/bindme.sh/firewallme.sh: will
# be backported to ansible/playbooks/zabbix/ once proven live. Self-contained
# by design — manual wget of sites.csv/devices.csv/begyndelse.json from the
# provisioning server is the expected, supported path here, not a shortcut
# to be "fixed" later.
#
# -------------------------------------------------------------------------------------------------
# Version history
# -------------------------------------------------------------------------------------------------
# v1.0.0  2026-09-01  Initial release. Covers: hostname/IP setup, OS/codename detection,
#                     Zabbix 8.0 repo + zabbix-server-mysql/zabbix-frontend-php/apache install,
#                     MariaDB DB+user creation (generated password, not hand-typed), DB schema
#                     import (auto-detects old create.sql.gz vs newer zabbix-sql-scripts split
#                     layout — could not verify which one 8.0 actually ships from this sandbox,
#                     see the live Zabbix-version verification note below), zabbix.conf.php
#                     written directly (skips the browser setup.php wizard), Apache vhost with
#                     ServerName zabbix.<domain> (parameterised from begyndelse.json) + a genuine
#                     301 redirect from "/" to the frontend, monitoring toolkit (fping/nmap/snmp/
#                     snmp-mibs-downloader/tcpdump/traceroute/whois), UFW allowing the Zabbix
#                     trapper port (10051) only from VRK+FRD+every site subnet (sites.csv-driven,
#                     same pattern as rudderme.sh's own allowed-networks section), API-level
#                     access restriction on api_jsonrpc.php to the same subnet list, Admin
#                     password rotated off the Zabbix default via the API (generated, printed
#                     once at the end — never left as Admin/zabbix), "auto-registration" host
#                     group + autoregistration action created via the API, DB housekeeping
#                     tightened (shorter default retention than Zabbix's own shipped defaults,
#                     Robert: "I HATE when the database grows to a ridiculous size") plus a
#                     weekly systemd timer running mysqlcheck --optimize against the zabbix DB —
#                     MariaDB's InnoDB engine does not reclaim disk space from the housekeeper's
#                     own DELETEs without this, which is the actual mechanism behind Robert's
#                     complaint, not a housekeeper settings problem per se. Native MySQL/MariaDB
#                     table PARTITIONING (Zabbix's own recommended approach for genuinely large
#                     history/trends tables) is NOT implemented here — flagged as a real, higher-
#                     effort option to come back to if the timer-based OPTIMIZE approach turns
#                     out not to be enough, not attempted blind in an unattended script.
#
#                     ZABBIX VERSION — confirmed live against the real repo.zabbix.com from this
#                     session (not guessed): Robert's brief said "LTS 7.0" in point 1 but then
#                     gave a corrected URL under /zabbix/8.0/release/debian/ at the end, and
#                     confirmed 8.0 when asked directly. Checked repo.zabbix.com directly: 8.0 is
#                     a real, current top-level version (sits after 7.0/7.2/7.4 in the version
#                     listing, consistent with Zabbix's real ~2-year LTS cadence), and the
#                     zabbix-release pointer package's real filename/apt-source format was
#                     confirmed by downloading and inspecting it: the .deb is
#                     zabbix-release_latest_8.0+debian<N>_all.deb (N = lsb_release -s -r, e.g.
#                     "13" for trixie — matches Robert's own hint), and it installs a DEB822
#                     .sources file using Suites: <codename> (e.g. "trixie" — matches Robert's
#                     other hint, lsb_release -c -s). HOWEVER: browsing
#                     repo.zabbix.com/zabbix/8.0/release/debian/dists/trixie/main/ directly from
#                     this session showed only binary-all/ (containing zabbix-release itself) and
#                     source/ — no binary-amd64/ directory, i.e. no zabbix-server-mysql/
#                     zabbix-frontend-php indexed there as of this check. The SAME check against
#                     bookworm, and against every other recent version (6.0/6.4/7.0/7.2/7.4) back
#                     to 5.0, showed the identical pattern — which reads as a sandbox/proxy
#                     limitation in THIS environment's outbound network rather than a genuine
#                     "Zabbix hasn't shipped real .debs" finding (6.0/7.0 are definitely,
#                     unambiguously real-world GA and installable). Not something this session
#                     could fully resolve either way. Section 8 below (repo + package install)
#                     therefore includes an explicit `apt-cache policy zabbix-server-mysql` sanity
#                     check straight after `apt-get update`, before anything else runs, so a
#                     genuinely missing package fails fast with a clear message instead of
#                     halfway through a long install. Treat this whole area as UNVERIFIED until
#                     confirmed on a real run — flagging per this repo's own "frame as
#                     verification, not fix claims" convention rather than asserting it works.
#
#                     ROLE CODE / IP — EXAZBXCLD001 follows the same "single instance, CLD only"
#                     convention as RUD (.12)/RMM (.14)/SLT (.22) in role_codes.csv, but ZBX is
#                     NOT yet a real row in role_codes.csv/devices.csv, and no CLD octet has been
#                     assigned — this script deliberately does NOT hardcode a "correct" default
#                     IP the way rudderme.sh does for RUD's already-known .12, since there isn't
#                     one yet. Free CLD octets as of this session (devices.csv doesn't use them):
#                     .15, .16, .23, and most of the range above .82 excluding .250. Robert: pick
#                     one and this script's suggested-default can be updated, or just answer the
#                     prompt manually each run until role_codes.csv/devices.csv get a real ZBX row.
# v1.1.0  2026-09-01  Robert: "8.0 folders are all messed up, switch it out for 7.0 -- Zabbix
#                     flexibility means you can literally swap 8.0 for 7.0", and gave the real
#                     product package URL (https://repo.zabbix.com/zabbix/7.0/debian/pool/main/z/
#                     zabbix/) that v1.0.0's own version-history note above was speculating about.
#                     Checked live: this fully explains the v1.0.0 finding rather than it being a
#                     sandbox/proxy artefact after all -- 7.0 (and every older version, matching
#                     the classic layout the original 2019-era reference script used) publishes
#                     BOTH zabbix-release and the real product packages under a FLAT
#                     zabbix/<version>/debian/pool/... path with NO "/release/" segment at all
#                     (confirmed: repo.zabbix.com/zabbix/7.0/release/debian/ is a genuine 404).
#                     8.0 is different -- it has a real, live "/release/" tree (the zabbix-release
#                     pointer package installs fine from it, confirmed in v1.0.0) but that tree is
#                     still sparsely populated (no binary-amd64/ for any Debian release, checked
#                     directly), which is apparently a newer, not-yet-fully-populated URL scheme
#                     Zabbix is transitioning to for 8.0, not a sandbox limitation as v1.0.0
#                     guessed. Downloaded and inspected the real 7.0 zabbix-release package to
#                     confirm its .sources content before changing anything here (not assumed to
#                     match 8.0's): single file /etc/apt/sources.list.d/zabbix.sources (not the
#                     three-file split 8.0 uses), URIs: https://repo.zabbix.com/zabbix/7.0/debian,
#                     Suites: trixie, plus a pre-disabled (Enabled: no) 6.5 entry -- no
#                     zabbix-unstable.sources at all for 7.0, so Section 8's "disable unstable"
#                     step is now dead code for this version (left in place, harmless -- already
#                     conditional on the file existing, silently no-ops now instead of doing
#                     something). ZABBIX_MAJOR changed 8.0 -> 7.0; the release-package download
#                     URL construction in Section 8 changed to the flat (no "/release/") path;
#                     removed the now-provably-wrong "no binary-amd64 for ANY version" theory from
#                     being treated as settled anywhere in this file. Confirmed real, current
#                     package names for 7.0/debian13 directly from the pool listing while here:
#                     zabbix-server-mysql, zabbix-frontend-php, zabbix-apache-conf,
#                     zabbix-sql-scripts, zabbix-agent (classic, NOT zabbix-agent2 -- Robert was
#                     explicit: "agent is agent not agent2, I am not using agent2") all exist for
#                     debian13 up to at least 7.0.30 -- Section 8's package list already used
#                     zabbix-agent, not agent2, so no change needed there. Also removed a dead,
#                     unused ZBX_PKGS array left over from drafting (the real install list is
#                     INSTALLABLE_ZBX_PKGS, built by checking each candidate individually) --
#                     included a guessed php8.2-mysql entry that was never actually referenced
#                     anywhere and isn't needed (apt resolves zabbix-frontend-php's own PHP
#                     dependency automatically).
# v1.2.0  2026-09-02  Robert: pointed at repo.zabbix.com/zabbix/7.0/debian-arm64/pool/main/z/
#                     zabbix-release/ and asked to sha256sum the arm64 "_all.deb" against the
#                     amd64 one this script already used, to confirm whether "Architecture: all"
#                     really means one universal file. It doesn't: downloaded both, hashes and
#                     file sizes differ. Extracted and diffed both -- the ONLY difference is the
#                     embedded zabbix.sources file's URI (repo.zabbix.com/zabbix/7.0/debian vs
#                     .../debian-arm64), everything else (keyring, changelog, copyright,
#                     zabbix-tools.sources) is byte-identical. So "all" describes the .deb
#                     PACKAGE FORMAT (no compiled binaries inside, installs fine on any dpkg
#                     regardless of host CPU), not the repo TREE it configures -- picking the
#                     wrong tree silently points apt at the wrong architecture's actual product
#                     packages. This script was hardcoded to the amd64 ("debian") tree
#                     unconditionally -- a real bug on an arm64 box, not previously exercised
#                     since every live test so far (firewall/windows_bootstrap work earlier this
#                     session) has been amd64. Confirmed live that debian-arm64 genuinely
#                     publishes real arm64-native zabbix-server-mysql builds for debian13, not
#                     just a placeholder tree. Fixed: Section 4 now runs `dpkg --print-architecture`
#                     and sets ZBX_DEBIAN_TREE to "debian" (amd64) or "debian-arm64" (arm64), used
#                     throughout Section 8's URL construction instead of the hardcoded "debian"
#                     path segment. Any other architecture dies with a clear message rather than
#                     silently trying the wrong tree.
# v1.3.0  2026-09-02  Robert, live on EXAZABCLD001, two real bugs found on the first genuine
#                     test run:
#                     1) "Failed to restart NetworkManager.service: Unit NetworkManager.service
#                     not found." -- the old Section 3 (Network / Static IP) ran BEFORE the old
#                     Section 5 (Base packages, which is what installs network-manager if
#                     missing) -- on a box that didn't already have NetworkManager, this was
#                     always going to fail. Reordered: OS/codename detection is now Section 3,
#                     base packages (incl. network-manager) is now Section 4, and Network/Static
#                     IP is now Section 5, running after network-manager is guaranteed installed.
#                     Sections 6 onward keep their numbers unchanged. rudderme.sh (this script's
#                     own template) has the IDENTICAL structural bug -- fixed there too the same
#                     day, see its own changelog.
#                     2) Robert was about to type in .22 as the static IP -- the script's
#                     ip_in_use() said "appears free", but .22 is already EXASLTCLD001's
#                     (Salt master) in both cld.ini and devices.csv. ip_in_use() is a live
#                     ping/arping probe only -- it can't see an allocation that isn't currently
#                     answering ICMP. Added an explicit warning comment directly above the IP
#                     prompt (Section 5) and softened the "appears free" success message to make
#                     clear it's a live-probe result, not a devices.csv/cld.ini cross-check --
#                     this script still doesn't (and structurally can't, being a standalone
#                     break-glass script with no inventory access) verify against the real
#                     allocation list itself, so the operator has to.
# v1.4.0  2026-09-02  Robert, live on EXAZABCLD001, second real run: "E: Package
#                     'snmp-mibs-downloader' has no installation candidate" -- confirmed live
#                     against packages.debian.org: the package genuinely exists for trixie, but
#                     lives in Debian's non-free component (MIB file licensing), and this
#                     estate's preseed (bootstrap/web/debian/lvm-*.seed) never enables non-free/
#                     contrib -- a standard Debian default, not a preseed bug. This was bundled
#                     into the single Section 4 BASE_PKGS apt-get call, so this one unavailable
#                     package failed the WHOLE batch -- curl/git/fping/nmap/tcpdump/etc. never
#                     installed either, even though every one of them would have worked fine.
#                     Split into its own best-effort install: enable non-free first (handles
#                     both the DEB822 debian.sources format trixie's installer actually writes
#                     and the classic sources.list format), then install just this one package
#                     on its own -- a failure here warns and continues rather than dying, since
#                     the rest of the script doesn't depend on it.
# v1.5.0  2026-09-02  Robert, live on EXAZABCLD001, third real run: "it didn't error but it just
#                     quit" right after MariaDB installed -- no [ERROR] message, just silently
#                     back at the shell prompt. That's exactly where the first gen_password()
#                     call sits (ZABBIX_DB_PASSWORD). Root cause, reproduced locally before
#                     fixing: classic set -o pipefail trap -- `head -c N` reads exactly N bytes
#                     then closes its input; `tr`, still writing into a closed pipe, gets
#                     SIGPIPE-killed and exits 141; pipefail propagates that as the whole
#                     pipeline's exit status; set -e aborts the script immediately with no
#                     message at all (a SIGPIPE-killed process prints nothing). All three
#                     gen_password() call sites (DB password, frontend session key, Admin API
#                     password) were equally exposed -- the DB password just happened to be the
#                     first one reached. Fixed with `|| true` on the whole pipeline, confirmed
#                     locally afterward that the generated password is still the correct
#                     length/content, not just that the script survives.
# -------------------------------------------------------------------------------------------------

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

# ------------------------------------------------------------------------------
# Colour helpers — identical to ansibleme.sh / rudderme.sh / firewallme.sh
# ------------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'
info()    { echo -e "${CYAN}[*]${NC} $*"; }
success() { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*" >&2; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
section() { echo; echo -e "${WHITE}── $* ──${NC}"; echo; }

# Checks whether an IP is already live on the network (ping + arping fallback)
ip_in_use() {
  local ip="$1"
  if ping -c1 -W1 "$ip" &>/dev/null 2>&1; then
    return 0
  fi
  if command -v arping &>/dev/null; then
    local gw_iface
    gw_iface=$(ip route | awk '/default/{print $5}' | head -1)
    if [[ -n "${gw_iface}" ]] && arping -c1 -W1 -I "${gw_iface}" "$ip" &>/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

# Generates a random alnum-only credential — safe to embed unescaped in SQL,
# shell heredocs, and JSON payloads (no quotes/backslashes/$/backticks to
# fight with), unlike the hand-typed example password in the old reference
# scripts this was ported from.
#
# BUG FIX (2026-09-02, found live on EXAZABCLD001 -- Robert: "it didn't error but it just
# quit" right after MariaDB installed, which is exactly where the first gen_password() call
# sits): classic set -o pipefail trap. `head -c N` reads exactly N bytes then closes its
# input; `tr`, still trying to write into a closed pipe, gets killed by SIGPIPE and exits
# non-zero (141) -- with pipefail active, that becomes the WHOLE pipeline's exit status, and
# under set -e the script aborts immediately with NO error message at all (a SIGPIPE-killed
# process doesn't print anything). Reproduced locally to confirm before fixing: `bash -c 'set
# -euo pipefail; tr -dc A-Za-z0-9 < /dev/urandom | head -c 28' ; echo $?` prints nothing and
# exits 141. `|| true` on the whole pipeline swallows that specific failure (confirmed the
# password still comes out correct length/content) without masking a genuine problem
# elsewhere, since this line does nothing else that could fail. All three call sites (DB
# password, frontend session key, Admin API password) were equally exposed -- the DB password
# was just the first one reached.
gen_password() {
  tr -dc 'A-Za-z0-9' < /dev/urandom | head -c "${1:-28}" || true
}

# ------------------------------------------------------------------------------
# Must run as root
# ------------------------------------------------------------------------------
[[ $EUID -ne 0 ]] && die "Run this script with sudo or as root."

# ------------------------------------------------------------------------------
# Preflight -- ensure /etc/example-music/ + sites.csv + begyndelse.json
# ------------------------------------------------------------------------------
# Same pattern as every other break-glass script (Robert, 2026-08-29) — detects
# which provisioning network this box is on from its own default gateway, and
# fetches whatever's missing before load_sites_csv() (and the begyndelse.json
# lookup further down) ever run. Exits 0, not 1 — this isn't a crash.

PREFLIGHT_DIR="/etc/example-music"
mkdir -p "${PREFLIGHT_DIR}" 2>/dev/null || true

PREFLIGHT_GW=$(ip route 2>/dev/null | awk '/default/ {print $3; exit}')
if [[ "${PREFLIGHT_GW}" == "172.16.124.2" ]]; then
  PREFLIGHT_SERVER="http://172.16.124.1:8000"   # Fredericia Havn
else
  PREFLIGHT_SERVER="http://192.168.139.50"      # Edinburgh / vRACK (default)
fi

preflight_fetch() {
  local filename="$1"
  local dest="${PREFLIGHT_DIR}/${filename}"
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  [[ -f "${dest}" ]] && return 0
  [[ -f "${script_dir}/${filename}" ]] && return 0

  local url="${PREFLIGHT_SERVER}/proxmox/${filename}"
  info "${filename} not found locally -- fetching from ${url} ..."
  if wget -q --tries=1 --timeout=15 -O "${dest}" "${url}" 2>/dev/null && [[ -s "${dest}" ]]; then
    success "Downloaded ${filename} to ${dest}."
    return 0
  fi
  rm -f "${dest}" 2>/dev/null
  return 1
}

PREFLIGHT_MISSING=()
for PREFLIGHT_FILE in sites.csv begyndelse.json; do
  preflight_fetch "${PREFLIGHT_FILE}" || PREFLIGHT_MISSING+=("${PREFLIGHT_FILE}")
done

if [[ ${#PREFLIGHT_MISSING[@]} -gt 0 ]]; then
  warn "Could not obtain: ${PREFLIGHT_MISSING[*]}"
  warn "This box may not be on a known provisioning network (checked gateway"
  warn "'${PREFLIGHT_GW:-<none>}', tried ${PREFLIGHT_SERVER}), or that server isn't"
  warn "reachable right now."
  warn "Place the missing file(s) at ${PREFLIGHT_DIR}/ by hand and re-run, or fix"
  warn "network connectivity first."
  exit 0
fi

# ------------------------------------------------------------------------------
# Site data — loaded from sites.csv (single source of truth)
# ------------------------------------------------------------------------------
declare -A SITE_OCTET SITE_CITY SITE_COUNTRY SITE_ENTITY SITE_DC SITE_FW

load_sites_csv() {
  local csv_path=""

  if [[ -n "${SITES_CSV:-}" && -f "${SITES_CSV}" ]]; then
    csv_path="${SITES_CSV}"
  else
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "${script_dir}/sites.csv" ]]; then
      csv_path="${script_dir}/sites.csv"
    elif [[ -f "/etc/example-music/sites.csv" ]]; then
      csv_path="/etc/example-music/sites.csv"
    fi
  fi

  if [[ -z "${csv_path}" ]]; then
    echo -e "\033[0;31m[ERROR]\033[0m sites.csv not found." >&2
    echo -e "  Looked in: same directory as script, /etc/example-music/sites.csv" >&2
    echo -e "  Set SITES_CSV=/path/to/sites.csv to override." >&2
    exit 1
  fi

  local first=1
  # 17-column header (Site,City,Country,CountryCode,Province,OfficeName,Street,PostalCode,
  # Subnet,Gateway,DC,FW,Landline,Mobile,Timezone,AnsibleRegion,Entity) — same field list every
  # other break-glass script in this repo uses as of the 2026-08-29 fix, including the
  # comma-in-Entity reconstruction via $_rest.
  while IFS=',' read -r site city country cc province officename street postalcode subnet gateway dc fw landline mobile tz ansible_region entity _rest \
      || [[ -n "$site" ]]; do
    [[ "${first}" -eq 1 ]] && { first=0; continue; }
    site="${site// /}"
    [[ -z "${site}" ]] && continue
    [[ -n "${_rest}" ]] && entity="${entity},${_rest}"
    local octet
    octet=$(echo "${subnet}" | awk -F'.' '{print $3}')
    SITE_OCTET["${site}"]="${octet}"
    SITE_CITY["${site}"]="${city}"
    SITE_COUNTRY["${site}"]="${country}"
    SITE_ENTITY["${site}"]="${entity}"
    SITE_DC["${site}"]="${dc}"
    SITE_FW["${site}"]="${fw}"
  done < "${csv_path}"
}

load_sites_csv

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
ZABBIX_MAJOR="7.0"
ZABBIX_ADMIN_USER="Admin"          # Zabbix's own built-in superadmin account name
AUTOREG_GROUP_NAME="auto-registration"
SENTINEL="/etc/.i_am_a_zabbix_server"
DB_CREDS_FILE="/root/.zabbix_db_credentials"
API_CREDS_FILE="/root/.zabbix_api_credentials"

# ------------------------------------------------------------------------------
# Banner
# ------------------------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            Example Music:- Zabbix Server Bootstrap           ║${NC}"
echo -e "${CYAN}║                        zabbixme.sh                           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}  Running on hostname: ${GREEN}$(hostname)${NC}"
echo

# ------------------------------------------------------------------------------
# Section 1 — Site / node identity
# ------------------------------------------------------------------------------
section "1. Node identity"

DETECTED_SITE=""
HOSTNAME_NOW=$(hostname)
if [[ "$HOSTNAME_NOW" =~ ^EXA[A-Z]{3}([A-Z]{3})[0-9]{3}$ ]]; then
  DETECTED_SITE="${BASH_REMATCH[1]}"
fi

echo -e "${CYAN}Known site codes:${NC}"
echo -e "${CYAN}  $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort | tr '\n' ' ')${NC}"
echo

SITE_CODE=""
while true; do
  if [[ -n "$DETECTED_SITE" && -v SITE_OCTET[$DETECTED_SITE] ]]; then
    read -rp "  Site code (detected from hostname: ${DETECTED_SITE}, Enter to accept): " SITE_INPUT
    SITE_INPUT="${SITE_INPUT:-${DETECTED_SITE}}"
  else
    read -rp "  Enter site code for this node (CLD, unless a second Zabbix server is genuinely intended): " SITE_INPUT
  fi
  SITE_CODE="${SITE_INPUT^^}"

  if [[ -v SITE_OCTET[$SITE_CODE] ]]; then
    WG_OCTET="${SITE_OCTET[$SITE_CODE]}"
    SUBNET="192.168.${WG_OCTET}"
    SITE_DISPLAY_CITY="${SITE_CITY[$SITE_CODE]:-${SITE_CODE}}"
    SITE_DISPLAY_COUNTRY="${SITE_COUNTRY[$SITE_CODE]:-Unknown}"
    SITE_DISPLAY_ENTITY="${SITE_ENTITY[$SITE_CODE]:-Example Music}"
    echo -e "  ${GREEN}→ ${SITE_CODE}: ${SITE_DISPLAY_CITY}, ${SITE_DISPLAY_COUNTRY} — ${SITE_DISPLAY_ENTITY}${NC}"
    echo -e "  ${GREEN}→ management subnet ${SUBNET}.0/24${NC}"
    if [[ "$SITE_CODE" != "CLD" ]]; then
      warn "Zabbix is a single-instance-CLD-only role in this estate today (same convention as"
      warn "Rudder/TacticalRMM/Salt master) — confirm a second Zabbix server is genuinely intended"
      warn "before continuing."
    fi
    break
  else
    warn "Unknown site code '${SITE_CODE}'. Try again."
  fi
done

# ------------------------------------------------------------------------------
# Section 1a — well-known addresses from begyndelse.json (single source of truth)
# ------------------------------------------------------------------------------
# domain_fqdn parameterises every hostname/ServerName below rather than hardcoding
# "jukebox.internal" — same fix rudderme.sh got on 2026-07-17 after being missed by
# that migration entirely. VRK_SUBNET/FRD_SUBNET drive the auto-registration and
# API IP-restriction lists further down (Section 6/16) alongside every site's own
# Subnet from sites.csv — this is the "figure that out from sites.csv" part of
# Robert's brief, plus the two provisioning networks it can't tell you about on
# its own.
command -v jq &>/dev/null || { apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true; apt-get install -y -qq jq; }

BEGYNDELSE_FILE=""
if [[ -n "${BEGYNDELSE_JSON:-}" && -f "${BEGYNDELSE_JSON}" ]]; then
  BEGYNDELSE_FILE="${BEGYNDELSE_JSON}"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "${SCRIPT_DIR}/begyndelse.json" ]]; then
    BEGYNDELSE_FILE="${SCRIPT_DIR}/begyndelse.json"
  elif [[ -f "/etc/example-music/begyndelse.json" ]]; then
    BEGYNDELSE_FILE="/etc/example-music/begyndelse.json"
  fi
fi
[[ -z "${BEGYNDELSE_FILE}" ]] && die "begyndelse.json not found (looked in \$BEGYNDELSE_JSON, script directory, /etc/example-music/) -- cannot determine domain/provisioning subnets."

EXA_DOMAIN=$(jq -r '.domain_fqdn' "${BEGYNDELSE_FILE}")
VRK_SUBNET=$(jq -r '.provisioning_edinburgh.subnet' "${BEGYNDELSE_FILE}")
FRD_SUBNET=$(jq -r '.provisioning_fredericia_havn.subnet' "${BEGYNDELSE_FILE}")

# ------------------------------------------------------------------------------
# Section 2 — Hostname
# ------------------------------------------------------------------------------
section "2. Hostname"

info "Detecting hostname for this Zabbix server..."
CURRENT_HOSTNAME=$(hostname -s)
SUGGESTED_HOSTNAME=""

if [[ "${CURRENT_HOSTNAME}" =~ ^[Ee][Xx][Aa] ]]; then
  SUGGESTED_HOSTNAME="${CURRENT_HOSTNAME^^}"
  info "Detected EXA-convention hostname: ${SUGGESTED_HOSTNAME}"
else
  SUGGESTED_HOSTNAME="EXAZBXCLD001"
  warn "Current hostname '${CURRENT_HOSTNAME}' does not match EXA* convention."
  warn "EXAZBXCLD001 is a SUGGESTED default only -- ZBX is not yet a real role_codes.csv row."
fi

read -rp "  Hostname for this Zabbix server [${SUGGESTED_HOSTNAME}]: " HOSTNAME_INPUT
THIS_HOSTNAME="${HOSTNAME_INPUT:-${SUGGESTED_HOSTNAME}}"
THIS_HOSTNAME="${THIS_HOSTNAME^^}"

info "Setting hostname to ${THIS_HOSTNAME}..."
hostnamectl set-hostname "${THIS_HOSTNAME}"
grep -q "${THIS_HOSTNAME,,}" /etc/hosts 2>/dev/null || \
  echo "127.0.1.1  ${THIS_HOSTNAME,,}.${EXA_DOMAIN}  ${THIS_HOSTNAME,,}" >> /etc/hosts
success "Hostname set to ${THIS_HOSTNAME}."

# ------------------------------------------------------------------------------
# Section 3 — OS / codename detection
# ------------------------------------------------------------------------------
# BUG FIX (2026-09-02, found live on EXAZABCLD001): this used to be Section 3, running BEFORE
# base package install -- on a box without NetworkManager already present (this one didn't have
# it), "systemctl restart NetworkManager" inside the old Section 3 failed outright ("Unit
# NetworkManager.service not found") since nothing had installed it yet. Moved network
# configuration to AFTER base package install (see the new Section 5 below, right after Section
# 4 installs network-manager if missing) -- OS/codename detection and base packages have no
# dependency on network config, so they move up here unchanged in spirit, just renumbered.
section "3. OS / codename detection"

command -v lsb_release &>/dev/null || { apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true; apt-get install -y -qq lsb-release; }

OS_DISTRIBUTOR=$(lsb_release -i -s)
OS_CODENAME=$(lsb_release -c -s)      # e.g. "trixie" -- needed for the apt .sources Suites: line
OS_RELEASE_NUM=$(lsb_release -s -r)   # e.g. "13"      -- needed for the zabbix-release .deb filename

info "Detected: ${OS_DISTRIBUTOR} ${OS_RELEASE_NUM} (${OS_CODENAME})"

if [[ "${OS_DISTRIBUTOR}" != "Debian" ]]; then
  die "This script is Debian-only (detected '${OS_DISTRIBUTOR}'). Not tested on anything else."
fi

# CPU architecture -- Zabbix ships genuinely SEPARATE apt repo trees per architecture
# (.../debian for amd64, .../debian-arm64 for arm64), not one universal tree. Confirmed live
# 2026-09-02 (Robert): downloaded the "_all.deb" zabbix-release package from both trees and
# sha256sum'd them -- they are NOT identical (only the embedded .sources URI differs, pointing
# at "debian" vs "debian-arm64"). "Architecture: all" here just means the .deb package format
# itself has no compiled binaries and will dpkg-install on any host arch -- it does NOT mean the
# two trees' CONTENT is interchangeable. Picking the wrong one silently points apt at the wrong
# architecture's package set. ZBX_DEBIAN_TREE feeds every repo.zabbix.com URL from here on.
HOST_ARCH=$(dpkg --print-architecture)
case "${HOST_ARCH}" in
  amd64) ZBX_DEBIAN_TREE="debian" ;;
  arm64) ZBX_DEBIAN_TREE="debian-arm64" ;;
  *) die "Unsupported architecture '${HOST_ARCH}' -- Zabbix ${ZABBIX_MAJOR}'s Debian repo only has confirmed trees for amd64 (debian) and arm64 (debian-arm64)." ;;
esac
info "Architecture: ${HOST_ARCH} -> using repo tree '${ZBX_DEBIAN_TREE}'"

# ------------------------------------------------------------------------------
# Section 4 — Base + monitoring toolkit packages
# ------------------------------------------------------------------------------
section "4. Base packages + monitoring toolkit"

info "Updating package lists..."
apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true

BASE_PKGS=()
command -v curl    &>/dev/null || BASE_PKGS+=(curl)
command -v wget    &>/dev/null || BASE_PKGS+=(wget)
command -v git     &>/dev/null || BASE_PKGS+=(git)
command -v vim     &>/dev/null || BASE_PKGS+=(vim)
command -v htop    &>/dev/null || BASE_PKGS+=(htop)
command -v tree    &>/dev/null || BASE_PKGS+=(tree)
command -v jq      &>/dev/null || BASE_PKGS+=(jq)
command -v python3 &>/dev/null || BASE_PKGS+=(python3)
command -v arping  &>/dev/null || BASE_PKGS+=(arping)
command -v nmcli   &>/dev/null || BASE_PKGS+=(network-manager)
dpkg -s molly-guard         &>/dev/null || BASE_PKGS+=(molly-guard)
dpkg -s fail2ban            &>/dev/null || BASE_PKGS+=(fail2ban)
dpkg -s ufw                 &>/dev/null || BASE_PKGS+=(ufw)
dpkg -s ca-certificates      &>/dev/null || BASE_PKGS+=(ca-certificates)
dpkg -s gnupg                &>/dev/null || BASE_PKGS+=(gnupg)
dpkg -s apt-transport-https  &>/dev/null || BASE_PKGS+=(apt-transport-https)

# Robert's monitoring toolkit ask (point 4) -- "fping, nmap, snmpwalk, snmp-mibs, etc, etc, etc":
# treated as "the standard diagnostic kit a monitoring server needs", not an exhaustive list --
# extend as needed. snmp-mibs-downloader is deliberately NOT in this batch -- see below, it
# lives in Debian's non-free component (not enabled by this estate's preseed) and needs its own
# handling, not a blind apt-get install alongside everything else.
command -v fping       &>/dev/null || BASE_PKGS+=(fping)
command -v nmap         &>/dev/null || BASE_PKGS+=(nmap)
command -v snmpwalk      &>/dev/null || BASE_PKGS+=(snmp)
command -v tcpdump        &>/dev/null || BASE_PKGS+=(tcpdump)
command -v traceroute      &>/dev/null || BASE_PKGS+=(traceroute)
command -v whois             &>/dev/null || BASE_PKGS+=(whois)

if [[ ${#BASE_PKGS[@]} -gt 0 ]]; then
  info "Installing: ${BASE_PKGS[*]}"
  APT_LOG=$(mktemp /tmp/zabbixme-apt-XXXXXX.log)
  if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      -o Dpkg::Options::="--force-confold" \
      -o Dpkg::Options::="--force-confdef" \
      -o Dpkg::Use-Pty=0 \
      --no-install-recommends \
      "${BASE_PKGS[@]}" > "$APT_LOG" 2>&1; then
    success "Base packages installed."
    rm -f "$APT_LOG"
  else
    APT_RC=$?
    warn "apt-get install failed (exit ${APT_RC}) — last 20 lines of log:"
    tail -20 "$APT_LOG" >&2
    warn "Full log: ${APT_LOG}"
    die "Package installation failed. Fix the above and re-run."
  fi
else
  success "All base packages already present."
fi

# BUG FIX (2026-09-02, found live on EXAZABCLD001): snmp-mibs-downloader has no installation
# candidate on a stock estate build -- confirmed live against packages.debian.org: the package
# genuinely exists for trixie, but lives in Debian's non-free component (MIB file licensing),
# and this estate's preseed (bootstrap/web/debian/lvm-*.seed) never enables non-free/contrib --
# a completely standard Debian default, not a preseed bug to fix there. Previously bundled into
# the single BASE_PKGS apt-get call above, which meant this ONE unavailable package failed the
# WHOLE batch -- curl/git/fping/nmap/etc. never installed either, even though every one of them
# would have worked fine. Split out into its own best-effort install: enable non-free first
# (handles both the DEB822 debian.sources format trixie's installer actually writes, and the
# classic sources.list format, in case this ever runs on an older/hand-built box), then install
# just this one package on its own -- a failure here is a warning, not a die, since Robert's
# broader ask (the monitoring toolkit) still needs the rest of this script to run either way.
if ! dpkg -s snmp-mibs-downloader &>/dev/null; then
  NONFREE_ENABLED=0
  for SOURCES_FILE in /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list; do
    [[ -f "${SOURCES_FILE}" ]] || continue
    if [[ "${SOURCES_FILE}" == *.sources ]]; then
      # DEB822 format -- Components: line, space-separated.
      if grep -qE "^Components:.*\bmain\b" "${SOURCES_FILE}" && ! grep -qE "^Components:.*\bnon-free\b" "${SOURCES_FILE}"; then
        info "Enabling non-free component in ${SOURCES_FILE} (needed for snmp-mibs-downloader)..."
        sed -i -E "s/^(Components:.*\bmain\b)(.*)$/\1 non-free\2/" "${SOURCES_FILE}"
        NONFREE_ENABLED=1
      fi
    else
      # Classic one-line-per-repo format -- append non-free to any "main"-only debian mirror line.
      if grep -qE "^deb .*\bmain\b" "${SOURCES_FILE}" && ! grep -qE "^deb .*\bnon-free\b" "${SOURCES_FILE}"; then
        info "Enabling non-free component in ${SOURCES_FILE} (needed for snmp-mibs-downloader)..."
        sed -i -E "s/^(deb .*\bmain\b)(.*)$/\1 non-free\2/" "${SOURCES_FILE}"
        NONFREE_ENABLED=1
      fi
    fi
  done
  if [[ "${NONFREE_ENABLED}" -eq 1 ]]; then
    apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true
  fi
  if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends snmp-mibs-downloader &>/dev/null; then
    success "snmp-mibs-downloader installed."
  else
    warn "snmp-mibs-downloader still not installable -- skipping. snmpwalk/snmpget will work but"
    warn "show numeric OIDs instead of resolved names. Install manually later if needed:"
    warn "  apt-get install snmp-mibs-downloader"
  fi
fi

# snmp-mibs-downloader ships with MIB downloading DISABLED by default on Debian (the "mibs :"
# line in /etc/snmp/snmp.conf suppresses them, and the actual MIB files aren't fetched until
# download-mibs runs) -- Robert asked for the tool, which means having it actually able to
# resolve OID names, not just installed and inert.
if [[ -f /etc/snmp/snmp.conf ]] && grep -q "^mibs :$" /etc/snmp/snmp.conf 2>/dev/null; then
  info "Enabling MIB resolution (removing the default 'mibs :' suppression line)..."
  sed -i '/^mibs :$/d' /etc/snmp/snmp.conf
fi
if command -v download-mibs &>/dev/null; then
  info "Downloading MIBs (download-mibs) — this can take a minute..."
  download-mibs &>/dev/null || warn "download-mibs returned non-zero — MIB resolution may be incomplete. Re-run manually: download-mibs"
  success "MIBs downloaded."
fi

# ------------------------------------------------------------------------------
# Section 5 — Network / Static IP
# ------------------------------------------------------------------------------
# Runs AFTER base packages (Section 4) on purpose -- network-manager is installed there. See
# this file's own 2026-09-02 changelog entry for why this used to be Section 3 and broke on a
# box without NetworkManager already present.
section "5. Network / Static IP"

PROV_NET_DEFAULT="${SUBNET}"
info "Management subnet for this site: ${PROV_NET_DEFAULT}.x"

read -rp "  Gateway last octet [253]: " GW_OCTET_INPUT
GW_OCTET="${GW_OCTET_INPUT:-253}"
PROV_GW="${PROV_NET_DEFAULT}.${GW_OCTET}"

# No CSV-assigned octet exists yet for Zabbix (see this file's own version-history note above) --
# deliberately NOT defaulting to a specific value the way rudderme.sh can for RUD's already-known
# .12. Robert: pick a free octet (.15/.16/.23 and most of the range above .82 were free as of
# 2026-09-01) and type it in below. IMPORTANT: the ip_in_use() check right below is a LIVE
# ping/arping probe only -- it does NOT cross-check sites.csv/devices.csv for octets that are
# already allocated on paper but not currently answering (e.g. EXASLTCLD001 at .22, which may
# not respond to ICMP). A "appears free" result here is not proof the octet is actually
# unclaimed -- check devices.csv/cld.ini yourself before typing one in, found live 2026-09-02
# when EXAZABCLD001 was about to be given .22 (already EXASLTCLD001's).
read -rp "  Static IP for this Zabbix server (no assigned default yet -- see comment above): " NODE_STATIC_IP
[[ -z "${NODE_STATIC_IP}" ]] && die "A static IP is required -- Zabbix is a permanent infrastructure node, not a DHCP client."

info "Checking whether ${NODE_STATIC_IP} is already in use..."
if ip_in_use "${NODE_STATIC_IP}"; then
  CURRENT_IPS=$(hostname -I)
  if echo "$CURRENT_IPS" | grep -qw "${NODE_STATIC_IP}"; then
    info "${NODE_STATIC_IP} is already assigned to this host — continuing."
  else
    die "${NODE_STATIC_IP} is already in use by another host. Resolve the conflict first."
  fi
else
  success "${NODE_STATIC_IP} appears free (live probe only -- not cross-checked against devices.csv/cld.ini) — proceeding."
fi

info "Detecting network interface..."
PROV_IFACE=""
for iface in $(ls /sys/class/net/); do
  [[ "$iface" == "lo" ]] && continue
  ip_addr=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP "(?<=inet\s)\d+\.\d+\.\d+\.\d+" | head -1)
  if [[ -n "$ip_addr" ]]; then
    PROV_IFACE="$iface"
    success "Detected interface: ${PROV_IFACE} (currently ${ip_addr})"
    break
  fi
done

if [[ -z "$PROV_IFACE" ]]; then
  warn "Could not auto-detect interface."
  AVAILABLE_IFACES=($(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' | grep -v '@'))
  read -rp "  Enter interface name (available: ${AVAILABLE_IFACES[*]}): " PROV_IFACE
  PROV_IFACE="${PROV_IFACE:-${AVAILABLE_IFACES[0]:-eth0}}"
fi

PROV_MAC=$(cat "/sys/class/net/${PROV_IFACE}/address" 2>/dev/null)
info "Pinning ${PROV_IFACE} (MAC ${PROV_MAC}) via systemd .link..."
mkdir -p /etc/systemd/network
cat > /etc/systemd/network/10-zabbix-prov.link << EOF
# Example Music — Zabbix server interface pin
# Written by zabbixme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# MAC: ${PROV_MAC}  interface: ${PROV_IFACE}
[Match]
MACAddress=${PROV_MAC}
[Link]
Name=${PROV_IFACE}
EOF
success "Interface pin written."

info "Configuring static IP via NetworkManager..."
systemctl disable networking.service 2>/dev/null || true
systemctl mask    networking.service 2>/dev/null || true

if [[ -f /etc/network/interfaces ]]; then
  if grep -qE "^(auto|allow-|iface)\s+${PROV_IFACE}" /etc/network/interfaces 2>/dev/null; then
    warn "Removing ifupdown stanza for ${PROV_IFACE} from /etc/network/interfaces..."
    cp -n /etc/network/interfaces /etc/network/interfaces.bak
    sed -i "/^auto\s\+${PROV_IFACE}\b/d"    /etc/network/interfaces
    sed -i "/^allow-.*\s${PROV_IFACE}\b/d"  /etc/network/interfaces
    success "Cleaned /etc/network/interfaces"
  fi
fi

NM_CONF="/etc/NetworkManager/NetworkManager.conf"
NM_RESTART_REQUIRED=0
if grep -q "managed=false" "${NM_CONF}" 2>/dev/null; then
  warn "NetworkManager.conf has managed=false — fixing..."
  sed -i "s/managed=false/managed=true/" "${NM_CONF}"
  NM_RESTART_REQUIRED=1
fi

nmcli con delete "zabbix-static" 2>/dev/null || true

nmcli con add type ethernet ifname "${PROV_IFACE}" con-name "zabbix-static" \
  ipv4.method manual \
  ipv4.addresses "${NODE_STATIC_IP}/24" \
  ipv4.gateway "${PROV_GW}" \
  ipv4.dns "${PROV_NET_DEFAULT}.10" \
  ipv4.dns-search "${EXA_DOMAIN}" \
  ipv6.method ignore \
  connection.autoconnect yes \
  connection.autoconnect-priority 100 \
  && success "NM profile zabbix-static written." \
  || warn "nmcli con add returned non-zero — check: nmcli connection show zabbix-static"

# BUG FIX (2026-09-02, Robert: "running things over SSH and dropping/upping the interface kills
# the run either in ansible or scripts" -- told repeatedly, this had never actually been fixed
# here). Matches firewallme.sh's own WAN activation prompt exactly (same wording, same default).
# systemctl restart NetworkManager tears down and re-evaluates every connection the daemon
# manages, including whichever one this SSH session is riding on right now -- doing that
# unconditionally is what actually causes the drop, not nmcli con add itself (writing a profile
# to disk doesn't activate it on an interface that already has a live connection). The profile
# above is written either way; only the restart/activation is gated.
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              Interface Activation                    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo
warn "If you are connected via SSH over this interface, restarting NetworkManager"
warn "now may drop your session. The connection profile above is written regardless --"
warn "if you say N, bring it up yourself afterwards, or just reboot (autoconnect is set)."
echo
read -rp "Activate the new static IP now? [y/N] " NM_ACTIVATE_ANSWER
if [[ "${NM_ACTIVATE_ANSWER,,}" == "y" ]]; then
  info "Restarting NetworkManager to apply the new static IP..."
  systemctl restart NetworkManager
  sleep 3
  nmcli con up zabbix-static 2>/dev/null || true
  success "NetworkManager restarted and zabbix-static activated."
elif [[ "${NM_RESTART_REQUIRED}" -eq 1 ]]; then
  warn "Activation skipped. Note: NetworkManager.conf's managed=false fix above also needs a"
  warn "restart to take effect, not just this new profile."
  warn "Bring it up yourself later:  systemctl restart NetworkManager && nmcli con up zabbix-static"
  warn "Or just reboot — the profile is set to autoconnect."
else
  warn "Activation skipped — bring it up yourself with: nmcli con up zabbix-static"
  warn "Or just reboot — the profile is set to autoconnect."
fi

# ------------------------------------------------------------------------------
# Section 6 — UFW firewall
# ------------------------------------------------------------------------------
section "6. Firewall (UFW)"

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment "SSH"
ufw allow 80/tcp   comment "Zabbix web UI (redirects to HTTPS if configured)"
ufw allow 443/tcp  comment "Zabbix web UI HTTPS"

# Robert point 6: "the API will only allow IPs from the VRK, FRD and sites subnets to add to
# the auto-registration". Zabbix itself has no native inbound-IP allowlist for the trapper port
# agents connect to (10051) -- that's an OS-firewall job, same as rudderme.sh's own UFW section
# for Rudder's agent ports. VRK_SUBNET/FRD_SUBNET come from begyndelse.json (Section 1a); every
# site's own subnet comes from sites.csv, same loop rudderme.sh already uses for its own
# allowed-networks list.
ufw allow from "${VRK_SUBNET}" to any port 10051 proto tcp comment "Zabbix trapper -- VRK" 2>/dev/null || true
ufw allow from "${FRD_SUBNET}" to any port 10051 proto tcp comment "Zabbix trapper -- FRD" 2>/dev/null || true
for site_code in $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort); do
  oct="${SITE_OCTET[$site_code]}"
  [[ -z "$oct" ]] && continue
  ufw allow from "192.168.${oct}.0/24" to any port 10051 proto tcp \
    comment "Zabbix trapper ${site_code}" 2>/dev/null || true
done

ufw --force enable
ufw status verbose
success "UFW configured."

# ------------------------------------------------------------------------------
# Section 7 — MariaDB
# ------------------------------------------------------------------------------
section "7. MariaDB (database backend)"

if ! dpkg -s mariadb-server &>/dev/null 2>&1; then
  info "Installing MariaDB server..."
  APT_LOG=$(mktemp /tmp/zabbixme-mariadb-apt-XXXXXX.log)
  if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" \
      mariadb-server mariadb-client > "$APT_LOG" 2>&1; then
    success "MariaDB installed."
    rm -f "$APT_LOG"
  else
    warn "MariaDB install failed — last 20 lines:"
    tail -20 "$APT_LOG" >&2
    die "MariaDB install failed. Fix the above and re-run."
  fi
else
  success "MariaDB already installed."
fi

systemctl enable --now mariadb

ZABBIX_DB_NAME="zabbix"
ZABBIX_DB_USER="zabbix"

if [[ -f "${DB_CREDS_FILE}" ]]; then
  info "Existing DB credentials file found at ${DB_CREDS_FILE} — reusing (not regenerating)."
  # shellcheck disable=SC1090
  source "${DB_CREDS_FILE}"
else
  ZABBIX_DB_PASSWORD=$(gen_password 28)
  cat > "${DB_CREDS_FILE}" << EOF
# Generated by zabbixme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ) -- root-only, never committed anywhere.
ZABBIX_DB_NAME="${ZABBIX_DB_NAME}"
ZABBIX_DB_USER="${ZABBIX_DB_USER}"
ZABBIX_DB_PASSWORD="${ZABBIX_DB_PASSWORD}"
EOF
  chmod 0600 "${DB_CREDS_FILE}"
  success "Generated new DB credentials, saved to ${DB_CREDS_FILE} (root-only)."
fi

info "Creating database and user (idempotent — CREATE ... IF NOT EXISTS)..."
# utf8mb4 / utf8mb4_bin -- Zabbix's own current requirement, not the utf8/utf8_bin the old
# (2019-era, 4.0) reference script used. Getting this wrong is a real, documented source of
# "Character set utf8 is not supported" install failures on modern Zabbix.
mysql -u root << SQL
CREATE DATABASE IF NOT EXISTS ${ZABBIX_DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER IF NOT EXISTS '${ZABBIX_DB_USER}'@'localhost' IDENTIFIED BY '${ZABBIX_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${ZABBIX_DB_NAME}.* TO '${ZABBIX_DB_USER}'@'localhost';
SET GLOBAL log_bin_trust_function_creators = 1;
FLUSH PRIVILEGES;
SQL
success "Database '${ZABBIX_DB_NAME}' and user '${ZABBIX_DB_USER}' ready."

# ------------------------------------------------------------------------------
# Section 8 — Zabbix repository + server/frontend packages
# ------------------------------------------------------------------------------
section "8. Zabbix ${ZABBIX_MAJOR} repository + packages"

if ! dpkg -s zabbix-release &>/dev/null 2>&1; then
  # 7.0 (and every older version) uses the classic FLAT layout -- no "/release/" segment at
  # all, confirmed live 2026-09-01 (repo.zabbix.com/zabbix/7.0/release/debian/ is a genuine
  # 404; the real product packages AND this pointer package both live directly under
  # zabbix/7.0/debian/pool/...). This is a different URL shape than 8.0's newer "/release/"
  # tree -- do not copy this construction back to 8.0 without re-checking, see v1.1.0's
  # changelog entry above.
  #
  # ZBX_DEBIAN_TREE (Section 4) selects "debian" vs "debian-arm64" -- these are genuinely
  # different repo trees, not just a path alias, confirmed live 2026-09-02 by sha256sum'ing
  # the "_all.deb" zabbix-release package from both: different hashes, different sizes, only
  # the embedded .sources URI differs (points at "debian" vs "debian-arm64"). The .deb
  # FILENAME pattern itself is identical either way ("_all.deb", same naming), only the path
  # segment changes.
  ZBX_RELEASE_URL="https://repo.zabbix.com/zabbix/${ZABBIX_MAJOR}/${ZBX_DEBIAN_TREE}/pool/main/z/zabbix-release/zabbix-release_latest_${ZABBIX_MAJOR}%2Bdebian${OS_RELEASE_NUM}_all.deb"
  info "Fetching zabbix-release package: ${ZBX_RELEASE_URL}"
  ZBX_RELEASE_DEB=$(mktemp /tmp/zabbix-release-XXXXXX.deb)
  if ! wget -q --tries=1 --timeout=30 -O "${ZBX_RELEASE_DEB}" "${ZBX_RELEASE_URL}"; then
    die "Could not download zabbix-release for Debian ${OS_RELEASE_NUM} (${OS_CODENAME}, ${HOST_ARCH}) from ${ZBX_RELEASE_URL} -- check the URL is still current at repo.zabbix.com/zabbix/${ZABBIX_MAJOR}/${ZBX_DEBIAN_TREE}/pool/main/z/zabbix-release/ (this exact filename pattern was verified live on 2026-09-01/02, but repo layouts do change)."
  fi
  dpkg -i "${ZBX_RELEASE_DEB}"
  rm -f "${ZBX_RELEASE_DEB}"
  success "zabbix-release installed."
else
  success "zabbix-release already installed."
fi

# 7.0's release package writes a single zabbix.sources file (no separate unstable channel to
# worry about, unlike 8.0) -- this check is now dead code for 7.0 specifically, left in place
# harmlessly (already conditional on the file existing) in case a future version reintroduces
# an unstable/dev channel the same way 8.0 has one.
UNSTABLE_SOURCES="/etc/apt/sources.list.d/zabbix-unstable.sources"
if [[ -f "${UNSTABLE_SOURCES}" ]] && ! grep -q "^Enabled: no" "${UNSTABLE_SOURCES}" 2>/dev/null; then
  info "Disabling zabbix-unstable repo (pre-release channel, not wanted here)..."
  echo "Enabled: no" >> "${UNSTABLE_SOURCES}"
fi

apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true

# Sanity check BEFORE the real install attempt -- confirmed live 2026-09-01 that 7.0 genuinely
# does publish zabbix-server-mysql for debian13/trixie (up to at least 7.0.30), so this is now
# a belt-and-braces check rather than a known-uncertain one -- kept anyway, since a repo layout
# can always change again, and failing fast here with a clear message beats a confusing error
# halfway through a long install either way.
if ! apt-cache policy zabbix-server-mysql 2>/dev/null | grep -q "Candidate:"; then
  die "zabbix-server-mysql has no installable candidate after adding the ${ZABBIX_MAJOR} repo for Debian ${OS_RELEASE_NUM} (${OS_CODENAME}, ${HOST_ARCH}). Check https://repo.zabbix.com/zabbix/${ZABBIX_MAJOR}/${ZBX_DEBIAN_TREE}/pool/main/z/zabbix/ by hand, or try 'apt-cache policy zabbix-server-mysql' yourself for the full picture."
fi
CANDIDATE_VER=$(apt-cache policy zabbix-server-mysql 2>/dev/null | awk '/Candidate:/{print $2}')
success "zabbix-server-mysql candidate found: ${CANDIDATE_VER}"

# zabbix-agent, NOT zabbix-agent2 -- Robert was explicit: "agent is agent not agent2, I am not
# using agent2". Filtered down to what's actually resolvable before installing, rather than
# assuming every name exists verbatim in this exact package set.
INSTALLABLE_ZBX_PKGS=()
for pkg in zabbix-server-mysql zabbix-frontend-php zabbix-sql-scripts zabbix-apache-conf zabbix-agent; do
  if apt-cache policy "$pkg" 2>/dev/null | grep -q "Candidate:"; then
    INSTALLABLE_ZBX_PKGS+=("$pkg")
  else
    warn "Package '$pkg' not found in the repo -- skipping (may not exist under this name for ${ZABBIX_MAJOR})."
  fi
done
[[ ${#INSTALLABLE_ZBX_PKGS[@]} -eq 0 ]] && die "None of the expected Zabbix packages resolved -- something is wrong with the repo setup above."

# Apache + PHP are pulled in automatically as zabbix-frontend-php dependencies.
info "Installing: ${INSTALLABLE_ZBX_PKGS[*]}"
APT_LOG=$(mktemp /tmp/zabbixme-zbx-apt-XXXXXX.log)
if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" \
    "${INSTALLABLE_ZBX_PKGS[@]}" > "$APT_LOG" 2>&1; then
  success "Zabbix packages installed."
  rm -f "$APT_LOG"
else
  warn "Zabbix package install failed — last 30 lines:"
  tail -30 "$APT_LOG" >&2
  die "Zabbix install failed. Fix the above and re-run."
fi

# Stop nginx if present (same reasoning as the old reference script -- Apache is the chosen
# HTTP daemon here, don't fight nginx for port 80/443 if it happens to be installed already).
if systemctl is-active --quiet nginx 2>/dev/null; then
  warn "nginx is running -- stopping it (Apache is this estate's chosen HTTP daemon)."
  systemctl stop nginx
  systemctl disable nginx 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# Section 9 — Database schema import + zabbix_server.conf + housekeeping
# ------------------------------------------------------------------------------
section "9. Database schema + server config + housekeeping"

# Schema location has moved across Zabbix versions (create.sql.gz under the -mysql package's
# own doc dir historically, vs a dedicated zabbix-sql-scripts package with schema/images/data
# split from ~6.4 onward) -- zabbix-sql-scripts is confirmed to exist as a real package for
# 7.0/debian13, so the split layout is the expected path here, but auto-detected with the old
# layout as a fallback rather than hardcoded, since the split file structure itself
# (schema/images/data vs a single combined file) wasn't directly inspected.
SCHEMA_IMPORTED_MARKER="/var/lib/mysql/${ZABBIX_DB_NAME}/.zabbixme_schema_imported"
if [[ -f "${SCHEMA_IMPORTED_MARKER}" ]]; then
  success "Schema already imported (marker present) — skipping."
else
  SCHEMA_CANDIDATES=(
    "/usr/share/doc/zabbix-server-mysql/create.sql.gz"
    "/usr/share/zabbix-sql-scripts/mysql/create.sql.gz"
    "/usr/share/zabbix/sql-scripts/mysql/create.sql.gz"
  )
  SCHEMA_FILE=""
  for candidate in "${SCHEMA_CANDIDATES[@]}"; do
    [[ -f "${candidate}" ]] && { SCHEMA_FILE="${candidate}"; break; }
  done

  if [[ -n "${SCHEMA_FILE}" ]]; then
    info "Importing schema from ${SCHEMA_FILE} (this can take a minute)..."
    zcat "${SCHEMA_FILE}" | mysql -u"${ZABBIX_DB_USER}" -p"${ZABBIX_DB_PASSWORD}" "${ZABBIX_DB_NAME}"
    touch "${SCHEMA_IMPORTED_MARKER}" 2>/dev/null || true
    success "Schema imported."
  else
    # Newer split layout: schema.sql.gz + images.sql.gz + data.sql.gz, imported in that order.
    SPLIT_DIR=""
    for d in /usr/share/zabbix-sql-scripts/mysql /usr/share/zabbix/sql-scripts/mysql; do
      [[ -f "${d}/schema.sql.gz" ]] && { SPLIT_DIR="${d}"; break; }
    done
    if [[ -n "${SPLIT_DIR}" ]]; then
      info "Importing split schema from ${SPLIT_DIR} (schema, images, data)..."
      for part in schema images data; do
        if [[ -f "${SPLIT_DIR}/${part}.sql.gz" ]]; then
          zcat "${SPLIT_DIR}/${part}.sql.gz" | mysql -u"${ZABBIX_DB_USER}" -p"${ZABBIX_DB_PASSWORD}" "${ZABBIX_DB_NAME}"
        fi
      done
      touch "${SCHEMA_IMPORTED_MARKER}" 2>/dev/null || true
      success "Split schema imported."
    else
      die "Could not find the Zabbix DB schema anywhere expected (checked: ${SCHEMA_CANDIDATES[*]}, and the split schema/images/data layout under zabbix-sql-scripts). Find it manually: dpkg -L zabbix-sql-scripts zabbix-server-mysql | grep -i sql"
    fi
  fi
fi

info "Writing /etc/zabbix/zabbix_server.conf DB settings..."
ZBX_SRV_CONF="/etc/zabbix/zabbix_server.conf"
if [[ -f "${ZBX_SRV_CONF}" ]]; then
  sed -i "s/^# DBName=.*/DBName=${ZABBIX_DB_NAME}/;   s/^DBName=.*/DBName=${ZABBIX_DB_NAME}/"       "${ZBX_SRV_CONF}"
  sed -i "s/^# DBUser=.*/DBUser=${ZABBIX_DB_USER}/;   s/^DBUser=.*/DBUser=${ZABBIX_DB_USER}/"       "${ZBX_SRV_CONF}"
  if grep -q "^DBPassword=" "${ZBX_SRV_CONF}" 2>/dev/null; then
    sed -i "s/^DBPassword=.*/DBPassword=${ZABBIX_DB_PASSWORD}/" "${ZBX_SRV_CONF}"
  else
    echo "DBPassword=${ZABBIX_DB_PASSWORD}" >> "${ZBX_SRV_CONF}"
  fi
  success "zabbix_server.conf DB settings written."
else
  die "${ZBX_SRV_CONF} not found -- zabbix-server-mysql package layout may differ from what this script expects."
fi

systemctl enable zabbix-server
systemctl restart zabbix-server

info "Waiting for zabbix-server to come up (up to 60s)..."
ZBX_SRV_READY=0
for i in $(seq 1 12); do
  systemctl is-active --quiet zabbix-server && { ZBX_SRV_READY=1; break; }
  sleep 5
done
if [[ "$ZBX_SRV_READY" -eq 1 ]]; then
  success "zabbix-server is running."
else
  warn "zabbix-server did not report active within 60s -- check: journalctl -fu zabbix-server"
fi

# DB pruning / housekeeping (Robert, point 8: "I HATE when the database grows to a ridiculous
# size because MariaDB doesn't housekeep correctly"). Two real, distinct mechanisms, both
# applied:
#   1. Shorter default retention than Zabbix's own shipped defaults -- set directly against the
#      config table (the housekeeper reads these on its own schedule, no restart needed). These
#      are deliberately tighter than Zabbix's stock defaults, not a re-statement of them --
#      adjust in Administration -> General -> Housekeeping in the frontend if too aggressive.
#   2. A weekly systemd timer running mysqlcheck --optimize against the zabbix DB. This is the
#      actual mechanism behind the complaint: MariaDB's InnoDB engine does not automatically
#      return freed space to the OS after the housekeeper's own row-level DELETEs -- the table
#      files just keep growing regardless of how aggressive the retention settings are, until
#      something runs OPTIMIZE TABLE (which the housekeeper itself never does). Native
#      partitioning (DROP PARTITION instead of DELETE) is Zabbix's own recommended fix for
#      genuinely large installs and would avoid this entirely, but is real DDL surgery on live
#      history/trends tables -- not attempted unattended here; worth coming back to if the
#      timer-based approach isn't enough.
info "Tightening DB housekeeping retention..."
mysql -u"${ZABBIX_DB_USER}" -p"${ZABBIX_DB_PASSWORD}" "${ZABBIX_DB_NAME}" << SQL
UPDATE config SET
  hk_history_global = 1, hk_history = '7d',
  hk_trends_global   = 1, hk_trends  = '90d',
  hk_events_mode     = 1,
  hk_events_trigger  = '14d',
  hk_events_internal = '3d',
  hk_events_discovery= '3d',
  hk_events_autoreg  = '3d',
  hk_sessions_mode   = 1, hk_sessions = '30d',
  hk_audit_mode      = 1, hk_audit    = '90d';
SQL
success "Housekeeping retention tightened (history=7d, trends=90d — adjust in the frontend if needed)."

info "Installing weekly DB optimise timer..."
cat > /etc/systemd/system/zabbix-db-optimize.service << EOF
[Unit]
Description=Optimize Zabbix MariaDB tables (reclaim InnoDB space the housekeeper's DELETEs leave behind)
After=mariadb.service

[Service]
Type=oneshot
ExecStart=/usr/bin/mysqlcheck -u${ZABBIX_DB_USER} -p${ZABBIX_DB_PASSWORD} --optimize ${ZABBIX_DB_NAME}
EOF
cat > /etc/systemd/system/zabbix-db-optimize.timer << 'EOF'
[Unit]
Description=Weekly Zabbix MariaDB optimise

[Timer]
OnCalendar=Sun 03:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
chmod 0600 /etc/systemd/system/zabbix-db-optimize.service   # embeds the DB password
systemctl daemon-reload
systemctl enable --now zabbix-db-optimize.timer
success "Weekly DB optimise timer installed (Sundays 03:00 — see 'systemctl list-timers')."

# ------------------------------------------------------------------------------
# Section 10 — Frontend config (zabbix.conf.php, written directly)
# ------------------------------------------------------------------------------
section "10. Frontend configuration"

# Written directly rather than via the browser setup.php wizard -- the frontend detects an
# existing zabbix.conf.php and skips the wizard automatically, which is what makes this
# scriptable at all. FRONTEND_CONF_DIR resolved dynamically (see Section 11) rather than
# assumed, since package layouts vary.
FRONTEND_ROOT=$(dpkg -L zabbix-frontend-php 2>/dev/null | grep -m1 '/index\.php$' | xargs dirname)
[[ -z "${FRONTEND_ROOT}" ]] && die "Could not determine the Zabbix frontend's installed path (dpkg -L zabbix-frontend-php had no index.php) -- check the package actually installed correctly."
FRONTEND_CONF="${FRONTEND_ROOT}/conf/zabbix.conf.php"

ZBX_SESSION_KEY=$(gen_password 32)
mkdir -p "$(dirname "${FRONTEND_CONF}")"
cat > "${FRONTEND_CONF}" << EOF
<?php
// Generated by zabbixme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ) -- skips the browser setup wizard.
\$DB['TYPE']     = 'MYSQL';
\$DB['SERVER']   = 'localhost';
\$DB['PORT']     = '0';
\$DB['DATABASE'] = '${ZABBIX_DB_NAME}';
\$DB['USER']     = '${ZABBIX_DB_USER}';
\$DB['PASSWORD'] = '${ZABBIX_DB_PASSWORD}';
\$DB['ENCRYPTION']        = false;
\$DB['DOUBLE_IEEE754']    = true;

\$ZBX_SERVER      = 'localhost';
\$ZBX_SERVER_PORT = '10051';
\$ZBX_SERVER_NAME = '${THIS_HOSTNAME}';

\$IMAGE_FORMAT_DEFAULT = IMAGE_FORMAT_PNG;

\$SSO['SP_TYPE']    = ADFS_ONELOGIN_SETTINGS_XML;
\$SSO['SP_KEY']     = 'sp.key';
\$SSO['SP_CERT']    = 'sp.crt';
\$SSO['IDP_CERT']   = 'idp.crt';
\$SSO['SETTINGS']   = [];

\$ZBX_SESSION_NAME = 'zbx_session_${ZBX_SESSION_KEY:0:8}';
EOF
chown www-data:www-data "${FRONTEND_CONF}" 2>/dev/null || true
chmod 0640 "${FRONTEND_CONF}"
success "zabbix.conf.php written to ${FRONTEND_CONF}"

# ------------------------------------------------------------------------------
# Section 11 — Apache vhost: ServerName + "/" -> frontend 301 redirect
# ------------------------------------------------------------------------------
section "11. Apache virtual host"

ZBX_FQDN="zabbix.${EXA_DOMAIN}"
a2enmod rewrite &>/dev/null || true

cat > /etc/apache2/sites-available/zabbix.conf << EOF
# Generated by zabbixme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# Robert point 3: hitting "/" 301-redirects to the Zabbix WebUI, same as asking for
# ${ZBX_FQDN} directly -- both land on the same vhost, both redirect to /zabbix/.
<VirtualHost *:80>
    ServerName ${ZBX_FQDN}
    ServerAlias ${NODE_STATIC_IP}

    DocumentRoot /var/www/html
    Alias /zabbix ${FRONTEND_ROOT}

    RedirectMatch 301 ^/\$ /zabbix/

    <Directory ${FRONTEND_ROOT}>
        Options FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>

    # Robert point 6 (API restriction): api_jsonrpc.php reachable only from VRK/FRD/site
    # subnets -- everything else (the UI itself) stays open to the LAN as normal.
    <Location /zabbix/api_jsonrpc.php>
        Require ip ${VRK_SUBNET}
        Require ip ${FRD_SUBNET}
EOF
for site_code in $(echo "${!SITE_OCTET[@]}" | tr ' ' '\n' | sort); do
  oct="${SITE_OCTET[$site_code]}"
  [[ -z "$oct" ]] && continue
  echo "        Require ip 192.168.${oct}.0/24" >> /etc/apache2/sites-available/zabbix.conf
done
cat >> /etc/apache2/sites-available/zabbix.conf << EOF
    </Location>

    ErrorLog \${APACHE_LOG_DIR}/zabbix_error.log
    CustomLog \${APACHE_LOG_DIR}/zabbix_access.log combined
</VirtualHost>
EOF

a2dissite 000-default &>/dev/null || true
a2ensite zabbix &>/dev/null
apache2ctl configtest && systemctl reload apache2 || warn "apache2ctl configtest failed -- check /etc/apache2/sites-available/zabbix.conf by hand before it's live."
success "Apache vhost written: http://${ZBX_FQDN}/ and http://${NODE_STATIC_IP}/ both redirect to /zabbix/"

# ------------------------------------------------------------------------------
# Section 12 — Wait for frontend/API, rotate Admin off the default password
# ------------------------------------------------------------------------------
section "12. Frontend + API readiness, Admin password rotation"

ZBX_API_URL="http://localhost/zabbix/api_jsonrpc.php"

info "Waiting for the Zabbix API to respond (up to 2 minutes)..."
ZBX_API_READY=0
for i in $(seq 1 24); do
  if curl -s -o /dev/null -w "%{http_code}" -X POST -H 'Content-Type: application/json-rpc' \
      -d '{"jsonrpc":"2.0","method":"apiinfo.version","params":{},"id":1}' \
      "${ZBX_API_URL}" 2>/dev/null | grep -q "200"; then
    ZBX_API_READY=1
    break
  fi
  sleep 5
done

if [[ "$ZBX_API_READY" -ne 1 ]]; then
  warn "Zabbix API did not respond within 2 minutes -- skipping Admin password rotation and"
  warn "auto-registration setup (Sections 12-14). Re-run this script once the frontend/API"
  warn "are confirmed reachable, or do these steps manually in the UI."
else
  success "Zabbix API is responding."

  # Default Zabbix credentials are Admin/zabbix -- login with those, then immediately rotate to
  # a generated password so the default is never left live. If this fails, the password was
  # probably already rotated by a previous run -- that's fine, not treated as an error.
  ZBX_API_AUTH=$(curl -s -X POST -H 'Content-Type: application/json-rpc' \
    -d '{"jsonrpc":"2.0","method":"user.login","params":{"username":"Admin","password":"zabbix"},"id":1}' \
    "${ZBX_API_URL}" | jq -r '.result // empty')

  if [[ -n "${ZBX_API_AUTH}" ]]; then
    if [[ -f "${API_CREDS_FILE}" ]]; then
      source "${API_CREDS_FILE}"
    else
      ZBX_ADMIN_PASSWORD=$(gen_password 24)
    fi
    curl -s -X POST -H 'Content-Type: application/json-rpc' \
      -d '{"jsonrpc":"2.0","method":"user.update","params":{"userid":"1","password":"'"${ZBX_ADMIN_PASSWORD}"'"},"id":1,"auth":"'"${ZBX_API_AUTH}"'"}' \
      "${ZBX_API_URL}" > /dev/null
    cat > "${API_CREDS_FILE}" << EOF
# Generated by zabbixme.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ) -- root-only, never committed anywhere.
ZBX_ADMIN_USER="Admin"
ZBX_ADMIN_PASSWORD="${ZBX_ADMIN_PASSWORD}"
EOF
    chmod 0600 "${API_CREDS_FILE}"
    success "Admin password rotated off the Zabbix default — saved to ${API_CREDS_FILE} (root-only)."
    # Re-auth with the new password for the sections below.
    ZBX_API_AUTH=$(curl -s -X POST -H 'Content-Type: application/json-rpc' \
      -d '{"jsonrpc":"2.0","method":"user.login","params":{"username":"Admin","password":"'"${ZBX_ADMIN_PASSWORD}"'"},"id":1}' \
      "${ZBX_API_URL}" | jq -r '.result // empty')
  else
    warn "Could not log in as Admin/zabbix -- password was probably already rotated by an"
    warn "earlier run of this script. Re-auth with the saved credentials instead."
    if [[ -f "${API_CREDS_FILE}" ]]; then
      source "${API_CREDS_FILE}"
      ZBX_API_AUTH=$(curl -s -X POST -H 'Content-Type: application/json-rpc' \
        -d '{"jsonrpc":"2.0","method":"user.login","params":{"username":"Admin","password":"'"${ZBX_ADMIN_PASSWORD}"'"},"id":1}' \
        "${ZBX_API_URL}" | jq -r '.result // empty')
    fi
  fi

  # --------------------------------------------------------------------------
  # Section 13 — "auto-registration" host group (Robert point 5)
  # --------------------------------------------------------------------------
  section "13. auto-registration host group"

  if [[ -n "${ZBX_API_AUTH:-}" ]]; then
    AUTOREG_GROUP_ID=$(curl -s -X POST -H 'Content-Type: application/json-rpc' \
      -d '{"jsonrpc":"2.0","method":"hostgroup.get","params":{"filter":{"name":["'"${AUTOREG_GROUP_NAME}"'"]}},"id":1,"auth":"'"${ZBX_API_AUTH}"'"}' \
      "${ZBX_API_URL}" | jq -r '.result[0].groupid // empty')

    if [[ -z "${AUTOREG_GROUP_ID}" ]]; then
      AUTOREG_GROUP_ID=$(curl -s -X POST -H 'Content-Type: application/json-rpc' \
        -d '{"jsonrpc":"2.0","method":"hostgroup.create","params":{"name":"'"${AUTOREG_GROUP_NAME}"'"},"id":1,"auth":"'"${ZBX_API_AUTH}"'"}' \
        "${ZBX_API_URL}" | jq -r '.result.groupids[0] // empty')
      [[ -n "${AUTOREG_GROUP_ID}" ]] && success "Host group '${AUTOREG_GROUP_NAME}' created (id ${AUTOREG_GROUP_ID})." \
        || warn "Could not create host group '${AUTOREG_GROUP_NAME}' -- check the API response manually."
    else
      success "Host group '${AUTOREG_GROUP_NAME}' already exists (id ${AUTOREG_GROUP_ID})."
    fi

    # UNVERIFIED (flagged, not asserted as fact): Zabbix's autoregistration API surface has
    # changed across major versions -- pre-6.4 used action.create with eventsource=2 for the
    # whole ruleset; 6.4+ split this into autoregistration.update (host-metadata matching rules)
    # plus a normal action.create (eventsource=2, "on registration" trigger -> add to group).
    # This uses the 6.4+ shape, which 7.0 (being newer than 6.4) is expected to still use, but
    # has NOT been confirmed against the real Zabbix 7.0 API docs -- check Administration ->
    # General -> Autoregistration in the UI after this runs to confirm it actually took effect.
    if [[ -n "${AUTOREG_GROUP_ID}" ]]; then
      info "Creating autoregistration action (new registrations -> ${AUTOREG_GROUP_NAME})..."
      curl -s -X POST -H 'Content-Type: application/json-rpc' \
        -d '{"jsonrpc":"2.0","method":"action.create","params":{"name":"Auto-add to '"${AUTOREG_GROUP_NAME}"'","eventsource":2,"status":0,"filter":{"evaltype":0,"conditions":[]},"operations":[{"operationtype":4,"opgroup":[{"groupid":"'"${AUTOREG_GROUP_ID}"'"}]}]},"id":1,"auth":"'"${ZBX_API_AUTH}"'"}' \
        "${ZBX_API_URL}" > /tmp/zbx-autoreg-action.json
      if jq -e '.result' /tmp/zbx-autoreg-action.json > /dev/null 2>&1; then
        success "Autoregistration action created."
      else
        warn "Autoregistration action creation returned: $(cat /tmp/zbx-autoreg-action.json)"
        warn "Check/create it manually: Administration -> Actions -> Autoregistration actions"
      fi
      rm -f /tmp/zbx-autoreg-action.json
    fi
  fi
fi

# ------------------------------------------------------------------------------
# Section 14 — Dynamic MOTD
# ------------------------------------------------------------------------------
section "14. Dynamic MOTD"

cat > /etc/update-motd.d/10-examplemusic << MOTD
#!/usr/bin/env bash
WH='\033[1;37m'; YL='\033[1;33m'; GR='\033[0;32m'; CY='\033[0;36m'; NC='\033[0m'
UPTIME=\$(uptime -p)
LOAD=\$(cut -d' ' -f1-3 /proc/loadavg)
MEM_TOTAL=\$(awk '/MemTotal/{print int(\$2/1024)}' /proc/meminfo)
MEM_FREE=\$(awk '/MemAvailable/{print int(\$2/1024)}' /proc/meminfo)
MEM_USED=\$(( MEM_TOTAL - MEM_FREE ))
DISK=\$(df -h / | awk 'NR==2{print \$3" used of "\$2" ("\$5")"}')
ZBX_STATUS=\$(systemctl is-active zabbix-server 2>/dev/null || echo "unknown")
DB_SIZE=\$(mysql -u${ZABBIX_DB_USER} -p${ZABBIX_DB_PASSWORD} -N -e "SELECT ROUND(SUM(data_length+index_length)/1024/1024) FROM information_schema.tables WHERE table_schema='${ZABBIX_DB_NAME}';" 2>/dev/null || echo "?")
echo -e "
\${WH}╔══════════════════════════════════════════════════════════════╗\${NC}
\${WH}║     EXAMPLE MUSIC LIMITED: \$(printf '%-35s' "\${HOSTNAME}")║\${NC}
\${WH}╚══════════════════════════════════════════════════════════════╝\${NC}

  \${YL}Site     :\${NC} ${SITE_CODE}: ${SITE_DISPLAY_CITY}, ${SITE_DISPLAY_COUNTRY}
  \${YL}Entity   :\${NC} ${SITE_DISPLAY_ENTITY}
  \${YL}Role     :\${NC} Zabbix monitoring server

  \${WH}── Zabbix ───────────────────────────────────────────────────\${NC}
    \${CY}Server\${NC}    : \${GR}\${ZBX_STATUS}\${NC}
    \${CY}Web UI\${NC}    : \${GR}http://${ZBX_FQDN}/\${NC}
    \${CY}DB size\${NC}   : \${GR}\${DB_SIZE} MB\${NC}

  \${WH}── System ───────────────────────────────────────────────────\${NC}
    \${CY}Uptime\${NC}    : \${GR}\${UPTIME}\${NC}
    \${CY}Load\${NC}      : \${GR}\${LOAD}\${NC}
    \${CY}Memory\${NC}    : \${GR}\${MEM_USED}MB\${NC} used of \${MEM_TOTAL}MB
    \${CY}Disk /\${NC}    : \${GR}\${DISK}\${NC}

  \${WH}── Quick reference ──────────────────────────────────────────\${NC}
    \${CY}Logs        :\${NC} tail -f /var/log/zabbix/zabbix_server.log
    \${CY}Restart     :\${NC} systemctl restart zabbix-server
    \${CY}DB creds    :\${NC} ${DB_CREDS_FILE}
    \${CY}API creds   :\${NC} ${API_CREDS_FILE}
"
MOTD

chmod +x /etc/update-motd.d/10-examplemusic

if grep -q "^PrintMotd" /etc/ssh/sshd_config 2>/dev/null; then
  sed -i "s/^PrintMotd.*/PrintMotd yes/" /etc/ssh/sshd_config
else
  echo "PrintMotd yes" >> /etc/ssh/sshd_config
fi

cat > /etc/profile.d/motd.sh << 'EOF'
[[ -x /etc/update-motd.d/10-examplemusic ]] && /etc/update-motd.d/10-examplemusic
EOF

systemctl restart ssh 2>/dev/null || true
success "Dynamic MOTD configured."

# ------------------------------------------------------------------------------
# Section 15 — Sentinel file
# ------------------------------------------------------------------------------
{
  echo "Configured by Example Music zabbixme.sh"
  echo "Site        : ${SITE_CODE}"
  echo "City        : ${SITE_DISPLAY_CITY}"
  echo "Country     : ${SITE_DISPLAY_COUNTRY}"
  echo "Entity      : ${SITE_DISPLAY_ENTITY}"
  echo "Hostname    : ${THIS_HOSTNAME}"
  echo "Static IP   : ${NODE_STATIC_IP}"
  echo "Zabbix URL  : http://${ZBX_FQDN}/"
  echo "Zabbix ver  : ${ZABBIX_MAJOR} (candidate ${CANDIDATE_VER:-unknown})"
  echo "Date        : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${SENTINEL}"
chmod 0444 "${SENTINEL}"
success "Sentinel file written to ${SENTINEL}"

# ------------------------------------------------------------------------------
# Final banner
# ------------------------------------------------------------------------------
echo
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  SETUP COMPLETE — ${THIS_HOSTNAME}${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "${CYAN}  Site        : ${SITE_CODE} — ${SITE_DISPLAY_CITY}, ${SITE_DISPLAY_COUNTRY}${NC}"
echo -e "${CYAN}  Hostname    : ${THIS_HOSTNAME}${NC}"
echo -e "${CYAN}  Static IP   : ${NODE_STATIC_IP} (takes effect on reboot)${NC}"
echo -e "${CYAN}  Zabbix URL  : http://${ZBX_FQDN}/  (also: http://${NODE_STATIC_IP}/)${NC}"
echo

echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}  ║   CREDENTIALS — READ THIS BEFORE THE TERMINAL SCROLLS AWAY   ║${NC}"
echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "  ${WHITE}DB (root-only file)${NC}  : ${GREEN}${DB_CREDS_FILE}${NC}"
echo -e "  ${WHITE}API/Admin (root-only)${NC}: ${GREEN}${API_CREDS_FILE}${NC}"
echo -e "  ${YELLOW}Store both in the password manager, then consider removing the files.${NC}"
echo

echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}  ║   REMAINING MANUAL / FOLLOW-UP STEPS                          ║${NC}"
echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "  ${WHITE}1.${NC} Confirm the Zabbix ${ZABBIX_MAJOR} package availability finding in this file's own"
echo -e "     version-history comment actually resolved cleanly on this real run (it may not"
echo -e "     have — this was the one thing this script's design couldn't fully verify in"
echo -e "     advance)."
echo -e "  ${WHITE}2.${NC} Confirm the autoregistration action actually took effect:"
echo -e "     ${CYAN}Administration → Actions → Autoregistration actions${NC}"
echo -e "  ${WHITE}3.${NC} role_codes.csv / devices.csv have no ZBX row yet — add one with a real CLD"
echo -e "     octet once this build is confirmed good."
echo -e "  ${WHITE}4.${NC} Agent deployment is explicitly OUT of scope for this script:"
echo -e "     ${CYAN}TODO: Linux agent — Ansible playbook (EnableRemoteCommands, zabbix_agentd.conf)${NC}"
echo -e "     ${CYAN}TODO: Windows agent — Salt module${NC}"
echo -e "     ${CYAN}TODO: curl/wget on every device for auto-registration (agent-side, not server-side)${NC}"
echo
echo -e "${GREEN}============================================================${NC}"
echo
