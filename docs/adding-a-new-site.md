# Adding a new site to the estate

**Classification:** Internal — Infrastructure
**Doc ID:** OPS-SITE-001

The step-by-step workflow for adding a genuinely new site — before any hardware exists,
a "paper site" — to `benarbejde/sites.csv` and getting it correctly represented
everywhere else. Written 2026-09-24 after Robert asked how PHI/DET (real `sites.csv`
entries with zero equipment anywhere) actually came to exist, and how that should work
going forward without doing it by hand.

This doc covers the part `docs/adding-a-new-device.md` (OPS-DEVICE-001) doesn't — creating
the site itself. Once the site exists, adding *specific* real hardware to it is that other
doc's job, not this one's.

## 1. Add a row to `benarbejde/sites.csv`

```
Site,City,Country,CountryCode,Province,OfficeName,Street,PostalCode,Subnet,Gateway,DC,FW,Landline,Mobile,Timezone,AnsibleRegion,Entity
```

- `Site`: 2-4 uppercase letters, not already in use — check both `sites.csv` and
  `role_codes.csv` (site codes and role codes share no namespace, but a typo that collides
  with a role code will confuse everything downstream).
- `Subnet`: a genuinely free `/24` — check `sites.csv` for the highest allocated third
  octet in the target country/region and pick the next one, or ask Robert for a specific
  block if one's already earmarked.
- `Gateway`/`DC`/`FW`: for a standard site these are almost always `.253`/`.10`/`.253`
  respectively (matching the [Addressing](../README.md#addressing) convention) — copy an
  existing same-region site's row as your starting template rather than typing these from
  scratch.
- `AnsibleRegion`: match an existing site in the same real-world region —
  `uk_site`/`eu_site`/`dk_site`/`de_site`/`us_site`/`ca_site`/`apac_site` cover most cases;
  `cloud_site`/`lb_site` are special (CLD/VRK-adjacent), don't use them for an ordinary new
  site.
- `Entity`: the legal entity this site trades under — copy the exact string from another
  site in the same country (e.g. `Example Music (US) LLC.`), don't invent a new variant.

**Never guess a subnet or gateway is free without checking** — same standing rule as
`adding-a-new-device.md`'s IP-octet guidance. Confirm with Robert before committing.

## 2. Regenerate and get the boilerplate written

Two ways to do this, in increasing order of automation:

**Manual** (same commands as `adding-a-new-device.md` step 4 — inventory `.ini`,
`group_vars`/`begyndelse.json`/Salt pillar, network diagrams). Nothing in `devices.csv`
needs touching yet — every standard boilerplate device (router, firewall, switch, WAP,
SBC, badge reader, NAS, two Proxmox nodes + their BMCs, domain controller) is already
fully predictable from `sites.csv` + `address_policy.csv` alone and renders correctly with
**zero** `devices.csv` rows (confirmed live against `det.ini`).

**Automated** (recommended — this is exactly what removes the human-error risk of typing
out 12 hostname/IP/vendor combinations by hand):

```bash
python3 at_have_ryggen_fri/check_new_site_boilerplate.py --apply <SITE>
```

This writes real `devices.csv` rows for the full boilerplate list, each marked
`Planned=yes` (the same convention already used estate-wide for confirmed-but-not-yet-built
hardware, e.g. ODE's second firewall) — not asserting the hardware is real yet, just
recording what's expected so diagrams and inventory reflect it, and so this same check
stops reporting the site as having *literally nothing* known about it. It then
regenerates every derived artefact (`.ini` files, `group_vars`, diagrams) in the same run,
and syncs the `bootstrap/web/proxmox/` mirror copies. Refuses to run against a site that
isn't in `sites.csv`, is one of the architecturally-special sites (CLD/VRK/FRD), or already
has any real `devices.csv` rows — this is specifically for a genuinely brand-new site, not
a way to bulk-append to one already in progress.

**A partially-built site — already has some real equipment, just not all of it** — needs a
different command:

```bash
python3 at_have_ryggen_fri/check_new_site_boilerplate.py --complete <SITE>
```

Checks every boilerplate Type against what the site already has on record (any real row of
that Type counts, regardless of Number/octet — a firewall sitting at a non-standard Number
still counts as "this site has a firewall"), then writes `Planned=yes` rows for exactly the
missing Types, leaving everything already there untouched. Refuses if the site has zero
existing rows at all (use `--apply` instead) or is architecturally special. Found live
2026-09-24 asking whether an already-started site (FAX) had everything — it didn't (missing
SBC/badge-reader/NAS/both Proxmox+BMC pairs/a real DCS, despite already having a router,
firewall, switch and WAPs).

**Both deliberately do NOT touch `ad_computers.json`.** That file drives real
`New-ADComputer` creation — writing planned/unbuilt hardware into it would try to create
real AD objects for equipment that doesn't exist yet. AD records only get added once
hardware is actually confirmed built (Phase 2, below).

## 3. Run the harness

```bash
bash at_have_ryggen_fri/run.sh
```

Check 44 (`check_new_site_boilerplate.py`) confirms the new site's addressing is sane and
shows its boilerplate. If you used `--apply`, the rest of the harness (freshness checks,
role-code checks, etc.) confirms the regeneration actually landed cleanly. Fix anything it
flags before committing.

## 4. Commit

One commit for the `sites.csv` row plus every file `--apply`/the manual regeneration
touched — same rule as `adding-a-new-device.md` step 8, don't split the source-data edit
from its own regeneration.

## Phase 2 — as real hardware actually gets built

This doc only gets the site *existing correctly*. As real equipment is physically
installed at the site, hand off to `docs/adding-a-new-device.md` for each device: convert
its `Planned=yes` placeholder row (if `--apply` was used) into a real, vendor-confirmed
`devices.csv` row, and add the matching `ad_computers.json` record for anything
AD-trackable (switch, WAP, SBC, badge reader, NAS, ILO/RAC). RTR/FWL/PVE never get
`ad_computers.json` records (not domain-joined); the domain controller gets its own AD
computer object automatically via DC promotion, not through this file at all. Then build
the actual device via the relevant buildsheet/playbook — see `docs/INDEX.md`'s Quick
Reference table.

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
