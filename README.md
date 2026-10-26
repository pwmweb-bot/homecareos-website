# homecareOS marketing site

Static HTML for [homecareos.co.uk](https://www.homecareos.co.uk). The agency app at `app.homecareos.co.uk` is a separate product and is not built from this repository.

Copy is British English.

## Build

`python3 build.py` does two things:

1. Replaces the first `<nav class="nav">` and `<footer class="footer">` in each HTML page with `partials/header.html` and `partials/footer.html`, injects `partials/gtag.html` (Consent Mode defaults, GA4 and Google Ads), and cache-busts `styles.css`.
2. Rewrites `sitemap.xml`.

It does not upload or deploy anything. Publishing to the live site is a separate manual step on the host. Do not run IndexNow until that upload has happened (`scripts/README-indexnow.md`).

```bash
python3 build.py                  # every *.html and blog/*.html, then sitemap
python3 build.py pricing.html     # inject one page, then sitemap
python3 build.py sitemap          # rewrite sitemap.xml only
```

`lastmod` is the file's last git commit date (`YYYY-MM-DD`). A page that is untracked or has uncommitted changes uses today's date. Pages with `<meta name="robots" content="noindex">` are left out, as is `blog/index.html` (a fallback for the directory). `testimonials.html` stays out until it has real testimonials and the noindex tag is removed.

## Blog posts

Drafts live in `content/blog/` as Markdown with front matter. Copy `content/blog/_template.md`. Files whose names start with `_` are templates and are not published. The `content/` directory is not served: `.htaccess` returns 404 for it.

Required front matter:

| Field | Rule |
| --- | --- |
| `title` | 60 characters or fewer. Becomes the `<title>`, `og:title`, `twitter:title`, H1 and Article `headline`. |
| `description` | 160 characters or fewer. Becomes the meta description, Open Graph and Twitter descriptions, and the Article description. |
| `slug` | Lowercase hyphenated words. The URL is `/blog/<slug>.html`. |
| `date` | `YYYY-MM-DD`. |
| `keywords` | Comma-separated. Written to the keywords meta tag. |

Optional: `category`, `standfirst`, `breadcrumb`, `image`, `image_alt`, `image_caption`, `updated`, `related`, `feature_title`, `feature_href`, `feature_category`, `feature_summary`, `faqs`, `cta_title`, `cta_text`, `cta_secondary`, `cta_secondary_href`.

```bash
python3 build.py publish
python3 build.py publish content/blog/your-post.md
```

Publish renders `blog/<slug>.html` in the same shape as the existing posts (canonical URL, Open Graph, Article and Breadcrumb JSON-LD, shared nav and footer), inserts a card at the top of `blog.html`, and regenerates the sitemap. Commit both the Markdown and the generated HTML.

Do not invent statistics, quotations, customer names or prices. If a figure is not on a public page you can link, leave it out.

Check lengths and the links in newly published posts:

```bash
python3 scripts/check_seo.py
```

## Help centre

The help centre is `/help.html`, with one page per article in `help/`. The articles live in `content/help/articles.py`; `scripts/build_help.py` renders them (landing page, articles, header and footer, sitemap). Edit the data, never the generated HTML:

```bash
python3 scripts/build_help.py
python3 scripts/check_seo.py
```

Each article has a status badge: **Live** (every agency has it), **Rolling out** (it works in the new HomecareOS design, which is being switched on agency by agency) or **Coming soon** (planned; never write steps for it). Check every step against the app on `main` before publishing. Steps describe the new design screens, not the old office pages. Screenshots go in `images/help/` and must be the new design on demo data; an article without one shows a marked placeholder (`data-screenshot-needed`). `.htaccess` sends `/help/` to `/help.html`, as it does for `/blog/`.

## `/blog/`

`blog/` is a real directory of post files, so Apache will not apply the pretty-URL rewrite and, with indexes off, `/blog/` returns 403. `.htaccess` 301-redirects `/blog/` and `/blog/index.html` to `/blog.html`. `blog/index.html` is a noindex fallback with the same destination, for a host that ignores the rewrite.
