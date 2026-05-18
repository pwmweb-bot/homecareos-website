# IndexNow setup — homecareos.co.uk

**What it does**: Instantly notifies Microsoft Bing, Yandex, Naver, Seznam.cz, and Yep
when content on `homecareos.co.uk` changes — instead of waiting days/weeks for them
to re-crawl on their own schedule. Indexing in those engines drops from ~1–3 weeks
to <1 hour.

**What it doesn't do**: Notify Google. Google doesn't participate in IndexNow. We
use Google's Indexing API separately via the `seo-google` skill.

---

## Key file

| | |
|---|---|
| Key | `988cc8d9-63ce-4fdb-8474-18c9385d993d` |
| Key file path | `website/988cc8d9-63ce-4fdb-8474-18c9385d993d.txt` |
| Live URL (post-deploy) | `https://www.homecareos.co.uk/988cc8d9-63ce-4fdb-8474-18c9385d993d.txt` |
| File contents | Just the key string, no quotes, no newline (36 bytes) |

**Do not delete the key file from `website/`** — IndexNow validates ownership by
fetching that URL. If it returns 404, submissions fail with HTTP 403.

If the key is ever leaked or compromised, rotate it:
1. Generate a new UUID
2. Replace the constant `KEY=` in `submit-indexnow.sh`
3. Rename the file in `website/`
4. Deploy

---

## Workflow

### When publishing a new blog post or major page

```bash
cd website
./scripts/submit-indexnow.sh \
  https://www.homecareos.co.uk/blog/your-new-post.html
```

Multiple URLs in one call (up to 10,000):

```bash
./scripts/submit-indexnow.sh \
  https://www.homecareos.co.uk/pricing.html \
  https://www.homecareos.co.uk/compare-birdie.html \
  https://www.homecareos.co.uk/blog/some-new-post.html
```

### When major site-wide changes ship (e.g. pricing model change, all-pages copy update)

```bash
./scripts/submit-indexnow.sh --all
```

This reads every `<loc>` from `sitemap.xml` and submits the lot. **Use sparingly** —
once after initial setup, and only after meaningful site-wide changes. Submitting
the full sitemap repeatedly will trigger HTTP 429 (rate-limit).

### Dry-run (no HTTP call, just shows the payload)

```bash
./scripts/submit-indexnow.sh --dry-run https://www.homecareos.co.uk/pricing.html
./scripts/submit-indexnow.sh --dry-run --all
```

---

## Response codes

The script translates IndexNow's HTTP codes into colour-coded output:

| Code | Meaning | Action |
|---|---|---|
| **200** | URLs submitted successfully | None |
| **202** | Received; key validation pending | None — IndexNow will verify the key file on its own schedule. Common on first submission |
| **400** | Invalid format | Check the script — probably a code change broke the JSON payload |
| **403** | Key file not reachable | Verify the key file is live at the URL above; check it's deployed and returns 200 |
| **422** | URLs don't belong to host | Make sure every URL starts with `https://www.homecareos.co.uk/` |
| **429** | Too many requests | Wait at least an hour before retrying. Don't submit the same URL repeatedly |

---

## Verification

After deploying the key file to production, confirm it's reachable:

```bash
curl -I "https://www.homecareos.co.uk/988cc8d9-63ce-4fdb-8474-18c9385d993d.txt"
# Expect: HTTP/2 200 ... Content-Type: text/plain
```

To verify the key file contents:

```bash
curl "https://www.homecareos.co.uk/988cc8d9-63ce-4fdb-8474-18c9385d993d.txt"
# Expect: 988cc8d9-63ce-4fdb-8474-18c9385d993d
```

Once the key file is reachable, IndexNow will start validating subsequent
submissions. Bing typically begins crawling submitted URLs within an hour.

To verify URLs are being indexed faster:
- Bing Webmaster Tools → URL Inspection
- ChatGPT search ("homecareOS pricing" should surface the latest copy faster)

---

## Architecture

The script in this folder is **fully stateless**. There's no database, no log, no
queue. Each invocation does one POST to `https://api.indexnow.org/indexnow`, which
is IndexNow's unified endpoint — it fans out the submission to all five
participating search engines in one call.

No deploy automation is wired up. If/when you want submissions to fire automatically
on website deploys, add the following to your 20i deploy hook (or whatever
post-deploy step you run):

```bash
# Only submit changed files. Adjust `git diff` range to match your deploy flow.
changed_urls=$(
  git diff --name-only HEAD~1 HEAD -- 'website/*.html' 'website/blog/*.html' \
    | sed 's|^website/||' \
    | sed 's|^|https://www.homecareos.co.uk/|'
)
[ -n "$changed_urls" ] && ./scripts/submit-indexnow.sh $changed_urls
```

For now this stays manual — Phil decides per deploy which URLs are worth pinging.

---

## History

- **10 May 2026** — Initial setup. Key generated, file saved to website root,
  script written, all 54 sitemap URLs bulk-submitted (HTTP 202). Awaiting next
  website deploy for the key file to become reachable; IndexNow will validate
  the key on its next pass and start propagating the queued URLs.
