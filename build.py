#!/usr/bin/env python3
"""Inject the shared header (partials/header.html) into every page, and bump the
CSS cache-buster. Re-runnable: it replaces the current <nav class="nav">...</nav>
block (including one already injected) with the partial's current content.

Usage:
  python3 build.py            # all root + blog pages
  python3 build.py a.html b.html   # only the named files
"""
import io, re, sys, glob, os

ROOT = os.path.dirname(os.path.abspath(__file__))
CSS_VERSION = "20260902meganav"

HEADER = io.open(os.path.join(ROOT, "partials/header.html"), encoding="utf-8").read().rstrip("\n")
FOOTER = io.open(os.path.join(ROOT, "partials/footer.html"), encoding="utf-8").read().rstrip("\n")
NAV_RE = re.compile(r'<nav class="nav"[^>]*>.*?</nav>', re.S)
FOOTER_RE = re.compile(r'<footer class="footer"[^>]*>.*?</footer>', re.S)
CSS_RE = re.compile(r'(styles\.css\?v=)[^"\']*')

def build(files):
    changed, skipped_nonav, skipped_nofoot = [], [], []
    for f in files:
        path = os.path.join(ROOT, f)
        s = io.open(path, encoding="utf-8", errors="ignore").read()
        orig = s
        if NAV_RE.search(s):
            s = NAV_RE.sub(lambda m: HEADER, s, count=1)
        else:
            skipped_nonav.append(f)
        if FOOTER_RE.search(s):
            s = FOOTER_RE.sub(lambda m: FOOTER, s, count=1)
        else:
            skipped_nofoot.append(f)
        s = CSS_RE.sub(r"\g<1>" + CSS_VERSION, s)
        if s != orig:
            io.open(path, "w", encoding="utf-8").write(s)
            changed.append(f)
    return changed, skipped_nonav, skipped_nofoot

if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        files = args
    else:
        os.chdir(ROOT)
        files = sorted(glob.glob("*.html")) + sorted(glob.glob("blog/*.html"))
    changed, nonav, nofoot = build(files)
    print(f"changed: {len(changed)} files")
    print(f"no <nav class='nav'> (skipped nav inject): {nonav}")
    print(f"no <footer class='footer'> (skipped footer inject): {nofoot}")
