#!/usr/bin/env python3
"""Inject the shared header and footer, regenerate sitemap.xml, and publish
blog posts from Markdown.

The site is static HTML. This script does not deploy it. The Google tag
(partials/gtag.html) is injected with the header and footer, so page files
are not edited by hand when the tag changes.

Usage:
  python3 build.py                         # inject partials, then sitemap
                                           # (*.html, blog/, help/, account/)
  python3 build.py a.html b.html           # inject those files, then sitemap
  python3 build.py sitemap                 # rewrite sitemap.xml only
  python3 build.py publish                 # every content/blog/*.md except _*
  python3 build.py publish content/blog/x.md
"""
import io, re, sys, glob, os
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
CSS_VERSION = "20261016cta"

HEADER = io.open(os.path.join(ROOT, "partials/header.html"), encoding="utf-8").read().rstrip("\n")
FOOTER = io.open(os.path.join(ROOT, "partials/footer.html"), encoding="utf-8").read().rstrip("\n")
GTAG = io.open(os.path.join(ROOT, "partials/gtag.html"), encoding="utf-8").read().strip("\n")
NAV_RE = re.compile(r'<nav class="nav"[^>]*>.*?</nav>', re.S)
FOOTER_RE = re.compile(r'<footer class="footer"[^>]*>.*?</footer>', re.S)
CSS_RE = re.compile(r'(styles\.css\?v=)[^"\']*')
GTAG_MARKER_RE = re.compile(r"[ \t]*<!-- hcos:gtag -->.*?<!-- /hcos:gtag -->\n?", re.S)
COOKIE_SRC_RE = re.compile(
    r'<script\s+src="/cookie-consent\.js[^"]*"\s+defer></script>'
    r'|<script\s+defer\s+src="/cookie-consent\.js[^"]*"></script>'
)


def legacy_gtag_span(html):
    """Return [start, end) of the pre-partial gtag bootstrap, if present."""
    idx = 0
    while True:
        idx = html.find("window.dataLayer", idx)
        if idx < 0:
            return None
        if "function gtag" not in html[idx:idx + 500]:
            idx += len("window.dataLayer")
            continue
        script_start = html.rfind("<script", 0, idx)
        if script_start < 0:
            return None
        before = html[:script_start].rstrip(" \t")
        comment = re.search(r"<!-- Google tag \(gtag\.js\)[^>]*-->$", before)
        start = comment.start() if comment else script_start
        consent = COOKIE_SRC_RE.search(html, idx)
        if not consent:
            return None
        end = consent.end()
        if end < len(html) and html[end] == "\n":
            end += 1
        return start, end


def inject_gtag(html):
    block = GTAG + "\n"
    if "<!-- hcos:gtag -->" in html:
        return GTAG_MARKER_RE.sub(block, html, count=1)
    span = legacy_gtag_span(html)
    if span:
        return html[:span[0]] + block + html[span[1]:]
    head = re.search(r"</head>", html, re.I)
    if not head:
        return html
    return html[:head.start()] + block + html[head.start():]

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
        s = inject_gtag(s)
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

def inject(files):
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
    return bad


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["publish"]:
        from blogpub import publish_command, write_sitemap
        publish_command(args[1:])
        write_sitemap()
    elif args[:1] == ["sitemap"]:
        from blogpub import write_sitemap
        write_sitemap()
    else:
        if args:
            files = args
        else:
            os.chdir(ROOT)
            files = (
                sorted(glob.glob("*.html"))
                + sorted(glob.glob("blog/*.html"))
                + sorted(glob.glob("help/*.html"))
                + sorted(glob.glob("account/*.html"))
            )
        inject(files)
        from blogpub import write_sitemap
        write_sitemap()
