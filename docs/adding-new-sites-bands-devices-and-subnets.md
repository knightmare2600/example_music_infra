# Adding New Sites, Bands, Devices and Subnets to the Framework

**Classification:** Internal — Infrastructure
**Doc ID:** OPS-ONBOARD-001 (merges and retires OPS-SITE-001 `adding-a-new-site.md` and
OPS-DEVICE-001 `adding-a-new-device.md` — both fully folded into this doc, 2026-10-03, so
there is a single source of truth for onboarding instead of three overlapping docs
cross-referencing each other. Neither old file exists any more; every reference to
either, anywhere in the repo, now points here.)

## 0. Introduction

This is the combined, exhaustive walkthrough for bringing a genuinely new site into the
estate end to end: the site itself, its standard equipment, any non-standard device, its
subnet, and — because this is a *music* company — the band(s) based there, their AD
organisational units, security groups and user accounts.

**Worked example used throughout**: a new site at **Bremen, Germany** (site code `BRE`),
to host the German new-wave band **Trio** (of "Da Da Da" fame), modelled with their
classic 1980–1985 line-up: Stephan Remmler (vocals/keyboards), Gert "Kralle" Krawinkel
(guitar), Peter Behrens (drums). Every command and value below is real and was checked
against this estate's actual current data before being written down — but this
particular run was **never actually executed**; nothing in `benarbejde/`,
`ansible/configs/inventory/`, or `docs/network-diagram/` was touched to produce this
document. Treat every snippet as "what you would type," not "what has already
happened."

---

## 1. Prerequisites

Read this whole section before touching anything. It exists so you don't discover a
missing piece of context three steps in, at 3am, after a long-haul flight.

### 1.1 What you need before you start

- A clone of this repo, with `.githooks/pre-commit` installed (`## One-time setup (per
  clone)` in the top-level `README.md` — if you skip this, the `bootstrap/web/proxmox/`
  mirror copies of `sites.csv`/`devices.csv`/`address_policy.csv`/`role_codes.csv` will
  silently drift from `benarbejde/`'s real copies, and nothing will tell you until
  `check_generated_freshness.py` fails on a later, unrelated run).
- Python 3 with no extra packages needed for the generator scripts (stdlib only).
- `ansible-galaxy collection install -r ansible/playbooks/windows_adschema/requirements.yml`
  (and the equivalent for any other module you'll touch) if this is a fresh clone.
- The vault password (`--ask-vault-pass`), for every playbook invocation below.
- **Read access to a senior engineer** (Robert, or whoever's on call) — this procedure
  has several deliberate stop-and-confirm points. They are not optional. Do not pick a
  subnet, a site code, a free device octet, or a company-entity string on your own and
  just run with it.

### 1.2 The standard equipment every new site gets

This is the estate's standard boilerplate, defined in `benarbejde/address_policy.csv` —
every ordinary site gets these, and **none of them need a `devices.csv` row** (that file
is exceptions-only; the standard template renders all of this automatically from
`sites.csv` + `address_policy.csv` alone):

| Device | Standard octet(s) | Notes |
|---|---|---|
| Router (`RTR`) | `.1` | Upstream router |
| Firewall (`FWL`) | `.253` (primary), `.254` (secondary) | Secondary is usually `Planned=yes` until actually built |
| Switch (`SWI`) | `.250`, `.251`, `.252` | Up to 3 standard slots |
| Proxmox nodes (`PVE`) | `.5`, `.6`, `.7` | Up to 3 standard slots — the normal real-world count is 2 |
| BMC (`ILO`/`RAC` — iDRAC/iLO/Redfish) | `.2`, `.3`, `.4` | One per PVE node, same octet pool regardless of vendor — the vendor's own naming (`ILO` for HPE, `RAC` for Dell) decides the `Type`, not the octet |
| Domain Controller (`DCS`) | `.10` (primary), `.11` (secondary) | A *standard* site's own DCS is never given an explicit `devices.csv` row even once built — see §4 below |
| NAS (`NAS`) | `.19` | Storage (TrueNAS etc.) |
| Badge reader (`RDR`) | `.21` | |
| Session Border Controller (`SBC`) | `.48` | VoIP |
| Wireless access points (`WAP`) | `.82`–`.94` | Count varies per site, 1–13 |
| Example workstation/laptop (`WKS`/`LAP`) | `.101`/`.102` | Illustrative slots, not a real device you need to provision |
| DHCP pool | `.150`–`.250` | Not a device — reserved range, every site firewall's `dnsmasq` serves from it |

If a site genuinely doesn't need one of these (no NAS, say), that's fine — the
boilerplate tooling in Part A still writes a `Planned=yes` placeholder row for it, which
is correct: it documents that the estate's standard kit list expects one, even if it
hasn't been built yet.

### 1.3 Everything this touches — nothing here writes itself

Every one of the following gets updated as part of this procedure. If you only do the
"obvious" bit (the `sites.csv` row) and stop, every one of these stays stale:

- `benarbejde/sites.csv` — the site itself.
- `benarbejde/devices.csv` — only for devices outside the standard boilerplate (almost
  never needed for a genuinely new site on day one).
- `ansible/configs/inventory/<site>.ini` — the real Ansible inventory file for the site.
  **Generated, never hand-written.**
- `ansible/configs/inventory/group_vars/all/site_services.yml`, `benarbejde/begyndelse.json`,
  `ansible/configs/inventory/salt/pillar/sites.sls` — generated group-vars/pillar data.
  **Generated, never hand-written.**
- `docs/network-diagram/*.md` — the New Network box, Topology sketch, and Old Network
  box diagrams. **Generated, never hand-written.**
- `bootstrap/web/proxmox/`'s mirror copies of the four `benarbejde/*.csv` files —
  handled automatically by the pre-commit hook, not something you copy by hand.
- `benarbejde/jukebox.example.tdf` — only if you're also adding a band/users (Part C).
- `benarbejde/ad_users.json` / `benarbejde/ad_groups.json` — regenerated from the `.tdf`,
  never hand-edited directly.
- `benarbejde/ad_computers.json` — **not** touched by any of this until real hardware is
  actually built (Phase 2, §4 below) — don't pre-populate it for planned kit.

One command drives most of the "generated" list in one go — `benarbejde/regenerate_all.py`
— used throughout this doc rather than the five separate commands it wraps (the full
breakdown of what it runs internally, for when you need to debug one step alone, is in
Part B §4).

---

## Part A — Adding the site itself

### A.1 Add a row to `benarbejde/sites.csv`

```
Site,City,Country,CountryCode,Province,OfficeName,Street,PostalCode,Subnet,Gateway,DC,FW,Landline,Mobile,Timezone,AnsibleRegion,Entity
```

- `Site`: 2–4 uppercase letters, not already in use — check both `sites.csv` and
  `role_codes.csv` (site codes and role codes share no namespace, but a typo that
  collides with a role code will confuse everything downstream).

  ```bash
  grep -i "^BRE," benarbejde/sites.csv
  grep -i "^BRE," benarbejde/role_codes.csv
  ```

  Both come back empty — `BRE` is free. (Checked against the real repo at the time of
  writing — re-check it yourself before you commit, since someone else may have taken
  it since.) **Rule, not a suggestion**: every real site today uses a 2–4 letter,
  real-world-city-based code (`AAR`=Aarhus, `ABD`=Aberdeen, `CHI`=Chicago…). None are
  named after a band, a project, or anything else — keep "site" and "band" conceptually
  separate even when, like this worked example, they're being stood up together.

- `Subnet`: a genuinely free `/24`. **Never guess a subnet is free without checking** —
  see Part D below for the full derivation-and-confirmation procedure. For this worked
  example, Part D's result is **42** (`192.168.42.0/24`) — confirmed with Robert
  directly before being written into this example.

- `Gateway`/`DC`/`FW`: for a standard site these are almost always `.253`/`.10`/`.253`
  respectively (matching the [Addressing](../README.md#addressing) convention) — copy
  an existing same-region site's row as your starting template rather than typing these
  from scratch.

- `AnsibleRegion`: match an existing site in the same real-world region —
  `uk_site`/`eu_site`/`dk_site`/`de_site`/`us_site`/`ca_site`/`apac_site` cover most
  cases; `cloud_site`/`lb_site` are special (CLD/VRK-adjacent), don't use them for an
  ordinary new site.

- `Entity`: the legal entity this site trades under — copy the exact string from
  another site in the same country (e.g. `Example Music (US) LLC.`), don't invent a new
  variant.

Checked against real existing German rows (`BER`/`BON`/`DRS`/`DUS`/`MUN`) rather than
guessed, the worked-example row is:

```
BRE,Bremen,Germany,DE,Bremen,,<street — confirm with Robert, see note>,28195,192.168.42.0/24,192.168.42.253,192.168.42.10,192.168.42.253,+49 421 555 0xxx,+49 1515 555 0xxx,Europe/Berlin,de_site,Example Music (Deutschland) GmbH
```

- `Landline`/`Mobile` use the same `555` placeholder-number convention every other
  site's fictional phone number already uses (real area code, fake subscriber number) —
  deliberate, not a real phone number, matching `BER`'s `+49 311 555 xxx` and similar.
- `Entity` = `Example Music (Deutschland) GmbH` — copied byte-for-byte from an existing
  German site, **not** invented. If this site genuinely needs a different one (a
  different subsidiary), that's a confirm-with-Robert question, not a judgement call to
  make alone.
- `Province` = `Bremen` — Bremen is unusual among German states in that the city and the
  federal state (`Land Bremen`) share a name; this affects the AD OU path too, see
  Part C's own note on it.
- `Street`/`PostalCode` are illustrative placeholders in this worked example — **a real
  new-site row needs the real registered office address**, which is not something to
  invent. Confirm it before writing the real row.

**Never guess a subnet or gateway is free without checking** — confirm with Robert
before committing.

### A.2 Regenerate and get the boilerplate written

Two ways to do this, in increasing order of automation:

**Manual** (same commands as Part B §4 below — inventory `.ini`, `group_vars`/
`begyndelse.json`/Salt pillar, network diagrams). Nothing in `devices.csv` needs
touching yet — every standard boilerplate device (router, firewall, switch, WAP, SBC,
badge reader, NAS, two Proxmox nodes + their BMCs, domain controller) is already fully
predictable from `sites.csv` + `address_policy.csv` alone and renders correctly with
**zero** `devices.csv` rows (confirmed live against `det.ini`).

**Automated** (recommended — this is exactly what removes the human-error risk of
typing out a dozen hostname/IP/vendor combinations by hand):

```bash
python3 at_have_ryggen_fri/check_new_site_boilerplate.py --apply BRE
```

This writes real `devices.csv` rows for the full boilerplate list, each marked
`Planned=yes` (the same convention already used estate-wide for confirmed-but-not-yet-
built hardware, e.g. ODE's second firewall) — not asserting the hardware is real yet,
just recording what's expected so diagrams and inventory reflect it, and so this same
check stops reporting the site as having *literally nothing* known about it. It then
regenerates every derived artefact (`.ini` files, `group_vars`, diagrams) in the same
run, and syncs the `bootstrap/web/proxmox/` mirror copies. Refuses to run against a site
that isn't in `sites.csv`, is one of the architecturally-special sites (`CLD`/`VRK`/
`FRD`), or already has any real `devices.csv` rows — this is specifically for a
genuinely brand-new site, not a way to bulk-append to one already in progress.

**A partially-built site — already has some real equipment, just not all of it** —
needs a different command:

```bash
python3 at_have_ryggen_fri/check_new_site_boilerplate.py --complete BRE
```

Checks every boilerplate Type against what the site already has on record (any real row
of that Type counts, regardless of Number/octet — a firewall sitting at a non-standard
Number still counts as "this site has a firewall"), then writes `Planned=yes` rows for
exactly the missing Types, leaving everything already there untouched. Refuses if the
site has zero existing rows at all (use `--apply` instead) or is architecturally
special.

**Both deliberately do NOT touch `ad_computers.json`.** That file drives real
`New-ADComputer` creation — writing planned/unbuilt hardware into it would try to
create real AD objects for equipment that doesn't exist yet. AD records only get added
once hardware is actually confirmed built (§4 below).

### A.3 Run the harness

```bash
bash at_have_ryggen_fri/run.sh
```

Check 44 (`check_new_site_boilerplate.py`) confirms the new site's addressing is sane
and shows its boilerplate. If you used `--apply`, the rest of the harness (freshness
checks, role-code checks, etc.) confirms the regeneration actually landed cleanly. Fix
anything it flags before committing.

### A.4 Commit

One commit for the `sites.csv` row plus every file `--apply`/the manual regeneration
touched — don't split the source-data edit from its own regeneration.

---

## Part B — Adding a device that isn't part of the standard boilerplate

Only relevant if the new site needs something *beyond* the standard kit list in §1.2 (a
second NAS, an unusual appliance, whatever) — or any time you're adding a device to an
**already-existing** site. If everything the new site needs is already covered by Part
A, **skip this whole part**.

### B.1 Does this device need a new role code?

Check whether `benarbejde/role_codes.csv` already has a `Code` matching what this
device actually is (e.g. `SVR`, `WKS`, `NAS`). If it's a genuinely new class of device,
add a row first:

```
Code,Name,Category,ConnectionMethod,Emoji,DNSAlias,Notes
```

- `Code`: 2-4 uppercase letters, not already in use.
- `ConnectionMethod`: how Ansible/Salt reaches it (`ssh`/`winrm`/`telnet`/`snmp`/`http`/
  `none`).
- `Emoji`: shows up in every generated network diagram — see
  [network-diagram.md](network-diagram.md)'s Visual Standard section.
- `DNSAlias`: only set this if the role gets a friendly short CNAME (like `SLT` →
  `salt`) — leave blank otherwise, most roles don't have one.

Also add the matching row to `docs/emojis/README.md`'s legend table —
`check_role_codes.py` (check 20) fails if the two ever disagree.

**Never guess a code is fine without checking** — `check_role_code_usage.py` (check 34)
hard-fails if `devices.csv` ever uses a `Type` with no matching `role_codes.csv` `Code`,
but it only catches it after the fact. Check first.

### B.2 Pick a site and a free IP octet

Run the free-octet finder against the site this device belongs to:

```bash
python3 benarbejde/suggest_free_ip.py <SITE>
# e.g.
python3 benarbejde/suggest_free_ip.py BRE
```

It reads `benarbejde/devices.csv` (real occupied octets, attributed to the device's
*effective* subnet — its `SubnetSite` override if set, otherwise its `Site`) and
`benarbejde/address_policy.csv` (estate-wide standard-slot reservations —
RTR/BMC/DCS/NAS/RDR/PVE/SWI/FWL/WAP/WKS/LAP — reserved whether or not this particular
site has one of those yet) and prints a suggested list of genuinely free octets.

**This is a suggestion, not a decision.** Pick one from the list and confirm it with
Robert before writing anything to `devices.csv` — do not silently commit a chosen IP
yourself. (This is a standing instruction, not a one-off preference. The same rule, at
whole-subnet scale instead of single-device scale, is Part D below.)

### B.3 Add the `devices.csv` row

```
Site,Type,Number,HostOctet,OS,ConnectionType,Managed,Notes,SubnetSite,Legacy,Migrating,Planned
```

- `Site`: the site this device is hostnamed under (may differ from `SubnetSite` — see
  [network-diagram.md](network-diagram.md)'s SubnetSite note, or
  `check_subnet_site_mismatch.py`, check 27).
- `Type`: the role code from B.1.
- `Number`: instance number — `1` unless this role already has one at this site (e.g. a
  second PBX is `2`).
- `HostOctet`: the octet confirmed with Robert in B.2.
- `Notes`: free text — what this device is for, who asked, when. Every real example in
  `devices.csv` writes a full sentence here; a bare device description with no context
  is a missed opportunity six months from now.
- `SubnetSite`: leave blank unless this device's real IP sits on a different site's
  subnet than its hostname implies.
- `Legacy`/`Migrating`/`Planned`: leave blank (`no`) unless genuinely one of those — see
  existing rows for examples.

`devices.csv` is **exceptions-only** — don't add a row for something the standard
addressing convention (`address_policy.csv` + `sites.csv`) already covers automatically
(a site's router, DCs, Proxmox nodes, SBC, firewalls).

### B.4 Regenerate everything downstream

Nothing here writes itself — every generated artefact needs an explicit regeneration
after `devices.csv`/`role_codes.csv` changes. Run the single orchestrator rather than
the commands by hand:

```bash
python3 benarbejde/regenerate_all.py
# or, to also run the full harness immediately afterward:
python3 benarbejde/regenerate_all.py --verify
```

This is the one real implementation of the regeneration sequence — the exact same
commands `at_have_ryggen_fri/check_new_site_boilerplate.py`'s own `--apply`/`--complete
<SITE>` already use for the new-site-boilerplate workflow in Part A, extracted into
`benarbejde/regenerate_all.py` so there's a single general entry point for any
`benarbejde/` edit, not just that one case.

<details>
<summary>What it runs internally, if a step fails and you need to debug it directly</summary>

```bash
# Inventory .ini files -- MUST pass -o explicitly. The default -o is
# ~/ansible/configs/inventory (a home-directory path, NOT this repo) --
# omitting it silently writes stray .ini files outside the repo entirely.
# Also prompts "Overwrite? [y/N]" once per existing .ini file (53+ of them) --
# pipe `yes` through it, you always want the fresh regeneration to win here.
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

These five commands can't be combined into fewer calls — `generate_inventory.py`'s own
flags are deliberately kept mutually exclusive (an additive-flags attempt once broke
`check_generated_freshness.py`'s process isolation and leaked 52 stray `.ini` files into
a default path). `regenerate_all.py` above runs them as genuinely separate subprocesses
for exactly this reason.
</details>

`bootstrap/web/proxmox/`'s mirror copies of `sites.csv`/`devices.csv`/`address_policy.csv`/
`role_codes.csv` do **not** need a manual copy step — `.githooks/pre-commit` overwrites
them from `benarbejde/` automatically and stages the result as part of your commit (see
the top-level `README.md`'s `benarbejde/` section). Make sure that hook is actually
installed (`## One-time setup (per clone)` in the same `README.md`) — if it isn't, the
copies will drift and nothing will tell you until `check_generated_freshness.py` (check
6) fails on your next harness run.

### B.5 Run the harness

```bash
bash at_have_ryggen_fri/run.sh
```

Confirms the regeneration in B.4 actually matches what's committed (check 6, check 14,
check 31, check 32), the new role code (if any) is consistent everywhere (check 20,
check 34), and nothing else drifted. Fix anything it flags before committing.

### B.6 Update hand-maintained docs, if this device needs it

`site-inventory.md`, `network-inventory.md`, and `ExampleMusic_Beginners_Guide.md`'s
per-site tables are **not** generated — they're hand-maintained prose that happens to
reference real hostnames. `check_doc_role_coverage.py` (check 28, informational unless
`--strict`) flags a real device missing from its site's section in either file — fix
anything it reports.

### B.7 Build the device, if applicable

This doc only covers getting the device correctly represented in the data — actually
building/provisioning it depends entirely on what it is. See [INDEX.md](INDEX.md)'s
Quick Reference table for the right buildsheet/playbook (Proxmox node, domain
controller, workstation, firewall, etc.).

### B.8 Commit

One commit for the `devices.csv`/`role_codes.csv` change plus every regenerated file it
touches. Don't split the source-data edit from its own regeneration into separate
commits — a commit that changes `devices.csv` without also updating what it generates
is exactly what `check_generated_freshness.py` exists to catch.

---

## Part C — Adding the band and its AD presence

This is the part neither of the two merged docs ever covered. Three layers, in order:
the raw demo-data source file, the generated JSON it produces, and the live AD objects
built from that JSON.

### C.0 How this estate actually models "a band" in Active Directory

Real people (band members, solo artists, even the odd actor/opera singer — see Arne
Lundemann at NYB, a genuine precedent for exactly this kind of addition) are AD users,
grouped into:

- **An AD security group per band/artist** (e.g. `Trio`), used for things like shared
  mailing lists and access control.
- **A dedicated OU per band**, nested under that site's `Users` OU, which itself nests
  under the full geographic hierarchy:

  ```
  DC=jukebox,DC=internal
   └─ OU=Sites
       └─ OU=Europe                    (continent)
           └─ OU=Germany                (country)
               └─ OU=Bremen              (city — no separate Province OU for BRE, see C.2 note)
                   ├─ OU=Users
                   │   └─ OU=Trio        (the band)
                   ├─ OU=Devices
                   └─ OU=Groups
  ```

  (Full canonical tree, every continent/country, is documented at the top of
  `ansible/playbooks/windows_adschema/playbooks/10-ad-schema.yml` — read it if Germany
  or Europe ever need a structural change, not just a new leaf.)

- **Cross-band functional groups** that members also belong to (`Vocalists`,
  `Guitarists`, `Bassists`, `Drummers`, …) — these are shared across every band in the
  estate, not per-band. Trio's three members will each join their own band group *plus*
  the matching instrument group(s).

**Important, checked directly, not assumed**: the city/country/continent OU skeleton
(`OU=Bremen,OU=Germany,OU=Europe,OU=Sites`) is built from **`sites.csv` directly** —
Part A, once run, is enough to get that skeleton created on the next `populate_ad` run,
*before* any band exists. The band's own leaf OU (`OU=Trio`) is built separately, from
the generated `ad_users.json`/`ad_groups.json` — so Part A and Part C are independent of
each other in sequence (you could do C before A, and the band OU creation would simply
wait until BRE's own city OU exists to nest under), but both still need to happen before
AD actually reflects a complete new site with a band in it.

### C.1 Edit `benarbejde/jukebox.example.tdf`

**Read the "LEGACY/DEFUNCT TOOL" warning in `parse_tdf.py`'s own header before touching
this** — the `.tdf` + `parse_tdf.py` pairing is still the real, live, correct way to
add/change **users and groups** (confirmed via real git history — D-A-D and Arne
Lundemann were added exactly this way, 2026-07-11). It is **not** the way to touch
computer accounts any more (`ad_computers.json` is now reconciled from `devices.csv` by
`benarbejde/merge_ad_computers.py` instead) — don't let that warning scare you off the
users/groups half, which is unaffected.

Find the `$Script:rawUsers=@(` array and add one block per band member, following the
exact existing convention (one `## ========== BandName (Country/City) ==========`
comment header, then one hashtable per member):

```powershell
## ========== Trio (Deutschland/Bremen) ==========
@{ Name='Stephan Remmler' ; SamAccountName='stephan.remmler' ; UserPrincipalName='stephan.remmler@example.net' ; LastLogonDate=(Get-Date).AddDays(-1.4) ; OU=@('Deutschland','Bremen','Trio') ; Groups=@('Trio','Vocalists','Keyboardists') ; Title='Lead Vocalist/Keyboardist' ; Email='stephan.remmler@example.net' ; Country='DE' ; Disabled=$false ; Locked=$false ; MustChangePassword=$false ; Department='Music' ; physicalDeliveryOfficeName='Bremen Office' ; telephoneNumber='+49 421 555 0101' ; mobile='+49 1515 555 0102' ; Street='<real street — confirm>' ; City='Bremen' ; PostalCode='28195' ; Company='Example Music (Deutschland) GmbH' ; Manager='' ; Description='Lead vocalist, keyboardist and co-founder of Trio' ; AuditLog=@(@{ Timestamp=(Get-Date).AddDays(-42).AddHours(9); Action='Created'; Details='User account created'; By='admin' }) },
@{ Name='Gert Krawinkel' ; SamAccountName='gert.krawinkel' ; UserPrincipalName='gert.krawinkel@example.net' ; LastLogonDate=(Get-Date).AddDays(-2.1) ; OU=@('Deutschland','Bremen','Trio') ; Groups=@('Trio','Guitarists') ; Title='Guitarist' ; Email='gert.krawinkel@example.net' ; Country='DE' ; Disabled=$false ; Locked=$false ; MustChangePassword=$false ; Department='Music' ; physicalDeliveryOfficeName='Bremen Office' ; telephoneNumber='+49 421 555 0103' ; mobile='+49 1515 555 0104' ; Street='<real street — confirm>' ; City='Bremen' ; PostalCode='28195' ; Company='Example Music (Deutschland) GmbH' ; Manager='Stephan Remmler' ; Description='Guitarist and co-founder of Trio, also known as "Kralle"' ; AuditLog=@(@{ Timestamp=(Get-Date).AddDays(-40).AddHours(9); Action='Created'; Details='User account created'; By='admin' }) },
@{ Name='Peter Behrens' ; SamAccountName='peter.behrens' ; UserPrincipalName='peter.behrens@example.net' ; LastLogonDate=(Get-Date).AddDays(-1.8) ; OU=@('Deutschland','Bremen','Trio') ; Groups=@('Trio','Drummers') ; Title='Drummer' ; Email='peter.behrens@example.net' ; Country='DE' ; Disabled=$false ; Locked=$false ; MustChangePassword=$false ; Department='Music' ; physicalDeliveryOfficeName='Bremen Office' ; telephoneNumber='+49 421 555 0105' ; mobile='+49 1515 555 0106' ; Street='<real street — confirm>' ; City='Bremen' ; PostalCode='28195' ; Company='Example Music (Deutschland) GmbH' ; Manager='Stephan Remmler' ; Description='Drummer and co-founder of Trio' ; AuditLog=@(@{ Timestamp=(Get-Date).AddDays(-40).AddHours(9); Action='Created'; Details='User account created'; By='admin' }) },
```

Then find `$Script:rawDemoGroups=@(` and add **one** matching group row:

```powershell
@{ Name='Trio' ; Description='German new wave band, formed 1980, best known for "Da Da Da"' ; Type='Security' ; Scope='Global' ; ManagedBy='Stephan Remmler' ; Email='trio@example.net' },
```

**Checked, not assumed — why the `OU` array here is only 3 elements**
(`'Deutschland','Bremen','Trio'`), with no Province token even though `sites.csv` has
`Province=Bremen` for `BRE`: `parse_tdf.py`'s own `_user_ou_path()` decodes a 3-element
array as `(Country, City, Band)` and a 4-element one as `(Country, Province, City,
Band)` — it does **not** read `sites.csv` at all for this, it's a self-contained
function with its own `COUNTRY_NORM`/`CONTINENT_MAP` tables. Berlin and Bonn (both
`Province`-blank in `sites.csv`) use the 3-element form; Dresden/Dusseldorf/Munich (which
have a real distinct `Province`) use 4. Bremen is the one German site where the
city and the federal state share a name — using the 3-element form here, matching
Berlin/Bonn, is this document's own judgement call, flagged for a senior to override if
wrong, not asserted as definitely correct.

**If this were the estate's first site in a genuinely new country or continent** —
not the case for Bremen, Germany already exists in `COUNTRY_NORM`/`CONTINENT_MAP` — you
would also need to add entries to those two dictionaries in `parse_tdf.py` itself before
regenerating. Check this every time; don't assume every country is already covered.

### C.2 Regenerate `ad_users.json` and `ad_groups.json`

```bash
python3 benarbejde/parse_tdf.py --section users
python3 benarbejde/parse_tdf.py --section groups
```

**Never run `--section computers`** as part of this or any other change — see the
warning in C.1 and the script's own header. Users/groups are unaffected by that
restriction.

Confirm the new users resolved to a sane OU, by hand, before moving on:

```bash
python3 -c "
import json
for u in json.load(open('benarbejde/ad_users.json')):
    if u['ad_band_ou_name'] == 'Trio':
        print(u['Name'], '->', u['ad_ou'])
"
```

Expect to see all three members resolve to
`OU=Trio,OU=Users,OU=Bremen,OU=Germany,OU=Europe,OU=Sites,DC=jukebox,DC=internal`. If any
of them resolve somewhere unexpected (blank `ad_ou`, wrong country, wrong continent), do
not proceed — go back and check the `.tdf` entry's `OU` array against §C.0/C.1 above
before touching AD at all.

### C.3 Run the harness

```bash
bash at_have_ryggen_fri/run.sh
```

This catches the same class of problem `windows_adschema/30-ad-users.yml`'s own live
run would otherwise surface for the first time against a real DC — duplicate
`SamAccountName`s, group-name collisions with an existing user, and similar. **Fixing
this here, against the data alone, is far cheaper than fixing it live against AD** — see
the real incident history in `docs/INCIDENT-LOG.md` (INC-2026-09-23-ADSCHEMA-TEST) for
exactly how expensive a live-only discovery of this class of bug has been before.

### C.4 Build the AD objects for real

This is a **separate, deliberate action** against a live Domain Controller — not
something that happens automatically from editing a JSON file. Confirm you actually want
to do this now (not just prepare the data) before running it.

```bash
# If you're following straight on from a fresh DC promotion, 40-dc-summary.yml already
# printed the exact command for you — use that one. Otherwise, standalone:
ansible-playbook playbooks/windows_adschema/site.yml -e populate_ad=yes --ask-vault-pass
```

You'll be prompted for the target Domain Controller (any healthy, reachable DC in the
forest — this is additive-only against the whole forest, not scoped to BRE specifically).
This runs, in order: `00-ad-preflight.yml` (the DC prompt) → `10-ad-schema.yml` (creates
the OU skeleton, including BRE's new city OU and Trio's new band OU, additive only) →
`20-ad-groups.yml` (creates the `Trio` security group) → `30-ad-users.yml` (creates the
three user accounts) → `40-ad-computers.yml` (no-op for this change — `ad_computers.json`
wasn't touched).

**This is additive only, and safe to re-run.** Nothing here resets a password, deletes an
object, or touches anything that already exists correctly — confirmed standing behaviour
across this whole module, not a new claim made just for this doc.

---

## Part D — Confirming and checking the subnet

The procedure pulled out as its own section because it applies to *both* Part A (the
site's own `/24`) and, in miniature, to Part B (a single device's octet within an
existing site's `/24`).

### D.1 The rule

The third octet of a new site's `192.168.X.0/24` subnet is loosely derived from the
city's real phone/area code — **not** a rigid, mechanical formula, a judgement call
checked against two hard constraints:

1. **Must be under 255** (it's the third octet of a `/24` — `0`–`255` is the whole usable
   range, and several values near the top are already reserved estate-wide for other
   purposes — don't pick something that happens to collide with a *type* of usage, not
   just a specific site. Check `benarbejde/address_policy.csv` too, not just `sites.csv`.)
2. **Must not already be in use** by another site — check `benarbejde/sites.csv` directly,
   every time, never from memory.

**Confirmed against the real, current `sites.csv` data before writing this down** (not
asserted from a clean formula): this is *inspired by*, not always identical to, the real
area code. Aberdeen's `+44 1224` → octet `224` (exact). Dusseldorf's `+44 211` → octet
`211` (exact). Hull's `+44 1482` → octet `148` (drop the trailing digit). Clydebank and
Glasgow share the real area code `141`, but can't share an octet — Glasgow got the exact
`141`, Clydebank got bumped to `41` (a truncation of the same number) specifically to
avoid the collision. A few older entries don't obviously fit any clean rule at all —
treat those as historical, not as evidence the rule is stricter than it is.

### D.2 The actual steps

1. **Get the city's real area/dial code.** For Bremen, Germany: `0421`.
2. **Generate 2–3 plausible octet candidates from it** — the whole number if it's
   already under 255, otherwise a recognisable truncation (drop the leading digit, drop
   the trailing digit, or both). For `0421` → `421` (too big, over 255, discard outright)
   → `42` (drop trailing `1`) or `21` (drop leading `4`).
3. **Check every candidate against `sites.csv` for a collision**:
   ```bash
   grep -c ",192\.168\.42\.0/24," benarbejde/sites.csv   # 0 = free
   grep -c ",192\.168\.21\.0/24," benarbejde/sites.csv   # 0 = free
   ```
   For this worked example: `124` and `41` (two other plausible derivations of `0421`)
   were already taken (`ABD` and `CLY` respectively) — ruled out immediately. `42` and
   `21` both came back genuinely free.
4. **Present the free candidates to a senior engineer and get an explicit choice before
   writing anything down.** This is not a formality — it's the same standing rule
   Part B §2 states for a single device's octet (`suggest_free_ip.py`'s own output:
   "This is a suggestion, not a decision"), applied at the whole-site level. **Do not
   silently pick one yourself and commit it.**

   For this worked example, both `42` and `21` were presented, and `42` was the
   confirmed choice — that's why Part A above uses `192.168.42.0/24`, not `192.168.21.0/24`
   (which remains free for a future site, noted here rather than left undocumented).

### D.3 What this looks like for a single device, not a whole site

Same shape, smaller scope — covered in full in Part B §2. The tool differs
(`suggest_free_ip.py <SITE>` instead of a manual phone-code derivation, since a device's
octet just needs to be free *within* an already-existing site's subnet, not derived from
anything external), but the governing rule is identical: **surface candidates, let a
senior make the final call, never commit one yourself.**

---

## 2. Full worked-example command sequence, start to finish

Everything above, concatenated into the order you'd actually run it in. Still
illustrative — this was not actually executed to produce this document.

```bash
# Part A — the site
grep -i "^BRE," benarbejde/sites.csv benarbejde/role_codes.csv     # confirm BRE is free
# Part D — subnet (confirm with a senior BEFORE writing the row — done here, result: 42)
grep -c ",192\.168\.42\.0/24," benarbejde/sites.csv
grep -c ",192\.168\.21\.0/24," benarbejde/sites.csv
# ... hand-edit benarbejde/sites.csv, add the BRE row (A.1) ...
python3 at_have_ryggen_fri/check_new_site_boilerplate.py --apply BRE
bash at_have_ryggen_fri/run.sh                                     # fix anything red

# Part C — the band
# ... hand-edit benarbejde/jukebox.example.tdf, add Trio's 3 users + 1 group (C.1) ...
python3 benarbejde/parse_tdf.py --section users
python3 benarbejde/parse_tdf.py --section groups
bash at_have_ryggen_fri/run.sh                                     # fix anything red
ansible-playbook playbooks/windows_adschema/site.yml -e populate_ad=yes --ask-vault-pass

# Commit — one commit per logical unit, not one giant commit for everything
git add benarbejde/sites.csv ansible/configs/inventory/bre.ini \
        ansible/configs/inventory/group_vars/all/site_services.yml \
        benarbejde/begyndelse.json ansible/configs/inventory/salt/pillar/sites.sls \
        docs/network-diagram/*.md bootstrap/web/proxmox/sites.csv \
        bootstrap/web/proxmox/devices.csv benarbejde/devices.csv
git commit -m "Add BRE (Bremen) site + standard boilerplate"

git add benarbejde/jukebox.example.tdf benarbejde/ad_users.json benarbejde/ad_groups.json
git commit -m "Add Trio (Bremen) to AD demo data"
```

---

## 3. A note on devices that are already built when this happens

If a site's boilerplate devices are being added *after* they're already physically
racked and working (not the usual "paper site first" flow Part A assumes), the
sequence differs — see §4, "Phase 2," below: convert each `Planned=yes` placeholder row
into a real, vendor-confirmed row as each device is actually confirmed built, and add
the matching `ad_computers.json` record for anything AD-trackable (switch, WAP, SBC,
badge reader, NAS, ILO/RAC). Routers, firewalls, and Proxmox nodes never get
`ad_computers.json` records (they're not domain-joined); the domain controller gets its
own AD computer object automatically via DC promotion, not through this file at all.

## 4. Phase 2 — as real hardware actually gets built

Everything above only gets the site/device *existing correctly* in the data. As real
equipment is physically installed, for each device: convert its `Planned=yes`
placeholder row (if `--apply`/`--complete` was used) into a real, vendor-confirmed
`devices.csv` row via Part B, and add the matching `ad_computers.json` record for
anything AD-trackable (switch, WAP, SBC, badge reader, NAS, ILO/RAC). RTR/FWL/PVE never
get `ad_computers.json` records (not domain-joined); the domain controller gets its own
AD computer object automatically via DC promotion, not through this file at all. Then
build the actual device via the relevant buildsheet/playbook — see `docs/INDEX.md`'s
Quick Reference table.

---

## 5. Quick-reference checklist

Print this bit out. Tick each box in order.

- [ ] Site code confirmed free (both `sites.csv` and `role_codes.csv`)
- [ ] Subnet octet derived from the city's real area code, candidates checked against
      `sites.csv`, **confirmed with a senior**, not picked alone
- [ ] `sites.csv` row added, `Entity`/`AnsibleRegion`/`Gateway`/`DC`/`FW` copied from a
      real same-country row, not invented
- [ ] `check_new_site_boilerplate.py --apply <SITE>` run
- [ ] Harness green
- [ ] Any non-boilerplate device added via Part B's own procedure, with its own octet
      confirmed the same way
- [ ] Band + members added to `jukebox.example.tdf`, following the existing format
      exactly
- [ ] `parse_tdf.py --section users` and `--section groups` run
- [ ] New users' `ad_ou` spot-checked by hand — resolves where expected, not blank
- [ ] Harness green again
- [ ] `populate_ad=yes` run against a real DC, once you're actually ready to create
      live AD objects (not before)
- [ ] Separate commits for the site/device work and the band/AD work
- [ ] If any device is already physically built, its `Planned=yes` row converted to
      real per §3/§4, and `ad_computers.json` updated to match

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
