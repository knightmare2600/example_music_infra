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
#   6. check_generated_freshness.py -- configs/inventory/*.ini, site_services.yml,
#      and begyndelse.json are re-derivable byte-for-byte from
#      benarbejde/sites.csv+devices.csv+address_policy.json+ad_forest.json --
#      catches "edited the source, forgot to regenerate."
#   7. check_doc_index.py   -- docs/INDEX.md: every link resolves to a real
#      file (fails if not); every real doc under docs/ is linked from it
#      (warns if not -- some are deliberately excluded, see the script).
#   8. check_facts.py       -- facts.yml: a short, hand-curated list of
#      specific facts (an IP, a hostname) restated as prose across multiple
#      docs/scripts, confirmed still true in every file that asserts them.
#   9. check_scenarios.py   -- scenarios.yml: the four bare-metal-to-working-
#      estate scenarios (PVE+Ansible node, DNS, firewall, Windows unattend)
#      -- confirms every file each depends on still exists and a handful of
#      load-bearing warnings/framing comments haven't been edited away.
#      Doesn't build real infrastructure -- see scenarios.yml's own header.
#
# Nothing here touches a real host, needs a vault password, or needs network
# access beyond localhost -- safe to run any time, by anyone, on any clone.
#
# Usage:
#   ./run.sh
#
# Changelog:
#   2026-07-10  Initial version.
#   2026-07-10  Phase 1 of the repo-wide extrapolation: added
#               check_generated_freshness.py, check_doc_index.py, and
#               check_facts.py (sections 6-8). check_references.py also
#               gained loop+item.attr resolution this same day (see its own
#               header) -- together these extend the "does everything that's
#               referenced actually exist / actually agree" philosophy from
#               just Ansible playbooks to benarbejde/'s generated files and
#               docs/INDEX.md.
#   2026-07-10  Phase 2: added check_scenarios.py (section 9), covering the
#               four bare-metal bootstrap scenarios discussed with Robert.
#               Landed alongside a full correction pass on
#               docs/bootstrap/bootstrapping.md (prompted by researching
#               these scenarios and finding it substantially stale) and the
#               2 stale docs check_facts.py's first real facts caught
#               (docs/buildsheets/buildsheet-firewall.md,
#               docs/inventory/EXADNSVRK001-dns.md) -- harness is fully
#               green again as of this entry.
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

ref_out=$(python3 "${HERE}/check_references.py")
ref_rc=$?
echo "$ref_out"
if [[ $ref_rc -ne 0 ]]; then
  fail "Broken file reference(s) found -- see above."
  FAILED_CHECKS+=("check_references.py")
elif echo "$ref_out" | grep -q "drop-in asset(s)"; then
  warn "All references resolve, but some drop-in assets aren't present yet (see above) -- expected on a fresh clone."
else
  success "All literal file references resolved."
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
# 6. Generated-file freshness (benarbejde/ -> configs/inventory/, begyndelse.json)
# ------------------------------------------------------------------------------
section "6. Generated-file freshness — check_generated_freshness.py"

if out=$(python3 "${HERE}/check_generated_freshness.py"); then
  echo "$out"
  success "All generated files are fresh."
else
  echo "$out"
  fail "Generated file(s) have drifted from benarbejde/ -- see above."
  FAILED_CHECKS+=("check_generated_freshness.py")
fi

# ------------------------------------------------------------------------------
# 7. Documentation index integrity — docs/INDEX.md
# ------------------------------------------------------------------------------
section "7. Documentation index — check_doc_index.py"

idx_out=$(python3 "${HERE}/check_doc_index.py")
idx_rc=$?
echo "$idx_out"
if [[ $idx_rc -ne 0 ]]; then
  fail "docs/INDEX.md has broken link(s) -- see above."
  FAILED_CHECKS+=("check_doc_index.py")
elif echo "$idx_out" | grep -q "not linked from docs/INDEX.md"; then
  warn "docs/INDEX.md has no broken links, but some real docs aren't indexed (see above)."
else
  success "docs/INDEX.md is complete and every link resolves."
fi

# ------------------------------------------------------------------------------
# 8. Hand-curated cross-file facts — facts.yml
# ------------------------------------------------------------------------------
section "8. Cross-file facts — check_facts.py"

if out=$(python3 "${HERE}/check_facts.py"); then
  echo "$out"
  success "All registered facts hold everywhere they're asserted."
else
  echo "$out"
  fail "Registered fact(s) have drifted -- see above."
  FAILED_CHECKS+=("check_facts.py")
fi

# ------------------------------------------------------------------------------
# 9. Bare-metal bootstrap scenarios — scenarios.yml
# ------------------------------------------------------------------------------
section "9. Bootstrap scenarios — check_scenarios.py"

if out=$(python3 "${HERE}/check_scenarios.py"); then
  echo "$out"
  success "All 4 bootstrap scenarios' required files and assertions hold."
else
  echo "$out"
  fail "Bootstrap scenario check(s) failed -- see above."
  FAILED_CHECKS+=("check_scenarios.py")
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
