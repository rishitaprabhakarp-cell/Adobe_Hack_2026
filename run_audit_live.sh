#!/usr/bin/env bash
# run_audit_live.sh — Brand AI Readiness Audit runner
# Usage: bash run_audit_live.sh <url> [options]
#
# Options:
#   --format html,md,pdf,json   Report formats (default: html,md)
#   --brand-name "Acme Corp"    Brand name in report title
#   --brand-color "#FF0000"     Accent color for HTML/PDF reports
#   --no-report                 Skip report generation (raw JSON outputs only)
#
# Examples:
#   bash run_audit_live.sh https://example.com
#   bash run_audit_live.sh https://example.com --format html,pdf --brand-name "Example"
#   bash run_audit_live.sh https://example.com --format html,md,pdf,json

URL="${1:-https://www.adobe.com}"
shift 2>/dev/null || true

# ── Parse options ─────────────────────────────────────────────────────────────
REPORT_FORMAT="html,md"
BRAND_NAME=""
BRAND_COLOR="#0066CC"
NO_REPORT=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --format)       REPORT_FORMAT="$2"; shift 2 ;;
    --brand-name)   BRAND_NAME="$2";    shift 2 ;;
    --brand-color)  BRAND_COLOR="$2";   shift 2 ;;
    --no-report)    NO_REPORT=true;     shift   ;;
    *) shift ;;
  esac
done

PYTHON="${AUDIT_PYTHON:-/tmp/audit_venv/bin/python3}"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
DOMAIN=$(echo "$URL" | sed 's|https://||' | sed 's|http://||' | sed 's|/.*||')
OUTPUT_DIR="/tmp/audit_results/${DOMAIN}/${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

BASE="$(cd "$(dirname "$0")/skills" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       Brand AI Readiness Audit — Live Run                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  URL        : $URL"
echo "  Domain     : $DOMAIN"
echo "  Output dir : $OUTPUT_DIR"
echo "  Python     : $PYTHON"
echo "  Timestamp  : $TIMESTAMP"
echo ""

# ── Launch all scripts in parallel ──────────────────────────────────────────
echo "  🚀 Launching 13 skill scripts in parallel…"
echo ""

"$PYTHON" "$BASE/crawlability-probe/scripts/crawlability_check.py"                    "$URL" > "$OUTPUT_DIR/crawlability.json"    2>"$OUTPUT_DIR/crawlability.err"    &  PID_crawlability=$!
"$PYTHON" "$BASE/render-gap-detector/scripts/render_check.py"                         "$URL" > "$OUTPUT_DIR/render.json"           2>"$OUTPUT_DIR/render.err"           &  PID_render=$!
"$PYTHON" "$BASE/structured-data-auditor/scripts/schema_audit.py"                     "$URL" > "$OUTPUT_DIR/schema.json"           2>"$OUTPUT_DIR/schema.err"           &  PID_schema=$!
"$PYTHON" "$BASE/entity-corroboration-checker/scripts/entity_check.py"               "$URL" > "$OUTPUT_DIR/entity.json"           2>"$OUTPUT_DIR/entity.err"           &  PID_entity=$!
"$PYTHON" "$BASE/content-extractability-auditor/scripts/content_check.py"             "$URL" > "$OUTPUT_DIR/content.json"          2>"$OUTPUT_DIR/content.err"          &  PID_content=$!
"$PYTHON" "$BASE/eeeat-signal-checker/scripts/eeeat_check.py"                         "$URL" > "$OUTPUT_DIR/eeeat.json"            2>"$OUTPUT_DIR/eeeat.err"            &  PID_eeeat=$!
"$PYTHON" "$BASE/engagement-analyzer/scripts/engagement_check.py"                    "$URL" > "$OUTPUT_DIR/engagement.json"       2>"$OUTPUT_DIR/engagement.err"       &  PID_engagement=$!
"$PYTHON" "$BASE/rsl-licensing-checker/scripts/rsl_check.py"                          "$URL" > "$OUTPUT_DIR/rsl.json"              2>"$OUTPUT_DIR/rsl.err"              &  PID_rsl=$!
"$PYTHON" "$BASE/opengraph-meta-auditor/scripts/og_audit.py"                          "$URL" > "$OUTPUT_DIR/opengraph.json"        2>"$OUTPUT_DIR/opengraph.err"        &  PID_opengraph=$!
"$PYTHON" "$BASE/technical-seo-probe/scripts/technical_check.py"                      "$URL" > "$OUTPUT_DIR/technical.json"        2>"$OUTPUT_DIR/technical.err"        &  PID_technical=$!
"$PYTHON" "$BASE/landing-clarity-auditor/scripts/landing_clarity_check.py"            "$URL" > "$OUTPUT_DIR/landing_clarity.json"  2>"$OUTPUT_DIR/landing_clarity.err"  &  PID_landing_clarity=$!
"$PYTHON" "$BASE/content-trust-auditor/scripts/content_trust_check.py"                "$URL" > "$OUTPUT_DIR/content_trust.json"    2>"$OUTPUT_DIR/content_trust.err"    &  PID_content_trust=$!
"$PYTHON" "$BASE/url-resilience-checker/scripts/url_resilience_check.py"              "$URL" > "$OUTPUT_DIR/url_resilience.json"   2>"$OUTPUT_DIR/url_resilience.err"   &  PID_url_resilience=$!

echo "  ⏳ Waiting for all scripts to finish…"
wait $PID_crawlability;   EC_crawlability=$?
wait $PID_render;         EC_render=$?
wait $PID_schema;         EC_schema=$?
wait $PID_entity;         EC_entity=$?
wait $PID_content;        EC_content=$?
wait $PID_eeeat;          EC_eeeat=$?
wait $PID_engagement;     EC_engagement=$?
wait $PID_rsl;            EC_rsl=$?
wait $PID_opengraph;      EC_opengraph=$?
wait $PID_technical;      EC_technical=$?
wait $PID_landing_clarity; EC_landing_clarity=$?
wait $PID_content_trust;  EC_content_trust=$?
wait $PID_url_resilience; EC_url_resilience=$?

# ── Summary table ─────────────────────────────────────────────────────────────
echo ""
echo "┌──────────────────────────┬────────┬────────────────────────────────────────────┐"
printf "│ %-24s │ %-6s │ %-42s │\n" "Skill" "Status" "Key Signal"
echo "├──────────────────────────┼────────┼────────────────────────────────────────────┤"

PASS=0; FAIL=0

print_row() {
  local skill="$1" ec="$2" out="$3" err_f="$4"

  if [[ $ec -ne 0 ]]; then
    FAIL=$((FAIL+1))
    local err_snip
    err_snip=$(grep -v '^\[' "$err_f" 2>/dev/null | head -1 || echo "see .err file")
    printf "│ %-24s │ %-6s │ %-42s │\n" "$skill" "❌ ERR" "${err_snip:0:42}"
    return
  fi

  if ! "$PYTHON" -c "import json,sys; json.load(open('$out'))" 2>/dev/null; then
    FAIL=$((FAIL+1))
    printf "│ %-24s │ %-6s │ %-42s │\n" "$skill" "⚠️ INV" "Invalid JSON"
    return
  fi

  PASS=$((PASS+1))

  local sig
  case $skill in
    crawlability)
      llms=$("$PYTHON" -c "import json; d=json.load(open('$out')); print(d.get('llms_txt',{}).get('status','?'))" 2>/dev/null)
      blocked=$("$PYTHON" -c "
import json; d=json.load(open('$out'))
bots=d.get('robots',{}).get('bots',{})
print(len([b for b,v in bots.items() if v.get('fully_blocked')]))" 2>/dev/null)
      cdnwaf=$("$PYTHON" -c "
import json; d=json.load(open('$out'))
blocked=[e['bot'] for e in d.get('bot_enforcement',[]) if e.get('cdn_waf_blocked')]
print('CDN-blocks:'+','.join(blocked) if blocked else 'CDN:clear')" 2>/dev/null)
      sig="llms.txt=${llms} | bots_blocked=${blocked} | ${cdnwaf}"
      ;;
    render)
      sig=$("$PYTHON" -c "import json; d=json.load(open('$out')); rg=d.get('render_gap',{}); print(f\"delta={rg.get('word_delta','?')} words | js_only={rg.get('js_only_word_count','?')}\")" 2>/dev/null)
      ;;
    schema)
      sig=$("$PYTHON" -c "
import json; d=json.load(open('$out'))
types=list(d.get('schemas',{}).keys())[:4]
print(f\"{len(types)} types: {', '.join(types)}\")" 2>/dev/null)
      ;;
    entity)
      sig=$("$PYTHON" -c "import json; d=json.load(open('$out')); print(str(d.get('entity_name','?'))[:20] + ' | same_as=' + str(len(d.get('same_as',[]))))" 2>/dev/null)
      ;;
    content)
      sig=$("$PYTHON" -c "
import json; d=json.load(open('$out'))
pages=d.get('pages',[])
if pages:
  p=pages[0]
  caps=p.get('answer_capsules',{})
  cliche=p.get('ai_cliches',{})
  print(f\"capsules={caps.get('answer_capsules_found','?')}/{caps.get('sections_analyzed','?')} | cliches={cliche.get('cliche_count','?')}\")
else: print('no pages')" 2>/dev/null)
      ;;
    eeeat)
      sig=$("$PYTHON" -c "
import json; d=json.load(open('$out'))
wiki=d.get('wikidata_p856',{}).get('wikidata_entity_found','?')
bylines=d.get('author_signals',{}).get('author_count','?')
https=d.get('https_check',{}).get('https_enforced','?')
print(f\"wikidata={wiki} | bylines={bylines} | https={https}\")" 2>/dev/null)
      ;;
    engagement)
      sig=$("$PYTHON" -c "import json; d=json.load(open('$out')); print(str(d)[:50])" 2>/dev/null | tr '\n' ' ')
      ;;
    rsl)
      sig=$("$PYTHON" -c "
import json; d=json.load(open('$out'))
rsl=d.get('rsl_declaration',{}).get('has_rsl','?')
eps=d.get('ai_discovery_endpoint_count','?')
llms=d.get('llms_txt_deep_validation',{}).get('passes_spec','?')
print(f\"rsl={rsl} | endpoints={eps}/14 | llms_spec={llms}\")" 2>/dev/null)
      ;;
    opengraph)
      sig=$("$PYTHON" -c "
import json; d=json.load(open('$out'))
pages=d.get('pages',[])
if pages:
  og=pages[0].get('og',{})
  print(f\"title={bool(og.get('og:title'))} | img={bool(og.get('og:image'))} | desc={bool(og.get('og:description'))}\")
else: print('no pages')" 2>/dev/null)
      ;;
    technical)
      sig=$("$PYTHON" -c "
import json; d=json.load(open('$out'))
https=d.get('https',{}).get('enforced','?')
canon=d.get('canonical',{}).get('present','?')
h1=d.get('headings',{}).get('h1_count','?')
print(f\"https={https} | canonical={canon} | h1={h1}\")" 2>/dev/null)
      ;;
  esac

  printf "│ %-24s │ %-6s │ %-42s │\n" "$skill" "✅ OK " "${sig:0:42}"
}

print_row "crawlability"    "$EC_crawlability"    "$OUTPUT_DIR/crawlability.json"    "$OUTPUT_DIR/crawlability.err"
print_row "render-gap"      "$EC_render"          "$OUTPUT_DIR/render.json"          "$OUTPUT_DIR/render.err"
print_row "schema"          "$EC_schema"          "$OUTPUT_DIR/schema.json"          "$OUTPUT_DIR/schema.err"
print_row "entity"          "$EC_entity"          "$OUTPUT_DIR/entity.json"          "$OUTPUT_DIR/entity.err"
print_row "content"         "$EC_content"         "$OUTPUT_DIR/content.json"         "$OUTPUT_DIR/content.err"
print_row "eeeat"           "$EC_eeeat"           "$OUTPUT_DIR/eeeat.json"           "$OUTPUT_DIR/eeeat.err"
print_row "engagement"      "$EC_engagement"      "$OUTPUT_DIR/engagement.json"      "$OUTPUT_DIR/engagement.err"
print_row "rsl"             "$EC_rsl"             "$OUTPUT_DIR/rsl.json"             "$OUTPUT_DIR/rsl.err"
print_row "opengraph"       "$EC_opengraph"       "$OUTPUT_DIR/opengraph.json"       "$OUTPUT_DIR/opengraph.err"
print_row "technical"       "$EC_technical"       "$OUTPUT_DIR/technical.json"       "$OUTPUT_DIR/technical.err"
print_row "landing-clarity" "$EC_landing_clarity" "$OUTPUT_DIR/landing_clarity.json" "$OUTPUT_DIR/landing_clarity.err"
print_row "content-trust"   "$EC_content_trust"   "$OUTPUT_DIR/content_trust.json"   "$OUTPUT_DIR/content_trust.err"
print_row "url-resilience"  "$EC_url_resilience"  "$OUTPUT_DIR/url_resilience.json"  "$OUTPUT_DIR/url_resilience.err"

echo "└──────────────────────────┴────────┴────────────────────────────────────────────┘"
echo ""
echo "  Results: ✅ $PASS passed  ❌ $FAIL errored"
echo "  All JSON outputs: $OUTPUT_DIR/"
echo ""

# ── Print stderr for any failures ────────────────────────────────────────────
for skill in crawlability render schema entity content eeeat engagement rsl opengraph technical landing_clarity content_trust url_resilience; do
  ec_var="EC_${skill}"
  if [[ "${!ec_var}" -ne 0 ]]; then
    echo "── stderr: $skill ──────────────────────────────────────"
    cat "$OUTPUT_DIR/${skill}.err" 2>/dev/null | head -20
    echo ""
  fi
done

echo "Tip: cat $OUTPUT_DIR/<skill>.json | python3 -m json.tool | less"
echo ""

# ── Generate reports ─────────────────────────────────────────────────────────
if [[ "$NO_REPORT" == "true" ]]; then
  echo "  --no-report flag set: skipping report generation."
  exit 0
fi

REPORT_SCRIPT="$(cd "$(dirname "$0")" && pwd)/generate_report.py"

if [[ ! -f "$REPORT_SCRIPT" ]]; then
  echo "  ⚠  generate_report.py not found — skipping report generation."
  exit 0
fi

echo "────────────────────────────────────────────────────────────────"
echo "  Generating reports (format: ${REPORT_FORMAT})…"
echo "────────────────────────────────────────────────────────────────"

REPORT_ARGS=(
  "$OUTPUT_DIR"
  "--format" "$REPORT_FORMAT"
  "--brand-color" "$BRAND_COLOR"
)
[[ -n "$BRAND_NAME" ]] && REPORT_ARGS+=("--brand-name" "$BRAND_NAME")

"$PYTHON" "$REPORT_SCRIPT" "${REPORT_ARGS[@]}"

echo ""
echo "Open HTML report:"
echo "  open $OUTPUT_DIR/reports/ai-readiness-audit-${DOMAIN/www./}.html"
