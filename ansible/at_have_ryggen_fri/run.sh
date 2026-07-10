#!/usr/bin/env bash
# ==============================================================================
# at_have_ryggen_fri/run.sh
# Example Music Limited — Ansible verification harness
# ==============================================================================
# "At have ryggen fri" -- Danish: to have your back covered.
#
# Runs everything this repo has learned it needs to check the hard way, in one
# place, so the next change doesn't silently reintroduce a bug already found
# and fixed once:
#   1. YAML validity        -- every *.yml under ansible/ parses.
#   2. ansible-playbook --syntax-check on every real playbook (files with a
#      top-level hosts: key; task-fragment files are exercised indirectly via
#      whatever includes them).
#   3. check_references.py  -- every literal (non-Jinja) template:/copy:/
#      win_copy:/include_tasks:/import_tasks:/import_playbook: path actually
#      resolves to a real file on disk.
#   4. check_inventory_structure.py -- the real configs/inventory has the
#      windows_dc -> windows_server -> windows -> windows_nodes chain, and
#      group_vars genuinely resolves (become correctly scoped to Linux only,
#      colours.yml's _c dict present) -- no live host is ever contacted.
#   5. add_host_probe/      -- add_host in one play is visible, with correct
#      group_vars, to a later play in the same run (the mechanism
#      windows_bootstrap/00-preflight.yml's Phase H2 depends on).
#
# Nothing here touches a real host, needs a vault password, or needs network
# access beyond localhost -- safe to run any time, by anyone, on any clone.
#
# Usage:
#   ./run.sh
#
# Changelog:
#   2026-07-10  Initial version.
# ==============================================================================
set -uo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'
info()    { echo -e "${CYAN}[*]${NC} $*"; }
success() { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*" >&2; }
fail()    { echo -e "${RED}[✗]${NC} $*" >&2; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
section() { echo; echo -e "${WHITE}── $* ──${NC}"; echo; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(cd "${HERE}/.." && pwd)"
REPO_ROOT="$(cd "${ANSIBLE_DIR}/.." && pwd)"

command -v ansible-playbook >/dev/null || die "ansible-playbook not found on PATH"
command -v python3         >/dev/null || die "python3 not found on PATH"

FAILED_CHECKS=()

# ------------------------------------------------------------------------------
# 1. YAML validity
# ------------------------------------------------------------------------------
section "1. YAML validity — every *.yml under ansible/"

yaml_errors=0
while IFS= read -r -d '' f; do
  # Ansible-vault-encrypted values use a !vault YAML tag that plain PyYAML
  # doesn't know how to construct -- register a no-op constructor for it
  # (this checks structural validity, not that we can decrypt secrets).
  if ! python3 -c "
import sys, yaml
class L(yaml.SafeLoader): pass
L.add_constructor('!vault', lambda loader, node: '<vault-encrypted>')
list(yaml.load_all(open(sys.argv[1]), Loader=L))
" "$f" 2>/tmp/ryggen_fri_yaml_err; then
    fail "$(realpath --relative-to="$REPO_ROOT" "$f"): $(tail -1 /tmp/ryggen_fri_yaml_err)"
    (( yaml_errors++ ))
  fi
done < <(find "$ANSIBLE_DIR" -name "*.yml" -not -path "*/at_have_ryggen_fri/*" -print0)
rm -f /tmp/ryggen_fri_yaml_err

if [[ $yaml_errors -eq 0 ]]; then
  success "All YAML files parse cleanly."
else
  fail "$yaml_errors YAML file(s) failed to parse."
  FAILED_CHECKS+=("YAML validity")
fi

# ------------------------------------------------------------------------------
# 2. ansible-playbook --syntax-check on every real playbook
# ------------------------------------------------------------------------------
section "2. ansible-playbook --syntax-check"

syntax_errors=0
syntax_checked=0
while IFS= read -r -d '' f; do
  # Only files with a top-level "hosts:" key are real playbooks -- task
  # fragment files (included via include_tasks) aren't valid --syntax-check
  # targets on their own and are exercised indirectly via whatever includes
  # them (caught by check_references.py instead).
  if ! grep -qE '^\s*hosts:' "$f"; then
    continue
  fi
  (( syntax_checked++ ))
  rel="$(realpath --relative-to="$ANSIBLE_DIR" "$f")"
  # cd into ansible/ first: ansible.cfg's roles_path is relative to cwd, and
  # is only picked up by Ansible's own config auto-discovery when it's the
  # current directory (see docs/ansible/beginners_guide_to_ansible.md's
  # "Inventory and group_vars" section -- the same "the loaded path IS the
  # search path" principle, applied to roles_path instead of inventory).
  # -e target=/-e ad_forest_json_path= are harmless for playbooks that don't
  # use them, and let --syntax-check get past vars_prompt defaults that
  # reference {{ target }} or a real control node's /etc/example-music/
  # ad_forest.json (which doesn't exist in this sandbox) without either
  # being a genuine playbook bug.
  if ! out=$(cd "$ANSIBLE_DIR" && ansible-playbook --syntax-check \
        -i configs/inventory "$rel" \
        -e target=_ryggen_fri_syntax_check_dummy_ \
        -e "ad_forest_json_path=${REPO_ROOT}/benarbejde/ad_forest.json" 2>&1); then
    fail "$(realpath --relative-to="$REPO_ROOT" "$f")"
    echo "$out" | sed 's/^/      /'
    (( syntax_errors++ ))
  fi
done < <(find "$ANSIBLE_DIR/playbooks" -name "*.yml" -print0)

info "Syntax-checked $syntax_checked playbook file(s)."
if [[ $syntax_errors -eq 0 ]]; then
  success "All playbooks pass --syntax-check."
else
  fail "$syntax_errors playbook(s) failed --syntax-check."
  FAILED_CHECKS+=("ansible-playbook --syntax-check")
fi

# ------------------------------------------------------------------------------
# 3. Reference integrity (templates / copy / win_copy / includes)
# ------------------------------------------------------------------------------
section "3. Reference integrity — check_references.py"

if python3 "${HERE}/check_references.py"; then
  success "All literal file references resolved."
else
  fail "Broken file reference(s) found -- see above."
  FAILED_CHECKS+=("check_references.py")
fi

# ------------------------------------------------------------------------------
# 4. Real inventory structure + group_vars resolution
# ------------------------------------------------------------------------------
section "4. Inventory structure — check_inventory_structure.py"

if python3 "${HERE}/check_inventory_structure.py"; then
  success "Inventory structure and group_vars assertions passed."
else
  fail "Inventory structure/group_vars assertion(s) failed -- see above."
  FAILED_CHECKS+=("check_inventory_structure.py")
fi

# ------------------------------------------------------------------------------
# 5. add_host visibility probe
# ------------------------------------------------------------------------------
section "5. add_host visibility — add_host_probe/"

if out=$(cd "${HERE}/add_host_probe" && ansible-playbook -i inventory.ini playbook.yml 2>&1); then
  success "add_host -> group_vars visibility confirmed."
else
  fail "add_host visibility probe failed:"
  echo "$out" | sed 's/^/      /'
  FAILED_CHECKS+=("add_host_probe")
fi

# ------------------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------------------
section "Summary"

if [[ ${#FAILED_CHECKS[@]} -eq 0 ]]; then
  success "Ryggen er fri — all checks passed."
  exit 0
else
  fail "${#FAILED_CHECKS[@]} check(s) failed:"
  for c in "${FAILED_CHECKS[@]}"; do
    echo -e "  ${RED}✗${NC} $c"
  done
  exit 1
fi
