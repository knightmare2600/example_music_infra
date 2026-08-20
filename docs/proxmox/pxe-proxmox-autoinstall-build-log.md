# Proxmox VE 9 auto-install via PXE — build log and working notes

> **Superseded as the current path, 2026-08-20 — kept for the record, not current guidance.**
> Neither approach this document describes (BMC-ISO delivery, or its replacement
> `select-pve-answer.sh`) is what the estate actually uses now. A third, different approach —
> `klargoring`, a real PXE boot of Robert's own live-installer distro — was tested end-to-end
> for the first time on `EXAPVEVRK002` and worked correctly. See
> `docs/proxmox/NET-PVE-KLARGORING-001-klargoring-pve-install.md` for the current, confirmed
> procedure. This document's own "Still open" section below, gating "polished procedure"
> status on a successful end-to-end test boot, never actually got that test for the approaches
> described here — `select-pve-answer.sh` remains genuinely untested to this day.

Version history:
- v1.0 — 2026-07-18 — initial draft, written up from the live working session that superseded `claude_prompts.md`
- v1.1 — 2026-07-18 — BMC virtual media confirmed as the sole delivery method going forward (not the
  full-network `initrd`-loaded `.iso` path); `:proxmox-ve` menu entry rewritten accordingly; dropped
  the plan to host all four `.iso`s on HTTP
- v1.2 — 2026-07-18 — macOS POST shim confirmed not required (all four `.iso`s point at Edinburgh's
  `:8001` regardless of site); file/menu deployment mechanism is a git commit + pull on both sites,
  not `scp`; Windows POST shim is now the only genuine blocker left before a test boot
- v1.3 — 2026-07-18 — Windows POST shim deployed and confirmed working live (`Start-ProxmoxAnswerShim.ps1`
  v1.0.1, both GET and POST against a real `VRK-answer.toml` returned 200 with correct content).
  **The BMC-mounted-ISO test boot itself then failed outright** — blank cursor, no sign of the
  mounted ISO being picked up by the installer's init script the way the network-loaded companion
  ISO was during earlier (non-BMC) testing. Section 2's inherited assumption ("the installer's init
  script treats a real mounted block device and an iPXE-loaded in-memory file interchangeably")
  did not hold up on the one real test that mattered. **This whole approach — `prepare-iso --pxe`,
  four site/mode ISOs, BMC virtual media as the payload-delivery mechanism — is abandoned, not just
  paused.** Given how rarely a PVE node actually gets built, and that an operator is physically at
  the console for BMC virtual media anyway, the effort of debugging *why* the BMC path doesn't work
  isn't worth it against a simpler alternative: script the plain manual-wget flow this document's own
  section 3/`docs/bootstrap/bootstrapping.md` §6.3 already documents as the fallback, with a real
  script (`bootstrap/web/proxmox/select-pve-answer.sh`) doing the site/disk-count detection and
  fetch instead of a human guessing the right filename by hand. See section 9 below for that script.
  `Start-ProxmoxAnswerShim.ps1`/`bootstrap/serve.py` are unaffected by this — the plain manual-wget
  path this new script drives is a GET, not a POST, so neither shim is actually needed for Proxmox
  at all any more; they remain independently useful, just not on this critical path.

This is **not** the polished procedure document — that's still gated on a successful end-to-end
test boot (see "Still open" below), matching the original plan's own rule. This is the honest
record of how we got here, including the wrong turns, so nobody has to rediscover them.

---

## 1. Why this document exists, and how it differs from `claude_prompts.md`

`claude_prompts.md` in this same directory captured the *plan* as it stood before any of it had
touched real hardware: four site/mode ISOs, BMC virtual media, `--fetch-from iso`. Once we actually
had `proxmox-auto-install-assistant` installed and started running real commands against a real
ISO, several of those decisions turned out to be wrong or incomplete. This document is the record
of what actually happened, kept deliberately unsanitised.

---

## 2. Architecture as it actually stands now

- **Decided, 2026-07-18: BMC virtual media is the sole delivery method for the squashfs payload,
  operationally.** `prepare-iso --pxe` also produces a companion `.iso` that iPXE *can* load as a
  second `initrd` module over HTTP instead (confirmed working, see below) — that path remains true
  and useful to know about, but is not what's actually used. Instead, the correct site/mode `.iso`
  gets mounted as iLO/iDRAC virtual media on the target host before boot, and the PXE-delivered
  `vmlinuz`/`initrd.img` (identical for every site and mode) is all that travels over HTTP. This
  presumes the installer's init script treats a real mounted block device and an iPXE-loaded
  in-memory file interchangeably when searching for `proxmox.iso` — inherited from the original
  session's claim (stated as "verified against Proxmox docs and forum threads" before any of this
  document's testing began), not independently re-confirmed by us. Worth proving on the first real
  test boot, not just assuming it carries over.
- **The full-network path was fully built and confirmed working anyway**, before the BMC decision
  was made: `prepare-iso --pxe` produces a companion ISO that iPXE loads as a *second* `initrd`
  module (renamed `proxmox.iso` in the boot environment) alongside the real `initrd.img`, entirely
  over HTTP, with no BMC media needed at all. Confirmed by inspecting the tool's own auto-generated
  `boot.ipxe` output, not inferred from documentation. Kept here for the record — this is the
  fallback if the BMC-delivery assumption above doesn't hold up on a real test boot.
- **Four separate PXE pairs, not one shared pair.** `--fetch-from http` takes an optional `--url`;
  if omitted, the installer falls back to DHCP option 250 or a DNS TXT record — there is no
  kernel-command-line override. Since neither fallback fits our infrastructure as currently
  understood, the URL is baked in at `prepare-iso` time, meaning one build per site/mode
  combination (FRD-answer, FRD-degraded, VRK-answer, VRK-degraded).
- **`--fetch-from iso` is incompatible with `--pxe`.** The answer file would need to live inside an
  ISO body that `--pxe` explicitly doesn't produce. `http` is the only viable mode for PXE output.
- **The answer-file fetch is an HTTP POST**, confirmed from `prepare-iso --help` verbatim: "requested
  via an HTTP Post request". This mattered a lot — see section 4.
- **All four TOML URLs point at `192.168.139.50:8001`**, not split per site. This is a presumption,
  not a confirmed fact — flagged in section 5. The `:8001` is the not-yet-deployed PowerShell POST
  shim (section 6, item 1) — `static-web-server` stays on port 80 for everything else and 405s any
  POST, which is exactly why the build URLs must not point at the default port.
- **`vmlinuz` is byte-identical across all four variants, and `initrd.img` is too** — confirmed by
  `sha256sum` after all four builds (same hash for all four `vmlinuz`, same separate hash for all
  four `initrd.img`). Neither file carries the per-variant fetch config, which was a genuine "stop
  and look" moment before it was confirmed correct. The actual per-variant config lives in
  **`/auto-installer-mode.toml` inside the companion `.iso`** (all four `.iso` hashes differ, as
  expected), confirmed by extracting it directly:
  ```
  mode = "http"
  partition_label = "proxmox-ais"

  [http]
  url = "http://192.168.139.50:8001/proxmox/FRD-answer.toml"
  ```
  Consistent with the tool's own process trace — "Preparing ISO..." (where this file is written)
  runs before "Creating vmlinuz and initrd.img..." (a plain extraction/recompression of `/boot`),
  so the split-out PXE files were never going to carry variant-specific data in the first place.

---

## 3. Real kernel parameters, confirmed vs. fictitious

The auto-generated `boot.ipxe` from `prepare-iso --pxe-loader ipxe` is the ground truth here — more
reliable than the wiki, which turned out to be incomplete on exactly this point.

**Real, confirmed** (present in the generated `boot.ipxe`, and cross-checked against a community PXE
tutorial and the PVE admin guide's description of the "Install Proxmox VE (Automated)" GRUB entry):
```
kernel vmlinuz ramdisk_size=16777216 rw quiet initrd=initrd.img splash=silent proxmox-start-auto-installer
...
initrd initrd.img
initrd proxmox-ve_9.2-1-auto-from-http-url.iso proxmox.iso
boot
```

**Not real** — present in the live `menu.ipxe`'s `:proxmox-ve` entry, absent from `prepare-iso --help`,
absent from the generated `boot.ipxe`, and absent from a `grep` of the vanilla ISO's own initrd contents:
```
proxmox-auto-install-mode=http proxmox-auto-install-url=${boot-url}/proxmox/${site-prefix}-answer.toml
```
That entry was written on assumption (plausible-looking, modelled on the Debian `url=` preseed
convention) and never tested. It needs replacing with something built off the real generated
stanza, not patched in place. This is still an open item — see section 6.

---

## 4. Mistakes made along the way, and what they taught us

Recording these because each one changed the design, not just because they're embarrassing.

1. **Guessed a `--fetch-from http-kernel` mode existed.** It doesn't. Only `iso`, `http`, `partition`
   are real, confirmed via the tool's own `--help` and its Rust source on GitHub. Lesson: don't
   assert plausible-sounding flag names without checking the actual CLI.

2. **Assumed BMC virtual media would still be required for the squashfs even in PXE mode.** Wrong —
   see section 2. The correction came from actually building one variant and reading its generated
   `boot.ipxe`, not from further doc research.

3. **Guessed the initrd's compression format instead of checking it.** Tried
   `zstd -d -c initrd.img | cpio -idm` blind. It was the wrong container assumption for that
   particular decompression path and `cpio` choked on non-cpio bytes, flooding raw binary to the
   terminal and desyncing the PuTTY session into echoing garbage as literal input. The actual fix
   was `file initrd.img` first (confirmed genuinely Zstandard-compressed), then `unmkinitramfs`
   (from `initramfs-tools-core`) — an existing tool that already solves the
   multi-segment-initrd-unpacking problem correctly, rather than hand-rolling the decompression
   pipeline. Lesson: check the generator/format before guessing the consumer command, and never
   pipe unknown binary content straight at an interactive terminal.

4. **First `prepare-iso --pxe` run failed on disk space.** `--output` was pointed at
   `/tmp/pve-iso-check/pxe-test`, which is tmpfs (1.9G total on this host) — the tool tries to write
   a full companion ISO (~1.6GB) there even in `--pxe` mode (see next point), and ran out of room
   mid-write. Fix: point `--output` at the ZFS-backed home directory instead of `/tmp`.

5. **Misread what `--pxe` actually produces.** The `--help` text — "Instead of only producing an ISO
   file, additionally generate 'initrd.img' and 'vmlinuz'" — reads at a glance like "PXE output
   instead of an ISO." It means the opposite: PXE files *in addition to* the ISO. Every variant
   built this way leaves a ~1.6GB companion ISO behind as well as the split files, and that ISO
   is *not* a throwaway — see section 2, it's the second `initrd` module the boot chain needs.

6. **First POST-shim snippet had a real bug.** `functools.partial(SimpleHTTPRequestHandler, ...)`
   with `handler.do_POST = handler.do_GET` set on the partial object doesn't attach the method the
   way `HTTPServer` needs — it needed to be a proper subclass with `do_POST = do_GET` as a class
   attribute. Caught on re-reading before it was actually run, not after a failure — worth stating
   plainly it hadn't been tested at the point it was handed over.

7. **Static file servers on both sites reject the POST the installer needs to make.** Confirmed
   empirically:
   ```
   curl -i -X POST http://192.168.139.50/proxmox/FRD-answer.toml
   HTTP/1.1 405 Method Not Allowed
   ```
   `static-web-server` (Windows, Edinburgh) has no method/verb configuration option anywhere in its
   full `--help` output — this is architectural, not a missing config flag. `python3 -m http.server`
   (macOS, Fredericia) never implements `do_POST` in the stdlib handler at all. See section 6 for
   the agreed fixes, neither of which has been deployed yet.

8. **Build commands referenced a per-variant `--output` directory that was never created.**
   `mkdir -p ~/pxe-build ~/pxe-final` only creates the two parent directories; `--output
   ~/pxe-build/frd-answer` needs that exact subdirectory to already exist (`prepare-iso` will not
   create it — confirmed by its own error, "must point to an existing directory when '--pxe' is
   specified"). Because the commands were handed over as plain sequential lines rather than
   `&&`-chained, the failed `prepare-iso` didn't stop the block — every subsequent `mv` then failed
   too, on top of unrelated shell prompt text getting interpreted as commands from pasting multiple
   blocks in close succession. Fixed by creating each variant's subdirectory explicitly before its
   `prepare-iso` call, and chaining each variant's block with `&&` so one failure stops that block
   cleanly instead of cascading into unrelated-looking errors. Section 7 below reflects the fix.

---

## 5. Presumptions flagged, not yet confirmed

- **All four TOML URLs point at `192.168.139.50:8001`** rather than splitting FRD variants to
  Fredericia's own server. Evidence for the host: the original brief describes a single central
  TOML server, and `curl -X POST` against `192.168.139.50/proxmox/FRD-answer.toml` (port 80)
  returned 405 (method rejected) rather than 404 (not found) — proving the file genuinely exists
  there, just not servable via POST on that port. Not yet confirmed: whether Fredericia's network
  (described as "physically a MacBook running python3 -m http.server 8000... Legal fiction", on a
  distinct gateway/subnet, possibly Fusion-NAT'd) can actually route to `192.168.139.50` at all. If
  it can't, the FRD variants need rebuilding against Fredericia's own server instead once
  `/proxmox/` is confirmed mirrored there.
- **The `:8001` port assumes the PowerShell POST shim (section 6, item 1) is deployed and listening
  on `/proxmox/` before these four variants are built.** Building against port 80 would silently
  bake in a fetch that 405s at install time — the build step (item 2) must not run before the shim
  is confirmed live, matching the dependency order already listed in section 6.
- **RAM headroom on target hosts — reduced concern under BMC delivery, but not eliminated.** Under
  the full-network path this needed ~2GB+ free (staging `initrd.img` plus the full 1.6GB companion
  ISO in RAM before the kernel starts). Under BMC delivery, iLO/iDRAC virtual media conventionally
  presents as a live, on-demand-read block device rather than something preloaded wholesale into
  RAM — if true, only the ~116MB `initrd.img` needs staging. This is an assumption about how HP
  iLO's virtual media specifically behaves, not something tested in this session.
- **Fredericia's link bandwidth** — no longer relevant at all. Not just to squashfs delivery (nothing
  1.6GB-sized crosses that link under BMC delivery) but to the answer-file POST fetch too: all four
  `.iso`s' `/auto-installer-mode.toml` point at `192.168.139.50:8001` regardless of site, so a
  Fredericia-sited host's POST never touches Fredericia's own server either. The only thing that
  server needs to serve for this flow is the two GET-only files in item 5 below.

---

## 6. Still open

In dependency order:

1. **Deploy the Windows POST-fetch shim — the one genuine blocker left.** `static-web-server-x64.exe`
   stays running unchanged on port 80; a small `HttpListener`-based PowerShell shim on a separate
   port (`:8001`) handles the `/proxmox/*.toml` POST fetch. Nothing completes an install until
   something is listening there. ~~macOS (Fredericia) POST fix~~ **turned out not to be needed**:
   established once all four `.iso`s were confirmed to point at `192.168.139.50:8001` regardless of
   site — Fredericia's server only ever needs to serve plain GET requests for the two files in item
   5, so its existing `python3 -m http.server` is fine as-is. The drop-in Python replacement drafted
   earlier is still a reasonable thing to deploy for its own sake (consistency, in case future work
   does need POST there), just not load-bearing for this flow.
2. ~~Build all four PXE variants and confirm they're correct.~~ **Done and fully verified,
   2026-07-18.** `vmlinuz` identical across all four (`9eaf9a7fa2cc...`), `initrd.img` also
   identical across all four (`ec3bb86a6a2d...`, one shared hash, different from the `vmlinuz`
   hash) — both expected, see section 2. The four companion `.iso` files each hash differently, and
   direct extraction of `/auto-installer-mode.toml` from `proxmox-frd-answer.iso` confirmed the
   correct URL baked in. Nothing left unverified here.
3. ~~Resolve the filename mismatch.~~ **Decided, 2026-07-18.** Fix the stanza, not the files — keep
   the tool-generated names (`vmlinuz`, `initrd.img`) and update `menu.ipxe`'s paths to match. See
   section 8 for the actual rewritten entry.
4. ~~Rewrite the `:proxmox-ve` entry.~~ **Decided, 2026-07-18.** BMC delivery only, going forward —
   no second `initrd ... proxmox.iso` line, and no site/mode branching needed for file selection
   since `vmlinuz`/`initrd.img` are identical everywhere; the entry just reuses the already-resolved
   `${boot-url}` the same way every other OS entry in the menu does. Answer-vs-degraded selection is
   entirely a manual "which ISO did you mount" decision now, not an iPXE concern at all — see
   section 8.
5. Get the **shared** `vmlinuz` and `initrd.img` (one copy of each, not four — grab them from
   `~/pxe-test/` on `pve-install`, already correctly named, no rename needed) and the section 8
   stanza into both sites. Mechanism: commit both files under wherever `proxmox/` resolves in the
   docroot, and the new `:proxmox-ve` entry into `menu.ipxe`, in the existing git repo; both sites
   pick it up on their next `git pull` — no direct `scp`/network-reachability question between
   `pve-install` and either site's server, sidestepped entirely by using the same sync mechanism
   already used for `/debian` and everything else in that repo. The four `.iso`s do **not** get
   committed anywhere — they get mounted directly via iLO/iDRAC on whichever host is being
   provisioned, confirmed as trivial given the technicians' machines have local capacity for this.
6. ~~First real end-to-end test boot on one host, testing specifically whether the BMC-mounted ISO
   gets found by the init script the same way the network-loaded one did.~~ **Done, 2026-07-18 —
   and it failed.** Blank cursor, no sign of the mounted ISO being picked up at all. The whole
   BMC-delivery approach (this document's sections 2, 7, 8) is abandoned as a result — see the v1.3
   changelog entry at the top and section 9 below for what replaces it. This document still isn't
   the polished procedure doc the original plan's rule gates on; that gate now applies to
   `select-pve-answer.sh` instead (section 9), not to anything BMC-related above.

---

## 7. Build commands used (four PXE variants)

Run on `pve-install` (`ansible@192.168.139.85`). One block at a time — paste one, wait for the
prompt to return, then paste the next. Pasting several blocks in quick succession is what caused
shell prompt text to get interpreted as a literal command during the first attempt (see mistake 8).

Each variant's `--output` subdirectory must exist before `prepare-iso` runs — it will not create
one itself. Each block is `&&`-chained so a failed `prepare-iso` stops that block cleanly instead
of the `mv` lines cascading into unrelated-looking errors (also mistake 8).

```
mkdir -p ~/pxe-final
```

```
mkdir -p ~/pxe-build/frd-answer && \
sudo proxmox-auto-install-assistant prepare-iso ~/proxmox-ve_9.2-1.iso \
  --fetch-from http \
  --url "http://192.168.139.50:8001/proxmox/FRD-answer.toml" \
  --pxe --pxe-loader ipxe \
  --output ~/pxe-build/frd-answer && \
mv ~/pxe-build/frd-answer/vmlinuz    ~/pxe-final/vmlinuz-frd-answer && \
mv ~/pxe-build/frd-answer/initrd.img ~/pxe-final/initrd-frd-answer.img && \
mv ~/pxe-build/frd-answer/*.iso      ~/pxe-final/proxmox-frd-answer.iso && \
mv ~/pxe-build/frd-answer/*.ipxe     ~/pxe-final/boot-frd-answer.ipxe
```

```
mkdir -p ~/pxe-build/frd-degraded && \
sudo proxmox-auto-install-assistant prepare-iso ~/proxmox-ve_9.2-1.iso \
  --fetch-from http \
  --url "http://192.168.139.50:8001/proxmox/FRD-degraded.toml" \
  --pxe --pxe-loader ipxe \
  --output ~/pxe-build/frd-degraded && \
mv ~/pxe-build/frd-degraded/vmlinuz    ~/pxe-final/vmlinuz-frd-degraded && \
mv ~/pxe-build/frd-degraded/initrd.img ~/pxe-final/initrd-frd-degraded.img && \
mv ~/pxe-build/frd-degraded/*.iso      ~/pxe-final/proxmox-frd-degraded.iso && \
mv ~/pxe-build/frd-degraded/*.ipxe     ~/pxe-final/boot-frd-degraded.ipxe
```

```
mkdir -p ~/pxe-build/vrk-answer && \
sudo proxmox-auto-install-assistant prepare-iso ~/proxmox-ve_9.2-1.iso \
  --fetch-from http \
  --url "http://192.168.139.50:8001/proxmox/VRK-answer.toml" \
  --pxe --pxe-loader ipxe \
  --output ~/pxe-build/vrk-answer && \
mv ~/pxe-build/vrk-answer/vmlinuz    ~/pxe-final/vmlinuz-vrk-answer && \
mv ~/pxe-build/vrk-answer/initrd.img ~/pxe-final/initrd-vrk-answer.img && \
mv ~/pxe-build/vrk-answer/*.iso      ~/pxe-final/proxmox-vrk-answer.iso && \
mv ~/pxe-build/vrk-answer/*.ipxe     ~/pxe-final/boot-vrk-answer.ipxe
```

```
mkdir -p ~/pxe-build/vrk-degraded && \
sudo proxmox-auto-install-assistant prepare-iso ~/proxmox-ve_9.2-1.iso \
  --fetch-from http \
  --url "http://192.168.139.50:8001/proxmox/VRK-degraded.toml" \
  --pxe --pxe-loader ipxe \
  --output ~/pxe-build/vrk-degraded && \
mv ~/pxe-build/vrk-degraded/vmlinuz    ~/pxe-final/vmlinuz-vrk-degraded && \
mv ~/pxe-build/vrk-degraded/initrd.img ~/pxe-final/initrd-vrk-degraded.img && \
mv ~/pxe-build/vrk-degraded/*.iso      ~/pxe-final/proxmox-vrk-degraded.iso && \
mv ~/pxe-build/vrk-degraded/*.ipxe     ~/pxe-final/boot-vrk-degraded.ipxe
```

```
# cleanup + verify
rm -rf ~/pxe-build
cd ~/pxe-final
ls -la
sha256sum vmlinuz-frd-answer vmlinuz-frd-degraded vmlinuz-vrk-answer vmlinuz-vrk-degraded
```

Expected result: all four `sha256sum` lines identical. If any differ, stop and compare rather than
assuming which one is "right" — same rule as the original plan's own verification step.

---

## 8. Rewritten `:proxmox-ve` menu entry (BMC delivery)

Replaces the old entry in `menu.ipxe`, which used kernel parameters (`proxmox-auto-install-mode=`,
`proxmox-auto-install-url=`) that turned out not to be real — see section 3. Not yet pasted into the
live file or tested; that's section 6, item 6.

```
# ===========================================================================
# PROXMOX VE
# x86_64 only -- Proxmox does not publish arm64 installer ISOs
#
# BMC-delivery only. The correct ${site-prefix}-answer.toml or ${site-prefix}-degraded.toml
# variant's ISO (built via `proxmox-auto-install-assistant prepare-iso --fetch-from http --pxe`)
# must already be mounted as iLO/iDRAC virtual media on the target host BEFORE this is booted --
# this stanza only delivers the shared kernel+initrd, identical for every site and mode. The
# answer file itself is fetched over HTTP from the URL baked into that specific mounted ISO's
# own /auto-installer-mode.toml -- this stanza has no visibility into which ISO that is, hence
# the echo below. Confirmed against proxmox-auto-install-assistant's own generated boot.ipxe
# (2026-07-18): proxmox-start-auto-installer is the real trigger; there is no
# proxmox-auto-install-mode/-url kernel parameter, unlike what this entry previously assumed.
# ===========================================================================
:proxmox-ve
iseq ${arch} arm64 && goto noarch-msg ||
echo Site: ${site-prefix}  -- CONFIRM the matching ${site-prefix} ISO is mounted via iLO/BMC before continuing
kernel ${boot-url}/proxmox/vmlinuz ramdisk_size=16777216 rw quiet initrd=initrd.img splash=silent proxmox-start-auto-installer
initrd ${boot-url}/proxmox/initrd.img
boot
```

Dropped `vga=791 video=vesafb:ywrap,mtrr` from the old entry — not present in the tool's own
confirmed-correct generated stanza, and not worth carrying over untested params from the version
that turned out to be wrong elsewhere. If there's a specific known reason they're needed, they can
go back in.

**Superseded, 2026-07-18 — kept for the record, not the current design.** This section (and the
`:proxmox-ve` menu entry it describes) was written before the BMC virtual media approach failed its
real test boot (see the v1.3 changelog entry and section 6, item 6). `menu.ipxe`'s `:proxmox-ve` is
now a stub pointing at section 9 below, not this stanza.

---

## 9. What actually ships: `select-pve-answer.sh`

Simpler than everything above, and doesn't touch PXE/iPXE at all. PVE nodes are built rarely
enough, with an operator physically at the console for BMC virtual media anyway, that scripting
the plain manual-wget flow `docs/bootstrap/bootstrapping.md` §6.3 already documents is a better
trade than debugging why the ISO-based approach didn't boot.

**Flow:**
1. Mount a plain, unmodified Proxmox VE ISO via iLO/iDRAC virtual media — no `prepare-iso`
   pre-baking, no per-site/mode variants, one ISO works everywhere.
2. Boot it, select **Install Proxmox VE (Automated)** at Proxmox's own native boot menu, with no
   fetch URL configured. This drops to a root shell — documented, expected behaviour, not an
   error (§6.3).
3. From that shell:
   ```
   wget http://<provisioning-server>/proxmox/select-pve-answer.sh
   sh select-pve-answer.sh
   ```
4. The script detects which provisioning network it's on (same gateway-based logic `menu.ipxe`
   already uses: `192.168.139.254` → Edinburgh/VRK, `172.16.124.2` → Fredericia/FRD, parsed
   straight from `/proc/net/route` — no dependency on `ip`/`route` being present), counts real
   physical disks via `/sys/block` (excluding `loop*`/`ram*`/`sr*`/`fd*`/`dm-*` — the last one
   matters because a server being rebuilt could have leftover LVM signatures on its physical disks,
   and `sr*` matters because the BMC-mounted Proxmox ISO itself shows up as an `sr*` optical
   device), suggests `answer` (2+ disks) or `degraded` (fewer), lets the operator confirm or
   override, then fetches the right `${site-prefix}-${variant}.toml` into
   `/run/automatic-installer-answers` and verifies it's really TOML (non-empty, starts with
   `[global]`) before saying it's safe to `exit`.
5. Operator types `exit` themselves — the script never does this on their behalf — handing back to
   the Proxmox installer, which finds the answer file in place and proceeds unattended from there.

**Written in POSIX `sh`, not bash** — this runs inside Proxmox's installer environment (BusyBox
`ash`), which has no bash at all. The gateway-detection and disk-enumeration logic was tested
directly against a real `busybox ash` interpreter and real `/proc/net/route`/`/sys/block` content
before being committed — including a real bug the first version had (device-mapper/LVM volumes
weren't excluded from the disk count, overcounting a single physical disk as three on a box that
happened to run its root filesystem on LVM) — but the actual `wget` fetch against a genuine Proxmox
installer environment has **not** been tested live yet. Same rule as everywhere else in this
document: confirm on the next real boot before calling this done.
