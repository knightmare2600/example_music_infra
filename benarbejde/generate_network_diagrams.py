#!/usr/bin/env python3

# ==================================================================================================
# Example Music -- New Network diagram generator
#
# Generates the "New Network (current)" mermaid subgraph for each site in sites.csv, from the same
# single source of truth generate_inventory.py uses for the real Ansible inventory (sites.csv +
# devices.csv + address_policy.csv + ad_forest.json) -- not a second, hand-maintained data model.
# Reuses generate_inventory.py's own building blocks (compute_standard_devices_for_site(),
# load_devices(), NON_STANDARD_SITES, NO_STANDARD_ROUTER_SITES, ALWAYS_EXCLUDE_TYPES) rather than
# re-deriving which devices are real -- if those rules change, this picks the change up for free.
#
# Output is inserted into docs/network-diagram/<region>.md (one file per region -- split
# 2026-07-13, see REGION_FILES below and docs/network-diagram.md's own header for why: GitHub's
# mermaid renderer got unreliable with all 51 sites' diagrams on one page) between matching
#   %% GENERATED:NEW-NETWORK:<SITE>:START / :END
# markers by insert_into_docs(). at_have_ryggen_fri's freshness check (check 14) regenerates
# into a scratch dir and diffs against what's committed -- this script is the single place that
# logic lives; the check just calls it and compares.
#
# See docs/network-diagram.md's "Visual Standard" section for the shape/colour/symbol convention
# this implements, and at_have_ryggen_fri/README.md's Backlog section for the overall plan.
# ==================================================================================================

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate_inventory as gi

SITES_CSV = HERE / "sites.csv"
DEVICES_CSV = HERE / "devices.csv"
ADDRESS_POLICY = HERE / "address_policy.csv"
DOCS_DIR = HERE.parent / "docs" / "network-diagram"

# Which region file each site's New Network block lives in -- must match the actual file layout
# under docs/network-diagram/ (split 2026-07-13 from the former single network-diagram.md).
# BRD (legacy alias for BER) and VRK (already inside CLD's diagram) deliberately have no entry --
# neither has its own diagram section anywhere, same as before the split.
# CLD deliberately has no entry either, as of 2026-07-30: Robert replaced its auto-generated New
# Network box with a hand-drawn topology sketch (see docs/network-diagram/cld.md directly) as the
# prototype for an eventual per-site template -- same "no diagram section here" treatment as
# BRD/VRK above, not an oversight.
# ODE/FRD dropped from danmark.md's list the same day, then every remaining site across every
# region file the same way shortly after -- the full rollout, once the pattern had been proven on
# CLD (black-swan)/ODE (regular)/VRK+FRD (NON_STANDARD_SITES). All 53 sites now render via
# render_topology_block()/TOPOLOGY_SITES below instead of this dict -- every list here is
# deliberately empty, kept only so a region file can still be found if a topology-only site's
# devices ever need tracing back to which file its "Old Network" box lives in.
REGION_FILES = {
  "cld.md": [],
  "scotland.md": [],
  "england.md": [],
  "danmark.md": [],
  "deutschland.md": [],
  "sverige.md": [],
  "norge.md": [],
  "nederland.md": [],
  "italia.md": [],
  "osterreich.md": [],
  "lebanon.md": [],
  "canada.md": [],
  "united-states.md": [],
  "australia.md": [],
  "new-zealand.md": [],
}
SITE_TO_REGION_FILE = {site: fname for fname, sites in REGION_FILES.items() for site in sites}

# All known device Type codes, for reference/validation only -- as of 2026-07-13 every node gets
# a single uniform shape (node_box() below) and an emoji does the "what is this" job instead of
# shape geometry (Robert's call: the 5-shape system was too visually heavy -- "more shapes than
# the Ministry of Sound" -- across a 50+ node diagram). CURVEBALL_TYPES kept only to distinguish
# "genuinely no symbol agreed yet" (falls back to PLACEHOLDER_SYMBOL) from "not a device this
# generator ever emits" (which would be a real bug, not a missing symbol).
CURVEBALL_TYPES = {'VND', 'MUS', 'PAY', 'COF', 'TEA', 'PMP', 'CLK', 'MIC', 'RAD', 'MOO', 'LIN', 'FCL', 'AST', 'TTY', 'BUS', 'CAR', 'JET', 'TRK', 'DON'}

# Per-type Unicode symbols. "Feel" over "official" -- Robert's own framing, 2026-07-13: these are
# not meant to be literal/precise device iconography, just evocative enough to scan quickly. Full
# reasoning and a human-browsable legend live in docs/emojis/README.md -- both trace back to the
# same source, so they can't drift.
#
# 2026-07-20: loaded from benarbejde/role_codes.csv's Code/Emoji columns instead of a hardcoded
# dict here -- this used to be a second, hand-maintained copy of the same data
# address_policy.json's connection_types and docs/emojis/README.md each also carried their own
# version of (found while cleaning up the retired PRV convention: three places to keep in sync by
# hand is exactly the kind of drift this repo's own harness exists to catch). role_codes.csv is
# now the single source of truth for "what does this 3-letter code mean" across all three.
ROLE_CODES_CSV = HERE / "role_codes.csv"
PLACEHOLDER_SYMBOL = "❓"  # ❓ -- pending sign-off, do not guess a replacement

def _load_type_symbols():
  with open(ROLE_CODES_CSV, newline="", encoding="utf-8") as f:
    return {row["Code"]: row["Emoji"] for row in csv.DictReader(f)}

TYPE_SYMBOLS = _load_type_symbols()

# Code -> singular display name, same role_codes.csv source as TYPE_SYMBOLS -- used only for the
# "Other" bucket's grouped-count labels (e.g. "5x Cars"), added 2026-07-30 alongside that feature.
def _load_type_names():
  with open(ROLE_CODES_CSV, newline="", encoding="utf-8") as f:
    return {row["Code"]: row["Name"] for row in csv.DictReader(f)}

TYPE_NAMES = _load_type_names()

# A handful of role_codes.csv Names don't naively pluralize well (BUS's "Tour bus" -> "Tour buss"
# with a bare +s) or read better shortened for a compact diagram label (PHN's full "Office/desk
# phone" -> "Office phones", matching Robert's own hand-built FAL prototype exactly). Only override
# what's actually been hit -- not a guess at every possible irregular plural in role_codes.csv.
TOPOLOGY_PLURAL_OVERRIDES = {"BUS": "Tour buses", "PHN": "Office phones"}


def _pluralize_type_name(name: str) -> str:
  # Several role_codes.csv Names carry a trailing " (...)" qualifier (NAS's "Storage (NAS/SAN --
  # e.g. TrueNAS)", DCR's "Domain controller (legacy naming)"...) -- pluralizing the whole string
  # naively tacks the "s" on after the closing paren ("...naming)s"). Split it off, pluralize the
  # real word, reattach.
  m = re.match(r'^(.+?)(\s*\([^)]*\))?$', name)
  base, suffix = m.group(1), m.group(2) or ""
  if base.endswith(("s", "x", "z", "ch", "sh")):
    base += "es"
  elif len(base) > 1 and base.endswith("y") and base[-2] not in "aeiou":
    base = base[:-1] + "ies"
  else:
    base += "s"
  return base + suffix

# Terms that must never appear in a New Network label -- FSMO roles and health/low-disk-space
# annotations stay old-infra-only (docs/network-inventory.md), by data-source construction (neither
# sites.csv nor devices.csv carries this information at all) but enforced here too as a defensive
# backstop, not just a doc convention that could rot.
BANNED_TERMS = re.compile(r'FSMO|DFSR|low disk|OOS \d|EOL\b|UNHEALTHY|out of sync', re.IGNORECASE)


def node_box(node_id: str, label: str) -> str:
  """One uniform shape for every node -- a plain rounded rect. The emoji in the label carries the
  "what kind of device is this" job now, not shape geometry (see TYPE_SYMBOLS above)."""
  return f'{node_id}["{label}"]'


def short_note(notes: str) -> str:
  """First clause of a devices.csv Notes field -- these are often a full sentence or more of
  free-text context (e.g. the CLD/FRD PBX row), not diagram-label length. Split on the first
  ' -- ', '. ', or ' — ' (em dash), whichever comes first; cap at 60 chars either way.
  Em dash added 2026-07-30 -- found live during the topology rollout: FAL's real NAS Notes
  ("Site NAS/SAN — EXANASFAL001 (.19 standard slot) — installed...") uses em dashes as its
  actual clause separator, which this function didn't recognise, so it fell through to a hard
  60-char truncation instead of a clean first-clause cut -- a pre-existing bug, not new to the
  topology renderer (the same garbled label was already sitting in the committed flat New
  Network box for FAL/TOR before this fix)."""
  notes = (notes or "").strip()
  if not notes:
    return ""
  cut = len(notes)
  for sep in (" -- ", ". ", " — "):
    idx = notes.find(sep)
    if idx != -1:
      cut = min(cut, idx)
  short = notes[:cut].strip()
  if len(short) > 60:
    short = short[:57].rstrip() + "..."
  return short


def build_site_devices(site: str, net, devices_by_site: dict):
  """Every confirmed-real device for one site -- standard-slot + devices.csv exceptions hostnamed
  here, PLUS any device hostnamed elsewhere whose SubnetSite points at this site (physically here
  even though it's named/managed under another site -- see the CLD PBX / FRD Havn case). Returns a
  list of dicts: hostname, type, octet, label, subnet_site (site this is physically on, if not
  itself), is_foreign (True if hostnamed under a DIFFERENT site but physically here).
  """
  out = []

  # Which Types this site already has a real devices.csv row for -- passed to
  # compute_standard_devices_for_site() so it doesn't synthesize a generic "Standard SWI slot 1"
  # placeholder that would duplicate/shadow a real, more-informative devices.csv SWI entry (see
  # that function's own docstring; matters for SWI today, 2026-07-14). real_octets is the
  # per-instance version (added 2026-07-30 alongside SWI's move to DNS_MULTI_ALL_INSTANCES) --
  # without it, a site with a real SWI2 row would lose its still-synthesized SWI1 too.
  real_types = {dev["type"] for dev in devices_by_site.get(site, [])}
  real_octets = {}
  for dev in devices_by_site.get(site, []):
    if dev["octet"] is not None:
      real_octets.setdefault(dev["type"], set()).add(int(dev["octet"]))

  if site not in gi.NON_STANDARD_SITES:
    for d in gi.compute_standard_devices_for_site(
        site, net, real_device_types=real_types, real_device_octets=real_octets):
      dtype = re.match(r'EXA([A-Z]{3})', d["Hostname"]).group(1)
      if dtype == 'RTR' and site in gi.NO_STANDARD_ROUTER_SITES:
        continue  # documentation-only placeholder for DNS purposes, not a real device here
      if d.get("SubnetSite"):
        # FWL1's bare hostname now DNS-synthesizes at the VRK/provisioning-network address
        # (Robert, 2026-07-26 -- matches Ansible's own inventory convention for this
        # hostname), a second, DNS-only entry alongside the real -LAN one for the same
        # physical device. One box per physical firewall on a site diagram, not two --
        # skip anything the generator marked as living on a different subnet than this
        # site's own (the -LAN entry, with no SubnetSite key, is what actually gets drawn).
        continue
      out.append({
        # -LAN suffix is a DNS-only disambiguator (see above) -- strip it for the diagram
        # label, this is still just "the firewall", not a second device. Same for the Notes
        # text: the full "this is what the bare hostname meant before..." explanation belongs
        # in the DNS zone file's comment, not a compact diagram label.
        "hostname": d["Hostname"].removesuffix("-LAN"), "type": dtype, "octet": d["HostOctet"],
        "label_extra": (
          "LAN face" if d["Hostname"].endswith("-LAN")
          else d["Notes"].replace("Standard ", "").replace(" slot", "")
        ),
        "subnet_site": None, "is_foreign": False,
      })

  for dev in devices_by_site.get(site, []):
    if dev.get("subnet_site"):
      continue  # hostnamed here but physically elsewhere -- belongs in ITS subnet_site's box, not this one
    out.append({
      "hostname": dev["hostname"], "type": dev["type"], "octet": dev["octet"],
      "label_extra": short_note(dev["notes"]), "subnet_site": None, "is_foreign": False,
    })

  # VRK has no diagram section of its own (it's the vRACK/provisioning layer, not a physical
  # site -- see docs/network-diagram/cld.md's own header) -- its real devices.csv rows
  # (EXADNSVRK001, its TMP provisioning server, EXAFWLVRK001) fold into CLD's page, the same way
  # the old hand-drawn diagram always treated them as one combined view. Confirmed 2026-07-14: VRK has
  # zero entries in benarbejde/ad_computers.json (the real pre-project AD export), same as CLD
  # itself -- neither is legacy, both are purely current infrastructure.
  if site == "CLD":
    for dev in devices_by_site.get("VRK", []):
      if dev.get("subnet_site"):
        continue
      out.append({
        "hostname": dev["hostname"], "type": dev["type"], "octet": dev["octet"],
        "label_extra": short_note(dev["notes"]) + " (VRK)",
        "subnet_site": None, "is_foreign": False,
      })

  for other_site, devs in devices_by_site.items():
    if other_site == site:
      continue
    for dev in devs:
      if dev.get("subnet_site") == site:
        out.append({
          "hostname": dev["hostname"], "type": dev["type"], "octet": dev["octet"],
          "label_extra": short_note(dev["notes"]) + f" (hostnamed under {other_site})",
          "subnet_site": site, "is_foreign": True,
        })

  return out


def render_new_network_block(site: str, sites_row: dict, devices_by_site: dict) -> str:
  """Returns the New Network subgraph as mermaid text (no outer graph/fence -- caller embeds this
  alongside the Old Network subgraph inside one shared ```mermaid block, or on its own for a
  new-build site with no Old Network counterpart)."""
  try:
    net = gi.validate_cidr(sites_row["Subnet"])
  except ValueError:
    net = None

  devices = build_site_devices(site, net, devices_by_site) if net is not None else []
  # Same exclusion render_topology_block() applies via TOPOLOGY_EXCLUDE_TYPES (defined further
  # down this file) -- DCR rows carry real historical FSMO/health-status detail that's fine for
  # the Old Network but must never reach a *current*-infrastructure box. This path predates that
  # exclusion (added 2026-07-31 for the topology renderer only) -- DCR rows added here 2026-08-03
  # for the Old Network's own DCS->DCR rename hit this gap immediately (BANNED_TERMS correctly
  # crashed on KGE's "27 days out of sync, disk space low" DCR row before this fix).
  devices = [d for d in devices if d["type"] not in TOPOLOGY_EXCLUDE_TYPES]

  lines = [f'    subgraph NEW_{site} ["\U0001F195 New Network (current)"]']
  seen_ids = {}
  for dev in devices:
    if dev["type"] == "TMP":
      # Bootstrap-only provisioning server (VRK/FRD only) -- deliberately
      # never gets a formal EXA<ROLE><SITE><NNN> hostname (2026-07-21), unlike
      # every other device here. No hostname part at all -- label_extra (its
      # notes, e.g. "Provisioning server", plus " (VRK)" when folded into
      # CLD's page below) and the .octet suffix already say enough; showing
      # a computed IP here would need this device's own site's subnet, not
      # necessarily the one `net` (this function's own site) refers to.
      parts = []
    else:
      parts = [dev["hostname"]]
    if dev["label_extra"]:
      parts.append(dev["label_extra"])
    if dev["octet"]:
      parts.append(f'.{dev["octet"]}')
    label = " · ".join(parts)  # single line -- · separator, not <br/> -- see node_box()
    if BANNED_TERMS.search(label):
      raise ValueError(f"Banned FSMO/health term found in New Network label for {site}: {label!r}")

    base_id = f"N_{dev['type']}"
    seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
    node_id = base_id if seen_ids[base_id] == 1 else f"{base_id}{seen_ids[base_id]}"

    if dev["type"] in TYPE_SYMBOLS:
      symbol = TYPE_SYMBOLS[dev["type"]]
    elif dev["type"] in CURVEBALL_TYPES:
      symbol = PLACEHOLDER_SYMBOL  # curveball type with no agreed symbol yet (e.g. MUS) -- ask, don't guess
    else:
      raise ValueError(f"Device type {dev['type']!r} has no entry in TYPE_SYMBOLS (node {node_id}, site {site})")
    display_label = f"{symbol} {label}".strip()
    lines.append(f'      {node_box(node_id, display_label)}')

  if not devices:
    lines.append('      N_EMPTY["No confirmed devices in sites.csv/devices.csv yet"]')

  lines.append('    end')
  lines.append(f'    style NEW_{site} fill:#E69F00,stroke:#D55E00,color:#000000')
  return "\n".join(lines)


def load_all(sites_csv=SITES_CSV, devices_csv=DEVICES_CSV, policy=ADDRESS_POLICY):
  gi.load_address_policy(policy)
  sites = {r["Site"]: r for r in csv.DictReader(open(sites_csv))}
  devices_by_site, _stats = gi.load_devices(devices_csv)
  return sites, devices_by_site


def generate_all(sites_csv=SITES_CSV, devices_csv=DEVICES_CSV, policy=ADDRESS_POLICY):
  """Returns {site: new_network_block_text} for every site in sites.csv."""
  sites, devices_by_site = load_all(sites_csv, devices_csv, policy)
  return {site: render_new_network_block(site, row, devices_by_site) for site, row in sites.items()}


# ==================================================================================================
# Topology sketch generator -- 2026-07-30, prototyped by hand for CLD/ODE/VRK/FRD (see those
# files' git history the same day) before being turned into this generalised version. Produces the
# right-angle, single-column-per-branch, black/white style built out in that hand-authored round,
# from the same real+planned device data every other generator function here already uses -- not a
# second copy of "what devices exist."
# ==================================================================================================

# Type -> its topology parent Type. Keyed off the device TYPE, not the site, so CLD "looking
# different" from ODE falls out naturally from which types are present, not from special-casing
# CLD in code (confirmed against both real builds before writing this down). Anything not listed
# here falls into the "Other" bucket -- a floating, disconnected two-column group, not parented
# under anything (see render_topology_block()'s own "Other" bucket section). RTR itself has no
# entry -- it's the root, parented under the site's own top-level cloud node instead.
TOPOLOGY_PARENT_TYPE = {
  "SWI": "RTR", "BMC": "RTR", "PVE": "RTR",
  "NAS": "SWI", "RDR": "SWI", "MUS": "SWI", "WAP": "SWI",
  "DCS": "PVE", "SBC": "PVE", "PBX": "PVE", "ANS": "PVE", "RUD": "PVE",
  "SLT": "PVE", "SVR": "PVE", "UFC": "PVE", "FWL": "PVE",
}

# Canonical child order within each branch -- matches the order Robert confirmed for CLD/ODE.
# Anything of a listed parent-Type not named here (a type this template hasn't seen yet) is
# appended after, in devices.csv row order -- never dropped, just unordered relative to these.
SWI_CHILD_ORDER = ["NAS", "RDR", "MUS", "WAP"]
PVE_CHILD_ORDER = ["ANS", "DCS", "RUD", "SVR", "SLT", "PBX", "SBC", "UFC", "FWL"]

# Real devices.csv rows that still shouldn't appear on a *current-state* topology diagram --
# confirmed dormant, not a data error (see the "RUD" entry's own role_codes.csv row, and
# project_rudder_dormant_docs_correction in memory: Robert confirmed 2026-07-30 the Rudder server
# is code-only/unused on the live network). Same shape as generate_inventory.py's own
# ALWAYS_EXCLUDE_TYPES -- a static set checked every run, so a future regeneration can't silently
# reintroduce it; if a type's dormant status ever changes, this line is the one place to update.
#
# DCR added 2026-07-31 -- Robert: "legacy devices have seeped into the new diagrams which isn't
# suppsoed [sic] ot happen, we are deploying new hypervisors, new DCS new SBCs etc." Every real
# DCR row in devices.csv today is genuinely legacy/broken, not just a differently-coded current DC:
# EDI's two ("DC secondary needs rebuild", "DECOMMISSION PENDING") and TOR's one ("Undocumented
# legacy AD install found on site, no-one on record knew it existed"). role_codes.csv's own DCR
# row claims "devices.csv rows using DCR are typos and treated as DCS" -- that was never actually
# implemented (DCR was never in TOPOLOGY_PARENT_TYPE either, it fell into the "Other" bucket by
# omission, not design) and doesn't match what's actually in the data. Flagged to Robert, not
# silently reinterpreted -- if a genuinely-current DC is ever mistyped as DCR instead of DCS, this
# exclusion would hide it too; the real fix for that case is correcting the devices.csv row's Type,
# not carving out an exception here.
TOPOLOGY_EXCLUDE_TYPES = {"RUD", "DCR"}

TOPOLOGY_STYLE = "fill:#000000,stroke:#FFFFFF,color:#FFFFFF"


def load_planned_devices(site: str, devices_csv=DEVICES_CSV):
  """Planned=yes rows for one site, straight from devices.csv -- deliberately NOT via
  gi.load_devices() (which excludes them for every real consumer, see that function's own
  comment). Same dict shape as build_site_devices()'s entries, plus "planned": True, so both can
  feed the same rendering code without the renderer needing two different shapes to handle."""
  out = []
  with open(devices_csv, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
      if r["Site"].strip() != site:
        continue
      if (r.get("Planned") or "").strip().lower() not in ("yes", "y", "true", "1"):
        continue
      dtype = r["Type"].strip().upper()
      try:
        number = int(r["Number"])
      except (KeyError, ValueError):
        number = 1
      out.append({
        "hostname": gi.build_hostname(dtype, site, number),
        "type": dtype, "octet": r["HostOctet"].strip(),
        # "{Type} {N}" -- matches the clean "FWL 1"/"BMC 1" label real synthesized devices get
        # (build_site_devices() turns "Standard FWL slot 1" into the same shape), rather than
        # surfacing this row's own free-text Notes (would show "Not yet built" as the label).
        "label_extra": f"{dtype} {number}",
        "subnet_site": None, "is_foreign": False, "planned": True,
      })
  return out


def _topology_symbol(dtype: str) -> str:
  if dtype in TYPE_SYMBOLS:
    return TYPE_SYMBOLS[dtype]
  if dtype in CURVEBALL_TYPES:
    return PLACEHOLDER_SYMBOL
  raise ValueError(f"Device type {dtype!r} has no entry in TYPE_SYMBOLS")


def _octet_int(dev: dict):
  """dev['octet'] is a string for standard-slot-synthesized entries (build_site_devices() copies
  compute_standard_devices_for_site()'s HostOctet straight through) but an int for devices.csv-
  exception entries (gi.load_devices() parses HostOctet itself) -- same inconsistency already
  present in the data build_site_devices() returns, not introduced here. None if absent/blank."""
  octet = dev.get("octet")
  if octet is None or octet == "":
    return None
  return int(octet) if str(octet).isdigit() else None


def _title_case_preserve_acronyms(text: str) -> str:
  """Capitalise each word, leaving already-uppercase words (acronyms: CCTV, HID, NTP...) and
  alphanumeric ones (VT320) untouched -- str.title()/str.capitalize() would mangle 'CCTV' into
  'Cctv'."""
  def cap_word(w):
    if w.isupper() or any(c.isdigit() for c in w):
      return w
    return w[:1].upper() + w[1:]
  return " ".join(cap_word(w) for w in text.split())


def _format_ip_ranges(net, octets: list) -> str:
  """Full IP for the first octet, then just the trailing octet(s)/range(s) for the rest -- e.g.
  four cameras at .70-.73 on a /24 -> '192.168.76.70-73', not the ambiguous bare '.70-.73'
  (Robert, 2026-07-31: 'omitted the subnet, which is a big no no') or the verbose repeated-prefix
  '192.168.76.70-192.168.76.73'."""
  ranges = _compress_ranges(octets)
  base = str(gi.offset_ip(net, ranges[0][0])).rsplit(".", 1)[0]
  parts = [f"{a}" if a == b else f"{a}-{b}" for a, b in ranges]
  return f"{base}.{','.join(parts)}"


def _topology_label(dev: dict, net) -> str:
  """Three-line label (Robert, 2026-07-31: single-line boxes read "crowded") -- hostname (with
  the emoji) on line 1, description on line 2 (title-cased, acronyms preserved), full IP (or "No
  IP Address") on line 3. <br/> is mermaid's own line-break syntax inside a node label. Full IPs
  only, never a bare octet -- ambiguous about which subnet, flagged as a real problem more than
  once this session."""
  symbol = _topology_symbol(dev["type"])
  hostname_line = f"{symbol} {dev['hostname']}" if dev["type"] != "TMP" else symbol
  lines = [hostname_line]
  if dev.get("label_extra"):
    lines.append(_title_case_preserve_acronyms(dev["label_extra"]))
  octet_int = _octet_int(dev)
  if octet_int is not None and net is not None:
    ip_line = gi.offset_ip(net, octet_int)
  else:
    ip_line = "No IP Address"
  if dev.get("planned"):
    ip_line += " — planned"
  lines.append(ip_line)
  label = "<br/>".join(lines)
  if BANNED_TERMS.search(label):
    raise ValueError(f"Banned FSMO/health term found in topology label: {label!r}")
  return label


def _compress_ranges(values: list) -> list:
  """[1, 2, 3, 6, 7] -> [(1, 3), (6, 7)]. Caller formats each (start, end) pair -- hostname
  instance numbers need zero-padding (002-005), IP octets don't (.63-.66), so the padding choice
  isn't baked in here."""
  vals = sorted(set(values))
  if not vals:
    return []
  ranges = []
  start = prev = vals[0]
  for v in vals[1:]:
    if v == prev + 1:
      prev = v
      continue
    ranges.append((start, prev))
    start = prev = v
  ranges.append((start, prev))
  return ranges


def _topology_other_group_label(dtype: str, group: list, net) -> str:
  """Grouped label for 2+ real devices.csv rows of the same 'Other' bucket type -- one three-line
  box with a count (hostname range / '4 x CCTV Cameras' / full-IP range) instead of one box per
  real row. Ports Robert's hand-built FAL prototype (docs/network-diagram/scotland.md, 2026-07-30)
  into the generator, then the 2026-07-31 three-line/full-IP-range style pass (the bare-octet
  ".70-.73" this originally produced was the "omitted the subnet" bug Robert flagged)."""
  symbol = _topology_symbol(dtype)
  name = TOPOLOGY_PLURAL_OVERRIDES.get(dtype) or _pluralize_type_name(TYPE_NAMES.get(dtype, dtype))
  # Number isn't a field build_site_devices() hands back (only hostname/type/octet/label_extra/
  # subnet_site/is_foreign) -- parsed back out of the hostname's own EXA<TYPE><SITE><NNN> trailing
  # digits rather than threading a new field through every caller for this one label.
  numbers = [int(re.search(r'(\d+)$', d["hostname"]).group(1)) for d in group]
  hostname_prefix = re.sub(r'\d+$', '', group[0]["hostname"])
  num_str = ",".join(
    f"{a:03d}" if a == b else f"{a:03d}-{b:03d}" for a, b in _compress_ranges(numbers)
  )
  octets = [o for o in (_octet_int(d) for d in group) if o is not None]
  if octets and net is not None:
    ip_line = _format_ip_ranges(net, octets)
  else:
    ip_line = "No IP Address"
  lines = [
    f"{symbol} {hostname_prefix}{num_str}",
    f"{len(group)} x {_title_case_preserve_acronyms(name)}",
    ip_line,
  ]
  label = "<br/>".join(lines)
  if BANNED_TERMS.search(label):
    raise ValueError(f"Banned FSMO/health term found in topology label: {label!r}")
  return label


def _first_instance(devices: list, dtype: str):
  """The device this type's children attach to -- always the lowest-octet real instance (PVE1,
  not PVE2; SWI1, not SWI2/3), matching every hand-built example so far, none of which ever hung
  a service off a *second* PVE/SWI/BMC instance."""
  candidates = [d for d in devices if d["type"] == dtype]
  if not candidates:
    return None
  return min(candidates, key=lambda d: _octet_int(d) if _octet_int(d) is not None else 999)


def _drop_unbuilt_extra_fwl(devices: list, devices_by_site: dict, site: str) -> list:
  """FWL is the one type where BOTH standard slots (FWL1 .253, FWL2 .254) get synthesized for
  every site unconditionally (ROLE_OFFSETS, not the DNS_MULTI_FIRST_INSTANCE_ONLY gate everything
  else uses) -- a permanent address reservation, not a signal a second unit is actually racked.
  Confirmed 2026-07-30 against ODE: build_site_devices() handed back a real-looking FWL2 entry
  Robert had already told us doesn't exist yet, which then collided with the deliberately-added
  Planned=yes row for the same address. Keep FWL1 always; drop any FWL instance beyond it unless
  it's backed by an actual devices.csv row for this site (real hardware) -- the Planned mechanism
  is what puts it back for sites where Robert's confirmed it's coming."""
  real_hostnames = {d["hostname"] for d in devices_by_site.get(site, [])}
  fwls = sorted(
    (d for d in devices if d["type"] == "FWL"),
    key=lambda d: _octet_int(d) if _octet_int(d) is not None else 999,
  )
  keep = set()
  for i, d in enumerate(fwls):
    if i == 0 or d["hostname"] in real_hostnames:
      keep.add(id(d))
  return [d for d in devices if d["type"] != "FWL" or id(d) in keep]


def render_topology_block(site: str, sites_row: dict, devices_by_site: dict) -> str:
  """The hand-drawn-style topology sketch, generalised. Returns mermaid text (graph TD onward, no
  outer fence -- caller embeds it same as render_new_network_block())."""
  try:
    net = gi.validate_cidr(sites_row["Subnet"])
  except ValueError:
    net = None

  real = build_site_devices(site, net, devices_by_site) if net is not None else []
  # build_site_devices() folds VRK's own real devices into CLD's list (its "(VRK)" suffix is the
  # only marker) -- fine for the old octet-only box, but their real IPs are on VRK's own subnet
  # (192.168.139.x), not CLD's, and this renderer computes full IPs from CLD's `net`. Confirmed
  # live 2026-07-30: without this filter EXADNSVRK001 renders as "192.168.69.8", a wrong address.
  # VRK has its own dedicated topology diagram now (docs/network-diagram/vrk.md) -- matches what
  # was actually hand-built and approved for CLD, which never included these either.
  real = [d for d in real if not d.get("label_extra", "").endswith(" (VRK)")]
  real = [d for d in real if d["type"] not in TOPOLOGY_EXCLUDE_TYPES]
  real = _drop_unbuilt_extra_fwl(real, devices_by_site, site)
  planned = load_planned_devices(site)
  all_devices = real + planned

  node_ids = {}
  seen_ids = {}
  def node_id_for(dev):
    key = (dev["type"], dev["hostname"])
    if key in node_ids:
      return node_ids[key]
    base = f"T_{dev['type']}"
    seen_ids[base] = seen_ids.get(base, 0) + 1
    nid = base if seen_ids[base] == 1 else f"{base}{seen_ids[base]}"
    node_ids[key] = nid
    return nid

  lines = ["%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%", "graph TD"]
  style_lines = []

  def emit_node(nid, dev, label_net):
    lines.append(f'    {nid}["{_topology_label(dev, label_net)}"]')
    style_lines.append(f'    style {nid} {TOPOLOGY_STYLE}')

  def emit_chain(nids):
    if len(nids) > 1:
      lines.append("    " + " --> ".join(nids))

  # -- Special case: VRK/FRD have no RTR/SWI/BMC/PVE hierarchy at all, just whatever real (+
  # planned) devices exist, chained flat under a single self-labelled network node. --
  if site in gi.NON_STANDARD_SITES:
    root_id = f"T_{site}"
    site_label = "vRACK" if site == "VRK" else sites_row.get("City", site)
    root_dev_label = f"☁️ {site} — {site_label} network fabric, {sites_row['Subnet']}"
    lines.append(f'    {root_id}["{root_dev_label}"]')
    style_lines.append(f'    style {root_id} {TOPOLOGY_STYLE}')
    chain = [root_id]
    for dev in all_devices:
      nid = node_id_for(dev)
      emit_node(nid, dev, net)
      chain.append(nid)
    emit_chain(chain)
    lines.extend(style_lines)
    return "\n".join(lines)

  # -- Regular/black-swan sites: VRK cloud -> RTR -> {SWI-branch, BMC-branch, PVE-branch...} --
  vrk_id = "T_VRK"
  lines.append(f'    {vrk_id}["☁️ VRK — vRACK, 192.168.139.0/24"]')
  style_lines.append(f'    style {vrk_id} {TOPOLOGY_STYLE}')

  rtr = _first_instance(all_devices, "RTR")
  if rtr is None and net is not None:
    # build_site_devices() drops RTR entirely for NO_STANDARD_ROUTER_SITES (CLD/FRD) -- "not a
    # real device, documentation-only" for the flat New Network box's purposes. Robert's own CLD
    # sketch put EXARTRCLD001 at the top of the topology anyway (the structural anchor point,
    # regardless of whether it's "real" in the strict devices.csv sense) -- synthesize it here,
    # topology-view only, matching that confirmed precedent rather than silently dropping it.
    rtr = {
      "hostname": gi.build_hostname("RTR", site, 1), "type": "RTR",
      "octet": str(gi.OFFSETS_SINGLE["RTR"]), "label_extra": "RTR 1",
      "subnet_site": None, "is_foreign": False,
    }
    all_devices = [rtr] + all_devices
  if rtr is None:
    lines.extend(style_lines)
    return "\n".join(lines)
  rtr_id = node_id_for(rtr)
  emit_node(rtr_id, rtr, net)
  lines.append(f'    {vrk_id} --> {rtr_id}')

  hub_devices = [d for d in all_devices if TOPOLOGY_PARENT_TYPE.get(d["type"]) == "RTR"]
  for dev in hub_devices:
    nid = node_id_for(dev)
    emit_node(nid, dev, net)
    lines.append(f'    {rtr_id} --> {nid}')

  # SWI branch: NAS/RDR/MUS/WAP, in canonical order, chained under SWI1 specifically.
  swi1 = _first_instance(all_devices, "SWI")
  if swi1:
    branch = [d for d in all_devices if TOPOLOGY_PARENT_TYPE.get(d["type"]) == "SWI"]
    branch.sort(key=lambda d: SWI_CHILD_ORDER.index(d["type"]) if d["type"] in SWI_CHILD_ORDER else 99)
    chain = [node_id_for(swi1)]
    for dev in branch:
      nid = node_id_for(dev)
      emit_node(nid, dev, net)
      chain.append(nid)
    emit_chain(chain)

  # PVE branch: services/VMs, in canonical order, chained under PVE1 specifically.
  pve1 = _first_instance(all_devices, "PVE")
  if pve1:
    branch = [d for d in all_devices if TOPOLOGY_PARENT_TYPE.get(d["type"]) == "PVE"]
    branch.sort(key=lambda d: PVE_CHILD_ORDER.index(d["type"]) if d["type"] in PVE_CHILD_ORDER else 99)
    chain = [node_id_for(pve1)]
    for dev in branch:
      nid = node_id_for(dev)
      emit_node(nid, dev, net)
      chain.append(nid)
    emit_chain(chain)

  # "Other" bucket: anything with no TOPOLOGY_PARENT_TYPE entry -- curveball/novelty devices and
  # endpoints with no defined place in the RTR/SWI/PVE hierarchy. Floats as its own disconnected
  # group (2026-07-30, Robert: "these random devices can just be 'floating'" -- no implied parent
  # relationship to BMC or anything else; an earlier version chained it under BMC1, which is what
  # this replaced). One box per TYPE, not per real devices.csv row -- FAL alone has 46 of these
  # (5x cars, 5x trucks, 5x jets...), grouped with a count in the label (e.g. "5x Cars") to stay
  # readable, matching Robert's own hand-built FAL prototype (scotland.md) which this generalises.
  # Laid out in two columns (alternating by first-seen type order), each column its own simple
  # top-to-bottom chain -- no cross-column edges: an earlier attempt used invisible ~~~ rank-hint
  # edges between corresponding rows to align the columns, which Robert found rendered as a
  # diagonal cascade/waterfall instead of a clean grid -- removed, two independent chains only.
  other = [d for d in all_devices if d["type"] not in TOPOLOGY_PARENT_TYPE and d["type"] != "RTR"]
  if other:
    groups = {}
    for dev in other:
      groups.setdefault(dev["type"], []).append(dev)

    left, right = [], []
    for i, (dtype, group) in enumerate(groups.items()):
      if len(group) == 1:
        nid = node_id_for(group[0])
        emit_node(nid, group[0], net)
      else:
        nid = f"T_OTH_{dtype}"
        lines.append(f'    {nid}["{_topology_other_group_label(dtype, group, net)}"]')
        style_lines.append(f'    style {nid} {TOPOLOGY_STYLE}')
      (left if i % 2 == 0 else right).append(nid)

    emit_chain(left)
    emit_chain(right)

  lines.extend(style_lines)
  return "\n".join(lines)


# Every site is on the topology style as of 2026-07-30 -- CLD (black-swan)/ODE (regular)/
# VRK+FRD (NON_STANDARD_SITES) proved the pattern by hand first, then the remaining 48 rolled out
# together in one pass. CLD/VRK keep their own standalone file; every other site's block lives in
# its existing shared region file (see each file's own git history the same day for the full
# restructuring). Kept as an explicit dict (not "every REGION_FILES site") so a site can be
# reverted to the old flat-box style individually without touching the others, if that's ever
# needed.
TOPOLOGY_SITES = {
  "CLD": "cld.md", "VRK": "vrk.md", "FRD": "danmark.md", "ODE": "danmark.md",
  "FAL": "scotland.md",
  "EDI": "scotland.md",
  "GLA": "scotland.md",
  "CLY": "scotland.md",
  "DUN": "scotland.md",
  "PER": "scotland.md",
  "ABD": "scotland.md",
  "LND": "england.md",
  "BIR": "england.md",
  "MCR": "england.md",
  "LIV": "england.md",
  "NEW": "england.md",
  "SHE": "england.md",
  "HAL": "england.md",
  "HUL": "england.md",
  "COV": "england.md",
  "CPH": "danmark.md",
  "KGE": "danmark.md",
  "FAX": "danmark.md",
  "KOR": "danmark.md",
  "AAR": "danmark.md",
  "FRE": "danmark.md",
  "NYB": "danmark.md",
  "BON": "deutschland.md",
  "BER": "deutschland.md",
  "MUN": "deutschland.md",
  "DRS": "deutschland.md",
  "DUS": "deutschland.md",
  "GOT": "sverige.md",
  "OSL": "norge.md",
  "AMS": "nederland.md",
  "MIL": "italia.md",
  "VIE": "osterreich.md",
  "BRT": "lebanon.md",
  "BRK": "canada.md",
  "TOR": "canada.md",
  "MTL": "canada.md",
  "KNG": "canada.md",
  "LAX": "united-states.md",
  "NYC": "united-states.md",
  "NJC": "united-states.md",
  "MIA": "united-states.md",
  "ATL": "united-states.md",
  "CHI": "united-states.md",
  "SEA": "united-states.md",
  "SFO": "united-states.md",
  "PHI": "united-states.md",
  "DET": "united-states.md",
  "SYD": "australia.md",
  "MEL": "australia.md",
  "AKL": "new-zealand.md",
}


TOPOLOGY_MARKER_START = "%% GENERATED:TOPOLOGY:{site}:START"
TOPOLOGY_MARKER_END = "%% GENERATED:TOPOLOGY:{site}:END"


def insert_topology_into_docs(docs_dir=DOCS_DIR, sites_csv=SITES_CSV, devices_csv=DEVICES_CSV, policy=ADDRESS_POLICY):
  """Marker-wraps and (re)writes each TOPOLOGY_SITES site's topology mermaid block, same
  idempotent shape as insert_into_docs() for the flat New Network box. Scopes its search to that
  site's own "## <CODE> --...\\n...\\n## <next site>" section first (danmark.md has two sites both
  titled "### Topology sketch...", identically -- without scoping, a naive search would find
  ODE's heading and FRD's interchangeably). Returns (inserted, replaced, missing) site-code lists.
  """
  sites, devices_by_site = load_all(sites_csv, devices_csv, policy)

  by_file = {}
  for site, fname in TOPOLOGY_SITES.items():
    by_file.setdefault(fname, []).append(site)

  inserted, replaced, missing = [], [], []

  for fname, site_codes in by_file.items():
    docs_path = docs_dir / fname
    text = docs_path.read_text(encoding="utf-8")

    for site in site_codes:
      block = render_topology_block(site, sites[site], devices_by_site)
      # No indent, unlike the flat New Network box's markers -- that one sits nested inside a
      # subgraph; this is a standalone top-level `graph TD`, flush left like every hand-authored
      # version of it already committed.
      start_marker = TOPOLOGY_MARKER_START.format(site=site)
      end_marker = TOPOLOGY_MARKER_END.format(site=site)
      wrapped = f"{start_marker}\n{block}\n{end_marker}"

      # Scope to this site's own section: from its own "## <CODE> --" header (or, for a
      # single-site file like cld.md/vrk.md, the whole file) up to the next top-level "## " header.
      site_header_re = re.compile(r'^## ' + re.escape(site) + r'\b.*$', re.MULTILINE)
      m = site_header_re.search(text)
      if m:
        next_header = re.search(r'^## (?!' + re.escape(site) + r'\b)', text[m.end():], re.MULTILINE)
        section_end = m.end() + next_header.start() if next_header else len(text)
        section_start = m.start()
      else:
        section_start, section_end = 0, len(text)
      section = text[section_start:section_end]

      start_idx = section.find(start_marker)
      if start_idx != -1:
        end_idx = section.find(end_marker, start_idx)
        if end_idx == -1:
          raise ValueError(f"{site}: found TOPOLOGY START marker but no matching END marker in {fname}")
        end_idx += len(end_marker)
        new_section = section[:start_idx] + wrapped + section[end_idx:]
        text = text[:section_start] + new_section + text[section_end:]
        replaced.append(site)
        continue

      # No markers yet -- first run against hand-authored content. Replace the mermaid fence
      # immediately following "Topology sketch" within this site's own section, where that
      # heading exists (cld.md/danmark.md) -- vrk.md never got a separate heading for it (only
      # one mermaid fence in the whole file), so fall back to the last fence in the section.
      fence_re = re.compile(r'Topology sketch.*?\n\n```mermaid\n.*?\n```', re.DOTALL)
      m2 = fence_re.search(section)
      if m2 is not None:
        heading_end = section.index("```mermaid\n", m2.start()) + len("```mermaid\n")
        fence_close = section.index("\n```", heading_end)
      else:
        all_fences = list(re.finditer(r'```mermaid\n.*?\n```', section, re.DOTALL))
        if not all_fences:
          missing.append(site)
          continue
        last = all_fences[-1]
        heading_end = last.start() + len("```mermaid\n")
        fence_close = section.index("\n```", heading_end)
      new_section = section[:heading_end] + wrapped + section[fence_close:]
      text = text[:section_start] + new_section + text[section_end:]
      inserted.append(site)

    docs_path.write_text(text, encoding="utf-8")

  return inserted, replaced, missing


# ==================================================================================================
# Old Network generator -- 2026-08-03, following the RTR/FWL AD re-audit (see
# benarbejde/legacy-devices.csv's own header and this file's git history the same day).
# Generalises the ~30 hand-built "Old Network (legacy, hand restyled -- prototype, not yet
# generated)" sections into the same generate-from-source-of-truth pattern render_topology_block()
# already uses, from two real data sources instead of one:
#   - devices.csv rows with Legacy=yes -- device classes that persisted continuously from the old
#     network into the new one (RTR, SWI, and every ordinary devices.csv exception Type: WKS, PHN,
#     CAM, WAP, SRV...). Read directly here (load_legacy_standard_devices()), NOT via
#     gi.load_devices() -- that function's STANDARD_OFFSETS dedup silently drops any row whose
#     octet matches the *new* network's standard slot for that Type, which is exactly what RTR's
#     real historic octet (.1) and SWI's (.250/.251) do (see address_policy.csv) -- every Legacy
#     RTR/SWI row would vanish before ever reaching this renderer otherwise. Confirmed empirically
#     2026-08-03 against FAL specifically (see IPOverride below).
#   - legacy-devices.csv -- device classes with no live counterpart at all (RAC/iLO/iDRAC, ESX,
#     VCT), see that file's own header.
#
# IPOverride convention: a devices.csv Notes field containing "IPOverride: X.X.X.X" overrides the
# normal HostOctet+site-subnet IP computation entirely. Exists for exactly one confirmed case so
# far -- FAL's real old EXARTRFAL001, genuinely squatting off its own subnet at 192.168.1.1 (Robert
# 2026-08-03: same disaster-zone pattern as FALCAM's static .1.1) -- kept as a Notes convention,
# not a new devices.csv column, because it's a single known exception, not a pattern.
#
# NOT yet covered: old-network domain controllers (Type=DCS). DCS is a standard-slot synthesized
# type for the new network (address_policy.csv: .10/.11 -- same continuity-collision shape as
# RTR/SWI), and no old DCS row has been through the same AD-cross-reference rigor RTR got before
# being trusted -- rendering old DC nodes needs that same verification pass first, not a rushed
# guess. Sites whose hand-built diagram has an O_DC/O_DC1/O_DC2 node will lose it in the generated
# version until that follow-up lands -- flagged, not silently dropped.
#
# Also a deliberate, disclosed simplification: several hand-built diagrams split devices across
# TWO old switches (e.g. SYD's server-stuff-under-SW1, endpoint-stuff-under-SW2), a distinction no
# data source records (only "a switch existed", never "which switch this device was on"). Every
# non-RTR/SWI device attaches to the first SWI instance uniformly here rather than guessing a split.
# ==================================================================================================

LEGACY_DEVICES_CSV = HERE / "legacy-devices.csv"

OLD_NETWORK_STYLE = TOPOLOGY_STYLE  # identical black/white convention, same constant, not a second copy

IP_OVERRIDE_RE = re.compile(r'IPOverride:\s*(\d{1,3}(?:\.\d{1,3}){3})')


def load_legacy_standard_devices(site: str, devices_csv=DEVICES_CSV):
  """Legacy=yes devices.csv rows for one site, read directly (bypassing gi.load_devices() -- see
  this section's own header for why). Returns dicts shaped: hostname, type, number, octet (string
  or None), ip_override (string or None), os, notes -- same shape load_legacy_extra_devices()
  returns, so render_old_network_block() doesn't need to handle two different shapes."""
  out = []
  with open(devices_csv, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
      if r["Site"].strip() != site:
        continue
      if (r.get("Legacy") or "").strip().lower() != "yes":
        continue
      dtype = r["Type"].strip().upper()
      try:
        number = int(r["Number"])
      except (KeyError, ValueError):
        continue
      notes = r.get("Notes", "") or ""
      ip_override = None
      m = IP_OVERRIDE_RE.search(notes)
      if m:
        ip_override = m.group(1)
        notes = (notes[:m.start()] + notes[m.end():]).strip(" -,()")
      octet_raw = r["HostOctet"].strip()
      out.append({
        "hostname": gi.build_hostname(dtype, site, number), "type": dtype, "number": number,
        "octet": octet_raw or None, "ip_override": ip_override,
        "os": (r.get("OS") or "").strip(), "notes": notes.strip(),
      })
  return out


def load_legacy_extra_devices(site: str, legacy_csv=LEGACY_DEVICES_CSV):
  """legacy-devices.csv rows (RAC/ESX/VCT -- old-network-only core infra with no live devices.csv
  counterpart -- plus, since 2026-08-04, a site-specific RTR/etc. hostname-reuse exception, see
  that file's own header) for one site. Same dict shape as load_legacy_standard_devices() so both
  feed the same renderer, including the same IPOverride Notes convention (FAL's old Cisco lives
  here specifically because it needs it: 192.168.1.1, off its own subnet)."""
  out = []
  if not legacy_csv.exists():
    return out
  with open(legacy_csv, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
      if r["Site"].strip() != site:
        continue
      dtype = r["Type"].strip().upper()
      try:
        number = int(r["Number"])
      except (KeyError, ValueError):
        continue
      notes = r.get("Notes", "") or ""
      ip_override = None
      m = IP_OVERRIDE_RE.search(notes)
      if m:
        ip_override = m.group(1)
        notes = (notes[:m.start()] + notes[m.end():]).strip(" -,()")
      octet_raw = (r.get("HostOctet") or "").strip()
      out.append({
        "hostname": gi.build_hostname(dtype, site, number), "type": dtype, "number": number,
        "octet": octet_raw or None, "ip_override": ip_override,
        "os": (r.get("OS") or "").strip(), "notes": notes.strip(),
      })
  return out


def load_old_network_devices(site: str, devices_csv=DEVICES_CSV, legacy_csv=LEGACY_DEVICES_CSV):
  return load_legacy_standard_devices(site, devices_csv) + load_legacy_extra_devices(site, legacy_csv)


def old_network_sites(devices_csv=DEVICES_CSV, legacy_csv=LEGACY_DEVICES_CSV):
  """Every site with at least one Legacy=yes devices.csv row or legacy-devices.csv row --
  dynamically derived, not a hand-maintained dict like TOPOLOGY_SITES, because "which sites have
  real old-network data" is itself a fact those two files already carry; hand-maintaining a third
  copy of that list would be exactly the kind of drift this repo's harness exists to catch."""
  sites = set()
  with open(devices_csv, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
      if (r.get("Legacy") or "").strip().lower() == "yes":
        sites.add(r["Site"].strip())
  if legacy_csv.exists():
    with open(legacy_csv, newline="", encoding="utf-8") as f:
      for r in csv.DictReader(f):
        sites.add(r["Site"].strip())
  return sites


def _old_network_ip(dev: dict, net) -> str:
  if dev.get("ip_override"):
    return dev["ip_override"]
  octet = dev.get("octet")
  if not octet or not str(octet).isdigit() or net is None:
    return "No IP Address"
  return str(gi.offset_ip(net, int(octet)))


def _old_network_label(dev: dict, net) -> str:
  """Unlike _topology_label()/render_new_network_block()'s labels, BANNED_TERMS is deliberately
  NOT enforced here (Robert, 2026-08-03): the New Network ban exists to keep FSMO/health-status
  chatter out of *current* documentation, but the Old Network is explicitly historical -- "DFSR
  stopped, C: 5% free", "27 days out of sync" etc. are real, informative operational history for
  dead infrastructure, not live-network noise. Stripping it would lose real content for no safety
  benefit; the New Network generator's own ban is untouched."""
  symbol = _topology_symbol(dev["type"])
  lines = [f"{symbol} {dev['hostname']}"]
  desc = dev.get("os") or ""
  short_notes = short_note(dev.get("notes") or "")
  if short_notes:
    desc = f"{desc} · {short_notes}" if desc else short_notes
  if desc:
    lines.append(desc)
  lines.append(_old_network_ip(dev, net))
  return "<br/>".join(lines)


def _old_network_group_label(dtype: str, group: list, net) -> str:
  """Same shape as _topology_other_group_label() (hostname range / count+name / IP range) for 2+
  same-Type devices at a site -- e.g. ABD's real committed "EXAWAPABD001-002 / 2x Ubiquiti UniFi
  U6-Pro / No IP Address" WAP box, generalised. No BANNED_TERMS check, same reasoning as
  _old_network_label(). RAC/ESX/DCR are never passed here -- render_old_network_block() keeps
  those individual so the manages-edge/bare-metal logic still has one node per real device."""
  symbol = _topology_symbol(dtype)
  name = TOPOLOGY_PLURAL_OVERRIDES.get(dtype) or _pluralize_type_name(TYPE_NAMES.get(dtype, dtype))
  numbers = sorted(d["number"] for d in group)
  hostname_prefix = re.sub(r'\d+$', '', group[0]["hostname"])
  num_str = ",".join(
    f"{a:03d}" if a == b else f"{a:03d}-{b:03d}" for a, b in _compress_ranges(numbers)
  )
  octets = [int(o) for d in group if (o := d.get("octet")) and str(o).isdigit()]
  overrides = [d["ip_override"] for d in group if d.get("ip_override")]
  if overrides and not octets:
    ip_line = overrides[0] if len(set(overrides)) == 1 else "No IP Address"
  elif octets and net is not None:
    ip_line = _format_ip_ranges(net, octets)
  else:
    ip_line = "No IP Address"
  lines = [
    f"{symbol} {hostname_prefix}{num_str}",
    f"{len(group)} x {_title_case_preserve_acronyms(name)}",
    ip_line,
  ]
  return "<br/>".join(lines)


def render_old_network_block(site: str, sites_row: dict, devices_csv=DEVICES_CSV, legacy_csv=LEGACY_DEVICES_CSV):
  """Returns the Old Network mermaid text (graph TD onward, no outer fence -- same convention as
  render_topology_block()), or None if this site has no old-network data, or no real RTR recorded
  (caller skips both cases -- never fabricates a router, see the RTR/FWL audit's own conclusion
  that some sites' old diagrams genuinely have nothing to show and that's fine as-is).

  Hierarchy: Internet -> RTR -> {each SWI directly}; everything else attaches to the first SWI if
  one exists, else straight to RTR (matches ODE/ATL's real no-switch-layer structure). RAC gets a
  dotted "manages" edge to the ESX sharing its Number, mirroring every hand-built diagram's own
  convention -- see this section's header for the dual-switch simplification this implies.
  """
  try:
    net = gi.validate_cidr(sites_row["Subnet"])
  except ValueError:
    net = None

  devices = load_old_network_devices(site, devices_csv, legacy_csv)
  if not devices:
    return None

  rtr = _first_instance(devices, "RTR")
  if rtr is None:
    return None

  type_counts = {}
  for dev in devices:
    type_counts[dev["type"]] = type_counts.get(dev["type"], 0) + 1

  node_ids = {}
  def node_id_for(dev):
    key = (dev["type"], dev["number"])
    if key in node_ids:
      return node_ids[key]
    nid = f"O_{dev['type']}" if type_counts[dev["type"]] == 1 else f"O_{dev['type']}{dev['number']}"
    node_ids[key] = nid
    return nid

  lines = ["%%{init: {'flowchart': {'curve': 'stepAfter'}}}%%", "graph TD"]
  style_lines = []
  edges = []

  def emit_node(dev):
    nid = node_id_for(dev)
    lines.append(f'    {nid}["{_old_network_label(dev, net)}"]')
    style_lines.append(f'    style {nid} {OLD_NETWORK_STYLE}')
    return nid

  inet_id = "O_INET"
  lines.append(f'    {inet_id}["\U0001F310 Internet"]')
  style_lines.append(f'    style {inet_id} {OLD_NETWORK_STYLE}')

  rtr_id = emit_node(rtr)
  edges.append(f'{inet_id} --> {rtr_id}')

  swis = sorted([d for d in devices if d["type"] == "SWI"], key=lambda d: d["number"])
  swi_ids = []
  for swi in swis:
    sid = emit_node(swi)
    swi_ids.append(sid)
    edges.append(f'{rtr_id} --> {sid}')

  attach_id = swi_ids[0] if swi_ids else rtr_id
  esxs_by_number = {d["number"]: d for d in devices if d["type"] == "ESX"}
  dcrs = sorted([d for d in devices if d["type"] == "DCR"], key=lambda d: d["number"])
  # Bare-metal pattern (ABD/TOR: a RAC/iLO managing a DC directly, no hypervisor layer at all) --
  # only applies when the site has no ESX to attach the RAC to instead. Which specific DCR is
  # VM-hosted-on-ESX vs standalone genuinely varies per site with no reliable signal in the data
  # to derive it (confirmed against ODE, which has both ESX *and* DCR but chains DCR straight off
  # RTR, not through ESX) -- so every DCR beyond the bare-metal-RAC case attaches directly, the
  # same disclosed simplification as the SW1/SW2 split above.
  bare_metal_dc = dcrs[0] if (dcrs and not esxs_by_number) else None

  rest = sorted(
    (d for d in devices if d["type"] not in ("RTR", "SWI")),
    key=lambda d: (d["type"], d["number"]),
  )

  # Group 2+ same-Type devices into one box (matches the New Network topology's own "Other"
  # bucket grouping, and every hand-built diagram that already did this for WAP/CAM, e.g. ABD's
  # real "EXAWAPABD001-002 / 2x Ubiquiti UniFi U6-Pro"). RAC/ESX/DCR stay individual regardless of
  # count -- the manages-edge/bare-metal-DC logic above needs one real node per device for those.
  NEVER_GROUP = {"RAC", "ESX", "DCR"}
  groups = {}
  singles = []
  for dev in rest:
    if dev["type"] in NEVER_GROUP:
      singles.append(dev)
    else:
      groups.setdefault(dev["type"], []).append(dev)

  grouped_rest = list(singles)
  group_nodes = []  # (dtype, group) pairs rendered as one box, in Type order
  for dtype in sorted(groups):
    group = groups[dtype]
    if len(group) == 1:
      grouped_rest.append(group[0])
    else:
      group_nodes.append((dtype, group))
  grouped_rest.sort(key=lambda d: (d["type"], d["number"]))

  for dev in grouped_rest:
    if dev is bare_metal_dc:
      nid = node_id_for(dev)
      lines.append(f'    {nid}["{_old_network_label(dev, net)}"]')
      style_lines.append(f'    style {nid} {OLD_NETWORK_STYLE}')
      continue  # arrives only via the RAC "manages" edge below, no direct attach_id edge
    nid = emit_node(dev)
    edges.append(f'{attach_id} --> {nid}')
    if dev["type"] == "RAC":
      if dev["number"] in esxs_by_number:
        edges.append(f'{nid} -.->|"manages"| {node_id_for(esxs_by_number[dev["number"]])}')
      elif bare_metal_dc is not None:
        edges.append(f'{nid} -.->|"manages"| {node_id_for(bare_metal_dc)}')

  for dtype, group in group_nodes:
    nid = f"O_{dtype}"
    lines.append(f'    {nid}["{_old_network_group_label(dtype, group, net)}"]')
    style_lines.append(f'    style {nid} {OLD_NETWORK_STYLE}')
    edges.append(f'{attach_id} --> {nid}')

  lines.extend(f'    {e}' for e in edges)
  lines.append("")
  lines.extend(style_lines)
  return "\n".join(lines)


OLDNET_MARKER_START = "%% GENERATED:OLDNETWORK:{site}:START"
OLDNET_MARKER_END = "%% GENERATED:OLDNETWORK:{site}:END"


def insert_old_network_into_docs(docs_dir=DOCS_DIR, sites_csv=SITES_CSV, devices_csv=DEVICES_CSV,
                                  legacy_csv=LEGACY_DEVICES_CSV):
  """Marker-wraps and (re)writes each old-network site's Old Network mermaid block, same
  idempotent shape as insert_topology_into_docs(). Site list comes from old_network_sites() (data-
  derived), file location from TOPOLOGY_SITES (every old-network site already has a topology entry
  -- it's a real, currently-onboarded site by definition). Scopes its search to that site's own
  section first, same reason insert_topology_into_docs() does. Returns (inserted, replaced,
  missing) site-code lists."""
  sites, _ = load_all(sites_csv, devices_csv, ADDRESS_POLICY)

  candidate_sites = sorted(old_network_sites(devices_csv, legacy_csv))
  by_file = {}
  for site in candidate_sites:
    fname = TOPOLOGY_SITES.get(site)
    if fname is None:
      continue
    by_file.setdefault(fname, []).append(site)

  inserted, replaced, missing = [], [], []

  for fname, site_codes in by_file.items():
    docs_path = docs_dir / fname
    text = docs_path.read_text(encoding="utf-8")

    for site in site_codes:
      block = render_old_network_block(site, sites[site], devices_csv, legacy_csv)
      if block is None:
        missing.append(site)
        continue

      start_marker = OLDNET_MARKER_START.format(site=site)
      end_marker = OLDNET_MARKER_END.format(site=site)
      wrapped = f"{start_marker}\n{block}\n{end_marker}"

      site_header_re = re.compile(r'^## ' + re.escape(site) + r'\b.*$', re.MULTILINE)
      m = site_header_re.search(text)
      if m:
        next_header = re.search(r'^## (?!' + re.escape(site) + r'\b)', text[m.end():], re.MULTILINE)
        section_end = m.end() + next_header.start() if next_header else len(text)
        section_start = m.start()
      else:
        section_start, section_end = 0, len(text)
      section = text[section_start:section_end]

      start_idx = section.find(start_marker)
      if start_idx != -1:
        end_idx = section.find(end_marker, start_idx)
        if end_idx == -1:
          raise ValueError(f"{site}: found OLDNETWORK START marker but no matching END marker in {fname}")
        end_idx += len(end_marker)
        new_section = section[:start_idx] + wrapped + section[end_idx:]
        text = text[:section_start] + new_section + text[section_end:]
        replaced.append(site)
        continue

      # No markers yet -- first run against hand-authored content. The Old Network fence is always
      # the FIRST ```mermaid fence in this site's section (the Topology sketch fence, matched by
      # insert_topology_into_docs()'s own heading search, always comes later) -- excluding any
      # fence embedded inside a collapsed <details> reference block, which sits after the live one.
      details_idx = section.find("<details>")
      search_region = section[:details_idx] if details_idx != -1 else section
      all_fences = list(re.finditer(r'```mermaid\n.*?\n```', search_region, re.DOTALL))
      if not all_fences:
        missing.append(site)
        continue
      first = all_fences[0]
      heading_end = first.start() + len("```mermaid\n")
      fence_close = section.index("\n```", heading_end)
      new_section = section[:heading_end] + wrapped + section[fence_close:]
      text = text[:section_start] + new_section + text[section_end:]
      inserted.append(site)

    docs_path.write_text(text, encoding="utf-8")

  return inserted, replaced, missing


# %% is mermaid's real comment syntax -- an HTML <!-- --> comment is NOT valid inside a flowchart
# body (confirmed via a live kroki.io round-trip 2026-07-13: mermaid's lexer treats "<!--" as the
# start of an HTML tag (TAGSTART), which is only legal inside a node label, not as a bare statement
# in the graph body -- real HTTP 400 syntax error, not a guess).
MARKER_START = "    %% GENERATED:NEW-NETWORK:{site}:START"
MARKER_END = "    %% GENERATED:NEW-NETWORK:{site}:END"


def insert_into_docs(docs_dir=DOCS_DIR, sites_csv=SITES_CSV, devices_csv=DEVICES_CSV, policy=ADDRESS_POLICY):
  """Idempotently (re)writes every site's marker-wrapped New Network block into its region file
  under docs_dir (see REGION_FILES/SITE_TO_REGION_FILE above).

  Three cases per site, all converging on the same marker-wrapped, freshly-generated form:
    1. Markers already present (re-run / freshness check) -- replace content between them.
    2. No markers, but a bare "subgraph NEW_<SITE> [" already exists -- wrap it with markers and
       replace with freshly-generated text, so it's guaranteed byte-identical to the generator's
       own output.
    3. Neither exists -- insert directly after "style OLD_<SITE> fill:...", the last line of that
       site's Old Network box, still inside the same fence.

  Returns (inserted, replaced, missing) site-code lists for the caller to report.
  """
  blocks = generate_all(sites_csv, devices_csv, policy)

  by_file = {}
  for site, block in blocks.items():
    fname = SITE_TO_REGION_FILE.get(site)
    if fname is None:
      continue  # e.g. BRD/VRK -- no diagram section anywhere, by design
    by_file.setdefault(fname, []).append((site, block))

  inserted, replaced, missing = [], [], []

  for fname, site_blocks in by_file.items():
    docs_path = docs_dir / fname
    text = docs_path.read_text(encoding="utf-8")

    for site, block in site_blocks:
      start_marker = MARKER_START.format(site=site)
      end_marker = MARKER_END.format(site=site)
      wrapped = f"{start_marker}\n{block}\n{end_marker}"

      start_idx = text.find(start_marker)
      if start_idx != -1:
        end_idx = text.find(end_marker, start_idx)
        if end_idx == -1:
          raise ValueError(f"{site}: found START marker but no matching END marker in {fname}")
        end_idx += len(end_marker)
        text = text[:start_idx] + wrapped + text[end_idx:]
        replaced.append(site)
        continue

      bare_re = re.compile(
        r'    subgraph NEW_' + re.escape(site) + r' \[.*?\n'
        r'(?:.*\n)*?'
        r'    style NEW_' + re.escape(site) + r' fill:[^\n]*\n?',
      )
      m = bare_re.search(text)
      if m:
        text = text[:m.start()] + wrapped + "\n" + text[m.end():]
        replaced.append(site)
        continue

      old_style_re = re.compile(r'    style OLD_' + re.escape(site) + r' fill:[^\n]*\n')
      m = old_style_re.search(text)
      if m:
        text = text[:m.end()] + wrapped + "\n" + text[m.end():]
        inserted.append(site)
        continue

      missing.append(site)

    docs_path.write_text(text, encoding="utf-8")

  return inserted, replaced, missing


def main():
  if "--write" in sys.argv:
    inserted, replaced, missing = insert_into_docs()
    print(f"Flat New Network boxes -- inserted (new): {len(inserted)} {inserted}")
    print(f"Flat New Network boxes -- replaced (existing marker or bare block): {len(replaced)} {replaced}")
    if missing:
      print(f"MISSING -- no Old Network box and no existing New Network block found, skipped: {missing}", file=sys.stderr)

    t_inserted, t_replaced, t_missing = insert_topology_into_docs()
    print(f"Topology sketches -- inserted (new): {len(t_inserted)} {t_inserted}")
    print(f"Topology sketches -- replaced (existing marker or bare block): {len(t_replaced)} {t_replaced}")
    if t_missing:
      print(f"MISSING -- no Topology sketch heading/fence and no existing marker found, skipped: {t_missing}", file=sys.stderr)

    # Wired in 2026-08-04 (Robert's call) -- insert_old_network_into_docs() existed, fully built,
    # since before this file's 2026-07-31 restyling, but was never called from here. The
    # GENERATED:OLDNETWORK markers already in docs/network-diagram/*.md implied this ran on every
    # --write same as the topology sketch below; it didn't, and real drift had already
    # accumulated (confirmed: FAL's Old Network box was missing a workstation devices.csv had
    # gained, and a router note added earlier the same day this got wired in).
    o_inserted, o_replaced, o_missing = insert_old_network_into_docs()
    print(f"Old Network boxes -- inserted (new): {len(o_inserted)} {o_inserted}")
    print(f"Old Network boxes -- replaced (existing marker or bare block): {len(o_replaced)} {o_replaced}")
    if o_missing:
      print(f"Old Network boxes -- no RTR/old-network data, nothing to render (expected for some sites): {len(o_missing)} {o_missing}")
    return

  blocks = generate_all()
  only = sys.argv[1] if len(sys.argv) > 1 else None
  for site, block in blocks.items():
    if only and site != only:
      continue
    print(f"--- {site} ---")
    print(block)
    print()


if __name__ == "__main__":
  main()
