#!/usr/bin/env python3

# ==================================================================================================
# Example Music -- New Network diagram generator
#
# Generates the "New Network (current)" mermaid subgraph for each site in sites.csv, from the same
# single source of truth generate_inventory.py uses for the real Ansible inventory (sites.csv +
# devices.csv + address_policy.json + ad_forest.json) -- not a second, hand-maintained data model.
# Reuses generate_inventory.py's own building blocks (compute_standard_devices_for_site(),
# load_devices(), NON_STANDARD_SITES, NO_STANDARD_ROUTER_SITES, ALWAYS_EXCLUDE_TYPES) rather than
# re-deriving which devices are real -- if those rules change, this picks the change up for free.
#
# Output is inserted into docs/network-diagram.md between matching
#   <!-- GENERATED:NEW-NETWORK:<SITE>:START --> / :END -->
# markers by insert_into_docs(). ansible/at_have_ryggen_fri's freshness check (check 14) regenerates
# into a scratch dir and diffs against what's committed -- this script is the single place that
# logic lives; the check just calls it and compares.
#
# See docs/network-diagram.md's "Visual Standard" section for the shape/colour/symbol convention
# this implements, and ansible/at_have_ryggen_fri/README.md's Backlog section for the overall plan.
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
ADDRESS_POLICY = HERE / "address_policy.json"
DOCS_FILE = HERE.parent / "docs" / "network-diagram.md"

# Same five-shape vocabulary as docs/network-diagram.md's Visual Standard section. Keep these two
# in sync by hand (the list is small and stable); check_network_diagram_shape_compliance (harness
# check 15) enforces that every generated node actually uses one of these five wrappers, so drift
# between this map and the documented standard fails loudly rather than silently.
NET_TYPES = {'RTR', 'FWL', 'SWI'}
SRV_TYPES = {'DCS', 'DCR', 'SVR', 'SRV', 'RDR', 'RRY', 'ANS', 'PBX', 'DNS', 'PRV', 'NAS', 'PVE', 'SBC', 'TAR', 'UFC', 'RAC'}
WIRELESS_TYPES = {'WAP'}
ENDPOINT_TYPES = {'WKS', 'LAP', 'MBP', 'TAB', 'SUR', 'PHN', 'PRN', 'CAM', 'LCD', 'VCU', 'TVS', 'MAC', 'NIX', 'BPS'}
CURVEBALL_TYPES = {'VND', 'MUS', 'PAY', 'COF', 'TEA', 'PMP', 'CLK', 'MIC', 'RAD', 'MOO', 'LIN', 'FCL', 'AST', 'TTY', 'BUS', 'CAR', 'JET', 'TRK', 'DON'}

# Placeholder Unicode symbols pending Robert's Phase 5 sign-off (see the curveball table in the
# plan) -- literal question mark, not a guess, per "if unsure, ask" instruction.
PLACEHOLDER_SYMBOL = "❓"  # ❓

# Terms that must never appear in a New Network label -- FSMO roles and health/low-disk-space
# annotations stay old-infra-only (docs/network-inventory.md), by data-source construction (neither
# sites.csv nor devices.csv carries this information at all) but enforced here too as a defensive
# backstop, not just a doc convention that could rot.
BANNED_TERMS = re.compile(r'FSMO|DFSR|low disk|OOS \d|EOL\b|UNHEALTHY|out of sync', re.IGNORECASE)


def shape_wrap(node_id: str, label: str, dtype: str) -> str:
  if dtype in NET_TYPES:
    return f'{node_id}{{{{"{label}"}}}}'
  if dtype in SRV_TYPES:
    return f'{node_id}[("{label}")]'
  if dtype in WIRELESS_TYPES:
    return f'{node_id}(("{label}"))'
  if dtype in ENDPOINT_TYPES:
    return f'{node_id}(["{label}"])'
  if dtype in CURVEBALL_TYPES:
    return f'{node_id}>"{label}"]'
  raise ValueError(f"Unmapped device type for shape assignment: {dtype!r} (node {node_id})")


def short_note(notes: str) -> str:
  """First clause of a devices.csv Notes field -- these are often a full sentence or more of
  free-text context (e.g. the CLD/FRD PBX row), not diagram-label length. Split on the first
  ' -- ' or '. ', whichever comes first; cap at 60 chars either way."""
  notes = (notes or "").strip()
  if not notes:
    return ""
  cut = len(notes)
  for sep in (" -- ", ". "):
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

  if site not in gi.NON_STANDARD_SITES:
    for d in gi.compute_standard_devices_for_site(site, net):
      dtype = re.match(r'EXA([A-Z]{3})', d["Hostname"]).group(1)
      if dtype == 'RTR' and site in gi.NO_STANDARD_ROUTER_SITES:
        continue  # documentation-only placeholder for DNS purposes, not a real device here
      out.append({
        "hostname": d["Hostname"], "type": dtype, "octet": d["HostOctet"],
        "label_extra": d["Notes"].replace("Standard ", "").replace(" slot", ""),
        "subnet_site": None, "is_foreign": False,
      })

  for dev in devices_by_site.get(site, []):
    if dev.get("subnet_site"):
      continue  # hostnamed here but physically elsewhere -- belongs in ITS subnet_site's box, not this one
    out.append({
      "hostname": dev["hostname"], "type": dev["type"], "octet": dev["octet"],
      "label_extra": short_note(dev["notes"]), "subnet_site": None, "is_foreign": False,
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

  lines = [f'    subgraph NEW_{site} ["\U0001F195 New Network (current)"]']
  seen_ids = {}
  for dev in devices:
    label = dev["hostname"]
    if dev["label_extra"]:
      label += f'<br/>{dev["label_extra"]}'
    if dev["octet"]:
      label += f'<br/>.{dev["octet"]}'
    if BANNED_TERMS.search(label):
      raise ValueError(f"Banned FSMO/health term found in New Network label for {site}: {label!r}")

    base_id = f"N_{dev['type']}"
    seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
    node_id = base_id if seen_ids[base_id] == 1 else f"{base_id}{seen_ids[base_id]}"

    symbol = PLACEHOLDER_SYMBOL if dev["type"] in CURVEBALL_TYPES else ""
    display_label = f"{symbol} {label}".strip()
    lines.append(f'      {shape_wrap(node_id, display_label, dev["type"])}')

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


# %% is mermaid's real comment syntax -- an HTML <!-- --> comment is NOT valid inside a flowchart
# body (confirmed via a live kroki.io round-trip 2026-07-13: mermaid's lexer treats "<!--" as the
# start of an HTML tag (TAGSTART), which is only legal inside a node label, not as a bare statement
# in the graph body -- real HTTP 400 syntax error, not a guess).
MARKER_START = "    %% GENERATED:NEW-NETWORK:{site}:START"
MARKER_END = "    %% GENERATED:NEW-NETWORK:{site}:END"


def insert_into_docs(docs_path=DOCS_FILE, sites_csv=SITES_CSV, devices_csv=DEVICES_CSV, policy=ADDRESS_POLICY):
  """Idempotently (re)writes every site's marker-wrapped New Network block into docs_path.

  Three cases per site, all converging on the same marker-wrapped, freshly-generated form:
    1. Markers already present (re-run / freshness check) -- replace content between them.
    2. No markers, but a bare "subgraph NEW_<SITE> [" already exists (the four new-build sites,
       hand-inserted before this function existed) -- wrap it with markers and replace with
       freshly-generated text, so it's guaranteed byte-identical to the generator's own output.
    3. Neither exists (the 47 pre-existing sites) -- insert directly after "style OLD_<SITE>
       fill:...", the last line of that site's Old Network box, still inside the same fence.

  Returns (inserted, replaced, missing) site-code lists for the caller to report.
  """
  blocks = generate_all(sites_csv, devices_csv, policy)
  text = docs_path.read_text(encoding="utf-8")

  inserted, replaced, missing = [], [], []

  for site, block in blocks.items():
    start_marker = MARKER_START.format(site=site)
    end_marker = MARKER_END.format(site=site)
    wrapped = f"{start_marker}\n{block}\n{end_marker}"

    start_idx = text.find(start_marker)
    if start_idx != -1:
      end_idx = text.find(end_marker, start_idx)
      if end_idx == -1:
        raise ValueError(f"{site}: found START marker but no matching END marker")
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
    print(f"Inserted (new): {len(inserted)} {inserted}")
    print(f"Replaced (existing marker or bare block): {len(replaced)} {replaced}")
    if missing:
      print(f"MISSING -- no Old Network box and no existing New Network block found, skipped: {missing}", file=sys.stderr)
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
