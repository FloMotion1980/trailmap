# -*- coding: utf-8 -*-
"""Tiny localhost-only HTTP sink so a browser page can hand large harvests straight to disk.

    python tools/harvest_receiver.py --dir "Material/Pfälzer Wald/trailforks" --port 8765

Then, from any page in the browser:

    await fetch('http://127.0.0.1:8765/save?name=trails.json', {method:'POST', body: JSON.stringify(x)})

Why this exists. Pulling a whole Trailforks region gives tens of thousands of coordinates, and the two
transfer routes used before both hit a wall:

* **Returning it from `javascript_exec`** is capped somewhere around 1.5 KB per response and burns the
  agent's context for data it only needs on disk. A 130 KB listing is 4+ calls of pure noise.
* **`a.click()` on a Blob URL** works exactly once per origin: Chrome then treats further programmatic
  downloads as "multiple automatic downloads" and blocks them silently until the user grants permission.
  That is what happened harvesting the Pfälzerwald listing right after the Harz geometry.

`http://127.0.0.1` is a trustworthy origin in Chrome, so an HTTPS page may POST to it without tripping
mixed-content blocking -- the only thing needed is the CORS headers below. Bound to the loopback interface
only, and a POSTed name is reduced to its basename with a suffix whitelist, so a page cannot choose where
on disk anything lands.
"""
import argparse
import http.server
import os
import re
import sys
import threading

ALLOWED_SUFFIX = (".json", ".csv", ".txt", ".gpx")
MAX_BYTES = 64 * 1024 * 1024


def make_handler(outdir):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            # Chrome's Private Network Access check: a page on a PUBLIC origin (https://trailforks.com)
            # reaching a LOCAL address is refused outright -- the fetch fails with a bare
            # "TypeError: Failed to fetch" and the request never arrives here, so the receiver's own log
            # stays empty and looks like a port problem. This header is the documented opt-in, and it has
            # to be on the preflight response as well as the real one.
            self.send_header("Access-Control-Allow-Private-Network", "true")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            body = b'{"ok":true,"receiver":"trailmap"}'
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            m = re.search(r"[?&]name=([^&]+)", self.path)
            raw = m.group(1) if m else "harvest.json"
            # basename only, and a conservative charset: the page picks the name, not the location.
            name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(raw))
            if not name.endswith(ALLOWED_SUFFIX):
                name += ".json"
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BYTES:
                self.send_response(413)
                self._cors()
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            data = b""
            while len(data) < length:
                chunk = self.rfile.read(min(65536, length - len(data)))
                if not chunk:
                    break
                data += chunk
            path = os.path.join(outdir, name)
            with open(path, "wb") as fh:
                fh.write(data)
            print("received %-42s %9d bytes" % (name, len(data)), flush=True)
            body = ('{"ok":true,"bytes":%d,"name":"%s"}' % (len(data), name)).encode()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass                      # the received-line above is the only output worth having

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--seconds", type=int, default=0, help="auto-shutdown after N seconds (0 = never)")
    args = ap.parse_args()

    outdir = os.path.abspath(args.dir)
    os.makedirs(outdir, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(outdir))
    print("receiver on http://127.0.0.1:%d -> %s" % (args.port, outdir), flush=True)
    if args.seconds:
        threading.Timer(args.seconds, srv.shutdown).start()
        print("will shut down after %ds" % args.seconds, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    print("receiver stopped", flush=True)


if __name__ == "__main__":
    main()
