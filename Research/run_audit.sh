#!/bin/bash
# run_audit.sh — Run all Brand AI Readiness Audit scripts against a URL
# Usage: bash run_audit.sh https://example.com
#
# Requires: Python 3.9+, pip install requests

URL="${1:-https://example.com}"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
DOMAIN=$(echo "$URL" | sed 's|https\?://||' | sed 's|/.*||')
OUTPUT_DIR="audit_results/${DOMAIN}/${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  Brand AI Readiness Audit — Script Runner${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -e "  Target  : ${YELLOW}$URL${NC}"
echo -e "  Domain  : ${YELLOW}$DOMAIN${NC}"
echo -e "  Output  : ${YELLOW}$OUTPUT_DIR${NC}"
echo -e "  Started : $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo -e "${BLUE}==================================================${NC}"
echo ""

SCRIPTS=(
  "crawlability-probe/scripts/crawlability_check.py:crawlability-probe"
  "render-gap-detector/scripts/render_check.py:render-gap-detector"
  "structured-data-auditor/scripts/schema_audit.py:structured-data-auditor"
  "entity-corroboration-checker/scripts/entity_check.py:entity-corroboration-checker"
  "engagement-analyzer/scripts/engagement_check.py:engagement-analyzer"
  "content-extractability-auditor/scripts/content_check.py:content-extractability-auditor"
  "eeeat-signal-checker/scripts/eeeat_check.py:eeeat-signal-checker"
  "technical-seo-probe/scripts/technical_check.py:technical-seo-probe"
  "opengraph-meta-auditor/scripts/og_audit.py:opengraph-meta-auditor"
  "rsl-licensing-checker/scripts/rsl_check.py:rsl-licensing-checker"
)

TOTAL=0
ERRORS=0
START_TIME=$SECONDS

for entry in "${SCRIPTS[@]}"; do
  script="${entry%%:*}"
  skill_name="${entry##*:}"
  output_file="$OUTPUT_DIR/${skill_name}.json"

  printf "  %-42s" "$skill_name..."

  # Run script, capture stderr separately
  STDERR_FILE=$(mktemp)
  if python3 "skills/$script" "$URL" 2>"$STDERR_FILE" > "$output_file"; then
    # Validate JSON
    if python3 -c "import json,sys; json.load(open('$output_file'))" 2>/dev/null; then
      echo -e "${GREEN}OK ✓${NC}"
      TOTAL=$((TOTAL + 1))
    else
      echo -e "${RED}INVALID JSON ✗${NC}"
      ERRORS=$((ERRORS + 1))
      cat "$STDERR_FILE" >> "$output_file.error"
    fi
  else
    EXIT_CODE=$?
    echo -e "${RED}FAILED (exit $EXIT_CODE) ✗${NC}"
    ERRORS=$((ERRORS + 1))
    cp "$STDERR_FILE" "$output_file.error"
  fi
  rm -f "$STDERR_FILE"
done

ELAPSED=$((SECONDS - START_TIME))

echo ""
echo -e "${BLUE}==================================================${NC}"
echo -e "  Scripts : ${GREEN}$TOTAL passed${NC} / ${RED}$ERRORS failed${NC} of $((TOTAL + ERRORS)) total"
echo -e "  Runtime : ${ELAPSED}s"
echo -e "  Results : ${YELLOW}$OUTPUT_DIR/${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

if [ $TOTAL -gt 0 ]; then
  echo -e "${BLUE}Quick preview — Crawlability:${NC}"
  if [ -f "$OUTPUT_DIR/crawlability-probe.json" ]; then
    python3 -c "
import json
data = json.load(open('$OUTPUT_DIR/crawlability-probe.json'))
r = data.get('robots_txt', {})
l = data.get('llms_txt', {})
s = data.get('sitemap', [{}])
print(f'  robots.txt  : HTTP {r.get(\"status\", \"?\")}, {len(r.get(\"bots\", {}))} bots checked')
print(f'  llms.txt    : HTTP {l.get(\"status\", \"?\")}, starts_with_#={l.get(\"starts_with_hash\", \"?\")}')
if s: print(f'  sitemap     : HTTP {s[0].get(\"status\", \"?\")}, lastmod_count={s[0].get(\"lastmod_count\", 0)}')
blocked = [b for b,v in r.get('bots',{}).items() if v.get('fully_blocked') and b in ['GPTBot','ClaudeBot','PerplexityBot']]
if blocked: print(f'  BLOCKED BOTS: {blocked}')
" 2>/dev/null || echo "  (parse error — check $OUTPUT_DIR/crawlability-probe.json)"
  fi

  echo ""
  echo -e "${BLUE}Quick preview — Render Gap:${NC}"
  if [ -f "$OUTPUT_DIR/render-gap-detector.json" ]; then
    python3 -c "
import json
data = json.load(open('$OUTPUT_DIR/render-gap-detector.json'))
pages = data.get('pages', [])
for p in pages[:3]:
  path = p.get('path', '/')
  wc = p.get('word_count', '?')
  cls = p.get('classification', '?')
  spa = p.get('spa_shell_detected', False)
  print(f'  {path:20s}  {wc:4} words  {cls}  SPA={spa}')
" 2>/dev/null || echo "  (parse error — check $OUTPUT_DIR/render-gap-detector.json)"
  fi

  echo ""
  echo -e "${BLUE}Quick preview — Schema Types Found:${NC}"
  if [ -f "$OUTPUT_DIR/structured-data-auditor.json" ]; then
    python3 -c "
import json
data = json.load(open('$OUTPUT_DIR/structured-data-auditor.json'))
types = data.get('site_schema_types', [])
print(f'  {types[:10]}')
print(f'  speakable={data.get(\"site_has_speakable\")}, faqpage={data.get(\"site_has_faqpage\")}, howto={data.get(\"site_has_howto\")}')
" 2>/dev/null || echo "  (parse error)"
  fi
fi

echo ""
echo "To view any result in full:"
echo "  cat $OUTPUT_DIR/<skill-name>.json | python3 -m json.tool"
echo ""
echo "Next step: Use an AI agent with the audit-orchestrator skill to"
echo "interpret these results and generate the final report."
echo ""
