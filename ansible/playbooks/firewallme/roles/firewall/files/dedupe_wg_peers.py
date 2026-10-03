#!/usr/bin/env python3
# =============================================================================
# roles/firewall/files/dedupe_wg_peers.py
# Example Music Limited — remove unmanaged, duplicate WireGuard [Peer] blocks
# =============================================================================
# Pushed to and run ON the target hub by playbooks/dedupe-wg-peers.yml (ansible.builtin.script),
# operating on that host's own /etc/wireguard/wg0.conf.
#
# Does exactly one thing: finds a [Peer] stanza that is NOT inside a
# "# BEGIN ANSIBLE MANAGED BLOCK <site>" / "# END ANSIBLE MANAGED BLOCK <site>" marker pair,
# whose PublicKey is byte-identical to one that IS inside such a pair, and removes only that
# unmanaged stanza. A managed block, the [Interface] section, and any unmanaged [Peer] whose
# PublicKey does NOT match a managed one (i.e. a real, not-yet-Ansible-registered peer) are
# never touched.
#
# Root cause this cleans up: bootstrap/web/provision/firewallme.sh's interactive hub-bootstrap
# "Add spoke peer?" loop writes a plain, unmarked [Peer] block directly (no PresharedKey, no
# marker). playbooks/add-wg-spoke.yml's later, correct registration of the same site uses
# blockinfile with its own per-site marker -- which can never find or remove that earlier
# unmarked block, since blockinfile only ever manages its own marker. Confirmed safe to remove
# the unmanaged copy: WireGuard treats two [Peer] stanzas sharing one PublicKey as the same
# peer, and the kernel applies whichever one is encountered LAST when the file is loaded -- the
# managed (correct, PresharedKey-bearing) block already wins live; the unmanaged one is dead text.
#
# Idempotent: zero matches -> zero changes, DEDUPE_COUNT=0, exit 0.
# --check: reports exactly what would be removed, writes nothing.
# Apply mode: backs up the original file to <path>.bak-dedupe before writing.
# =============================================================================
# Changelog:
#   2026-10-02  Initial version. Robert, after a live-confirmed duplicate on
#               EXAFWLCLD001 (FAL/ODE/LIV) -- built as a real, idempotent, reusable
#               mechanism rather than a one-off manual edit.
# =============================================================================

import argparse
import re
import sys
from pathlib import Path

MANAGED_RE = re.compile(
    r"# BEGIN ANSIBLE MANAGED BLOCK (\S+)\n(.*?)\n# END ANSIBLE MANAGED BLOCK \1\n",
    re.DOTALL,
)
PUBKEY_RE = re.compile(r"^PublicKey\s*=\s*(\S+)", re.MULTILINE)
# Optional comment line (## SITE or # SITE), then [Peer], then any lines that are
# neither another section header ([...]) nor blank -- i.e. the whole stanza's body.
PEER_STANZA_RE = re.compile(
    r"(?:^(#+[ \t]*\S.*)\n)?^\[Peer\]\n(?:^(?!\[|[ \t]*$).*\n?)*",
    re.MULTILINE,
)


def parse_managed_pubkeys(content):
    pubkeys = set()
    for m in MANAGED_RE.finditer(content):
        pk = PUBKEY_RE.search(m.group(2))
        if pk:
            pubkeys.add(pk.group(1))
    return pubkeys


def find_unmanaged_peer_stanzas(content):
    managed_spans = [(m.start(), m.end()) for m in MANAGED_RE.finditer(content)]

    def in_managed(pos):
        return any(s <= pos < e for s, e in managed_spans)

    stanzas = []
    for m in PEER_STANZA_RE.finditer(content):
        if in_managed(m.start()):
            continue
        pk = PUBKEY_RE.search(m.group(0))
        if not pk:
            continue
        label = (m.group(1) or "").strip()
        stanzas.append((m.start(), m.end(), pk.group(1), label, m.group(0)))
    return stanzas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--check", action="store_true", help="Report only, write nothing")
    args = ap.parse_args()

    content = Path(args.path).read_text()
    managed_pubkeys = parse_managed_pubkeys(content)
    to_remove = [
        s for s in find_unmanaged_peer_stanzas(content) if s[2] in managed_pubkeys
    ]

    if not to_remove:
        print("DEDUPE_COUNT=0")
        return 0

    for _start, _end, pubkey, label, body in to_remove:
        print(f"-- would remove: {label or '(no label)'} ({pubkey}) --")
        print(body.rstrip("\n"))
        print("-- end --")

    if args.check:
        print(f"DEDUPE_COUNT={len(to_remove)} (check mode, nothing written)")
        return 0

    new_content = content
    for start, end, _pubkey, _label, _body in sorted(
        to_remove, key=lambda s: s[0], reverse=True
    ):
        new_content = new_content[:start] + new_content[end:]
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)

    Path(args.path + ".bak-dedupe").write_text(content)
    Path(args.path).write_text(new_content)
    print(f"DEDUPE_COUNT={len(to_remove)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
