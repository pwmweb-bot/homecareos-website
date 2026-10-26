#!/usr/bin/env python3
"""Render the help centre from content/help/articles.py.

Writes help.html (the landing page) and help/<slug>.html (one per article),
then runs build.py on them to inject the shared header, footer and Google tag,
and rewrites the sitemap.

  python3 scripts/build_help.py

Commit the article data and the generated HTML together.
"""
import html
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "content", "help"))
from articles import ARTICLES, ROLES, GETTING_STARTED  # noqa: E402

SITE = "https://www.homecareos.co.uk"
UPDATED = "2026-10-26"
HELP_CSS = "/help/help.css?v=20261026"
HELP_JS = "/js/help.js?v=20261026"
BY_SLUG = {a["slug"]: a for a in ARTICLES}

STATUS = {
    "live": ("Live", "Every agency has this today."),
    "rolling": ("Rolling out", "These steps use the new HomecareOS screens, which are being switched on agency by agency."),
    "soon": ("Coming soon", "Planned. Not available yet."),
}

# Thin line icons, 24px grid, stroke only. No decoration.
ICONS = {
    "office": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 4v5M8 13h3M8 16h6"/>',
    "carer": '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
    "owner": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"/>',
    "start": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "user-plus": '<circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 12 0v1M19 8v6M16 11h6"/>',
    "clipboard": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1M9 10h6M9 14h6M9 18h3"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "calendar-x": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4M10 13l4 4M14 13l-4 4"/>',
    "user-switch": '<circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 12 0v1M16 9h6M19 6l3 3-3 3M22 16h-6M19 13l-3 3 3 3"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "pill": '<rect x="2.5" y="8.5" width="19" height="7" rx="3.5" transform="rotate(-45 12 12)"/><path d="M8.5 8.5l7 7"/>',
    "smartphone": '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "map-pin": '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "check-square": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 12l3 3 5-6"/>',
    "alert": '<path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18h.01"/>',
    "users": '<circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 12 0v1M16 4a4 4 0 0 1 0 8M22 21v-1a6 6 0 0 0-4-5.6"/>',
    "message": '<path d="M4 4h16v12H8l-4 4V4z"/><path d="M8 9h8M8 12h5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 16l5-5 4 4 3-3 6 6"/><circle cx="15.5" cy="8.5" r="1.5"/>',
}


def icon(name, size=24, cls="help-icon"):
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{ICONS[name]}</svg>')


def esc(s):
    return html.escape(s, quote=True)


def text(s):
    """Plain text of a snippet that may hold simple inline HTML."""
    import re
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def badge(status):
    label, _ = STATUS[status]
    return f'<span class="help-badge help-badge-{status}">{label}</span>'


def head(title, description, canonical, ld, og_type="article"):
    lds = "\n".join(
        f'  <script type="application/ld+json">\n  {json.dumps(block, ensure_ascii=False)}\n  </script>' for block in ld
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <link rel="icon" type="image/svg+xml" href="/images/brand/favicon-light.svg">
  <link rel="icon" type="image/svg+xml" media="(prefers-color-scheme: dark)" href="/images/brand/favicon-dark.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-light-32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/favicon-light-16.png">
  <link rel="icon" type="image/png" sizes="192x192" href="/favicon-light-192.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <meta name="theme-color" content="#16323D">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canonical}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:locale" content="en_GB">
  <meta property="og:site_name" content="homecareOS">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <link rel="preload" href="/fonts/dmsans-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/fonts/dmsans.css?v=20260521">
  <link rel="stylesheet" href="/styles.css?v=20261016cta">
  <link rel="stylesheet" href="{HELP_CSS}">
{lds}
  <script src="/js/book-demo.js?v=20261020" defer></script>
  <script src="{HELP_JS}" defer></script>
</head>
<body class="help-page">
  <a href="#main-content" class="skip-link" id="skip-link">Skip to main content</a>
  <nav class="nav" role="navigation" aria-label="Main navigation"></nav>
"""


FOOT = """  <footer class="footer" role="contentinfo"></footer>
  <script>
    const nav = document.querySelector('.nav');
    window.addEventListener('scroll', () => { nav.classList.toggle('scrolled', window.scrollY > 20); });
    const toggle = document.getElementById('nav-toggle');
    const links = document.getElementById('nav-links');
    toggle.addEventListener('click', () => {
      const isOpen = links.classList.toggle('open');
      toggle.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen);
    });
    document.querySelectorAll('.nav-dropdown-toggle').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const dropdown = btn.closest('.nav-dropdown');
        const isOpen = dropdown.classList.toggle('open');
        btn.setAttribute('aria-expanded', isOpen);
      });
    });
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.nav-dropdown')) {
        document.querySelectorAll('.nav-dropdown.open').forEach(d => {
          d.classList.remove('open');
          d.querySelector('.nav-dropdown-toggle')?.setAttribute('aria-expanded', 'false');
        });
      }
    });
    document.getElementById('skip-link').addEventListener('click', function(e) {
      e.preventDefault();
      document.getElementById('main-content').focus();
    });
  </script>

</body>
</html>
"""

STILL_STUCK = f"""<aside class="help-stuck" aria-labelledby="stuck-heading">
          <div class="help-stuck-icon">{icon("phone", 28)}</div>
          <div>
            <h2 id="stuck-heading">Still stuck?</h2>
            <p>Book a 15-minute demo and we will walk you through it, or call us on <a href="tel:01905674704">01905 674704</a>.</p>
          </div>
          <div class="help-stuck-actions">
            <a href="/booking.html" class="btn btn-primary">Book a 15-minute demo</a>
            <a href="tel:01905674704" class="btn btn-outline">Call 01905 674704</a>
          </div>
        </aside>"""


def card(a):
    role = ROLES[a["role"]]
    search = " ".join([a["title"], a["summary"], a["keywords"], role["name"]]).lower()
    return f"""<a class="help-card" href="/help/{a['slug']}.html" data-search="{esc(search)}">
              <span class="help-card-icon">{icon(a['icon'])}</span>
              <span class="help-card-body">
                <span class="help-card-title">{esc(a['title'])}</span>
                <span class="help-card-summary">{esc(a['summary'])}</span>
                <span class="help-card-meta">{badge(a['status'])}</span>
              </span>
            </a>"""


def landing():
    title = "Help centre: guides for home care agencies | HomecareOS"
    if len(title) > 60:
        title = "HomecareOS Help: guides for agencies and carers"
    description = ("Step-by-step HomecareOS guides for office teams, carers and agency owners: "
                   "service users, care plans, the rota, cover, eMAR and the carer app.")
    canonical = SITE + "/help.html"
    ld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": "HomecareOS Help centre",
         "description": description, "url": canonical, "inLanguage": "en-GB",
         "hasPart": [{"@type": "TechArticle", "headline": a["title"], "url": f"{SITE}/help/{a['slug']}.html"} for a in ARTICLES]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Help", "item": canonical}]},
    ]
    out = [head(title, description, canonical, ld, og_type="website")]
    path = []
    for i, (t, slug, sub) in enumerate(GETTING_STARTED, 1):
        path.append(f"""<li class="help-path-step">
              <a href="/help/{slug}.html">
                <span class="help-path-num">{i}</span>
                <span class="help-path-title">{esc(t)}</span>
                <span class="help-path-sub">{esc(sub)}</span>
              </a>
            </li>""")
    sections = []
    for key, role in ROLES.items():
        items = [a for a in ARTICLES if a["role"] == key]
        cards = "\n            ".join(card(a) for a in items)
        sections.append(f"""<section class="help-role" id="{key}" aria-labelledby="{key}-heading">
          <header class="help-role-head">
            <span class="help-role-icon">{icon(key, 28)}</span>
            <div>
              <h2 id="{key}-heading">{esc(role['name'])}</h2>
              <p>{esc(role['intro'])}</p>
            </div>
          </header>
          <div class="help-grid">
            {cards}
          </div>
        </section>""")
    legend = "".join(f'<li>{badge(k)} <span>{esc(v[1])}</span></li>' for k, v in STATUS.items())
    out.append(f"""  <main id="main-content" tabindex="-1">
    <header class="page-header help-header">
      <div class="container">
        <nav class="breadcrumbs" aria-label="Breadcrumb">
          <a href="/index.html">Home</a>
          <span aria-hidden="true">/</span>
          <span class="current" aria-current="page">Help</span>
        </nav>
        <h1>HomecareOS Help centre</h1>
        <p>Short, step-by-step guides for the office, carers and agency owners.</p>
        <form class="help-search" role="search" onsubmit="return false">
          <label for="help-search-input" class="visually-hidden">Search the help centre</label>
          {icon("search", 20)}
          <input id="help-search-input" type="search" placeholder="Search, for example &quot;cover&quot; or &quot;clock in&quot;" autocomplete="off">
        </form>
        <p class="help-search-count" id="help-search-count" aria-live="polite"></p>
      </div>
    </header>
    <div class="section help-section">
      <div class="container">
        <section class="help-start" id="getting-started" aria-labelledby="start-heading">
          <header class="help-role-head">
            <span class="help-role-icon">{icon("start", 28)}</span>
            <div>
              <h2 id="start-heading">Getting started: five steps for a new agency</h2>
              <p>Do these in order and your first carer can clock in to your first visit.</p>
            </div>
          </header>
          <ol class="help-path">
            {"".join(path)}
          </ol>
        </section>
        {"".join(sections)}
        <p class="help-empty" id="help-empty" hidden>No guides match that search. Try another word, or call us on <a href="tel:01905674704">01905 674704</a>.</p>
        <section class="help-legend" aria-labelledby="legend-heading">
          <h2 id="legend-heading">What the labels mean</h2>
          <ul>{legend}</ul>
          <p>The new HomecareOS design is being switched on agency by agency. If your screens look different from a guide, call us and we will walk you through it.</p>
        </section>
        {STILL_STUCK}
      </div>
    </div>
  </main>
""")
    out.append(FOOT)
    return "".join(out)


def article(a):
    role = ROLES[a["role"]]
    canonical = f"{SITE}/help/{a['slug']}.html"
    label, meaning = STATUS[a["status"]]
    steps_ld = [{"@type": "HowToStep", "position": i, "name": text(t), "text": text(d)}
                for i, (t, d) in enumerate(a["steps"], 1)]
    ld = [
        {"@context": "https://schema.org", "@type": "HowTo", "name": a["title"], "description": a["description"],
         "inLanguage": "en-GB", "dateModified": UPDATED, "step": steps_ld},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Help", "item": SITE + "/help.html"},
            {"@type": "ListItem", "position": 2, "name": role["name"], "item": f"{SITE}/help.html#{a['role']}"},
            {"@type": "ListItem", "position": 3, "name": a["title"], "item": canonical}]},
    ]
    out = [head(a["seo_title"], a["description"], canonical, ld)]
    before = ""
    if a.get("before"):
        before = ('<div class="help-before"><h2>Before you start</h2><ul>'
                  + "".join(f"<li>{b}</li>" for b in a["before"]) + "</ul></div>")
    steps = "".join(
        f'<li><span class="help-step-num" aria-hidden="true">{i}</span><div><h3>{t}</h3><p>{d}</p></div></li>'
        for i, (t, d) in enumerate(a["steps"], 1))
    if a.get("image"):
        src, alt = a["image"]
        cap = a.get("image_caption") or "The new HomecareOS design, shown with demo data."
        figure = (f'<figure class="help-figure"><img src="/images/help/{src}" alt="{esc(alt)}" width="1600" height="900" '
                  f'loading="lazy"><figcaption>{esc(cap)}</figcaption></figure>')
    else:
        figure = (f'<figure class="help-figure help-figure-placeholder" data-screenshot-needed="true">'
                  f'<div class="help-placeholder">{icon("image", 32)}<span>Screenshot coming soon</span></div>'
                  f'<!-- {esc(a.get("image_note", "Screenshot to add (new design only)."))} --></figure>')
    tips = ""
    if a.get("tips"):
        tips = ('<div class="help-tips"><h2>Good to know</h2><ul>'
                + "".join(f"<li>{t}</li>" for t in a["tips"]) + "</ul></div>")
    soon = ""
    if a.get("soon"):
        soon = (f'<div class="help-soon"><h2>{badge("soon")} Coming soon</h2><ul>'
                + "".join(f"<li>{t}</li>" for t in a["soon"]) + "</ul></div>")
    related = "".join(card(BY_SLUG[s]) for s in a["related"])
    reading = ""
    if a.get("reading"):
        reading = ('<div class="help-reading"><h2>Further reading</h2><ul>'
                   + "".join(f'<li><a href="{h}">{esc(t)}</a></li>' for h, t in a["reading"]) + "</ul></div>")
    subject = f"Help article feedback: {a['title']}"
    mailto = "mailto:hello@homecareos.co.uk?subject=" + subject.replace(" ", "%20").replace(":", "%3A").replace("&", "%26")
    out.append(f"""  <main id="main-content" tabindex="-1">
    <header class="page-header help-header help-header-article">
      <div class="container">
        <nav class="breadcrumbs" aria-label="Breadcrumb">
          <a href="/help.html">Help</a>
          <span aria-hidden="true">/</span>
          <a href="/help.html#{a['role']}">{esc(role['name'])}</a>
          <span aria-hidden="true">/</span>
          <span class="current" aria-current="page">{esc(a['title'])}</span>
        </nav>
        <div class="help-article-tags">
          <span class="help-role-tag">{icon(a['role'], 16)} {esc(role['name'])}</span>
          {badge(a['status'])}
        </div>
        <h1>{esc(a['title'])}</h1>
        <p>{a['intro']}</p>
      </div>
    </header>
    <article class="section help-section" aria-label="{esc(a['title'])}">
      <div class="container help-article">
        <p class="help-status-note help-status-{a['status']}">{badge(a['status'])} <span>{esc(meaning)}{" If your screens look different, call us on 01905 674704 and we will walk you through it." if a['status'] == 'rolling' else ""}</span></p>
        {before}
        <h2 class="help-steps-heading">Steps</h2>
        <ol class="help-steps">{steps}</ol>
        {figure}
        {tips}
        {soon}
        {reading}
        <section class="help-feedback" aria-labelledby="feedback-heading" data-article="{a['slug']}">
          <h2 id="feedback-heading">Was this helpful?</h2>
          <div class="help-feedback-buttons">
            <button type="button" class="btn btn-outline btn-sm" data-helpful="yes">Yes</button>
            <button type="button" class="btn btn-outline btn-sm" data-helpful="no">No</button>
          </div>
          <p class="help-feedback-thanks" hidden data-for="yes">Thank you. Glad it helped.</p>
          <p class="help-feedback-thanks" hidden data-for="no">Sorry about that. <a href="{mailto}">Tell us what was missing</a> and we will improve this guide.</p>
        </section>
        <section class="help-related" aria-labelledby="related-heading">
          <h2 id="related-heading">Related articles</h2>
          <div class="help-grid help-grid-related">
            {related}
          </div>
        </section>
        {STILL_STUCK}
      </div>
    </article>
  </main>
""")
    out.append(FOOT)
    return "".join(out)


def main():
    os.makedirs(os.path.join(ROOT, "help"), exist_ok=True)
    files = ["help.html"]
    open(os.path.join(ROOT, "help.html"), "w", encoding="utf-8").write(landing())
    for a in ARTICLES:
        for s in a["related"]:
            assert s in BY_SLUG, f"{a['slug']}: unknown related {s}"
        assert a["status"] in STATUS
        assert "CareOS" not in json.dumps(a).replace("HomecareOS", "").replace("homecareOS", ""), a["slug"]
        rel = f"help/{a['slug']}.html"
        open(os.path.join(ROOT, rel), "w", encoding="utf-8").write(article(a))
        files.append(rel)
    subprocess.run([sys.executable, os.path.join(ROOT, "build.py")] + files, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
