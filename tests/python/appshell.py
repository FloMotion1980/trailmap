# -*- coding: utf-8 -*-
"""
@suite   appshell
@area    Service worker, cache versions, app-shell integrity
@always
@files   Trailmap App/index.html, Trailmap App/sw.js, Trailmap App/style.css
@touches CACHE_NAME, PRELOAD_CACHE_NAME, STYLE_URL, ROTATE_URL, APP_SHELL, style.css, leaflet-rotate.js

The three-way version sync is the reason this suite runs on every change. If a new index.html is paired with
an old style.css, a newly added element has NO rules at all -- therefore no position:absolute -- and paints
behind #map, which is absolutely positioned over the whole area. It does not look unstyled, it disappears
completely; that is how the pinned Tourenbuilder sheet went missing on the user's phone while everything else
looked normal. Three things have to move together: the ?v= in index.html's <link>, STYLE_URL in sw.js, and
(because the stylesheet is in APP_SHELL) CACHE_NAME / PRELOAD_CACHE_NAME.

Also checked: nothing in APP_SHELL points at a file that does not exist, since a failed precache request
rejects the whole install and leaves the worker permanently uninstalled -- offline silently stops working
while the online app looks perfect.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "Trailmap App")


def read(name):
    return io.open(os.path.join(APP, name), encoding="utf-8").read()


def run(t):
    html, sw = read("index.html"), read("sw.js")

    t.case("the stylesheet version is the same in all three places")
    link = re.search(r'<link rel="stylesheet" href="style\.css\?v=(\d+)"', html)
    style_url = re.search(r'STYLE_URL\s*=\s*"\./style\.css\?v=(\d+)"', sw)
    cache_name = re.search(r'CACHE_NAME\s*=\s*"trailmap-v(\d+)"', sw)
    preload = re.search(r'PRELOAD_CACHE_NAME\s*=\s*"trailmap-v(\d+)"', html)
    t.ok("index.html links a versioned stylesheet", bool(link), link and link.group(0), "style.css?v=N")
    t.ok("sw.js has STYLE_URL", bool(style_url), style_url and style_url.group(0), 'STYLE_URL = "./style.css?v=N"')
    t.ok("sw.js has CACHE_NAME", bool(cache_name), cache_name and cache_name.group(0), "trailmap-vN")
    t.ok("index.html has PRELOAD_CACHE_NAME", bool(preload), preload and preload.group(0), "trailmap-vN")
    if link and style_url:
        t.eq("index.html and sw.js request the same stylesheet", link.group(1), style_url.group(1))
    if cache_name and preload:
        t.eq("CACHE_NAME == PRELOAD_CACHE_NAME", cache_name.group(1), preload.group(1))
    if link and cache_name:
        # Not required by the browser, but keeping them equal is what makes "which version is this?" answerable
        # from a single number -- and the version indicator in Kartenoptionen reads the cache name.
        t.eq("the cache generation matches the stylesheet version", cache_name.group(1), link.group(1))

    t.case("the rotation plugin's version is the same in both places and it is precached")
    # Same failure mode as the stylesheet, one step worse: leaflet-rotate is cache-first with a version in its
    # URL, so index.html and sw.js disagreeing means the file either never updates or (offline, with only the
    # other ?v= cached) does not load at all. The app survives that -- canRotate goes false and only the
    # orientation mode is gone -- which is exactly why nothing would shout about it.
    rot_tag = re.search(r'<script src="leaflet-rotate\.js\?v=(\d+)"', html)
    rot_url = re.search(r'ROTATE_URL\s*=\s*"\./leaflet-rotate\.js\?v=(\d+)"', sw)
    t.ok("index.html loads a versioned leaflet-rotate", bool(rot_tag), rot_tag and rot_tag.group(0), 'leaflet-rotate.js?v=N')
    t.ok("sw.js has ROTATE_URL", bool(rot_url), rot_url and rot_url.group(0), 'ROTATE_URL = "./leaflet-rotate.js?v=N"')
    if rot_tag and rot_url:
        t.eq("both request the same file", rot_tag.group(1), rot_url.group(1))
    t.ok("the file is on disk", os.path.exists(os.path.join(APP, "leaflet-rotate.js")), True, True)
    shell_src = re.search(r"APP_SHELL\s*=\s*\[([\s\S]*?)\]", sw)
    t.ok("and it is in APP_SHELL, so a first-ever offline visit has it",
         bool(shell_src) and "ROTATE_URL" in shell_src.group(1), True, True)

    t.case("every APP_SHELL entry exists on disk")
    shell = re.search(r"APP_SHELL\s*=\s*\[([\s\S]*?)\]", sw)
    t.ok("APP_SHELL found", bool(shell), bool(shell), True)
    missing, checked = [], 0
    if shell:
        for raw in re.findall(r'"([^"]+)"', shell.group(1)):
            if raw.startswith("http"):
                continue                                  # CDN assets: cached at runtime, not verifiable here
            path = raw.split("?")[0].lstrip("./")
            if not path or path == "/":
                continue
            checked += 1
            if not os.path.exists(os.path.join(APP, path)):
                missing.append(raw)
        # STYLE_URL is spliced in by variable, not as a literal, so count it separately.
        if style_url and not os.path.exists(os.path.join(APP, "style.css")):
            missing.append("style.css")
    t.ok("at least the shell's local files were checked", checked >= 2, checked, ">= 2")
    t.eq("no precache entry is a dead path", missing, [])

    t.case("the default region is precached and it is only ONE region")
    if shell:
        regions_in_shell = re.findall(r'"[^"]*regions/([a-z0-9_]+)\.json[^"]*"', shell.group(1))
        t.eq("exactly one region in the shell", len(regions_in_shell), 1)
        # Precaching every region would defeat the lazy loading the whole architecture exists for.
        t.ok("and it is the boot default", regions_in_shell == ["paznaun"], regions_in_shell, ["paznaun"])

    t.case("cache writes inside the fetch handler are wrapped in waitUntil")
    # Without it the browser may kill the worker before the write lands, silently dropping tiles from the
    # cache -- a real, previously fixed bug that leaves no trace when it comes back.
    puts = [m.start() for m in re.finditer(r"cache\.put\(", sw)]
    t.ok("there are cache.put calls to check", len(puts) > 0, len(puts), "> 0")
    unguarded = []
    for pos in puts:
        window = sw[max(0, pos - 600):pos]
        if "waitUntil" not in window:
            unguarded.append(sw[max(0, pos - 90):pos + 20].strip().splitlines()[-1])
    t.eq("every one sits inside a waitUntil", unguarded, [])

    t.case("the tile preload fetches with no-cors")
    # Public tile servers send no CORS headers, so a default-mode fetch rejects and nothing lands in the cache.
    # Note this lives in index.html's preload button, NOT in sw.js: the worker only ever answers requests the
    # page already made, and the browser fixes their mode. Worth stating, because CLAUDE.md lists the rule
    # under sw.js and this suite first looked for it there.
    t.ok('index.html preloads with mode: "no-cors"', 'mode: "no-cors"' in html or "mode: 'no-cors'" in html,
         'mode: "no-cors"' in html, True)

    t.case("index.html is one script block wrapped in the fatal-error try, and boot's rejection is caught")
    t.eq("exactly one inline script block", html.count("<script>"), 1)
    t.ok("the try/catch that feeds #fatalError is there", "catch (err)" in html and "fatalError" in html, True, True)
    # Everything past boot()'s first await is asynchronous: neither that try{} nor window.onerror sees a throw
    # there (an unhandled rejection is not an error event), which used to leave a silently half-started app.
    t.ok("boot() has a .catch", re.search(r"boot\(\)\s*\.catch\(", html) is not None, True, True)
    t.ok("window.onerror still shows the panel", "window.onerror" in html, True, True)

    t.case("the fatal-error panel's own copy stays generic")
    # It used to carry two paragraphs from the era when this was a file opened out of the Files app -- a
    # "preview-opened file" explanation and an iPhone "In Safari öffnen" tip -- neither of which is true of an
    # installed PWA served over HTTPS. The user called the tip out on 2026-08-04 ("Diese iPhone Tipp solltest
    # du aus der Fehlermeldung entfernen. Er stimmt nicht"), and on a home-screen PWA this panel is not
    # something a rider can dismiss, so wrong advice here is worse than none. The one case those paragraphs
    # described writes its OWN message into #fatalErrorMsg from boot(), which is why the static markup needs
    # nothing case-specific -- and that is the property checked: platform advice belongs in the dynamic
    # message, never in the static box.
    html = read("index.html")
    box = html[html.index('<div id="fatalError">'):html.index('<div id="regionDialog">')]
    visible = re.sub(r"<!--.*?-->", "", box, flags=re.S)          # the comment explains the history; ignore it
    strayed = [w for w in ("iPhone", "Safari", "Vorschau", "Files", "Chrome", "Android", "iOS")
               if w.lower() in visible.lower()]
    t.eq("no platform-specific advice in the static box", strayed, [])
    t.ok("it still says what to do", "Neu laden" in visible, visible.count("<p"), "mentions reloading")
    # The file:// case still has to carry its own explanation, or removing the static advice would leave the
    # one situation it was written for with nothing at all.
    t.ok("and the file:// case writes its own specific message",
         "http.server" in html and "fatalErrorMsg" in html, True, True)

    t.case("a clickable vector layer does not draw the browser's own focus box")
    # Leaflet gives every interactive polyline a tabindex, and the native focus ring follows the path's
    # RECTANGULAR SVG bounding box rather than its shape -- on an irregular trail that paints a stray black
    # frame across the map, most visibly after clicking a Trailrunde segment (2026-07-23). One CSS rule
    # suppresses it, and nothing else in the app would notice if it were dropped.
    css = read("style.css")
    rule = re.search(r"\.leaflet-interactive:focus\s*\{[^}]*\}", css)
    t.ok("style.css still suppresses it", rule and re.search(r"outline\s*:\s*none", rule.group(0)),
         rule.group(0) if rule else "no .leaflet-interactive:focus rule at all", "outline:none")

    t.case("the app folder contains only app files")
    # The whole folder is the Pages artifact, so anything in it is published and reachable by URL. One-off
    # editors, review pages and debug artifacts belong in tools/.
    allowed_ext = {".html", ".css", ".js", ".json", ".png", ".jpg", ".svg", ".ico", ".webmanifest", ".txt"}
    strays = []
    for name in os.listdir(APP):
        p = os.path.join(APP, name)
        if os.path.isdir(p):
            if name not in ("regions", "icons", "img", "assets"):
                strays.append(name + "/")
            continue
        if os.path.splitext(name)[1].lower() not in allowed_ext:
            strays.append(name)
    t.eq("nothing unexpected is published", strays, [])
    t.eq("index.html is the only html file in the app folder",
         sorted(f for f in os.listdir(APP) if f.endswith(".html")), ["index.html"])
