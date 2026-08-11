# Example Music Limited — Incident Log

**Doc ID:** OPS-INC-001  
**Scope:** Example Music Limited — Infrastructure  
**Applies to:** Operational incidents affecting the estate's infrastructure, tooling, or automation

---

## About this document

This is not a finger-pointing exercise. It is an honest, upfront record that something went wrong — a gap in a process, a mistake, an outcome nobody planned for — and what was done about it. Mistakes happen; that is not news to anyone who has run real infrastructure for any length of time. What matters is that they get caught, contained, fixed, and turned into something the estate is better protected against next time.

A few ground rules for every entry in this log:

- **No blame, no euphemisms.** We say what happened in plain language. We don't dress up a mistake in management-speak to soften it, and we don't need to soften it — but we also don't need to be crude or rude about it either, and we don't name-and-shame the people involved. Roles are used instead of names throughout.
- **Not everything is written down.** Some technical detail is deliberately left out where spelling it out in full serves no purpose beyond embarrassment — the difference between "an omission in the process left a required credential unavailable when it was needed" and the exact, unflattering specifics of how that happened. The engineering substance — cause, impact, fix — is always in here. Colour that adds nothing isn't.
- **The order of operations is always the same:** stop the problem from spreading, let the engineers actually fixing it work without someone stood over their shoulder, and only once things are stable and a safe hold period has passed does the paperwork — this document, any process or harness changes, any new procedure — get written up.
- **Every incident here made the estate better**, by definition — an incident is what happens when an error, omission, or mistake wasn't yet caught by something that now is (or, at minimum, is written down as a known, understood risk). Remove one contributing gap and, on the next attempt, that path to the accident is closed. That doesn't mean nothing will ever go wrong again — it means every entry here is a genuine, permanent improvement, and this log is the record of accumulating them.

## Index

Newest incident at the top, oldest at the bottom — read bottom-to-top for chronological (oldest-to-newest) order. New entries are added at the top as they're formally written up, which is not necessarily the order they occurred — this log starts partway through the estate's history, and earlier incidents are backfilled retroactively as time allows, inserted below the entries that are actually more recent rather than always appended at the very bottom.

| Incident ID | Date | Summary |
|---|---|---|
| [INC-2026-08-11-SALT-DISK-FULL](#inc-2026-08-11-salt-disk-full--root-filesystem-filled-by-an-oversized-git-clone-on-the-salt-master) | 2026-08-11 | The Salt master's root filesystem filled completely, blocking all login, because its git-based state/pillar delivery was cloning the estate's entire infrastructure repository in full |
| [INC-2026-07-16-ANSIBLE-LOCK](#inc-2026-07-16-ansible-lock--ansible-account-administratively-locked-out-on-a-live-firewall-node) | 2026-07-16 | The `ansible` account's administrative lock rejected every login method, not just password, on a live firewall node |
| [INC-2026-07-12-SSH-KEY](#inc-2026-07-12-ssh-key--lost-ssh-keypair-delayed-pve-node-deployment-in-scandinavia) | 2026-07-12 | Lost/forgotten SSH keypair delayed PVE node deployment in Scandinavia |
| [INC-2026-04-03-BMC-CREDS](#inc-2026-04-03-bmc-creds--mismatched-bmc-credentials-on-a-newly-delivered-fal-server) | 2026-04-03 | Vendor delivered the wrong physical chassis under otherwise-correct paperwork — documented BMC credentials didn't work on arrival at FAL |

---

## INC-2026-08-11-SALT-DISK-FULL — Root filesystem filled by an oversized git clone on the Salt master

### Incident Background

**Date:** 11 August 2026
**Scope:** The Salt master (EXASLTCLD001)
**Cause (summary):** Salt's git-based state and pillar delivery had been cloning the estate's entire infrastructure repository in full — including years of large binaries the repository still carries in its history from before it adopted Git LFS — until the root filesystem filled completely.

An engineer went to sign in to the Salt master and every login attempt was rejected outright. Investigation traced the cause to the root filesystem being completely full — roughly 3GB of the space in use sat under a single pair of directories, `/var/cache/salt/master/gitfs` and `/var/cache/salt/master/git_pillar`, Salt's own local caches for the git-backed mechanisms that serve its states and pillar data.

### Root Cause & Mitigation

Salt's `gitfs` (fileserver) and `git_pillar` (pillar) backends each maintain their own persistent local clone of the git repository they're configured against, refreshed incrementally after the first clone — not unlike an ordinary `git pull`. The problem was not that either kept re-downloading everything on every update; it was that the *one* clone each maintained was, by default, a full-history clone of a repository whose history permanently carries a large amount of binary content committed before the repository adopted Git LFS (that migration was deliberately prospective-only, not a history rewrite, so the old content never left). Salt only ever needed a handful of small text files from two subdirectories, but was downloading — and retaining — the repository's entire history regardless.

Root cause confirmed directly, not assumed: an identical local clone of the same repository measured the same size independently, confirming the repository's own history was the source, not anything specific to how the master had been configured.

The first fix attempted was a shallow clone. Salt supports a shallow-clone option (`gitfs_depth`/`git_pillar_depth`), but it only takes effect on one of its three possible git-handling backends (`gitcli`, which shells out to the system `git` binary) — the other two do not honour it at all. Checking what this master actually had installed showed neither of the other two backends' required libraries were present, meaning it had already been using the shallow-clone-capable backend the whole time, by accident, never as a deliberate choice. That backend and the shallow-clone depth were pinned explicitly, cutting the two caches from roughly 3GB to under 700MB.

That fix did not hold up under live testing, and its unwinding is its own real lesson (below). The backend it depended on turned out to have a genuine defect: it never correctly pointed its local clone at the branch it had actually fetched, leaving that reference dangling at a branch name the repository doesn't use. The real, correctly-fetched data was present the whole time under a different, correctly-named reference — but anything that depended on the dangling one silently failed to find real content, even though a plain listing of "what files exist" succeeded, because listing and reading a specific file's content don't use the same path internally. This surfaced days later, the first time a real minion actually tried to use the delivered content rather than just receive it.

Two further fixes were needed once that was understood, in order:

- Switched away from the defective backend to a different one. The first replacement chosen turned out to be invisible to Salt's own runtime for an unrelated reason (Salt bundles its own self-contained Python interpreter, separate from the host's system Python — a package installed for the system Python does nothing for Salt's own), which took the master's service down outright for a short period until corrected to a backend Salt's own error output confirmed was already available to it.
- With a working backend in place, delivery still failed for one further, independent reason: this repository defines real large-file-handling rules that were never registered on this master. An unregistered rule referenced anywhere in a repository's own configuration can affect how git handles a checkout of that repository as a whole, not only the specific files the rule names. Registering it — deliberately in a mode that does not download the actual content of the files it covers, keeping this master's footprint small on that front — resolved the remaining failure.

None of the working backends support the shallow-clone option the first fix relied on, so full-history clones are back, for real, as a permanent, accepted cost — this is not the smaller-footprint outcome originally aimed for. Verified directly, not assumed, that this settled state doesn't grow further on its own: a repeat update cycle with nothing new to fetch left the cache's total size and an existing file's modification time both completely unchanged, confirming genuinely incremental updates rather than repeated full rebuilds. A further, separate and distinct inefficiency was also found — one of the two caches checks out far more of the repository than it strictly needs, and does not fully honour the "don't download large-file content" setting for that broader checkout — assessed as a known, accepted inefficiency rather than a growth risk, since real headroom exists and it does not increase over time.

As an independent safety margin — not a fix for the underlying cause, but sound practice regardless of it — the root logical volume on the Salt master was also extended by 10GB.

### Lessons Learned

- **Nothing was watching free disk space on this host, so a slow, entirely predictable growth had no chance to be caught before it became a full lockout.** The underlying cache had been growing since the day this delivery mechanism was first configured; nothing flagged it at 50% full, or 80%, or 95% — the first signal was the disk hitting 100% and blocking login outright. Estate-wide disk/resource monitoring (already an open piece of work — see the SNMP/Zabbix monitoring rollout notes) would have caught this at a much earlier, much calmer point.
- **A tool's own caching behaviour is not necessarily proportionate to the size of what it's actually meant to be caching.** Two small directories of text files resulted in gigabytes of on-disk cache, because the caching mechanism's design (a full git clone) was never scoped to the small thing it was actually being used for.
- **When a default behaviour turns out to be relying on which optional components happen to be absent, that's worth pinning down explicitly, not left to chance** — this master had been using one particular backend the entire time, purely because certain unrelated components were never installed. That was a lucky accident, not a decision anyone had made — and in this specific case, the accidental default itself later turned out to be defective, which would never have been discovered if it had simply been left alone rather than pinned down and tested properly.
- **A fix that only addresses the symptom that was noticed can leave a real defect in place, waiting for the next thing that happens to depend on it.** The disk-space fix was complete and correct on its own terms, but it was layered on top of a backend nobody had verified actually worked correctly end to end — only that it existed and produced a smaller cache. The defect underneath was only found because a genuinely new kind of test (a real minion actually trying to use the delivered content, not just confirm it was present) was run days later.
- **When a fix doesn't hold up, the right response is to verify the next one just as rigorously, not more hastily.** Each step in unwinding this — identifying the defective backend, choosing its replacement, finding the replacement's own unrelated problem, finding the large-file-handling gap underneath that — was confirmed against direct evidence (the master's own logs, direct inspection of what was actually on disk) before moving to the next step, rather than assumed fixed and moved past.

### Improvements Made

- The Salt master's git-based fileserver and pillar delivery now use a backend confirmed to work correctly end to end against a real minion, with large-file handling correctly registered — not merely a backend that happened to produce a smaller cache.
- The root logical volume on the Salt master was extended by 10GB as an independent safety margin.
- Verified, not assumed, that the current configuration's cache size is stable under repeated updates rather than growing over time.
- Full troubleshooting documentation for this entire class of problem — diagnosing delivery failures, checking the git-backed caches are healthy, forcing a refresh, recovering a master that won't start, and the exact commands for applying state from the command line — is now written up in `docs/management/Salt_Beginners_Guide.md`, so none of this needs re-deriving live under pressure again.
- This incident is now on record as a concrete example of why disk/resource monitoring belongs on the estate's roadmap — a low-cost, entirely preventable class of failure that a basic threshold alert would have caught with days or weeks of advance warning instead of zero.

### Executive Summary

The Salt master became completely unreachable when its root filesystem filled up, traced to gigabytes of accumulated cache from a git-based delivery mechanism that had been cloning the estate's entire infrastructure repository in full since the day it was first configured. Nothing had been watching free disk space on this host, so the growth went unnoticed until it caused a full lockout rather than being caught early. The first fix reduced the cache size significantly, but the backend it relied on turned out to have a genuine defect that only surfaced once a real minion tried to use the delivered content days later — silently failing in a way that a same-day check of "is the content present" did not catch. Diagnosing and correcting that took the master briefly offline a second time, for an unrelated and separate reason found along the way, before landing on a backend confirmed to work correctly, plus one further real gap (a missing large-file-handling registration) found and fixed underneath that. The final configuration accepts a larger on-disk footprint than the first fix aimed for, as the genuine cost of using a backend that actually works, verified not to grow further on its own. The root filesystem was given an independent safety margin regardless. Full troubleshooting documentation for the entire class of problem is now written up, and the clearest lasting lesson — the absence of basic disk-space monitoring on this host, and by extension elsewhere in the estate — is recorded as a concrete case for prioritising that work.

---

## INC-2026-07-16-ANSIBLE-LOCK — `ansible` account administratively locked out on a live firewall node

### Incident Background

**Date:** 16 July 2026
**Scope:** A live firewall node (EXAFWLBRT001) during WireGuard spoke-peering testing
**Cause (summary):** Two independent pieces of automation set the `ansible` account's shadow
password field to an administratively-locked state, intending "key and passwordless-sudo only" —
under the SSH hardening already in place elsewhere in the same role (`UsePAM yes`), a locked
account is rejected for every login method, not just password, contradicting the intent behind
the lock.

While live-testing WireGuard spoke registration, both console login and a fully key-based,
non-interactive SSH connection to the `ansible` account on a firewall node were rejected outright.
No password was involved in either attempt — the rejection happened before authentication method
even mattered.

### Root Cause & Mitigation

Two separate places in the automation asserted a locked shadow state for the `ansible` account,
each added independently, at different times, apparently on the same (incorrect) assumption that
locking a Linux account's password only blocks password-based login. Under the sshd configuration
already in place for these nodes (`UsePAM yes`), `pam_unix`'s account-management phase rejects a
locked account for *every* authentication method presented to it, including public-key auth — the
lock is checked after the key has already been verified, not instead of it.

One of the two locations reasserted the lock on every single run of the routine automation that
maintains these nodes, not just at first creation — meaning a manual unlock, applied to restore
access, would be silently undone the next time that automation touched the host.

Both locations were corrected to never assert an administrative lock: the account is created (or
confirmed to exist) without one, and a defensive task now actively clears any lock found on every
run, so a manual unlock survives future runs instead of being reverted by them. The general
routine-maintenance path for ordinary Linux nodes gained the same defensive clearing task, since
the same incorrect assumption could plausibly exist anywhere a Linux account is provisioned this
way.

Recovery, for a node already stuck in this state with no working session left at all, used local
console access and Debian's single-user recovery mode (interrupting GRUB, appending
`init=/bin/bash` to the kernel line) to reach an unauthenticated root shell, from which the lock
was cleared directly. This is now written up as a standing procedure —
[`docs/linux-recovery-runbook.md`](linux-recovery-runbook.md) — rather than something to
re-derive under pressure next time.

### Lessons Learned

- **"Locked password" and "no password" are not interchangeable, and the difference has real
  consequences under PAM.** A Linux account with no password set is nonetheless still usable for
  key-based/passwordless-sudo auth; the same account with an *administrative lock* applied is
  rejected outright by PAM's account phase for every method, once `UsePAM yes` is in the sshd
  config. The intended security posture ("key and sudo only, no password") requires the former,
  not the latter.
- **A defensive setting reasserted on every automation run needs the same scrutiny as one applied
  once.** The version of this bug that reapplied the lock on every routine run was the more
  damaging of the two — it silently undid manual recovery, turning a one-time mistake into a
  recurring one until the automation itself was fixed.
- **Local/console recovery access remains essential even in a heavily key- and Ansible-driven
  estate.** Every layer of remote access (SSH key, sudo, the automation itself) can, in principle,
  fail together if the failure is in the account layer underneath all of them — the same lesson
  the BMC-credential incident above already established for a different failure mode (remote
  access to management hardware) applies here too, one level further down the stack.

### Improvements Made

- Both automation paths that could assert an administrative lock on the `ansible` account no
  longer do so, and both now include a defensive task that actively clears one if found, on every
  run — a manual recovery now survives the next routine run rather than being undone by it.
- A new standing recovery procedure, [`docs/linux-recovery-runbook.md`](linux-recovery-runbook.md)
  (`OPS-RECOVERY-001`), documents the GRUB single-user-mode recovery path end to end, so it's a
  known, rehearsed step rather than a live investigation the next time any Linux node in the
  estate ends up in a similar state, for any reason.
- The Ansible documentation set gained a real, transcript-backed troubleshooting entry describing
  this exact failure mode and how to distinguish it from an ordinary passwordless-sudo problem.

### Executive Summary

Two independent pieces of automation locked the `ansible` account on Linux nodes, on the mistaken
assumption that a locked password only blocks password-based login — under this estate's own SSH
hardening, it blocks every login method, including the key-based access the automation itself
depends on. One of the two reasserted the lock on every routine run, which is why a manual unlock
didn't hold. Both are now fixed to never lock the account and to actively clear a lock if found,
so a recurrence heals itself rather than needing manual intervention again. A full recovery
procedure is now written up as a standing runbook rather than something to work out from scratch
under pressure.

---

## INC-2026-07-12-SSH-KEY — Lost SSH keypair delayed PVE node deployment in Scandinavia

### Incident Background

**Date:** 12 July 2026  
**Scope:** Deployment of a new Proxmox VE node in Gothenburg, Sweden (Scandinavia region)  
**Cause (summary):** An omission in the estate's SSH keypair process left the private half of a required key unavailable when a live deployment needed it, delaying that node's onboarding.

During a live deployment of a new Proxmox VE node in Gothenburg, the automation responsible for giving the node its real identity (hostname, static networking) failed to connect. Nothing about the failure pointed at why — the node was reachable on the network — but the connection itself would not complete.

### Root Cause & Mitigation

Investigation traced the failure to the SSH keypair the estate's automation uses to reach Proxmox nodes: the private half of that key — required on the Ansible control node, per the configured path automation relies on — could not be found there. Only the public half — routinely distributed to new nodes during provisioning — was present. An omission in the process that carries a keypair from wherever it's generated to where it's actually needed had gone unnoticed until this deployment hit it for the first time on real hardware.

To keep the affected build moving, the engineer generated a fresh keypair directly on the control node and manually added the new public key to the Gothenburg node — using a combination of direct SSH (where already reachable) and out-of-band BMC/console access (where it wasn't) — restoring managed access without needing to rebuild the node. Username/password authentication remained available throughout as an existing, already-accepted fallback for Proxmox nodes specifically: if key-based access is ever unavailable, password auth is the documented alternative for these nodes, not a new decision made in response to this incident.

### Lessons Learned

- There was a check that a *public* key existed somewhere in the repository, but nothing that confirmed the *private* half was actually present and working before automation depended on it.
- The failure gave no indication it was a key/authentication problem — it looked identical to a generic network issue, and the real cause only became clear after testing the connection by hand.
- There was no written recovery procedure for this exact situation. It was worked out live, under time pressure, rather than being a known, rehearsed step.

### Improvements Made

- The verification harness run before any change is trusted now includes a dedicated SSH keypair check — it confirms the public key is consistent everywhere it's committed, and, on the real control node, that the private half is genuinely present.
- The node-onboarding automation now performs a real connection test using the actual configured key before doing anything else, and stops outright with a clear explanation if that test fails, instead of proceeding and failing confusingly later.
- The recovery steps used here — generate fresh, redistribute the public half, verify — are now written down as a documented procedure.
- **Cross-check, every time.** The fix for this exact problem was tested end-to-end against a real connection before being trusted — not just read over and assumed correct. That's the standing rule for anything touching access to live infrastructure: a second, independent pass — another engineer, or a genuine live test — before it's relied on operationally. The same reason airline cabin crews call out "cross-check" to one another before a door is armed applies here: the cost of skipping it is paid later, at the worst possible time.

### Executive Summary

A gap in how SSH keypairs move from creation to actual use let a key go missing without anyone knowing, until a live deployment in Scandinavia needed it and lost time as a result. Nothing was lost that couldn't be regenerated, and the affected node was recovered the same day using existing, documented fallback access. The automation and its safety checks have both been updated so this specific failure mode is now caught immediately, with a clear explanation, instead of surfacing as an unexplained delay. This is how these incidents work: something exposes a gap nobody had reason to look for yet, it gets fixed, and the fix becomes a permanent part of how the estate protects itself going forward.

---

## INC-2026-04-03-BMC-CREDS — Mismatched BMC credentials on a newly-delivered FAL server

### Incident Background

**Date:** 3 April 2026  
**Scope:** Commissioning of a newly-delivered physical server at FAL (Falkirk)  
**Cause (summary):** The vendor shipped a different physical chassis than the one described on its own accompanying asset tags and paperwork — identically specced, but not the same unit — so the documented BMC administrator credentials did not work on the hardware actually received.

A new server arrived at FAL and was racked as normal. The asset tags and delivery paperwork listed BMC administrator credentials for remote out-of-band management. Those credentials did not authenticate against the delivered unit. It was later established that the vendor had shipped a different, identically-specced chassis than the one the paperwork actually described — a fulfilment mix-up on their end, not a data-entry error on ours. The hardware itself was fine for purpose; only the credentials on file were wrong for the box in front of the technician.

### Root Cause & Mitigation

With the documented BMC credentials unusable, remote out-of-band access to the server was not available at all — there was no way to reach it except locally. The technician connected a crash cart (monitor, keyboard, a small power bar) directly to the server. A mild inconvenience at FAL, with a technician already on site; the same problem at a site without easy physical presence, such as LAX or SYD, would have cost considerably more time.

With local console access, the technician PXE-booted the server using the estate's own iPXE menu to boot into GParted Live (already an existing boot option, not something built for this), then installed `ipmitool` on that live environment.

From there, `ipmitool user set password 2 <new password>` reset the BMC's administrator account directly, in-band, from the host's own IPMI device — bypassing the broken remote credential path entirely (method per [Exxact's own "Resetting the BMC Using ipmitool on Linux" guide](https://support.exxactcorp.com/hc/en-us/articles/31728599437847-Resetting-the-BMC-Using-ipmitool-on-Linux)). The technician confirmed the new password actually worked and enabled Serial-over-LAN before rebooting out of GParted — not assumed, tested, before moving on.

Once rebooted, the technician independently confirmed BMC connectivity a second way — using [`fyrtaarn`](https://github.com/knightmare2600/fyrtaarn) and a separate `ipmitool` check from a different machine entirely (a MacBook) — before trusting the new credentials for anything further. Only then did the technician log into the BMC properly and use virtual media to install Proxmox VE, as any normal build would.

Licensing and asset records were updated to reflect the chassis actually received, rather than the one originally described on paperwork — the hardware itself needed no remedial work.

### Lessons Learned

- Asset tags and delivery paperwork describing BMC credentials cannot be assumed to match the physical hardware actually received — a vendor fulfilment error can substitute a different, even identically-specced, unit without it being obvious until credentials are tried.
- Recovery from unusable/mismatched BMC credentials does not require vendor involvement or a warranty RMA cycle — local console access plus a standard, documented `ipmitool` procedure was enough, provided someone can physically reach the box.
- Physical proximity matters specifically for this failure mode: the same problem at a harder-to-reach site turns a same-visit fix into a real delay.

### Improvements Made

- Documentation was updated to reflect the credential-reset procedure actually used, so the next occurrence of this specific problem is a known, rehearsed step rather than a live investigation.
- The senior technician was informed, and the vendor was formally emailed to raise a compliance record over the chassis mismatch — the appropriate escalation channel for a vendor-side fulfilment error, separate from the technical recovery itself.
- **Cross-check, every time.** The reset password was tested and SOL was confirmed working before the technician moved on — not assumed correct. Then it was verified again, independently, a second way (`fyrtaarn` plus a separate `ipmitool` check from an entirely different machine) before being trusted for the actual build. The same standing rule as every other entry in this log: a second, independent pass before relying on something operationally, because the cost of skipping it is paid later, at the worst possible time.

### Executive Summary

A vendor fulfilment error — the wrong physical chassis delivered under otherwise-correct paperwork — meant a new FAL server's documented BMC credentials didn't work on arrival. Nothing was actually broken: the hardware was fit for purpose, and the credentials were recoverable on site, the same visit, using a standard local procedure rather than a vendor RMA cycle. Every step of the recovery was verified before being trusted for the next one. A compliance record was raised with the vendor as the appropriate formal follow-up. This is how these incidents work: something exposes a gap nobody had reason to look for yet, it gets handled, and the fix becomes a permanent part of how the estate protects itself going forward.
