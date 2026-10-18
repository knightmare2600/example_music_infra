# Procedure: Domain Rename — Propagating a New AD Domain Through the Estate

**Doc ID:** NET-AD-RENAME-001
**Scope:** Propagating a new `domain_fqdn`/`netbios_name` through every file, script, and
host in the estate that references it.
**Applies to:** A domain that has **already been built live** under its new name — this
procedure does **not** rename or rebuild Active Directory itself.
**Who can run this:** A junior engineer may run Steps 1–7 below, but **Step 0 must be
confirmed by a senior engineer first, in writing, before starting**, and a senior engineer
must review the diff and harness output before anything in Step 8 is committed/pushed.

---

## Step 0 — STOP. Confirm the live forest already exists. (Senior sign-off required)

**This document does not create, rename, or rebuild the Active Directory forest.** It
propagates a domain name that is **already real and live** through this repo's own data
and configuration, so the estate's tooling matches reality. If the live forest has not
already been rebuilt/promoted under the new name, running this procedure will make every
file in the repo correctly describe a domain that doesn't exist yet — which is worse than
doing nothing, because it will look finished.

Renaming a live AD forest in place (Microsoft's `rendom` procedure) is high-risk and rarely
done; the realistic path in this estate is building fresh DC(s) under the new name and
decommissioning the old ones — a separate, senior-engineer-only operation using
`windows_dc`'s own playbooks, not covered here.

**Before continuing, a senior engineer must explicitly confirm, in writing (ticket/chat,
not verbally):**
- [ ] The new domain is already a real, live, promoted AD forest, reachable from the
      estate.
- [ ] You have been told the exact new `domain_fqdn` (and `netbios_name`, if it's
      changing too) to use below — don't infer or guess it.
- [ ] You have been told whether this is a full cutover (old domain gone) or a transition
      period (both old and new domains briefly coexist) — the steps below assume a full
      cutover; if it's a transition, stop and ask, this procedure doesn't cover that case.

If any box above isn't checked, **stop here** and go get it checked. Don't proceed on
an assumption.

---

## Step 1 — Edit `benarbejde/ad_forest.json`

This is the **only file in the whole procedure you edit by hand.** Every other file
listed below is either generated from it or reads it live — editing them directly instead
of this file is the mistake this doc exists to prevent.

```bash
vim benarbejde/ad_forest.json
```

Change `domain_fqdn` (and `netbios_name`, if Step 0 said it's changing too). Leave
every other field (`forest_mode`, `domain_mode`, `hub_sites`, `cld_site`,
`dns_forwarders`) alone unless Step 0 specifically told you otherwise — this procedure is
about the domain name, not the forest topology.

**Check it parses before moving on:**

```bash
python3 -c "import json; print(json.load(open('benarbejde/ad_forest.json')))"
```

If that errors, you've broken the JSON (a missing comma is the usual culprit) — fix it
before continuing.

---

## Step 2 — Regenerate everything derived from it

```bash
python3 benarbejde/regenerate_all.py --verify
```

This one command regenerates every file that bakes `domain_fqdn` in at generation time
rather than reading it live — most importantly `benarbejde/begyndelse.json` and
`ansible/configs/inventory/group_vars/all/site_services.yml`. **Don't skip this step
thinking the next steps will pick the new value up on their own — they read these
generated files, not `ad_forest.json` directly, and those files do not update
themselves.**

`--verify` also runs the full harness at the end automatically. Expect to see
`Checked ad_forest.json's domain_fqdn (...)` near the bottom of the output, followed by
`No domain inconsistencies found across any enumerated file.` **If you see anything red,
stop here and work through it before continuing — don't proceed past a failing harness.**

---

## Step 3 — Regenerate the AD users/groups data

```bash
python3 benarbejde/merge_ad_users.py
```

Rewrites `benarbejde/ad_users.json`/`ad_groups.json` with the new domain baked into
every `UserPrincipalName`/`Email` field. **Never** run anything in
`benarbejde/archive/` for this — `parse_tdf.py` is retired (2026-10-18) and would
silently discard real data if it were ever run again; see its own header if you want the
full reasoning, but the short version is: don't go in there.

`ad_computers.json` does **not** need regenerating for this specifically —
`benarbejde/merge_ad_computers.py` already derives `DNSHostName`'s domain suffix live
from `ad_forest.json`, so it's only worth re-running if you've also got an unrelated
`devices.csv` change to pick up at the same time.

---

## Step 4 — Regenerate the Proxmox inventory audit data

```bash
python3 bootstrap/web/proxmox/site-inventory-audit.py --generate-hosts
python3 bootstrap/web/proxmox/site-inventory-audit.py --generate-inventory
```

---

## Step 5 — Re-run the per-service provisioning scripts

These read `begyndelse.json` live (now correctly regenerated in Step 2) and bake the
domain into their own generated output. Run each **on the host it provisions**, not from
your own checkout:

- `bootstrap/web/provision/firewallme.sh`
- `bootstrap/web/provision/bindme.sh` — also bakes the value into `bind-aliases.sh`,
  `regen-zone.sh`, and its own dynamic MOTD; re-running it refreshes all three, don't
  hand-edit those files directly.
- `bootstrap/web/provision/rudderme.sh`

If you're not sure which hosts these apply to, **ask — don't guess which boxes to touch.**

---

## Step 6 — Push the refreshed data out to every host that keeps its own copy

Several hosts (every firewall, every Proxmox node, among others) keep their **own
separate deployed copy** of `benarbejde/*` at `/etc/example-music/*`, and nothing
refreshes that automatically just because the repo changed. See
[refresh-after-data-changes.md](../refresh-after-data-changes.md) for the full detail —
the short version for this procedure:

```bash
ansible-playbook playbooks/linux/tools.yml --limit all
```

This is the **only** playbook that deploys `benarbejde/*` to every managed host's own
`/etc/example-music/*`. Skipping this step is how a host ends up quietly still
referencing the old domain weeks later, discovered only when something on that specific
box breaks — this has happened before (see `refresh-after-data-changes.md`'s own incident
history), don't repeat it.

---

## Step 7 — Final verification (run this even though Step 2 already ran it once)

```bash
bash at_have_ryggen_fri/run.sh
```

Steps 3–6 happened after Step 2's own harness run, so re-run it now to confirm nothing
in those later steps introduced something new. **Expect zero new failures compared to
before you started** — check the "Summary" block at the end against what you saw before
Step 0. If anything is red that wasn't red before you started, stop and investigate before
touching git.

---

## Step 8 — Commit, get Malcolm to review, then push

```bash
git status
git diff
```

**Stop here and get a senior engineer (Malcolm) to actually read the diff and the Step 7
harness output before you commit anything.** This changes data that every build,
provisioning script, and AD operation in the estate depends on — a second pair of eyes
before it goes in is not optional for this one.

Once reviewed:

```bash
git add benarbejde/ad_forest.json benarbejde/begyndelse.json benarbejde/ad_users.json \
        benarbejde/ad_groups.json ansible/configs/inventory/group_vars/all/site_services.yml \
        ansible/configs/inventory/salt/pillar/sites.sls
git commit -m "Domain rename: <old-domain> -> <new-domain>"
git push
```

Committing triggers `.githooks/pre-commit`, which syncs `benarbejde/ad_forest.json` and
`begyndelse.json` to their served copies at `bootstrap/web/proxmox/` automatically — you
don't need a separate step for that.

---

## Known exception, deliberately not migrated

`bootstrap/web/windows/Join-DomainAndBootstrap.ps1` is marked a historical artefact
(superseded by `windows_bootstrap/playbooks/80-domainjoin.yml`) and explicitly must not
be kept in sync — if this script is ever actually run again, it will reference the old
domain; that's accepted, not a bug to fix as part of this procedure.

If you find anything else still hardcoding the old domain that this procedure didn't
cover — a new script, a doc, a config file — flag it to a senior engineer rather than
hand-fixing it yourself; it likely means something needs adding to this list, or to
`at_have_ryggen_fri/check_domain_consistency.py`, not just a one-off edit.

---

## Appendix — Legacy bulk find-and-replace (senior-engineer use only, historical)

**Not part of the normal procedure above — do not use this unless a senior engineer
specifically directs you to, for a file this document's main procedure genuinely doesn't
cover.** This is the original, one-time method from the historical `jukebox.example` →
`jukebox.internal` rename (forced by `.example` being an RFC 2606-reserved TLD Windows
DNS rejects), kept here only as a fallback for a file outside the generated/live-read set
above — documentation prose, a stray one-off file, etc.

### Context

Active Directory forest names must use a TLD Windows DNS can host as a zone. RFC 2606
reserves `.example`, `.test`, `.invalid`, and `.localhost` — Windows DNS rejects these as
zone names with `ERROR_INVALID_NAME (Win32 123)`.

### Pre-flight dry run

```powershell
Get-ChildItem -Path "." -Recurse -File |
    Where-Object { $_.Extension -notin @(".exe",".dll",".sys",".bin",".iso",".img",".zip",".7z",".msi",".msu") } |
    Where-Object { Select-String -Path $_.FullName -Pattern "OLD_DOMAIN_REGEX" -Quiet 2>$null } |
    Select-Object FullName
```

Review the output carefully, especially `.ps1`/`.bat`/`.cmd` files — a domain string may
appear in a context beyond a simple name swap (hardcoded FQDNs, credentials, UPN
suffixes).

### Perform the replace

```powershell
Get-ChildItem -Path "." -Recurse -File |
    Where-Object { $_.Extension -notin @(".exe",".dll",".sys",".bin",".iso",".img",".zip",".7z",".msi",".msu") } |
    Where-Object { Select-String -Path $_.FullName -Pattern "OLD_DOMAIN_REGEX" -Quiet 2>$null } |
    ForEach-Object {
        (Get-Content $_.FullName) -replace "OLD_DOMAIN_REGEX", "NEW_DOMAIN" | Set-Content $_.FullName -Encoding UTF8
    }
```

### Linux/macOS equivalent

```bash
grep -r "OLD_DOMAIN_REGEX" . --include="*" -l
find . -type f ! -name "*.exe" ! -name "*.bin" ! -name "*.iso" | \
    xargs sed -i 's/OLD_DOMAIN_REGEX/NEW_DOMAIN/g'
```

### Notes

- **Regex escaping** — `.` must be escaped as `\.` to match a literal dot, or
  `jukebox.example` would also match `jukeboxXexample`.
- **Binary files** — excluded above; if any tooling embeds the domain in a compiled
  binary, that must be rebuilt from source separately.
- **`.docx`/`.xlsx`/`.pptx`** — Office Open XML formats are ZIP archives, not matched by
  `Get-Content`; use in-app Find & Replace or the Office COM object instead.
- **Verification** — re-run the dry-run query; it must return no results.

---

## Related Procedures

- [refresh-after-data-changes.md](../refresh-after-data-changes.md) — the general
  `benarbejde/`-change refresh gap this procedure's Step 6 is a specific instance of.
- `buildsheet-domainControllers.md` — DC promotion over WireGuard (the senior-only forest
  build Step 0 above assumes has already happened).
- `bootstrapping.md` — environment bootstrap sequence.
- `ExampleMusic_UPN_DNS_dnsmasq_Procedure.md` — UPN suffix configuration.
