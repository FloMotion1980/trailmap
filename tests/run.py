# -*- coding: utf-8 -*-
"""The one entry point for Trailmap's tests.

    python tests/run.py                    # every suite: run the Python ones, bundle every browser one
    python tests/run.py --changed          # only the suites your current changes can plausibly affect
    python tests/run.py --changed --base origin/main
    python tests/run.py --suite pipeline solo
    python tests/run.py --list             # what exists and what each suite watches

WHY IT IS TWO RUNNERS AND NOT ONE PROCESS. The Python suites check the build pipeline and the data, and run
headless right here. The browser suites have to execute *inside the running app's page*: everything the app
owns (`lineLayers`, `soloId`, `LIFTS`, …) is a const/let inside its top-level try{} block and is therefore
unreachable from any separately-evaluated script, while plain function declarations do leak to the global
scope (sloppy-mode Annex B). There is no way to import the app; you can only stand inside it. So this script
runs the Python half and *bundles* the selected browser half into one paste-ready file, printing the path.

WHY THE SELECTION MAP LIVES IN THE TEST FILES. Each suite declares what it watches in its own header:

    @suite   solo
    @area    Solo mode
    @files   Trailmap App/index.html
    @touches applySolo, clearSolo, applyLiftVisibility, baselineLineOpacity
    @needs   region=bikekingdom, builder=off

`--changed` selects a suite when one of its @files changed AND (it declares no @touches, or one of them
appears in the diff). Declaring this next to the tests is the point: a mapping kept in a doc rots silently,
whereas this one is read by the runner every time, and a changed file that no suite claims is reported as a
GAP rather than passing quietly. `@always` marks the cheap data checks that run whatever changed.
"""
import argparse
import fnmatch
import io
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
BUNDLE = os.path.join(TESTS, "_bundle.js")
# `// @tag` in a .js header, `# @tag` or a bare `@tag` inside a .py module docstring.
TAG = re.compile(r"^\s*(?://|#)?\s*@(\w+)(?:\s+(.*?))?\s*$")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_header(path):
    """Read the @tags out of a suite's first 80 lines. Unknown tags are kept, so adding one is harmless."""
    meta = {"path": path, "kind": "python" if path.endswith(".py") else "browser",
            "files": [], "touches": [], "always": False, "standalone": False,
            "needs": "", "area": "", "suite": None}
    with io.open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            if n > 80:
                break
            m = TAG.match(line)
            if not m:
                continue
            key, val = m.group(1), m.group(2) or ""
            if key in ("files", "touches"):
                meta[key] += [v.strip() for v in val.split(",") if v.strip()]
            elif key in ("always", "standalone"):
                meta[key] = True
            elif key in meta or key in ("needs", "area", "suite"):
                meta[key] = val
    if not meta["suite"]:
        meta["suite"] = os.path.splitext(os.path.basename(path))[0].lstrip("_")
    return meta


def discover():
    suites = []
    for sub in ("python", "browser"):
        d = os.path.join(TESTS, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.startswith("_") or not name.endswith((".py", ".js")):
                continue
            suites.append(parse_header(os.path.join(d, name)))
    return suites


def git(*args):
    try:
        out = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        return out.stdout or ""
    except Exception:
        return ""


def changed_files_and_lines(base):
    """Uncommitted work plus, if a base is given, everything since it. Returns (files, diff text)."""
    files, diff = set(), []
    ranges = ["HEAD"] if base is None else [base]
    for rng in ranges:
        for line in git("diff", "--name-only", rng).splitlines():
            if line.strip():
                files.add(line.strip())
        diff.append(git("diff", "-U0", rng))
    for line in git("status", "--porcelain").splitlines():   # includes untracked
        p = line[3:].strip().strip('"')
        if p:
            files.add(p)
    return files, "\n".join(diff)


def select(suites, changed, diff):
    chosen, reasons, claimed = [], {}, set()
    for s in suites:
        if s["always"]:
            chosen.append(s)
            reasons[s["suite"]] = "@always"
            continue
        hits = [f for f in changed if any(fnmatch.fnmatch(f, pat) or f == pat for pat in s["files"])]
        if not hits:
            continue
        claimed.update(hits)
        if not s["touches"]:
            chosen.append(s)
            reasons[s["suite"]] = "%s changed" % hits[0]
            continue
        syms = [sym for sym in s["touches"] if re.search(r"\b%s\b" % re.escape(sym), diff)]
        if syms:
            claimed.update(hits)
            chosen.append(s)
            reasons[s["suite"]] = "%s in %s" % (", ".join(syms[:3]), hits[0])
    # A file nobody watches is the interesting case: it is a hole in the library, not a pass.
    gaps = sorted(f for f in changed
                  if f not in claimed
                  and not f.startswith("tests/")
                  and not f.startswith("docs/")
                  and f not in ("CLAUDE.md",)
                  and not any(any(fnmatch.fnmatch(f, pat) or f == pat for pat in s["files"]) for s in suites))
    return chosen, reasons, gaps


def run_python(suite):
    """Each Python suite exposes run(t) and uses the tiny collector below. No pytest: this repo has no
    dependency manifest at all and adding one for the tests would be the biggest new moving part here."""
    sys.path.insert(0, os.path.dirname(suite["path"]))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    name = os.path.splitext(os.path.basename(suite["path"]))[0]
    mod = __import__(name)
    t = Collector(suite["suite"])
    try:
        mod.run(t)
    except Exception as err:            # a suite that blows up is a failure, not a crash of the runner
        import traceback
        t.fail_hard("%s: %s" % (type(err).__name__, err), traceback.format_exc())
    return t


class Collector(object):
    def __init__(self, suite):
        self.suite = suite
        self.cases = []
        self.current = None

    def case(self, name):
        self.current = {"name": name, "checks": []}
        self.cases.append(self.current)

    def ok(self, label, cond, got=None, want=None):
        self.current["checks"].append({"label": label, "pass": bool(cond), "got": got, "want": want})

    def eq(self, label, got, want):
        self.ok(label, got == want, got, want)

    def near(self, label, got, want, tol):
        self.ok(label, abs(got - want) <= tol, got, "%s ±%s" % (want, tol))

    def fail_hard(self, msg, detail=""):
        self.case("suite aborted")
        self.ok(msg, False, detail.strip().splitlines()[-1] if detail else "", "no exception")

    @property
    def checks(self):
        return sum(len(c["checks"]) for c in self.cases)

    def report(self):
        passed = failed = 0
        lines = []
        for c in self.cases:
            bad = [x for x in c["checks"] if not x["pass"]]
            if bad:
                failed += 1
                lines.append("  FAIL  %s" % c["name"])
                for b in bad:
                    lines.append("          %s: got %r, want %r" % (b["label"], b["got"], b["want"]))
            else:
                passed += 1
                lines.append("  ok    %s" % c["name"])
        return passed, failed, lines


def bundle(browser_suites):
    """One paste-ready file: the shared harness, then each selected suite, then the report. Individual
    suites are also pasteable on their own (harness first) -- this exists so "run what changed" is one paste."""
    parts = [io.open(os.path.join(TESTS, "browser", "_harness.js"), encoding="utf-8").read()]
    # State-changing suites go LAST. `regions` genuinely loads and unloads region data, and although it puts
    # the set back itself, running it before the others once left seven suites reporting failures that read
    # like broken filter rules. Cheap insurance: order the bundle so nothing depends on that restore working.
    browser_suites = sorted(browser_suites, key=lambda s: (s["suite"] == "regions", s["suite"]))
    for s in browser_suites:
        parts.append("\n// ===== %s =====\n" % os.path.basename(s["path"]))
        parts.append(io.open(s["path"], encoding="utf-8").read())
    # No trailing TM.report(): the harness reports by itself once the queue drains. Calling it here as well
    # printed an empty "0 passed, 0 failed" the instant the bundle loaded, before a single case had run --
    # which reads exactly like a broken suite.
    parts.append("\n")
    with io.open(BUNDLE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(parts))
    return BUNDLE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", action="store_true", help="only suites your changes can affect")
    ap.add_argument("--base", default=None, help="compare against this ref instead of the working tree")
    ap.add_argument("--suite", nargs="*", default=None, help="run these suites by name")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    suites = discover()
    if args.list:
        print("suite            kind     watches")
        print("-" * 78)
        for s in suites:
            watch = "@always" if s["always"] else (", ".join(s["touches"][:4]) or ", ".join(s["files"]))
            print("%-16s %-8s %s" % (s["suite"], s["kind"], watch[:56]))
            if s["needs"]:
                print("%-16s %-8s needs: %s" % ("", "", s["needs"]))
        return 0

    reasons, gaps = {}, []
    if args.suite:
        chosen = [s for s in suites if s["suite"] in args.suite]
        missing = set(args.suite) - {s["suite"] for s in chosen}
        if missing:
            print("unknown suite(s): %s" % ", ".join(sorted(missing)))
            return 2
    elif args.changed:
        changed, diff = changed_files_and_lines(args.base)
        chosen, reasons, gaps = select(suites, changed, diff)
        print("changed: %s" % (", ".join(sorted(changed)) or "nothing"))
    else:
        chosen = suites

    py = [s for s in chosen if s["kind"] == "python"]
    js = [s for s in chosen if s["kind"] == "browser"]

    print("\nselected %d of %d suites%s" % (len(chosen), len(suites), " (--changed)" if args.changed else ""))
    for s in chosen:
        print("  %-16s %s" % (s["suite"], reasons.get(s["suite"], "")))
    if gaps:
        print("\nGAP — changed but watched by no suite:")
        for f in gaps:
            print("  %s" % f)

    total_pass = total_fail = total_checks = 0
    if py:
        print("\n--- python ---")
        for s in py:
            started = time.time()
            t = run_python(s)
            p, f, lines = t.report()
            total_pass += p
            total_fail += f
            total_checks += t.checks
            print("%s  (%d checks, %.1fs)" % (s["suite"], t.checks, time.time() - started))
            print("\n".join(lines))

    if js:
        shared = [s for s in js if not s["standalone"]]
        alone = [s for s in js if s["standalone"]]
        print("\n--- browser ---")
        # Serve from the REPO ROOT, not from "Trailmap App/": a suite loaded from a different origin than the
        # page reports every error as an opaque "Script error." with no line number, and the app's own
        # window.onerror turns that into its fatal panel. Cost an hour once; hence the instruction.
        print("Serve the repo root and open the app from there, so the tests are same-origin:")
        print("  python -m http.server 8099   →   http://localhost:8099/Trailmap%20App/index.html")
        if shared:
            path = bundle(shared)
            print("\n%d suite(s) bundled: %s" % (len(shared), ", ".join(s["suite"] for s in shared)))
            needs = sorted({n.strip() for s in shared for n in s["needs"].split(",") if n.strip()})
            if needs:
                print("preconditions: %s" % "; ".join(needs))
            print("Paste into the console:  %s" % path)
        for s in alone:
            print("\n%s brings its own harness — paste it ALONE: %s" % (s["suite"], s["path"]))
            if s["needs"]:
                print("  preconditions: %s" % s["needs"])

    print("\n%d passed, %d failed, %d checks (python)" % (total_pass, total_fail, total_checks))
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
