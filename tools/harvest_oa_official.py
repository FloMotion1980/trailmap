# -*- coding: utf-8 -*-
"""Holt die OFFIZIELLEN Laengen- und Hoehenmeterangaben eines Betreibers aus dessen eigenem
Outdooractive-Projekt -- der Quelle, aus der seine Website die Zahlen selbst bezieht.

Warum das hier steht (2026-08-25): in `bikecircus` war der gespeicherte Anstieg bei fast jeder
Abfahrt zwei- bis dreistellig, obwohl es reine Abfahrten sind -- Monti-Trail 81 m, X-Line 98 m.
Der Betreiber selbst sagt 3 m bzw. 0 m. Die alten Zahlen stammen aus einer Aufzeichnung
(GPS-Rauschen summiert sich ueber tausende Punkte), und genau dafuer gilt die Regel in CLAUDE.md:
die Angabe des Betreibers gewinnt, Trailforks ist nur der Rueckfall.

Wie man an Projekt und Schluessel kommt: die Detailseite EINES Trails auf der Betreiberseite laedt
`//www.outdooractive.com/alpportal/oa_head.js?proj=<PROJEKT>&key=<SCHLUESSEL>&lang=de`. Beides steht
offen im Quelltext, es braucht keine Anmeldung. Die Tour-IDs stehen in `sitemap.tours.xml`, am Ende
jeder URL nach dem Unterstrich.

Drei Regeln, die das Zuordnen erst zuverlaessig machen -- jede aus einem echten Fehlgriff gelernt:

1. **Die Katalognummer entscheidet, nicht der Name.** Die Betreiber-Slugs heissen `sh-02-monti-line-...`
   und `le-16-...`; der Trailforks-Name derselben Trails traegt dieselbe Nummer ("Monti-Trail SH02").
   Ueber die Nummer ist die Zuordnung eindeutig -- ueber den Namen hat "Pro-Line" zwoelf Treffer
   (jede "Promenade" im Tal) und "Z-Line" einunddreissig.
2. **`-runde` und `-tour` sind keine Trails.** Zu vielen Trails gibt es eine gleichnamige Rundtour
   (`sh-40-hochalm-trail-runde` neben `sh-43-hochalm-trail`), und deren Zahlen sind die der ganzen
   Runde inklusive Auffahrt.
3. **Die Richtung kann entgegengesetzt sein.** Vink Link ist bei uns bewusst abwaerts gedreht (Commit
   dcbfa8f), die Betreibertour laeuft aufwaerts: 90 m Anstieg, 1 m Abstieg. Wer das uebernimmt, dreht
   einen Trail in den Zahlen um. Erkannt wird es am Vorzeichen des Netto-Hoehenunterschieds unseres
   eigenen Profils; up/down werden dann getauscht.

Aufruf:
    python tools/harvest_oa_official.py <portal|all> [--apply]
"""
import io, json, math, os, re, sys, unicodedata, urllib.request

REGION = "Trailmap App/regions/bikecircus.json"
CACHE = "Material/Saalbach/oa_official"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

PORTALS = {
    "saalbach": {
        "sitemap": "https://www.saalbach.com/sitemap.tours.xml",
        "proj": "api-saalbach", "key": "IMBSMP7G-EMWGKTHO-4OSSYIOS",
        "subregion": "saalbach", "codes": ("sh",),
        # Trails ohne Katalognummer im Trailforks-Namen, von Hand zugeordnet:
        "manual": {
            "Höllentrail": "9801710",   # sh-38-hoellen-trail
            "Hochalm-Trail": "7851373",      # sh-43-hochalm-trail, nicht die -runde
        },
    },
    "leogang": {
        "sitemap": "https://www.saalfelden-leogang.com/sitemap.tours.xml",
        "proj": "api-saalfelden-leogang", "key": "ISMPI7CE-EMWGMOEW-4OSSFCYV",
        # KEINE Nummernzuordnung hier, und die `le-NN-`-Seiten sind ausgeschlossen: in Leogang ist die
        # LE-Nummer die des TOUREN-Katalogs, nicht die des Trails. `le-10-matzalm-trail-tour` ist eine
        # 16,44-km-Runde mit 820 m auf und 820 m ab -- der Matzalm-Trail selbst ist 3,7 km lang und hat
        # gar keine eigene Betreiberseite. Die Trails haben schlichte Slugs (`steinberg-line`, `hangman-i`).
        "subregion": "leogang", "codes": (), "skip_prefix": "le-",
        "manual": {
            "Vali's Hölle": "57947927",
            "T-LINE by GoPro": "809414716",
            "Hangman I": "22908699",
            "Steinberg Line": "37890143",
        },
    },
}
NOT_A_TRAIL = ("-runde", "-tour", "alternative", "rundtour", "etappe", "umfahrung", "skitouren",
               "winterwanderweg", "rennrad", "e-bike", "gravel")


def get(url, cache_name):
    p = os.path.join(CACHE, cache_name)
    if os.path.exists(p):
        return io.open(p, encoding="utf-8").read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    body = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    os.makedirs(CACHE, exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(body)
    return body


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s)


def stem(name):
    return norm(re.sub(r"\b(trail|line|lines)\b", " ", name.lower()))


def hv(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    x = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(x))


def official(portal, tour_id):
    xml = get("https://www.outdooractive.com/api/project/%s/oois/%s?key=%s&lang=de"
              % (portal["proj"], tour_id, portal["key"]), "oa_%s.xml" % tour_id)
    e = re.search(r'<elevation ascent="(-?[\d.]+)" descent="(-?[\d.]+)"', xml)
    l = re.search(r"<length>([\d.]+)</length>", xml)
    t = re.search(r"<title>(.*?)</title>", xml)
    if not e:
        return None
    return {"title": t.group(1) if t else "",
            "up": round(float(e.group(1))), "down": round(float(e.group(2))),
            "len": round(float(l.group(1)) / 1000.0, 2) if l else None}


def tf_codes():
    """Trail-id -> Katalognummer, aus dem Trailforks-Namen ("Monti-Trail SH02" -> ("sh", 2))."""
    mp = json.load(io.open("Material/Saalbach/tf_mapping_union.json", encoding="utf-8"))["mapping"]
    tab = json.load(io.open("Material/Saalbach/trailforks_table.json", encoding="utf-8"))
    out = {}
    for tid, slug in mp.items():
        nm = (tab.get(slug) or {}).get("name") or ""
        m = re.search(r"\b([A-Z]{1,2})\s?-?\s?(\d{1,3})\b", nm)
        if m:
            out[tid] = (m.group(1).lower(), int(m.group(2)))
    return out


def run(which, d, apply_it):
    portal = PORTALS[which]
    sm = get(portal["sitemap"], "sitemap.%s.tours.xml" % which)
    tours = {}
    for url in re.findall(r"<loc>(.*?)</loc>", sm):
        m = re.match(r"https://[^/]+/de/tour/(.+)_(\d+)$", url)
        if m:
            tours[m.group(2)] = m.group(1)
    codes = tf_codes()
    prof = d["elevationProfiles"]
    rows, changed = [], 0
    for t in d["lineTrails"]:
        if t.get("region") != portal["subregion"] or t.get("loop"):
            continue
        tid, note = None, ""
        if t["name"] in portal["manual"]:
            tid, note = portal["manual"][t["name"]], "von Hand"
        elif t["id"] in codes:
            pre, nr = codes[t["id"]]
            pat = re.compile(r"^%s-0*%d-" % (pre, nr))
            cand = [k for k, s in tours.items() if pat.match(s)]
            if len(cand) == 1:
                tid, note = cand[0], "Nr. %s%d" % (pre.upper(), nr)
        if tid is None:
            st = stem(t["name"])
            skip = portal.get("skip_prefix")
            cand = [k for k, s in tours.items()
                    if st and st in norm(s) and not any(x in s for x in NOT_A_TRAIL)
                    and not (skip and s.startswith(skip))]
            if portal["codes"]:
                pref = [k for k in cand if re.match(r"^(%s)-\d" % "|".join(portal["codes"]), tours[k])]
                cand = pref or cand
            # Bei mehreren: die Seite, deren Slug GENAU der Name ist, gewinnt -- "hangman-i" gegen
            # "hangman-i-umfahrung" und "hangman-ii", die denselben Namensstamm enthalten.
            if len(cand) > 1:
                exact = [k for k in cand if norm(tours[k]) == norm(t["name"])]
                cand = exact or cand
            if len(cand) == 1:
                tid, note = cand[0], "Name"
            else:
                rows.append((t, None, "offen (%d Kandidaten)" % len(cand)))
                continue
        off = official(portal, tid)
        if not off:
            rows.append((t, None, "keine Hoehendaten"))
            continue
        g = d["trailGeo"][t["id"]]
        ourlen = sum(hv(g[i - 1], g[i]) for i in range(1, len(g))) / 1000.0
        p = prof.get(t["id"])
        ournet = (p[-1][1] - p[0][1]) if p else 0
        if ournet * (off["up"] - off["down"]) < 0:
            off["up"], off["down"] = off["down"], off["up"]
            note += " (Richtung gedreht)"
        # Eine Runde kommt dort heraus, wo sie angefangen hat: gleicher Auf- wie Abstieg ist die
        # Signatur einer Tour, nicht die einer Abfahrt. Das faengt die `le-NN-...-tour`-Seiten auch
        # dann noch ab, wenn ihr Slug das Wort "Tour" nicht traegt.
        if off["up"] == off["down"] and off["up"] > 20:
            rows.append((t, off, note + " RUNDE (auf == ab) -- nicht uebernommen"))
            continue
        if off["len"] and abs(off["len"] - ourlen) / off["len"] > 0.25:
            rows.append((t, off, note + " LAENGE %.2f vs %.2f -- nicht uebernommen" % (off["len"], ourlen)))
            continue
        # Und eine Angabe, die den Hoehenunterschied der Linie selbst nicht hergibt, ist keine Angabe:
        # Gateways Betreiberseite nennt 2 m Abstieg fuer einen Trail, dessen Anfang 51 m ueber seinem
        # Ende liegt. Das Vorzeichen war schon richtig, die Groesse ist es nicht.
        if abs(ournet) > 25 and (off["up"] + off["down"]) < abs(ournet) * 0.5:
            rows.append((t, off, note + " ZU KLEIN gegen %d m Netto -- nicht uebernommen" % abs(ournet)))
            continue
        rows.append((t, off, note))
        if apply_it and (t["up"], t["down"], t["len"]) != (off["up"], off["down"], off["len"]):
            t["len"], t["up"], t["down"] = off["len"], off["up"], off["down"]
            changed += 1
    print("\n=== %s ===" % which)
    print("%-24s %6s %5s %5s | %6s %5s %5s | %s"
          % ("Trail", "len", "up", "down", "off", "up", "down", "Quelle"))
    for t, off, note in rows:
        if not off:
            print("%-24s %6s %5s %5s | %-20s %s"
                  % (t["name"][:24], t["len"], t["up"], t["down"], "--", note))
        else:
            same = (t["up"] == off["up"] and t["down"] == off["down"] and t["len"] == off["len"])
            print("%-24s %6s %5s %5s | %6s %5s %5s | %s%s"
                  % (t["name"][:24], t["len"], t["up"], t["down"], off["len"], off["up"], off["down"],
                     note[:44], "" if same else "  <-- weicht ab"))
    return changed


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    apply_it = "--apply" in sys.argv
    d = json.load(io.open(REGION, encoding="utf-8"))
    total = 0
    for w in (list(PORTALS) if which == "all" else [which]):
        total += run(w, d, apply_it)
    if apply_it and total:
        sys.path.insert(0, "tools")
        from trailmap_pipeline import write_region
        write_region(REGION, d["lineTrails"], d["trailGeo"], d["elevationProfiles"],
                     places=d.get("places"), lifts=d.get("lifts"),
                     trail_segments=d.get("trailSegments"), ratings=d.get("ratings"))
        print("\n%d Trails geschrieben -- jetzt tools/update_region_versions.py laufen lassen" % total)


main()
