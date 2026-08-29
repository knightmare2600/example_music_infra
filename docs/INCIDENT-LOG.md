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
| [INC-2026-08-28-FIREWALLME-CSV](#inc-2026-08-28-firewallme-csv--compliance-driven-out-of-hours-rebuild-exposed-a-break-glass-provisioning-bug-broken-for-every-site) | 2026-08-28 | An out-of-hours Coventry firewall rebuild, prompted by premature Compliance pestering over a BCP test still a month away, exposed a break-glass provisioning script broken for every site in the estate |
| [INC-2026-08-21-CTRLALTDEL](#inc-2026-08-21-ctrlaltdel--console-ctrlaltdelete-rebooted-a-live-firewall-node) | 2026-08-21 | A Ctrl+Alt+Del sent via the Proxmox console rebooted a live firewall node — Windows habit, not a Linux "unlock" gesture; molly-guard never saw it since it never touched SSH |
| [INC-2026-08-11-SALT-DISK-FULL](#inc-2026-08-11-salt-disk-full--root-filesystem-filled-by-an-oversized-git-clone-on-the-salt-master) | 2026-08-11 | The Salt master's root filesystem filled completely, blocking all login, because its git-based state/pillar delivery was cloning the estate's entire infrastructure repository in full |
| [INC-2026-07-16-ANSIBLE-LOCK](#inc-2026-07-16-ansible-lock--ansible-account-administratively-locked-out-on-a-live-firewall-node) | 2026-07-16 | The `ansible` account's administrative lock rejected every login method, not just password, on a live firewall node |
| [INC-2026-07-12-SSH-KEY](#inc-2026-07-12-ssh-key--lost-ssh-keypair-delayed-pve-node-deployment-in-scandinavia) | 2026-07-12 | Lost/forgotten SSH keypair delayed PVE node deployment in Scandinavia |
| [INC-2026-04-03-BMC-CREDS](#inc-2026-04-03-bmc-creds--mismatched-bmc-credentials-on-a-newly-delivered-fal-server) | 2026-04-03 | Vendor delivered the wrong physical chassis under otherwise-correct paperwork — documented BMC credentials didn't work on arrival at FAL |

---

## INC-2026-08-28-FIREWALLME-CSV — Compliance-driven out-of-hours rebuild exposed a break-glass provisioning bug broken for every site

### Incident Background

**Date:** 28 August 2026, out of hours
**Scope:** `EXAFWLCOV001` (Coventry firewall) provisioning, and — as investigation showed — the site-data parsing in every one of the estate's four break-glass provisioning scripts (`firewallme.sh`, `bindme.sh`, `rudderme.sh`, `ansibleme.sh`)
**Cause (summary):** `benarbejde/sites.csv` gained four new columns since these scripts' CSV field-parsing was last touched; none of the four had their hardcoded column positions updated to match, so every one of them silently derived garbage — or nothing at all — for every site's subnet-derived values.

A Senior Technician was reached out of hours by the Compliance team, pressing for readiness confirmation ahead of an upcoming Business Continuity Plan (BCP) test that was, at the time, still a full month away. The Senior Technician's response is on record: *"A failure to plan on the part of the Compliance team does not constitute an emergency on his part."* Rather than engage further with a deadline that wasn't actually imminent, and already up dealing with a genuine, unrelated out-of-hours task of his own — bringing a newly-built firewall VM for Coventry (`EXAFWLCOV001`) into service — the Senior Technician used the moment to get that rebuild done via the estate's documented break-glass path (`firewallme.sh`) rather than wait for Ansible connectivity or normal working hours. That path had not been exercised end-to-end against the estate's current `sites.csv` schema in some time. Typing `COV` as the site code produced a derived WAN IP of `192.168.139.` and a WireGuard tunnel address of `10.0..1` — both missing their octet entirely.

### Root Cause & Mitigation

`firewallme.sh`'s `load_sites_csv()` reads `benarbejde/sites.csv` with a fixed, positional `while IFS=',' read -r <field names...>` line, written for an older, 13-column version of that file. `Province`/`OfficeName`/`Street`/`PostalCode` were added between `CountryCode` and `Subnet` at some point after that line was last touched, and every field from `Subnet` onward had been silently reading the wrong column since — not COV-specific, every site's derivation was affected the same way, confirmed by reproducing the identical failure directly from other sites' rows. The WireGuard step failing immediately afterward was the same bug again, one hop over: a spoke derives its hub's LAN/tunnel subnets from `CLD`'s own row through the identical broken read, so it was handed a malformed CIDR (`192.168..0/24`) and failed on it — one root cause, not two.

The identical field list, byte-for-byte, was found in `bindme.sh`, `rudderme.sh`, and `ansibleme.sh` too — all three share obvious lineage with `firewallme.sh` (each one's own comments already cross-reference the others). Ansible's own port of this logic was confirmed unaffected: it reads `sites.csv` by column *name*, not position, so this exact class of drift can't touch it — the normal, actively-maintained path was never at risk.

All four scripts' field lists were corrected to the real current column order. A separate, narrower issue was found during verification: two sites (`BRT`, `MIL`) have a genuinely comma-containing address inside properly double-quoted CSV, which none of these scripts' naive comma-splitting can respect regardless of field-list correctness. Both were resolved by removing the comma from the address data itself rather than building a CSV-quote-aware parser — a real fix would need a dependency (e.g. Python) not guaranteed present this early in a fresh install, and neither address lost anything real by losing the comma: `MIL`'s Street (`"Piazza Armando Diaz, 2"` → `Piazza Armando Diaz 2`) and `BRT`'s OfficeName (`"1st Floor, General Aviation Terminal"` → `1st Floor General Aviation Terminal`). Every row in `sites.csv` now naive-splits identically to a proper CSV parse — there are no remaining known exceptions.

### Lessons Learned

- **A break-glass path needs the same ongoing scrutiny as the path it's a fallback for, not less.** This class of drift would have been caught immediately by any routine use of `firewallme.sh` — it went unnoticed for as long as it did precisely because the normal, Ansible-based path is the one actually exercised day to day, and the break-glass path sat untested until the one moment it was actually needed.
- **A defensive assumption baked into a fixed-position parser has no way to notice the thing it's parsing has changed shape.** `sites.csv` gaining four columns was normal, expected schema evolution, not a mistake — the mistake was that nothing outside these four scripts' own heads knew their copy of the column layout needed to move with it.
- **Two failure symptoms in the same run sharing one upstream cause is common enough to check for before assuming two separate bugs.** The WAN-IP failure and the WireGuard failure looked like unrelated problems until both were traced back to the exact same broken lookup, just applied to two different sites' rows.
- **Urgency that originates from a missed deadline elsewhere is not the same thing as urgency in the system actually being paged about.** A BCP test a month out is a real, legitimate piece of work — it is not, on its own, a reason to interrupt an out-of-hours engineer outside of the process built for scheduling it. The estate is genuinely better off for the break-glass bug being found when it was; it is not better off for the manner in which the opportunity to find it arose.

### Improvements Made

- All four break-glass scripts' `sites.csv` field-parsing corrected to the real current column order, and verified against every site currently on record, not just the one that surfaced the problem.
- `MIL`'s Street address and `BRT`'s OfficeName address both corrected to remove their one embedded comma each — the same class of separate parsing failure, resolved the same way for both once it was clear there was no real reason to treat them differently.
- A new, permanent harness check (`at_have_ryggen_fri/check_breakglass_csv_fields.py`) now runs on every harness pass: it confirms every break-glass script's field list still matches `sites.csv`'s real column order, and independently confirms every row in `sites.csv` naive-comma-splits the same way it properly CSV-parses — the exact two ways this incident's root causes could recur. Robert's own words: *"we need harness checks because this is an operational gap."*
- **Process, not just code:** Compliance-originated requests outside of a genuine live incident are now routed through the team's standard working-hours process rather than directly to whoever's reachable out of hours — formalising, calmly and after the fact, what the Senior Technician's response asserted informally in the moment. The Compliance team's own contribution to squaring things away was entirely voluntary and good-natured: pizza for the IT team, accepted in the same spirit it was offered.

### Executive Summary

An out-of-hours interruption from the Compliance team, over a Business Continuity Plan test that was not due for another month, coincided with a Senior Technician independently using the estate's documented break-glass provisioning path to bring a new Coventry firewall into service. That use surfaced a real, previously-undiscovered defect: all four of the estate's break-glass scripts had been silently deriving wrong or empty network addresses for every site, since `sites.csv` gained four columns their parsing was never updated to match. Ansible's own equivalent logic was unaffected throughout. All four scripts were corrected and verified against the estate's full current site list, one narrower related data-formatting issue was fixed at the source, and a new permanent harness check now guards against both the original defect and its narrower cousin ever recurring unnoticed. The organisational friction that led to the discovery was resolved the same way every other people-facing outcome in this log is — calmly, without blame, and with the Compliance team's own goodwill (pizza) closing the loop.

---

## INC-2026-08-21-CTRLALTDEL — Console Ctrl+Alt+Delete rebooted a live firewall node

### Incident Background

**Date:** 21 August 2026, 18:34 BST (Friday, office closed)
**Scope:** `EXAFWLLIV001` (Liverpool firewall) — a live production firewall VM
**Cause (summary):** A console-delivered Ctrl+Alt+Del, sent out of Windows habit, is a real reboot signal on Linux, not a screen-unlock gesture — the firewall rebooted immediately.

A junior engineer (PFY) was working alone late on a Friday, office already closed, doing routine console-based checks on `EXAFWLLIV001` via Proxmox's own web console (noVNC/xterm.js — not SSH). Muscle memory from years of Windows administration took over — Ctrl+Alt+Del to "wake up"/unlock the session, the way it works at a Windows logon or locked-workstation screen (the old `msgina.dll`-era secure attention sequence, still second nature to most Windows admins). Linux has no equivalent concept at all: the same keystroke, delivered to a real console, is systemd's literal reboot trigger (`ctrl-alt-del.target`, aliased to `reboot.target` by default). The firewall rebooted within seconds.

### Root Cause & Mitigation

Two separate things had to both be true for this to actually cause a reboot, and neither was in place:

1. **`ctrl-alt-del.target` was not masked.** By default, every systemd host starts this target (which reboots the machine) the moment a console-level Ctrl+Alt+Del is received — a decades-old convention inherited from physical server-room access, where a live person at a physical console pressing that combination is assumed to know what they're doing. A VM's web-based console is functionally the same signal path, but without any of the physical-presence assumptions that made the convention reasonable in the first place.
2. **Nothing here was reachable via SSH, so `molly-guard` (already deployed estate-wide, `common_packages`) never had a chance to intercept anything.** `molly-guard` wraps `reboot`/`shutdown`/`halt` when issued as commands over an interactive SSH session — it has no visibility at all into a raw keystroke sequence delivered through an out-of-band console. This was never a `molly-guard` gap; it was a class of input `molly-guard` was never positioned to see in the first place.

The reboot itself was clean — a normal, graceful `reboot.target` run, not a crash — and the firewall came back up correctly on its own, WireGuard included, with no data loss and no configuration damage. The only real cost was a few minutes of downtime for one site's WAN/VPN path, during a period (Friday evening, office closed) where the impact was about as low as this class of mistake could ever land.

**Fix**, added to the firewall role (`roles/firewall/tasks/12_console_hardening.yml`), covers both of the above, together — masking the target alone is not sufficient on its own:

- `ctrl-alt-del.target` is masked outright — a single (or a few) Ctrl+Alt+Del keypresses now does nothing.
- `CtrlAltDelBurstAction=none` is set in `/etc/systemd/system.conf.d/10-disable-ctrl-alt-del.conf`. This closes a real, separate gap: systemd has its own built-in "panic" override — 7 presses within 2 seconds bypasses the target mechanism entirely and forces an immediate, ungraceful reboot, specifically designed so an admin can still force a reboot even if the target is masked or broken. An anxious operator mashing the same key combination repeatedly because the first press "didn't do anything" is exactly the scenario this burst path exists for — and exactly the scenario that needed closing here too. Confirmed against `systemd`'s own documented behaviour before treating the target-mask alone as sufficient, rather than assuming it would cover both cases.

Legitimate remote reboot/shutdown of these VMs is unaffected — Proxmox's own `qm reboot`/`qm shutdown` via `qemu-guest-agent` is a completely different, agent-mediated mechanism, not a console keystroke, and remains the preferred way to restart these nodes.

### Lessons Learned

- **Causation does not equal correlation, and everybody makes mistakes.** A single ordinary keystroke, applied out of well-worn habit in an unfamiliar context, was enough on its own — no chain of separate errors, no negligence, nothing that reflects on the person involved beyond being human. Treating it as anything other than that would itself be the wrong lesson to take from it.
- **A protection that only covers one input path (SSH) can leave a completely different, equally real path (a console) wide open** — `molly-guard` was never wrong or incomplete at the one job it does; the gap was assuming SSH-based protection was protection against reboots in general, when it was only ever protection against reboots issued as SSH commands.
- **Old muscle memory from a different operating system is a real, recurring risk category on mixed-OS estates**, not a one-off — anyone with years of Windows administration behind them will occasionally reach for a Windows reflex on a Linux box, especially late, alone, and outside normal hours. The fix for this category is removing the hazard from the system, not asking people to never make the mistake.
- **A calm, blameless response is itself part of the fix, not just a courtesy.** The engineer was walked through what happened, given space to decompress, and reminded — with genuine warmth, not just words — that nobody died and no planes fell out of the sky. That matters operationally, not just kindly: an engineer who feels safe reporting "I think I just did something" reports it immediately, every time; one who fears blame hesitates, and that hesitation is where small incidents turn into bigger ones.

### Improvements Made

- `roles/firewall/tasks/12_console_hardening.yml` added to the firewall role — masks `ctrl-alt-del.target` and disables the `CtrlAltDelBurstAction` panic-reboot path on every firewall node, present and future, going forward automatically as part of normal provisioning.
- **Immediate response, on the night:**
  1. The PFY was gently taken out of the loop for a few minutes — not as any form of punishment, but specifically to avoid a second, compounding mistake landing on top of the first while still rattled. He went and made coffee for the team.
  2. Given time to decompress, with good-natured banter rather than a dressing-down — reminded that Linux is not Windows, and reminded just as firmly that nobody died and no planes fell out of the sky.
  3. The firewall was back within 3-4 minutes, WireGuard reconnected cleanly on its own. The PFY was allowed to finish his coffee and take a short breather before coming back.
  4. A senior staff member shadowed him afterward and traded a couple of his own "IT war stories" — proof, from someone senior, that nobody is perfect and everyone has a story like this somewhere in their career.
  5. The PFY was "fined" a symbolic £1, added to the estate's running "Should Box" — a light-hearted, well-established team tradition, not a real disciplinary record — and the incident was considered closed the same evening.

### Executive Summary

A junior engineer working alone on a Friday evening sent Ctrl+Alt+Del through a live firewall VM's Proxmox console, out of long-standing Windows habit — on Linux, that keystroke is a genuine reboot signal, not a screen-unlock gesture, and the firewall rebooted within seconds. `molly-guard`, already deployed estate-wide, offered no protection here, not because it failed, but because the input never touched SSH, the only path it was ever built to guard. The reboot itself was clean, the firewall came back up correctly on its own within a few minutes with no data loss, and the impact — a brief WAN/VPN gap at one site, during a quiet Friday evening with the office already closed — was about as low as this category of mistake could land. The response prioritised the engineer's wellbeing as much as the technical fix: a short break, warmth rather than blame, a senior colleague's own war stories, and a token, good-humoured £1 to the "Should Box" — closed out the same night with no lasting friction. The estate is now permanently better protected against this exact input on every firewall node: `ctrl-alt-del.target` is masked, and systemd's own separate "panic" burst-reboot override is disabled too, closing both the direct path and the escape hatch someone panicking might otherwise still trigger.

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
