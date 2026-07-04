# windows_adschema

Builds the AD OU schema, security groups, user accounts and (once migrated)
computer accounts against a single target Domain Controller. Ansible-driven
replacement for manually populating a demo/production forest from the TDF
and sites.csv.

## Usage
```
# Normal path — via windows_dc/site.yml, prompted once at 85-dc-preflight.yml
ansible-playbook playbooks/windows_dc/site.yml -i <inventory> -e target=<host>

# Standalone — prompted for the target Domain Controller
ansible-playbook playbooks/windows_adschema/site.yml -e populate_ad=yes --ask-vault-pass

# Standalone — target supplied directly, skips the prompt
ansible-playbook playbooks/windows_adschema/site.yml -e populate_ad=yes -e ad_target=<host> --ask-vault-pass

# Single stage, run directly without site.yml
ansible-playbook playbooks/windows_adschema/playbooks/20-ad-groups.yml -e ad_target=<host> --ask-vault-pass
```

No tags are used here — unlike windows_dc/site.yml, this playbook is always
run against a single host to "up" the AD schema, so there's nothing to
select between.

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
(once migrated) all read the same value back out of `hostvars['localhost']`
rather than prompting again.

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
