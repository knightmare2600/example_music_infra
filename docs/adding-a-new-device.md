# Adding a new device to the estate

**Classification:** Internal — Infrastructure
**Doc ID:** OPS-DEVICE-001

The step-by-step workflow for adding a new device — a new server, a new client
endpoint, anything — to `benarbejde/devices.csv` and getting every generated
artefact (inventory `.ini` files, DNS, network diagrams, Salt pillar) back in
sync with it. Written 2026-08-06 after this exact workflow (adding
`EXAMSHCLD001`/`EXARMMCLD001`) was done by hand with no doc to follow —
Robert: "how do we 'set' an IP without running the harness — docs need
fattening up."

See [ExampleMusic_Beginners_Guide.md](ExampleMusic_Beginners_Guide.md) for the
estate's addressing conventions in full; this doc is the practical checklist,
not a repeat of that explanation.

## 1. Does this device need a new role code?

Check whether `benarbejde/role_codes.csv` already has a `Code` matching what
this device actually is (e.g. `SVR`, `WKS`, `NAS`). If it's a genuinely new
class of device, add a row first:

```
Code,Name,Category,ConnectionMethod,Emoji,DNSAlias,Notes
```

- `Code`: 2-4 uppercase letters, not already in use.
- `ConnectionMethod`: how Ansible/Salt reaches it (`ssh`/`winrm`/`telnet`/
  `snmp`/`http`/`none`).
- `Emoji`: shows up in every generated network diagram — see
  [network-diagram.md](network-diagram.md)'s Visual Standard section.
- `DNSAlias`: only set this if the role gets a friendly short CNAME (like
  `SLT` → `salt`) — leave blank otherwise, most roles don't have one.

Also add the matching row to `docs/emojis/README.md`'s legend table —
`check_role_codes.py` (check 20) fails if the two ever disagree.

**Never guess a code is fine without checking** — `check_role_code_usage.py`
(check 34) hard-fails if `devices.csv` ever uses a `Type` with no matching
`role_codes.csv` `Code`, but it only catches it after the fact. Check first.

## 2. Pick a site and a free IP octet

Run the free-octet finder against the site this device belongs to:

```bash
python3 benarbejde/suggest_free_ip.py <SITE>
# e.g.
python3 benarbejde/suggest_free_ip.py CLD
```

It reads `benarbejde/devices.csv` (real occupied octets, attributed to the
device's *effective* subnet — its `SubnetSite` override if set, otherwise its
`Site`) and `benarbejde/address_policy.csv` (estate-wide standard-slot
reservations — RTR/BMC/DCS/NAS/RDR/PVE/SWI/FWL/WAP/WKS/LAP — reserved whether
or not this particular site has one of those yet) and prints a suggested list
of genuinely free octets.

**This is a suggestion, not a decision.** Pick one from the list and confirm
it with Robert before writing anything to `devices.csv` — do not silently
commit a chosen IP yourself. (This is a standing instruction, not a
one-off preference — see the project memory this doc itself came out of.)

## 3. Add the `devices.csv` row

```
Site,Type,Number,HostOctet,OS,ConnectionType,Managed,Notes,SubnetSite,Legacy,Migrating,Planned
```

- `Site`: the site this device is hostnamed under (may differ from
  `SubnetSite` — see [network-diagram.md](network-diagram.md)'s SubnetSite
  note, or `check_subnet_site_mismatch.py`, check 27).
- `Type`: the role code from step 1.
- `Number`: instance number — `1` unless this role already has one at this
  site (e.g. a second PBX is `2`).
- `HostOctet`: the octet confirmed with Robert in step 2.
- `Notes`: free text — what this device is for, who asked, when. Every real
  example in `devices.csv` writes a full sentence here; a bare device
  description with no context is a missed opportunity six months from now.
- `SubnetSite`: leave blank unless this device's real IP sits on a different
  site's subnet than its hostname implies.
- `Legacy`/`Migrating`/`Planned`: leave blank (`no`) unless genuinely one of
  those — see existing rows for examples.

`devices.csv` is **exceptions-only** — don't add a row for something the
standard addressing convention (`address_policy.csv` + `sites.csv`) already
covers automatically (a site's router, DCs, Proxmox nodes, SBC, firewalls).

## 4. Regenerate everything downstream

Nothing here writes itself — every generated artefact needs an explicit
regeneration command after `devices.csv`/`role_codes.csv` changes.

```bash
# Inventory .ini files -- MUST pass -o explicitly. The default -o is
# ~/ansible/configs/inventory (a home-directory path, NOT this repo) --
# omitting it silently writes stray .ini files outside the repo entirely.
# See generate_inventory.py's own main() comment for the real 2026-07-30
# incident this footgun caused. Also prompts "Overwrite? [y/N]" once per
# existing .ini file (53 of them) -- pipe `yes` through it, you always want
# the fresh regeneration to win here. Confirmed live, 2026-08-06: this exact
# command, piped through `yes`, regenerated all 53 files with zero drift.
yes | python3 benarbejde/generate_inventory.py benarbejde/sites.csv \
  -o ansible/configs/inventory \
  --devices benarbejde/devices.csv

# site_services.yml, begyndelse.json, salt/pillar/sites.sls -- these three
# default to the correct real repo path already (resolved relative to the
# generator script's own location), no -o footgun.
python3 benarbejde/generate_inventory.py benarbejde/sites.csv --emit-group-vars \
  --devices benarbejde/devices.csv
python3 benarbejde/generate_inventory.py benarbejde/sites.csv --emit-begyndelse-json \
  --devices benarbejde/devices.csv
python3 benarbejde/generate_inventory.py benarbejde/sites.csv --emit-site-grains-pillar \
  --devices benarbejde/devices.csv

# Network diagrams (New Network box, Topology sketch, Old Network box) --
# writes docs/network-diagram/*.md in place.
python3 benarbejde/generate_network_diagrams.py --write
```

`bootstrap/web/proxmox/`'s mirror copies of `sites.csv`/`devices.csv`/
`address_policy.csv`/`role_codes.csv` do **not** need a manual copy step —
`.githooks/pre-commit` overwrites them from `benarbejde/` automatically and
stages the result as part of your commit (see the top-level `README.md`'s
`benarbejde/` section). Make sure that hook is actually installed (`## One-time
setup (per clone)` in the same `README.md`) — if it isn't, the copies will
drift and nothing will tell you until `check_generated_freshness.py` (check 6)
fails on your next harness run.

## 5. Run the harness

```bash
bash at_have_ryggen_fri/run.sh
```

Confirms the regeneration in step 4 actually matches what's committed (check
6, check 14, check 31, check 32), the new role code (if any) is consistent
everywhere (check 20, check 34), and nothing else drifted. Fix anything it
flags before committing.

## 6. Update hand-maintained docs, if this device needs it

`site-inventory.md`, `network-inventory.md`, and
`ExampleMusic_Beginners_Guide.md`'s per-site tables are **not** generated —
they're hand-maintained prose that happens to reference real hostnames.
`check_doc_role_coverage.py` (check 28, informational unless `--strict`) flags
a real device missing from its site's section in either file — fix anything
it reports.

## 7. Build the device, if applicable

This doc only covers getting the device correctly represented in the data —
actually building/provisioning it depends entirely on what it is. See
[INDEX.md](INDEX.md)'s Quick Reference table for the right buildsheet/
playbook (Proxmox node, domain controller, workstation, firewall, etc.).

## 8. Commit

One commit for the `devices.csv`/`role_codes.csv` change plus every
regenerated file it touches — see recent examples in `git log` for the
expected shape (e.g. the commit that added `EXAMSHCLD001`/`EXARMMCLD001`).
Don't split the source-data edit from its own regeneration into separate
commits — a commit that changes `devices.csv` without also updating what it
generates is exactly what `check_generated_freshness.py` exists to catch.
