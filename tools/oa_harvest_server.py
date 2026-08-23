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
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: Bike Kingdom's, and still the default so the original invocation keeps working unchanged. Every one of
#: these four is overridable from the command line, because the second project to need this (Garda
#: Trentino, 2026-08-21) differs in all four and copying the file would have been the third copy of the
#: same browser trick:
#:
#:     python tools/oa_harvest_server.py --proj api-gardatrentino --key ATLFE9GX-EMWGKQIH-4OSSEBMT
#:         --out "Material/Gardasee/oa_tours.json" --port 8766 --ids 9952405,9952384,...
#:
#: The project/key pair is not a secret: it sits in the tourism site's own page source, which is where
#: each of these came from, and it only scopes the API to that project's own content.
OUT = os.path.join(ROOT, "Material", "BikeKingdom", "oa_tours.json")
IDS_FILE = os.path.join(ROOT, "Material", "BikeKingdom", "trails_api.tsv")
PROJ = "api-arosalenzerheide"
KEY = "IETVOSAR-EMWGMZIJ-4OSSIQCH"


def _cli(argv, flag, default):
    return argv[argv.index(flag) + 1] if flag in argv else default


PAGE = """<!doctype html><meta charset="utf-8"><title>OA Harvest</title>
<body style="font-family:system-ui;padding:20px;max-width:52em">
<h2>Outdooractive-Ernte</h2><pre id="log">bereit</pre>
<script>
const IDS = %IDS%, PROJ = "%PROJ%", KEY = "%KEY%", PROBE = %PROBE%;
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
          // --probe writes the whole `rating` object plus any top-level key that looks like a rating,
          // a vote count or a view count, WITHOUT the geometry. That is how "does Outdooractive expose a
          // community rating like Trailforks does" gets answered from the API itself rather than guessed:
          // its `rating.difficulty`/`stamina`/`experience` are EDITORIAL scales, and whether there is a
          // separate crowd rating next to them is exactly what a reduced extraction hides.
          _probe: PROBE ? Object.assign({ rating: t.rating || null },
              Object.fromEntries(Object.entries(t).filter(([k, v]) =>
                  /rat|vote|star|review|popular|view|count|fav|like/i.test(k) &&
                  (typeof v !== "object" || v === null)))) : undefined,
        };
        if (PROBE) { delete out[t.id].geometry; }
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
        return [x for x in argv[argv.index("--ids") + 1].split(",") if x]
    if "--ids-file" in argv:
        path = argv[argv.index("--ids-file") + 1]
        return [ln.split("	")[0].strip() for ln in io.open(path, encoding="utf-8")
                if ln.strip() and not ln.startswith("#")]
    ids = []
    with open(IDS_FILE, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            ids.append(line.split("\t")[0])
    return ids


class Handler(BaseHTTPRequestHandler):
    ids = []
    proj = PROJ
    key = KEY
    out = OUT
    probe = False

    def do_GET(self):
        if self.path.startswith("/harvest"):
            body = (PAGE.replace("%IDS%", json.dumps(self.ids))
                        .replace("%PROJ%", self.proj).replace("%KEY%", self.key)
                        .replace("%PROBE%", "true" if self.probe else "false")).encode("utf-8")
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
        out_path = self.out
        if os.path.exists(out_path):
            try:
                with open(out_path, encoding="utf-8") as fh:
                    have = json.load(fh)
                have.update(data)
                data = have
            except ValueError:
                pass
        # `out_path`, NOT the module-global OUT. Getting this one line wrong while the merge-read above
        # already used out_path is how a Garda Trentino harvest ended up merged into Bike Kingdom's own
        # oa_tours.json (2026-08-21) -- silently, because merging never fails and the message still reports a
        # plausible count. It also destroys the file it lands in, which is a source a region is rebuilt from.
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False)
        msg = ("%d neu -> %d Touren, %d mit Geometrie"
               % (fresh, len(data), sum(1 for v in data.values() if v.get("geometry")))).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)
        print("geschrieben:", out_path, msg.decode("utf-8"))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    argv = sys.argv[1:]
    Handler.proj = _cli(argv, "--proj", PROJ)
    Handler.key = _cli(argv, "--key", KEY)
    out = _cli(argv, "--out", OUT)
    Handler.out = out if os.path.isabs(out) else os.path.join(ROOT, out)
    Handler.probe = "--probe" in argv
    Handler.ids = wanted_ids(argv)
    print("%d ids, project %s -> %s" % (len(Handler.ids), Handler.proj, Handler.out))
    # --port, because a stale server from an earlier run keeps listening on the default and silently
    # ANSWERS the next harvest -- with its own --out, which is how a Garda harvest reached Bike Kingdom's
    # file even after --out was fixed. A fresh port is the cheap way to be sure which process replied.
    port = int(_cli(argv, "--port", "8765"))
    print("open http://localhost:%d/harvest.html" % port)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
