# Build Sheet — Domain Controllers (EXADCS\*001)

**Document ID:** NET-BUILD-DCS-001  
**Classification:** Internal — Network Operations  
**Domain:** `jukebox.internal` (NetBIOS: `JUKEBOX`)  
**Last Updated:** 2026-03-06  
**Signed off by:** ___________________________  Date: ___________

---

## Standard Build Reference

### Unattend XML
Use `autounattend2022.xml` or `autounattend_2022gui.xml` from `C:\DeployTools\unattend_xml\`  

> **Correction (2026-08-03):** the real, current `PostOOBE.cmd` does **not** map a `Z:` drive —
> it runs `Join-DomainAndBootstrap.ps1` directly from a hardcoded UNC path (`\\DC01\deploytools\`),
> no credential env var, no unmap step. Also: `PostOOBE.cmd`'s `\\DC01\deploytools\` and the
> script's own `$DeployToolsShare` (`\\EXADCSCPH001\DeployTools`) are two different, unreconciled
> UNC paths — `DC01` doesn't follow this estate's `EXA*` convention and no `DCS` host is defined
> for `CPH` in `devices.csv`. See `docs/bootstrap/bootstrapping.md` §8.1 for the full detail —
> this whole path is also a historical artefact, superseded by `windows_bootstrap`, not a live
> build procedure any more.

> **Live WinPE step (2026-09-04):** before/during the install, run
> `bootstrap/web/windows/Deploy-OpenSSH.cmd` from WinPE against the target — see that file's own
> header for the full sequence and provisioning-server layout. It downloads the arch-appropriate
> `headlessunattend*.xml`, runs `Sources\Setup.exe /unattend`, injects boot-critical drivers into
> the offline image via DISM, and stages `Detect-Platform.cmd`/`SetupComplete.cmd`/
> `Install-OpenSSH.ps1` so the box comes up OpenSSH-reachable at first boot. For DCs specifically
> this matters more than for a regular server/workstation build — `windows_dc`'s promotion
> playbooks (see Promotion Status below) need SSH reachability to connect at all, so this step
> can't be skipped or deferred the way it might be tempting to on a box you're about to RDP into
> by hand instead.

### Windows Optional Features
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.0.1
```

### Chocolatey Packages (choco install)
```
7zip.install  notepadplusplus.install  hyper  putty.install  winscp.install  far  powershell-core
rustdesk.install  edit  sdelete  wget  busybox  vcredist-all  dotnetfx  windirstat
```

`sysinternals` was removed from this list 2026-08-14 after a live SHA256 checksum-mismatch failure against `EXADCSLAX001` (upstream `download.sysinternals.com` zip updated in place without the Chocolatey package's checksum catching up). Individual Sysinternals tools (ProcExp, ADExplorer, etc.) are instead deployed as committed binaries under `ansible/playbooks/windows_bootstrap/playbooks/files/{x86_64,arm64}/`.

> **RustDesk** is also pre-staged in `C:\DeployTools\utils\` on the WinPE image.  
> Acknowledge at build time that RustDesk is installed and reachable before signing off.

### PowerShell 7 Modules (Install-Module)
```
PSConsoleTools  PSWindowsUpdate  PSWriteColor  PSReadLine  Terminal-Icons  CompletionPredictor  NerdFonts
```

### Nerd Fonts

Not a Chocolatey package — `tasks/fonts.yml` fetches JetBrains Mono Nerd Font directly from its
upstream GitHub release zip (`exa_font_files`, `group_vars/all/vars.yml`) and deploys only the
specific variants listed (Regular/Bold/BoldItalic/Italic/Mono-Regular).

### RSAT / AD Management Tools (Install-WindowsFeature)

Server OS installs RSAT via Server Manager features, not `Add-WindowsCapability` (that mechanism
is for client/workstation OS — see `buildsheet-workstation.md`). DC promotion itself
(`windows_dc/playbooks/10-dc-install-features.yml`) installs:
```
AD-Domain-Services  DNS  GPMC  RSAT-AD-Tools  RSAT-AD-PowerShell  RSAT-DNS-Server
```

### OpenSSH Boot Commands
```powershell
Set-Service -Name sshd -StartupType Automatic
Restart-Service sshd
```

### IP Convention
```
Primary DC   : 192.168.<site-octet>.10
Secondary DC : 192.168.<site-octet>.11  (if applicable)
```

---

## Promotion Status

DC promotion is automated by the `windows_dc` Ansible module — see
**`ansible/playbooks/windows_dc/README.md`** for the full playbook order, usage, and
site-specific replication-source logic. Run from the `ansible/` root:

```bash
ansible-playbook -i configs/inventory playbooks/windows_dc/site.yml \
  -e target=<hostname>
```

The `DC` checkbox below confirms this run completed cleanly (`failed=0`) — including
`30-dc-replicate.yml`'s replication/SYSVOL health check and `40-dc-summary.yml`'s `dcdiag`
report — and that report has been signed off on the DC Promotion Sheet.

> **NET-AD-DC-001** (`docs/active-directory/ad-dc-wireguard-deployment.md`) is a historical,
> manual-PowerShell record of an early promotion (EXADCSODE001, pre-Ansible) — not a live
> procedure. Do not follow it for new builds; it predates `windows_dc` and is left in place for
> forensic reference only. Documented as such 2026-07-15, per the same "historical artefact, not
> a live path" pattern already applied to `PostOOBE.cmd`/`Join-DomainAndBootstrap.ps1` (see
> `docs/bootstrap/bootstrapping.md`).

---

## Build Checklist

> **Columns:** HN = Hostname set correctly · RDP = RDP enabled · SF = OpenSSH feature installed · SB = SSH start on boot · SR = SSH started/restarted · CH = Chocolatey installed · CP = Choco packages installed · P7 = PowerShell 7 installed · PM = PS7 modules installed · DJ = Domain joined (JUKEBOX) · RS = RSAT / AD tools installed · DC = DC promoted (see NET-AD-DC-001) · IP = Static IP set · RD = RustDesk acknowledged

### Scotland

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSFAL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | HEAD OFFICE / PDC EMULATOR / FSMO |
| EXADCSEDI001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCREDI002/003 to be decommissioned |
| EXADCSGLA001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRGLA001 to be decommissioned |
| EXADCSABD001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSCLY001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSDUN001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSPER001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### England

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSLND001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRLND001 to be decommissioned |
| EXADCSBIR001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRBIR001 to be decommissioned |
| EXADCSMCR001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRMCR001 to be decommissioned |
| EXADCSLIV001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRLIV001 to be decommissioned |
| EXADCSNEW001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRNEW001 to be decommissioned |
| EXADCSSHE001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSHUL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSCOV001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSHAL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Danmark

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSCPH001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ORIG DC → SITE DC · DeployTools host |
| EXADCSKGE001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ WS2016 EOL — rebuild priority |
| EXADCSFAX001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSKOR001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSODE001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | EU HUB |

### Deutschland

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSBON001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | SCHEMA MASTER / DOMAIN NAMING MASTER |
| EXADCSBER001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCSBRD001 in inventory |
| EXADCSMUN001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Sverige / Norge / Nederland / Italia / Österreich

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSGOT001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Gothenburg |
| EXADCSOSL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Oslo |
| EXADCSAMS001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Amsterdam |
| EXADCSMIL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Milan |
| EXADCSVIE001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Vienna |

### Canada

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSBRK001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | NA / APAC HUB |
| EXADCSTOR001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Toronto |
| EXADCSMTL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Montréal |

### USA

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSNYC001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | New York |
| EXADCSLAX001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Los Angeles |
| EXADCSMIA001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Miami — PENDING BUILD |
| EXADCSNJC001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | New Jersey |
| EXADCSCHI001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Chicago |
| EXADCSATL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Atlanta |

### Australia / New Zealand

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSSYD001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Sydney |
| EXADCSMEL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Melbourne |
| EXADCSAKL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Auckland |

---

## DC Promotion Sheet

Attach or staple the `windows_dc/site.yml` run's final play recap and `40-dc-summary.yml`
`dcdiag` output for each node once promoted. The `DC` checkbox above is not ticked until
that report is complete and signed off.

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

## Appendix A — Legacy Hostnames & Known Naming Inconsistencies

> **Action for build engineer:** When you encounter any of the hostnames or naming patterns below,  
> update the relevant record to use the canonical convention and note it in the build log.  
> Do not propagate legacy names into new DNS records, AD objects, or documentation.

### DCR → DCS (Legacy Regional DCs — Rebuild in Progress)

> **Table below is a stale, incomplete snapshot (found 2026-08-03) — only 8 sites listed.**
> `at_have_ryggen_fri/run.sh` section 29 (`check_dcr_devices.py`) is the live, authoritative
> source: it found **38 real `EXADCR*` devices across ~30 sites** the same session this note
> was added — CPH (x2), ODE (x2), TOR (x2), KGE, FAX, KOR, AAR, BON, BER, MEL, SYD, AKL, DUN,
> PER, ABD, CLY (x2), HAL, HUL, SHE, LAX, NYC, BRK, FAL (x2), and more, on top of the 8 below.
> Run that check for the current, complete list and each device's real notes/status rather than
> trusting this table as exhaustive — it was not kept in sync as new sites' legacy DCR devices
> were discovered in `devices.csv`.

The following DCs exist under the legacy `EXADCR*` naming scheme. They are functional but  
will be replaced by new `EXADCS*` builds as part of this rollout. Until decommissioned,  
the legacy nodes should remain in service. Do **not** demote them until the new DCS node  
for that site is promoted, replicated, and signed off.

| Legacy Hostname | Site | Canonical Replacement | Status |
|----------------|------|-----------------------|--------|
| `EXADCRGLA001` | GLA | `EXADCSGLA001` | Pending rebuild |
| `EXADCREDI002` | EDI | `EXADCSEDI001` | DC secondary needs rebuild (`.12`) |
| `EXADCREDI003` | EDI | `EXADCSEDI001` | Decommission pending (`.13`) |
| `EXADCRLND001` | LND | `EXADCSLND001` | Pending rebuild |
| `EXADCRMCR001` | MCR | `EXADCSMCR001` | Pending rebuild |
| `EXADCRLIV001` | LIV | `EXADCSLIV001` | Pending rebuild |
| `EXADCRNEW001` | NEW | `EXADCSNEW001` | Pending rebuild |
| `EXADCRBIR001` | BIR | `EXADCSBIR001` | Pending rebuild |

### BRD → BER (West Berlin Site Code Correction)

The network inventory currently records the West Berlin site as `BRD` in some places.  
`BER` is canonical. The inventory will be updated as part of the next full review.

| Legacy / Incorrect | Canonical | Affected hostnames |
|--------------------|-----------|-------------------|
| `EXADCSBRD001` | `EXADCSBER001` | Update DNS, AD site object, inventory |
| `BRD` site code | `BER` | Update any references in site-inventory.md, network-inventory.md |

### SVR vs SRV — SVR Is Current, SRV Is Legacy

Corrected 2026-08-04 (Robert's call) — two earlier versions of this section both got the
direction wrong, in opposite ways: an original version said `EXASVR*` was legacy and should
be renamed to `EXASRV*`; a 2026-08-03 correction of that then over-corrected to say neither
was legacy, that both were permanently coexisting codes. Repo history (`docs/proxmox/pve-create-vm.md`'s
own 2026-03-03 changelog, and commit `b00b376`) showed the *original* intent had actually
been the reverse of both — `SRV` current, `SVR` legacy — but with no way to settle which of
the three conflicting accounts reflected reality, Robert made the definitive call: **`SVR` is
the current code, `SRV` is retired.**

Every real device that used to carry `EXASRV*` has been renamed to `EXASVR*` in `devices.csv`,
`ad_computers.json`, and `role_codes.csv` (2026-08-04): `EXASVRFAL001` (reserved slot),
`EXASVRCLY001`, `EXASVRBIR001`, `EXASVRBRD001`, `EXASVRLAX001`, `EXASVRSYD001`,
`EXASVRMEL001`, `EXASVRAKL001` — joining the two devices that were already correctly `SVR`,
`EXASVRCLD002` (Windows Admin Centre) and `EXASVRLIV001` (LIV file server). `SRV` remains
defined in `role_codes.csv` as a legacy alias only, for reading old references — no current
`devices.csv` row uses it. See `network-inventory.md`'s Naming Convention Reference table for
the current worked example.

---

*Internal Use Only — Network Engineering*
