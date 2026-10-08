# playbooks/cloudpanel/

Ansible playbooks for installing [CloudPanel](https://www.cloudpanel.io/) (the
Community Edition) on a fresh Debian or Ubuntu box — a straight conversion of
CloudPanel's own real installer script, not a reimplementation from docs or
guesswork.

**Converted from the real, checksum-verified upstream script**, 2026-10-07:

```
curl -sS https://installer.cloudpanel.io/ce/v2/install.sh -o install.sh
echo "8146dbe0a488e7088b04071b0c34d59aa0ab1fe9dcec382d395fd155c9e6c476 install.sh" | sha256sum -c
```

Every repo URL, GPG key URL, package name, and database-engine combination
in this playbook family is transcribed directly from that script — nothing
here was invented or guessed from CloudPanel's own docs. See each numbered
playbook's own header comment for exactly which of the original script's
bash functions it replaces.

**One deliberate deviation**, flagged in `30-cloudpanel.yml`'s own header:
the original script calls out to a public CloudFront endpoint purely to
learn its own public IP for the final "access CloudPanel at..." message —
irrelevant on this estate's internal addressing, so the final message uses
`ansible_host` instead. Everything else is a faithful conversion, not a
redesign.

---

## Files

Numbered-stage chain, matching `proxmox`/`salt`/`windows_bootstrap`/`truenas`'s
own `00-preflight`/major-step-of-10 convention, driven by `site.yml`:

| File | What it does | Original script function(s) |
|------|---------------|------------------------------|
| `playbooks/00-preflight.yml` | Hostname/site facts, OS/version/port/hostname-resolution/disk-space checks, database-engine validity check | `setOSInfo`, `checkRequirements`, `checkOperatingSystem`, `checkPortConflicts`, `checkDatabaseEngine`, `checkIfHostnameResolves`, `checkRootPartitionSize`, plus Robert's own pasted prerequisite (`apt update && apt -y upgrade && apt -y install curl wget sudo`) |
| `playbooks/10-packages.yml` | Base packages, locale generation, removes any pre-existing MySQL packages | `setupRequiredPackages`, `generateLocales`, `removeUnnecessaryPackages` |
| `playbooks/20-database.yml` | CloudPanel's own apt repo + the database engine itself | `addAptSourceList`, `installMySQL` |
| `playbooks/30-cloudpanel.yml` | Installs the `cloudpanel` package, confirms it's actually listening on 8443 | `setupCloudPanel`, `showSuccessMessage` |
| `playbooks/40-admin-user.yml` | Admin account (`clpctl user:add`) + database master credentials (`clpctl db:show:master-credentials`), both filed into KeePass | *not in the original script — its own first-run flow is manual, see below* |
| `playbooks/50-cleanup.yml` | `apt clean` (the original's `history -c` has no real Ansible equivalent — doesn't apply to a task run over SSH) | `cleanUp` |

`20-database.yml`'s own install logic is driven by
`group_vars/cloudpanel_servers/main.yml`'s `cloudpanel_db_matrix` — one entry
per (OS, OS version, database engine) combination the real script supports,
each tagged with which of four real mechanisms it needs (CloudPanel's own
repo, Percona's `percona-release` bootstrap, MariaDB's official repo, or
plain apt with no custom repo at all). This replaces the original script's
~400-line nested case statement with one lookup + four generic task blocks —
same real combinations, same real URLs/package names, one source of truth
instead of re-deriving the same validation twice (once in `checkDatabaseEngine`,
once again in `installMySQL`).

A real, deliberate asymmetry from the upstream script is preserved exactly,
not "fixed": MariaDB 11.4 gets the `mysql` → `mariadb-*` compatibility
symlinks on Debian 12, but **not** on Ubuntu 22.04 or 24.04 — confirmed by
reading `installMySQL()` directly, not assumed to be consistent across OSes.

### Admin account + KeePass (`40-admin-user.yml`)

CloudPanel's own first-run flow for creating the admin account is manual —
browse to `https://<ip>:8443` and fill in a form. There's no automated
equivalent in `install.sh` at all. The real mechanism this playbook uses
instead, confirmed via CloudPanel's own docs
(`cloudpanel.io/docs/v2/cloudpanel-cli/root-user-commands/`) before writing
it, not guessed:

```
clpctl user:add --userName='...' --email='...' --firstName='...' \
  --lastName='...' --password='...' --role='admin' --timezone='...' \
  --status='1'
```

a root-local CLI command, no HTTP request involved. `clpctl user:list` is
checked first so this never actually calls `user:add` against an existing
username — the real behaviour of `user:add` on a duplicate (error vs silent
update vs duplicate row) isn't documented anywhere findable, so this
sidesteps that unknown entirely rather than relying on it.

The password is generated and filed into KeePass via the same
check-defer-write pattern every other in-scope credential in this estate
uses (`ansible/tasks/keepass_credential_sync.yml`), at
`Infrastructure/<site>/<hostname>-cloudpanel-admin`.

**Also wires up the database master credentials** CloudPanel generates for
itself during `20-database.yml` (`clpctl db:show:master-credentials`) — a
second real credential this service produces, filed at
`Infrastructure/<site>/<hostname>-cloudpanel-db-master`. ***The exact output
format of `db:show:master-credentials` is NOT independently confirmed*** —
confirmed only that it shows Host/User Name/Password/Port/a Connect Command,
not the precise text layout. The parsing regex in `40-admin-user.yml` is a
reasonable attempt (tested locally against a few plausible format guesses,
not a real box) and fails loudly rather than filing a wrong value if it
can't find something that looks like a password — but it genuinely needs
confirming against a real run. If it fails, run
`clpctl db:show:master-credentials` by hand on the box and paste the real
output back so the regex can be corrected to match it exactly.

---

## Usage

First run, on a fresh box:

```
ansible-playbook playbooks/cloudpanel/site.yml \
  -i configs/inventory --limit <hostname>
```

Choosing a database engine (default `MYSQL_8.4`, matching the original
script's own default when `DB_ENGINE` is unset — see
`group_vars/cloudpanel_servers/main.yml`'s `cloudpanel_db_matrix` for every
supported combination):

```
ansible-playbook playbooks/cloudpanel/site.yml \
  -i configs/inventory --limit <hostname> -e cloudpanel_db_engine=MARIADB_12.3
```

Standalone plays can also be run directly without `site.yml` — each one is
self-contained and re-derives whatever facts it needs rather than assuming
an earlier play in the same run already set them:

```
ansible-playbook playbooks/cloudpanel/playbooks/20-database.yml -i configs/inventory --limit <hostname>
```

Inventory — add a host under `[cloudpanel_servers]`:

```
[cloudpanel_servers]
EXACLP<SITE>001   ansible_host=<address>
```

(`CLP` as the 3-letter role code, matching every other service's own
`EXA[ROLE][SITE][NNN]` convention — not yet added to `benarbejde/devices.csv`,
since that's a separate decision about whether this becomes a tracked,
per-site standard role rather than a one-off box.)

---

## Not yet done

- **Not live-tested end-to-end** — this is a straight conversion of a real
  script (plus a from-scratch addition for the admin account), not yet run
  against a real box.
- **`db:show:master-credentials`'s exact output format is unconfirmed** —
  see `40-admin-user.yml`'s own header and the section above. The first real
  run is also the first real test of this specific parsing step.
- **`clpctl user:add` against an existing username is unconfirmed** —
  sidestepped by checking `user:list` first rather than relying on it, but
  the underlying behaviour itself was never confirmed either way.
