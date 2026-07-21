#!/usr/bin/env python3
"""
serve.py — Drop-in http.server replacement that also answers POST
Example Music Limited — Internal Infrastructure

Why this exists
----------------
Fredericia Havn's provisioning server (172.16.124.1 — physically a MacBook, see
docs/bootstrap/bootstrapping.md §4.1a) runs `python3 -m http.server 8000` to mirror
Edinburgh's `web/` tree. That's fine for iPXE/preseed/first-boot.sh fetches — they're
all plain GET. Proxmox VE's own automated installer is the one client on this network
that isn't: when a node boots with `proxmox-fetch-from-url` pointing at an answer.toml
(VRK-answer.toml / FRD-answer.toml), the installer's own HTTP client fetches it via
POST, not GET, sending the node's system properties as the request body so the
answer file's `[[match]]` filters can key off them. http.server's stock
SimpleHTTPRequestHandler only implements do_GET/do_HEAD, so it answers that POST with
"501 Unsupported method" — which is exactly the "auto-install mode 'fails' to fetch
the answer file (expected, this is the mechanism, not an error)" behaviour
docs/bootstrap/bootstrapping.md §6.3 already documents working around by hand
(`wget`-ing the file manually once the installer drops to a shell). This script closes
that gap: same server, same invocation, one line added so the automatic fetch works
too and the manual wget fallback stops being necessary.

Genuinely a drop-in replacement, not a rewrite — SimpleHTTPRequestHandler is exactly
what `python3 -m http.server` already runs; this is the same stdlib class with one
method aliased. Same directory served (cwd, same as http.server), same port argument.

Usage — identical to how you already run http.server:
    cd web/                 # or wherever you currently cd before serving
    python3 serve.py 8000    # or omit the port; defaults to 8000, same as http.server

A note on ports: 8000 never needed root on macOS/Linux (only <1024 does) — nothing
about privilege changes by switching from http.server to this.

The one thing worth actually testing rather than trusting on say-so: aliasing
do_POST straight to do_GET does NOT drain the POST request body off the socket
before responding. On a kept-alive HTTP/1.1 connection that would corrupt the next
request on the same socket — the leftover body bytes would be read as if they were
the start of the following request. This doesn't bite here because
SimpleHTTPRequestHandler defaults to protocol_version = "HTTP/1.0", which closes the
connection after every single request/response regardless of any Connection header
the client sends — there is no "next request on the same socket" for the leftover
body to corrupt. Confirmed by inspecting http.server's own source (BaseHTTPRequestHandler
default protocol_version), not just assumed. Verify directly against a real Proxmox
node's fetch before relying on this for a live install, same as any other bootstrap
tooling in this repo:
    python3 serve.py 8000 &
    curl -i http://172.16.124.1:8000/proxmox/FRD-answer.toml
    curl -i -X POST http://172.16.124.1:8000/proxmox/FRD-answer.toml
Both should come back 200 with the TOML body.

Known limitation: unlike `python3 -m http.server`, this does not implement the
`--bind`/`--directory`/port-as-flag CLI surface documented in
docs/bootstrap/bootstrapping.md (e.g. `python3 -m http.server 80 --bind 192.168.139.50
-d web/`) — only a single optional positional port argument, matching Fredericia
Havn's actual real-world invocation (`python3 -m http.server 8000`, no flags). Add
those if this ever needs to replace Edinburgh's `static-web-server.exe` too; not
needed for the case this was written for.

Changelog:
    2026-07-18  Initial version. Written in response to Proxmox's automated installer
                POSTing its answer-file fetch instead of GETting it — confirmed
                against a real symptom (installer treats the fetch as failed, same
                "expected, not an error" behaviour docs/bootstrap/bootstrapping.md
                §6.3 already documents working around via manual wget). do_POST
                aliased straight to do_GET rather than writing a real POST handler --
                SimpleHTTPRequestHandler's GET handler only ever reads the URL path
                and serves a file from disk, so it works unmodified as a POST handler
                too; the installer's request body is simply never read, which is
                fine since nothing on this server needs it. Not yet confirmed live
                against a real Proxmox node's automated fetch in this environment --
                verify with the curl pair above before trusting this for an actual
                unattended install.
"""

import http.server
import sys


class Handler(http.server.SimpleHTTPRequestHandler):
  # Proxmox's automated installer fetches answer files via POST (see module
  # docstring). Aliasing straight to do_GET is safe here specifically because
  # SimpleHTTPRequestHandler serves purely from the URL path -- it never reads
  # the request body -- and defaults to HTTP/1.0 (connection closes after every
  # request), so an undrained POST body can never bleed into a reused connection.
  do_POST = http.server.SimpleHTTPRequestHandler.do_GET


if __name__ == "__main__":
  port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
  httpd = http.server.HTTPServer(("0.0.0.0", port), Handler)
  # Matches python3 -m http.server's own startup line, for genuine drop-in parity.
  print(f"Serving HTTP on 0.0.0.0 port {port} (http://0.0.0.0:{port}/) ...")
  httpd.serve_forever()
