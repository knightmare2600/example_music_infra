#!/usr/bin/env python3
"""Add/move a site under a hub's spokes: list in group_vars/firewalls/main.yml.

Usage: update_hub_topology.py <path> <site_code> <new_hub_code>

Called by 09b_register_spoke_on_hub.yml (delegate_to: localhost) whenever a
spoke is auto-registered on its hub, so wg_hub_topology -- the list other
spokes under the same hub use to build their own AllowedIPs
(00_preflight_4_post_ask.yml) -- never silently drifts out of sync with what's
actually configured live.

Edits only the four known "  <HUB>:\\n    spokes: [...]" lines via regex --
never a full YAML parse/re-dump -- so every comment and the rest of the file's
formatting survives untouched. Removes the site from any OTHER hub's list
first (handles a site moving hub, e.g. BRT: ODE -> CLD, 2026-07-17), then adds
it to the target hub's list if not already present, keeping each list sorted
to match the file's existing alphabetical convention.

Prints CHANGED or OK on the last line so the calling Ansible task can set
changed_when from stdout, without writing the file at all when nothing moved.
"""
import re
import sys


def main() -> int:
    path, site, new_hub = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(path, encoding="utf-8") as f:
        text = f.read()

    pattern = re.compile(r"^(  ([A-Z]{3}):\n    spokes: )\[([^\]]*)\]", re.MULTILINE)

    hubs = {}
    for m in pattern.finditer(text):
        hub_code = m.group(2)
        spokes = [s.strip() for s in m.group(3).split(",") if s.strip()]
        hubs[hub_code] = spokes

    if new_hub not in hubs:
        print(f"ERROR: hub '{new_hub}' not found in {path}", file=sys.stderr)
        return 1

    changed = False
    for hub_code, spokes in hubs.items():
        if hub_code != new_hub and site in spokes:
            spokes.remove(site)
            changed = True
    if site not in hubs[new_hub]:
        hubs[new_hub].append(site)
        hubs[new_hub].sort()
        changed = True

    def replace(m: "re.Match[str]") -> str:
        hub_code = m.group(2)
        return f"{m.group(1)}[{', '.join(hubs[hub_code])}]"

    new_text = pattern.sub(replace, text)

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print("CHANGED")
    else:
        print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
