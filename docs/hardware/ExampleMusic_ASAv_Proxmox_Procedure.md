# Example Music Limited — Cisco ASAv QEMU VM on Proxmox

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-08 | Initial document — Cisco ASAv QEMU VM creation on Proxmox |

---

## Standard IP Convention

Every site follows this addressing scheme within its `/24` subnet.
Exceptions are noted in individual site entries.

| Address | Role | Hostname pattern |
|---------|------|-----------------|
| `.1` | Primary internet gateway | `EXAFWL<SITE>001` / `EXARTR<SITE>001` |
| `.2` | BMC pool slot 1 — DRAC / iLO | `EXARAC<SITE>001` |
| `.3` | BMC pool slot 2 — or RAC emulator VM on single-PVE-node sites | `EXARAC<SITE>002` |
| `.4` | BMC pool slot 3 — or RAC emulator VM on two-PVE-node sites | `EXARAC<SITE>003` |
| `.5` | PVE node 1 | `EXAPVE<SITE>001` |
| `.6` | PVE node 2 | `EXAPVE<SITE>002` |
| `.7` | PVE node 3 | `EXAPVE<SITE>003` |
| `.10` | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11` | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.48` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBC<SITE>001` |
| `.100`–`.249` | DHCP pool | — |
| `.250`–`.252` | RT switches | `EXASWI<SITE>001`–`003` |
| `.253` | Secondary internet gateway | — |

> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM. Physical PVE node BMCs consume from `.2` upward; the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.
>
> ***NB: On three-PVE-node sites the pool is fully consumed by physical BMCs.***

---

## 1. Overview

This procedure describes how to deploy a Cisco ASAv (Adaptive Security Appliance — virtual) as a QEMU virtual machine on a Proxmox VE host. The ASAv is used within lab and test environments to provide firewall, NAT, VPN, and security policy functionality equivalent to a physical Cisco ASA appliance.

The deployment uses a Cisco-supplied QCOW2 disk image rather than an ISO, which requires a specific import workflow that differs from a standard Proxmox VM build.

> ℹ The ASAv deployed via this method is bandwidth-limited to **100Kbps** due to the absence of a Cisco licence. This is sufficient for lab, test, and configuration practice purposes. All ASA features are available. For production use, a valid Cisco Smart Licence is required.

---

## 2. Scope

### 2.1 In Scope

- Creating a Proxmox QEMU VM configured correctly for ASAv
- Importing a Cisco ASAv QCOW2 image into the VM
- Initial boot verification and serial console access
- Network interface mapping (Proxmox `net` → ASA interface)

### 2.2 Out of Scope

- Cisco ASAv initial configuration (firewall policies, NAT, VPN — separate procedure)
- Cisco Smart Licensing
- Proxmox cluster or HA configuration
- Production deployment — this procedure is for lab use only

---

## 3. Infrastructure Reference

### 3.1 Proxmox Host

This procedure is performed on any Proxmox VE node in the estate. Substitute the correct hostname and storage name for your target node.

| Item | Example value | Notes |
|------|--------------|-------|
| Proxmox node | `EXAPVEFAL001` | Any PVE node with sufficient resource |
| Storage (LVM) | `local-lvm` | Target storage for the imported disk |
| QCOW2 upload path | `/var/lib/vz/template/qemu/` | Standard Proxmox template path |
| VM ID | `300` | Choose a free ID on your node |
| VM Name | `asav-lab-001` | Follow `EXANIX<SITE>00N` or similar convention |

> ℹ The Cisco ASAv requires a minimum of **2 vCPUs** and **2048MB RAM**. It will boot with 1 vCPU but may exhibit instability under load.

### 3.2 Software Images

Obtain the ASAv QCOW2 image from Cisco's software download portal (requires a valid Cisco account). Tested versions include:

| Image filename | ASA version |
|----------------|-------------|
| `asav941.qcow2` | 9.4.1 |
| `asav983.qcow2` | 9.8.3 |

> ⚠ Do not store Cisco software images in this document or in any public repository. Images must be obtained directly from [Cisco Software Download](https://software.cisco.com/) using a licensed account. See the password manager for Cisco portal credentials.

---

## 4. Prerequisites

1. Proxmox VE node is online and accessible via the web UI (`https://<node-ip>:8006`)
2. SSH access to the Proxmox node is available (for `qm importdisk` command)
3. ASAv QCOW2 image has been downloaded from Cisco and is available locally
4. Sufficient storage space on `local-lvm` — the ASAv disk image is approximately 200MB but expands on import
5. A free VM ID has been identified on the target Proxmox node

---

## 5. Procedure

### 5.1 Create a New Virtual Machine

From the Proxmox web UI, click **Create VM** in the top-right corner.

---

**Step 1 — General**

Set the **VM ID** and **Name** for the new virtual machine.

![Proxmox Create VM — General tab showing VM ID and Name fields](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-1.png)

| Setting | Value |
|---------|-------|
| VM ID | Choose a free ID (e.g. `300`) |
| Name | e.g. `asav-lab-001` |

---

**Step 2 — OS**

Set the OS source to **Do not use any media** and Guest OS type to **Other**.

![Proxmox Create VM — OS tab with 'Do not use any media' and Guest OS 'Other' selected](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-3.png)

| Setting | Value |
|---------|-------|
| ISO Image | Do not use any media |
| Guest OS Type | Other |

> ℹ We are not booting from an ISO — the ASAv uses a QCOW2 disk image that will be imported separately after the VM is created.

---

**Step 3 — System**

Leave all System settings as **defaults**.

![Proxmox Create VM — System tab with all default settings](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-4.png)

---

**Step 4 — Disks**

Set **Bus/Device** to **VirtIO Block**. Leave all other settings as default. This disk is a placeholder and will be removed shortly after the VM is created.

![Proxmox Create VM — Disks tab with Bus/Device set to VirtIO Block](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-5.png)

| Setting | Value |
|---------|-------|
| Bus/Device | VirtIO Block |
| All other settings | Default |

---

**Step 5 — CPU**

Leave as defaults: **1 Socket / 1 Core**.

![Proxmox Create VM — CPU tab showing 1 socket, 1 core defaults](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-6.png)

---

**Step 6 — Memory**

Set memory to **2048 MB**.

![Proxmox Create VM — Memory tab set to 2048MB](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-7.png)

| Setting | Value |
|---------|-------|
| Memory | 2048 MB |

---

**Step 7 — Network**

Leave network defaults. The initial network adapter uses the **VirtIO** model.

![Proxmox Create VM — Network tab with VirtIO model and default bridge](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-8.png)

> ℹ The VirtIO network model uses host CPU cycles to process network traffic. For a lab environment this is acceptable. If you require dedicated network performance, consider using an E1000 model instead.

---

**Step 8 — Confirm**

Review the summary and click **Finish**.

![Proxmox Create VM — Confirm tab showing summary of all settings](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-9.png)

---

### 5.2 Add Additional Hardware

Once the VM has been created, add the following hardware via **Hardware → Add** in the VM's settings:

| Hardware | Quantity | Settings |
|----------|----------|----------|
| Network Device | 3× | Default model and bridge — these become GigabitEthernet0/0, 0/1, 0/2 |
| Serial Port | 1× | Serial port 0 — required for console access |

The VM should now have **4 network interfaces total** (net0–net3) and **1 serial port**.

---

### 5.3 Remove the Placeholder Disk

The disk created during VM setup must be removed before importing the ASAv image:

1. In the VM **Hardware** tab, select the existing hard disk
2. Click **Detach** — it will appear as **Unused Disk 0**
3. Select **Unused Disk 0** and click **Remove**
4. Confirm removal

> ⚠ Ensure you are removing the disk from the correct VM ID. Removing a disk is irreversible.

---

### 5.4 Upload the QCOW2 Image to Proxmox

Copy the ASAv QCOW2 image to the Proxmox node using SCP or SFTP. Upload to the standard QEMU template directory:

```bash
scp asav983.qcow2 root@192.168.76.5:/var/lib/vz/template/qemu/
```

Verify the file is present on the node:

```bash
ls -lh /var/lib/vz/template/qemu/asav983.qcow2
```

---

### 5.5 Import the QCOW2 Image into the VM

SSH into the Proxmox node and run the `qm importdisk` command, substituting your VM ID and image filename:

```bash
qm importdisk 300 /var/lib/vz/template/qemu/asav983.qcow2 local-lvm
```

| Parameter | Value | Notes |
|-----------|-------|-------|
| `300` | VM ID | Must match the VM created in step 5.1 |
| `asav983.qcow2` | Image filename | Use the full path if not in the current directory |
| `local-lvm` | Target storage | Adjust if your storage is named differently |

Once complete, a new **Unused Disk 0** will appear in the VM's Hardware list.

---

### 5.6 Attach the Imported Disk

1. In the VM **Hardware** tab, select **Unused Disk 0**
2. Click **Edit**
3. Change **Bus/Device** to **VirtIO Block**
4. Click **Add**

![Proxmox VM Hardware — editing Unused Disk 0 to set Bus/Device to VirtIO Block](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-10.png)

The disk will now appear as `virtio0` in the hardware list.

---

### 5.7 Set the Boot Order

1. Navigate to the VM **Options** tab
2. Select **Boot Order** and click **Edit**

![Proxmox VM Options — Boot Order edit dialog showing virtio0 device](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-11.png)

3. Drag **virtio0** to the top of the boot order list
4. Tick the **Enabled** checkbox next to virtio0
5. Click **OK**

---

### 5.8 Start the VM and Verify Boot

1. Start the VM from the Proxmox UI
2. Open the **noVNC Console**

The ASAv bootloader will appear:

![Proxmox noVNC console showing Cisco ASAv bootloader screen](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-12.png)

The ASAv will complete its first boot sequence:

![Proxmox noVNC console showing Cisco ASAv fully booted](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-13.png)

> ⚠ The ASAv will **reboot once automatically** during first boot. This is normal behaviour. Wait for it to return to the boot prompt before proceeding.

---

### 5.9 Connect via Serial Console

Once the ASAv has completed its reboot, open a console session using **xterm.js** (available from the Proxmox console dropdown — select **xterm.js** rather than noVNC):

![Proxmox xterm.js serial console showing ASA CLI prompt](https://www.thenetworkwizard.co.uk/wp-content/uploads/2022/07/image-14.png)

The ASA CLI prompt (`ciscoasa>`) confirms the device is operational.

---

## 6. Verification

### 6.1 Confirm Interfaces

From the ASA CLI, run:

```
ciscoasa> show interface ip brief
```

Expected output:

```
GigabitEthernet0/0         unassigned      YES unset  administratively down up
GigabitEthernet0/1         unassigned      YES unset  administratively down up
GigabitEthernet0/2         unassigned      YES unset  administratively down up
Management0/0              unassigned      YES unset  administratively down up
```

All four interfaces should be present and show **up** on the line protocol (even though they are administratively down — this is correct for a freshly deployed ASAv).

### 6.2 Interface to Network Adapter Mapping

The Proxmox network adapters map to ASA interfaces as follows:

| Proxmox adapter | ASA interface |
|-----------------|---------------|
| `net0` | `Management0/0` |
| `net1` | `GigabitEthernet0/0` |
| `net2` | `GigabitEthernet0/1` |
| `net3` | `GigabitEthernet0/2` |

> ℹ Connect Proxmox bridge interfaces (`net0`–`net3`) to the appropriate VLANs or internal bridges in the Proxmox network configuration to wire the ASAv into your lab topology.

### 6.3 Confirm ASA Version

```
ciscoasa> show version
```

Verify the software version matches the QCOW2 image used during import (e.g. 9.8.3).

---

## 7. Rollback

If the deployment needs to be undone:

1. Power off the VM from the Proxmox UI
2. Select the VM and click **More → Remove**
3. Tick **Destroy unreferenced disks** to also remove the imported QCOW2 disk from storage
4. Confirm removal

The QCOW2 source file at `/var/lib/vz/template/qemu/` is not removed automatically — delete it manually if no longer needed:

```bash
rm /var/lib/vz/template/qemu/asav983.qcow2
```

---

## 8. Troubleshooting

### 8.1 VM Boots to GRUB or Blank Screen

- Verify the boot order has `virtio0` enabled and at the top (section 5.7)
- Verify the disk was imported and attached as **VirtIO Block** (not IDE or SATA)
- Check the disk import completed without errors — re-run `qm importdisk` if uncertain

### 8.2 `qm importdisk` Fails

- Verify the QCOW2 file path is correct and the file is not corrupted: `md5sum asav983.qcow2` and compare against Cisco's published checksum
- Verify the target storage (`local-lvm`) has sufficient free space: `pvesm status`
- Verify the VM ID exists: `qm list`

### 8.3 No Serial Console Output in xterm.js

- Confirm a Serial Port (port 0) was added to the VM hardware (section 5.2)
- Try the noVNC console as a fallback — the first boot messages appear there
- Restart the VM and wait for the second boot cycle to complete before connecting

### 8.4 Interfaces Missing from `show interface ip brief`

- Confirm 4 network adapters (net0–net3) are attached to the VM (section 5.2)
- A freshly deployed ASAv expects exactly 4 interfaces; if fewer are present some will not appear
- Power off, add any missing network devices, then power on again

### 8.5 ASAv Reboots in a Loop

- This can occur if the QCOW2 image is corrupt or was incompletely transferred
- Verify file integrity with `md5sum` against Cisco's published hash
- Re-download the image if the hash does not match

---

## 9. Deployment Checklist

| # | Task | Done |
|---|------|------|
| 1 | ASAv QCOW2 image downloaded from Cisco and integrity verified | ☐ |
| 2 | Proxmox node accessible via web UI and SSH | ☐ |
| 3 | VM created with correct OS (Other), disk bus (VirtIO), memory (2048MB) | ☐ |
| 4 | 3× additional network devices added (net1–net3) | ☐ |
| 5 | 1× serial port added | ☐ |
| 6 | Placeholder disk detached and removed | ☐ |
| 7 | QCOW2 image uploaded to `/var/lib/vz/template/qemu/` | ☐ |
| 8 | `qm importdisk` completed without errors | ☐ |
| 9 | Imported disk attached as VirtIO Block (`virtio0`) | ☐ |
| 10 | Boot order updated — `virtio0` enabled and first | ☐ |
| 11 | VM started and bootloader observed in noVNC | ☐ |
| 12 | First-boot reboot completed | ☐ |
| 13 | Serial console connected via xterm.js | ☐ |
| 14 | `show interface ip brief` shows all 4 interfaces | ☐ |
| 15 | Interface-to-adapter mapping documented for this VM | ☐ |

---

## Naming Convention Reference

| Prefix | Role | Example |
|--------|------|---------|
| `EXAFWL` | Firewall | `EXAFWLFAL001` |
| `EXARTR` | Router | `EXARTRFAL001` |
| `EXASWI` | Switch | `EXASWIFAL001` |
| `EXADCS` / `EXADCR` | Domain Controller (site/regional) | `EXADCSFAL001` |
| `EXAPVE` | Proxmox VE node | `EXAPVEFAL001` |
| `EXASRV` | Server | `EXASVRCLD001` |
| `EXARAC` | Remote Access Console (DRAC/iLO/RAC emulator) | `EXARACFAL001` |
| `EXANAS` | NAS | `EXANASFAL001` |
| `EXASBC` | VOIP SBC — trunks to `EXACLDPBX001` | `EXASBCFAL001` |
| `EXAPBX` | PBX | `EXACLDPBX001` |
| `EXAPRV` | Provisioning / bootstrap server | `EXAPRVFAL001` |
| `EXAWAP` | WiFi Access Point | `EXAWAPFAL001` |
| `EXAWKS` | Workstation | `EXAWKSFAL001` |
| `EXALAP` | Laptop | `EXALAPFAL001` |
| `EXAMBP` | MacBook Pro | `EXAMBPFAL001` |
| `EXAMAC` | iMac | `EXAMACFAL001` |
| `EXASUR` | Surface | `EXASURFAL001` |
| `EXATAB` | Tablet | `EXATABFAL001` |
| `EXAPHN` | Phone | `EXAPHNFAL001` |
| `EXACAM` | Camera | `EXACAMFAL001` |
| `EXAVND` / `EXADON` | Vending machine | `EXAVNDFAL001` |
| `EXAMUS` | Jukebox / instrument | `EXAMUSFAL001` |
| `EXAPAY` | Payphone | `EXAPAYFAL001` |
| `EXANIX` | Unix / legacy system | `EXANIXPER001` |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
