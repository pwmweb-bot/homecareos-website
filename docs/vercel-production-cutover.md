# HomecareOS website — Vercel production cutover

This file is not deployed. It is the checklist for pointing the live domain at Vercel later. Do not run it until Philip says to put the site live.

## Noindex (already scoped — do not add a global one)

`vercel.json` sets `X-Robots-Tag: noindex, nofollow` only when the request host matches `*.vercel.app` (the preview alias and git preview URLs). A production custom domain such as `www.homecareos.co.uk` will **not** receive that header.

- Leave the host-conditioned rule in place so previews stay noindex.
- Do **not** replace it with a header on `/(.*)` that has no `has` host condition.
- Production HTML already has `<meta name="robots" content="index, follow">`.

## Before DNS changes

1. Confirm this branch has been approved and is ready to go live (or has been merged, if that is the agreed path).
2. Add the production domains to the existing HomecareOS website Vercel project — do not create a new project. Typical records:
   - `www.homecareos.co.uk` — CNAME to `cname.vercel-dns.com` (or the target Vercel shows).
   - Apex `homecareos.co.uk` — ALIAS/ANAME/CNAME flattening to Vercel, or a 301 at the DNS provider to `www`.
3. Leave all mail records (MX, SPF, DKIM, DMARC) and the existing `app` / `heroes` records untouched.
4. Confirm redirects, extensionless URLs, blocked tooling paths, cache headers, and the CSP still hold on a production-domain preview or after a host assignment, before cutting public DNS.
5. Do not use `build.py publish` as part of the cutover; it recreates the withdrawn `blog/best-domiciliary-care-software-uk.html`.
