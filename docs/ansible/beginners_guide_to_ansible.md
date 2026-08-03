# Example Music Limited — Beginner's Guide to Ansible

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Purpose

This document provides a practical introduction to Ansible as it is actually used at
Example Music. It started as a write-up of one real troubleshooting/learning session on
`EXADNSVRK001` (the sudo/become/reboot walkthrough further down still uses that session's
real captured output — new administrators are encouraged to compare their own output
against it). It has since grown to cover the repository's actual architecture: how the
inventory is organised, where `group_vars`/`host_vars` have to live and why, how a
brand-new host gets correct variables before it's even in the inventory file, and what
"idempotent" means in practice rather than just in the textbook definition.

If you only read one thing before touching this repo, read
**[Inventory and group_vars — the part that isn't optional](#inventory-and-group_vars--the-part-that-isnt-optional)**.
It explains a mistake that is easy to make, silent when made, and was made once already
in this repo's own history.

---

## What is Ansible?

Ansible is an automation framework used to configure, deploy and maintain systems.

Rather than manually logging into servers and performing repetitive administrative tasks, administrators write **playbooks** which describe the desired state of a system.

Typical uses include:

- Installing software
- Managing users
- Deploying configuration files
- Managing DNS
- Restarting services
- Provisioning infrastructure

At Example Music, Ansible is used as the primary Linux configuration and deployment platform, and (via `windows_bootstrap`/`windows_dc`/`windows_adschema`) the primary Windows one too.

---

## Example Environment

The following examples were captured from:

```text
Hostname : EXADNSVRK001
Address  : 192.168.139.8
Role     : DNS Server
Domain   : jukebox.internal
```

---

## How This Repository Is Organised

Everything Ansible needs to run — inventory, generated group variables, and (for the
Windows AD demo data) pre-generated JSON — is produced from a small set of hand-maintained
files in **`benarbejde/`** (Danish: roughly "the legwork done in advance"), at the repo
root, outside `ansible/` entirely:

| File | What it is |
|------|------------|
| `sites.csv` | One row per site — subnet, gateway, city, country, entity, timezone |
| `devices.csv` | **Exceptions only** — a device row is only needed if it doesn't fit the standard addressing convention |
| `address_policy.json` | The standard addressing convention (which host-role gets which octet offset) as data |
| `begyndelse.json` | Well-known service addresses (DNS, Ansible control node, PBX, Rudder…) for consumers that run *before* Ansible exists on a box (`bindme.sh`, `ansibleme.sh`) |
| `ad_forest.json` | AD forest identity — domain FQDN, NetBIOS name, DNS forwarders — single source for what used to be three separately hardcoded variables. `domain_fqdn` is genuinely changeable — every consumer derives from it rather than hardcoding `jukebox.internal` — one edit here (e.g. to an illustrative `disco.internal`, not a real value) is all a rename would take, no other file should need touching |
| `generate_inventory.py` | Reads all of the above, writes `ansible/configs/inventory/*.ini` (one file per site) plus `group_vars/all/site_services.yml` |

The rule that makes this work: **nothing downstream hardcodes a fact that one of these
files already states.** If you need to know a site's subnet, a device's IP, or the AD
domain name, there is exactly one file that says so, and every consumer — Ansible
playbooks, the pre-Ansible bootstrap shell scripts, `bind9-dns.yml`'s DNS zone generation —
reads the same one. `.githooks/pre-commit` auto-copies the subset of `benarbejde/` that the
PXE preseed web server needs into `bootstrap/web/proxmox/` on every commit, so that copy can
never drift from the source of truth by hand-editing.

### Two separate deploy mechanisms — don't conflate them

`benarbejde/` files reach two genuinely different audiences, via two genuinely different,
unrelated mechanisms. Mixing them up is an easy, recurring source of confusion:

1. **`.githooks/pre-commit` → `bootstrap/web/proxmox/`.** Feeds the PXE/preseed web server —
   consumers that run *before* Ansible (or even a git clone) exists on a box at all
   (`bindme.sh`, early preseed/unattend stages). Fires automatically on every commit.
2. **`ansible/playbooks/linux/tools.yml` → `/etc/example-music/` on every Ansible-managed
   Linux host.** Feeds consumers that are themselves Ansible plays — `sites.csv`,
   `devices.csv`, `address_policy.json`, `ad_forest.json`, and the TDF-derived `ad_*.json`
   files all go here identically, via the same `copy:` task pattern in the same playbook.
   This is a normal Ansible run, not automatic — it needs to have actually been run (or
   re-run) against a given host for that host's `/etc/example-music/` copy to be current.
   The **Ansible control node counts as one of these hosts** — it doesn't get a free pass
   just because it also happens to hold the git clone `benarbejde/` itself came from.

**Why not just have Ansible read `benarbejde/` directly, skipping the `/etc/example-music/`
copy entirely?** Two files in the whole repo do exactly this (`linux/tools.yml` itself, and
`proxmox/bootstrap-new-node.yml`, via a `{{ playbook_dir }}/../../../benarbejde/...}}`
relative path) — and it works fine for them, *because* each is one standalone playbook
sitting at one fixed, known directory depth. It does **not** generalise to `group_vars/`
files like `group_vars/all/vars.yml`, which get auto-loaded for every play across the whole
tree regardless of depth (`windows_dc/playbooks/`, `bind9/`, `rudder/`,
`windows_bootstrap/playbooks/`, …) — a single relative-path expression can't correctly
count `../` for all of them at once. `/etc/example-music/` is a fixed, depth-independent
path that works the same way from anywhere, which is exactly why `group_vars/all/vars.yml`'s
`ad_forest_json_path` and `bind9-dns.yml`'s own copy of the same pattern both hardcode it
rather than deriving it. (One thing that *isn't* the reason: on a real control node built via
`ansibleme.sh`, the working `ansible/` directory is actually a symlink to the real git clone
— confirmed empirically that this doesn't break `{{ playbook_dir }}`-relative resolution,
Ansible resolves the real path transparently. The symlink is a non-issue either way.)

### A worked example: `jukebox.example.tdf`

`benarbejde/jukebox.example.tdf` and `benarbejde/parse_tdf.py` are worth knowing about
specifically because they show where the "single source of truth" boundary is drawn. The
TDF file is old demo data (users, groups, computers, in a legacy PowerShell-literal format);
`parse_tdf.py` is a hand-run, offline script that turns it into `ad_users.json`/
`ad_groups.json`/`ad_computers.json`. **No playbook or task reads the TDF file or invokes
this script, at any point.** Only the JSON it produces — deployed to `/etc/example-music/`
— is a real Ansible dependency (read by `windows_adschema/playbooks/{20,30,40}-*.yml`). The
script's own header calls itself out as a "LEGACY / DEFUNCT TOOL" for exactly this reason:
it's useful for regenerating the demo data by hand, but it is deliberately *not* wired into
anything Ansible runs, so a change to that old PowerShell-literal format can never silently
break a live playbook run.

---

## Inventory and `group_vars` — the part that isn't optional

If you've used Puppet, you might look for Ansible's equivalent of `modules.pp` — a config
file that tells the tool "here's where to look for things." Ansible doesn't have a separate
one. **The inventory path you pass with `-i` *is* the search path.**

Specifically: `group_vars/` and `host_vars/` are auto-loaded by a built-in vars plugin
(`ansible.builtin.host_group_vars`). That plugin's own documentation says it "only applies
to inventory sources that are existing paths" — in practice this means `group_vars/` and
`host_vars/` are only discovered when they live **inside** the directory you actually pass
to `-i` (or that `ansible.cfg`'s `inventory =` points at). A directory sitting next to it —
even one directory up, even with an identical name — is not searched. There's no separate
"add this to the search path" setting to reach for; moving the inventory *is* the only lever.

This repo learned that the hard way. `group_vars/` used to sit at `ansible/group_vars/`,
sibling to `ansible/configs/inventory/` (the real, loaded inventory path). It looked correct
— same repo, one directory over — but it silently never applied to a single numbered
playbook, because it was never *inside* the loaded path. The result was a set of
`undefined variable` crashes deep into the `windows_dc` chain that only reproduced on a
fresh host, because a host that had already picked up variables from an earlier working
run kept them cached in its facts. Confirming this took an isolated test harness (a
throwaway inventory + a marker `group_vars/testgroup/vars.yml` file, moved between a
sibling location and a nested one, with `ansible-playbook -i <path> --limit testgroup`
run after each move) rather than reading documentation and guessing — the plugin's actual
behaviour was the only thing that settled it. This is a general lesson worth keeping,
not just an anecdote: when infrastructure behaviour is surprising, build the smallest
possible reproduction before proposing a fix.

The fix was to physically move the directory: `group_vars/` and `host_vars/` now live at
`ansible/configs/inventory/group_vars/` and `.../host_vars/` — genuinely inside the
`inventory =` target. **A symlink was tried first and explicitly rejected**, because this
repo is cloned on Windows, Linux, and macOS, and symlinks don't survive that reliably
(Windows needs special permissions to create them at all; git on Windows can check one out
as a plain text file containing the link target unless `core.symlinks=true` is set, which
isn't guaranteed on every clone). A real directory move, tracked by git like any other file,
works identically everywhere. See `ansible/README.md`'s "`group_vars`/`host_vars` location"
section for the full technical detail — this is deliberately not duplicated here beyond what
a beginner needs to know: **if `ansible.cfg`'s `inventory =` path ever changes, `group_vars`/
`host_vars` have to move with it, or every group-specific variable silently stops applying.**

### What `configs/inventory/` actually contains

```text
configs/inventory/
├── main.ini              ← pvenodes, ansiblehosts, dcs, firewalls (from discovery)
├── rudder.ini             ← Rudder server + relay hosts
├── cld.ini, fal.ini, …    ← one file per site (53 total), generated — do not hand-edit
├── group_vars/
│   ├── all/                ← every host (packages, colours, AD forest identity)
│   ├── linux/               ← Linux-only: privilege escalation
│   ├── windows_nodes/        ← every Windows host: SSH connection settings
│   ├── windows_dc/            ← Domain Controllers
│   └── …
└── host_vars/
    └── <hostname>.yml     ← rare, host-specific overrides
```

Ansible merges every `.ini` file in `configs/inventory/` automatically — you don't list them
individually. Regenerate the generated `.ini` files after changing `sites.csv`/`devices.csv`:

```bash
python3 benarbejde/generate_inventory.py benarbejde/sites.csv \
  -o ansible/configs/inventory --devices benarbejde/devices.csv
```

---

## Dynamic Inventory Registration — `add_host`

A practical problem falls out of the rule above: a *brand-new* host being bootstrapped for
the first time isn't in `configs/inventory/<site>.ini` yet — it can't be, the whole point of
the run is to bring it to a known-good state so it *can* be added. But without being in a
group, it gets none of that group's `group_vars` (its Windows connection settings, its
domain controller variables, whatever the role needs).

The naive fix is to require the operator to hand-edit the `.ini` file before every first
run. That works, but it's exactly the kind of manual, error-prone step this repo tries to
design out — and for someone still learning Ansible, being told to edit an inventory file
correctly *before* they've successfully run their first playbook is a bad place to start.

The actual fix, used in `windows_bootstrap/playbooks/00-preflight.yml`, is Ansible's
built-in `add_host` module. It registers a host into a group **for the rest of the current
run only** — it never touches any file on disk, and the registration doesn't survive past
the `ansible-playbook` process exiting:

```yaml
- name: "[H2] Register into {{ _permanent_groups | join(', ') }} for the rest of this run"
  add_host:
    name:         "{{ target_hostname | upper }}"
    groups:       "{{ _permanent_groups }}"
    ansible_host: "{{ static_ip }}"
  delegate_to: localhost
  become: false
```

Two things make this actually useful rather than just a curiosity:

1. **`delegate_to: localhost`** runs the `add_host` task on the control node (where the
   in-memory inventory lives), not on the remote target — this is what lets a later,
   separately-imported play's `hosts:` pattern see the new group membership, confirmed
   empirically with a two-play test harness before trusting it in a real bootstrap chain.
2. **Registering into the most specific group is enough.** Adding a host to `windows_dc`
   correctly inherits every parent group's `group_vars` too (`windows_server` →
   `windows` → `windows_nodes`), including connection settings like
   `group_vars/windows_nodes/connection.yml`'s SSH user/key/shell — there's no need to
   also pass those as explicit `add_host` variables.

This means a genuinely new host can be bootstrapped with nothing more than
`-e target=<hostname> -e static_ip=<ip>` and correct group variables resolve from the very
first task onward — no pre-editing an `.ini` file, no bare-IP inventory hack that bypasses
`group_vars` entirely. The host still gets added to `configs/inventory/<site>.ini` for real
once bootstrap completes; `add_host` only covers the run that gets it there.

---

## Bootstrapping the Base Nodes — A Worked Example From Nothing

Everything above is easier to follow with a real, concrete run through it. This section
walks through building CLD's core estate — the Ansible control node, the site firewall
(also the estate's WireGuard hub), and the first domain controller — starting from a bare
Proxmox hypervisor and nothing else. It ties together `benarbejde/` as the source of truth,
the inventory/`group_vars` mechanism, and `add_host` dynamic registration, all in one
concrete sequence rather than three separate abstract explanations.

**The starting point:** `EXAPVECLD001` (CLD's own Proxmox hypervisor) is already built —
imaged via its iLO BMC (`192.168.139.3`, HP iLO — can mount the Proxmox ISO as virtual
media) — but not yet Ansible-managed. It's currently reachable at `192.168.139.243`, a
provisioning-network address, not its real final one. *(Mounting the ISO by hand via iLO is
a manual step today — PXE-booting Proxmox directly is planned work, not yet built. Come back
to this once that lands.)* Nothing else exists yet: no Ansible control node, no firewall, no
domain. This is genuinely the chicken-and-egg case
`docs/proxmox/Procedure-PVE-Node-Onboarding.md` calls out — the fix for it is
`bootstrap/web/provision/ansibleme.sh`, a break-glass script that configures a box directly
over SSH without needing an existing Ansible control node to drive it.

One thing worth noting before starting: **creating a VM on a Proxmox host doesn't require
that host to be Ansible-onboarded at all** — `create-vm.py` (or the Proxmox web UI) talks
directly to the PVE API, which is already up on any built hypervisor regardless of whether
Ansible manages it yet. That's what breaks the apparent circularity below: every VM in this
walkthrough gets created on `EXAPVECLD001` while it's still sitting at its provisioning
address, `192.168.139.243`, onboarding it comes later as its own explicit step.

### 1. `EXAANSCLD001` — the Ansible control node itself

Create the VM on `EXAPVECLD001` (`192.168.139.243`) the same way
`docs/buildsheets/buildsheet-firewall.md`'s Step 1 does it for a firewall — `create-vm.py`
against the PVE API, boot order CD-ROM first. PXE/preseed installs Debian the same way it
does for every other Linux box in this estate (see `docs/bootstrap/bootstrapping.md`) —
`late_command.sh` already drops an `ansible` system user and the estate's SSH key onto it
during that same install, before anything Ansible-related has run. In this walkthrough the
box comes up on `192.168.69.222` — a DHCP lease from CLD's own LAN pool (`.100`–`.249` per
`address_policy.json`), not the shared `192.168.139.0/24` provisioning network the firewalls
land on, since this VM was given a single NIC on CLD's LAN bridge rather than a dual-homed
WAN/LAN pair.

SSH in as `ansible` (the key's already there) and fetch the real bootstrap script from the
provisioning server:

```bash
ssh ansible@192.168.69.222
wget http://192.168.139.50/provision/ansibleme.sh
chmod +x ansibleme.sh
sudo ./ansibleme.sh
```

> The URL above is the *actual* git-tracked path (`bootstrap/web/provision/ansibleme.sh`) —
> worth flagging because `docs/buildsheets/buildsheet-firewall.md`'s equivalent `wget` for
> `firewallme.sh` omits the `/provision/` segment, which looks stale against the real file
> tree. Not fixed here — out of scope for this section — but don't copy that one literally.

`ansibleme.sh` is self-contained and interactive. In order, it: reconfigures this box's own
static IP (to `192.168.69.9`, per `devices.csv`'s `CLD,ANS,1,9` row — the same value
`begyndelse.json`'s `ansible_control` entry already states); generates the estate's Ansible
SSH keypair; clones this repo into `/home/ansible/example-music-infra` and symlinks
`ansible/` to `/home/ansible/ansible`; writes `ansible.cfg` and scaffolds
`configs/inventory/`; and offers to onboard PVE nodes and run a discovery scan of the rest of
the estate. Say no to both for now — those are the next two steps, done deliberately rather
than as part of this run.

**End state:** a real Ansible control node at `192.168.69.9`, with `ansible-playbook`
runnable from `~/ansible` against everything covered below.

### 2. `EXAPVECLD001` — onboarding the hypervisor everything else runs on

From `EXAANSCLD001`, onboard the hypervisor itself. It's still sitting at its provisioning
address, so this is exactly `proxmox/bootstrap-new-node.yml`'s documented case — a
freshly-preseeded node on DHCP getting its real identity for the first time:

```bash
ansible-playbook -i "192.168.139.243," -i configs/inventory \
  -e target="192.168.139.243" playbooks/proxmox/bootstrap-new-node.yml
```

You'll be asked to confirm the target hostname (`EXAPVECLD001`) and the derived static IP
before anything changes. That derivation matters here: `EXAPVECLD001` is CLD's standard PVE1
slot (`address_policy.json`'s `PVE` role offset, `.5`) **within CLD's own LAN subnet**,
`192.168.69.0/24` — so the confirmed address is `192.168.69.5`, not a `192.168.139.x`
address. `configs/inventory/cld.ini` already has this exact entry
(`EXAPVECLD001 ansible_host=192.168.69.5`, generated straight from `sites.csv` — nothing to
hand-edit), and `docs/proxmox/Procedure-PVE-Node-Onboarding.md` uses this very host as its
own worked example. The `192.168.139.0/24` range is the shared provisioning network, never a
site's permanent address for anything other than a firewall's WAN face — worth being
precise about, since it's an easy mix-up.

The playbook renames the host, rewrites its networking to static, then chains straight into
the full `site.yml` stage chain (packages, ansible access, `/etc/example-music/`, scripts,
virt-tools, systemd units), rebooting once at the very end.

**End state:** `EXAPVECLD001` fully Ansible-managed at `192.168.69.5`.

### 3. `EXAFWLCLD001` — the site firewall and estate WireGuard hub

Create another VM on `EXAPVECLD001` (now itself onboarded, though that's not a prerequisite
— see the note above), PXE-installed the same way. In this walkthrough it comes up on
`192.168.139.188` — the shared provisioning network this time, since a firewall genuinely
needs a WAN-facing NIC there.

The committed inventory already has an entry for this host —
`configs/inventory/cld.ini` says `EXAFWLCLD001 ansible_host=192.168.139.69` — but that's its
*final* WAN address, not reachable yet. The very first run against a brand-new firewall
needs to override that for just this one connection:

```bash
ansible-playbook -i configs/inventory \
  -e target=EXAFWLCLD001 -e ansible_host=192.168.139.188 \
  playbooks/firewallme/playbooks/90-firewall.yml --ask-vault-pass
```

> `-e ansible_host=...` beats the inventory-set value (extra-vars are the highest-precedence
> source in Ansible), so this connects to the box's real current address while every other
> group-derived setting (`ansible_user=ansible`, become, `group_vars/firewalls/main.yml`'s
> hub tables) still resolves normally — `EXAFWLCLD001` is already a genuine, correctly
> grouped inventory host, unlike a PVE node's brand-new-hostname problem, so no `add_host`
> dance is needed here at all. Flagged honestly: this exact override isn't a documented,
> previously-tested worked example anywhere in this repo — it's derived directly from how
> `late_command.sh` already provisions the `ansible` user/key and from standard Ansible
> variable precedence, not from a prior live run in this state.

CLD is the estate's black site, so the role asks its extra black-site `CONFIRM`, then — as
of the WireGuard hub-bootstrap work landed 2026-07-18 — detects that this host has no
existing `/etc/wireguard/private.key` and asks a further, CLD-only prompt: *"No existing hub
config found on EXAFWLCLD001 (CLD) — set it up now?"* Answer `CONFIRM`. That's what actually
triggers key generation and the `wg0.conf` `[Interface]` write for a from-scratch hub — it
used to be silently skipped for CLD unconditionally, full stop. WAN mode is forced static
here (mandatory for the black site); the role derives `192.168.139.69` and asks you to
confirm it, matching `192.168.139.<CLD's site-octet, 69>`, the same convention every other
site's WAN address follows.

**End state:** `EXAFWLCLD001` is the estate's WireGuard hub, static WAN `192.168.139.69`,
tunnel address `10.0.69.1`, ready to accept spokes.

### 4. `EXADCSCLD001` — the first domain controller (forest root)

Create a Windows Server VM on `EXAPVECLD001`, install via the estate's unattend answer file
(see `docs/bootstrap/bootstrapping.md`'s Windows section), and once it's reachable over
WinRM after OOBE, run the DC onboarding chain from `EXAANSCLD001`:

```bash
ansible-playbook -i configs/inventory playbooks/windows_dc/site.yml \
  -e target=<its-current-reachable-address>
```

`windows_bootstrap/playbooks/00-preflight.yml` (the same `add_host` mechanism described
above, in the flesh) asks for the real hostname (`EXADCSCLD001`), whether this is the first
DC in the forest (**yes** — nothing exists yet), and the static IP to assign. That last one
is `192.168.69.10` — `sites.csv`'s own `DC` column for CLD already states this directly, no
derivation needed. Being first-in-forest means DNS resolution falls back to BIND9
(`192.168.139.8`, the estate's `EXADNSVRK001`) until this DC promotes itself and becomes its
own DNS server. Once the rename/static-IP/reboot cycle completes,
`add_host` registers the box into `windows_dc` (and its parent groups) for the rest of this
same run, and the DC-specific stages (`windows_dc/playbooks/00-dc-preflight.yml` onward) take
over — `Install-ADDSForest`, not a join, since this is the forest root.

**End state:** the `jukebox.internal` forest exists, with `EXADCSCLD001` as its first DC at
`192.168.69.10`.

### 5. Proving WireGuard end-to-end — `EXAFWLFAL001`

With CLD's hub genuinely up, the next firewall built anywhere is the real end-to-end test.
`EXAFWLFAL001` comes up on `192.168.139.237` this time — a DHCP lease from the same shared
provisioning network as CLD's own firewall used earlier, not its final address. Same
pattern as step 3:

```bash
ansible-playbook -i configs/inventory \
  -e target=EXAFWLFAL001 -e ansible_host=192.168.139.237 \
  playbooks/firewallme/playbooks/90-firewall.yml --ask-vault-pass
```

FAL isn't the black site, so this one's simpler: WAN derives to `192.168.139.76` (FAL's own
site-octet), WireGuard role defaults to `spoke`, hub site defaults to `CLD`. Once the role
finishes, `10_register_spoke_on_hub.yml` automatically registers `EXAFWLFAL001` as a peer on
`EXAFWLCLD001` — delegating straight to `192.168.139.69` — and (as of the same 2026-07-18
work) checks that hub is actually reachable on port 22 first, deferring cleanly with a clear
message rather than failing raw if CLD isn't up yet.

> The spoke's own tunnel IP (default `10.0.<site-octet>.1`, offered at the prompt) is what
> gets written into the hub's `[Peer]` `AllowedIPs` and used in the live `wg set` call — as of
> `6c3527b` (2026-07-24) this is validated as a real IPv4 address before either happens.
> Before that fix, anything mistyped or pasted into that prompt propagated unchecked all the
> way to a live `wg set` command on the hub, which failed with an opaque non-zero exit instead
> of a clear error at the point of bad input.

Verify the tunnel from either end:

```bash
sudo wg show                    # both ends — look for a recent handshake
ping -c 3 10.0.69.1              # from FAL, to CLD's hub tunnel address
```

> **This is not enough on its own — verify real LAN-to-LAN traffic too.** A recent handshake
> and a successful ping to the hub's own tunnel address prove the tunnel is up; they do **not**
> prove a spoke can actually reach anything *behind* the hub's LAN. Found live 2026-07-24,
> `EXAFWLBRT001` → `EXAFWLCLD001`: `wg show` looked perfect on both ends, and the spoke could
> even reach the hub's own firewall LAN IP directly — but every real LAN client behind the hub
> (`EXAANSCLD001`, `EXADCSCLD001`) was 100% unreachable, port `filtered`. Root cause:
> `07_nftables.yml`'s `wg0` forward rules were gated `and not fw_is_black_site` — since CLD
> *is* the black site, the one hub node had zero rules permitting `wg0 → LAN` forwarding, so
> its own `policy drop` silently ate every packet. Fixed in `19dd5da`; every build from that
> commit onward is unaffected, but the lesson stands regardless — always finish a WireGuard
> verification with a real LAN-client test, not just a tunnel-level one:
> ```bash
> ping -c 4 192.168.69.9          # from the spoke, to a real host behind the hub's LAN
> nmap -p22 -Pn 192.168.69.9      # -Pn matters: ICMP alone can look like "host down"
> ```

**What this whole walkthrough demonstrates:** `benarbejde/` as the single source of truth
(every address above came from `sites.csv`, `devices.csv`, or `address_policy.json` — none
were invented), `add_host` resolving group membership for a host that doesn't exist in any
`.ini` file yet, and the same core idea — a fresh box reachable only by its temporary address
becoming a fully-managed, correctly-configured estate member — playing out identically
across a Debian firewall, a Debian hypervisor, and a Windows domain controller.

---

## Real-World Invocations — Day 2: Already-Onboarded Hosts

Everything above is day 0 — a box with no history, reachable only by a temporary address,
becoming a managed estate member for the first time. Once a host is genuinely onboarded
(a real, correct `.ini` entry, DNS resolves its hostname, the `ansible` key already works),
the same playbooks get invoked differently: no `-e ansible_host=` override, no `add_host`
dance — just `-e target=<hostname>`, or nothing at all if the group default is right. Three
real invocations from this estate's own operational history, each chosen because something
about it isn't obvious from the command alone.

### Firewall — a routine re-run against a host that already exists

```bash
ansible-playbook -i configs/inventory playbooks/firewallme/playbooks/90-firewall.yml \
  -e target=EXAFWLCLD001 --ask-vault-pass
```

That's the whole difference from the from-scratch form in step 3 above — no `ansible_host`
override, because `configs/inventory/cld.ini` already resolves `EXAFWLCLD001` to its real,
final address. Every prompt in `00_preflight_3_ask.yml` still runs the same way; nothing
about being a re-run skips them.

One thing worth knowing before running this against more than one host at once (leaving
`target` unset, or pointing it at a group): `90-firewall.yml`'s main play carries `serial: 1`
(added 2026-07-31). Every prompt in that role is an `ansible.builtin.pause` task, and pause
does not reliably register a separate answer for each host in a parallel batch — confirmed
live, in a different play, back on 2026-07-16 (see `ssh_preflight_with_fallback.yml`'s own
header) — only one host in the batch actually gets what you type; every other host silently
inherits the same answer. A single `-e target=<host>` run was never affected (one host in the
batch either way); `serial: 1` only changes what happens the moment more than one firewall is
targeted in the same invocation, turning that from a silent correctness bug into a proper
one-host-at-a-time pass.

### Domain controller — re-running to confirm a fix actually held

```bash
ansible-playbook -i configs/inventory playbooks/windows_dc/site.yml \
  -e target=EXADCSCLD001
```

The full form (no `--skip-tags bootstrap`) — worth knowing *why* that matters here rather
than the narrower "DC stages only" form from `windows_dc/README.md`: `windows_bootstrap`'s
`00-preflight.yml` carries a failsafe (`[B0]`) for a recurring, never-fully-explained bug
where a Windows box ends up with `DefaultShell=pwsh.exe` set, which breaks every
module-based Ansible connection outright (`pwsh -SSHServerMode` doesn't parse Ansible's
`-EncodedCommand` invocation the way PowerShell 5.1 does). B0 lives in the `bootstrap` tag —
skip it, and a box already in that broken state has nothing left to rescue it.

B0 itself had a real bug of its own for weeks: a `delegate_to: localhost` task doesn't reset
`ansible_shell_type` back to local just because `ansible_connection: local` is set alongside
it — the play's own Windows-target value leaked through, so B0's actual `ssh ... reg delete
DefaultShell` command never executed at all, silently swallowed by its own `failed_when:
false`. Fixed 2026-07-28. **Confirmed live for the first time 2026-08-01**: a real DC hit the
broken `DefaultShell` state, this exact command's B0 stage caught it and corrected it, and a
second run of the identical command afterward connected and completed cleanly — proof the
fix holds, not just that the bug it used to have is gone.

### Full BIND9 rebuild — `EXADNSVRK001`

```bash
ansible-playbook -i configs/inventory playbooks/bind9/bind9-dns.yml
```

No tags at all — every play in the file runs, base install/config included, not just zone
generation. This is the one to reach for after adding real `devices.csv` rows that need to
show up in DNS (as opposed to a routine refresh of already-correct zone content, which only
needs `--tags zones-full,reload`).

**The trap this file's own header warns about, hit for real this session**: an earlier,
narrower run used `--tags zones,reload` — `zones` (Play 1) is superseded by `zones-full`
(Play 2) and only ever regenerates zones from its own old, hardcoded `SUFFIX_MAP`. It never
reads `devices.csv` at all, so two freshly-added devices (`EXAPVEVRK001`, `EXABMCVRK001`)
sat correctly in the repo's generated data but never made it into the live zone — `host
exapvevrk001 192.168.139.8` kept returning `NXDOMAIN` until the full, untagged run above
actually ran `zones-full`.

Real captured output from that run, confirming success:

```text
[+]   EXADNSVRK001      ════════════════════════════════════════════════════════════════
                        BIND9 DNS SETUP COMPLETE — EXADNSVRK001
                      ════════════════════════════════════════════════════════════════
                        Zone        : jukebox.internal
                        DNS IP      : 192.168.139.8 (active)
                        Self-test   : forward + PTR lookups both passed
                      ════════════════════════════════════════════════════════════════
```

```bash
$ host exapvevrk001 192.168.139.8
exapvevrk001.jukebox.internal has address 192.168.139.5
```

---

## Understanding an Ansible Playbook Command

The following command was executed:

```text
ansible@exadnsvrk001[~/ansible]$ ansible-playbook -i /home/ansible/ansible/configs/inventory --limit ansiblehosts --check --diff --step playbooks/linux/tools.yml
```

Breaking this down:

| Option | Purpose |
|--------|---------|
| `ansible-playbook` | Executes a playbook |
| `-i` | Specifies the inventory — must be a path *containing* `group_vars`/`host_vars` for those to be picked up (see above) |
| `--limit ansiblehosts` | Restricts execution to hosts in the `ansiblehosts` group |
| `--check` | Dry-run mode |
| `--diff` | Show changes that would occur |
| `--step` | Prompt before every task |
| `playbooks/linux/tools.yml` | Playbook being executed |

---

## Example Playbook Execution

The following output was captured exactly during execution:

```text
ansible@exadnsvrk001[~/ansible]$ ansible-playbook -i /home/ansible/ansible/configs/inventory --limit ansiblehosts --check --diff --step playbooks/linux/tools.yml
[WARNING]: Deprecation warnings can be disabled by setting `deprecation_warnings=False` in ansible.cfg.
[DEPRECATION WARNING]: community.general.yaml has been deprecated. The plugin has been superseded by the the option `result_format=yaml` in callback plugin ansible.builtin.default from ansible-core 2.13 onwards. This feature will be removed from collection 'community.general' version 12.0.0.

PLAY [Deploy common tools] *************************************************************************************************************************************************
Perform task: TASK: Gathering Facts (N)o/(y)es/(c)ontinue: y

Perform task: TASK: Gathering Facts (N)o/(y)es/(c)ontinue: *****************************************************************************************************************

TASK [Gathering Facts] *****************************************************************************************************************************************************
ok: [192.168.139.8]
Perform task: TASK: Install common packages (N)o/(y)es/(c)ontinue: y

Perform task: TASK: Install common packages (N)o/(y)es/(c)ontinue: *********************************************************************************************************

TASK [Install common packages] *********************************************************************************************************************************************
The following additional packages will be installed:
  libblas3 liblinear4 liblua5.4-0 nmap-common
Suggested packages:
  liblinear-tools liblinear-dev ncat ndiff zenmap
The following NEW packages will be installed:
  libblas3 liblinear4 liblua5.4-0 nmap nmap-common
0 upgraded, 5 newly installed, 0 to remove and 0 not upgraded.
changed: [192.168.139.8]
Perform task: TASK: Set default shell to zsh for ansible user (N)o/(y)es/(c)ontinue: y

Perform task: TASK: Set default shell to zsh for ansible user (N)o/(y)es/(c)ontinue: ***************************************************************************************

TASK [Set default shell to zsh for ansible user] ***************************************************************************************************************************
changed: [192.168.139.8]

PLAY RECAP *****************************************************************************************************************************************************************
192.168.139.8             : ok=3    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

---

## Understanding the Output

The play begins with:

```text
PLAY [Deploy common tools]
```

This indicates that Ansible has started executing a play called `Deploy common tools`.

The first task:

```text
TASK [Gathering Facts]
ok: [192.168.139.8]
```

collects information about the remote host including operating system, hostname, network interfaces, CPU information, and memory information.

The following line:

```text
changed: [192.168.139.8]
```

does **not** indicate an error. It indicates that Ansible believes a change would be required. Because this run used `--check`, the changes were simulated rather than executed.

---

## Idempotency — Why Re-running a Playbook Is Safe

A playbook is **idempotent** when running it twice produces the same end state as running
it once — the second run reports `ok` (nothing to do) for anything the first run already
handled, rather than erroring or re-doing work. This isn't automatic; Ansible modules are
generally written to check state before changing it, but a playbook can still break
idempotency if it's written carelessly (e.g. a `command:` task that isn't itself
idempotent, or `hosts:` that resolves inconsistently between runs).

A concrete example, found during a 2026-07-09 audit of the `windows_bootstrap` chain: two
of its numbered plays (`10-rename.yml`, `40-choco-packages.yml`) had
`hosts: "{{ target_hosts | default(target | default('all')) }}"`, while every other play in
the chain used the simpler `hosts: "{{ target | default('all') }}"`. The difference matters:
if an earlier play in the same run had set `target_hosts` as a fact (via `set_fact`), those
two plays would keep targeting the stale value instead of picking up the
[dynamically-registered](#dynamic-inventory-registration--add_host) group membership from
`add_host` in `00-preflight.yml` — silently bootstrapping the wrong host, or none at all, on
a re-run in the same process. The fix was mechanical (make the `hosts:` line consistent
across every numbered play), but finding it required tracing exactly what each play's
`hosts:` pattern resolves to on both a first run and a second, back-to-back run — not just
reading each file in isolation.

**Practical takeaway for a beginner:** it's always safe, and a good habit, to re-run a
playbook you've already run — a healthy chain converges to the same state regardless of
starting point, and a play reporting a change on a run where you expected none is a signal
worth investigating, not ignoring.

---

## Renumbering / Reworking Live Conventions

Idempotency (above) covers re-running a playbook with the **same** inputs. This section
covers a different, riskier case: changing what the **default** or convention itself is —
renumbering a scheme, renaming a role, moving a value from one file to another. The moment
you change a default in code, you've created a split: every *new* thing built from that
point on gets the new value, but everything already built and running still has the old one,
until someone deliberately goes and migrates it. Code and live reality now disagree, and
they'll keep disagreeing until you close the gap on purpose. This is a distinct category of
change from ordinary feature work, and it deserves its own checklist — this section is that
checklist, kept general on purpose, because WireGuard tunnel addressing won't be the last
thing in this estate that needs renumbering or reworking.

### The checklist

1. **Find every place the old value is hardcoded or defaulted — not just the "obvious" file.**
   Grep the whole repo, not just the Ansible role you're thinking about. This estate has more
   than one implementation of some things: an Ansible role *and* a break-glass script that
   predates it and still gets used (`firewallme.sh`, `bindme.sh`, `rudderme.sh`, `ansibleme.sh`
   — see the top-level `README.md`'s bootstrap section for why they're kept). If the Ansible
   default changes and the break-glass script's matching default doesn't, the next person who
   reaches for the break-glass path (by design, exactly when Ansible *can't* help) builds
   something inconsistent with everything Ansible now expects.

2. **Don't trust a grep match at face value — read what the surrounding code actually does.**
   A literal string match for the old value can turn up something that looks related but
   isn't. (Real example, immediately below: `firewallme.sh` had *two* things containing
   `.2` near WireGuard — only one of them was the convention being changed.) Skimming the
   surrounding logic before editing is not optional here; a wrong edit in this category
   doesn't fail loudly, it silently reworks the wrong thing.

3. **Change every default together, in one commit.** A partial change — spoke default
   updated, but the hub-side registration default left on the old value — doesn't fail
   loudly. It creates a mismatch between what a newly-built spoke actually uses and what the
   hub expects from it, and that class of mismatch tends to fail *silently* (traffic just
   doesn't arrive, rather than an error telling you why) — worse than a hard failure, because
   nothing points you at the cause.

4. **Before touching anything already live, confirm there's a recovery path that doesn't
   depend on the thing you're changing.** If the only way to reach a box is through the exact
   mechanism you're about to change mid-flight, a mistake mid-migration can lock you out
   entirely. If there's an independent path (see the worked example below), a mistake is just
   something to fix on the next run, not an incident.

5. **Migrate already-live instances one at a time, verifying each before moving to the
   next.** Not a "re-run everything at once and see what happens" blast — confirm the first
   one actually came back up correctly before doing the second.

6. **Update every doc that states the old value as current, in the same pass** — not "later."
   A doc that's briefly wrong because you haven't gotten to it yet is exactly how these drift
   in the first place (see the repo-wide documentation audit this same guide's changelog
   references).

### Worked example: WireGuard spoke tunnel IP, `.2` → `.1` (2026-07-19)

**What changed:** every site firewall's own WireGuard tunnel address, within its own
`10.0.<site-octet>.0/24`, moves from `.2` to `.1` — matching the hub's (CLD's) own tunnel
address within *its* `/24` (`10.0.69.1`). This is a **readability convention, not a protocol
requirement** — confirmed safe before starting, not assumed: each site's `/24` is a private,
non-overlapping tunnel network (FAL's `10.0.76.0/24` and CLD's `10.0.69.0/24` never collide,
regardless of what last octet either uses), and the hub routes to each spoke via an explicit
`/32` host route (`add-wg-spoke.yml`), not subnet adjacency. The payoff is purely human: any
firewall's own wg0 address is now always `.1` in its own tunnel `/24`, full stop, instead of
"`.1` if it's the hub, `.2` if it's a spoke."

**Every place the old default lived (step 1 above, applied for real):**

| File | What it was |
|------|-------------|
| `ansible/playbooks/firewallme/roles/firewall/tasks/00_preflight_3_ask.yml` | The interactive prompt's default, for a spoke's own tunnel IP |
| `ansible/playbooks/firewallme/playbooks/add-wg-spoke.yml` | `spoke_tunnel_ip`'s default — what the **hub** registers as that peer's allowed source address |
| `bootstrap/web/provision/firewallme.sh` | `WG_SPOKE_DEFAULT_IP` — the break-glass script's own mirror of the same prompt |

**The trap step 2 warns about, hit for real while making this change:** `firewallme.sh` also
has a `SPOKE_TUNNEL_OCTET=2` variable, a few hundred lines away from `WG_SPOKE_DEFAULT_IP`,
that looks like the same thing on a bare grep for `.2`. It isn't. It's a sequential-slot
counter used only when interactively building a **hub** and adding multiple spoke *peers* to
it by hand — each new peer gets the next free octet **inside the hub's own `/24`**
(`10.0.69.2`, `10.0.69.3`, ...), a completely different, older addressing scheme from a time
before every site had its own `/24`. Changing it to match would have been wrong on two counts:
wrong scheme, and it would have collided with the hub's own `.1` inside that same `/24`. It
was read in full and left untouched.

**Why this is safe to roll out to live spokes one at a time (step 4 above):** Ansible reaches
every firewall over its VRK/WAN address, not over the WireGuard tunnel itself — nftables
always allows SSH from the VRK network regardless of the WireGuard tunnel's state (see
`group_vars/firewalls/main.yml`'s WAN-IP self-heal notes). A live spoke's WireGuard tunnel
being briefly down mid-migration does **not** lock Ansible out of managing that box. The
worst case is a temporary gap in that one site's cross-site traffic (AD replication, DFS, and
similar) — not an incident, and always recoverable by re-running the same two playbooks.

**Per-spoke migration procedure** (do this once per already-deployed spoke, one at a time):

1. Re-run the firewall role against the spoke. This is a full interactive run — every prompt
   in `00_preflight_3_ask.yml` fires again, not just the tunnel-IP one; accept the new `.1`
   default when it's asked. This rewrites the spoke's `wg0.conf` `Address =` line and
   restarts `wg-quick@wg0`.
2. Re-run `add-wg-spoke.yml` against the hub (`EXAFWLCLD001`) for that site. This updates the
   hub's `AllowedIPs` entry for that one spoke from `.2/32` to `.1/32` — the `blockinfile`
   marker is per-site, so this only touches that spoke's own `[Peer]` block, nothing else on
   the hub.
3. Verify on both ends: `wg show wg0` should show a recent handshake; `ping` the other side's
   tunnel IP.
4. If it doesn't come back: nothing is lost. SSH access is unaffected (see above) — check
   `journalctl -u wg-quick@wg0` on the spoke, then re-run both playbooks again. Neither is
   destructive or one-shot.

CLD's own hub tunnel IP is unaffected by any of this — it was already `.1`.

**Practical takeaway for a beginner:** a changed default is not the same thing as a completed
change. Everything built before the change still has the old value until someone deliberately
migrates it — and the migration deserves at least as much care as the original code change,
because it's the part that touches things already running.

---

## Understanding `ansible.cfg`

`ansible.cfg` is generated automatically by `ansibleme.sh` when the Ansible control node is
first set up, and is also committed to the repo (`ansible/ansible.cfg`) as the actual source
of truth — every setting and value below is taken directly from that committed file, with its
inline comments trimmed for readability (see `ansible/ansible.cfg` itself for the full comments,
including the 2026-07-09 ini-section-bug story referenced below):

```ini
[defaults]
interpreter_python = auto_silent
host_key_checking  = True

# firewallme's playbook uses a real Ansible role at a non-default location.
roles_path = playbooks/firewallme/roles

# Single, consolidated inventory location (see "Inventory and group_vars" above).
inventory = /home/ansible/ansible/configs/inventory

remote_user = ansible
private_key_file   = /home/ansible/ansible/configs/ansible-id_rsa

# Colourised output — see "Colourised Output" section below.
callback_plugins   = /home/ansible/ansible/callback_plugins
stdout_callback    = exa_pretty
callback_whitelist = exa_pretty
result_format      = yaml
bin_ansible_callbacks = True

forks = 50
timeout = 5
retry_files_enabled = True
retry_files_save_path = /tmp
display_skipped_hosts = False
display_failed_stderr = False

[callback_exa_pretty]
suppress_unreachable   = True
show_unreachable_hosts = False

[privilege_escalation]
become        = False
become_method = sudo
become_user   = root

[ssh_connection]
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=accept-new
pipelining = True
connect_timeout = 5

[persistent_connection]
command_timeout = 30
connect_retry_timeout = 15
```

Important settings and why they differ from a default Ansible installation:

| Setting | Value | Reason |
|---------|-------|--------|
| `host_key_checking` | `True` | `accept-new` (below) handles new hosts correctly, so `True` here only ever catches a *changed* fingerprint — a MITM safeguard, not a nuisance |
| `roles_path` | `playbooks/firewallme/roles` | The only role in this repo lives outside Ansible's playbook-relative default location |
| `inventory` | single path | See [Inventory and group_vars](#inventory-and-group_vars--the-part-that-isnt-optional) — this used to be two paths with incompatible group structures |
| `become` | **`False`** | Global privilege escalation is deliberately **off** — see [Understanding Sudo and Become](#understanding-sudo-and-become) below, this is not a mistake |
| `StrictHostKeyChecking` | `accept-new` | Trusts a host's key on first connect, but hard-fails on a *changed* key — unlike `no`, which silently accepts a changed key too |
| `forks` | `50` | Default is 5 — increased for an estate this size |
| `timeout` / `connect_timeout` | `5` | Short — hosts may be powered off and long waits aren't useful |
| `[persistent_connection]` | present | Required for network modules and larger parallel runs |

> **Note on `StrictHostKeyChecking=accept-new`:** this is a deliberate security improvement over `no`. With `no`, a changed host key (e.g. from a rebuilt node or a MITM attack) is silently accepted. With `accept-new`, new hosts are trusted on first connect, but a changed fingerprint for a known host causes a hard failure with a clear error message.

> **A real lesson in ini section semantics (2026-07-09):** an earlier version of this
> repo's committed `ansible.cfg` had `forks`, `timeout`, `retry_files_enabled`,
> `retry_files_save_path`, `display_skipped_hosts`, and `display_failed_stderr` sitting
> textually *after* a `[callback_exa_pretty]`/`[ssh_connection]` section header instead of
> under `[defaults]`. The file still parsed without error — ini section membership is purely
> positional (every `key = value` belongs to whichever `[section]` header appeared most
> recently above it), so there was no syntax error to catch, just six settings that were
> silently using Ansible's built-in defaults instead of the values written in the file
> (`forks=5` not `50`, `timeout=10s` not `5s`, etc.). Confirmed with Ansible's own
> `ansible.config.manager.ConfigManager` (`get_config_value_and_origin()` reports whether a
> setting came from the file or from Ansible's built-in default) — `ansible-config dump
> --only-changed -c ansible.cfg` is the quicker command-line equivalent for a spot check.
> **The takeaway: a config file that parses cleanly is not the same as a config file that
> does what it looks like it does** — worth an occasional `ansible-config dump --only-changed`
> against production to confirm the settings you expect are actually the ones in effect.

---

## Colourised Output — exa_pretty Callback

All Example Music Ansible playbooks use a custom callback plugin (`callback_plugins/exa_pretty.py`) that provides colourised terminal output following the same colour scheme as `firewallme.sh` and `ansibleme.sh`:

| Symbol | Colour | Meaning |
|--------|--------|---------|
| `[+]` | Green | Task ok / no change needed |
| `[→]` | Cyan | Task changed something |
| `[!]` | Yellow | Skipped / warning |
| `[✗]` | Red | Failed / unreachable |

This is enabled in `ansible.cfg` via:

```ini
stdout_callback   = exa_pretty
callback_whitelist = exa_pretty
```

### Verbose output and quiet ("demo") mode

Two independent knobs, added 2026-07-16 after repeatedly needing to fully swap to
`ANSIBLE_STDOUT_CALLBACK=default` just to see one task's real error detail:

**`-v` / `-vv` / `-vvv`** — works the same way it does for `ansible-core`'s own `default`
callback. No extra flags needed beyond the normal verbosity flags:

```bash
ansible-playbook -i configs/inventory playbooks/linux/tools.yml -v
```

At verbosity 1 and above, the full result dict is printed underneath every ok/changed/failed/
skipped/unreachable line — the same detail `-v` always gives you, just indented to stay readable
under `exa_pretty`'s formatting instead of replacing it. No change at all with no `-v` flags.

**`low_noise` mode** — for demos, or when you just want to see what actually changed without
pages of `no change` lines scrolling past. Skipped lines still show (useful to see which
conditional branches were skipped); only ok/no-change lines are suppressed. Two ways to turn it
on:

```bash
# per-run, no config file changes needed
ANSIBLE_EXA_LOW_NOISE=true ansible-playbook -i configs/inventory playbooks/linux/tools.yml
```

```ini
# or permanently, in ansible.cfg
[callback_exa_pretty]
low_noise = True
```

The two combine — `low_noise` still suppresses the no-change lines even with `-v` on, so you get
full detail on the changed/failed/skipped lines from a `low_noise` run without the no-change
noise burying them.

### Colour Constants — group_vars/all/colours.yml

The same ANSI colour codes used in the shell scripts are available as Ansible variables to all playbooks and roles. They are defined in `group_vars/all/colours.yml` and loaded automatically for every host in every play — no `vars_files` reference is needed.

```yaml
# group_vars/all/colours.yml
# Example Music Limited — ANSI colour constants
# Available in all playbooks, roles, and task files as {{ _c.G }}, {{ _c.R }} etc.
#
# Mapping mirrors firewallme.sh / ansibleme.sh line 128:
#   RED    \033[0;31m  → _c.R
#   GREEN  \033[0;32m  → _c.G
#   YELLOW \033[1;33m  → _c.Y
#   ORANGE \033[38;5;208m → _c.O
#   CYAN   \033[0;36m  → _c.C
#   WHITE  \033[1;37m  → _c.W
#   NC     \033[0m     → _c.NC (reset)

_c:
  R:  "\e[0;31m"
  G:  "\e[0;32m"
  Y:  "\e[1;33m"
  O:  "\e[38;5;208m"
  C:  "\e[0;36m"
  W:  "\e[1;37m"
  NC: "\e[0m"
```

Because it is in `group_vars/all/`, the `_c` dict is available everywhere without any import. Use it in `debug` task messages and `pause` prompt strings:

```yaml
- name: Show a colourised message
  ansible.builtin.debug:
    msg: "{{ _c.G }}[+]{{ _c.NC }} Task completed on {{ _c.W }}{{ inventory_hostname }}{{ _c.NC }}"

- name: Prompt operator with colour
  ansible.builtin.pause:
    prompt: |
      {{ _c.Y }}[!]{{ _c.NC }} Review the above carefully.
      Type {{ _c.G }}yes{{ _c.NC }} to proceed
```

> **Why `group_vars/all/` and not the role's `vars/` directory?** Placing it in `group_vars/all/` means the colour constants are available to every play — Windows playbooks, the bootstrap playbook, the firewall role, and any future playbooks — without needing a `vars_files:` reference in each one. A `vars/` file inside a role is only loaded when that role runs.

---

## Understanding Sudo and Become

**Privilege escalation is off by default in this repo** — `ansible.cfg`'s
`[privilege_escalation]` section sets `become = False` globally, not `True`. This is
deliberate, not an oversight: Windows hosts connect over SSH but have no `sudo` concept at
all, so a global `become = True` would break every Windows playbook the moment it tried to
escalate. Become is switched on only where it's actually needed — for the `linux` group —
via `group_vars/linux/main.yml`:

```yaml
# group_vars/linux/main.yml
# Privilege escalation for all Linux hosts.
ansible_become:        true
ansible_become_method: sudo
ansible_become_user:   root
```

`group_vars/all/main.yml` (loaded for every host, Linux and Windows alike) deliberately has
no `become` setting at all — only `group_vars/linux/main.yml` sets it, so only hosts in the
`linux` group ever escalate. This was "battle-tested" (`ansibleme.sh`'s own changelog wording)
after a global `become = True` genuinely broke Windows connectivity in an earlier version of
this repo — if you're tempted to move privilege escalation back to the global `[defaults]`/
`[privilege_escalation]` block for convenience, don't; it will break Windows again.

For a Linux host in the `linux` group, becoming root still requires the target host to
actually grant it — which is where passwordless sudo comes in:

```text
ansible@exadnsvrk001[~/ansible]$ sudo cat /etc/sudoers.d/ansible

# Ansible automation - full passwordless sudo
ansible ALL=(ALL) NOPASSWD: ALL
```

A common troubleshooting step is verifying whether passwordless sudo is functioning correctly on the target host itself, independent of what Ansible thinks it configured.

---

## Investigating Passwordless Sudo

The following commands were used during troubleshooting.

Verify group membership:

```text
ansible@exadnsvrk001[~/ansible]$ groups

ansible adm cdrom sudo dip users kvm
```

Verify effective permissions:

```text
ansible@exadnsvrk001[~/ansible]$ sudo -l

Matching Defaults entries for ansible on exadnsvrk001:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin, use_pty

User ansible may run the following commands on exadnsvrk001:
    (ALL : ALL) ALL
    (ALL) NOPASSWD: ALL
```

The important line is:

```text
(ALL) NOPASSWD: ALL
```

which confirms that passwordless sudo has been granted.

### When the ansible account is rejected entirely — not just for sudo

Real finding, live, 2026-07-16: a firewall node rejected *every* login as `ansible` — console and
SSH public-key auth both, not password auth specifically. `sudo -l`/groups checks above are moot if
you can't authenticate as the account at all in the first place.

Cause: `firewallme.sh` used to call `passwd -l ansible` right after creating the account, intending
"key/sudo only, no password auth." With `UsePAM yes` set (standard on every hardened SSH config in
this repo), `pam_unix`'s account phase rejects a *locked* account for every login method, not just
password — the lock and "no password set" are different things to PAM, and locking blocks
everything. Fixed at the source (the script now uses `usermod -p '*'` — sets a definite,
non-matching password hash instead of an administrative lock — never enables password auth, but
doesn't block key auth either), plus a healing task in `linux/tools.yml` for any node already
created under the old behaviour:

```bash
# what the healing task does, if you need to check or fix one by hand
sudo passwd -S ansible   # look for L (locked) in the second field
sudo usermod -U ansible  # clears the lock -- does NOT set or enable a real password
```

Don't reach for `passwd -u` here — on an account that never had a real password hash at all
(exactly what a bare `useradd` without `-p` leaves), `passwd -u` refuses outright ("would result in
a passwordless account") rather than clearing the lock. `usermod -U` doesn't have that guard.

---

## Verifying Sudoers Configuration

The configuration file permissions were checked:

```text
ansible@exadnsvrk001[~/ansible]$ ls -l /etc/sudoers.d/ansible

-r--r----- 1 root root 78 Jun 14 11:19 /etc/sudoers.d/ansible
```

The sudoers configuration was validated:

```text
ansible@exadnsvrk001[~/ansible]$ sudo visudo -c

/etc/sudoers: parsed OK
/etc/sudoers.d/README: parsed OK
/etc/sudoers.d/ansible: parsed OK
```

This confirms there are no syntax errors.

---

## Understanding Include Order

The following commands were executed:

```text
ansible@exadnsvrk001[~/ansible]$ sudo grep -n "sudo" /etc/sudoers
sudo grep -n "includedir" /etc/sudoers

49:# Allow members of group sudo to execute any command
50:%sudo        ALL=(ALL:ALL) ALL

54:@includedir /etc/sudoers.d
54:@includedir /etc/sudoers.d
```

This is important because `@includedir /etc/sudoers.d` appears after `%sudo ALL=(ALL:ALL) ALL`, which means the custom file `/etc/sudoers.d/ansible` is processed afterwards.

---

## Testing Passwordless Sudo Correctly

Many administrators use `sudo -v` when testing sudo. The following commands were used instead:

```text
ansible@exadnsvrk001[~/ansible]$ sudo -k
sudo id

uid=0(root) gid=0(root) groups=0(root)
```

and:

```text
ansible@exadnsvrk001[~/ansible]$ sudo -k
sudo whoami

root
```

These tests prove that sudo can execute privileged commands without prompting for a password.

---

## Reboot Verification

After troubleshooting, the server was rebooted:

```text
ansible@exadnsvrk001[~/ansible]$ sudo reboot
ansible@exadnsvrk001[~/ansible]$ Connection to 192.168.139.8 closed by remote host.
Connection to 192.168.139.8 closed.
```

The administrator then reconnected:

```text
knightmare@orangepipc:~$ ssh ansible@192.168.139.8
ansible@192.168.139.8's password:
```

The login banner confirmed successful startup:

```text
╔══════════════════════════════════════════════════════════════╗
║           EXAMPLE MUSIC LIMITED: exadnsvrk001            ║
╚══════════════════════════════════════════════════════════════╝

  Role     : DNS Server -- jukebox.internal
  Zone     : jukebox.internal  (708 A records, serial serial)

  ── Network ──────────────────────────────────────────────────
    DNS IP   : 192.168.139.8
    BIND9    : active

  ── System ───────────────────────────────────────────────────
    Uptime   : up 1 minute
    Load     : 0.27 0.15 0.06
    Memory   : 189MB used of 425MB
    Disk /   : 1.8G used of 3.7G (52%)
```

Passwordless sudo was tested again:

```text
ansible@exadnsvrk001[~]$ sudo -k
sudo whoami

root
```

System uptime immediately after reboot:

```text
ansible@exadnsvrk001[~]$ uptime
 18:39:12 up 1 min,  1 user,  load average: 0.25, 0.15, 0.06
```

This confirms that the sudo configuration remained functional after reboot.

---

## Recommended Workflow for New Administrators

Before executing any unfamiliar playbook:

```bash
ansible-playbook -i configs/inventory --limit HOSTGROUP --check --diff --step playbook.yml
```

Review every task carefully. Once satisfied:

```bash
ansible-playbook -i configs/inventory --limit HOSTGROUP playbook.yml
```

Always verify inventory, target hosts, become configuration, and sudo permissions before running production changes. Specifically:

- **`-i` must point at `configs/inventory`** (or wherever `ansible.cfg`'s `inventory =`
  points) — a bare IP or a path that doesn't contain `group_vars`/`host_vars` will silently
  skip every group-specific variable. See [Inventory and group_vars](#inventory-and-group_vars--the-part-that-isnt-optional).
- **A brand-new host that isn't in the inventory yet** isn't necessarily a blocker — some
  chains (`windows_bootstrap`) register it dynamically for the run via `add_host`. Check
  whether the playbook you're running does this before hand-editing an `.ini` file.
- **Don't expect `become` to "just work"** on a host outside the `linux` group — it's off
  by default everywhere else, deliberately.
- **A second run reporting unexpected `changed` tasks is worth investigating**, not
  re-running until it goes green — see [Idempotency](#idempotency--why-re-running-a-playbook-is-safe).

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-14 | Initial document |
| 2026-06-20 | Updated `ansible.cfg` to reflect current `ansibleme.sh`-generated config (`ansible.builtin.default` callback, `result_format`, `StrictHostKeyChecking=accept-new`, `forks`, `[persistent_connection]`) |
| 2026-06-20 | Added colourised output section — `exa_pretty` callback and `group_vars/all/colours.yml` |
| 2026-07-09 | Major expansion: added "How This Repository Is Organised" (`benarbejde/` single source of truth), "Inventory and group_vars" (the `host_group_vars` plugin mechanism, why it only auto-loads from inside the loaded inventory path, and the symlink-rejected/real-move fix), "Dynamic Inventory Registration" (`add_host` in `windows_bootstrap`'s preflight), and "Idempotency" (the `target`/`target_hosts` `hosts:` pattern bug found in the 2026-07-09 chain audit). Rewrote "Understanding ansible.cfg" against the actual committed `ansible/ansible.cfg` (previous version was stale and internally inconsistent with the Colourised Output section below it — it showed `ansible.builtin.default` as the callback when `exa_pretty` had already been rolled out). Corrected "Understanding Sudo and Become": the previous version stated `become = True` as the current global setting — it is, and must stay, `False`; Linux-only escalation lives in `group_vars/linux/main.yml`, and a global `become = True` previously broke Windows connectivity in production. |
| 2026-07-09 | While writing the `ansible.cfg` section against the real file, found `forks`/`timeout`/`retry_files_enabled`/`retry_files_save_path`/`display_skipped_hosts`/`display_failed_stderr` were textually inside the wrong `[section]` and silently inert — confirmed with `ansible.config.manager.ConfigManager`, not just by reading the file. Fixed the real `ansible/ansible.cfg` (all 6 now verified reading from the file), and added the "real lesson in ini section semantics" callout in "Understanding ansible.cfg" above. |
| 2026-07-18 | Added "Bootstrapping the Base Nodes" — a worked, address-accurate walkthrough building `EXAANSCLD001`, `EXAPVECLD001`, `EXAFWLCLD001`, and `EXADCSCLD001` from a bare Proxmox hypervisor, plus `EXAFWLFAL001` as the WireGuard end-to-end proof. Every address traced against `sites.csv`/`devices.csv`/`address_policy.json` (caught and corrected one real discrepancy along the way: CLD's PVE1 slot is `192.168.69.5`, on CLD's own LAN, not `192.168.139.x`) and against `docs/proxmox/Procedure-PVE-Node-Onboarding.md`'s own worked example. Also found `docs/buildsheets/buildsheet-firewall.md`'s `wget` for `firewallme.sh` omits the real `/provision/` path segment — flagged, not fixed (out of scope for this section). |
| 2026-07-19 | Added "Renumbering / Reworking Live Conventions" — a general checklist for any future change to a default/convention that already has live instances built against the old value (find every hardcoded copy including break-glass script mirrors, don't trust a grep match without reading the surrounding code, change every default together, confirm a recovery path independent of what's changing, migrate live instances one at a time, update docs in the same pass), with the 2026-07-19 WireGuard spoke tunnel IP change (`.2` → `.1`) as the first worked example — including a real trap hit while making it (`firewallme.sh`'s unrelated `SPOKE_TUNNEL_OCTET` legacy hub-building counter, which looked like the same convention on a bare grep and wasn't). |
| 2026-07-24 | Reviewed "5. Proving WireGuard end-to-end" against a real live WireGuard debug session (`EXAFWLCLD001`/`EXAFWLBRT001`) — the core walkthrough was already accurate, but the verification step only checked tunnel-level health (`wg show`, ping the hub's own tunnel address), which is exactly what looked perfect for hours while a real bug (CLD's `nftables` black-site exclusion dropping all `wg0 → LAN` forward traffic, `19dd5da`) silently blocked every spoke from reaching anything behind the hub's LAN. Added a callout with the real LAN-client test that actually catches this class of bug, plus a short note on the tunnel-IP input validation added the same session (`6c3527b`). |
| 2026-08-03 | Added "Real-World Invocations — Day 2: Already-Onboarded Hosts", three worked examples of the same playbooks used above but invoked against hosts that already exist, per Robert's request: a routine firewall re-run (`90-firewall.yml`, plus why `serial: 1` — added 2026-07-31 — matters the moment more than one host is targeted at once, not for a single `-e target=`); a domain controller re-run confirming the `windows_bootstrap` `[B0]` DefaultShell failsafe actually holds after its own `ansible_shell_type` bug was fixed (`00-preflight.yml`'s `bootstrap` tag has to run, so this is the full form, not `windows_dc/README.md`'s narrower "DC stages only"); and a full, untagged `bind9-dns.yml` rebuild of `EXADNSVRK001`, including the real `--tags zones,reload` trap hit this session (the old, superseded Play 1 — never reads `devices.csv`, so two freshly-added devices sat correctly generated but never made it into the live zone until the full run actually ran `zones-full`), with the real captured completion banner and `host` lookup proving it worked. |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
