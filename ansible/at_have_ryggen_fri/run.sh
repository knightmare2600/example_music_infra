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
#   1. YAML validity        -- every git-tracked *.yml/*.yaml in the whole repo
#      parses (via git ls-files, not a directory walk -- automatically covers
#      new files anywhere, not just ansible/).
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
#   7. check_doc_index.py   -- every relative link in every git-tracked *.md
#      file in the whole repo (not just docs/) resolves to a real file
#      (fails if not); separately, docs/INDEX.md specifically is checked for
#      completeness -- every real doc under docs/ linked from it (warns if
#      not -- some are deliberately excluded, see the script).
#   8. check_facts.py       -- facts.yml: a short, hand-curated list of
#      specific facts (an IP, a hostname) restated as prose across multiple
#      docs/scripts, confirmed still true in every file that asserts them.
#   9. check_scenarios.py   -- scenarios.yml: the four bare-metal-to-working-
#      estate scenarios (PVE+Ansible node, DNS, firewall, Windows unattend)
#      -- confirms every file each depends on still exists and a handful of
#      load-bearing warnings/framing comments haven't been edited away.
#      Doesn't build real infrastructure -- see scenarios.yml's own header.
#  10. check_site_data.py  -- benarbejde/sites.csv is read fresh every run:
#      every site code appears somewhere in docs/*.md, and every doc line
#      naming exactly one site code alongside a literal IP has the right
#      octet for that site. Runs against current sites.csv every time, so
#      any future edit to it is re-checked automatically, not just audited
#      once by hand.
#  11. check_ssh_keys.py -- bootstrap/web/ansible_sshkey.pub (the estate's
#      one committed public key) is checked against both VRK-answer.toml/
#      FRD-answer.toml's root-ssh-keys copies (clone-safe, a real failure).
#      Separately, host-local: is ansible.cfg's configured private_key_file
#      actually present on THIS host -- informational by default (a bare
#      clone genuinely won't have it), --strict fails on it. If missing,
#      scans ~/.ssh/ for a plausible candidate keypair and reports it.
#  12. check_playbook_dir_paths.py -- every "{{ playbook_dir }}/../.../X"
#      expression (used with read_csv/lookup('file',...)/shell, not the
#      literal src:/include_tasks: paths check 3 already covers) resolves
#      to a real file. Catches copy-pasted-from-a-deeper-file path depth
#      bugs -- found the hard way in bootstrap-new-node.yml, invisible to
#      both check 2 (--syntax-check doesn't execute tasks) and check 3
#      (Jinja, not literal) until a real run finally reached the task.
#  13. check_mermaid.py -- THE ONE EXCEPTION to "no network beyond
#      localhost": every ```mermaid block in every git-tracked *.md file
#      is actually rendered via kroki.io and confirmed to succeed, not
#      just locally syntax-guessed. Found 3 real, otherwise-invisible
#      Mermaid syntax bugs across 49 diagrams this way (literal \n instead
#      of <br/>, a backslash-escaped quote, an unquoted paren inside a
#      pipe-delimited edge label). Results cached by content hash so only
#      new/changed diagrams actually hit kroki.io on a given run. A
#      genuine render failure (HTTP 400, real syntax error) always fails
#      the check; kroki.io being unreachable is informational unless
#      --strict is passed.
#  14. check_network_diagram_freshness.py -- the "New Network (current)"
#      subgraph in every site section under docs/network-diagram/*.md (one
#      file per region -- split 2026-07-13, see docs/network-diagram.md's
#      own header for why; wrapped in %% GENERATED:NEW-NETWORK:<SITE>:
#      START/END marker comments) is re-derivable byte-for-byte from
#      benarbejde/sites.csv+devices.csv+address_policy.json via
#      generate_network_diagrams.py -- same "edited the source, forgot to
#      regenerate" class check 6 already catches for the Ansible inventory,
#      applied to the diagrams.
#  15. check_network_diagram_content.py -- independently scans (not just a
#      second run of the generator) every committed New Network block
#      across docs/network-diagram/*.md for two invariants from the Visual
#      Standard: no FSMO/health/low-disk-space terms ever appear (that data
#      is old-infra-only, per Robert's 2026-07-13 instruction), and every
#      node uses the uniform rect shape with a leading emoji symbol.
#      Catches drift a freshness diff alone wouldn't explain, and a
#      hand-edit that bypasses the generator entirely.
#  16. check_keepass_freshness.py -- Tier 1 (always runs): benarbejde/
#      extracted_credentials.json is well-formed, every entry has its
#      required fields, every role is one push_credentials_to_keepass.py
#      actually knows how to file, no duplicate (hostname, role) pairs.
#      Tier 2 (host-local, informational unless --strict): if this host has
#      both the live vault and the automation master-password file,
#      confirms push_credentials_to_keepass.py --dry-run has nothing left
#      to add -- same "source vs generated artefact" freshness pattern as
#      checks 6/14, applied to the KeePassXC vault. Added 2026-07-14 after
#      two TP-Link entries turned out to carry a stale/wrong password with
#      nothing to have caught it.
#  17. check_wireguard_hub_data.py -- every WireGuard hub (CLD/FAL/ODE/BRK) in
#      group_vars/firewalls/main.yml's wg_hub_wan_ips follows one uniform,
#      derivable convention: WAN IP = 192.168.139.<the hub's own site subnet
#      octet, from sites.csv>. Confirmed against all 4 real hubs before
#      writing this check -- FAL/ODE/BRK were already correct, only CLD had
#      drifted (192.168.139.139, a self-referential typo, instead of the
#      real 192.168.139.69). Also flags any hub with a blank
#      wg_hub_known_pubkeys entry, since that silently skips the live
#      known-good pubkey cross-check for every spoke built against it.
#      Added 2026-07-14 after the wrong CLD WAN IP was found live, during
#      the EXAFWLBRT001 firewallme test, with nothing to have caught it.
#
# Nothing here touches a real host or needs a vault password. ONE exception to
# "network access beyond localhost": check 13 (check_mermaid.py) genuinely
# needs to reach kroki.io to render-test every mermaid diagram -- see its own
# header for why a local syntax guess isn't good enough. Everything else is
# still safe to run any time, by anyone, on any clone, no network required.
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
#   2026-07-10  Repo-wide sweep, per Robert: "The test harness needs to check
#               documentation, truth be told it needs to check the entire
#               repo, so maybe git can 'help' here." Section 1 (YAML
#               validity) switched from an ansible/-only find to `git
#               ls-files` across the whole repo -- picked up 2 previously-
#               unchecked YAML files (benarbejde/ad_computers_vault.yml,
#               docs/zabbix_templates/*.yaml). check_doc_index.py's broken-
#               link check widened from "docs/INDEX.md's own links" to
#               "every relative link in every git-tracked *.md file in the
#               repo" (docs/INDEX.md completeness stays a separate,
#               docs/-specific check) -- found and fixed 2 more real broken
#               links in docs/ExampleMusic_Beginners_Guide.md (same
#               bootstrap/ vs active-directory/ path bug already fixed once
#               in docs/INDEX.md, plus a stray ../ in a same-directory
#               link) that the narrower check had no way to see.
#   2026-07-11  Added a persistent report file (reports/run-<timestamp>.log +
#               reports/latest.log, gitignored -- see the report-file block
#               below) after Robert pointed out check 3's drop-in-binary
#               output (it was already there -- see check_references.py)
#               had nowhere durable to land once terminal scrollback was
#               gone. --no-report added to skip it for callers that already
#               capture output themselves.
#   2026-07-12  Added check_mermaid.py (section 13), per Robert's ask after
#               fixing 3 real Mermaid syntax bugs across the repo's 49
#               diagrams by hand (literal \n, a backslash-escaped quote, an
#               unquoted paren in a pipe-delimited edge label) -- none of
#               which any structural check here could have caught, since
#               they're only real failures against Mermaid's actual parser,
#               not this repo's own YAML/Ansible structure. The one check in
#               this harness that needs real network access (kroki.io) --
#               see its own header for how that's handled safely (cached,
#               --strict-gated on network failure specifically, always hard
#               fails on a genuine syntax error).
#   2026-07-12  Added check_playbook_dir_paths.py (section 12) after
#               bootstrap-new-node.yml's sites_csv_src turned out to have
#               one extra level of ../ the whole time (copy-pasted from
#               00-preflight.yml, which lives one directory deeper) --
#               only surfaced once the SSH keypair preflight (below) let a
#               real run reach that task for the first time. Neither
#               --syntax-check nor check_references.py could ever have
#               caught this class of bug -- see the script's own header.
#   2026-07-12  Added check_ssh_keys.py (section 11), per Robert's 5-point
#               spec after the ansible-id_rsa private key went missing on
#               EXAANSCLD001 mid real-node test -- see that script's own
#               header and ansible/tasks/ssh_key_preflight.yml (the matching
#               real-connectivity playbook-layer check, wired into
#               bootstrap-new-node.yml and 00-preflight.yml). Point 1 of the
#               spec: this harness previously only ever checked a public key
#               exists (repo file presence) -- never the private half.
#   2026-07-11  Added check_site_data.py (section 10), per Robert: "all site
#               codes from sites.csv are in the documentation" and "their
#               subnets, gateways... match", checked automatically every
#               run rather than as a one-off audit. Found and fixed one real
#               bug (buildsheet-firewall.md's ATL row: wrong IP, wrong city
#               name -- leftover from before the fictional GAA/"Georgia AL"
#               code was consolidated into the real ATL/Atlanta). Also
#               surfaced a real, deliberate, previously-undocumented-here
#               convention while tuning out false positives: every site's
#               firewall also has a WAN IP on the provisioning network at
#               192.168.139.<site's own octet> (see
#               docs/inventory/EXADNSVRK001-dns.md) -- the checker now knows
#               to treat that pattern as correct, not a mismatch.
#   2026-07-13  Added check_network_diagram_freshness.py and
#               check_network_diagram_content.py (sections 14-15), landing
#               alongside benarbejde/generate_network_diagrams.py and the
#               "New Network (current)" box added to every site in
#               docs/network-diagram.md. Per Robert's ask: box the old,
#               sparse, hand-maintained diagrams as clearly-legacy, generate
#               a current-state counterpart from sites.csv/devices.csv, and
#               keep both in sync going forward rather than letting them
#               drift apart again the way the .ini/legend files already had
#               (see docs/network-cutover.md -- 18 sites' old diagrams had
#               RTR and FWL's octets genuinely backwards).
#   2026-07-13  Split docs/network-diagram.md's 51 site diagrams into 15
#               per-region files under docs/network-diagram/ -- Robert, after
#               the emoji/uniform-shape pass still left GitHub's renderer
#               unreliable: "there's just simply too much for GitHub to
#               render." docs/network-diagram.md is now an index (Visual
#               Standard, emoji legend, links out) rather than holding every
#               diagram itself. check_network_diagram_freshness.py/_content.py
#               (14-15) and generate_network_diagrams.py's insert_into_docs()
#               all updated to iterate the region files instead of one
#               monolith. Deferred to a later session, per Robert: per-site
#               colour-scheme fixes, CLD's Old Network box arguably
#               mislabelling something that was never really "legacy," and a
#               cloud-emoji/outline idea for the Internet node.
#   2026-07-14  Added check_keepass_freshness.py (section 16), per Robert
#               after two live TP-Link KeePass entries turned out to carry a
#               stale/wrong password with nothing in the harness to have
#               caught it: "It also suggests you likely need to plumb that
#               into the harness." Same Tier 1 (JSON structure, clone-safe)
#               / Tier 2 (live vault, host-local, informational) split as
#               check_ssh_keys.py.
#   2026-07-14  Added check_wireguard_hub_data.py (section 17). Live
#               EXAFWLBRT001 firewallme test found group_vars/firewalls/
#               main.yml's CLD hub WAN IP had been wrong (192.168.139.139,
#               a self-referential typo, instead of the real
#               192.168.139.69) for an unknown length of time -- Robert:
#               "this suggests the harness is also not checking such
#               things against docs, or memories." Checks every hub's WAN
#               IP against the derivable 192.168.139.<site-octet>
#               convention (confirmed against all 4 real hubs first, not
#               assumed), and flags any blank known-good pubkey.
# ==============================================================================
set -uo pipefail

# --strict: promotes "expected, informational" warnings (missing drop-in
# binaries, unindexed docs) to real failures. Added 2026-07-10 after Robert
# pointed out that burying 20 missing ARM64/x86_64 binaries as a generic
# "expected on a fresh clone" yellow line is the wrong default for someone
# actually about to deploy, not just cloning the repo to read it. Default
# behaviour (no flag) is unchanged -- still safe to run on a bare clone with
# nothing dropped in yet.
# --no-report: skip writing the report file (see below) -- for callers that
# only want the terminal output (e.g. piping into something else already).
STRICT=false
NO_REPORT=false
for arg in "$@"; do
  [[ "$arg" == "--strict" ]] && STRICT=true
  [[ "$arg" == "--no-report" ]] && NO_REPORT=true
done

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

# ------------------------------------------------------------------------------
# Report file — every run's full output (identical to what's on screen,
# colour codes included) is captured to a timestamped file under reports/,
# plus a fixed latest.log that's always overwritten. Added 2026-07-11: this
# harness previously only ever wrote to the terminal -- once scrollback was
# gone, so was the evidence a check had genuinely printed something (Robert
# asked "where is the reporting aspect... there's no output as far as I can
# see" re: the drop-in-binary warnings, which check 3 DOES print -- but
# nothing durable was kept to point at). reports/*.log is covered by the
# repo's existing global *.log gitignore rule -- these are run artefacts,
# not committed history.
if ! $NO_REPORT; then
  REPORT_DIR="${HERE}/reports"
  mkdir -p "$REPORT_DIR"
  REPORT_FILE="${REPORT_DIR}/run-$(date +%Y%m%d-%H%M%S).log"
  LATEST_FILE="${REPORT_DIR}/latest.log"
  exec > >(tee "$REPORT_FILE" "$LATEST_FILE") 2>&1
fi

command -v ansible-playbook >/dev/null || die "ansible-playbook not found on PATH"
command -v python3         >/dev/null || die "python3 not found on PATH"

FAILED_CHECKS=()

# ------------------------------------------------------------------------------
# 1. YAML validity
# ------------------------------------------------------------------------------
section "1. YAML validity — every git-tracked *.yml/*.yaml in the repo"

# git ls-files, not find: only checks files actually tracked (no stray/gitignored
# cruft), and automatically covers new files anywhere in the repo -- benarbejde/ and
# docs/ have their own YAML too (e.g. benarbejde/ad_computers_vault.yml,
# docs/zabbix_templates/*.yaml), previously missed entirely by an ansible/-only scan.
yaml_errors=0
while IFS= read -r -d '' f; do
  case "$f" in
    ansible/at_have_ryggen_fri/*) continue ;;
  esac
  # Ansible-vault-encrypted values use a !vault YAML tag that plain PyYAML
  # doesn't know how to construct -- register a no-op constructor for it
  # (this checks structural validity, not that we can decrypt secrets).
  if ! python3 -c "
import sys, yaml
class L(yaml.SafeLoader): pass
L.add_constructor('!vault', lambda loader, node: '<vault-encrypted>')
list(yaml.load_all(open(sys.argv[1]), Loader=L))
" "$REPO_ROOT/$f" 2>/tmp/ryggen_fri_yaml_err; then
    fail "$f: $(tail -1 /tmp/ryggen_fri_yaml_err)"
    (( yaml_errors++ ))
  fi
done < <(git -C "$REPO_ROOT" ls-files -z -- '*.yml' '*.yaml')
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
drop_in_count=$(echo "$ref_out" | grep -oE '^[0-9]+ drop-in asset' | grep -oE '^[0-9]+' || true)
if [[ $ref_rc -ne 0 ]]; then
  fail "Broken file reference(s) found -- see above."
  FAILED_CHECKS+=("check_references.py")
elif [[ -n "$drop_in_count" && "$drop_in_count" -gt 0 ]]; then
  if $STRICT; then
    fail "${drop_in_count} drop-in asset(s) missing -- see above. Failing because --strict was passed: you said you're about to deploy, not just reading the repo."
    FAILED_CHECKS+=("check_references.py (--strict: drop-in assets missing)")
  else
    warn "${drop_in_count} drop-in asset(s) aren't present yet (see above) -- expected on a fresh clone, but re-run with --strict before an actual deployment to fail on this instead of just warning."
  fi
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
# 7. Markdown link integrity (repo-wide) + docs/INDEX.md completeness
# ------------------------------------------------------------------------------
section "7. Markdown links — check_doc_index.py"

idx_out=$(python3 "${HERE}/check_doc_index.py")
idx_rc=$?
echo "$idx_out"
if [[ $idx_rc -ne 0 ]]; then
  fail "Broken markdown link(s) found -- see above."
  FAILED_CHECKS+=("check_doc_index.py")
elif echo "$idx_out" | grep -q "not linked from docs/INDEX.md"; then
  warn "No broken links, but some real docs aren't indexed in docs/INDEX.md (see above)."
else
  success "No broken markdown links anywhere in the repo; docs/INDEX.md is complete."
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
# 10. Site data coverage/consistency — benarbejde/sites.csv vs docs/
# ------------------------------------------------------------------------------
section "10. Site data — check_site_data.py"

if out=$(python3 "${HERE}/check_site_data.py"); then
  echo "$out"
  success "Every sites.csv site code is documented, no octet mismatches found."
else
  echo "$out"
  fail "Site coverage/consistency check(s) failed -- see above."
  FAILED_CHECKS+=("check_site_data.py")
fi

# ------------------------------------------------------------------------------
# 11. SSH keypair check — check_ssh_keys.py
# ------------------------------------------------------------------------------
section "11. SSH keypair — check_ssh_keys.py"

keys_out=$(python3 "${HERE}/check_ssh_keys.py")
keys_rc=$?
echo "$keys_out"
local_issue_count=$(echo "$keys_out" | grep -oE '^[0-9]+ local-only issue' | grep -oE '^[0-9]+' || true)
if [[ $keys_rc -ne 0 ]]; then
  fail "bootstrap/web/ansible_sshkey.pub has drifted from VRK/FRD-answer.toml -- see above."
  FAILED_CHECKS+=("check_ssh_keys.py")
elif [[ -n "$local_issue_count" && "$local_issue_count" -gt 0 ]]; then
  if $STRICT; then
    fail "${local_issue_count} local SSH keypair issue(s) -- see above. Failing because --strict was passed."
    FAILED_CHECKS+=("check_ssh_keys.py (--strict: local keypair issue)")
  else
    warn "${local_issue_count} local SSH keypair issue(s) (see above) -- expected on a bare clone, but a showstopper on the real control node. Re-run with --strict before an actual deployment."
  fi
else
  success "Public key consistent everywhere it's committed; local private key present and matching."
fi

# ------------------------------------------------------------------------------
# 12. playbook_dir-relative path check — check_playbook_dir_paths.py
# ------------------------------------------------------------------------------
section "12. playbook_dir-relative paths — check_playbook_dir_paths.py"

if out=$(python3 "${HERE}/check_playbook_dir_paths.py"); then
  echo "$out"
  success "All playbook_dir-relative paths resolve."
else
  echo "$out"
  fail "Unresolved playbook_dir-relative path(s) -- see above."
  FAILED_CHECKS+=("check_playbook_dir_paths.py")
fi

# ------------------------------------------------------------------------------
# 13. Mermaid diagram render check — check_mermaid.py
# ------------------------------------------------------------------------------
section "13. Mermaid diagrams — check_mermaid.py"

mermaid_args=()
$STRICT && mermaid_args+=("--strict")
if out=$(python3 "${HERE}/check_mermaid.py" "${mermaid_args[@]}"); then
  echo "$out"
  success "All mermaid diagrams render successfully (or unreachable ones are informational only)."
else
  echo "$out"
  if echo "$out" | grep -q "genuine syntax error"; then
    fail "One or more mermaid diagrams have a real syntax error -- see above."
    FAILED_CHECKS+=("check_mermaid.py")
  else
    fail "kroki.io was unreachable for one or more diagrams -- see above. Failing because --strict was passed."
    FAILED_CHECKS+=("check_mermaid.py (--strict: kroki.io unreachable)")
  fi
fi

# ------------------------------------------------------------------------------
# 14. Network diagram freshness — check_network_diagram_freshness.py
# ------------------------------------------------------------------------------
section "14. Network diagram freshness — check_network_diagram_freshness.py"

if out=$(python3 "${HERE}/check_network_diagram_freshness.py"); then
  echo "$out"
  success "docs/network-diagram/*.md's New Network boxes are fresh."
else
  echo "$out"
  fail "docs/network-diagram/*.md's New Network box(es) have drifted from sites.csv/devices.csv -- see above."
  FAILED_CHECKS+=("check_network_diagram_freshness.py")
fi

# ------------------------------------------------------------------------------
# 15. Network diagram content invariants — check_network_diagram_content.py
# ------------------------------------------------------------------------------
section "15. Network diagram content invariants — check_network_diagram_content.py"

if out=$(python3 "${HERE}/check_network_diagram_content.py"); then
  echo "$out"
  success "No banned FSMO/health terms found; every New Network node uses an approved shape."
else
  echo "$out"
  fail "New Network content invariant violation(s) -- see above."
  FAILED_CHECKS+=("check_network_diagram_content.py")
fi

# ------------------------------------------------------------------------------
# 16. KeePass credential freshness — check_keepass_freshness.py
# ------------------------------------------------------------------------------
section "16. KeePass credential freshness — check_keepass_freshness.py"

keepass_out=$(python3 "${HERE}/check_keepass_freshness.py")
keepass_rc=$?
echo "$keepass_out"
keepass_local_issue_count=$(echo "$keepass_out" | grep -oE '^[0-9]+ local-only issue' | grep -oE '^[0-9]+' || true)
if [[ $keepass_rc -ne 0 ]]; then
  fail "benarbejde/extracted_credentials.json has a structural problem -- see above."
  FAILED_CHECKS+=("check_keepass_freshness.py")
elif [[ -n "$keepass_local_issue_count" && "$keepass_local_issue_count" -gt 0 ]]; then
  if $STRICT; then
    fail "${keepass_local_issue_count} local KeePass vault issue(s) -- see above. Failing because --strict was passed."
    FAILED_CHECKS+=("check_keepass_freshness.py (--strict: local vault drift)")
  else
    warn "${keepass_local_issue_count} local KeePass vault issue(s) (see above) -- expected on a bare clone/CI runner with no local vault, but a real drift on a host that has one. Re-run with --strict before treating the vault as authoritative."
  fi
else
  success "extracted_credentials.json is well-formed; live vault (where available) is up to date."
fi

# ------------------------------------------------------------------------------
# 17. WireGuard hub data freshness — check_wireguard_hub_data.py
# ------------------------------------------------------------------------------
section "17. WireGuard hub data — check_wireguard_hub_data.py"

if out=$(python3 "${HERE}/check_wireguard_hub_data.py"); then
  echo "$out"
  success "Hub WAN IPs match sites.csv's convention; no blank known-good pubkeys."
else
  echo "$out"
  fail "WireGuard hub reference data has drifted -- see above."
  FAILED_CHECKS+=("check_wireguard_hub_data.py")
fi

# ------------------------------------------------------------------------------
# 18. Playbook directory documentation coverage — check_playbook_doc_coverage.py
# ------------------------------------------------------------------------------
section "18. Playbook doc coverage — check_playbook_doc_coverage.py"

covdoc_out=$(python3 "${HERE}/check_playbook_doc_coverage.py")
covdoc_rc=$?
echo "$covdoc_out"
if [[ $covdoc_rc -ne 0 ]]; then
  fail "Playbook module directory/ies missing a README.md -- see above."
  FAILED_CHECKS+=("check_playbook_doc_coverage.py")
elif echo "$covdoc_out" | grep -q "not named in any README/docs"; then
  warn "No missing READMEs, but some playbook file(s) look orphaned (see above)."
else
  success "Every playbook module directory has a README.md; no orphaned playbook files."
fi

# ------------------------------------------------------------------------------
# 19. Feature doc/check pairing — check_features.py
# ------------------------------------------------------------------------------
section "19. Feature doc/check pairing — check_features.py"

if out=$(python3 "${HERE}/check_features.py"); then
  echo "$out"
  success "Every registered feature's doc and check both hold."
else
  echo "$out"
  fail "Registered feature doc/check pairing has broken -- see above."
  FAILED_CHECKS+=("check_features.py")
fi

# ------------------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------------------
section "Summary"

if ! $NO_REPORT; then
  info "Full report written to: ${REPORT_FILE}"
  info "(also copied to: ${LATEST_FILE})"
fi

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
