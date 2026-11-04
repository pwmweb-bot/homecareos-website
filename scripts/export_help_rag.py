#!/usr/bin/env python3
"""Export the help centre to JSONL for a chat assistant and the in-app help.

Reads content/help/articles.py (the one source for the website help, the
in-app ? help and any assistant) and writes help/help-index.jsonl: one line
per chunk, step-level, plain text (HTML stripped), so a retriever can quote a
single step and link to the full guide.

  python3 scripts/export_help_rag.py            # write help/help-index.jsonl
  python3 scripts/export_help_rag.py --check    # fail if the file is stale

Every chunk carries:
  id            "<slug>#step-<n>", "<slug>#before-<n>", "<slug>#tip-<n>" or "<slug>#soon-<n>"
  kind          step | before | tip | soon ("soon" is planned, not built:
                an assistant must say so and never give steps for it)
  slug, title, role, status, summary, url
  step_n        1-based step number for kind "step", else null
  step_title    the step's short title (steps only), else null
  step_text     the chunk's text
  related       slugs of related articles
  screen_keys   in-app screen keys the article explains (articles.py "screens")

Run it after editing articles.py, and commit the output with the article.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "content", "help"))
from articles import ARTICLES, ROLES  # noqa: E402

SITE = "https://www.homecareos.co.uk"
OUT = os.path.join(ROOT, "help", "help-index.jsonl")


def text(s):
    """HTML fragment to one line of plain text."""
    s = re.sub(r"<[^>]+>", "", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def chunks():
    for a in ARTICLES:
        assert a["role"] in ROLES, a["slug"]
        base = {
            "slug": a["slug"],
            "title": text(a["title"]),
            "role": a["role"],
            "status": a["status"],
            "summary": text(a["summary"]),
            "url": f"{SITE}/help/{a['slug']}.html",
            "related": list(a.get("related", [])),
            "screen_keys": list(a.get("screens", [])),
        }
        for n, (t, d) in enumerate(a["steps"], 1):
            yield {"id": f"{a['slug']}#step-{n}", "kind": "step", **base,
                   "step_n": n, "step_title": text(t), "step_text": f"{text(t)}. {text(d)}".replace("?.", "?")}
        for kind, key in (("before", "before"), ("tip", "tips"), ("soon", "soon")):
            for n, t in enumerate(a.get(key) or [], 1):
                yield {"id": f"{a['slug']}#{kind}-{n}", "kind": kind, **base,
                       "step_n": None, "step_title": None, "step_text": text(t)}


def render():
    return "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks())


def main():
    out = render()
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if cur != out:
            sys.exit("help/help-index.jsonl is stale: run python3 scripts/export_help_rag.py")
        print("help/help-index.jsonl is up to date")
        return
    open(OUT, "w", encoding="utf-8").write(out)
    print(f"help/help-index.jsonl: {out.count(chr(10))} chunks from {len(ARTICLES)} articles")


if __name__ == "__main__":
    main()
