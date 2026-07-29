"""Local helper for harvesting Outdooractive project data through a real browser.

WHY THIS EXISTS: the Outdooractive project API that Bike Kingdom's own trail map uses answers 404 to any
plain HTTP client -- verified against 7 URL variants and 3 header sets (UA, Origin, Referer,
Accept-Language). It answers fine to a real browser. So the fetching has to happen in a browser, but the
*writing* has to happen here, and 750 KB of geometry has no business travelling through tool results.

This serves a harvester page and accepts its POST:

    python tools/oa_harvest_server.py            # then open http://localhost:8765/harvest.html
    python tools/oa_harvest_server.py --ids 1,2  # restrict to a few ids for a smoke test

Everything is same-origin from the browser's point of view (localhost:8765), which avoids both the
mixed-content block an https page would hit posting to http://localhost, and any CORS question on the POST.
The only cross-origin request is the one to outdooractive.com, which is what their own map does too.

Output: Material/BikeKingdom/oa_tours.json -- {id: {title, length, ascent, descent, difficulty, geometry}}
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Material", "BikeKingdom", "oa_tours.json")
IDS_FILE = os.path.join(ROOT, "Material", "BikeKingdom", "trails_api.tsv")
PROJ = "api-arosalenzerheide"
KEY = "IETVOSAR-EMWGMZIJ-4OSSIQCH"

PAGE = """<!doctype html><meta charset="utf-8"><title>OA Harvest</title>
<body style="font-family:system-ui;padding:20px;max-width:52em">
<h2>Outdooractive-Ernte</h2><pre id="log">bereit</pre>
<script>
const IDS = %IDS%, PROJ = "%PROJ%", KEY = "%KEY%";
const log = document.getElementById("log");
const say = (s) => { log.textContent = s + "\\n" + log.textContent.split("\\n").slice(0,14).join("\\n"); };
(async () => {
  const out = {};
  // Batched, because one request per tour would be 126 round trips -- their own map batches 25 at a time.
  for (let i = 0; i < IDS.length; i += 10) {
    const batch = IDS.slice(i, i + 10);
    const url = `https://www.outdooractive.com/api/oois/${batch.join(",")}`
              + `?project=${PROJ}&key=${KEY}&lang=de&format=json&display=full`;
    try {
      const j = await (await fetch(url)).json();
      for (const t of (j.tour || [])) {
        out[t.id] = {
          title: t.title || "",
          length: t.length || null,
          ascent: t.elevation ? t.elevation.ascent : null,
          descent: t.elevation ? t.elevation.descent : null,
          difficulty: t.rating ? t.rating.difficulty : null,
          geometry: t.geometry || null,
        };
      }
      say(`${Object.keys(out).length}/${IDS.length} geholt`);
    } catch (e) { say("FEHLER bei " + batch[0] + ": " + e.message); }
  }
  const r = await fetch("/save", { method: "POST", body: JSON.stringify(out) });
  say("gespeichert: " + (await r.text()));
  document.title = "FERTIG " + Object.keys(out).length;
})();
</script>
"""


def wanted_ids(argv):
    if "--ids" in argv:
        return argv[argv.index("--ids") + 1].split(",")
    ids = []
    with open(IDS_FILE, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            ids.append(line.split("\t")[0])
    return ids


class Handler(BaseHTTPRequestHandler):
    ids = []

    def do_GET(self):
        if self.path.startswith("/harvest"):
            body = (PAGE.replace("%IDS%", json.dumps(self.ids))
                        .replace("%PROJ%", PROJ).replace("%KEY%", KEY)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(n).decode("utf-8"))
        # MERGE, never overwrite: a later `--ids 45120014` run to add one trail (Wasserfall Lenzerheide,
        # 2026-07-29) would otherwise replace the whole 126-tour harvest with a single entry, and
        # Material/ is the source this region is rebuilt from.
        fresh = len(data)
        if os.path.exists(OUT):
            try:
                with open(OUT, encoding="utf-8") as fh:
                    have = json.load(fh)
                have.update(data)
                data = have
            except ValueError:
                pass
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False)
        msg = ("%d neu -> %d Touren, %d mit Geometrie"
               % (fresh, len(data), sum(1 for v in data.values() if v.get("geometry")))).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)
        print("geschrieben:", OUT, msg.decode("utf-8"))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    Handler.ids = wanted_ids(sys.argv[1:])
    print("%d ids -- http://localhost:8765/harvest.html" % len(Handler.ids))
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
