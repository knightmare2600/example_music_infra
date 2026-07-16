# Example Music Limited — Linux Account Lockout Recovery

**Doc ID:** OPS-RECOVERY-001
**Scope:** Any Debian Linux node in the estate (firewalls, Proxmox hosts, the Ansible control
node, ordinary Linux servers)
**Applies to:** The `ansible` account rejected entirely — console and SSH both, not just
password auth — with no other working session on the box

---

## When to use this

Every Linux node's `ansible` account is provisioned with a locked/no-password shadow entry by
design — key and passwordless-sudo only, no password ever set. That's intentional and correct.
What is **not** correct, and what this runbook recovers from, is the account being
*administratively locked* (a genuine PAM-level lock, not just "no password") — which gets
rejected for every login method under `UsePAM yes`, not just password auth. If SSH key auth to
`ansible` suddenly stops working with no config change on your end, and console login also
refuses the account, this is almost certainly what's happened.

Root cause and the code fixes already made for it are in `docs/INCIDENT-LOG.md`
(`INC-2026-07-16-ANSIBLE-LOCK`) and this repo's own git history
(`bootstrap/web/provision/firewallme.sh`, `ansible/playbooks/firewallme/roles/firewall/tasks/
05_packages.yml`, `ansible/playbooks/linux/tools.yml`). This runbook is for recovering a node
that's *already* stuck, whether from this specific cause or any other complete lockout.

`root` having no password and no direct login is a **separate, deliberate** Debian convention
(`d-i passwd/root-login boolean false` in the preseed, `PermitRootLogin no` in sshd hardening) —
not a bug, not something to re-enable as part of this procedure.

## Recovery via GRUB rescue mode

Needs physical or hypervisor console access (Proxmox's own VNC/serial console works fine —
this does not require network access to the box at all).

1. **Reboot the node** and interrupt the boot at the GRUB menu (hold Shift, or Esc on some
   Proxmox VM configs, during the very start of boot).
2. Highlight the normal boot entry, press `e` to edit it.
3. Find the line starting `linux` (or `linux16`)ending in something like `ro quiet`. Change `ro`
   to `rw` and append ` init=/bin/bash` at the end of that line.
4. Press `Ctrl+X` or `F10` to boot with the edited entry. This drops straight into a root shell
   with no login prompt at all — single-user recovery mode bypasses normal authentication
   entirely, which is exactly why it works when every normal account is locked out.
5. Confirm root is actually writable — don't assume the `rw` edit above was enough on its own:
   ```bash
   mount -o remount,rw /
   ```
6. Check what's actually locked before changing anything — don't assume, verify:
   ```bash
   passwd -S ansible
   passwd -S root
   ```
   The second field tells you: `L` = locked, `P` = usable password set, `NP` = no password set at
   all. `ansible` showing `L` is the bug this runbook exists for. `root` showing `L` or `NP` is
   normal and expected — leave it alone.
7. Clear the lock on `ansible` only:
   ```bash
   usermod -U ansible
   ```
   Not `passwd -u` — on an account with no real password hash behind the lock at all (which is
   the normal state here), `passwd -u` refuses outright ("would result in a passwordless
   account") rather than clearing it. `usermod -U` has no such guard.
8. Exit the recovery shell and reboot normally:
   ```bash
   exec /sbin/init
   ```
   or simply power-cycle the VM/host from the hypervisor if `exec /sbin/init` doesn't cleanly
   return the system to a normal boot.

## Verify before trusting it

Same standing rule as every other recovery procedure in this estate (see `INCIDENT-LOG.md`'s own
BMC-credential entry for the same discipline applied to a different failure mode) — confirm the
fix actually worked before relying on it for anything further:

```bash
ssh ansible@<node-ip>
```

from a machine that already has the Ansible key deployed. If that succeeds, the account is
usable again. Then, from the Ansible control node, run whichever routine playbook normally
touches this host (`linux/tools.yml`, or the `firewallme` role for firewall nodes) — both now
include a self-healing task that clears an administrative lock on every run, so a recurrence
from an as-yet-undiscovered path gets caught and fixed automatically rather than needing this
manual procedure a second time.

## If `usermod -U` doesn't fix it

That means the actual problem isn't the shadow lock flag — check `/etc/ssh/sshd_config` for
`AllowUsers`/`DenyUsers` restricting the account unexpectedly, check `/etc/security/access.conf`
if it's in use, and check whether sshd itself is even running (`systemctl status sshd` from the
same rescue shell, after `chroot`-ing appropriately if needed). Don't guess further than that
without pulling the actual error text — the same "verify, don't assume" discipline this whole
estate runs on.
