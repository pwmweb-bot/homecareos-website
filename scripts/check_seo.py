#!/usr/bin/env python3
"""Check title and meta description lengths, JSON-LD, and links in new posts.

Titles must be 60 characters or fewer. Descriptions must be 160 or fewer.
Counts are of the decoded text, not the HTML entity encoding.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_POSTS = [
    "blog/care-certificate-home-care-agencies.html",
    "blog/electronic-call-monitoring-home-care.html",
    "blog/care-planning-software-uk.html",
    "blog/national-minimum-wage-travel-time-home-care.html",
    "blog/safeguarding-adults-home-care-agencies.html",
    "blog/dbs-check-for-care-workers.html",
    "blog/duty-of-candour-home-care-agencies.html",
    "blog/cqc-notifications-home-care-agencies.html",
    "blog/cqc-statement-of-purpose-home-care.html",
    "blog/medication-management-home-care-nice-ng67.html",
    "blog/riddor-reporting-home-care-agencies.html",
    "blog/home-care-app-login-portals.html",
    "blog/lone-working-home-care-agencies.html",
    "blog/mandatory-training-care-workers.html",
    "blog/complaints-procedure-home-care-agencies.html",
    "blog/person-centred-care-plan-examples-home-care.html",
]
# Audit row marked keep. Do not shorten it in this change.
KEEP_OVER_LIMIT = {
    "blog/home-care-software-uk-guide.html":
        "Home Care Software UK: Domiciliary Buyer's Guide | homecareOS",
}
# Vendor help centres behind a Cloudflare bot check. They answer some scripted
# requests with 403 at random, while the same page opens in a browser. A 403 from
# these hosts is printed as a note to check by hand, not counted as a failure.
BOT_CHECK_HOSTS = {
    "onetouchhealthhelp.zendesk.com",
    "support.carelinelive.com",
}
# Ads landing pages. Google may crawl them, and they must stay out of the index.
NOINDEX_ALLOW = {
    "switch-from-quikplan.html",
}


class MetaGrab(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.robots = ""
        self.in_title = False
        self.title_done = False
        self.ld = []
        self.in_ld = False
        self.ld_buf = []

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "title" and not self.title_done:
            self.in_title = True
        if tag == "meta":
            name = (ad.get("name") or ad.get("property") or "").lower()
            if name == "description" and not self.description:
                self.description = ad.get("content") or ""
            if name == "robots":
                self.robots = ad.get("content") or ""
        if tag == "script" and ad.get("type") == "application/ld+json":
            self.in_ld = True
            self.ld_buf = []

    def handle_endtag(self, tag):
        if tag == "title" and self.in_title:
            self.in_title = False
            self.title_done = True
        if tag == "script" and self.in_ld:
            self.ld.append("".join(self.ld_buf))
            self.in_ld = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_ld:
            self.ld_buf.append(data)


def pages():
    found = []
    for dirpath, names in ((ROOT, [f for f in os.listdir(ROOT) if f.endswith(".html")]),):
        for name in names:
            found.append(name)
    blog = os.path.join(ROOT, "blog")
    for name in os.listdir(blog):
        if name.endswith(".html"):
            found.append("blog/" + name)
    return sorted(found)


def main():
    errors = []
    for rel in pages():
        if rel == "blog/index.html":
            continue
        path = os.path.join(ROOT, rel)
        parser = MetaGrab()
        parser.feed(open(path, encoding="utf-8", errors="ignore").read())
        title = parser.title.strip()
        desc = html.unescape(parser.description).strip()
        if rel in NOINDEX_ALLOW or "noindex" in parser.robots.lower():
            if rel in NOINDEX_ALLOW and "noindex" not in parser.robots.lower():
                errors.append(f"{rel} is an ads landing page and must be noindex")
            elif title and len(title) > 60 or desc and len(desc) > 160:
                if rel in NOINDEX_ALLOW:
                    pass
                else:
                    print(f"note: noindex, left unchanged {rel} title {len(title)} description {len(desc)}")
            continue
        if title and len(title) > 60:
            if KEEP_OVER_LIMIT.get(rel) == title:
                print(f"note: audit keep, title {len(title)} {rel}")
            else:
                errors.append(f"title {len(title)} {rel}: {title}")
        if desc and len(desc) > 160:
            errors.append(f"description {len(desc)} {rel}: {desc}")
        for block in parser.ld:
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f"json-ld {rel}: {exc}")

    testimonials = open(os.path.join(ROOT, "testimonials.html"), encoding="utf-8").read()
    if "noindex" not in testimonials:
        errors.append("testimonials.html is not noindex")
    sitemap = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    if "testimonials.html" in sitemap:
        errors.append("testimonials.html is still in sitemap.xml")
    for rel in sorted(NOINDEX_ALLOW):
        if rel in sitemap or f"/{rel}" in sitemap:
            errors.append(f"{rel} is noindex and must stay out of sitemap.xml")
    for rel in NEW_POSTS:
        loc = "https://www.homecareos.co.uk/" + rel
        if loc not in sitemap:
            errors.append(f"missing from sitemap: {loc}")

    link_errors = check_links(NEW_POSTS)
    errors.extend(link_errors)
    if errors:
        print(f"{len(errors)} problem(s):")
        print("\n".join(errors))
        return 1
    print(f"titles and descriptions within limits across {len(pages()) - 1} pages")
    print("JSON-LD parses; testimonials noindexed and absent from the sitemap")
    print(f"links checked on {len(NEW_POSTS)} new posts")
    return 0


def check_links(rels):
    problems = []
    seen = set()
    for rel in rels:
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        start = text.find("<main")
        end = text.find("<footer")
        if start >= 0 and end > start:
            text = text[start:end]
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            if href in seen:
                continue
            seen.add(href)
            if href.startswith("https://www.homecareos.co.uk/"):
                href = href[len("https://www.homecareos.co.uk"):]
            if href.startswith("/"):
                target = href.split("#", 1)[0].split("?", 1)[0]
                if target in ("", "/"):
                    fs = os.path.join(ROOT, "index.html")
                elif target.endswith("/"):
                    fs = os.path.join(ROOT, target.strip("/"), "index.html")
                else:
                    fs = os.path.join(ROOT, target.lstrip("/"))
                    if not os.path.isfile(fs) and os.path.isfile(fs + ".html"):
                        fs = fs + ".html"
                if not os.path.isfile(fs):
                    problems.append(f"missing file for {href} from {rel}")
            elif href.startswith("http"):
                status = fetch_status(href)
                host = urllib.parse.urlsplit(href).hostname or ""
                if status == 403 and host in BOT_CHECK_HOSTS:
                    print(f"note: 403 from bot check, open by hand: {href}")
                    continue
                if status is None or status >= 400:
                    problems.append(f"HTTP {status} {href}")
    return problems


def fetch_status(url):
    req = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "Mozilla/5.0 (compatible; homecareOS-linkcheck/1.0; +https://www.homecareos.co.uk/)",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(main())
