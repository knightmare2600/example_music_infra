# Example Music — Keeping Three Ansible Nodes in Sync

## The Problem

You have three Ansible control nodes:

```
ansible-master      (primary site)
ansible-odense      (Odense)
ansible-brockville  (Brockville)
```

All three need the same playbooks, roles, and configs. The master is the source of truth. You want changes to propagate without manual copying, without GitHub/Gitosis, and without fragile cron magic.

------

## Option 1 — lsyncd (Recommended for simplicity)

**What it is:** A daemon that watches the filesystem with inotify and fires rsync the moment a file changes. No cron, no polling, no external service. Ships in Debian repos.

**Topology:** One-way, master → children. Only the master can make authoritative changes. Children receive but do not push back.

### Install on master

```bash
sudo apt install lsyncd
```

### Config — `/etc/lsyncd/lsyncd.conf.lua`

```lua
-- Example Music — lsyncd configuration
-- Pushes /home/ansible/ansible/ to both child nodes on file change

settings {
    logfile    = "/var/log/lsyncd.log",
    statusFile = "/var/log/lsyncd.status",
    nodaemon   = false,
    inotifyMode = "CloseWrite or Modify",
}

-- ── Odense ────────────────────────────────────────────────────────────────────
sync {
    default.rsync,
    source    = "/home/ansible/ansible/",
    target    = "ansible@ansible-odense:/home/ansible/ansible/",
    rsync = {
        archive     = true,
        compress    = true,
        rsh         = "ssh -i /home/ansible/ansible/configs/ansible-id_rsa -o StrictHostKeyChecking=no",
        -- Never delete on target — master adds, children never lose
        delete      = false,
        -- Skip inventory: each site maintains its own
        filter      = { "- configs/inventory" },
    },
    delay = 5,   -- seconds to batch changes before firing rsync
}

-- ── Brockville ────────────────────────────────────────────────────────────────
sync {
    default.rsync,
    source    = "/home/ansible/ansible/",
    target    = "ansible@ansible-brockville:/home/ansible/ansible/",
    rsync = {
        archive     = true,
        compress    = true,
        rsh         = "ssh -i /home/ansible/ansible/configs/ansible-id_rsa -o StrictHostKeyChecking=no",
        delete      = false,
        filter      = { "- configs/inventory" },
    },
    delay = 5,
}
```

### Enable and start

```bash
sudo systemctl enable --now lsyncd
sudo systemctl status lsyncd
```

### What gets excluded

The inventory (`configs/inventory`) is intentionally excluded from sync. Each site needs its *own* inventory pointing at its local hosts. Everything else — playbooks, roles, files, templates — propagates automatically within a few seconds of a save on the master.

### Versioning caveat

lsyncd/rsync has no concept of conflict resolution. If someone edits a file on a child node, the next push from master will silently overwrite it. **Discipline:** Only ever edit on the master. Children are read-only by convention. If that's too loose for you, see Option 3.

------

## Option 2 — Unison (Bidirectional, when any node can be authoritative)

**What it is:** A bidirectional sync tool. Like rsync but it tracks what changed on *both* sides and can merge or flag conflicts. Runs as a daemon or on-demand. No server needed — it speaks directly over SSH.

**When to use it:** If Odense or Brockville staff need to create/edit playbooks locally and have those changes come back to master without a VPN call to someone.

### Install on all three nodes

```bash
sudo apt install unison
```

### Run from master (pulls and pushes in both directions)

```bash
unison /home/ansible/ansible/ ssh://ansible@ansible-odense//home/ansible/ansible/ -batch -auto -prefer=newer -ignore "Path configs/inventory"

unison /home/ansible/ansible/ ssh://ansible@ansible-brockville//home/ansible/ansible/ -batch -auto -prefer=newer -ignore "Path configs/inventory"
```

`-prefer=newer` resolves most conflicts automatically by taking the more recently modified file. `-batch` runs non-interactively. Conflicts that can't be auto-resolved are flagged in the log rather than silently overwriting — which is the key advantage over lsyncd.

To run this on a schedule without cron, you can use a systemd timer (see below) — cleaner than cron and logs to journald.

### Systemd timer (replaces cron — clean, logged, restartable)

```
/etc/systemd/system/ansible-sync-odense.service
[Unit]
Description=Example Music — Sync ansible workdir to Odense
After=network-online.target

[Service]
User=ansible
ExecStart=/usr/bin/unison /home/ansible/ansible/ \
  ssh://ansible@ansible-odense//home/ansible/ansible/ \
  -batch -auto -prefer=newer -ignore "Path configs/inventory"
/etc/systemd/system/ansible-sync-odense.timer
[Unit]
Description=Run ansible-sync-odense every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
sudo systemctl enable --now ansible-sync-odense.timer
systemctl list-timers ansible-sync*
```

Repeat for Brockville. Logs visible with `journalctl -u ansible-sync-odense`.

------

## Option 3 — Local Bare Git Repository (Best for versioning)

**What it is:** A bare git repo hosted on the master. Children do `git pull` to receive updates. Full commit history, rollback, blame — no GitHub, no Gitosis, just git over SSH.

**Topology:** Master hosts the bare repo. Children are clones. Only the master pushes. Children pull.

### One-time setup on master

```bash
# Create the bare repo
sudo -u ansible git init --bare /home/ansible/ansible-repo.git

# Convert the existing workdir into a git repo pointing at it
cd /home/ansible/ansible
sudo -u ansible git init
sudo -u ansible git remote add origin /home/ansible/ansible-repo.git

# First commit — exclude per-site inventory
echo "configs/inventory" >> /home/ansible/ansible/.gitignore
sudo -u ansible git add .
sudo -u ansible git commit -m "Initial commit — Example Music Ansible workdir"
sudo -u ansible git push -u origin main
```

### Clone on each child node

```bash
# Run this on ansible-odense and ansible-brockville
sudo -u ansible git clone ansible@ansible-master:/home/ansible/ansible-repo.git /home/ansible/ansible
```

### Pushing changes (master only)

```bash
cd /home/ansible/ansible
# ... edit a playbook ...
git add playbooks/my_new_playbook.yml
git commit -m "Add: my_new_playbook for Odense VLAN setup"
git push origin main
```

### Pulling on children (manual or via systemd timer)

```bash
cd /home/ansible/ansible && git pull
```

Or automate with a systemd timer using the same pattern as Option 2 but replacing the unison command with `git -C /home/ansible/ansible pull`.

### Why this is the right answer long-term

- Full history — you can see exactly what changed and when
- Rollback is one command: `git revert` or `git checkout <hash>`
- No silent overwrites — conflicts surface as merge errors
- No external service — the bare repo is just a directory on the master
- When you eventually *do* want GitHub, you add a second remote and push to both. Zero rework.

------

## Recommendation for Example Music Training Lab

| Concern                           | Choose   |
| --------------------------------- | -------- |
| Simplest possible setup           | lsyncd   |
| Any node can edit authoritatively | Unison   |
| Want history and rollback         | Bare git |
| Will grow into prod eventually    | Bare git |

**Short answer:** Start with **lsyncd** today — it needs two config files and a `systemctl enable`. When the lab matures and you want history, migrate to the bare git approach (it's a one-afternoon job and lsyncd can run alongside git during transition).

------

## What NOT to sync between sites

Regardless of which method you choose, always exclude:

```
configs/inventory       # Each site has its own hosts
configs/ansible-id_rsa  # Private key should not travel over the wire
                        # (it's already on children from the build playbook)
```

In lsyncd this is the `filter` list. In git this goes in `.gitignore`. In Unison this is the `-ignore` flag.
