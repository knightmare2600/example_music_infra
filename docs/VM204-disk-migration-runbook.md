# VM 1023 (EXASVRCLD01) Disk Right-Sizing & PBS Space Crisis — Full Runbook

**Date:** 13 July 2026
**Host:** exapvebru01 (Proxmox VE, ZFS pool `tank`)
**VM:** 1023 — EXASVRCLD01 (Windows Server, Oracle 11g `LOCALDB`, Acuitas/Acuity trading replication)
**PBS target:** backup_nas @ 192.168.0.150 (EXAPBSCLD01)

---

## 1. Background / Why This Happened

VM 1023 was consuming grossly over-provisioned disk space:

- **D: (HDD)** — provisioned as 3584G (3.5TB), actual data only ~321G. Root cause: an engineer had been storing full-size uncompressed DSLR JPEGs (originally shot at high resolution) without any resizing/compression, and the disk had simply never been right-sized to match real usage.
- **E: (TempStaging)** — provisioned as 1TB, actual data only ~9GB.

This bloat had two compounding costs:
1. Wasted space on the `tank` ZFS pool (thin-provisioned, but still carrying large `refreservation` overhead).
2. **PBS backups of VM 1023 were reading/storing terabytes of empty/overhead space every run**, which was the proximate cause of the PBS datastore nearly filling completely (down to ~15GB free) partway through this session.

Goal: shrink D: and E: down to sane sizes matching real usage + headroom, without data loss, without breaking the live Oracle database or the cross-server replication link to EXASVRPEN01, and without leaving PBS in a broken state.

---

## 2. Environment Details Discovered During This Session

- VM 1023 machine type: **`pc-i440fx-10.0`** (NOT q35) — this matters a lot, see Appendix A.
- SCSI controller: `virtio-scsi-single`
- Disks at start:
  - `sata0`: vm-1023-disk-1, 1T (backed E:)
  - `sata1`: vm-1023-disk-2, 50G (backed C:)
  - `sata2`: vm-1023-disk-3, 3584G (backed D:)
  - `sata3`: vm-1023-disk-4, 30G (unused/uninitialized, unrelated legacy disk)
- Storage backend: ZFS pool `tank` (NOT LVM-thin — important, some earlier assumptions in this session were LVM-thin-flavoured and had to be corrected for ZFS semantics)
- Live software discovered running on D:/E: mid-session (**not known to the operator beforehand**):
  - **Oracle 11g Database**, SID `LOCALDB`, ORACLE_HOME `D:\Oracle\product\11.2.0\dbhome_1`
  - **Acuitas/Acuity** trading/replication software (`D:\Acuity\Server\AcuitasServer.exe`, DCOM-activated, `-Embedding` flag)
  - **OCP** (`OCPDaemon`, `OCPService`, `OCPClient.exe`) — proper Windows services
  - **CIRAReplication.exe / Replication.exe** — active replication client connecting FROM `EXASVRPEN01` (192.168.0.254) into this Oracle instance every ~5-15 minutes

This discovery **significantly changed the risk profile** mid-task and forced a pause until an agreed maintenance window (17:10) could be arranged.

---

## 3. Pre-Work: Investigating TRIM/Optimize-Volume (Windows guest disk reclaim)

Original ask: run something Proxmox-equivalent to `fstrim` across all VMs/disks.

### Linux path (for context, not used on 1023 which is Windows)
```bash
qm guest cmd <vmid> fstrim-all
```

### Windows path (used throughout this session)
```powershell
Optimize-Volume -DriveLetter <X> -ReTrim -Verbose
```
Or for every mounted volume in one pass:
```powershell
Get-Volume | Where-Object {$_.DriveLetter} | ForEach-Object { Optimize-Volume -DriveLetter $_.DriveLetter -ReTrim -Verbose }
```

**Key clarification established:** `sdelete -z` (writing zeros to free space) was the old VMware/ESXi-era workaround for hypervisors with no live TRIM/UNMAP passthrough. On Proxmox with `discard=on` set on the virtio-scsi/sata controller, **live TRIM/UNMAP passthrough works natively** — no zero-write step needed, no ballooning risk, no risk to PBS deduplication (PBS dedupes zero/empty blocks near-perfectly regardless).

**Prerequisite for TRIM to actually reach the storage layer:** `discard=on` must be set on the VM's virtual disk config, e.g.:
```bash
qm set <vmid> -scsi0 <storage>:vm-<vmid>-disk-0,discard=on
```
Without this, TRIM commands succeed in the guest but are silently dropped — no space is reclaimed.

**Example real output from this session (VM 1023, before migration), confirming TRIM alone reclaimed multiple TB without any resize:**
```
Invoking retrim on TempStaging (E:)...
 Volume size = 1023.98 GB, Used space = 8.71 GB, Free space = 1015.26 GB
 Total space trimmed = 1011.77 GB
Invoking retrim on (C:)...
 Total space trimmed = 10.43 GB
Invoking retrim on HDD (D:)...
 Volume size = 3.49 TB, Used space = 335.14 GB, Free space = 3.17 TB
 Total space trimmed = 3.16 TB
```

This confirmed TRIM was working correctly, but also confirmed the disks were still nominally oversized — TRIM reclaims **allocated-but-unused blocks at the storage layer**, it does not shrink the **partition/zvol size** itself. That's a separate, manual process (this runbook).

---

## 4. Understanding ZFS zvol Sizing Quirks (discovered mid-session)

Checking `zfs list` immediately after trims showed `USED` figures that looked wrong (e.g. `3.87T` used on a disk with only 321G of real data). Root cause:

```bash
zfs get volsize,refreservation,used,referenced tank/vm-1023-disk-3
```
```
NAME                PROPERTY        VALUE      SOURCE
tank/vm-1023-disk-3  volsize         3.50T      local
tank/vm-1023-disk-3  refreservation  3.87T      local
tank/vm-1023-disk-3  used            3.87T      -
tank/vm-1023-disk-3  referenced      321G       -
```

**Lesson:** `used` on a zvol reflects `refreservation` (a safety-margin reservation set above `volsize` for metadata/slop), NOT real consumption. **`referenced` is the number that reflects real data on disk.** Any monitoring/Zabbix checks built against zvol usage should key off `referenced`, not `used`.

`refreservation` only blocks *other* datasets on the pool from using that space — it does not inflate `zpool list`'s actual `ALLOC` figure. So `zpool list` showing low usage and `zfs list` showing a huge `used` figure on one zvol are not contradictory; they're measuring different things.

---

## 5. Disk Migration Procedure (as actually executed, including corrections)

### 5.1 Mistake #1 — sizing syntax trap (early in session)

Attempted:
```bash
qm set 1023 -sata4 tank:32,size=500G,discard=on
```
**Result:** created a 32GB disk, not 500GB. The `tank:32` shorthand IS the size specifier in GB — the trailing `size=500G` is ignored/overridden.

**Correct syntax:**
```bash
qm set 1023 -sata4 tank:500,discard=on
```
(plain number after the colon = size in GB; no separate `size=` needed when creating new)

**Cleanup required:** the mistaken 32G disk had to be deleted:
```bash
qm set 1023 -delete sata4
```

### 5.2 Mistake #2 — SATA hotplug does not work on `pc-i440fx` machine type

After creating a disk on `sata4` while the VM was running, it never appeared in Windows even after:
```powershell
Update-HostStorageCache
```
or `diskpart` → `rescan`.

**Root cause:** SATA hot-add/hot-remove is only supported on Proxmox's **q35** machine type. On **i440fx** (this VM's type — confirmed via `qm config 1023 | grep machine` → `pc-i440fx-10.0`), SATA devices are enumerated only at QEMU process start. Adding/removing a SATA disk on a running i440fx VM updates the Proxmox config but has **no effect on the running guest** until a full `qm stop`/`qm start` (not a reboot — QEMU itself must restart).

**Fix used:** since the VM was already on `virtio-scsi-single` controller, new disks were added via `scsi` bus instead, which DOES hot-add live on i440fx:
```bash
qm set 1023 -delete sata4
qm set 1023 -scsi1 tank:500,discard=on
```
This worked immediately — disk appeared in Windows without any VM restart.

**Implication confirmed later:** the reverse is also true — detaching a SATA disk from a *running* VM does not make it disappear from the guest either; Windows keeps seeing/mounting it (just without a drive letter once reassigned) until the VM is fully stopped and started.

### 5.3 Mistake #3 — orphaned disks after correcting mistake #1/#2

After the sata4→scsi1 correction, `qm config 1023` showed:
```
unused0: tank:vm-1023-disk-5
unused1: tank:vm-1023-disk-6
```
These were the two false-start disks (the 32G mistake, and the briefly-created-then-moved 500G). Confirmed both were genuinely orphaned (not referenced by any bus) and safe to fully delete:
```bash
qm set 1023 -delete unused0
qm set 1023 -delete unused1
```
Verified clean afterward via `qm config 1023 | grep unused` (empty) and `zfs list -r tank | grep vm-1023` (both disk-5 and disk-6 gone).

### 5.4 E: Migration (25GB target) — full working procedure

1. **Check real usage / floor:**
```powershell
Get-Volume -DriveLetter E
Get-PartitionSupportedSize -DriveLetter E
```
Result: SizeMin ≈ 9.4GB (actual usage was ~8.7-9.25GB). Chose **25GB** as target (comfortable headroom).

2. **Confirm nothing actively using the drive:**
```powershell
Get-Process | Where-Object {$_.Path -like "E:\*"}
```
(empty — safe to proceed)

3. **Shrink the partition live (no VM downtime needed for a data volume shrink):**
```powershell
Resize-Partition -DriveLetter E -Size 25GB
```

4. **Hot-add new disk via SCSI (not SATA — see 5.2):**
```bash
qm set 1023 -scsi2 tank:25,discard=on
```

5. **In Windows, bring new disk online, initialize, format:**
```powershell
Get-Disk    # identify new disk number (was Offline, RAW, ~25GB)
Set-Disk -Number <N> -IsOffline $false
Initialize-Disk -Number <N> -PartitionStyle GPT
New-Partition -DiskNumber <N> -UseMaximumSize -DriveLetter Y
Format-Volume -DriveLetter Y -FileSystem NTFS -NewFileSystemLabel "TempStaging25"
```

6. **Robocopy old → new:**
```powershell
robocopy E:\ Y:\ /MIR /COPYALL /DCOPY:DAT /R:2 /W:5 /MT:16 /ETA /LOG:C:\robocopy_E_to_Y.log
```
Result: 77,788/77,788 files, 8.403GB, **0 Failed, 0 Mismatch**. ~1h37m elapsed (mostly directory-walk overhead on ~19.5k dirs), ~5m30s actual transfer.

7. **Verify directory counts match (sanity check for the "2 skipped dirs" robocopy always reports — this is cosmetic, root-dir related, not a real gap):**
```powershell
(Get-ChildItem E:\ -Recurse -Directory).Count
(Get-ChildItem Y:\ -Recurse -Directory).Count
```
Both returned 19528 — clean match.

8. **Delta pass (catch anything changed since first pass) — safe to do since nothing was using E:\:**
```powershell
robocopy E:\ Y:\ /MIR /COPYALL /DCOPY:DAT /R:2 /W:5 /MT:16 /ETA /LOG:C:\robocopy_E_to_Y_delta.log
```

9. **Drive letter swap — MISTAKE #4 here, see below, then corrected:**

**What was tried first (wrong — used a broad pipeline instead of explicit partition targeting):**
```powershell
Get-Partition -DriveLetter E | Remove-PartitionAccessPath -AccessPath "E:\"
Get-Partition -DiskNumber 5 | Remove-PartitionAccessPath -AccessPath "Y:\"
Get-Partition -DiskNumber 5 | Set-Partition -NewDriveLetter E
```
**Errors received:**
```
Remove-PartitionAccessPath : The access path is not valid.
Set-Partition : The requested access path is already in use.
```
**Root cause:** `Get-Partition -DiskNumber 5` (with no `-PartitionNumber`) returned ALL partitions on that disk, including the tiny Microsoft Reserved (MSR) partition (Partition 1). The pipeline hit the MSR partition too, and Windows' automount grabbed the freshly-vacated `E:` letter and assigned it to the MSR partition (a partition with no filesystem) rather than the real NTFS volume (Partition 2), due to a brief automount race.

**Diagnosis commands used:**
```powershell
Get-Partition -DiskNumber 5
Get-Volume
```

**Correct fix — target partitions explicitly by number:**
```powershell
Get-Partition -DiskNumber 5 -PartitionNumber 1 | Remove-PartitionAccessPath -AccessPath "E:\"
Get-Partition -DiskNumber 5 -PartitionNumber 2 | Set-Partition -NewDriveLetter E
```
Verified clean afterward via `Get-Volume` and `Get-Partition -DiskNumber 5` — `E:` correctly on the 24.98GB NTFS partition, MSR partition unlettered.

**Lesson for next time:** always target `-DiskNumber X -PartitionNumber Y` explicitly for access-path operations. Never pipe a bare `Get-Partition -DiskNumber X` (no partition number) into `Remove-PartitionAccessPath`/`Set-Partition` if the disk has more than one partition (GPT disks always have at least the MSR/system partition alongside the data partition).

10. **Final verification — confirm data is reachable and correct through new letter:**
```powershell
Get-ChildItem E:\ | Select-Object -First 5
(Get-ChildItem E:\ -Recurse -Directory).Count
```
Confirmed 19528 dirs, `Bru_Images` folder visible — correct data via new disk.

11. **Detach old E: disk (sata0) — MISTAKE #5 here (see Appendix B), then handled:**
```bash
qm set 1023 -delete sata0
```
Expected an `unused0:` entry to appear (parked, recoverable). **It did not appear.** See Appendix B for what this meant and how it was resolved (short version: because the VM was still *running* at the time, Proxmox destroys-from-tracking rather than parks; the zvol itself was confirmed still fully intact via `zfs list`, just orphaned rather than shown as `unused`). Re-attach command if ever needed:
```bash
qm set 1023 -sata0 tank:vm-1023-disk-1,discard=on,size=1T
```

### 5.5 D: Migration (500GB target) — full working procedure

This one carried much higher stakes due to the live Oracle database (see Section 6). Steps below assume Section 6's shutdown sequence has already been completed.

1. **Check real usage / floor:**
```powershell
Get-PartitionSupportedSize -DriveLetter D
```
Result: SizeMin ≈ 335GB (actual usage ~321G — floor is close to usage due to NTFS metadata/reserved zones, this is normal). Chose **500GB** as target for headroom.

2. **Shrink partition (done BEFORE the Oracle-discovery pause, while D: was still assumed to be simple data):**
```powershell
Resize-Partition -DriveLetter D -Size 500GB
```

3. **Hot-add new disk via SCSI:**
```bash
qm set 1023 -scsi1 tank:500,discard=on
```

4. **Initialize/format identically to E:'s procedure** (Disk 4, ~500GB, GPT, temp letter `Z:`).

5. **First robocopy pass (full copy, ~305.7GB, took ~24h25m elapsed / ~1h25m actual transfer — see note on /ETA flag below):**
```powershell
robocopy D:\ Z:\ /MIR /COPYALL /DCOPY:DAT /R:2 /W:5 /MT:16 /LOG:C:\robocopy_D_to_Z.log
```
Result: 153,280/153,280 files, 305.700GB, **0 Failed, 0 Mismatch**. "2 skipped" dirs — same cosmetic pattern as E:, confirmed via directory count match (25267 = 25267).

**Note on progress visibility:** robocopy has no native single "percentage progress bar" flag. `/ETA` (estimated time of arrival per file) was settled on as the best available middle-ground between silent and overly chatty. `/NP` should be avoided (removes progress entirely).

**Note on checking async command output (`qm guest exec`):** this pattern was used earlier in the session for running `Optimize-Volume` remotely without RDP:
```bash
qm guest exec <vmid> -- powershell -Command "..."
```
Returns a PID immediately (async). Check status/output with:
```bash
qm guest exec-status <vmid> <pid>
```
`out-data`/`err-data` may be base64-encoded depending on PVE version.

6. **⚠️ MID-TASK DISCOVERY: this volume hosts a live production Oracle database and Acuitas trading replication — see Section 6 before doing anything further with D:.**

7. **Once Section 6's shutdown is complete, delta robocopy pass:**
```powershell
robocopy D:\ Z:\ /MIR /COPYALL /DCOPY:DAT /R:2 /W:5 /MT:16 /ETA /LOG:C:\robocopy_D_to_Z_delta.log
```
Result: only 115 files changed (Oracle datafiles/redo logs/trace files) since first pass, 334.391GB total, **0 Failed, 0 Mismatch**. This is a transactionally-consistent copy because Oracle was fully stopped before this pass ran.

8. **Triple-check disk identities before touching drive letters (learned from the E: MSR mistake — always verify explicitly before any access-path operation):**
```powershell
Get-Disk | Select-Object Number, FriendlyName, PartitionStyle, OperationalStatus, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
Get-Partition | Select-Object DiskNumber, PartitionNumber, DriveLetter, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
Get-Volume | Select-Object DriveLetter, FileSystemLabel, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}, @{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB,2)}}
```
Confirmed: Disk 2 (physical 3584G, partition shrunk to 500G) = old D:. Disk 4 (physical 500G) = new Z:.

9. **Drive letter swap — done correctly this time, explicit partition targeting throughout:**
```powershell
Get-Partition -DiskNumber 2 -PartitionNumber 2 | Remove-PartitionAccessPath -AccessPath "D:\"
Get-Partition -DiskNumber 4 -PartitionNumber 2 | Remove-PartitionAccessPath -AccessPath "Z:\"
Get-Partition -DiskNumber 4 -PartitionNumber 2 | Set-Partition -NewDriveLetter D
```
Verified clean via `Get-Volume` / `Get-Partition -DiskNumber 4` — no errors, no stray letters this time.

10. **Restart Oracle + app layer** — see Section 6.4.

11. **Shutdown VM cleanly, fix boot order, detach old disks** — see Section 6.5.

---

## 6. Live Oracle Database & Acuitas Replication — Discovery and Safe Handling

### 6.1 How it was discovered

While checking what was using the D: volume (before assuming it was safe to touch), routine process checks revealed:
```powershell
Get-Process oracle*, tns* -ErrorAction SilentlyContinue
Get-Service | Where-Object {$_.DisplayName -like "*Oracle*"}
```
showed a live, long-running Oracle instance (94,000+ CPU seconds accumulated) with TNS listener, job scheduler, MTS recovery, and VSS writer services all active — not dormant install files as first assumed.

### 6.2 Establishing what was actually using it (read-only investigation, in order)

```powershell
Get-Service OracleServiceLOCALDB | Select-Object *
netstat -ano | findstr :1521
```
Confirmed all connections were loopback/link-local (same-host only) — nothing external over the network was hitting this DB directly.

```powershell
Get-ChildItem "D:\Oracle\diag\tnslsnr\*\listener\trace\listener.log" -ErrorAction SilentlyContinue
Get-Content "<path found above>" -Tail 50
```
This revealed the actual answer: recurring connections from `EXASVRPEN01` (192.168.0.254) via `D:\Acuity\CIRAReplication\CIRAReplication.exe` and `D:\Acuity\Replication\Replication.exe`, plus local connections from `D:\Acuity\Server\AcuitasServer.exe` and `D:\Acuity\OCP\OCPClient.exe`.

Cross-referencing local PIDs:
```powershell
Get-Process -Id <PID1,PID2,...> | Select-Object Id, ProcessName, Path, StartTime
```
confirmed the local process identities.

**Conclusion: this is live, active, cross-server trading/replication infrastructure (Acuitas/Acuity), not idle files. Decision made to pause the D: migration and schedule a proper window (17:10) rather than proceed live.**

### 6.3 Pre-flight checks before the 17:10 window

Confirmed OS-authenticated sysdba access was available (no separate Oracle password needed):
```powershell
net localgroup ORA_DBA
whoami
```
The logged-in account (`corp\example1-adm`) was already a member — sqlplus `/ as sysdba` should have worked without a password. **Notably, `EXASVRPEN01$` (the replication server's own machine account) was also a member of ORA_DBA — confirming the replication link was a deliberately configured, legitimate piece of infrastructure, not ad hoc.**

Confirmed `sqlplus` binary location:
```powershell
where.exe sqlplus
```

### 6.4 The actual shutdown/restart sequence (as executed, including the ORA-12560 detour)

**Step 1 — stop OCP services cleanly:**
```powershell
Stop-Service OCPService -Force
Stop-Service OCPDaemon -Force
```
(Note: `OCPService` returned a "stop failed" error due to `CanStop: False` in its service definition, but `Get-Service` afterward confirmed it had actually stopped anyway — the error was cosmetic, always verify actual state rather than trusting the command's own success/failure signal.)

**Step 2 — stop Acuitas (no service wrapper; these are DCOM `-Embedding` processes, self-managed by the COM runtime, no dedicated stop utility exists):**
```powershell
Get-CimInstance Win32_Process -Filter "Name='AcuitasServer.exe'" | Select-Object ProcessId, CommandLine
Get-Process AcuitasServer | Stop-Process -Confirm:$false
```

**Step 3 — attempted clean SQL*Plus shutdown, hit ORA-12560:**
```powershell
sqlplus / as sysdba
```
```
ERROR:
ORA-12560: TNS:protocol adapter error
```
**Root cause diagnosed:** `$env:ORACLE_HOME` was blank in the PowerShell session (required alongside `ORACLE_SID` for local "bequeath" connections — separate from the TNS listener). Confirmed via:
```powershell
echo $env:ORACLE_HOME
Get-ItemProperty "HKLM:\SOFTWARE\ORACLE\KEY_OraDb11g_home1" | Select-Object ORACLE_HOME, ORACLE_SID
```
**Attempted fix:**
```powershell
$env:ORACLE_HOME = "D:\Oracle\product\11.2.0\dbhome_1"
$env:ORACLE_SID = "LOCALDB"
```
This still did not resolve the login in time — **under time pressure, the decision was made to abandon the clean SQL*Plus shutdown and fall back to stopping the Windows services directly**, which triggers Oracle's internal shutdown/cleanup rather than a raw process kill:

```powershell
Stop-Service OracleOraDb11g_home1TNSListener -Force
Stop-Service OracleServiceLOCALDB -Force
Stop-Service OracleMTSRecoveryService -Force
Stop-Service OracleJobSchedulerLOCALDB -Force
```
`OracleServiceLOCALDB` took ~15+ seconds with repeated "Waiting for service to stop" warnings — normal for a database instance shutting down internally, not a hang.

**Verification all stopped:**
```powershell
Get-Service | Where-Object {$_.DisplayName -like "*Oracle*"}
Get-Process oracle*, tns* -ErrorAction SilentlyContinue
```
All Oracle services `Stopped` (except `OracleVssWriterLOCALDB`, harmless to leave running — doesn't hold datafile handles), no processes remained.

**Step 4 — robocopy delta pass, then drive letter swap (documented in 5.5 above).**

**Step 5 — restart Oracle (services, in reverse order):**
```powershell
$env:ORACLE_HOME = "D:\Oracle\product\11.2.0\dbhome_1"
$env:ORACLE_SID = "LOCALDB"
Start-Service OracleServiceLOCALDB
Start-Service OracleMTSRecoveryService
Start-Service OracleJobSchedulerLOCALDB
Start-Service OracleOraDb11g_home1TNSListener
```

**Step 6 — verify the database actually opened cleanly (not just that the service started):**
```powershell
Get-Content "D:\Oracle\diag\rdbms\localdb\LOCALDB\trace\alert_LOCALDB.log" -Tail 40
```
Confirmed the critical line: `Completed: alter database open` — clean, healthy startup with normal redo thread recovery, no errors.

**Step 7 — restart app layer:**
```powershell
Start-Service OCPDaemon
Start-Service OCPService
```
(Acuitas requires no manual start — it's DCOM-activated on demand.)

**Step 8 — confirm EXASVRPEN01 replication actually resumed (the real proof of success):**
```powershell
Get-Content "D:\Oracle\diag\tnslsnr\EXASVRCLD01\listener\trace\listener.log" -Tail 30 -Wait
```
Confirmed both `CIRAReplication.exe` and `Replication.exe` from `EXASVRPEN01` (192.168.0.254) successfully re-established sessions, no new TNS errors beyond a pre-existing, unrelated ~30-min-interval `TNS-12537`/`TNS-00507` pattern that predates this work.

### 6.5 VM restart for full disk cleanup (SATA limitation revisited)

Because SATA disks can't be hot-removed on `pc-i440fx` (see 5.2), the old E: disk (`sata0`, already detached from config) was still visible in Windows Disk Management until a full VM restart. To fully retire the old D: disk too and clear both from the guest's view:

1. **Stop app layer + Oracle again** (same sequence as 6.4 steps 1-3, this time via clean service stops since Oracle was already known-good and the login issue wasn't revisited under less time pressure — though the ORA-12560 cause, if hit again, is now understood and fixable via the ORACLE_HOME env var fix).

2. **Fix boot order BEFORE deleting sata0** (boot order was `sata0;sata1;scsi1;scsi2` — sata0 was about to be removed, and C: is actually on sata1, not scsi1/scsi2):
```bash
qm set 1023 -boot order=sata1
```

3. **Graceful guest shutdown from host (NOT `qm stop`, which is a hard power-off):**
```bash
qm shutdown 1023
qm status 1023   # wait for "stopped"
```

4. **With VM fully stopped, detach the old disks. This time, because the VM was OFF, deletions correctly parked as `unused` entries (see Appendix B for contrast with the live-VM behaviour):**
```bash
qm set 1023 -delete sata2   # old 3.5TB D: disk → became unused1
qm set 1023 -delete sata3   # unrelated 30GB uninitialized disk → became unused2
```
Verified via:
```bash
qm config 1023 | grep -E '^(sata|scsi|unused)'
zfs list -r tank | grep vm-1023
```
All three retiring disks (`unused0` = old 1TB E:, `unused1` = old 3.5TB D:, `unused2` = old unrelated 30GB) confirmed present as intact, recoverable zvols — nothing destroyed.

5. **Restart VM:**
```bash
qm start 1023
qm status 1023
```

6. **Full post-restart verification (all confirmed good):**
- `Get-Disk` / Explorer showed exactly 3 drives: C:, D: (500GB/164GB free), E: (25GB/16GB free) — old disks fully gone from Windows view now that the guest genuinely restarted
- Oracle auto-started cleanly on boot, `alert_LOCALDB.log` showed `Completed: alter database open` again with no errors
- OCP services running, client connected
- Acuitas dormant (normal — DCOM-activated)
- **EXASVRPEN01 replication reconnected again**, confirmed via listener log (`CIRAReplication.exe` at 18:00:11, `Replication.exe` at 18:02:45, both `establish`, no errors)

7. **Post-cutover TRIM pass (belt-and-braces, confirm no slack left from copy/format):**
```powershell
Get-Volume | Where-Object {$_.DriveLetter} | ForEach-Object { Optimize-Volume -DriveLetter $_.DriveLetter -ReTrim -Verbose }
```

8. **Confirm real ZFS usage on new disks (this is what actually predicts PBS backup size — see Section 7):**
```bash
zfs get volsize,refreservation,used,referenced tank/vm-1023-disk-7   # new D:
zfs get volsize,refreservation,used,referenced tank/vm-1023-disk-5   # new E:
```
Result: `referenced` = 319G (D:) and 9.25G (E:) — both genuinely thin, matching real Windows-reported usage almost exactly. Migration achieved its goal.

---

## 7. PBS Backup Space Crisis (occurred mid-session, same night)

### 7.1 How it was found

While planning the D: migration, a routine question ("will tonight's backup be small now?") led to checking actual PBS datastore headroom:
```bash
pvesm status
```
```
Name              Type     Status     Total (KiB)      Used (KiB) Available (KiB)        %
backup_nas         pbs     active      2129506224      2116621152        12885072   99.39%
```
**Only ~12.9GB free, 99.39% used.** VM 1023's existing PBS backups were each **~4.58 TiB** (matching the old bloated disk sizes) — these were the overwhelming cause.

VM 1023's backup schedule was confirmed via:
```bash
cat /etc/pve/jobs.cfg
```
Two separate jobs existed:
- `backup-def1cc42-0d7f` — **VM 1023 specifically, `mon..fri 00:00`** (i.e. fires tonight at midnight)
- `backup-5074fd14-b517` — VMs 105/106, monthly (unrelated, not a concern tonight)

### 7.2 MISTAKE #6 — attempting a manual test backup without checking space first

```bash
vzdump 1023 --storage backup_nas --mode snapshot --notes-template "post-migration-test"
```
Output showed:
```
INFO: efidisk0: dirty-bitmap status: created new
INFO: sata1: dirty-bitmap status: created new
INFO: scsi1: dirty-bitmap status: created new
INFO: scsi2: dirty-bitmap status: created new
INFO:   0% (1.6 GiB of 575.0 GiB) in 3s, read: 534.7 MiB/s, write: 525.3 MiB/s
```
**Critical realisation: "dirty-bitmap status: created new" on every disk meant this was reading the FULL 575GiB, not an incremental delta** — because the new disks (created fresh this session) have no prior PBS backup history, so PBS cannot do an incremental read against them regardless of how similar the actual data is to old backups. This directly contradicted an assumption that an "in-place swap" would result in a small/negligible backup.

Given only ~12.9GB was free against a 575GiB read, this was allowed to run briefly before being recognised as certain to fail:
```
INFO: Failed at 2026-07-13 18:09:38
ERROR: Backup job failed - interrupted by signal
```
Confirmed the VM itself was unaffected by the failed backup attempt (snapshot-mode backups use fs-freeze/thaw around the copy; an aborted backup does not corrupt the running guest).

### 7.3 MISTAKE #7 — misunderstanding `vzdump --stop`

Attempted to "stop the running backup" with:
```bash
vzdump 1023 --stop
```
**This does not stop anything — `--stop` in vzdump syntax means "stop the guest before backing up" (a vzdump backup-mode flag), and this command actually STARTED A SECOND BACKUP JOB**, this time writing to **local storage** (`/var/lib/vz/dump/...vma`) instead of PBS — a different, unintended risk (filling local disk instead of PBS).

**Correct way to actually kill a running vzdump job:**
```bash
ps aux | grep vzdump
kill <PID>          # graceful
kill -9 <PID>        # if it doesn't die
```
Then clean up the partial archive file once the process is confirmed dead:
```bash
ls -la /var/lib/vz/dump/
rm /var/lib/vz/dump/vzdump-qemu-1023-<timestamp>.vma
```

### 7.4 Pruning old backups and understanding PBS's Garbage Collection grace period

Identified backups via:
```bash
pvesm list backup_nas
```
Found two ~4.58TiB VM 1023 backups (2026-07-09, 2026-07-12) plus a 1-byte failed test backup from the aborted attempt above.

Removed the empty failed test and the older of the two legitimate VM 1023 backups:
```bash
proxmox-backup-client snapshot forget vm/1023/2026-07-13T17:05:55Z --repository root@pam@192.168.0.150:backup_nas
proxmox-backup-client snapshot forget vm/1023/2026-07-09T23:00:02Z --repository root@pam@192.168.0.150:backup_nas
```
(The operator also separately deleted the older duplicate backups of VM 105 and 106 via the PBS web UI at one point — a reasonable, low-risk prune given each still retained one backup, but this did not materially change the space math either — see below.)

Ran GC on the PBS server itself (GC only runs on the PBS host, not the PVE client):
```bash
ssh root@192.168.0.150
proxmox-backup-manager garbage-collection start backup_nas
```
Result:
```
Removed garbage: 26.187 GiB
Removed chunks: 9704
Pending removals: 1.172 TiB (in 362819 chunks)
On-Disk usage: 300.388 GiB (6.14%)
Deduplication factor: 16.27
```

**Key lesson — PBS Garbage Collection has a mandatory ~24-hour grace period:** deleting a backup ("forget") only removes the index reference. The underlying chunks are only physically removed by GC, and GC enforces a minimum-age threshold (chunk access-time must be older than the cutoff) before actually sweeping a chunk, specifically to protect against a chunk being deleted while another in-progress backup is about to reference it. **This is not configurable via a force flag in normal operation, and running GC additional times within the grace period does not help** — a second GC run confirmed this:
```
Removed garbage: 0 B
Removed chunks: 0
Pending removals: 1.174 TiB (in 365245 chunks)
```
Checking status directly confirmed the next scheduled GC pass was `04:00` — after tonight's midnight backup job, meaning no automatic reclaim would land before the deadline:
```bash
proxmox-backup-manager garbage-collection status backup_nas
```

**Conclusion: no action available that night (further deletions, more GC runs, deleting ALL remaining VM 1023 backups) would free real space before midnight. The grace period is time-gated, not action-gated.** Deleting the last remaining VM 1023 backup was specifically considered and rejected — it would have sacrificed the only independent point-in-time restore point for zero actual space benefit that night.

### 7.5 The decision: disable, don't delete further

Rather than let the midnight job fail loudly (a real but non-catastrophic outcome — a failed backup does not corrupt the VM or existing backups, it just fails and alerts), or gut the last remaining restore point for no benefit, the job was disabled for one night only:

```bash
nano /etc/pve/jobs.cfg
```
Manually changed only the first block's `enabled 1` → `enabled 0` (VM 1023's `mon..fri 00:00` job). The second block (105/106, monthly) was explicitly left untouched.

**Operator added an unmissable inline comment directly in the config to guard against "temporarily disabled forever" config drift:**
```
        enabled 0 <------------- OI FIX THIS TOMORROW OLD BEAN! 
```

**Follow-up actions identified for the next day (see Section 8 — Outstanding Items).**

---

## 8. Outstanding Items / Next-Day Follow-Up

1. **Check PBS GC ran successfully at 04:00** and confirm real free space returned:
   ```bash
   ssh root@192.168.0.150 "proxmox-backup-manager garbage-collection status backup_nas"
   pvesm status
   ```
2. **Re-enable the VM 1023 backup job** in `/etc/pve/jobs.cfg` (set `enabled 1` back, remove the inline warning comment).
3. **Run a fresh manual backup** to confirm it completes cleanly and lands at a sane size now that real space exists:
   ```bash
   vzdump 1023 --storage backup_nas --mode snapshot --notes-template "post-migration-verified"
   ```
4. **After a stability period of a few days**, actually destroy the three parked `unused` zvols to fully reclaim pool space (currently just parked, not consuming extra space beyond what they already occupied, but not contributing anything either):
   ```bash
   qm config 1023 | grep unused
   zfs destroy tank/vm-1023-disk-1   # old 1TB E:
   zfs destroy tank/vm-1023-disk-3   # old 3.5TB D:
   zfs destroy tank/vm-1023-disk-4   # old unrelated 30GB
   ```
   (Confirm exact disk names against current `qm config 1023` output first — do not assume these are still correct without checking.)
5. **Consider a Zabbix check** (fits the existing "PVE Health Checkup" template pattern already in use elsewhere) that alerts if a `vzdump` job in `/etc/pve/jobs.cfg` sits with `enabled 0` for longer than ~24-36 hours — turns "config drift I might forget" into an active page, rather than relying on the inline comment alone.
6. **Confirm whether the ORA-12560 (`ORACLE_HOME` blank) issue should be permanently fixed** at the system/profile level (e.g. setting it as a persistent machine environment variable) so future sqlplus sessions don't hit the same wall under time pressure.

---

## Appendix A — SATA Hotplug Limitation (pc-i440fx)

**Symptom:** A SATA disk added to (or removed from) a *running* VM on the `pc-i440fx` machine type does not appear/disappear in the guest, even after `Update-HostStorageCache`, `diskpart rescan`, or a full guest OS reboot from within Windows.

**Cause:** SATA controller devices in QEMU are enumerated only at process start on i440fx. Proxmox's hotplug support for SATA requires the `q35` machine type. On i440fx, only `virtio`/`scsi` bus devices genuinely hot-add/hot-remove live.

**Practical fix:** use `scsi` (matching the VM's existing `virtio-scsi-single` controller) for any disk that needs to be added/removed while the VM stays running. Reserve SATA-bus changes for VM restarts only.

**Verify machine type before planning any live disk operation:**
```bash
qm config <vmid> | grep machine
```

---

## Appendix B — `qm set -delete` on an Attached Disk: Live VM vs Stopped VM Behaviour

Two different outcomes were observed for the *same* command, depending on VM power state:

**VM running (observed with `sata0`, the old E: disk):**
```bash
qm set 1023 -delete sata0
```
No `unused0:` entry appeared in `qm config 1023`. The zvol was NOT destroyed — confirmed still present via `zfs list -r tank | grep vm-1023-disk-1` — but Proxmox stopped tracking it in the VM's config entirely (a true orphan, not a parked `unused` disk).

**VM stopped (observed later with `sata2`/`sata3`):**
```bash
qm set 1023 -delete sata2
qm set 1023 -delete sata3
```
Both correctly appeared as `unused1:`/`unused2:` in `qm config 1023` — the expected, safer "parked" behaviour.

**Lesson:** don't rely on `qm config <vmid> | grep unused` alone to confirm a disk was safely parked rather than destroyed if the delete was issued while the VM was running. Always cross-check with `zfs list -r <pool> | grep <disk-name>` (or `pvesm list` for LVM/other backends) to confirm the underlying storage object still physically exists, regardless of what the VM config shows. **Prefer stopping the VM before detaching disks whenever the "parked, not destroyed" safety net matters** — as it did here, retiring multi-terabyte production disks.

**Recovery command (re-attach an orphaned-but-intact disk), used as a template throughout this session:**
```bash
qm set <vmid> -<bus><N> <storage>:<disk-name>,discard=on,size=<original-size>
```

---

## Appendix C — Drive Letter Swap: Always Target Explicit Partition Numbers

**Symptom:** After removing a drive letter from one disk and assigning it to another via a piped `Get-Partition -DiskNumber X` (no `-PartitionNumber`), the letter can land on the wrong partition (e.g. the tiny Microsoft Reserved partition instead of the real NTFS data partition), because:
1. GPT disks always have more than one partition (at minimum, an MSR partition alongside the data partition).
2. A bare `Get-Partition -DiskNumber X` pipes ALL partitions on that disk into the next cmdlet.
3. Windows' automount can grab a freshly-vacated drive letter and assign it to whichever partition becomes eligible first — not necessarily the one you intended.

**Always do this instead:**
```powershell
Get-Partition -DiskNumber <X> -PartitionNumber <Y> | Remove-PartitionAccessPath -AccessPath "<Letter>:\"
Get-Partition -DiskNumber <X> -PartitionNumber <Y> | Set-Partition -NewDriveLetter <Letter>
```
And **before any access-path operation**, triple-confirm which disk/partition number is actually which drive letter using an unambiguous, size-cross-referenced view:
```powershell
Get-Disk | Select-Object Number, FriendlyName, PartitionStyle, OperationalStatus, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
Get-Partition | Select-Object DiskNumber, PartitionNumber, DriveLetter, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}
Get-Volume | Select-Object DriveLetter, FileSystemLabel, @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}}, @{N='FreeGB';E={[math]::Round($_.SizeRemaining/1GB,2)}}
```

---

## Appendix D — PBS Garbage Collection: What Actually Frees Space (and What Doesn't)

- `proxmox-backup-client snapshot forget <path>` — removes the backup **index only**. Frees zero disk space by itself.
- `proxmox-backup-manager garbage-collection start <datastore>` — the only thing that physically reclaims space, and **only for chunks whose access-time is already older than PBS's internal grace-period cutoff** (commonly ~24-25 hours). Chunks unreferenced more recently than that show up as "Pending removals" and will NOT be freed by running GC again sooner — the constraint is time-based, not repetition-based.
- There is no supported way to force-bypass the grace period. It exists specifically to prevent a race where a chunk still needed by an in-progress backup gets swept because it briefly looked unreferenced.
- **Practical implication:** if you need PBS space freed for a specific deadline, you must plan for the grace period in advance (delete old backups at least 24-25 hours before you need the space, not on the same day), or accept that the deadline will need to shift/skip.
- `pvesm list <storage>` is a convenient way to list PBS backups (with sizes) from the PVE side without needing `proxmox-backup-manager` (which is only installed on the PBS server itself, not on PVE nodes).

---

## Appendix E — Full Command Reference (this session, in rough chronological order)

```bash
# TRIM loop across all Windows VMs (host side, async)
for vmid in $(qm list | awk 'NR>1 {print $1}'); do
  status=$(qm status $vmid | awk '{print $2}')
  os=$(qm config $vmid | grep ^ostype | cut -d' ' -f2)
  if [ "$status" = "running" ] && [[ "$os" == win* ]]; then
    qm guest exec $vmid -- powershell -Command "Get-Volume | Where-Object {\$_.DriveLetter} | ForEach-Object { Optimize-Volume -DriveLetter \$_.DriveLetter -ReTrim -Verbose }"
  fi
done

# Check async guest-exec result
qm guest exec-status <vmid> <pid>

# ZFS real-usage check (the number that matters, not "used")
zfs get volsize,refreservation,used,referenced <pool>/<zvol>

# Correct disk creation syntax (size as plain number after colon)
qm set <vmid> -<bus><N> <storage>:<sizeGB>,discard=on

# Detach a disk safely (VM stopped preferred, for guaranteed "unused" parking)
qm set <vmid> -delete <bus><N>

# Re-attach a parked/orphaned disk
qm set <vmid> -<bus><N> <storage>:<disk-name>,discard=on,size=<size>

# Fully destroy a parked disk once confirmed no longer needed
zfs destroy <pool>/<disk-name>

# PBS: list backups from PVE side
pvesm list <storage>

# PBS: forget a specific snapshot
proxmox-backup-client snapshot forget <type>/<vmid>/<timestamp> --repository <user>@<host>:<datastore>

# PBS: run GC (must be run ON the PBS server itself)
ssh root@<pbs-host> "proxmox-backup-manager garbage-collection start <datastore>"
ssh root@<pbs-host> "proxmox-backup-manager garbage-collection status <datastore>"

# Kill a genuinely stuck/unwanted vzdump job (NOT `vzdump --stop`, which starts a new job)
ps aux | grep vzdump
kill <PID>

# Graceful guest shutdown (not qm stop, which is a hard power-off)
qm shutdown <vmid>
qm status <vmid>
qm start <vmid>
```

---

*End of runbook. Written same-night, from live session transcript, including all mistakes as encountered — intended as a training/reference document for future disk migrations on this infrastructure, not a sanitized "how it should have gone" version.*
