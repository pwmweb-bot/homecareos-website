#!/usr/bin/env python3
"""Inject the shared header (partials/header.html) into every page, and bump the
CSS cache-buster. Re-runnable: it replaces the current <nav class="nav">...</nav>
block (including one already injected) with the partial's current content.

Usage:
  python3 build.py            # all root + blog pages
  python3 build.py a.html b.html   # only the named files
"""
import io, re, sys, glob, os
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
CSS_VERSION = "20260909insp"

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

# --- structural guard -------------------------------------------------------
# In April 2026 the "remove chat widget" edit deleted the widget's opening tags
# but left its two closing </div>s sitting after </footer>. That survived on 41
# pages for five months because nothing ever checked. Browsers silently discard
# a stray </div>, so only a parser catches it. This is a warning, not a failure.

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

class TagBalance(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.stack, self.errors = [], []
    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()))
    def handle_startendtag(self, tag, attrs):
        pass  # <path/> and friends open and close in one go
    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.errors += [("unclosed <%s>" % t, p) for t, p in self.stack[i + 1:]]
                self.stack = self.stack[:i]
                return
        self.errors.append(("stray </%s>" % tag, self.getpos()))

def validate(files):
    bad = []
    for f in files:
        p = TagBalance()
        p.feed(io.open(os.path.join(ROOT, f), encoding="utf-8", errors="ignore").read())
        p.close()
        errs = p.errors + [("unclosed <%s> at EOF" % t, pos) for t, pos in p.stack]
        if errs:
            bad.append((f, errs))
    return bad

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
    bad = validate(files)
    if bad:
        print(f"\nWARNING: unbalanced tags in {len(bad)} file(s):")
        for f, errs in bad:
            print(f"  {f}")
            for msg, (line, col) in errs[:5]:
                print(f"      line {line} col {col}: {msg}")
    else:
        print(f"tag balance: clean across {len(files)} files")
