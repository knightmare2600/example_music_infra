# salt/

Salt states and pillar data for `EXASLTCLD001` (the Salt master — see
`ansible/playbooks/salt/README.md` for how the master itself gets built, and
`docs/buildsheets/buildsheet-salt-minion.md` for how minions get onboarded).

This directory is the content the master serves to minions — not to be
confused with `ansible/playbooks/salt/`, which is the Ansible playbook that
*bootstraps the master itself*.

## Layout

```
salt/
├── README.md          ← this file
├── states/
│   ├── top.sls        ← state top file (target-match -> state list)
│   ├── _modules/
│   │   └── screenprint.py  ← custom execution module, see below
│   ├── wintools/
│   ├── grains/
│   ├── audit/
│   ├── bespoke_app_install/  ← generic, NOT in top.sls — see its own
│   │                           install/init.sls header for why
│   └── adtools/       ← PS-easyIT AD/Exchange admin tool suite, NOT in
│                         top.sls either — apply explicitly per minion, see
│                         its own init.sls header
└── pillar/
    ├── top.sls        ← pillar top file (target-match -> pillar-data list)
    └── sites.sls      ← generated, Site -> {city, country, entity, street,
                          postal_code} lookup (benarbejde/generate_inventory.py
                          --emit-site-grains-pillar)
```

`_modules/` (and `_grains/`, `_states/`, etc. if any ever get added) live at
the top of `states/`, not their own top-level folder — Salt's own convention:
these "dunder" directories are resolved relative to `file_roots`/`gitfs_root`
(`salt/states` here), synced to minions automatically on highstate or via
`saltutil.sync_all`.

**`screenprint.py`** — colourised console output for `module.run` state calls.
Ported 2026-07-20 from `github.com/knightmare2600/saltstack` (Robert's own
personal Salt utilities repo, since retired — this was its only real content).
Extended the same day: the version there only took a `color` argument, but the
node-audit state it was ported alongside already called it with `messagetype`
instead — a parameter the function never actually had. `messagetype` is now
real, mapped onto the same ANSI colour convention
already used estate-wide in `colours.yml` (`_c.R/G/Y/C/W/NC`), not a new scheme
invented separately. See the module's own docstring for the full mapping.

## Delivery mechanism: gitfs / git_pillar — wired up 2026-07-20

This repo is public (`github.com/knightmare2600/example_music_infra`), so the
master reads `states/` and `pillar/` straight from the plain HTTPS clone URL —
no deploy key, no token, nothing to leak, since anyone can already read a
public repo. Salt's actual git-backed mechanisms are two separate things, not
one, both now configured in `ansible/playbooks/salt/playbooks/10-master.yml`'s
Section 6:

- **`gitfs`** (fileserver backend) — serves `states/` (`gitfs_root: salt/states`).
- **`git_pillar`** (an `ext_pillar` module) — serves `pillar/` separately
  (`root: salt/pillar`). Different config block from `gitfs_remotes`, even
  though both point at the same repo here.

Both replace a hand-rolled "clone the repo + cron job running `git pull` +
`salt '*' saltutil.refresh_pillar`" approach found in a dropped-in Salt state
while reviewing `salt/cleanup/salt/salt/pillar.sls` — neither gitfs nor
git_pillar need that; they sync from the git remote natively on their own.

**Shallow clone (added 2026-08-11, real live disk-bloat fix)**: both are
configured with `provider: gitcli` + `depth: 1` — a full-history clone of
this repo is 3GB+ (it permanently carries every large binary ever committed
before it was LFS-tracked; LFS migration here is prospective-only, not a
history rewrite), which gitfs/git_pillar were downloading in full for the
sake of a handful of small `states/`/`pillar/` text files. `depth: 1` only
has an effect on the `gitcli` provider, not `pygit2`/`gitpython` — see
`10-master.yml`'s own Section 6 header comment for the full reasoning and
the one-time cache-clear command needed after this landed.

## Pillar and secrets

This repo is public. Nothing genuinely sensitive goes in `pillar/` in
plaintext, ever — see `pillar/top.sls`'s own header. Salt's GPG pillar
renderer is the equivalent of this repo's existing `ansible-vault` pattern
(`ansible/configs/inventory/group_vars/rudder_servers/vault.yml`) if a real
secret is ever unavoidable here. Real credentials still belong in KeePass by
default, matching how every other credential in this estate is handled.

## Workflow note

Robert is dropping real Salt states in here for review before anything gets
committed or pushed — see git status/diff for what's actually staged at any
given point; nothing in this directory should be assumed pushed to GitHub
just because it's present in the working tree.
