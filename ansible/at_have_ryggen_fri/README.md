# at_have_ryggen_fri

Danish: *"at have ryggen fri"* — to have your back covered.

An Ansible verification harness. Run it before merging anything that touches
inventory, `group_vars`/`host_vars`, `ansible.cfg`, or any playbook's file
references, to catch the exact classes of bug found the hard way in this
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
| 3 | Reference integrity | `check_references.py` — every literal `src:`/`include_tasks:`/`import_tasks:`/`import_playbook:` path resolves to a real file, correctly handling both playbook-relative and role-relative (`roles/<name>/templates|files/`) resolution |
| 4 | Inventory structure | `check_inventory_structure.py` — the real `configs/inventory`'s `windows_dc → windows_server → windows → windows_nodes` chain exists across multiple sites (not just the 3 hand-curated ones); `group_vars` genuinely resolves (become correctly scoped to `linux` only, never Windows; `colours.yml`'s `_c` dict present) — via `ansible-inventory`, no host contacted |
| 5 | `add_host` visibility | `add_host_probe/` — a live two-play `ansible-playbook` run: play 1 registers a scratch host into a group via `add_host` (`delegate_to: localhost`), play 2 asserts that group's `group_vars` resolved for it — the exact mechanism `windows_bootstrap/00-preflight.yml`'s Phase H2 depends on |

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
- `run.sh`'s syntax-check step deliberately `cd`s into `ansible/` before
  invoking `ansible-playbook`, rather than running from this directory with
  an absolute path — `ansible.cfg`'s `roles_path` is relative, and is only
  picked up by Ansible's config auto-discovery when `ansible/` is the
  current directory. Getting this wrong produced a false "role not found"
  failure against `firewallme` while this harness was first being written.
