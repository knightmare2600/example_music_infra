# windows_adschema

Builds the AD OU schema, security groups, user accounts and computer
accounts against a single target Domain Controller. Ansible-driven
replacement for manually populating a demo/production forest from the TDF
and sites.csv.

## Usage

This is always run as its own, separate command — it is never automatically
chained from `windows_dc/site.yml`, even if you answered "yes" to the
`populate_ad` prompt at DC preflight. That prompt only records the answer;
`import_playbook`'s `hosts:` patterns are resolved at parse time, before the
prompt has actually run, so a later imported play has no way to see the
answer. `40-dc-summary.yml` prints the exact command below once DC
promotion has succeeded.

```
# Normal path — after DC promotion, once 40-dc-summary.yml prints this command
ansible-playbook playbooks/windows_adschema/site.yml -e populate_ad=yes -e ad_target=<host> --ask-vault-pass

# Standalone — prompted for the target Domain Controller
ansible-playbook playbooks/windows_adschema/site.yml -e populate_ad=yes --ask-vault-pass

# Single stage, run directly without site.yml
ansible-playbook playbooks/windows_adschema/playbooks/20-ad-groups.yml -e ad_target=<host> --ask-vault-pass
```

No tags are used here — unlike windows_dc/site.yml, this playbook is always
run against a single host to "up" the AD schema, so there's nothing to
select between.

## Playbook order

`00` is always the preflight ("before take off"); major steps increment by 10.

| File | Description |
|------|-------------|
| `playbooks/00-ad-preflight.yml` | Prompts for the target Domain Controller, stores it for every later stage to read back (see above) |
| `playbooks/10-ad-schema.yml` | Creates the AD OU schema (additive only) |
| `playbooks/20-ad-groups.yml` | Creates all AD security groups from `jukebox.example.tdf` (`$Script:rawDemoGroups`), under `OU=Security Groups,OU=IT Groups` |
| `playbooks/30-ad-users.yml` | Creates AD user accounts from `jukebox.example.tdf` (`$Script:rawUsers`) |
| `playbooks/40-ad-computers.yml` | Creates AD computer accounts from `ad_computers.json` |

## Dependencies
Install galaxy collections first:
```
ansible-galaxy collection install -r requirements.yml
```

## 00-ad-preflight.yml — target Domain Controller prompt

`00-ad-preflight.yml` prompts for the Domain Controller name or IP to build
and populate the AD schema against, and stores it against
`hostvars['localhost']['ad_target']` for every later stage in the same run
to read back.

**How it decides:**

| Condition | ad_target resolves to |
|-----------|------------------------|
| -e ad_target=\<host\> supplied | that value — prompt is skipped entirely |
| populate_ad=yes, no ad_target supplied | interactive prompt (00-ad-preflight.yml) |
| populate_ad != yes | play's hosts: pattern resolves to an empty list — prompt never fires |

**Order of operations:** the prompt happens once, in 00-ad-preflight.yml.
10-ad-schema.yml, 20-ad-groups.yml, 30-ad-users.yml and 40-ad-computers.yml
all read the same value back out of `hostvars['localhost']` rather than
prompting again.

**Standalone runs:** if you run a numbered stage directly without
00-ad-preflight.yml having run first in the same `ansible-playbook`
invocation, `hostvars['localhost']['ad_target']` won't exist. Each stage
falls back to `localhost` in that case and fails cleanly with a message
telling you to supply `-e ad_target=<host>` — it will not silently run
against the wrong host.

## Additive only

Every stage here is additive only (`state: present` throughout). None of
them delete OUs, groups, users or computer accounts on re-run. To remove
an object, use ADUC (`dsa.msc`) or a targeted ad-hoc task — there is no
automated wipe.
