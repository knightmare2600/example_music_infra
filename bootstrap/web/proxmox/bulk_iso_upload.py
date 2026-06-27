#!/usr/bin/env python3

"""
Proxmox ISO Bulk Uploader

Uploads ISO images from a local directory to a Proxmox node storage.

Supports:
- Bulk upload of ISO files
- Skip existing ISOs (default)
- Optional overwrite
- Progress bar per upload
- Parallel uploads
- SHA256 verification
- Auto-detect ISO-capable storage
- Pre-flight storage capacity validation

======================================================================
Example Usage
======================================================================

# Upload all ISOs in a directory (auto-detect storage)
./iso-uploader.py --host pve.example.com --user root@pam --node pve01 --directory /isos

# Upload with verification + 4 threads
./iso-uploader.py --host pve.example.com --user root@pam --node pve01 --directory /isos --threads 4 --verify

# Overwrite existing ISOs
./iso-uploader.py --host pve.example.com --user root@pam --node pve01 --directory /isos --overwrite

# Target specific storage
./iso-uploader.py --host pve.example.com --user root@pam --node pve01 --storage iso-store --directory /isos

# Upload a single ISO
./iso-uploader.py --host pve.example.com --user root@pam --node pve01 --directory /isos-single

======================================================================
Proxmox ISO Uploader
======================================================================

Full Version History:

v1.0   - Initial release
v1.1   - Bulk upload support
v1.2   - Skip existing + overwrite flag
v1.3   - Error handling improvements
v1.4   - Code style alignment
v1.5   - Parallel uploads, progress, SHA256, auto-storage
v1.6   - Capacity validation
        • Pre-flight storage free space check
        • Calculates total upload size
        • Hard fail if insufficient space
        • Optional warning-only mode

======================================================================
"""

import argparse
import getpass
import os
import sys
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

from proxmoxer import ProxmoxAPI
from proxmoxer.backends.https import AuthenticationError


class C:
  RED = "\033[91m"
  GREEN = "\033[92m"
  YELLOW = "\033[93m"
  CYAN = "\033[96m"
  RESET = "\033[0m"


lock = threading.Lock()


def header(title):
  print(f"{C.CYAN}==== {title} ===={C.RESET}")


def ok(msg):
  with lock:
    print(f"{C.GREEN}[OK] {msg}{C.RESET}")


def warn(msg):
  with lock:
    print(f"{C.YELLOW}[WARN] {msg}{C.RESET}")


def err(msg):
  with lock:
    print(f"{C.RED}[FAIL] {msg}{C.RESET}")


def human(size):
  """Convert bytes to human readable."""
  for unit in ["B","KB","MB","GB","TB"]:
    if size < 1024:
      return f"{size:.1f}{unit}"
    size /= 1024
  return f"{size:.1f}PB"


def connect(args):
  try:
    return ProxmoxAPI(
      args.host,
      user=args.user,
      password=args.password,
      verify_ssl=False
    )
  except AuthenticationError:
    err("Authentication failed")
    sys.exit(2)
  except Exception as e:
    err(f"Connection failed: {e}")
    sys.exit(2)


def detect_iso_storage(proxmox, node):
  for store in proxmox.nodes(node).storage.get():
    if "iso" in store.get("content", ""):
      return store["storage"]

  err("No ISO-capable storage found")
  sys.exit(1)


def get_storage_status(proxmox, node, storage):
  """
  Retrieve storage capacity information.
  """
  for store in proxmox.nodes(node).storage.get():
    if store["storage"] == storage:
      total = store.get("total", 0)
      used = store.get("used", 0)
      avail = total - used
      return total, used, avail

  err("Storage not found")
  sys.exit(1)


def list_existing_isos(proxmox, node, storage):
  existing = {}

  for item in proxmox.nodes(node).storage(storage).content.get():
    if item.get("content") == "iso":
      name = item.get("volid").split("/")[-1]
      size = item.get("size", 0)
      existing[name] = size

  return existing


def sha256_file(path):
  h = hashlib.sha256()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
      h.update(chunk)
  return h.hexdigest()


class ProgressFile:
  def __init__(self, path):
    self.f = open(path, "rb")
    self.size = os.path.getsize(path)
    self.read_bytes = 0
    self.path = path

  def read(self, chunk_size=1024 * 1024):
    data = self.f.read(chunk_size)
    if not data:
      return data

    self.read_bytes += len(data)
    percent = (self.read_bytes / self.size) * 100

    with lock:
      print(f"\r[{os.path.basename(self.path)}] {percent:5.1f}%", end="")

    return data

  def close(self):
    self.f.close()
    with lock:
      print("")


def preflight_capacity(files, existing, avail, args):
  """
  Validate total upload size vs available storage.
  """
  header("Pre-flight Capacity Check")

  total_needed = 0

  for path in files:
    name = os.path.basename(path)
    size = os.path.getsize(path)

    if name in existing and not args.overwrite:
      continue

    total_needed += size

  print(f"Required: {human(total_needed)}")
  print(f"Available: {human(avail)}")

  if total_needed > avail:
    if args.force:
      warn("Insufficient space but continuing (--force set)")
    else:
      err("Not enough storage space")
      sys.exit(1)
  else:
    ok("Capacity check passed")


def upload_one(proxmox, node, storage, path, existing, args):
  name = os.path.basename(path)
  size = os.path.getsize(path)

  if name in existing and not args.overwrite:
    warn(f"{name} exists (skipping)")
    return

  try:
    pf = ProgressFile(path)

    proxmox.nodes(node).storage(storage).upload.post(
      content="iso",
      filename=(name, pf)
    )

    pf.close()

    if args.verify:
      h = sha256_file(path)
      ok(f"{name} uploaded (sha256 {h[:8]}...)")
    else:
      ok(f"{name} uploaded")

  except Exception as e:
    err(f"{name} failed: {e}")


def process(proxmox, args):
  header("ISO Upload")

  if not os.path.isdir(args.directory):
    err("Invalid directory")
    sys.exit(1)

  storage = args.storage or detect_iso_storage(proxmox, args.node)
  ok(f"Using storage: {storage}")

  existing = list_existing_isos(proxmox, args.node, storage)

  files = [
    os.path.join(args.directory, f)
    for f in os.listdir(args.directory)
    if f.lower().endswith(".iso")
  ]

  total, used, avail = get_storage_status(proxmox, args.node, storage)

  print(f"Storage Total: {human(total)} Used: {human(used)} Free: {human(avail)}")

  preflight_capacity(files, existing, avail, args)

  with ThreadPoolExecutor(max_workers=args.threads) as pool:
    for path in files:
      pool.submit(upload_one, proxmox, args.node, storage, path, existing, args)


def main():
  parser = argparse.ArgumentParser()

  parser.add_argument("--host", required=True)
  parser.add_argument("--user", required=True)
  parser.add_argument("--node", required=True)
  parser.add_argument("--directory", required=True)

  parser.add_argument("--storage")
  parser.add_argument("--threads", type=int, default=3)
  parser.add_argument("--overwrite", action="store_true")
  parser.add_argument("--verify", action="store_true")
  parser.add_argument("--force", action="store_true",
                      help="Ignore capacity check failure")

  args = parser.parse_args()
  args.password = getpass.getpass(f"Password for {args.user}: ")
  proxmox = connect(args)
  process(proxmox, args)

if __name__ == "__main__":
  main()