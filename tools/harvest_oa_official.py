# -*- coding: utf-8 -*-
"""Holt die OFFIZIELLEN Laengen- und Hoehenmeterangaben eines Betreibers aus dessen eigenem
Outdooractive-Projekt -- der Quelle, aus der seine Website die Zahlen selbst bezieht.

Warum das hier steht (2026-08-25): in `bikecircus` war der gespeicherte Anstieg bei fast jeder
Abfahrt zweistellig bis dreistellig, obwohl es reine Abfahrten sind -- Monti-Trail 81 m, X-Line
98 m. Der Betreiber selbst sagt 3 m bzw. 0 m. Die alten Zahlen stammen aus einer Aufzeichnung
(GPS-Rauschen summiert sich ueber tausende Punkte), und genau dafuer gilt die Regel in CLAUDE.md:
die Angabe des Betreibers gewinnt, Trailforks ist nur der Rueckfall.

Wie man an Projekt und Schluessel kommt: die Detailseite eines Trails auf der Betreiberseite laedt
`//www.outdooractive.com/alpportal/oa_head.js?proj=<PROJEKT>&key=<SCHLUESSEL>&lang=de`. Beides steht
im Quelltext der Seite, es braucht keine Anmeldung. Die Tour-IDs stehen in `sitemap.tours.xml`, am
Ende jeder URL nach dem Unterstrich.

Aufruf:
    python tools/harvest_oa_official.py <portal> [--apply]

`--apply` schreibt len/up/down in die Regionsdatei (danach tools/update_region_versions.py!),
ohne das Flag wird nur die Tabelle gedruckt.
"""
import io, json, os, re, sys, unicodedata, urllib.request

PORTALS = {
    # portal-key: Betreiberportal, dessen OA-Projekt die offiziellen Zahlen fuehrt
    "saalbach": {
        "sitemap": "https://www.saalbach.com/sitemap.tours.xml",
        "proj": "api-saalbach", "key": "IMBSMP7G-EMWGKTHO-4OSSYIOS",
        "region": "Trailmap App/regions/bikecircus.json", "subregion": "saalbach",
    },
}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
CACHE = "Material/Saalbach/oa_official"

def get(url, cache_name=None):
    if cache_name:
        p = os.path.join(CACHE, cache_name)
        if os.path.exists(p):
            return io.open(p, encoding="utf-8").read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    body = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    if cache_name:
        os.makedirs(CACHE, exist_ok=True)
        io.open(os.path.join(CACHE, cache_name), "w", encoding="utf-8").write(body)
    return body

def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s)

def stem(name):
    """Der unterscheidende Teil eines Trailnamens: ohne -Trail/-Line, ohne Trennzeichen."""
    n = re.sub(r"\b(trail|line|lines)\b", " ", name.lower())
    return norm(n)

def official(portal, tour_id):
    xml = get("https://www.outdooractive.com/api/project/%s/oois/%s?key=%s&lang=de"
              % (portal["proj"], tour_id, portal["key"]), "oa_%s.xml" % tour_id)
    e = re.search(r'<elevation ascent="(-?[\d.]+)" descent="(-?[\d.]+)"', xml)
    l = re.search(r"<length>([\d.]+)</length>", xml)
    t = re.search(r"<title>(.*?)</title>", xml)
    if not e:
        return None
    return {"title": t.group(1) if t else "", "up": round(float(e.group(1))),
            "down": round(float(e.group(2))), "len": round(float(l.group(1)) / 1000.0, 2) if l else None}

def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "saalbach"
    apply_it = "--apply" in sys.argv
    portal = PORTALS[which]
    sm = get(portal["sitemap"], "sitemap.tours.xml")
    tours = {}
    for url in re.findall(r"<loc>(.*?)</loc>", sm):
        m = re.match(r"https://[^/]+/de/tour/(.+)_(\d+)$", url)
        if m:
            tours[m.group(2)] = m.group(1)

    d = json.load(io.open(portal["region"], encoding="utf-8"))
    rows = []
    for t in d["lineTrails"]:
        if t.get("region") != portal["subregion"] or t.get("loop"):
            continue
        st = stem(t["name"])
        hits = [(tid, slug) for tid, slug in tours.items() if st and st in norm(slug)]
        if len(hits) != 1:
            rows.append((t, None, "%d Treffer" % len(hits)))
            continue
        off = official(portal, hits[0][0])
        rows.append((t, off, hits[0][1]))

    print("%-24s %6s %5s %5s | %6s %5s %5s | %s" %
          ("Trail", "len", "up", "down", "off.len", "up", "down", "Quelle"))
    changed = 0
    for t, off, note in rows:
        if not off:
            print("%-24s %6s %5s %5s | %-20s %s" % (t["name"][:24], t["len"], t["up"], t["down"], "--", note))
            continue
        mark = "" if (t["up"] == off["up"] and t["down"] == off["down"]) else "  <-- weicht ab"
        print("%-24s %6s %5s %5s | %6s %5s %5s | %s%s" %
              (t["name"][:24], t["len"], t["up"], t["down"], off["len"], off["up"], off["down"],
               note[:34], mark))
        if apply_it and (t["up"] != off["up"] or t["down"] != off["down"] or t["len"] != off["len"]):
            t["len"], t["up"], t["down"] = off["len"], off["up"], off["down"]
            changed += 1
    if apply_it and changed:
        sys.path.insert(0, "tools")
        from trailmap_pipeline import write_region
        write_region(portal["region"], d["lineTrails"], d["trailGeo"], d["elevationProfiles"],
                     places=d.get("places"), lifts=d.get("lifts"),
                     trail_segments=d.get("trailSegments"), ratings=d.get("ratings"))
        print("\n%d Trails geschrieben -- jetzt tools/update_region_versions.py laufen lassen" % changed)

main()
