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

Phases 1 (repo-wide reference/data integrity) and 2 (the estate's bare-metal
bootstrap scenarios as repeatable checks) are both done as of 2026-07-10 —
see the git history for the fuller context if picking this back up later.
Phase 3 (the unattend XML per-edition variants, and any further findings)
is still open.

Nothing here touches a real host, needs a vault password, or needs network
access beyond `localhost` — safe to run on any clone, any time.

## Usage

```bash
cd ansible/at_have_ryggen_fri
./run.sh
```

Exit code 0 if every check passes, 1 otherwise. Colour-coded output follows
the same `[*]`/`[+]`/`[!]`/`[✗]` convention as `firewallme.sh`/`ansibleme.sh`.

## What it checks

| # | Check | How |
|---|-------|-----|
| 1 | YAML validity | Every `*.yml` under `ansible/` (excluding this directory) parses, including `!vault`-tagged files |
| 2 | `ansible-playbook --syntax-check` | Every file with a top-level `hosts:` key |
| 3 | Reference integrity | `check_references.py` — every literal `src:`/`include_tasks:`/`import_tasks:`/`import_playbook:` path resolves to a real file, correctly handling both playbook-relative and role-relative (`roles/<name>/templates|files/`) resolution. Also resolves `src: "...{{ item.attr }}..."` when combined with `loop: "{{ some_group_vars_list }}"` — the group_vars list is static, so `item.attr` is substitutable per loop item even though it's technically Jinja (this is how `50-binaries.yml`'s x86_64/arm64 binary paths get checked, not silently skipped as "dynamic") |
| 4 | Inventory structure | `check_inventory_structure.py` — the real `configs/inventory`'s `windows_dc → windows_server → windows → windows_nodes` chain exists across multiple sites (not just the 3 hand-curated ones); `group_vars` genuinely resolves (become correctly scoped to `linux` only, never Windows; `colours.yml`'s `_c` dict present) — via `ansible-inventory`, no host contacted |
| 5 | `add_host` visibility | `add_host_probe/` — a live two-play `ansible-playbook` run: play 1 registers a scratch host into a group via `add_host` (`delegate_to: localhost`), play 2 asserts that group's `group_vars` resolved for it — the exact mechanism `windows_bootstrap/00-preflight.yml`'s Phase H2 depends on |
| 6 | Generated-file freshness | `check_generated_freshness.py` — regenerates `configs/inventory/*.ini`, `site_services.yml`, and `begyndelse.json` from `benarbejde/sites.csv`+`devices.csv`+`address_policy.json`+`ad_forest.json` into a scratch dir and diffs against committed — catches "edited the source, forgot to regenerate" |
| 7 | Documentation index | `check_doc_index.py` — every link in `docs/INDEX.md` resolves to a real file (fails if not); every real doc under `docs/` is linked from it (warns if not — some are deliberately excluded) |
| 8 | Cross-file facts | `check_facts.py` — reads `facts.yml`, a short hand-curated list of specific facts (an IP, a hostname) restated as prose across multiple docs/scripts, and confirms each is still asserted correctly everywhere it's registered |
| 9 | Bootstrap scenarios | `check_scenarios.py` — reads `scenarios.yml`, covering the 4 bare-metal-to-working-estate scenarios (PVE+Ansible node, DNS, firewall, Windows unattend): confirms every file each depends on exists, and a handful of load-bearing warnings/framing comments (e.g. `ansibleme.sh`'s `git clone`, the break-glass framing in `bindme.sh`/`firewallme.sh`, the circular-dependency callout in `Procedure-PVE-Node-Onboarding.md`) haven't been edited away. Does not build real infrastructure — see `scenarios.yml`'s own header for what's deliberately out of scope (no real iLO/DRAC automation exists; the per-edition Windows unattend XML files don't exist yet) |

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
