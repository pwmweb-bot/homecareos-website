import hashlib, json, datetime, re, os

pages = [
    'features-scheduling.html',
    'features-ai-rota.html',
    'features-staff-management.html',
    'features-compliance.html',
    'features-care-records.html',
]

base_url = 'https://www.homecareos.co.uk/'
base_dir = '/Users/philipmartin/Documents/Claude/Projects/home care/website/'
out_dir  = base_dir + 'audits/seo-drift/baselines/'
os.makedirs(out_dir, exist_ok=True)

def extract(html, page):
    result = {}

    # title
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    result['title'] = m.group(1).strip() if m else ''

    # meta description
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta\s+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']', html, re.IGNORECASE)
    result['meta_description'] = m.group(1).strip() if m else ''

    # canonical
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']*)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<link[^>]+href=["\']([^"\']*)["\'][^>]+rel=["\']canonical["\']', html, re.IGNORECASE)
    result['canonical'] = m.group(1).strip() if m else ''

    # robots meta
    m = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']*)["\']', html, re.IGNORECASE)
    result['robots_meta'] = m.group(1).strip() if m else 'index,follow (default — no robots meta tag present)'

    # H1
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    result['h1'] = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''

    # H2s
    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL | re.IGNORECASE)
    result['h2s'] = [re.sub(r'<[^>]+>', '', h).strip() for h in h2s]

    # Schema types
    schemas = re.findall(r'"@type"\s*:\s*"([^"]+)"', html)
    result['schema_types'] = list(set(schemas))

    # OG tags
    og = {}
    for m2 in re.finditer(r'<meta\s+property=["\']([^"\']*)["\'][^>]+content=["\']([^"\']*)["\']', html, re.IGNORECASE):
        if m2.group(1).startswith('og:'):
            og[m2.group(1)] = m2.group(2)
    result['og_tags'] = og

    # Content hash (body text only, tags stripped)
    body_m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    body_text = re.sub(r'<[^>]+>', ' ', body_m.group(1)) if body_m else html
    body_text = re.sub(r'\s+', ' ', body_text).strip()
    result['content_hash'] = hashlib.sha256(body_text.encode()).hexdigest()

    # Domiciliary vs residential keyword hit counts
    dom_terms = ['domiciliary', 'home care', 'visiting carer', 'community care',
                 'care at home', 'live-in', 'field carer', 'in-home care']
    res_terms = ['care home', 'residential care', 'nursing home', 'care home rota',
                 'rota software for care homes', 'care home software', 'residential home']
    body_lower = body_text.lower()
    result['domiciliary_keyword_hits'] = {t: body_lower.count(t) for t in dom_terms if body_lower.count(t) > 0}
    result['residential_keyword_hits'] = {t: body_lower.count(t) for t in res_terms if body_lower.count(t) > 0}

    result['url'] = base_url + page
    result['captured_at'] = '2026-05-10T00:00:00Z'
    result['baseline_note'] = (
        'Post content/schema change designed to repel residential care home queries '
        'and reinforce domiciliary/home care positioning. Compare in ~4 weeks.'
    )
    return result

for page in pages:
    path = base_dir + page
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    data = extract(html, page)
    slug = page.replace('.html', '')
    out_path = out_dir + slug + '_baseline_20260510.json'
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=2)
    print('SAVED:', out_path)
    print('  title           :', data['title'])
    print('  h1              :', data['h1'])
    print('  meta_desc       :', data['meta_description'][:100])
    print('  canonical       :', data['canonical'])
    print('  robots          :', data['robots_meta'])
    print('  schema_types    :', data['schema_types'])
    print('  dom_kw_hits     :', data['domiciliary_keyword_hits'])
    print('  res_kw_hits     :', data['residential_keyword_hits'])
    print()

print('All 5 baselines captured.')
