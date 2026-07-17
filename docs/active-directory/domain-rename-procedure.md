# Procedure: Bulk Domain Name Replace After AD Forest Rebuild

## Preferred method (2026-07-17): `benarbejde/ad_forest.json` is the single source of truth

This document originally described only the bulk find-and-replace below, from the one-time
historical `jukebox.example` → `jukebox.internal` rename (forced by `.example` being an
RFC 2606-reserved TLD Windows DNS rejects). Since 2026-07-09, `benarbejde/ad_forest.json`
exists specifically so a **future** domain rename does not require that bulk-replace sweep at
all — it is the single source of truth for `domain_fqdn`, `netbios_name`, `forest_mode`,
`domain_mode`, `hub_sites`, `cld_site`, and `dns_forwarders`.

**To rename the domain today:**

1. Edit `benarbejde/ad_forest.json` — change `domain_fqdn` (and `netbios_name` if it should
   change too). That is the only file that should need a manual edit.
2. Everything below reads that file directly, or via its deployed/mirrored form
   (`begyndelse.json`, or the pre-commit-synced copy at `bootstrap/web/proxmox/ad_forest.json`)
   — no further editing needed, just re-run/re-deploy each:
   - `ansible/configs/inventory/group_vars/all/vars.yml` (`exa_domain`), `group_vars/windows_dc/vars.yml`
     (`ad_domain_name`, `ad_netbios_name`, `dc_hub_sites`, `dc_cld_site`, `dc_dns_forwarders`),
     `group_vars/rudder_servers/main.yml` (`rudder_domain` + its 3 LDAP DNs) — all Jinja lookups,
     take effect on next Ansible run.
   - `bootstrap/web/provision/firewallme.sh`, `bindme.sh`, `rudderme.sh` — read `begyndelse.json`
     live at script-run time via `jq`; re-run the script to pick up the new value. Note
     `bindme.sh` bakes the value into a handful of generated files (`bind-aliases.sh`,
     `regen-zone.sh`, the dynamic MOTD) at write time — re-run `bindme.sh` itself to refresh
     those, rather than editing them by hand.
   - `benarbejde/parse_tdf.py` — `--domain`'s default now reads `ad_forest.json` directly
     (co-located in `benarbejde/`); re-run it to regenerate `ad_users.json`/`ad_groups.json`/
     `ad_computers.json` with the new domain baked into every record (those are generated
     data dumps — the old per-record values do not update themselves).
   - `bootstrap/web/proxmox/site-inventory-audit.py` — reads the pre-commit-synced copy of
     `ad_forest.json` alongside itself; re-run `--generate-hosts`/`--generate-inventory` to
     regenerate.
3. **Known exception, deliberately not migrated**: `bootstrap/web/windows/Join-DomainAndBootstrap.ps1`
   is marked a historical artefact (superseded by `windows_bootstrap/playbooks/80-domainjoin.yml`)
   and explicitly must not be kept in sync — if this script is ever actually run again, use the
   bulk-replace procedure below on it specifically, or accept it will reference the old domain.
4. If anything is found still hardcoding the domain independently of `ad_forest.json` (a new
   script, a doc, a config file this list doesn't cover), the bulk-replace procedure below is
   still the right fallback for that specific file — it isn't retired, just no longer the
   primary method for everything this list already covers.

---

## Legacy method: bulk find-and-replace

The rest of this document is the original historical procedure, kept for anything not covered
above (documentation prose, one-off files, or a future exception like the one in step 3).

## Context

When rebuilding an Active Directory forest with a corrected domain name, all documentation,
scripts, and config files referencing the old domain name must be updated. This procedure
uses PowerShell to perform a safe find-and-replace across all plaintext files in a directory tree.

In this instance the change was:

| Old | New |
|-----|-----|
| `jukebox.example` | `jukebox.internal` |

---

## Why This Is Needed

Active Directory forest names must use a TLD that Windows DNS can host as a zone.
RFC 2606 reserves `.example`, `.test`, `.invalid`, and `.localhost` — Windows DNS rejects
these as zone names with `ERROR_INVALID_NAME (Win32 123)`. When a forest is built with
a reserved TLD the DNS zones cannot be created, breaking DC discovery, SRV lookups,
replication, and DC promotion.

The fix is to rebuild the forest with a valid internal TLD such as `.internal`, `.corp`,
or a subdomain of a real owned domain (e.g. `ad.example.com`). After rebuilding, all
references to the old domain name must be updated across the environment.

---

## Pre-Flight: Dry Run

Before changing anything, identify every file containing the old domain name.

### Pass 1 — Known text file extensions

```powershell
Get-ChildItem -Path "." -Recurse -Include "*.txt","*.md","*.cmd","*.bat","*.ps1","*.xml","*.json","*.ini","*.cfg" |
    Where-Object { Select-String -Path $_.FullName -Pattern "jukebox\.example" -Quiet } |
    Select-Object FullName
```

### Pass 2 — All non-binary files (catches .sh, .py, .ipxe, .seed, etc.)

```powershell
Get-ChildItem -Path "." -Recurse -File |
    Where-Object { $_.Extension -notin @(".exe",".dll",".sys",".bin",".iso",".img",".zip",".7z",".msi",".msu") } |
    Where-Object { Select-String -Path $_.FullName -Pattern "jukebox\.example" -Quiet 2>$null } |
    Select-Object FullName
```

Review the output carefully before proceeding. Pay particular attention to `.ps1`, `.bat`,
and `.cmd` files — scripts may reference the domain in contexts beyond a simple name swap
(hardcoded FQDNs, credentials, UPN suffixes).

---

## Perform the Replace

### Pass 1 — Known text file extensions

```powershell
Get-ChildItem -Path "." -Recurse -File -Include "*.txt","*.md","*.cmd","*.bat","*.ps1","*.xml","*.json","*.ini","*.cfg" |
    ForEach-Object {
        (Get-Content $_.FullName) -replace "jukebox\.example", "jukebox.internal" | Set-Content $_.FullName
    }
```

### Pass 2 — All non-binary files

```powershell
Get-ChildItem -Path "." -Recurse -File |
    Where-Object { $_.Extension -notin @(".exe",".dll",".sys",".bin",".iso",".img",".zip",".7z",".msi",".msu") } |
    Where-Object { Select-String -Path $_.FullName -Pattern "jukebox\.example" -Quiet 2>$null } |
    ForEach-Object {
        (Get-Content $_.FullName) -replace "jukebox\.example", "jukebox.internal" | Set-Content $_.FullName
    }
```

---

## Verification

Run the dry-run query again — it must return no results:

```powershell
Get-ChildItem -Path "." -Recurse -File |
    Where-Object { $_.Extension -notin @(".exe",".dll",".sys",".bin",".iso",".img",".zip",".7z",".msi",".msu") } |
    Where-Object { Select-String -Path $_.FullName -Pattern "jukebox\.example" -Quiet 2>$null } |
    Select-Object FullName
```

An empty result confirms the rename is complete.

---

## Notes

**Regex escaping** — the `-replace` operator uses regex. The `.` in the domain name must
be escaped as `\.` to match a literal dot. Without escaping, `jukebox.example` would also
match `jukeboxXexample`.

**Binary files** — `.exe`, `.dll`, `.iso` and similar binary formats are excluded from
the search. If any tooling embeds the domain name in a binary config (e.g. a compiled
installer) those must be rebuilt from source separately.

**`.docx`, `.xlsx`, `.pptx` files** — Office Open XML formats are ZIP archives and will
not be matched by `Get-Content`. If documentation exists in Office format, use
Find & Replace within the application, or script via the Office COM object.

**Encoding** — `Set-Content` defaults to UTF-8 on PowerShell 6+ and system default on
Windows PowerShell 5.1. If files use a specific encoding (e.g. UTF-8 with BOM), specify
explicitly:

```powershell
(Get-Content $_.FullName) -replace "jukebox\.example", "jukebox.internal" |
    Set-Content $_.FullName -Encoding UTF8
```

**Linux/macOS equivalent** — if running this on a Linux host (e.g. for docs in a Git repo):

```bash
# Dry run
grep -r "jukebox\.example" . --include="*" -l

# Replace
find . -type f ! -name "*.exe" ! -name "*.bin" ! -name "*.iso" | \
    xargs sed -i 's/jukebox\.example/jukebox.internal/g'
```

---

## Related Procedures

- `buildsheet-domainControllers.md` — DC promotion over WireGuard
- `bootstrapping.md` — environment bootstrap sequence
- `ExampleMusic_UPN_DNS_dnsmasq_Procedure.md` — UPN suffix configuration
