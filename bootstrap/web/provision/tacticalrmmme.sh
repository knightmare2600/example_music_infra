#!/usr/bin/env bash
# ==============================================================================
# Example Music Limited — TacticalRMM Break-Glass Install Wrapper
# EXARMMCLD001 (CLD-hosted TacticalRMM server)
#
# Wraps the upstream install.sh (github.com/amidaware/tacticalrmm) -- does NOT
# reimplement anything it does. install.sh remains the single source of truth
# for package installs, repo clones, DB setup, and Django migrations; this
# script only pre-flights, patches the Debian-version gate for Trixie, and
# captures/prints what install.sh generates that would otherwise only exist
# in terminal scrollback.
#
# BREAK-GLASS TOOL, matching bindme.sh/rudderme.sh's convention (Robert,
# 2026-08-05): interactive, root-run, ends in a REMAINING MANUAL STEPS banner.
# Location matches those two for consistency even though (unlike them) this
# step runs AFTER ansible/playbooks/tacticalrmm/tacticalrmm_server.yml and
# ansible/playbooks/bind9/bind9-dns.yml have already provisioned the box and
# its DNS records -- see PLAN-tacticalrmmme.md in that playbook's directory
# for the full design rationale and the five observations this was built
# from.
#
# Full design plan: ansible/playbooks/tacticalrmm/PLAN-tacticalrmmme.md
#
# -------------------------------------------------------------------------------------------------
# Version history
# -------------------------------------------------------------------------------------------------
# v1.0.0  2026-08-05  Phase 1 only: pre-flight checks (hostname sanity, RAM,
#                     existing-install, DNS). Fetch/patch, answer cheat-sheet,
#                     TOTP capture, and credential banner phases not yet
#                     written -- see PLAN-tacticalrmmme.md.
# -------------------------------------------------------------------------------------------------

set -euo pipefail

# ------------------------------------------------------------------------------
# Colour helpers — identical to bindme.sh / rudderme.sh
# ------------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'
info()    { echo -e "${CYAN}[*]${NC} $*"; }
success() { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*" >&2; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
section() { echo; echo -e "${WHITE}── $* ──${NC}"; echo; }

# ------------------------------------------------------------------------------
# Must run as root
# ------------------------------------------------------------------------------
[[ $EUID -ne 0 ]] && die "Run this script with sudo or as root."

# ------------------------------------------------------------------------------
# Constants — single CLD target, not multi-site like bindme.sh/rudderme.sh
# ------------------------------------------------------------------------------
EXPECTED_HOSTNAME="EXARMMCLD001"
EXPECTED_IP="192.168.69.14"
ROOT_DOMAIN="jukebox.internal"
SUBDOMAINS=(rmm api mesh)
MIN_RAM_MB=4096
RMM_INSTALL_DIR="/rmm"

# ------------------------------------------------------------------------------
# Banner
# ------------------------------------------------------------------------------
echo
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          Example Music:- TacticalRMM Install Wrapper          ║${NC}"
echo -e "${CYAN}║                      tacticalrmmme.sh                         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}  Running on hostname: ${GREEN}$(hostname)${NC}"
echo

# ------------------------------------------------------------------------------
# Section 1 — Pre-flight checks
# ------------------------------------------------------------------------------
section "1. Pre-flight checks"

# 1a. Hostname sanity — this script targets EXARMMCLD001 only, unlike the
# multi-site bindme.sh/rudderme.sh.
CURRENT_HOSTNAME=$(hostname -s)
if [[ "${CURRENT_HOSTNAME^^}" != "${EXPECTED_HOSTNAME}" ]]; then
  die "This script is written for ${EXPECTED_HOSTNAME} only. Current hostname is '${CURRENT_HOSTNAME}'. Refusing to continue on the wrong box."
fi
success "Hostname confirmed: ${EXPECTED_HOSTNAME}"

# 1b. RAM check — install.sh itself hard-fails partway through with
# "ERROR: A minimum of 4GB of RAM is required", but only after several
# minutes of apt work and, per the first live run, after the TOTP QR code
# had already been generated once. Catch this in under a second instead.
TOTAL_RAM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
if [[ "${TOTAL_RAM_MB}" -lt "${MIN_RAM_MB}" ]]; then
  die "Only ${TOTAL_RAM_MB}MB RAM available, install.sh requires at least ${MIN_RAM_MB}MB. Resize the VM before continuing -- do not proceed, this will waste a TOTP setup key (see PLAN-tacticalrmmme.md Phase 4)."
fi
success "RAM check passed: ${TOTAL_RAM_MB}MB available (minimum ${MIN_RAM_MB}MB)."

# 1c. Existing-install check
if [[ -d "${RMM_INSTALL_DIR}" ]]; then
  die "${RMM_INSTALL_DIR} already exists -- TacticalRMM appears to be already installed on this box. Refusing to run install.sh again blind. If a reinstall is genuinely intended, remove or move ${RMM_INSTALL_DIR} first and re-run."
fi
success "No existing install found at ${RMM_INSTALL_DIR}."

# 1d. DNS resolution check — the whole reason this section exists: verify
# all three subdomains resolve, and resolve to this box's own IP, before
# install.sh gets anywhere near them.
info "Checking DNS records resolve to ${EXPECTED_IP} before continuing..."
DNS_FAILED=0
for sub in "${SUBDOMAINS[@]}"; do
  fqdn="${sub}.${ROOT_DOMAIN}"
  resolved_ip=$(getent hosts "${fqdn}" | awk '{print $1}' | head -1)
  if [[ -z "${resolved_ip}" ]]; then
    warn "${fqdn} does not resolve at all."
    DNS_FAILED=1
  elif [[ "${resolved_ip}" != "${EXPECTED_IP}" ]]; then
    warn "${fqdn} resolves to ${resolved_ip}, expected ${EXPECTED_IP}."
    DNS_FAILED=1
  else
    success "${fqdn} → ${resolved_ip}"
  fi
done

if [[ "${DNS_FAILED}" -eq 1 ]]; then
  die "One or more DNS records are missing or wrong. Run: ansible-playbook playbooks/bind9/bind9-dns.yml --tags zones-full,reload -- then re-run this script. Not proceeding with install.sh until all three resolve correctly."
fi

success "All pre-flight checks passed."

# ------------------------------------------------------------------------------
# Section 2 — Fetch and patch install.sh
# ------------------------------------------------------------------------------
section "2. Fetch and patch install.sh"

INSTALL_SH_URL="https://raw.githubusercontent.com/amidaware/tacticalrmm/master/install.sh"
WORKDIR="/root/tacticalrmmme"
INSTALL_SH_PATH="${WORKDIR}/install.sh"

mkdir -p "${WORKDIR}"
cd "${WORKDIR}"

# Ansible's own tacticalrmm_server.yml provisioning almost certainly already
# installed these, but check rather than assume -- same defensive habit
# bindme.sh/rudderme.sh use for their own BASE_PKGS.
MISSING_PKGS=()
command -v curl    &>/dev/null || MISSING_PKGS+=(curl)
command -v python3 &>/dev/null || MISSING_PKGS+=(python3)
if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
  info "Installing: ${MISSING_PKGS[*]}"
  apt-get update -qq 2>&1 | grep -E "^(Err|W:|E:)" || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${MISSING_PKGS[@]}"
fi

# Always download fresh from upstream -- never vendor/fork a local copy.
# install.sh is the "known source of truth" (Robert, 2026-08-05); keeping a
# local copy would let it silently drift from what upstream actually ships.
info "Downloading install.sh from upstream..."
curl -fsSL -o "${INSTALL_SH_PATH}" "${INSTALL_SH_URL}"
success "Downloaded to ${INSTALL_SH_PATH}"

# Patch the Debian-version gate to allow Trixie through. Verified against
# the real upstream script (fetched 2026-08-05), not guessed:
#   if [[ "$relno" -ne 11 && "$relno" -ne 12 ]]; then
# widened to also allow relno 13 (Trixie) -- matches Robert's own
# hand-patched copy from the first live run exactly. Done via python3
# rather than sed: a literal string match/replace needs no regex-escaping
# of the many [[ ]] $ characters in the target line, and a failed match is
# easy to detect and treat as a hard failure rather than a silent sed no-op.
info "Patching OS-version check for Debian Trixie..."
PATCH_RESULT=$(python3 - "${INSTALL_SH_PATH}" <<'PYEOF'
import sys
path = sys.argv[1]
unpatched = 'if [[ "$relno" -ne 11 && "$relno" -ne 12 ]]; then'
patched = 'if [[ "$relno" -ne 11 && "$relno" -ne 12 && "$relno" -ne 13 ]]; then'
text = open(path, encoding="utf-8").read()
if patched in text:
    print("ALREADY_PATCHED")
elif unpatched in text:
    open(path, "w", encoding="utf-8").write(text.replace(unpatched, patched, 1))
    print("PATCHED")
else:
    print("LINE_NOT_FOUND")
PYEOF
)

case "${PATCH_RESULT}" in
  PATCHED)
    success "OS-version check patched to allow Debian 13 (Trixie)."
    ;;
  ALREADY_PATCHED)
    success "OS-version check already allows Debian 13 (Trixie) -- nothing to do."
    ;;
  LINE_NOT_FOUND)
    die "Could not find the expected OS-version-check line in install.sh -- upstream has changed it since this patch was written (2026-08-05). Do NOT proceed blindly: inspect ${INSTALL_SH_PATH} by hand, find the current version-check block (search for 'Only Debian'), and update the unpatched/patched strings in this script (Section 2) to match before re-running."
    ;;
  *)
    die "Unexpected output from the patch step: '${PATCH_RESULT}'"
    ;;
esac

chmod +x "${INSTALL_SH_PATH}"

# ------------------------------------------------------------------------------
# Section 3 — Answers you'll need for install.sh
# ------------------------------------------------------------------------------
section "3. Answers you'll need for install.sh"

# install.sh has no non-interactive bypass (no flags/env vars/config file --
# confirmed against the real script) and ansible.builtin.expect was already
# rejected, 2026-08-04, for the risk of a scripted prompt-feed dying partway
# through after install.sh has made irreversible changes. This section can't
# feed the prompts for you -- it only makes sure you're not hunting through
# a README for the answers while install.sh sits there waiting.

read -rp "  Admin/notification email address [webmaster@${ROOT_DOMAIN}]: " ADMIN_EMAIL_INPUT
ADMIN_EMAIL="${ADMIN_EMAIL_INPUT:-webmaster@${ROOT_DOMAIN}}"

# Suggest whoever actually invoked this script (via sudo) rather than
# hardcoding a name -- falls back to "admin" if run as a true root login
# with no SUDO_USER set.
SUGGESTED_ADMIN_USER="${SUDO_USER:-admin}"
read -rp "  Django admin username [${SUGGESTED_ADMIN_USER}]: " DJANGO_ADMIN_USER_INPUT
DJANGO_ADMIN_USER="${DJANGO_ADMIN_USER_INPUT:-${SUGGESTED_ADMIN_USER}}"

echo
info "Confirm before continuing:"
echo -e "    ${CYAN}Admin email${NC}            : ${GREEN}${ADMIN_EMAIL}${NC}"
echo -e "    ${CYAN}Django admin username${NC}  : ${GREEN}${DJANGO_ADMIN_USER}${NC}"
echo
read -rp "  Correct? [Y/n]: " CONFIRM_ANSWERS
CONFIRM_ANSWERS="${CONFIRM_ANSWERS:-Y}"
[[ "${CONFIRM_ANSWERS}" =~ ^[Yy] ]] || die "Aborted -- re-run and enter the correct values."

echo
echo -e "${YELLOW}  ╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}  ║   install.sh WILL ASK YOU THESE -- ANSWER EXACTLY AS BELOW    ║${NC}"
echo -e "${YELLOW}  ╚══════════════════════════════════════════════════════════════╝${NC}"
echo
printf "  %-28s %s\n" "Root domain:" "${ROOT_DOMAIN}"
for sub in "${SUBDOMAINS[@]}"; do
  case "${sub}" in
    rmm)  label="Frontend (rmm) subdomain:" ;;
    api)  label="Backend (api) subdomain:" ;;
    mesh) label="Mesh subdomain:" ;;
    *)    label="${sub} subdomain:" ;;
  esac
  printf "  %-28s %s\n" "${label}" "${sub}.${ROOT_DOMAIN}"
done
printf "  %-28s %s\n" "Email address:" "${ADMIN_EMAIL}"
printf "  %-28s %s\n" "Django admin username:" "${DJANGO_ADMIN_USER}"
echo
warn "install.sh's subdomain prompts want the FULL fqdn (e.g. 'rmm.${ROOT_DOMAIN}'), not just 'rmm' -- confirmed from the real transcript of the first live run."
warn "install.sh will separately prompt for the Django admin password with its own confirmation -- type it in yourself, nothing here feeds it."
echo
read -rp "  Press Enter once ready to launch install.sh interactively..." _

# ------------------------------------------------------------------------------
# Phase 4 onward (run install.sh with TOTP capture, credentials banner) not
# yet written -- see PLAN-tacticalrmmme.md.
# ------------------------------------------------------------------------------
