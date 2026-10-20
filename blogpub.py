"""Markdown blog publisher and sitemap writer. Used by build.py.

Source posts live in content/blog/*.md (not served; .htaccess returns 404).
`python3 build.py publish` writes blog/<slug>.html, refreshes the cards on
blog.html, and rebuilds sitemap.xml.
"""
import datetime
import glob
import html
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://www.homecareos.co.uk"
CONTENT_DIR = os.path.join(ROOT, "content", "blog")

def _partial(name):
    with open(os.path.join(ROOT, "partials", name), encoding="utf-8") as handle:
        return handle.read().strip("\n")


GTAG = _partial("gtag.html")

NAV_JS = """  <script>
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
"""


def parse_front_matter(text):
    if not text.startswith("---\n"):
        raise SystemExit("post is missing opening --- front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SystemExit("post front matter is not closed with ---")
    raw = text[4:end]
    body = text[end + 5:].lstrip("\n")
    data = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith(" "):
            raise SystemExit("unexpected indent in front matter: " + line)
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "":
            items = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                if not lines[i].strip():
                    i += 1
                    continue
                if not lines[i].startswith("  - "):
                    break
                item = {}
                first = lines[i][4:]
                k, _, v = first.partition(":")
                item[k.strip()] = _unquote(v.strip())
                i += 1
                while i < len(lines) and lines[i].startswith("    "):
                    k, _, v = lines[i].strip().partition(":")
                    item[k.strip()] = _unquote(v.strip())
                    i += 1
                items.append(item)
            data[key] = items
            continue
        data[key] = _unquote(val)
        i += 1
    return data, body


def _unquote(val):
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        return val[1:-1]
    return val


def require(meta, key):
    if not str(meta.get(key, "")).strip():
        raise SystemExit(f"front matter missing {key}")
    return str(meta[key]).strip()


def validate_meta(meta):
    title = require(meta, "title")
    description = require(meta, "description")
    slug = require(meta, "slug")
    date = require(meta, "date")
    keywords = require(meta, "keywords")
    if len(title) > 60:
        raise SystemExit(f"title is {len(title)} chars (max 60): {title}")
    if len(description) > 160:
        raise SystemExit(f"description is {len(description)} chars (max 160): {description}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise SystemExit(f"slug must be lowercase hyphenated words: {slug}")
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise SystemExit(f"date must be YYYY-MM-DD: {date}")
    meta["title"] = title
    meta["description"] = description
    meta["slug"] = slug
    meta["date"] = date
    meta["keywords"] = keywords
    meta.setdefault("category", "Guide")
    meta.setdefault("image", "/images/photos/team-reviewing-analytics.webp")
    meta.setdefault("image_alt", title)
    meta.setdefault("standfirst", description)
    meta.setdefault("breadcrumb", title)
    meta.setdefault("updated", date)
    return meta


def esc(text):
    return html.escape(text, quote=False)


def esc_attr(text):
    return html.escape(text, quote=True)


def format_inline(text):
    """Escape text, then apply **bold**, *em* and [label](url)."""
    out = []
    pos = 0
    pattern = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
    for match in pattern.finditer(text):
        out.append(_emphasis(esc(text[pos:match.start()])))
        label = _emphasis(esc(match.group(1)))
        href = esc_attr(match.group(2))
        out.append(f'<a href="{href}">{label}</a>')
        pos = match.end()
    out.append(_emphasis(esc(text[pos:])))
    return "".join(out)


def _emphasis(text):
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def heading_id(text, used):
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"
    slug = base
    n = 2
    while slug in used:
        slug = f"{base}-{n}"
        n += 1
    used.add(slug)
    return slug


def md_to_html(markdown):
    lines = markdown.replace("\r\n", "\n").split("\n")
    html_parts = []
    used_ids = set()
    i = 0

    def flush_paragraph(buf):
        if buf:
            html_parts.append("<p>" + format_inline(" ".join(buf)) + "</p>")

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("## "):
            title = stripped[3:].strip()
            html_parts.append(f'<h2 id="{heading_id(title, used_ids)}">{format_inline(title)}</h2>')
            i += 1
            continue
        if stripped.startswith("### "):
            title = stripped[4:].strip()
            html_parts.append(f'<h3 id="{heading_id(title, used_ids)}">{format_inline(title)}</h3>')
            i += 1
            continue
        if stripped.startswith("> "):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            inner = "</p><p style=\"margin:12px 0 0\">".join(format_inline(p) for p in " ".join(quote).split("\n\n") if p) if False else format_inline(" ".join(quote))
            html_parts.append(
                '<div style="background:var(--gray-100);padding:24px;border-radius:12px;border-left:4px solid var(--primary);margin:24px 0">'
                f'<p style="margin:0">{inner}</p></div>'
            )
            continue
        if stripped.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(format_inline(lines[i].strip()[2:].strip()))
                i += 1
            html_parts.append("<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>")
            continue
        if re.match(r"\d+\. ", stripped):
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i].strip()):
                items.append(format_inline(re.sub(r"^\d+\. ", "", lines[i].strip())))
                i += 1
            html_parts.append("<ol>" + "".join(f"<li>{item}</li>" for item in items) + "</ol>")
            continue
        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            html_parts.append(_table(rows))
            continue
        buf = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not _block_start(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        flush_paragraph(buf)
    return "\n".join(html_parts)


def _block_start(line):
    s = line.strip()
    return s.startswith(("## ", "### ", "> ", "- ", "|")) or bool(re.match(r"\d+\. ", s))


def _table(rows):
    parsed = []
    for row in rows:
        if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", row):
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        parsed.append(cells)
    if not parsed:
        return ""
    head, body = parsed[0], parsed[1:]
    thead = "<thead><tr>" + "".join(f"<th>{format_inline(c)}</th>" for c in head) + "</tr></thead>"
    tbody = "<tbody>" + "".join(
        "<tr>" + "".join(f"<td>{format_inline(c)}</td>" for c in row) + "</tr>" for row in body
    ) + "</tbody>"
    return f'<table class="compare-table" style="margin:24px 0">{thead}{tbody}</table>'


def _json(value):
    return json.dumps(value, ensure_ascii=False)


def _date_label(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


def _word_count(markdown):
    text = re.sub(r"[#>*\[\]\(\)_|]", " ", markdown)
    return len(re.findall(r"[A-Za-z0-9'’£-]+", text))


def render_post(meta, body_html, markdown):
    title = meta["title"]
    description = meta["description"]
    slug = meta["slug"]
    url = f"{SITE}/blog/{slug}.html"
    image = meta["image"] if meta["image"].startswith("/") else "/" + meta["image"]
    image_url = SITE + image
    published = meta["date"] + "T09:00:00+01:00"
    modified = meta["updated"] + "T09:00:00+01:00"
    if "T" in meta["updated"]:
        modified = meta["updated"]
    words = _word_count(markdown)
    minutes = max(1, round(words / 220))
    keywords = [k.strip() for k in meta["keywords"].split(",") if k.strip()]
    tags = "\n".join(
        f'  <meta property="article:tag" content="{esc_attr(tag)}">' for tag in keywords[:6]
    )
    faqs = meta.get("faqs") or []
    faq_html = ""
    faq_ld = ""
    if faqs:
        blocks = []
        entities = []
        for item in faqs:
            q = item.get("q", "").strip()
            a = item.get("a", "").strip()
            if not q or not a:
                continue
            blocks.append(
                '<details style="margin:16px 0;padding:16px 20px;background:var(--gray-100);border-radius:8px">'
                f'<summary style="font-weight:600;cursor:pointer">{esc(q)}</summary>'
                f'<p style="margin-top:12px">{esc(a)}</p></details>'
            )
            entities.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            })
        faq_html = (
            '<section class="section-sm" style="margin-top:64px;padding-top:48px;border-top:1px solid var(--gray-200)" aria-labelledby="faq-heading">'
            '<h2 id="faq-heading">Frequently asked questions</h2>'
            + "\n".join(blocks) + "</section>"
        )
        faq_ld = (
            '<script type="application/ld+json">\n'
            + _json({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": entities})
            + "\n  </script>"
        )
    related = list(meta.get("related") or [])
    if meta.get("feature_href"):
        related.append({
            "title": meta.get("feature_title") or "Related feature",
            "href": meta["feature_href"],
            "category": meta.get("feature_category") or "Feature",
            "summary": meta.get("feature_summary") or "",
        })
    related_html = ""
    if related:
        cards = []
        for item in related:
            href = item.get("href", "")
            cards.append(
                '<article class="blog-card"><div class="blog-card-body">'
                f'<div class="blog-meta"><span class="blog-category">{esc(item.get("category") or "Guide")}</span></div>'
                f'<h3><a href="{esc_attr(href)}">{esc(item.get("title") or "")}</a></h3>'
                f'<p>{esc(item.get("summary") or "")}</p>'
                f'<a href="{esc_attr(href)}" class="read-more">Read more &rarr;</a>'
                "</div></article>"
            )
        related_html = (
            '<section class="section-sm" style="margin-top:64px" aria-labelledby="related-heading">'
            '<h2 id="related-heading">Continue reading</h2>'
            '<div class="blog-grid" style="grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;margin-top:24px">'
            + "".join(cards) + "</div></section>"
        )
    cta_title = meta.get("cta_title") or "See it on a rota like yours"
    cta_text = meta.get("cta_text") or "Book a short demo, or start free for up to 5 carers. No card needed."
    cta_href = meta.get("cta_secondary_href") or "/pricing.html"
    cta_label = meta.get("cta_secondary") or "See pricing"
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "image": {"@type": "ImageObject", "url": image_url, "width": 1200, "height": 630},
        "datePublished": published,
        "dateModified": modified,
        "author": {
            "@type": "Person",
            "name": "Philip Martin",
            "jobTitle": "Founder, homecareOS",
            "url": f"{SITE}/team.html",
            "worksFor": {"@type": "Organization", "name": "PsycheMeta Ltd", "url": SITE},
        },
        "publisher": {
            "@type": "Organization",
            "name": "homecareOS",
            "url": SITE,
            "logo": {
                "@type": "ImageObject",
                "url": f"{SITE}/images/brand/mark-logo.png",
                "width": 600,
                "height": 600,
            },
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "articleSection": meta["category"],
        "keywords": meta["keywords"],
        "inLanguage": "en-GB",
        "wordCount": words,
    }
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog.html"},
            {"@type": "ListItem", "position": 3, "name": meta["breadcrumb"], "item": url},
        ],
    }
    caption = meta.get("image_caption") or meta["image_alt"]
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
  <meta name="description" content="{esc_attr(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{url}">
  <meta name="author" content="Philip Martin">
  <meta property="og:title" content="{esc_attr(title)}">
  <meta property="og:description" content="{esc_attr(description)}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{image_url}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{esc_attr(meta["image_alt"])}">
  <meta property="og:locale" content="en_GB">
  <meta property="og:site_name" content="homecareOS">
  <meta property="article:published_time" content="{published}">
  <meta property="article:modified_time" content="{modified}">
  <meta property="article:author" content="Philip Martin">
  <meta property="article:section" content="{esc_attr(meta["category"])}">
{tags}
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc_attr(title)}">
  <meta name="twitter:description" content="{esc_attr(description)}">
  <meta name="twitter:image" content="{image_url}">
  <link rel="preload" href="/fonts/dmsans-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/fonts/dmsans.css?v=20260521">
  <link rel="stylesheet" href="/styles.css?v=20260909insp">
{GTAG}
  <script type="application/ld+json">
  {_json(article_ld)}
  </script>
  <script type="application/ld+json">
  {_json(crumbs)}
  </script>
  {faq_ld}
  <script src="/js/book-demo.js?v=20261020" defer></script>
  <script src="/js/reveal.js?v=20260507" defer></script>
</head>
<body>
  <a href="#main-content" class="skip-link" id="skip-link">Skip to main content</a>
  <nav class="nav" role="navigation" aria-label="Main navigation"></nav>
  <main id="main-content" tabindex="-1">
    <header class="page-header">
      <div class="container">
        <nav class="breadcrumbs" aria-label="Breadcrumb">
          <a href="/index.html">Home</a>
          <span aria-hidden="true">/</span>
          <a href="/blog.html">Blog</a>
          <span aria-hidden="true">/</span>
          <span class="current" aria-current="page">{esc(meta["breadcrumb"])}</span>
        </nav>
        <span class="label">{esc(meta["category"])} &middot; {minutes} min read</span>
        <h1>{esc(title)}</h1>
        <p>{esc(meta["standfirst"])}</p>
        <div class="post-meta" style="display:flex;align-items:center;gap:16px;margin-top:24px;color:var(--gray-600);font-size:0.95rem">
          <span><strong style="color:var(--text)">By Philip Martin</strong> &middot; Founder, homecareOS</span>
          <span aria-hidden="true">&middot;</span>
          <time datetime="{esc_attr(meta["date"])}">Published {_date_label(meta["date"])}</time>
        </div>
      </div>
    </header>
    <article class="section" aria-label="{esc_attr(title)}">
      <div class="container" style="max-width:760px">
        <figure style="margin:0 0 40px">
          <img src="{esc_attr(image)}" alt="{esc_attr(meta["image_alt"])}" width="1200" height="630" loading="eager" style="width:100%;height:auto;border-radius:12px">
          <figcaption style="font-size:0.9rem;color:var(--gray-600);margin-top:8px;text-align:center">{esc(caption)}</figcaption>
        </figure>
        <div class="post-body">
{body_html}
        </div>
        {faq_html}
        <aside class="section-sm" style="margin-top:64px;padding:32px;background:var(--gray-100);border-radius:12px">
          <div style="display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap">
            <div style="flex:0 0 auto"><img src="/images/brand/mark.svg" alt="" width="64" height="64" style="background:var(--primary);padding:12px;border-radius:50%"></div>
            <div style="flex:1;min-width:240px">
              <h3 style="margin:0 0 8px;font-size:1.1rem">About the author</h3>
              <p style="margin:0 0 8px"><strong>Philip Martin</strong> is the founder of homecareOS and managing director of PsycheMeta Ltd. He works with UK home care agencies on the software they use to run the service.</p>
              <p style="margin:0;font-size:0.9rem"><a href="/about.html">More about homecareOS</a> &middot; <a href="/team.html">Team</a> &middot; <a href="https://www.linkedin.com/company/homecareos" rel="noopener">LinkedIn</a></p>
            </div>
          </div>
        </aside>
        {related_html}
        <section class="cta-section" style="margin-top:64px;border-radius:12px" aria-label="Call to action">
          <div class="container">
            <h2>{esc(cta_title)}</h2>
            <p>{esc(cta_text)}</p>
            <div class="cta-actions">
              <a href="/booking.html" class="btn btn-primary btn-lg">Book a 15-minute demo</a>
              <a href="/start.html" class="btn btn-ghost btn-lg">Get started for free</a>
            </div>
            <p style="margin:16px 0 0"><a href="{esc_attr(cta_href)}" style="color:inherit;text-decoration:underline">{esc(cta_label)}</a></p>
          </div>
        </section>
      </div>
    </article>
  </main>
  <footer class="footer" role="contentinfo"></footer>
{NAV_JS}
</body>
</html>
"""


def card_html(meta):
    image = meta["image"].lstrip("/")
    return f"""          <!-- post:{meta["slug"]} -->
          <article class="blog-card" data-reveal data-reveal-delay="0">
            <div class="blog-card-image">
              <img src="{esc_attr(image)}" alt="{esc_attr(meta["image_alt"])}" width="640" height="360" loading="lazy">
            </div>
            <div class="blog-card-body">
              <div class="blog-meta">
                <span class="blog-category">{esc(meta["category"])}</span>
                <time datetime="{esc_attr(meta["date"])}">{_date_label(meta["date"])}</time>
              </div>
              <h3><a href="blog/{meta["slug"]}.html">{esc(meta["title"])}</a></h3>
              <p>{esc(meta["description"])}</p>
              <a href="blog/{meta["slug"]}.html" class="read-more">Read More &rarr;</a>
            </div>
          </article>
          <!-- /post:{meta["slug"]} -->
"""


def _markdown_paths(paths):
    if paths:
        return [p if os.path.isabs(p) else os.path.join(ROOT, p) for p in paths]
    found = sorted(glob.glob(os.path.join(CONTENT_DIR, "*.md")))
    return [p for p in found if not os.path.basename(p).startswith("_")]


def publish_command(paths):
    from build import build, validate
    metas = []
    for path in _markdown_paths(paths):
        print(f"publish {os.path.relpath(path, ROOT)}")
        text = open(path, encoding="utf-8").read()
        meta, body = parse_front_matter(text)
        meta = validate_meta(meta)
        if os.path.basename(path).startswith("_"):
            raise SystemExit("refusing to publish a template file")
        rendered = render_post(meta, md_to_html(body), body)
        dest = os.path.join(ROOT, "blog", meta["slug"] + ".html")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8").write(rendered)
        rel = os.path.relpath(dest, ROOT)
        build([rel])
        bad = validate([rel])
        if bad:
            print(f"WARNING: tag balance in {rel}")
            for _f, errs in bad:
                for msg, (line, col) in errs[:8]:
                    print(f"  line {line} col {col}: {msg}")
            sys.exit(1)
        metas.append(meta)
    if metas:
        _refresh_blog_index(metas)


def _refresh_blog_index(metas):
    """Insert or replace the managed cards for these posts. Newest date first."""
    blog = os.path.join(ROOT, "blog.html")
    page = open(blog, encoding="utf-8").read()
    for meta in metas:
        page = re.sub(
            r"[ \t]*<!-- post:" + re.escape(meta["slug"]) + r" -->.*?<!-- /post:" + re.escape(meta["slug"]) + r" -->\n?",
            "",
            page,
            count=1,
            flags=re.S,
        )
    metas = sorted(metas, key=lambda m: m["slug"])
    metas = sorted(metas, key=lambda m: m["date"], reverse=True)
    block = "\n".join(card_html(m) for m in metas) + "\n"
    needle = '<div class="blog-grid">'
    idx = page.find(needle)
    if idx < 0:
        raise SystemExit("blog.html has no blog-grid")
    insert_at = idx + len(needle)
    # keep the newline that already follows the opening div
    if page[insert_at:insert_at + 1] == "\n":
        page = page[:insert_at + 1] + block + page[insert_at + 1:]
    else:
        page = page[:insert_at] + "\n" + block + page[insert_at:]
    open(blog, "w", encoding="utf-8").write(page)
    print(f"blog.html cards: {len(metas)}")


def _public_pages():
    pages = []
    for folder, names in (("", glob.glob(os.path.join(ROOT, "*.html"))),
                          ("blog", glob.glob(os.path.join(ROOT, "blog", "*.html")))):
        for path in names:
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if rel == "blog/index.html":
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            robots = re.search(r'<meta\s+[^>]*name="robots"[^>]*>', text, re.I)
            if robots and "noindex" in robots.group(0).lower():
                continue
            pages.append(rel)
    def key(rel):
        if rel == "index.html":
            return (0, "")
        if rel == "blog.html":
            return (2, "")
        if rel.startswith("blog/"):
            return (3, rel)
        return (1, rel)
    return sorted(set(pages), key=key)


def _lastmod(rel):
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", rel],
        cwd=ROOT, capture_output=True, text=True,
    )
    if status.stdout.strip():
        return datetime.date.today().isoformat()
    log = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", rel],
        cwd=ROOT, capture_output=True, text=True,
    )
    if log.stdout.strip():
        return log.stdout.strip()
    mtime = os.path.getmtime(os.path.join(ROOT, rel))
    return datetime.date.fromtimestamp(mtime).isoformat()


def _loc(rel):
    if rel == "index.html":
        return SITE + "/"
    return SITE + "/" + rel


def write_sitemap():
    pages = _public_pages()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <!-- Generated by build.py from each page's git date. Do not edit by hand. -->",
    ]
    for rel in pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(_loc(rel))}</loc>")
        lines.append(f"    <lastmod>{_lastmod(rel)}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")
    dest = os.path.join(ROOT, "sitemap.xml")
    open(dest, "w", encoding="utf-8").write("\n".join(lines))
    print(f"sitemap.xml: {len(pages)} urls")
