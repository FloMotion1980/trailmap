"""Regenerate Trailmap App/regions/version.json from the region files themselves.

WHY THIS EXISTS: the app fetches each region as `regions/<key>.json?v=<hash>` and the service worker serves
those cache-first, so *the hash in this manifest is the only thing that invalidates a cached region*. Miss the
step and an edited region silently never reaches a device that already has it -- and a region absent from the
manifest is fetched unversioned, i.e. cached once and then stale forever.

Both had already happened when this was written (2026-07-28): editing paznaun.json left its hash untouched, and
brandnertal/schladming/zugspitzarena had never been added at all. `validate_region.py` now checks the manifest,
but this is what fixes it.

    python tools/update_region_versions.py          # rewrite the manifest
    python tools/update_region_versions.py --check   # report drift, exit 1, change nothing

The algorithm is md5 of the file's bytes, first 10 hex chars -- derived from the existing entries, not chosen.
Only the *change* matters, but staying consistent means a rebuild produces no spurious diff.
"""
import hashlib
import io
import json
import os
import sys

REGIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           os.pardir, "Trailmap App", "regions")
MANIFEST = "version.json"


def file_hash(path):
    return hashlib.md5(io.open(path, "rb").read()).hexdigest()[:10]


def current_hashes():
    return {f[:-5]: file_hash(os.path.join(REGIONS_DIR, f))
            for f in sorted(os.listdir(REGIONS_DIR))
            if f.endswith(".json") and f != MANIFEST}


def main(argv):
    check_only = "--check" in argv
    path = os.path.join(REGIONS_DIR, MANIFEST)
    want = current_hashes()
    try:
        have = json.load(io.open(path, encoding="utf-8"))
    except (IOError, ValueError):
        have = {}

    stale = {k: (have.get(k), v) for k, v in want.items() if have.get(k) != v}
    orphaned = sorted(set(have) - set(want))

    for key, (old, new) in sorted(stale.items()):
        print("%-16s %s -> %s" % (key, old or "MISSING", new))
    for key in orphaned:
        print("%-16s stale entry, no such region file" % key)

    if not stale and not orphaned:
        print("version.json is up to date (%d regions)" % len(want))
        return 0
    if check_only:
        print("\n%d entr%s need updating -- run without --check"
              % (len(stale) + len(orphaned), "y" if len(stale) + len(orphaned) == 1 else "ies"))
        return 1

    # Same formatting as the existing manifest: one line, keys in file order.
    json.dump(want, io.open(path, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, separators=(",", ":"))
    print("\nwrote %s (%d regions)" % (MANIFEST, len(want)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
