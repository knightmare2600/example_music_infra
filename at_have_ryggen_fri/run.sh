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
#      begyndelse.json, and salt/pillar/sites.sls are re-derivable byte-for-byte
#      from benarbejde/sites.csv+devices.csv+address_policy.csv+ad_forest.json --
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
#      benarbejde/sites.csv+devices.csv+address_policy.csv via
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
#  20. check_role_codes.py -- benarbejde/role_codes.csv (every device-role code's
#      name/category/connection-method/emoji, added 2026-07-20 consolidating
#      three separate hand-maintained copies -- one already found drifted, MBP
#      was ssh in one, winrm in another) vs. docs/emojis/README.md's hand-
#      maintained legend, which should always agree with it exactly.
#  21. check_salt_states.py -- Salt's own equivalent of check 2, plus two
#      Salt-specific structural checks: every salt/states/**/*.sls (bar
#      _modules/) renders via Jinja (generic mock grains/pillar/salt context)
#      and the result parses as YAML -- the same "does this even parse" bar
#      --syntax-check sets for Ansible, which nothing previously checked for
#      Salt at all. Also: every state/pillar name in top.sls/pillar/top.sls
#      resolves to a real file; every messagetype: value used in a
#      screenprint.screen_print call is one screenprint.py's own
#      MESSAGETYPE_COLOR dict actually maps to a colour (read directly from
#      the module, not hand-copied here); every salt/states/ module directory
#      is named in salt/README.md. Added 2026-07-21 after reviewing a large
#      dropped-in Salt state tree found `messagetype: "warn"` (not a real
#      value) sitting silently uncaught in one of the ported files -- this
#      is the check that would have caught it without needing a human to
#      spot it by eye.
#  22. check_duplicate_devices.py -- every generated ansible/configs/inventory/
#      <site>.ini and generate_inventory.py --emit-devices-json's merged output
#      for the same hostname appearing twice at two different IPs: a standard-
#      slot template line and a real devices.csv row colliding on the same
#      role+instance number. Added 2026-07-22 after this exact bug turned up
#      live twice -- EXAFWLVRK001 in vrk.ini (904ddd0) and EXAWKSFAL001/
#      EXALAPFAL001 in fal.ini, both found only by eye, with nothing
#      previously checking for it automatically. bind9-dns.yml's zone
#      templates consume --emit-devices-json via a Jinja `first` filter,
#      which would silently pick one IP and drop the other rather than
#      erroring -- this check is the only thing that catches that class of
#      bug before it reaches a live zone file.
#  23. check_network_session_safety.py -- every ansible/playbooks/ and
#      ansible/tasks/ YAML file for the nmcli delete+recreate-same-connection
#      antipattern (Tier 1, hard fail) and ungated `nmcli connection up
#      <profile>` on a profile this same file templates (Tier 2,
#      informational unless --strict). Added 2026-07-22 after the exact same
#      bug -- unconditional `nmcli con delete X` + `nmcli con add ... con-name
#      X` on every run, no idempotency check, always reporting "changed" --
#      turned up live in bind9-dns.yml (killed Robert's SSH session on
#      EXADNSVRK001), then the identical copy-pasted pattern in
#      rudder_server.yml and salt/playbooks/10-master.yml, all fixed by hand
#      with nothing catching a fourth instance automatically.
#  24. check_control_node_freshness.py -- if /etc/example-music/ exists on
#      the machine this harness is being run from, hash-compares every file
#      linux/tools.yml deploys there (sites.csv, devices.csv, role_codes.csv,
#      address_policy.csv, ad_forest.json, ad_groups.json, ad_users.json,
#      ad_computers.json) against its benarbejde/ source. Skips cleanly if
#      /etc/example-music/ doesn't exist (not the control node). Added
#      2026-07-27 after bind9-dns.yml crashed live with a raw Python
#      KeyError -- traced to the Ansible control node's own served
#      address_policy.json predating a benarbejde/ schema change, because
#      linux/tools.yml hadn't been re-run against the control node itself.
#      This is the offline half of that fix; the in-playbook half is
#      ansible/tasks/example_music_freshness_gate.yml, included by every
#      playbook that reads /etc/example-music/* at runtime.
#  25. check_bootstrap_assets.py -- two tiers. Tier 1 (always hard fail):
#      bootstrap/web/proxmox/*.toml answer files, derived from
#      select-pve-answer.sh's own site_prefix/variant literals rather than
#      hand-copied a third time (check_ssh_keys.py's ANSWER_TOMLS is the
#      existing copy). Tier 2 (informational unless --strict): kernel/
#      initrd/iPXE-fetched boot binaries referenced by bootstrap/web/
#      menu.ipxe, with the small set of enumerable iPXE variables it uses
#      expanded programmatically. 192.168.139.50 isn't a fixed host to
#      detect (README.md: it's a role a technician's laptop assumes
#      temporarily via static-web-server.exe), so this reuses the existing
#      --strict idiom instead of any IP-based check. Added 2026-07-27.
#  30. check_legacy_devices.py -- benarbejde/legacy-devices.csv (old-network-
#      only core infra with no live counterpart: RAC/iLO/iDRAC, ESXi hosts,
#      vCenter) for structural validity, unknown Site codes, duplicate rows,
#      Types outside RAC/ESX/VCT, and -- the main point -- any row whose
#      computed hostname collides with a real hostname in the live generated
#      inventory. Added 2026-08-03 directly because of the EXAFWLFAL001 mess:
#      a hand-built Old Network diagram invented a device under a hostname
#      that turned out to already belong to a real, live, current device.
#      legacy-devices.csv exists to hold genuinely-dead old-network hardware
#      separately from devices.csv's live rows; this check is what keeps that
#      separation honest.
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
#   2026-07-21  Added check_salt_states.py (section 21), while reviewing a
#               large dropped-in Salt state tree (salt/cleanup/) and building
#               salt/states/ genuinely into this estate for the first time.
#               Nothing here previously checked Salt content at all -- a
#               broken Jinja expression, a dead top.sls reference, or an
#               invalid messagetype would only ever have surfaced against a
#               real minion (or a human reading closely, which is how
#               `messagetype: "warn"` was actually found, during this same
#               session's port of bespoke_app_install). Also folded
#               salt/pillar/sites.sls into check_generated_freshness.py's
#               existing coverage (section 6) -- it's generated by the same
#               benarbejde/generate_inventory.py, via
#               --emit-site-grains-pillar, and had nothing checking its
#               freshness either.
#   2026-07-20  Added check_role_codes.py (section 20), while cleaning up the
#               retired PRV convention: the same code->connection-method and
#               code->emoji data was hand-duplicated in three places
#               (address_policy.json's connection_types, generate_network_
#               diagrams.py's TYPE_SYMBOLS, docs/emojis/README.md) -- found
#               one already drifted (MBP: ssh in one copy, winrm in another)
#               while consolidating them into benarbejde/role_codes.csv, the
#               new single source of truth. The first two now load it
#               directly instead of hardcoding a copy; this check keeps the
#               third (docs/emojis/README.md, deliberately still hand-
#               maintained prose) honest against it.
#   2026-07-22  Added check_duplicate_devices.py (section 22), during a sweep
#               for other instances of the EXAFWLVRK001-style collision (904ddd0)
#               across every standard-slot role in generate_inventory.py's
#               build_ini(). Found two more, live, uncaught: EXAWKSFAL001 and
#               EXALAPFAL001 in fal.ini, each with a commented placeholder and
#               a real devices.csv row at different IPs. Fixed the same guard
#               pattern generically (FWL2/DCS1/DCS2/WKS1/LAP1, alongside
#               FWL1) and added this check so a future role or devices.csv
#               edit can't reintroduce the class silently.
#   2026-07-22  Added check_network_session_safety.py (section 23) --
#               deferred item from the bind9-dns.yml SSH-session-kill
#               incident, picked up after the identical delete+recreate
#               pattern was found and fixed by hand a second and third time
#               (rudder_server.yml, salt/playbooks/10-master.yml) in the
#               same week. Verified it has real teeth: 0 Tier 1 hits against
#               the three now-fixed files, 1 honest Tier 2 finding against
#               roles/firewall/tasks/06_network_manager.yml's own reviewed
#               `nmcli con up lan` (no strand-check, but LAN is never the
#               interface Ansible's session rides -- a human judgement call
#               this script can't know, hence Tier 2 not Tier 1), and a hard
#               Tier 1 fail when tested against a reconstructed copy of the
#               original broken rudder_server.yml snippet.
#   2026-07-27  Added check_control_node_freshness.py (section 24), after
#               tracing a live bind9-dns.yml crash to the control node's own
#               stale /etc/example-music/address_policy.json (every real
#               consumer reads it via delegate_to: localhost or
#               lookup('file', ...), which always evaluates on the
#               controller regardless of the play's target host). Verified
#               against a scratch /etc/example-music/-equivalent: clean
#               match silent, a tampered file caught, missing files caught,
#               correct exit codes both ways.
#   2026-07-27  Added check_bootstrap_assets.py (section 25) and extended
#               --strict's own doc comment to mention it. Robert's ask: same
#               idiom, applied to bootstrap/web/'s two asset classes (always-
#               required TOML answer files vs. context-dependent kernel/
#               initrd/iPXE binaries). Writing the menu.ipxe parser found
#               three real bugs in itself before it was trusted: a
#               documentation comment's "url=..." placeholder text getting
#               scanned as a real reference, `chain --autofree <url>`'s flag
#               token captured instead of the actual URL, and iPXE's
#               ${var:filter} colon syntax (${mac:hexhyp}) not being
#               recognised as a variable at all -- each fixed and re-verified
#               against the real file, output hand-checked line for line
#               against a full manual read of menu.ipxe before wiring in
#               pass/fail. Also surfaced, not fixed here: arch-auto's
#               initramfs-linux.img reference vs. the tracked file's real
#               name (initramfs-linux, no extension) -- a pre-existing
#               mismatch the check now catches on every run.
#   2026-08-03  Added check_legacy_devices.py (section 30) alongside the new
#               benarbejde/legacy-devices.csv. Direct follow-on from the
#               EXAFWLFAL001 discovery during the Old Network RTR/FWL
#               re-audit: a hand-built diagram's fictional device shared a
#               hostname with a real live one. RTR/SWI turned out to already
#               have real devices.csv continuity (Legacy=yes rows); RAC/ESX/
#               VCT never did -- legacy-devices.csv gives them a home, and
#               this check guards the boundary so a future row here can never
#               silently collide with the live generated inventory again.
# ==============================================================================
set -uo pipefail

# --strict: promotes "expected, informational" warnings (missing drop-in
# binaries, unindexed docs, local SSH keypair issues, KeePass vault drift,
# ungated nmcli connection-up findings, missing menu.ipxe-referenced boot
# binaries) to real failures. Added 2026-07-10 after Robert pointed out that
# burying 20 missing ARM64/x86_64 binaries as a generic "expected on a fresh
# clone" yellow line is the wrong default for someone actually about to
# deploy, not just cloning the repo to read it. Default behaviour (no flag)
# is unchanged -- still safe to run on a bare clone with nothing dropped in
# yet.
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
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
ANSIBLE_DIR="${REPO_ROOT}/ansible"

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
    at_have_ryggen_fri/*) continue ;;
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
# 20. Role code registry consistency — check_role_codes.py
# ------------------------------------------------------------------------------
section "20. Role code registry — check_role_codes.py"

if out=$(python3 "${HERE}/check_role_codes.py"); then
  echo "$out"
  success "docs/emojis/README.md matches benarbejde/role_codes.csv exactly."
else
  echo "$out"
  fail "role_codes.csv and docs/emojis/README.md have drifted -- see above."
  FAILED_CHECKS+=("check_role_codes.py")
fi

# ------------------------------------------------------------------------------
# 21. Salt state validity — check_salt_states.py
# ------------------------------------------------------------------------------
section "21. Salt state validity — check_salt_states.py"

if out=$(python3 "${HERE}/check_salt_states.py"); then
  echo "$out"
  success "All salt/ states render+parse cleanly; top.sls/pillar/top.sls targets resolve; every messagetype is valid; every module directory is documented."
else
  echo "$out"
  fail "Salt state issue(s) found -- see above."
  FAILED_CHECKS+=("check_salt_states.py")
fi

section "22. Duplicate hostname/IP collisions — check_duplicate_devices.py"

if out=$(python3 "${HERE}/check_duplicate_devices.py"); then
  echo "$out"
  success "No standard-slot template line collides with a real devices.csv row on the same hostname."
else
  echo "$out"
  fail "Duplicate hostname/IP collision(s) found -- see above."
  FAILED_CHECKS+=("check_duplicate_devices.py")
fi

section "23. Network session safety — check_network_session_safety.py"

net_out=$(python3 "${HERE}/check_network_session_safety.py")
net_rc=$?
echo "$net_out"
net_tier2_count=$(echo "$net_out" | grep -oE '^[0-9]+ informational finding' | grep -oE '^[0-9]+' || true)
if [[ $net_rc -ne 0 ]]; then
  fail "nmcli delete+recreate-same-connection antipattern found -- see above."
  FAILED_CHECKS+=("check_network_session_safety.py")
elif [[ -n "$net_tier2_count" && "$net_tier2_count" -gt 0 ]]; then
  if $STRICT; then
    fail "${net_tier2_count} ungated nmcli connection-up finding(s) -- see above. Failing because --strict was passed."
    FAILED_CHECKS+=("check_network_session_safety.py (--strict: ungated connection-up)")
  else
    warn "${net_tier2_count} ungated nmcli connection-up finding(s) (see above) -- informational, confirm by hand. Re-run with --strict to fail on this."
  fi
else
  success "No nmcli delete+recreate or ungated connection-up findings."
fi

# ------------------------------------------------------------------------------
# 24. Control node's own /etc/example-music/* freshness
# ------------------------------------------------------------------------------
section "24. Control node freshness — check_control_node_freshness.py"

if cnf_out=$(python3 "${HERE}/check_control_node_freshness.py"); then
  echo "$cnf_out"
  success "Control node's /etc/example-music/*, if present, matches benarbejde/*."
else
  echo "$cnf_out"
  fail "Control node's /etc/example-music/* has drifted from benarbejde/* -- see above."
  FAILED_CHECKS+=("check_control_node_freshness.py")
fi

# ------------------------------------------------------------------------------
# 25. Bootstrap assets
# ------------------------------------------------------------------------------
section "25. Bootstrap assets — check_bootstrap_assets.py"

assets_out=$(python3 "${HERE}/check_bootstrap_assets.py")
assets_rc=$?
echo "$assets_out"
boot_binary_missing_count=$(echo "$assets_out" | grep -oE '^[0-9]+ boot binary issue' | grep -oE '^[0-9]+' || true)
if [[ $assets_rc -ne 0 ]]; then
  fail "Required TOML/preseed answer file(s) missing -- see above."
  FAILED_CHECKS+=("check_bootstrap_assets.py")
elif [[ -n "$boot_binary_missing_count" && "$boot_binary_missing_count" -gt 0 ]]; then
  if $STRICT; then
    fail "${boot_binary_missing_count} boot binary asset(s) missing -- see above. Failing because --strict was passed: you said you're about to deploy, not just reading the repo."
    FAILED_CHECKS+=("check_bootstrap_assets.py (--strict: boot binaries missing)")
  else
    warn "${boot_binary_missing_count} boot binary asset(s) missing (see above) -- expected unless you're about to package the bootstrap kit. Re-run with --strict before an actual deployment."
  fi
else
  success "All required TOML/preseed files present; all menu.ipxe-referenced boot binaries present."
fi

# ------------------------------------------------------------------------------
# 26. Ansible collection requirements
# ------------------------------------------------------------------------------
section "26. Collection requirements — check_collection_requirements.py"

if colreq_out=$(python3 "${HERE}/check_collection_requirements.py"); then
  echo "$colreq_out"
  success "Every collection module used is declared in a requirements.yml, and every requirements.yml is documented with its install command."
else
  echo "$colreq_out"
  fail "A collection module is used without a matching requirements.yml entry, or a requirements.yml exists undocumented -- see above."
  FAILED_CHECKS+=("check_collection_requirements.py")
fi

# ------------------------------------------------------------------------------
# 27. SubnetSite/Site mismatches (informational, never fails)
# ------------------------------------------------------------------------------
section "27. SubnetSite mismatches — check_subnet_site_mismatch.py"

subnet_out=$(python3 "${HERE}/check_subnet_site_mismatch.py")
echo "$subnet_out"

# ------------------------------------------------------------------------------
# 28. Doc role coverage (informational unless --strict)
# ------------------------------------------------------------------------------
section "28. Doc role coverage — check_doc_role_coverage.py"

docrole_out=$(python3 "${HERE}/check_doc_role_coverage.py")
echo "$docrole_out"
docrole_count=$(echo "$docrole_out" | grep -oE '^[0-9]+ informational finding' | grep -oE '^[0-9]+' || true)
if [[ -n "$docrole_count" && "$docrole_count" -gt 0 ]]; then
  if $STRICT; then
    fail "${docrole_count} finding(s) across site-inventory.md/network-inventory.md/the Beginners Guide -- see above. Failing because --strict was passed."
    FAILED_CHECKS+=("check_doc_role_coverage.py (--strict: doc coverage gaps)")
  else
    warn "${docrole_count} finding(s) across site-inventory.md/network-inventory.md/the Beginners Guide (see above) -- expected until that doc catch-up happens. Re-run with --strict to fail on this."
  fi
else
  success "Every real, addressed device is mentioned in its own site's/section's coverage across all three hand-maintained docs."
fi

# ------------------------------------------------------------------------------
# 29. DCR (legacy-naming DC) devices (informational, never fails)
# ------------------------------------------------------------------------------
section "29. DCR devices — check_dcr_devices.py"

dcr_out=$(python3 "${HERE}/check_dcr_devices.py")
echo "$dcr_out"

# ------------------------------------------------------------------------------
# 30. legacy-devices.csv structure + live-hostname collision guard
# ------------------------------------------------------------------------------
section "30. Legacy devices — check_legacy_devices.py"

if out=$(python3 "${HERE}/check_legacy_devices.py"); then
  echo "$out"
  success "legacy-devices.csv is structurally sound and collides with nothing live."
else
  echo "$out"
  fail "legacy-devices.csv problem(s) found -- see above."
  FAILED_CHECKS+=("check_legacy_devices.py")
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
