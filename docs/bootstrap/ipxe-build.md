# iPXE Build Runbook

## Changelog

| Date | Change |
|---|---|
| 2026-03-03 | Initial document — dual-console build (VGA + serial), config/local override, deployment to Proxmox storage |


**Example Music Limited — Internal Infrastructure**

This runbook covers building a custom iPXE ISO with an embedded boot script, including dual-console support (VGA + serial) for use with Proxmox VE VMs.

---

## Background

The iPXE ISO attached to every VM at creation time (`ide2`) is a custom build with the `proxmox.ipxe` script baked in. When the VM boots cold with an empty disk, it falls through to the ISO, runs the script, and chainloads the Proxmox automated installer from `http://192.168.139.50`.

### Why a custom build?

- **Embedded script** — no DHCP/TFTP required, the boot logic is in the ISO itself
- **Dual console** — both VGA and serial (COM1 / ttyS0) are active simultaneously, so the iPXE menu appears correctly regardless of whether the VM uses VGA or serial console. This is required for FWL, RTR, SBC, NIX and other headless roles.

### Dual console — how it works

iPXE outputs to all enabled consoles simultaneously. In a Proxmox QEMU VM, the serial port is a virtualised device (`-serial socket`) — it is **not** BIOS console redirection. This means there is no double-character problem that affects physical machines with BIOS serial redirection enabled. Both consoles receive clean, independent output.

| Console | How to connect |
|---|---|
| VGA | Proxmox web UI → VM → Console tab |
| Serial (ttyS0) | `qm terminal <VMID>` on the Proxmox node |

---

## Build Machine

The ISO is built on a Linux node that has the iPXE source already cloned. The same machine was used for the original build. You need:

- `git` — to pull updates
- `gcc`, `make`, `binutils` — standard build tools
- `liblzma-dev` (or `xz-devel`) — required for iPXE compression
- `mtools` — for ISO generation

On Debian/Ubuntu:
```bash
apt install git gcc make binutils liblzma-dev mtools isolinux
```

On RHEL/CentOS/Rocky:
```bash
dnf install git gcc make binutils xz-devel mtools syslinux
```

---

## Repository Layout

```
ipxe/
└── src/
    ├── config/
    │   ├── console.h          ← upstream default (do not edit)
    │   ├── serial.h           ← upstream default (do not edit)
    │   └── local/
    │       └── console.h      ← our override (created once, survives git pull)
    └── bin/
        └── ipxe.iso           ← build output
```

The `config/local/` directory is included **after** the main config headers, so anything defined there overrides the upstream defaults. This keeps the working tree clean and means `git pull` never clobbers your settings.

---

## One-time Setup — Console Override

This only needs to be done once after cloning. The file persists across builds and `git pull` updates.

```bash
cd /path/to/ipxe/src

mkdir -p config/local

cat > config/local/console.h << 'EOF'
/*
 * Local console override — Example Music Limited
 *
 * Enable both VGA and serial simultaneously.
 * Serial defaults to COM1 (ttyS0) at 115200 8n1 — matches QEMU default.
 * See config/serial.h for COM port / speed options if needed.
 */
#define CONSOLE_PCBIOS          /* VGA output */
#define CONSOLE_SERIAL          /* COM1 / ttyS0 at 115200 8n1 */
EOF
```

Verify it was written correctly:
```bash
cat config/local/console.h
```

---

## Building the ISO

Run this from the `src/` directory. Adjust the `EMBED` path to wherever your
`proxmox.ipxe` script lives.

```bash
cd /path/to/ipxe/src

make bin/ipxe.iso EMBED=/path/to/proxmox/proxmox.ipxe
```

The build takes 1–3 minutes. Output will be `bin/ipxe.iso`.

### Example with absolute paths

```bash
cd /opt/ipxe/src

make bin/ipxe.iso EMBED=/srv/www/proxmox/proxmox.ipxe
```

### Confirming the build succeeded

```bash
ls -lh bin/ipxe.iso
# Should be roughly 1–2MB
```

---

## Deploying the ISO

Copy the finished ISO to the Proxmox storage that `create-vm.py` presents at the ISO selection step. Typically this is the `local` storage ISO directory:

```bash
scp bin/ipxe.iso root@192.168.139.50:/var/lib/vz/template/iso/ipxe-proxmox.iso
```

Or if building directly on the Proxmox node:

```bash
cp bin/ipxe.iso /var/lib/vz/template/iso/ipxe-proxmox.iso
```

The script will enumerate available ISOs from that path — the new build will appear in the selection menu automatically.

> **Naming convention:** `ipxe-proxmox.iso` — keep this consistent so existing
> VMs that reference it by name are not broken when you rebuild.

---

## Rebuilding After Changes

If `proxmox.ipxe` changes (e.g. new bootstrap server IP, new menu options), rebuild the ISO:

```bash
cd /path/to/ipxe/src
make bin/ipxe.iso EMBED=/path/to/proxmox/proxmox.ipxe
scp bin/ipxe.iso root@192.168.139.50:/var/lib/vz/template/iso/ipxe-proxmox.iso
```

No other changes are needed. The `config/local/console.h` override persists and does not need to be recreated.

### Pulling upstream iPXE updates

```bash
cd /path/to/ipxe
git pull
cd src
make bin/ipxe.iso EMBED=/path/to/proxmox/proxmox.ipxe
```

The `config/local/` directory is not tracked by git and will not be touched by `git pull`. Your console override survives.

---

## Changing Serial Port or Speed

The default is COM1 (`ttyS0`) at `115200 baud, 8 data bits, no parity, 1 stop bit` — this matches the QEMU virtual serial port as configured by Proxmox.

If you ever need to change this, create `config/local/serial.h`:

```bash
cat > config/local/serial.h << 'EOF'
/* Use COM2 instead of COM1 */
#define COMCONSOLE COM2

/* Speed — default is 115200, options: 9600 19200 38400 57600 115200 */
#define COMSPEED 115200
EOF
```

Then rebuild. For Proxmox QEMU VMs you should never need to change this.

---

## Troubleshooting

### Menu does not appear on serial console

Check that `config/local/console.h` exists and defines both `CONSOLE_PCBIOS` and `CONSOLE_SERIAL`. Rebuild after confirming.

```bash
cat /path/to/ipxe/src/config/local/console.h
```

### Build fails — missing headers or tools

```bash
# Debian/Ubuntu
apt install liblzma-dev mtools isolinux

# RHEL/Rocky
dnf install xz-devel mtools syslinux
```

### ISO appears empty or too small (< 512KB)

The `EMBED` path is wrong or the script has a syntax error. Check:

```bash
# Verify script exists at the path you passed to EMBED
ls -lh /path/to/proxmox/proxmox.ipxe

# Verify it starts with the iPXE shebang
head -1 /path/to/proxmox/proxmox.ipxe
# Should output: #!ipxe
```

### Double characters on serial output

This should not happen with QEMU virtual serial. If it does, the VM has both QEMU serial **and** BIOS serial redirection active. Check the VM's BIOS settings and disable serial console redirection in the firmware — the iPXE build handles serial output directly and does not need BIOS assistance.

---

## Quick Reference

```bash
# One-time: create console override
mkdir -p /path/to/ipxe/src/config/local
cat > /path/to/ipxe/src/config/local/console.h << 'EOF'
#define CONSOLE_PCBIOS
#define CONSOLE_SERIAL
EOF

# Build
cd /path/to/ipxe/src
make bin/ipxe.iso EMBED=/path/to/proxmox/proxmox.ipxe

# Deploy
cp bin/ipxe.iso /var/lib/vz/template/iso/ipxe-proxmox.iso
```
