#!/usr/bin/env python3
"""
parse_tdf.py — Convert jukebox.example.tdf sections to JSON for Ansible.

*** LEGACY / DEFUNCT TOOL — READ BEFORE USING ***
This is old code kept around because the demo data it produces (ad_users.json,
ad_groups.json, ad_computers.json) is still genuinely useful, not because this
is the current, actively-developed approach to anything. It is a manual,
offline, run-by-hand tool ONLY:
    - No Ansible playbook or task invokes this script, or reads
      jukebox.example.tdf, at any point, directly or indirectly. Only the
      JSON files this script produces are ever read by Ansible (by
      windows_adschema/playbooks/{20-ad-groups,30-ad-users,40-ad-computers}.yml).
    - jukebox.example.tdf and this script must stay that way: offline inputs
      to a manual regeneration step, never a live Ansible dependency. If you
      find yourself wiring either into a playbook, stop and reconsider.
Both files live in benarbejde/ alongside sites.csv/devices.csv, but unlike
those, neither is synced to bootstrap/web/proxmox/ or deployed to
/etc/example-music/ by anything — there's deliberately no live path for
either.

Usage:
    python3 parse_tdf.py --section {users|groups|computers}
                         [--tdf /path/to/jukebox.example.tdf]
                         [--domain jukebox.internal]
                         [--email-domain jukebox.internal]
                         [--sites-csv /path/to/sites.csv]
                         [--out /path/to/output.json]

    --domain defaults to ad_forest.json's domain_fqdn (co-located in
    benarbejde/, the repo's single source of truth for this) rather than a
    hardcoded literal -- pass --domain explicitly to override.

Sections:
    users     — $Script:rawUsers: user accounts with computed ad_ou paths
    groups    — $Script:rawDemoGroups: security groups
    computers — $Script:rawComputers: computer/device accounts with computed ad_ou paths

Output is a JSON array — written to --out if given, otherwise stdout (the
original behaviour; redirect with `> benarbejde/ad_users.json` yourself).
Errors and warnings go to stderr. Exit 0 on success, 1 on error.

Domain substitution:
    --domain        rewrites DNS hostnames (.example.net → .jukebox.internal, etc.)
    --email-domain  rewrites UPN and email address suffixes (@example.net → @...).
                    Defaults to --domain. Set to your routable email domain in
                    production (e.g. --email-domain example1.co.uk) so users can
                    log in as user@example1.co.uk. The AD forest must have that
                    suffix registered — ad_schema.yml Section 9 does this when
                    ad_upn_suffixes is non-empty.

Notes on demo-data quirks handled:
    • OU paths rooted at 'Resources' (room mailboxes) are skipped.
    • OU paths with a sub-city level (e.g. Falkirk > Grangemouth > Band) fold the
      sub-city into the parent city so they resolve into the schema hierarchy.
    • Unknown site codes for computers emit a warning to stderr and produce an
      empty ad_ou; those objects are skipped by the Ansible playbook.
    • Manager field is a display name string — the playbook resolves it to a
      SamAccountName via a name→SAM lookup built from the users list itself,
      preferring a candidate in the same ad_ou as the report (30-ad-users.yml
      Section D) since several real people appear twice under different bands
      with the same display Name (see next point).
    • A handful of real people who moved between two bands appear as two TDF
      records with the same Name (e.g. Terry Hall: The Specials + Fun Boy
      Three). AD requires a unique SamAccountName per object, so the SECOND
      such record must carry a disambiguating suffix (e.g. terry.hall.fb3,
      paul.weller.sc) — this is authored directly in the .tdf source, not
      generated here. Five more real duplicates (Andy Cox, David Steele, Lars
      Pedersen, Neil Finn, Eddie Rayner) were found missing this suffix
      2026-07-17 and fixed the same way (andy.cox.beat, david.steele.beat,
      lars.pedersen.1k, neil.finn.se, eddie.rayner.se) — if a future TDF edit
      adds another dual-band person, give the second occurrence the same
      treatment, or 30-ad-users.yml will silently create/manage only one of
      the two intended AD objects.
    • Locked=$true accounts are NOT reproducible programmatically; accounts will
      be created in an unlocked state regardless of the TDF value.

Changelog:
    2026-07-17  --domain's default was a hardcoded 'jukebox.internal' literal,
                independent of benarbejde/ad_forest.json (the repo's single
                source of truth for this since 2026-07-09) -- meaning this
                generator's default could silently drift from the real value
                if the forest were ever renamed. Now reads domain_fqdn from
                ad_forest.json (co-located in benarbejde/) at argparse-default
                time, falling back to the old literal only if that file is
                genuinely missing. --domain can still be passed explicitly to
                override, unchanged.
    2026-07-09  Fixed a real parser bug in _arr(): the OU-array regex stopped at
                the first ')', so a quoted element containing a literal paren
                (e.g. 'Chicago (Band)') silently truncated, dropping the real
                value and shifting every later field. Also fixed _EMAIL_PATTERNS
                to cover @fb3.example.net and @example.dk, previously missed.
    2026-07-09  Moved here from ansible/playbooks/windows_adschema/ (jukebox.
                example.tdf moved from the repo root at the same time) --
                consolidating this alongside sites.csv/devices.csv, the other
                source-of-truth files this script's sibling generator
                (generate_inventory.py) already lives next to. --tdf and
                --sites-csv now default to co-located paths instead of
                /etc/example-music/... (which nothing ever deployed either
                file to -- that default had never actually been exercised).
                Added --out for writing directly to a file, matching
                generate_inventory.py's own convention, instead of always
                requiring the caller to redirect stdout.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Domain substitution — split into DNS (hostnames) and email (UPN / addresses)
# ---------------------------------------------------------------------------

# Applied to DNSHostName on computer objects only.
_DNS_PATTERNS = [
    ('.example.net',    '.{d}'),
    ('.example.org',    '.{d}'),
    ('.example.com',    '.{d}'),
    ('jukebox.example', '{d}'),
    ('example.net',     '{d}'),
    ('example.org',     '{d}'),
    ('example.com',     '{d}'),
]

# Applied to UserPrincipalName and Email fields on user / group objects.
# fb3.example.net must be listed even though it contains 'example.net' as a
# substring -- .replace() only matches the exact leading pattern, and
# '@example.net' does not occur inside '@fb3.example.net' (there's no '@'
# immediately before 'example.net'), so without its own entry these addresses
# pass through unmodified. Same story for example.dk, a demo domain used by
# the Danish groups/users that was never added here.
_EMAIL_PATTERNS = [
    ('@fb3.example.net', '@{d}'),
    ('@example.net',     '@{d}'),
    ('@example.org',     '@{d}'),
    ('@example.com',     '@{d}'),
    ('@example.dk',      '@{d}'),
]

# ISO 3166-1 alpha-2 corrections (the TDF uses 'UK' but AD expects 'GB').
_COUNTRY_ISO = {
    'UK': 'GB',
}


def _sub_dns(s, domain):
    """Rewrite demo DNS suffixes to the AD internal domain."""
    if not isinstance(s, str):
        return s
    for old, tmpl in _DNS_PATTERNS:
        s = s.replace(old, tmpl.format(d=domain))
    return s


def _sub_email(s, email_domain):
    """Rewrite demo @example.* UPN/email suffixes to the production email domain."""
    if not isinstance(s, str):
        return s
    for old, tmpl in _EMAIL_PATTERNS:
        s = s.replace(old, tmpl.format(d=email_domain))
    return s


# ---------------------------------------------------------------------------
# Country / continent normalisation
# ---------------------------------------------------------------------------

COUNTRY_NORM = {
    'UK': 'United Kingdom',        'United Kingdom': 'United Kingdom',
    'DE': 'Germany',               'Deutschland': 'Germany',        'Germany': 'Germany',
    'DK': 'Denmark',               'Danmark': 'Denmark',            'Denmark': 'Denmark',
    'NL': 'Netherlands',           'Nederland': 'Netherlands',      'Netherlands': 'Netherlands',
    'SE': 'Sweden',                'Sverige': 'Sweden',             'Sweden': 'Sweden',
    'NO': 'Norway',                'Norge': 'Norway',               'Norway': 'Norway',
    'IT': 'Italy',                 'Italia': 'Italy',               'Italy': 'Italy',
    'AT': 'Austria',               'Osterreich': 'Austria',         'Austria': 'Austria',
    'US': 'United States',         'USA': 'United States',          'United States': 'United States',
    'CA': 'Canada',                'Canada': 'Canada',
    'AU': 'Australia',             'Australia': 'Australia',
    'NZ': 'New Zealand',           'New Zealand': 'New Zealand',
    'LB': 'Lebanon',               'Lebanon': 'Lebanon',
    'GL': 'Global',
}

CONTINENT_MAP = {
    'United Kingdom': 'Europe',
    'Germany':        'Europe',
    'Denmark':        'Europe',
    'Netherlands':    'Europe',
    'Sweden':         'Europe',
    'Italy':          'Europe',
    'Norway':         'Europe',
    'Austria':        'Europe',
    'United States':  'North America',
    'Canada':         'North America',
    'Australia':      'Asia Pacific',
    'New Zealand':    'Asia Pacific',
    'Lebanon':        'Middle East',
}

REGION_CONTINENT = {
    'uk_site':    'Europe',
    'de_site':    'Europe',
    'dk_site':    'Europe',
    'eu_site':    'Europe',
    'lb_site':    'Middle East',
    'us_site':    'North America',
    'ca_site':    'North America',
    'apac_site':  'Asia Pacific',
    'cloud_site': 'Cloud Infrastructure',
}

ROLE_TO_SUB_OU = {
    # Workstations
    'WKS': 'Workstations', 'LAP': 'Workstations', 'SUR': 'Workstations',
    'MBP': 'Workstations', 'MAC': 'Workstations', 'VDU': 'Workstations',
    # Servers
    'DCS': 'Servers', 'SRV': 'Servers', 'SVR': 'Servers',
    'SBC': 'Servers', 'RDR': 'Servers',
    # Infrastructure
    'FWL': 'Infrastructure', 'RTR': 'Infrastructure', 'SWI': 'Infrastructure',
    'RAC': 'Infrastructure', 'PVE': 'Infrastructure', 'NAS': 'Infrastructure',
    'NIX': 'Infrastructure',
    # Telephony
    'PHN': 'Telephony', 'PBX': 'Telephony', 'PAY': 'Telephony',
    # AV
    'LCD': 'AV', 'TVS': 'AV', 'VCU': 'AV', 'MIC': 'AV', 'RAD': 'AV',
    # IoT
    'CAM': 'IoT', 'WAP': 'IoT', 'CLK': 'IoT', 'PMP': 'IoT',
    'TEA': 'IoT', 'COF': 'IoT', 'PRN': 'IoT', 'DON': 'IoT',
    'VND': 'IoT', 'MUS': 'IoT', 'TTY': 'IoT', 'OB': 'IoT',
    # Assets
    'TAB': 'Assets', 'BUS': 'Assets', 'CAR': 'Assets', 'TRK': 'Assets',
    'JET': 'Assets', 'AST': 'Assets', 'MOO': 'Assets',
}


# ---------------------------------------------------------------------------
# Low-level field extractors
# ---------------------------------------------------------------------------

def _str(text, key):
    """Return the 'quoted' value for Key='value', or None."""
    m = re.search(
        r"(?:;\s*|^|\{)\s*'?" + re.escape(key) + r"'?\s*=\s*'([^']*)'",
        text,
    )
    return m.group(1) if m else None


def _bool(text, key):
    """Return True/False/None for Key=$true/$false/$null, or None if absent."""
    m = re.search(
        r"(?:;\s*|^|\{)\s*'?" + re.escape(key) + r"'?\s*=\s*\$(true|false|null)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    v = m.group(1).lower()
    return True if v == 'true' else (False if v == 'false' else None)


def _arr(text, key):
    """Return list of strings for Key=@('a','b','c'), or [] if absent.

    The closing ) is matched via a lookahead for a following ;/} rather than
    a plain [^)]* stop-at-first-) -- a quoted element containing a literal
    paren (e.g. 'Chicago (Band)') would otherwise truncate the capture at
    that inner ), silently dropping the rest of the array and shifting every
    later element down one position. Found via 3 mis-parsed OU arrays
    (Robert Lamm/Peter Cetera/Danny Seraphine, all 'Chicago (Band)') that
    resolved to a nonexistent 'Illinois' city OU instead of 'Chicago'.
    """
    m = re.search(
        r"(?:;\s*|^|\{)\s*'?" + re.escape(key) + r"'?\s*=\s*@\((.*?)\)(?=\s*[;}])",
        text,
    )
    if not m:
        return []
    return re.findall(r"'([^']*)'", m.group(1))


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

def _extract_section_lines(all_lines, var_name):
    """Yield lines inside $Script:varName=@( ... ) — stops at a lone ')' line."""
    start_re = re.compile(r'\$Script:' + re.escape(var_name) + r'\s*=\s*@\(')
    in_section = False
    for line in all_lines:
        if not in_section:
            if start_re.search(line):
                in_section = True
            continue
        stripped = line.strip()
        if stripped == ')':
            return
        yield line


# ---------------------------------------------------------------------------
# OU path derivation — users
# ---------------------------------------------------------------------------

def _user_ou_path(ou_list, base_dn):
    """
    Convert a TDF user OU array to structured AD DN fields.

    Returns a dict:
        ad_ou           — parent container DN for the user object
        ad_band_ou_name — band/team OU name (empty string if none)
        ad_band_parent  — parent DN for the band OU (empty string if none)

    Returns None to signal the user should be skipped entirely.
    """
    if not ou_list:
        return {'ad_ou': '', 'ad_band_ou_name': '', 'ad_band_parent': ''}

    work = list(ou_list)

    # Strip known prefix tokens
    if work and work[0] in ('Locations', 'Devices'):
        work = work[1:]

    if not work:
        return {'ad_ou': '', 'ad_band_ou_name': '', 'ad_band_parent': ''}

    # Non-standard roots: skip resource mailboxes, template containers, etc.
    non_standard_roots = {'Templates', 'Resources', 'Cloud', 'Service Accounts'}
    if work[0] in non_standard_roots:
        return None  # signal skip

    # ── Decode position-based components ────────────────────────────────────

    continent = ''
    country   = ''
    province  = ''
    city      = ''
    band      = ''

    if work[0] == 'Middle East':
        # @('Middle East', 'Lebanon', 'Beirut', 'Band')
        continent    = 'Middle East'
        country_raw  = work[1] if len(work) > 1 else ''
        country      = COUNTRY_NORM.get(country_raw, country_raw)
        city         = work[2] if len(work) > 2 else ''
        band         = work[3] if len(work) > 3 else ''

    elif len(work) >= 5:
        # @('UK', 'Scotland', 'Falkirk', 'Grangemouth', 'Lowlife')
        # Sub-city level present — collapse sub-city into city.
        country_raw = work[0]
        country     = COUNTRY_NORM.get(country_raw, country_raw)
        continent   = CONTINENT_MAP.get(country, 'Europe')
        province    = work[1]
        city        = work[2]
        # work[3] = sub-city (Grangemouth) — not in our schema, drop it
        band        = work[4]

    elif len(work) == 4:
        # @('UK', 'Scotland', 'Aberdeen', 'Eurythmics')
        country_raw = work[0]
        country     = COUNTRY_NORM.get(country_raw, country_raw)
        continent   = CONTINENT_MAP.get(country, 'Europe')
        province    = work[1]
        city        = work[2]
        band        = work[3]

    elif len(work) == 3:
        # @('Deutschland', 'Berlin', 'Simple Minds')
        country_raw = work[0]
        country     = COUNTRY_NORM.get(country_raw, country_raw)
        continent   = CONTINENT_MAP.get(country, 'Europe')
        city        = work[1]
        band        = work[2]

    elif len(work) == 2:
        # @('country', 'city') — no band OU
        country_raw = work[0]
        country     = COUNTRY_NORM.get(country_raw, country_raw)
        continent   = CONTINENT_MAP.get(country, 'Europe')
        city        = work[1]

    else:
        return {'ad_ou': '', 'ad_band_ou_name': '', 'ad_band_parent': ''}

    # ── Assemble the AD path ─────────────────────────────────────────────────

    parts = []
    if band:
        parts.append(f'OU={band}')
    parts.append('OU=Users')
    if city:
        parts.append(f'OU={city}')
    if province:
        parts.append(f'OU={province}')
    if country and country != 'Global':
        parts.append(f'OU={country}')
    if continent:
        parts.append(f'OU={continent}')
    parts.append('OU=Sites')
    parts.append(base_dn)

    ad_ou          = ','.join(parts)
    ad_band_parent = ','.join(parts[1:]) if band else ''

    return {
        'ad_ou':           ad_ou,
        'ad_band_ou_name': band,
        'ad_band_parent':  ad_band_parent,
    }


# ---------------------------------------------------------------------------
# OU path derivation — computers
# ---------------------------------------------------------------------------

def _computer_ou_path(role, site_code, base_dn, sites_by_code):
    """
    Derive the AD OU DN for a computer from its Role and Site code.
    Returns an empty string if the site code is unknown.
    """
    sub_ou = ROLE_TO_SUB_OU.get(role, 'Infrastructure')

    site = sites_by_code.get(site_code)
    if not site:
        print(f'WARNING: unknown site code {site_code!r} (role={role}) — ad_ou left blank',
              file=sys.stderr)
        return ''

    city           = site.get('City', '')
    province       = site.get('Province', '')
    country        = site.get('Country', '')
    ansible_region = site.get('AnsibleRegion', '')

    if ansible_region == 'cloud_site':
        return f'OU={sub_ou},OU=Devices,OU=Cloud Infrastructure,OU=Sites,{base_dn}'

    continent = REGION_CONTINENT.get(ansible_region, 'Europe')

    parts = [f'OU={sub_ou}', 'OU=Devices', f'OU={city}']
    if province:
        parts.append(f'OU={province}')
    parts.extend([f'OU={country}', f'OU={continent}', 'OU=Sites', base_dn])

    return ','.join(parts)


# ---------------------------------------------------------------------------
# Per-section line parsers
# ---------------------------------------------------------------------------

def _parse_group(line, domain, email_domain):
    t = line.strip().rstrip(', ;')
    if not (t.startswith('@{') and t.endswith('}')):
        return None
    name = _str(t, 'Name')
    if not name:
        return None
    return {
        'Name':        name,
        'Description': _str(t, 'Description') or '',
        'Type':        _str(t, 'Type')        or 'Security',
        'Scope':       _str(t, 'Scope')       or 'Global',
        'ManagedBy':   _str(t, 'ManagedBy')   or '',
        'Email':       _sub_email(_str(t, 'Email') or '', email_domain),
    }


def _parse_user(line, domain, email_domain, base_dn):
    t = line.strip().rstrip(', ;')
    if not (t.startswith('@{') and t.endswith('}')):
        return None
    name = _str(t, 'Name')
    sam  = _str(t, 'SamAccountName')
    if not name or not sam:
        return None
    if sam == 'template.users':
        return None

    ou_info = _user_ou_path(_arr(t, 'OU'), base_dn)
    if ou_info is None:
        return None  # non-standard root — skip

    country_raw = _str(t, 'Country') or ''

    return {
        'Name':                      name,
        'SamAccountName':            sam,
        'UserPrincipalName':         _sub_email(_str(t, 'UserPrincipalName') or '', email_domain),
        'Groups':                    _arr(t, 'Groups'),
        'Title':                     _str(t, 'Title')                     or '',
        'Email':                     _sub_email(_str(t, 'Email') or '', email_domain),
        'Country':                   country_raw,
        'CountryCode':               _COUNTRY_ISO.get(country_raw, country_raw),
        'Manager':                   _str(t, 'Manager')                   or '',
        'Disabled':                  _bool(t, 'Disabled')                 or False,
        'Locked':                    _bool(t, 'Locked')                   or False,
        'MustChangePassword':        _bool(t, 'MustChangePassword')       or False,
        'Department':                _str(t, 'Department')                or '',
        'Company':                   _str(t, 'Company')                   or '',
        'Description':               _str(t, 'Description')               or '',
        'telephoneNumber':           _str(t, 'telephoneNumber')           or '',
        'mobile':                    _str(t, 'mobile')                    or '',
        'Street':                    _str(t, 'Street')                    or '',
        'City':                      _str(t, 'City')                      or '',
        'PostalCode':                _str(t, 'PostalCode')                or '',
        'physicalDeliveryOfficeName': _str(t, 'physicalDeliveryOfficeName') or '',
        'ad_ou':                     ou_info['ad_ou'],
        'ad_band_ou_name':           ou_info['ad_band_ou_name'],
        'ad_band_parent':            ou_info['ad_band_parent'],
    }


def _parse_computer(line, domain, base_dn, sites_by_code):
    t = line.strip().rstrip(', ;')
    if not (t.startswith('@{') and t.endswith('}')):
        return None
    name = _str(t, 'Name')
    if not name:
        return None

    role = _str(t, 'Role') or ''
    site = _str(t, 'Site') or ''

    return {
        'Name':                   name,
        'SamAccountName':         _str(t, 'SamAccountName') or (name + '$'),
        'Role':                   role,
        'Site':                   site,
        'Description':            _str(t, 'Description')            or '',
        'Enabled':                _bool(t, 'Enabled'),
        'DNSHostName':            _sub_dns(_str(t, 'DNSHostName') or '', domain),
        'OS':                     _str(t, 'OS')                     or '',
        'OperatingSystemVersion': _str(t, 'OperatingSystemVersion') or '',
        'IPv4Address':            _str(t, 'IPv4Address')            or '',
        'ad_ou':                  _computer_ou_path(role, site, base_dn, sites_by_code),
        'ad_device_sub_ou':       ROLE_TO_SUB_OU.get(role, 'Infrastructure'),
    }


# ---------------------------------------------------------------------------
# Sites CSV loader
# ---------------------------------------------------------------------------

def _load_sites(csv_path):
    """Return {SiteCode: row_dict} from sites.csv, or {} on failure."""
    if not csv_path:
        return {}
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            return {row['Site']: row for row in csv.DictReader(f)}
    except FileNotFoundError:
        print(f'WARNING: sites.csv not found: {csv_path}', file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _default_domain(script_dir: Path) -> str:
    """Read domain_fqdn from ad_forest.json (single source of truth, co-located
    with this script in benarbejde/), rather than a hardcoded literal here that
    could silently drift from it. Falls back to 'jukebox.internal' only if the
    file is genuinely missing -- it always ships alongside this script."""
    forest_json = script_dir / 'ad_forest.json'
    try:
        with open(forest_json, encoding='utf-8') as f:
            return json.load(f)['domain_fqdn']
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        print(f'WARNING: could not read domain_fqdn from {forest_json} ({exc}) '
              f'-- falling back to jukebox.internal', file=sys.stderr)
        return 'jukebox.internal'


def main():
    script_dir = Path(__file__).resolve().parent

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--section',      required=True, choices=['users', 'groups', 'computers'])
    ap.add_argument('--tdf',          default=str(script_dir / 'jukebox.example.tdf'),
                    help='Path to jukebox.example.tdf (default: co-located with this script, '
                         'benarbejde/jukebox.example.tdf -- NOT /etc/example-music, this file is '
                         'never deployed there, see the module docstring)')
    ap.add_argument('--domain',       default=_default_domain(script_dir),
                    help='AD internal domain for DNS hostname rewriting (default: read from '
                         'ad_forest.json\'s domain_fqdn, the single source of truth)')
    ap.add_argument('--email-domain', default='',
                    help='Email/UPN domain for @example.* substitution (default: same as --domain)')
    ap.add_argument('--sites-csv',    default=str(script_dir / 'sites.csv'),
                    help='Path to sites.csv for computer OU derivation (default: co-located with '
                         'this script, benarbejde/sites.csv)')
    ap.add_argument('--out',          default=None, type=Path,
                    help='Write output here instead of stdout (default: print to stdout, as before)')
    args = ap.parse_args()

    email_domain  = args.email_domain or args.domain

    try:
        with open(args.tdf, encoding='utf-8') as f:
            all_lines = f.readlines()
    except FileNotFoundError:
        print(f'ERROR: TDF not found: {args.tdf}', file=sys.stderr)
        sys.exit(1)

    base_dn       = 'DC=' + ',DC='.join(args.domain.split('.'))
    sites_by_code = _load_sites(args.sites_csv)

    results = []

    if args.section == 'groups':
        for line in _extract_section_lines(all_lines, 'rawDemoGroups'):
            obj = _parse_group(line, args.domain, email_domain)
            if obj:
                results.append(obj)

    elif args.section == 'users':
        for line in _extract_section_lines(all_lines, 'rawUsers'):
            obj = _parse_user(line, args.domain, email_domain, base_dn)
            if obj:
                results.append(obj)

    elif args.section == 'computers':
        for line in _extract_section_lines(all_lines, 'rawComputers'):
            obj = _parse_computer(line, args.domain, base_dn, sites_by_code)
            if obj:
                results.append(obj)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print(f'Wrote {args.out}', file=sys.stderr)
    else:
        json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
        print()


if __name__ == '__main__':
    main()
