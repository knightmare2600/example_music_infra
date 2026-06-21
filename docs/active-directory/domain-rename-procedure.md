# Procedure: Bulk Domain Name Replace After AD Forest Rebuild

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
