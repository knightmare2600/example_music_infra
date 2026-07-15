# at_have_ryggen_fri

Danish: *"at have ryggen fri"* — to have your back covered.

A verification harness for this whole repo — not just the Ansible side.
Run it before merging anything that touches inventory, `group_vars`/
`host_vars`, `ansible.cfg`, `benarbejde/`'s source-of-truth files, or
`docs/`, to catch the exact classes of bug found the hard way in this
repo's history:

- `group_vars`/`host_vars` silently not applying because they live outside
  the loaded inventory path (the bug behind the 2026-07-09 consolidation —
  see `docs/ansible/beginners_guide_to_ansible.md`).
- `add_host` dynamic registration silently not propagating group_vars to a
  later play.
- A `template:`/`copy:`/`win_copy:`/`include_tasks:`/`import_playbook:`
  pointing at a file that doesn't actually exist.
- Malformed YAML that only breaks when a specific handler/task file is
  actually loaded, not on a casual read.
- `benarbejde/sites.csv`/`devices.csv`/etc. edited but `configs/inventory/`,
  `site_services.yml`, or `begyndelse.json` never regenerated to match.
- `docs/INDEX.md` linking to a file that's moved, or a real doc nobody
  indexed.
- A fact (an IP, a hostname) restated as prose in several docs/scripts,
  where one got fixed and the others didn't — found 2026-07-10 doing
  exactly this by hand for `EXAFWLVRK001`'s WAN IP before deciding to
  automate it.
- A site added to (or removed/renamed in) `sites.csv` that never made it
  into `docs/`, or a doc quoting a site's subnet/octet that doesn't match
  its real `sites.csv` row — found 2026-07-11 (`buildsheet-firewall.md`'s
  `ATL` row had both a wrong IP and a leftover pre-rename city name).
- The estate's SSH keypair genuinely going missing on the real control
  node, with no local file-existence check to catch it and no real
  connectivity test before Ansible's own connection attempt obscures the
  cause — found 2026-07-12 when `ansible-id_rsa` went missing on
  `EXAANSCLD001` mid real-node test (see `check_ssh_keys.py` and
  `ansible/tasks/ssh_key_preflight.yml`).
- A mermaid diagram that looks fine to read but genuinely fails to render
  — literal `\n` instead of `<br/>`, a backslash-escaped quote, an
  unquoted `(` inside a pipe-delimited edge label — none of which any
  YAML/Ansible-structural check could ever catch, since the failure is
  only real against Mermaid's own parser. Found across 49 diagrams,
  2026-07-12, after Robert spotted one broken on GitHub (see
  `check_mermaid.py`).
- `docs/network-diagram.md`'s hand-maintained per-site diagrams silently
  drifting from what `sites.csv`/`devices.csv` actually say is current —
  18 sites' diagrams had `RTR`/`FWL` genuinely swapped relative to
  `address_policy.json`'s real convention, invisible until the two were
  compared side by side. See `docs/network-cutover.md` and checks 14–15.

Phases 1 (repo-wide reference/data integrity), 2 (the estate's bare-metal
bootstrap scenarios as repeatable checks), and an initial repo-wide sweep
(using `git ls-files` instead of hardcoded directory scans, so coverage
grows automatically as the repo does) are all done as of 2026-07-10 — see
the git history for the fuller context if picking this back up later.
A first documentation-accuracy pass over the ~15 most operator-facing
procedure docs happened 2026-07-11 (FRD alternate boot-server cross-refs,
3 stale provisioning-server hostnames, 2 stale site codes, one fictional
directory listing, one stale "PhoenixPE" naming) — see the Methodology
section above for why this is a first pass, not a completed audit: `docs/`
has ~70 markdown files and only a fraction have been checked against real
source-of-truth data so far. Still open: the unattend XML per-edition
variants, this harness's own `docs/INDEX.md` entry, the remaining
un-audited procedure docs (buildsheets for domain controllers/server/
winadmin/workstation, the `proxmox_zabbix_cleanup/` procedures, the
Windows-side `bootstrap/` build guides), and any further findings.

Nothing here touches a real host or needs a vault password. One exception to
"network access beyond `localhost`": check 13 (`check_mermaid.py`) genuinely
needs to reach `kroki.io` to render-test mermaid diagrams — see its own
section below for why, and how that's handled safely. Everything else is
still safe to run on any clone, any time, no network required.

## Backlog

Tracks work agreed with Robert but not (yet) fully done. This is the agreed
home for tracking this specific piece of work — see the plan for the full
write-up.

**Network diagram standardisation** (started 2026-07-12/13):

- [x] Phase 1 — Old Network box + standard shapes/colours + per-site legend
      on all 47 existing `network-diagram.md` sites, plus a colour-only pass
      on the two site-to-hub topology diagrams (`buildsheet-firewall.md`,
      `ExampleMusic_Beginners_Guide.md` §6.1).
- [x] Phase 2 — `benarbejde/generate_network_diagrams.py`: New Network box
      generated from `sites.csv`/`devices.csv`/`address_policy.json` for all
      51 sites that have one, including the 4 genuine new-build sites (FRD,
      NYB, SEA, SFO — confirmed by Robert, not a data gap) getting a
      "New Build Location" placeholder in place of Old Network.
- [x] Phase 3 — `docs/network-cutover.md`, built from a real Old-vs-New
      octet comparison (18 sites' RTR/FWL swap, 2 site-specific collisions,
      6 sites' DCR→DCS rename explicitly excluded as not-a-conflict).
- [x] Phase 4 — checks 14–15 (`check_network_diagram_freshness.py`,
      `check_network_diagram_content.py`) wired into `run.sh`.
- [x] Phase 5 — joint icon/curveball sign-off with Robert 2026-07-13: all 22
      curveball/labelled types now have an agreed Unicode symbol
      (`benarbejde/generate_network_diagrams.py`'s `TYPE_SYMBOLS`), no `❓`
      placeholders left. Three literal asks aren't real Unicode characters —
      an AT&T logo / red British phonebox for `PAY`, an Atari logo for
      `AST`, a jukebox glyph for `MUS` (confirmed via web search, not
      assumed — no Unicode jukebox emoji exists) — same class of limitation
      that ruled out real Cisco stencils for the shape system. Substituted a
      telephone receiver, a joystick, and an optical disc respectively,
      flagged as such rather than silently picked. Visual read-through of
      FAL's finished diagram done together 2026-07-13 (published as a Claude
      Artifact, rendered from the committed doc via the same kroki.io
      round-trip check_mermaid.py uses) — Phase 5, and this plan, complete.
- [x] Phase 6 (post-hoc addendum) — visual density pass, 2026-07-13. Robert's
      feedback after the read-through: the 5-shape system plus 3-line labels
      made a 50+ node diagram "more shapes than the Ministry of Sound," and
      wanted server/network-infra types to get emoji too, not just curveball
      ones. Replaced the shape system with one uniform rect + emoji for
      every device type (all ~40 types now, not just the 22 curveball ones
      — see `docs/emojis/README.md`), and single-line labels (` · `
      separator, not `<br/>`). Applied to both Old and New Network boxes —
      Old Network's hand-written nodes reformatted via a one-off script, not
      hand-edited 47 times. Result was mixed: a small/typical site (GOT, 7
      nodes) got ~33% shorter; FAL (52 nodes, real device data, several
      already-short curveball labels) barely changed in total area — wider
      single-line labels roughly offset the height saved. Worth knowing
      before assuming this "fixes" every diagram's size. check 15 rewritten
      to check for the uniform shape + a leading emoji instead of the old
      5-shape list.
- [x] Phase 7 — split into per-region files, 2026-07-13. The emoji/uniform-
      shape pass (Phase 6) still wasn't enough — Robert: "there's just simply
      too much for GitHub to render." `docs/network-diagram.md`'s 51 diagrams
      split into 15 files under `docs/network-diagram/` (1–9 diagrams each,
      by region — Scotland, England, Danmark, etc.); the old file is now an
      index (Visual Standard, emoji legend, links out). Checks 14–15 and
      `generate_network_diagrams.py`'s `insert_into_docs()` all updated to
      iterate the region files; re-verified idempotent (zero diff) before
      trusting it, and both checks' guards re-confirmed against synthetic
      tampering after the restructure.
- [ ] Phase 8 (not started, deferred to a later session per Robert) —
      per-site colour-scheme fixes he can "tell at a glance" are wrong but
      wants to review properly rather than rushed; CLD's Old Network box
      arguably mislabels something as "legacy" that never really had an old
      network in the same sense other sites did; a cloud-outline or ☁️-emoji
      treatment for the Internet node instead of a plain box.

## Methodology — what does "a good run" actually mean?

A test harness that only checks that code does what the code does is
circular — it will always pass, and catches nothing. Every check here is
built against a **source of ground truth that's independent of the file
being checked**, so a real failure means the file actually disagrees with
something outside itself, not just that the checker's expectations were
generated from the same place. Three tiers, in increasing order of what
they can catch:

1. **Structural/mechanical integrity** (checks 1–5, 7's link half). Does
   this YAML parse? Does this playbook pass `--syntax-check`? Does this
   `template:`/`copy:`/`include_tasks:` path resolve to a real file? Does
   this markdown link point at something that exists? These don't know or
   care whether the *content* is correct — only whether the repo is
   internally consistent. A failure here is unambiguous: something is
   objectively broken, full stop.
2. **Regenerable-output freshness** (check 6). `configs/inventory/*.ini`,
   `site_services.yml`, and `begyndelse.json` are all deterministic
   functions of `benarbejde/`'s CSV/JSON source files. This check
   regenerates them from source into a scratch dir and diffs against
   what's committed. It can't tell you the *generation logic* is right
   (that's what actually running `generate_inventory.py` and reading its
   output critically, once, when it's written, is for) — only that nobody
   edited the source and forgot to regenerate afterward.
3. **Hand-curated ground truth** (checks 8–9: `facts.yml`, `scenarios.yml`).
   This is the only tier that catches *semantic* drift — a hostname, an
   IP, a procedure step that's gone stale. It works because a human (me)
   investigated the real, authoritative state of something (read
   `devices.csv`, traced what a script actually does, confirmed a fact
   against its real source) and registered that independently-established
   truth once. The check then verifies the repo still agrees with it. This
   is deliberately narrow: **it only catches drift in a fact someone has
   already registered.** It is not a generic scanner and will not notice a
   new, never-registered inconsistency on its own — that's the explicit
   tradeoff (see `facts.yml`'s own header) made in exchange for zero false
   positives against changelog entries and historical examples.

**The honest limitation this implies**: tier 3's coverage is only as wide
as what's actually been investigated and registered. As of 2026-07-10 that
was 5 facts and 4 scenarios — a small fraction of `docs/`'s ~70 markdown
files. A file with no registered fact and no scenario coverage can drift
indefinitely and this harness will stay green throughout, because tiers 1–2
never look at prose content at all. Widening tier 3's coverage (auditing
more of `docs/` the way `bootstrapping.md` was audited, then registering
what's found) is ongoing work, not a one-time pass — see the git log for
what's been swept so far, and treat a clean run as "everything currently
checked holds," not "this repo has no inaccuracies."

## Usage

```bash
cd ansible/at_have_ryggen_fri
./run.sh

# Before an actual deployment (not just cloning the repo to read it):
./run.sh --strict

# Skip writing a report file (see "Report file" below):
./run.sh --no-report
```

Exit code 0 if every check passes, 1 otherwise. Colour-coded output follows
the same `[*]`/`[+]`/`[!]`/`[✗]` convention as `firewallme.sh`/`ansibleme.sh`.

**`--strict`** promotes "expected, informational" warnings to real failures —
currently just missing drop-in binaries (check 3). Default behaviour treats
those as fine (a bare clone genuinely won't have them yet), which is correct
for "does the repo make sense" but wrong for "am I actually ready to deploy" —
use `--strict` for the latter. Added 2026-07-10 after 20 missing ARM64/x86_64
binaries were found buried in a generic yellow warning line instead of being
front and centre.

### Report file

Every run writes its full output (identical to what's on screen, colour codes
included) to `reports/run-<timestamp>.log`, plus `reports/latest.log` (always
overwritten). Both are covered by the repo's global `*.log` `.gitignore` rule
— these are run artefacts, not committed history, and `git status` stays
clean after running this. Added 2026-07-11: check 3 (`check_references.py`)
has always printed every missing drop-in binary by name (see "What it
checks" below) — but before this, that output only ever existed in terminal
scrollback. If you're not seeing something you expect the harness to report,
check `reports/latest.log` first — it has the complete, unedited output of
the last run, not just whatever's still on screen.

## What a real failure looks like

This isn't hypothetical — `check_facts.py` genuinely caught this on its first
run, 2026-07-10. `docs/buildsheets/buildsheet-firewall.md` still had the
firewall's old, pre-CLD/VRK-split WAN IP after every other file had already
been fixed:

```
── 8. Cross-file facts — check_facts.py ──

Checked 4 fact(s) against 14 file assertion(s) (facts.yml).

3 drifted assertion(s):
  [fwl_wan_ip] docs/buildsheets/buildsheet-firewall.md: does not contain "192.168.139.69"
      expected (per benarbejde/devices.csv (VRK,FWL,1,69)): "192.168.139.69"
  ...
[✗] Registered fact(s) have drifted -- see above.

── Summary ──

[✗] 1 check(s) failed:
  ✗ check_facts.py
```

What to do with output like this: the `[name]` in brackets (`fwl_wan_ip`)
is the fact's key in `facts.yml` — look it up there for the full context
(`source`, `description`) and the complete list of files it's supposed to
hold in. Fix the file named in the failure (either it's genuinely stale, or
the fact's registered `value` itself needs updating if the real IP/hostname
legitimately changed) and re-run. This one specific failure is what
prompted fixing that buildsheet the same day — see the git log around
2026-07-10 for the actual commit.

## What it checks

| # | Check | How |
|---|-------|-----|
| 1 | YAML validity | Every git-tracked `*.yml`/`*.yaml` in the whole repo (via `git ls-files`, excluding this directory) parses, including `!vault`-tagged files |
| 2 | `ansible-playbook --syntax-check` | Every file with a top-level `hosts:` key |
| 3 | Reference integrity | `check_references.py` — every literal `src:`/`include_tasks:`/`import_tasks:`/`import_playbook:` path resolves to a real file, correctly handling both playbook-relative and role-relative (`roles/<name>/templates|files/`) resolution. Also resolves `src: "...{{ item.attr }}..."` when combined with `loop: "{{ some_group_vars_list }}"` — the group_vars list is static, so `item.attr` is substitutable per loop item even though it's technically Jinja (this is how `50-binaries.yml`'s x86_64/arm64 binary paths get checked, not silently skipped as "dynamic") |
| 4 | Inventory structure | `check_inventory_structure.py` — the real `configs/inventory`'s `windows_dc → windows_server → windows → windows_nodes` chain exists across multiple sites (not just the 3 hand-curated ones); `group_vars` genuinely resolves (become correctly scoped to `linux` only, never Windows; `colours.yml`'s `_c` dict present) — via `ansible-inventory`, no host contacted |
| 5 | `add_host` visibility | `add_host_probe/` — a live two-play `ansible-playbook` run: play 1 registers a scratch host into a group via `add_host` (`delegate_to: localhost`), play 2 asserts that group's `group_vars` resolved for it — the exact mechanism `windows_bootstrap/00-preflight.yml`'s Phase H2 depends on |
| 6 | Generated-file freshness | `check_generated_freshness.py` — regenerates `configs/inventory/*.ini`, `site_services.yml`, and `begyndelse.json` from `benarbejde/sites.csv`+`devices.csv`+`address_policy.json`+`ad_forest.json` into a scratch dir and diffs against committed — catches "edited the source, forgot to regenerate" |
| 7 | Markdown link integrity | `check_doc_index.py` — every relative link in every git-tracked `*.md` file in the whole repo (not just `docs/`) resolves to a real file (fails if not); separately, `docs/INDEX.md` specifically is checked for completeness — every real doc under `docs/` linked from it (warns if not — some are deliberately excluded) |
| 8 | Cross-file facts | `check_facts.py` — reads `facts.yml`, a short hand-curated list of specific facts (an IP, a hostname) restated as prose across multiple docs/scripts, and confirms each is still asserted correctly everywhere it's registered |
| 9 | Bootstrap scenarios | `check_scenarios.py` — reads `scenarios.yml`, covering the 4 bare-metal-to-working-estate scenarios (PVE+Ansible node, DNS, firewall, Windows unattend): confirms every file each depends on exists, and a handful of load-bearing warnings/framing comments (e.g. `ansibleme.sh`'s `git clone`, the break-glass framing in `bindme.sh`/`firewallme.sh`, the circular-dependency callout in `Procedure-PVE-Node-Onboarding.md`) haven't been edited away. Does not build real infrastructure — see `scenarios.yml`'s own header for what's deliberately out of scope (no real iLO/DRAC automation exists; the per-edition Windows unattend XML files don't exist yet) |
| 10 | Site data | `check_site_data.py` — reads `benarbejde/sites.csv` fresh every run (not a frozen snapshot): every `Site` code appears somewhere in `docs/*.md`, and every doc line naming exactly one site code alongside a literal IP has the right third octet for that site. Knows about the estate's real, deliberate exceptions (CLD is dual-homed LAN+vRACK; every site's firewall also has a WAN IP on the provisioning network at `192.168.139.<its own octet>`) so it doesn't flag those as mismatches. Lines asserting more than 3 literal IPs (multi-site `sed`/config-edit commands) are skipped for the octet check — too ambiguous to attribute safely — but still count toward coverage |
| 11 | SSH keypair | `check_ssh_keys.py` — two tiers. Clone-safe (real failure): `bootstrap/web/ansible_sshkey.pub` (the estate's one committed, HTTP-servable public key) is checked against all four `VRK-`/`FRD-answer.toml` + `VRK-`/`FRD-degraded.toml` `root-ssh-keys` copies — every file says "keep in sync if rotated" in its own comments; this confirms that promise holds. Host-local (informational unless `--strict`): is `ansible.cfg`'s configured `private_key_file` actually present on *this* host — resolved via `ansible-config dump`, not a second hardcoded copy of the setting. Missing on a bare clone is expected; missing on the real control node is what actually happened 2026-07-12 (EXAANSCLD001, see `ansible/tasks/ssh_key_preflight.yml`'s header) and is what `--strict` is for. If missing, scans `~/.ssh/` for a plausible candidate keypair (`.pub` comment containing "exa") and reports it |
| 12 | `playbook_dir`-relative paths | `check_playbook_dir_paths.py` — every `"{{ playbook_dir }}/../.../X"` expression (used with `read_csv`/`lookup('file', ...)`/a shell command — not the literal `src:`/`include_tasks:` paths check 3 already covers) is resolved against the file's real location and confirmed to exist. Found the hard way, 2026-07-12: `bootstrap-new-node.yml`'s `sites_csv_src` had one extra level of `../` copy-pasted from `00-preflight.yml` (which lives one directory deeper) — invisible to both `--syntax-check` (doesn't execute tasks) and check 3 (Jinja, not literal) until a real run finally reached that task for the first time |
| 13 | Mermaid diagrams | `check_mermaid.py` — **the one check here that needs real network access.** Every ```` ```mermaid ```` block in every git-tracked `*.md` file is actually POSTed to `kroki.io` and confirmed to render, not just locally syntax-guessed (no mermaid parser is vendored here, and mermaid's grammar has real gotchas no structural YAML/Ansible check could ever catch). Found 3 genuine syntax bugs across the repo's 49 diagrams this way: literal `\n` instead of `<br/>` for label line breaks (938 occurrences), a backslash-escaped quote, and an unquoted `(` inside a pipe-delimited edge label. Results are cached by content hash (`reports/.mermaid_cache.json`, gitignored) so only new/changed diagrams actually hit kroki.io on a given run. A genuine render failure always fails the check; `kroki.io` being unreachable is informational unless `--strict` is passed |
| 14 | Network diagram freshness | `check_network_diagram_freshness.py` — regenerates every site's "New Network (current)" mermaid subgraph across `docs/network-diagram/*.md` (one file per region, via `benarbejde/generate_network_diagrams.py`, marker-wrapped in `%% GENERATED:NEW-NETWORK:<SITE>:START/END`) into a scratch copy and diffs against committed — same "edited the source, forgot to regenerate" class as check 6, applied to the diagrams |
| 15 | Network diagram content invariants | `check_network_diagram_content.py` — independently scans (doesn't just re-run the generator) every committed New Network block across `docs/network-diagram/*.md` for two invariants from `network-diagram.md`'s Visual Standard: no FSMO/health/low-disk-space terms ever appear (that data is old-infra-only), and every node uses the uniform rect shape with a leading emoji symbol (see `docs/emojis/README.md`) |
| 16 | KeePass credential freshness | `check_keepass_freshness.py` — two tiers. Clone-safe (real failure): `benarbejde/extracted_credentials.json` is well-formed JSON, every entry has its required fields, every `role` is one `push_credentials_to_keepass.py`'s `GROUP_FOR_ROLE` actually knows how to file, no duplicate `(hostname, role)` pairs. Host-local (informational unless `--strict`): if this host has both the live `.kdbx` and `benarbejde/.keepassxc_master_password`, confirms `push_credentials_to_keepass.py --dry-run` has nothing left to add — same "source vs generated artefact" freshness pattern as checks 6/14, applied to the KeePassXC vault. Added 2026-07-14 after two live TP-Link entries turned out to carry a stale/wrong password with nothing to have caught it |
| 17 | WireGuard hub data | `check_wireguard_hub_data.py` — every hub (`CLD`/`FAL`/`ODE`/`BRK`) in `group_vars/firewalls/main.yml`'s `wg_hub_wan_ips` is checked against the derivable `192.168.139.<site's own subnet octet>` convention (from `sites.csv`) every other WAN IP in the estate follows — confirmed against all 4 real hubs before writing this check, not assumed. Also flags any hub with a blank `wg_hub_known_pubkeys` entry, since that silently skips the live known-good pubkey cross-check for every spoke built against it. Added 2026-07-14 after `CLD`'s WAN IP turned out to be wrong (a self-referential typo, `192.168.139.139` instead of the real `192.168.139.69`) for an unknown length of time, found live during the `EXAFWLBRT001` test |
| 18 | Playbook doc coverage | `check_playbook_doc_coverage.py` — fully automatic, no registration needed. Every `ansible/playbooks/<module>/` directory containing a real playbook (top-level `hosts:` key, same convention check 2 uses) must have its own `README.md` (fails otherwise). Every real playbook file must be named in its own dir's README, `ansible/README.md`, or anywhere under `docs/`, or be the resolved target of an `include_tasks`/`import_tasks`/`import_playbook` elsewhere (warns if truly orphaned — needs human triage, doesn't fail a clone). Added 2026-07-15 after `windows_hygiene/` shipped with six real playbooks and zero doc coverage anywhere, found only by a manual docs-drift audit |
| 19 | Feature doc/check pairing | `check_features.py` — reads `features.yml`, a short hand-curated list mapping a named feature to its doc path and its harness check reference (mirrors `scenarios.yml`'s idiom, at a per-feature grain instead of per-bootstrap-scenario). Confirms the doc still exists and the referenced check still exists in this README/`run.sh`. The only mechanism here that catches "a fully correct doc exists but nobody ever built a matching check" (or vice versa) — checks 1-18 are all structural/link-based and can't see that class of gap by construction. Same honest limitation as `scenarios.yml`: only catches a *registered* pair going stale, not an unregistered gap forming in the first place. Added 2026-07-15, seeded with the KeePass and WireGuard hub-data pairs as the founding precedent |

## Design notes

- **Checks 1–4 need no real hosts and no vault access** — deliberately, so
  this can run from a bare clone with nothing else set up. Check 2 passes
  `-e ad_forest_json_path=<repo>/benarbejde/ad_forest.json` (the real
  source-of-truth file, not a duplicate fixture) and a dummy
  `-e target=` so playbooks whose `vars_prompt` defaults reference
  `{{ target }}` or a real control node's `/etc/example-music/ad_forest.json`
  don't false-positive as syntax errors.
- **Check 5 needs a real `ansible-playbook` run**, but only against a
  throwaway, checked-in scratch inventory (`add_host_probe/`) with one
  `ansible_connection=local` host — never a real target.
- `check_references.py`'s role-relative resolution (checking
  `roles/<name>/templates/`/`files/` in addition to the referencing task
  file's own directory) exists because the naive playbook-relative-only
  guess produced false positives against `firewallme/roles/firewall/` — this
  repo's one actual Ansible role — before the role-awareness was added.
- **Drop-in assets are reported, not silently skipped, and don't fail the
  run.** The first version of `check_references.py` treated any `{{ }}` in a
  path as unresolvable and moved on — which meant `50-binaries.yml`'s 20
  arch-specific binaries (`ADExplorer64.exe`, `jq-windows-*.exe`, etc.,
  referenced via `src: "x86_64/{{ item.src_amd64 }}"` + `loop: "{{
  binaries_extra }}"`) were invisibly absorbed into a "skipped N dynamic"
  count instead of being named. Fixed to resolve `item.attr` against the
  loop's group_vars-defined list and report each one explicitly as a
  "drop-in asset" — these genuinely aren't meant to be committed (see
  `playbooks/windows_bootstrap/playbooks/files/README.md` and the
  `.gitkeep` placeholders in `files/x86_64/`/`files/arm64/`), so a missing
  one is expected on a fresh clone and doesn't fail the harness, but it's
  now named by exact filename instead of hidden in a summary count.
- `run.sh`'s syntax-check step deliberately `cd`s into `ansible/` before
  invoking `ansible-playbook`, rather than running from this directory with
  an absolute path — `ansible.cfg`'s `roles_path` is relative, and is only
  picked up by Ansible's config auto-discovery when `ansible/` is the
  current directory. Getting this wrong produced a false "role not found"
  failure against `firewallme` while this harness was first being written.
- **`facts.yml` is deliberately narrow, not a general scanner.** A broad
  regex scan for IP-literal patterns across every doc/script was considered
  and rejected — it would produce real false positives against historical
  changelog entries (which correctly describe *old*, deliberately-
  superseded values, per this repo's "never delete version history" rule)
  and illustrative examples. `facts.yml` only catches drift in a fact
  someone has already registered; it will not catch a new, unregistered
  inconsistency. Add to it as drift is found, rather than trying to make it
  exhaustive up front.
- **`check_facts.py` found real drift on its first run** (2026-07-10) —
  `docs/buildsheets/buildsheet-firewall.md`, `docs/bootstrap/bootstrapping.md`,
  and `docs/inventory/EXADNSVRK001-dns.md` all had the stale
  `EXAFWLCLD001`/wrong-Ansible-node-hostname errors it was built to catch.
  All three were fixed the same day, alongside a full correction pass on
  `bootstrapping.md` (found substantially stale — fictional file paths,
  wrong site codes, a backwards addressing table — while researching the
  scenarios `scenarios.yml` now checks). The harness is fully green again.
- **`scenarios.yml`'s content assertions are deliberately about framing,
  not facts.** Things like "does `ansibleme.sh` still say `git clone`" or
  "does `Procedure-PVE-Node-Onboarding.md` still have its circular-
  dependency warning" aren't drift-from-a-known-value the way `facts.yml`
  checks are — they're "has this load-bearing explanation been quietly
  edited away by someone who didn't understand why it was there." Keep
  that distinction when deciding whether a new check belongs in
  `facts.yml` or `scenarios.yml`.
- **`git ls-files`, not `find`, for repo-wide enumeration** (checks 1 and
  7, 2026-07-10) — two deliberate properties, not just a syntax swap.
  First, it only sees files git actually tracks, so a stray untracked or
  `.gitignore`d file never produces a false failure. Second, and more
  importantly, it means coverage grows automatically as the repo does —
  no hardcoded directory list to remember to update when a new top-level
  folder shows up. This immediately paid off: widening check 1 past
  `ansible/` found two previously-unchecked YAML files
  (`benarbejde/ad_computers_vault.yml`, `docs/zabbix_templates/*.yaml`),
  and widening check 7 past `docs/INDEX.md`'s own links found two more
  real broken links in `docs/ExampleMusic_Beginners_Guide.md` that the
  narrower check had no way to see (including a repeat of the exact
  `bootstrap/` vs `active-directory/` path bug already fixed once in
  `docs/INDEX.md` — the same mistake had been made in a second file, and
  nothing had ever checked that file's own links before).
