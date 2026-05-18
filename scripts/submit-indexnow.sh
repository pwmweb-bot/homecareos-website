#!/usr/bin/env bash
#
# submit-indexnow.sh
# Push URL changes from homecareos.co.uk to participating IndexNow search engines
# (Microsoft Bing, Yandex, Naver, Seznam.cz, Yep) in a single API call.
#
# IndexNow protocol: https://www.indexnow.org/documentation
# Note: Google does NOT participate in IndexNow. Use the Google Indexing API
#       separately for Google submissions (already wired up via seo-google skill).
#
# Usage:
#   ./submit-indexnow.sh URL [URL ...]
#       Submit one or more specific URLs.
#       Example:
#         ./submit-indexnow.sh \
#           https://www.homecareos.co.uk/pricing.html \
#           https://www.homecareos.co.uk/compare-birdie.html
#
#   ./submit-indexnow.sh --all
#       Submit every URL in sitemap.xml. Use sparingly — once after first setup,
#       and only after a major site-wide update. Bing rate-limits repeated
#       full-sitemap submissions (429 response).
#
#   ./submit-indexnow.sh --dry-run [URL ...]
#       Print the JSON payload that would be sent. No HTTP call.
#
#   ./submit-indexnow.sh --help
#       Show this help.

set -euo pipefail

# ============================================================================
# CONFIG — edit if you rotate the key (see README for rotation procedure)
# ============================================================================
HOST="www.homecareos.co.uk"
KEY="988cc8d9-63ce-4fdb-8474-18c9385d993d"
KEY_LOCATION="https://${HOST}/${KEY}.txt"
ENDPOINT="https://api.indexnow.org/indexnow"

# ============================================================================
# Helpers
# ============================================================================

usage() {
  sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

err() {
  printf '\033[31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

# Build the JSON payload from a list of URLs (one per line on stdin).
# Validates that every URL is on $HOST (otherwise IndexNow returns 422).
build_payload() {
  local urls
  urls=$(cat)

  # Validate every URL is on our host
  while IFS= read -r url; do
    [ -z "$url" ] && continue
    if ! printf '%s' "$url" | grep -qE "^https://${HOST}/"; then
      err "URL not on ${HOST}: $url"
    fi
  done <<< "$urls"

  # Build JSON array via Python (stdlib only — portable, escapes correctly)
  python3 -c "
import json, sys
urls = [u.strip() for u in sys.stdin.read().splitlines() if u.strip()]
print(json.dumps({
    'host': '${HOST}',
    'key': '${KEY}',
    'keyLocation': '${KEY_LOCATION}',
    'urlList': urls
}, indent=2))
" <<< "$urls"
}

# POST the JSON payload to the IndexNow endpoint.
# Echoes the HTTP status and (if non-2xx) the response body for debugging.
submit() {
  local payload="$1"
  local response_file http_code
  response_file=$(mktemp)

  # Cleanup on function exit (return — not script EXIT — to avoid unbound-var
  # issues from set -u when the EXIT trap runs after locals have gone away).
  cleanup_response_file() { rm -f "$response_file"; }

  http_code=$(curl -sS -o "$response_file" -w "%{http_code}" \
    -X POST "$ENDPOINT" \
    -H "Content-Type: application/json; charset=utf-8" \
    -H "User-Agent: homecareOS-IndexNow/1.0 (https://${HOST}/)" \
    --max-time 30 \
    --data "$payload")

  case "$http_code" in
    200) printf '\033[32m✓\033[0m HTTP 200 — URLs submitted successfully\n' ;;
    202) printf '\033[33m●\033[0m HTTP 202 — Received, key validation pending (this is fine)\n' ;;
    400) printf '\033[31m✗\033[0m HTTP 400 — Invalid format (payload below)\n' >&2 ;;
    403) printf '\033[31m✗\033[0m HTTP 403 — Key not valid or file not reachable\n' >&2 ;;
    422) printf '\033[31m✗\033[0m HTTP 422 — URLs do not belong to host, or key schema mismatch\n' >&2 ;;
    429) printf '\033[31m✗\033[0m HTTP 429 — Too many requests (wait before retrying)\n' >&2 ;;
    *)   printf '\033[31m✗\033[0m HTTP %s — unexpected response\n' "$http_code" >&2 ;;
  esac

  # Show response body for non-2xx
  if [ "$http_code" -ge 400 ]; then
    echo "  Response body:" >&2
    sed 's/^/    /' "$response_file" >&2
    echo "  Payload sent:" >&2
    printf '%s\n' "$payload" | sed 's/^/    /' >&2
    cleanup_response_file
    return 1
  fi
  cleanup_response_file
}

# ============================================================================
# Main
# ============================================================================

# Parse args
DRY_RUN=0
ALL=0
URLS=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --help|-h)    usage 0 ;;
    --dry-run)    DRY_RUN=1 ;;
    --all)        ALL=1 ;;
    --)           shift; URLS+=("$@"); break ;;
    -*)           err "Unknown flag: $1" ;;
    *)            URLS+=("$1") ;;
  esac
  shift
done

# --all mode: read URLs from sitemap.xml
if [ "$ALL" -eq 1 ]; then
  if [ "${#URLS[@]}" -gt 0 ]; then
    err "--all cannot be combined with explicit URLs"
  fi
  SITEMAP="$(dirname "$0")/../sitemap.xml"
  if [ ! -f "$SITEMAP" ]; then
    err "sitemap.xml not found at $SITEMAP"
  fi
  # Portable equivalent of `mapfile -t URLS < <(...)` (works on macOS bash 3.2)
  while IFS= read -r line; do
    [ -n "$line" ] && URLS+=("$line")
  done < <(grep -oE '<loc>[^<]+</loc>' "$SITEMAP" | sed 's|<loc>||;s|</loc>||')
fi

if [ "${#URLS[@]}" -eq 0 ]; then
  usage 1
fi

# Sanity check: report URL count
echo "Submitting ${#URLS[@]} URL(s) to IndexNow (${ENDPOINT})…"

# Build payload from URLs
PAYLOAD=$(printf '%s\n' "${URLS[@]}" | build_payload)

if [ "$DRY_RUN" -eq 1 ]; then
  echo "── DRY RUN — payload not sent ──"
  printf '%s\n' "$PAYLOAD"
  exit 0
fi

submit "$PAYLOAD"
