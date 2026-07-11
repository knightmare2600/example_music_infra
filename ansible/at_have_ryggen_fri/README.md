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

Nothing here touches a real host, needs a vault password, or needs network
access beyond `localhost` — safe to run on any clone, any time.

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
