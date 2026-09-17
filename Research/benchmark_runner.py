#!/usr/bin/env python3
"""
benchmark_runner.py — Brand AI Readiness Audit · Benchmark Suite
=================================================================
Runs the full audit pipeline against 10 pre-selected benchmark sites,
collects per-site scores, and produces a comparative JSON dataset used
in EVAL.md to substantiate performance claims.

Usage:
    python benchmark_runner.py                          # run all 10 sites
    python benchmark_runner.py --sites stripe.com vercel.com
    python benchmark_runner.py --output-dir ./benchmark_results
    python benchmark_runner.py --skip-scripts          # use cached JSON (for re-renders)
    python benchmark_runner.py --compare-tool geoready # tag competitor baseline

Each site is audited by running all 10 Python skill scripts in parallel.
Results are saved to <output_dir>/<domain>/ and a master summary JSON is
written to <output_dir>/benchmark_summary.json.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK SITE REGISTRY
# Each entry is carefully chosen to span the full GEO readiness spectrum and
# cover diverse industries, so the benchmark is representative, not cherry-picked.
# ─────────────────────────────────────────────────────────────────────────────

BENCHMARK_SITES = [
    {
        "url": "https://stripe.com",
        "domain": "stripe.com",
        "tier": "GEO_READY",
        "industry": "FinTech / Payments",
        "rationale": (
            "Best-in-class structured data, rich JSON-LD, Organization sameAs, strong "
            "E-E-A-T. Expected to score ≥ 70 (GEO Ready). Serves as the upper benchmark."
        ),
        "expected_score_range": [68, 85],
        "expected_critical": 0,
        "known_gaps": ["No RSL 1.0", "No llms-full.txt"],
    },
    {
        "url": "https://openai.com",
        "domain": "openai.com",
        "tier": "GEO_READY",
        "industry": "AI / Technology",
        "rationale": (
            "Operator of GPTBot — has strong incentive and capability to be "
            "AI-crawlable. Has llms.txt, Organization JSON-LD, Wikidata entity. "
            "Expected near-perfect crawlability and entity scores."
        ),
        "expected_score_range": [72, 90],
        "expected_critical": 0,
        "known_gaps": ["Possible nosnippet on some pages"],
    },
    {
        "url": "https://anthropic.com",
        "domain": "anthropic.com",
        "tier": "GEO_READY",
        "industry": "AI / Research",
        "rationale": (
            "Has llms.txt, Claude/ClaudeBot policy alignment, Wikidata entry, "
            "strong E-E-A-T from research papers. Expected high crawlability + entity scores."
        ),
        "expected_score_range": [65, 82],
        "expected_critical": 0,
        "known_gaps": ["Possible thin schema on blog pages"],
    },
    {
        "url": "https://vercel.com",
        "domain": "vercel.com",
        "tier": "DEVELOPING",
        "industry": "Developer Tools / Cloud",
        "rationale": (
            "Strong technical SEO, SSR-first framework. Some gaps in E-E-A-T signals "
            "and off-page authority. Expected 55–70 range — a solid DEVELOPING score."
        ),
        "expected_score_range": [52, 70],
        "expected_critical": 0,
        "known_gaps": ["Thin review platform presence", "No RSS feed"],
    },
    {
        "url": "https://linear.app",
        "domain": "linear.app",
        "tier": "DEVELOPING",
        "industry": "Project Management SaaS",
        "rationale": (
            "Known to have llms.txt. Strong content structure, clean SSR. "
            "Gap in E-E-A-T review platforms. Good mid-range benchmark."
        ),
        "expected_score_range": [50, 68],
        "expected_critical": 0,
        "known_gaps": ["Limited review platform links", "No author bylines"],
    },
    {
        "url": "https://www.adobe.com",
        "domain": "adobe.com",
        "tier": "NOT_GEO_READY",
        "industry": "Creative Software / Enterprise",
        "rationale": (
            "Real audit already run (score: 48). Known gaps: no OG tags, no RSL, "
            "no AI discovery endpoints, thin E-E-A-T. Serves as the DEVELOPING/failing "
            "enterprise benchmark. Score confirmed at 48 from live run."
        ),
        "expected_score_range": [40, 55],
        "expected_critical": 1,
        "known_gaps": [
            "No OpenGraph tags (CRITICAL)",
            "No RSL 1.0",
            "No AI discovery endpoints",
            "No answer capsules",
        ],
        "confirmed_score": 48,
    },
    {
        "url": "https://www.hubspot.com",
        "domain": "hubspot.com",
        "tier": "DEVELOPING",
        "industry": "Marketing / CRM SaaS",
        "rationale": (
            "Heavy content marketing site with extensive blog. Expected strong E-E-A-T "
            "and content structure scores, but potential JS-rendering issues and "
            "thin AI-specific standards (RSL, llms.txt)."
        ),
        "expected_score_range": [45, 65],
        "expected_critical": 0,
        "known_gaps": ["Likely missing RSL/llms.txt", "JS-heavy pages"],
    },
    {
        "url": "https://www.shopify.com",
        "domain": "shopify.com",
        "tier": "DEVELOPING",
        "industry": "eCommerce Platform",
        "rationale": (
            "Well-known brand with strong entity signals. Expected to have schema on "
            "product pages, but gaps in AI-specific standards. Good mid-tier commercial benchmark."
        ),
        "expected_score_range": [48, 65],
        "expected_critical": 0,
        "known_gaps": ["Likely no llms.txt", "Variable schema quality across sections"],
    },
    {
        "url": "https://www.craigslist.org",
        "domain": "craigslist.org",
        "tier": "NOT_GEO_READY",
        "industry": "Classifieds / Marketplace",
        "rationale": (
            "Intentionally bare-bones HTML. No JSON-LD, no llms.txt, minimal meta tags. "
            "Expected to be near the floor — a clear NOT_GEO_READY case with many HIGH findings."
        ),
        "expected_score_range": [10, 30],
        "expected_critical": 0,
        "known_gaps": [
            "No JSON-LD", "No llms.txt", "No OG tags", "No AI discovery endpoints"
        ],
    },
    {
        "url": "https://supabase.com",
        "domain": "supabase.com",
        "tier": "DEVELOPING",
        "industry": "Developer Tools / Database",
        "rationale": (
            "Developer-first company with strong docs. Likely has some GEO signals "
            "but may lack review platform presence and RSL. Good open-source benchmark."
        ),
        "expected_score_range": [50, 68],
        "expected_critical": 0,
        "known_gaps": ["Possible thin E-E-A-T", "No RSL 1.0"],
    },
]

# Tier thresholds (Directive Consulting 2026)
TIER_LABELS = {
    "GEO_READY":     {"min": 70, "label": "GEO Ready",     "color": "🟢"},
    "DEVELOPING":    {"min": 50, "label": "Developing",    "color": "🟡"},
    "NOT_GEO_READY": {"min": 0,  "label": "Not GEO Ready", "color": "🔴"},
}

# Scripts to run per site (relative to repo root)
SKILL_SCRIPTS = [
    ("crawlability",  "skills/crawlability-probe/scripts/crawlability_check.py",  "crawlability.json"),
    ("render",        "skills/render-gap-detector/scripts/render_check.py",        "render.json"),
    ("schema",        "skills/structured-data-auditor/scripts/schema_audit.py",    "schema.json"),
    ("entity",        "skills/entity-corroboration-checker/scripts/entity_check.py","entity.json"),
    ("content",       "skills/content-extractability-auditor/scripts/content_check.py","content.json"),
    ("eeeat",         "skills/eeeat-signal-checker/scripts/eeeat_check.py",         "eeeat.json"),
    ("engagement",    "skills/engagement-analyzer/scripts/engagement_check.py",    "engagement.json"),
    ("rsl",           "skills/rsl-licensing-checker/scripts/rsl_check.py",          "rsl.json"),
    ("opengraph",     "skills/opengraph-meta-auditor/scripts/og_audit.py",         "opengraph.json"),
    ("technical",     "skills/technical-seo-probe/scripts/technical_check.py",     "technical.json"),
]


# ─────────────────────────────────────────────────────────────────────────────
# SCRIPT RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_script(python: str, script_path: str, url: str, output_path: Path, timeout: int = 90) -> dict:
    """Run a single skill script. Returns {ok, elapsed_s, error}."""
    t0 = time.time()
    try:
        result = subprocess.run(
            [python, script_path, url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = round(time.time() - t0, 1)
        if result.returncode != 0:
            return {"ok": False, "elapsed_s": elapsed, "error": f"exit {result.returncode}: {result.stderr[:300]}"}
        # Validate JSON
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return {"ok": False, "elapsed_s": elapsed, "error": f"invalid JSON: {e}"}
        output_path.write_text(result.stdout, encoding="utf-8")
        return {"ok": True, "elapsed_s": elapsed, "error": None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "elapsed_s": timeout, "error": f"timeout after {timeout}s"}
    except Exception as e:
        return {"ok": False, "elapsed_s": round(time.time() - t0, 1), "error": str(e)}


def audit_site(site: dict, output_dir: Path, python: str, skip_scripts: bool) -> dict:
    """Run all scripts for one site. Returns a run record."""
    url = site["url"]
    domain = site["domain"]
    site_dir = output_dir / domain
    site_dir.mkdir(parents=True, exist_ok=True)

    run_record = {
        "url": url,
        "domain": domain,
        "tier": site["tier"],
        "industry": site["industry"],
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "script_results": {},
        "scripts_ok": 0,
        "scripts_failed": 0,
        "total_elapsed_s": 0,
    }

    if skip_scripts:
        print(f"  ⏭  {domain} — skipping scripts (--skip-scripts)")
        return run_record

    print(f"\n  🔍  Auditing {domain} ...")

    # Run all scripts in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        repo_root = Path(__file__).parent
        for skill_name, script_rel, output_file in SKILL_SCRIPTS:
            script_abs = repo_root / script_rel
            out_path = site_dir / output_file
            fut = executor.submit(run_script, python, str(script_abs), url, out_path)
            futures[fut] = skill_name

        for fut in as_completed(futures):
            skill_name = futures[fut]
            res = fut.result()
            run_record["script_results"][skill_name] = res
            run_record["total_elapsed_s"] += res["elapsed_s"]
            if res["ok"]:
                run_record["scripts_ok"] += 1
                print(f"      ✓  {skill_name} ({res['elapsed_s']}s)")
            else:
                run_record["scripts_failed"] += 1
                print(f"      ✗  {skill_name}: {res['error']}")

    return run_record


# ─────────────────────────────────────────────────────────────────────────────
# SCORE EXTRACTOR
# Pulls scores from generate_report.py output if available, else approximates
# from raw script JSON for a fast benchmark summary.
# ─────────────────────────────────────────────────────────────────────────────

def extract_scores_from_dir(site_dir: Path) -> dict:
    """
    Attempt to read scores from a pre-generated report JSON, or compute
    a lightweight approximation from raw script outputs.
    """
    # 1. Try enriched report JSON (most accurate)
    for fname in ["report.json", "ai-readiness-audit-*.json"]:
        import glob
        matches = list(site_dir.glob(fname)) + list(site_dir.glob("reports/" + fname))
        for match in matches:
            try:
                with open(match) as f:
                    data = json.load(f)
                if "overall_score" in data:
                    return {
                        "overall_score": data["overall_score"],
                        "geo_readiness": data.get("geo_readiness", "Unknown"),
                        "total_findings": data.get("summary", {}).get("total_findings", 0),
                        "critical": data.get("summary", {}).get("critical", 0),
                        "high": data.get("summary", {}).get("high", 0),
                        "source": "report_json",
                        "dimension_scores": {
                            d["name"]: d["score"]
                            for d in data.get("dimension_scores", [])
                        },
                        "engine_scores": data.get("engine_scores", {}),
                    }
            except Exception:
                pass

    # 2. Lightweight approximation from raw script outputs
    findings = []
    for _, _, output_file in SKILL_SCRIPTS:
        path = site_dir / output_file
        if path.exists():
            try:
                data = json.load(open(path))
                if "findings" in data:
                    findings.extend(data["findings"])
            except Exception:
                pass

    if not findings:
        return {"overall_score": None, "source": "none"}

    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        sev = f.get("severity", "LOW")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    # Rough penalty model (same logic as generate_report.py)
    penalty = (sev_counts["CRITICAL"] * 20 + sev_counts["HIGH"] * 7 +
               sev_counts["MEDIUM"] * 3 + sev_counts["LOW"] * 1)
    approx_score = max(0, min(100, 100 - penalty))

    tier = ("GEO Ready" if approx_score >= 70
            else "Developing" if approx_score >= 50
            else "Not GEO Ready")

    return {
        "overall_score": approx_score,
        "geo_readiness": tier,
        "total_findings": len(findings),
        "critical": sev_counts["CRITICAL"],
        "high": sev_counts["HIGH"],
        "medium": sev_counts["MEDIUM"],
        "low": sev_counts["LOW"],
        "source": "approximated",
        "dimension_scores": {},
        "engine_scores": {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_summary(sites: list[dict], run_records: list[dict], output_dir: Path) -> dict:
    """Build the master benchmark_summary.json."""
    results = []
    for site, record in zip(sites, run_records):
        domain = site["domain"]
        site_dir = output_dir / domain
        scores = extract_scores_from_dir(site_dir)

        # Validate against expected range
        expected_lo, expected_hi = site["expected_score_range"]
        score = scores.get("overall_score")
        in_range = (score is not None and expected_lo <= score <= expected_hi)

        results.append({
            "domain": domain,
            "url": site["url"],
            "industry": site["industry"],
            "expected_tier": site["tier"],
            "expected_range": site["expected_score_range"],
            "confirmed_score": site.get("confirmed_score"),
            "observed_score": score,
            "in_expected_range": in_range,
            "geo_readiness": scores.get("geo_readiness"),
            "total_findings": scores.get("total_findings"),
            "critical": scores.get("critical", 0),
            "high": scores.get("high", 0),
            "medium": scores.get("medium", 0),
            "low": scores.get("low", 0),
            "dimension_scores": scores.get("dimension_scores", {}),
            "engine_scores": scores.get("engine_scores", {}),
            "known_gaps": site["known_gaps"],
            "scripts_ok": record["scripts_ok"],
            "scripts_failed": record["scripts_failed"],
            "total_elapsed_s": record["total_elapsed_s"],
            "score_source": scores.get("source"),
        })

    # Aggregate stats
    scored = [r for r in results if r["observed_score"] is not None]
    in_range_count = sum(1 for r in scored if r["in_expected_range"])
    avg_score = round(sum(r["observed_score"] for r in scored) / len(scored), 1) if scored else None

    tier_distribution = {
        "GEO_READY":     sum(1 for r in results if r["expected_tier"] == "GEO_READY"),
        "DEVELOPING":    sum(1 for r in results if r["expected_tier"] == "DEVELOPING"),
        "NOT_GEO_READY": sum(1 for r in results if r["expected_tier"] == "NOT_GEO_READY"),
    }

    # Score monotonicity check: GEO_READY sites should outscore NOT_GEO_READY sites
    geo_ready_scores    = [r["observed_score"] for r in scored if r["expected_tier"] == "GEO_READY" and r["observed_score"]]
    not_ready_scores    = [r["observed_score"] for r in scored if r["expected_tier"] == "NOT_GEO_READY" and r["observed_score"]]
    monotonicity_ok     = (
        bool(geo_ready_scores) and bool(not_ready_scores)
        and min(geo_ready_scores) > max(not_ready_scores)
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "Brand AI Readiness Audit Marketplace v2.0",
        "sites_audited": len(results),
        "sites_scored": len(scored),
        "average_score": avg_score,
        "in_expected_range": in_range_count,
        "score_accuracy_pct": round(in_range_count / len(scored) * 100, 1) if scored else 0,
        "tier_distribution": tier_distribution,
        "monotonicity_check_passed": monotonicity_ok,
        "results": results,
    }
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# Calls generate_report.py for each site to produce HTML/MD reports.
# ─────────────────────────────────────────────────────────────────────────────

def generate_reports_for_site(python: str, site: dict, site_dir: Path, formats: str = "html,md,json") -> bool:
    """Run generate_report.py for a given site directory."""
    repo_root = Path(__file__).parent
    gen_script = repo_root / "generate_report.py"
    if not gen_script.exists():
        return False
    try:
        result = subprocess.run(
            [python, str(gen_script), str(site_dir),
             "--format", formats,
             "--brand-name", site["domain"],
             "--site", site["url"]],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MARKDOWN TABLE PRINTER
# ─────────────────────────────────────────────────────────────────────────────

def print_summary_table(summary: dict) -> None:
    """Print a console-friendly markdown table of results."""
    print("\n" + "═" * 100)
    print("  BENCHMARK RESULTS")
    print("═" * 100)
    hdr = f"{'Domain':<25} {'Industry':<28} {'Tier':<15} {'Score':>6} {'Range':>12} {'✓':>4} {'Findings':>9}"
    print(hdr)
    print("─" * 100)
    for r in summary["results"]:
        score_str = str(r["observed_score"]) if r["observed_score"] is not None else "N/A"
        lo, hi    = r["expected_range"]
        range_str = f"[{lo}–{hi}]"
        check     = "✓" if r["in_expected_range"] else "✗"
        tier_icon = {"GEO_READY": "🟢", "DEVELOPING": "🟡", "NOT_GEO_READY": "🔴"}.get(r["expected_tier"], "⚪")
        find_str  = f"C:{r['critical']} H:{r['high']} M:{r['medium']} L:{r['low']}"
        print(f"{r['domain']:<25} {r['industry']:<28} {tier_icon} {r['expected_tier']:<12} {score_str:>6} {range_str:>12} {check:>4} {find_str:>9}")
    print("─" * 100)
    print(f"  Sites scored: {summary['sites_scored']}/{summary['sites_audited']}")
    print(f"  Average score: {summary['average_score']}")
    print(f"  In expected range: {summary['in_expected_range']}/{summary['sites_scored']} ({summary['score_accuracy_pct']}%)")
    print(f"  Monotonicity (GEO Ready > Not GEO Ready): {'✓ PASS' if summary['monotonicity_check_passed'] else '✗ FAIL'}")
    print("═" * 100 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run the Brand AI Readiness Audit benchmark suite against 10 pre-selected sites."
    )
    parser.add_argument(
        "--sites", nargs="+", metavar="DOMAIN",
        help="Subset of sites to run (by domain, e.g. stripe.com). Default: all 10.",
    )
    parser.add_argument(
        "--output-dir", default="./benchmark_results", metavar="DIR",
        help="Directory to write results (default: ./benchmark_results).",
    )
    parser.add_argument(
        "--skip-scripts", action="store_true",
        help="Skip running scripts; only re-score from existing JSON outputs.",
    )
    parser.add_argument(
        "--generate-reports", action="store_true",
        help="After scripts run, call generate_report.py for each site.",
    )
    parser.add_argument(
        "--report-formats", default="html,md,json",
        help="Report formats to generate (default: html,md,json).",
    )
    parser.add_argument(
        "--python", default=sys.executable,
        help="Python interpreter to use (default: current venv python).",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter sites
    sites = BENCHMARK_SITES
    if args.sites:
        sites = [s for s in BENCHMARK_SITES if s["domain"] in args.sites]
        if not sites:
            print(f"ERROR: No matching sites found for: {args.sites}", file=sys.stderr)
            sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  Brand AI Readiness Audit — Benchmark Suite")
    print(f"  Sites: {len(sites)}  |  Output: {output_dir}")
    print(f"{'═'*60}")

    # Run audits
    run_records = []
    t_start = time.time()
    for site in sites:
        record = audit_site(site, output_dir, args.python, args.skip_scripts)
        run_records.append(record)

        if args.generate_reports and not args.skip_scripts:
            site_dir = output_dir / site["domain"]
            ok = generate_reports_for_site(args.python, site, site_dir, args.report_formats)
            print(f"      {'✓' if ok else '✗'}  Report generation for {site['domain']}")

    total_elapsed = round(time.time() - t_start, 1)

    # Build summary
    summary = build_summary(sites, run_records, output_dir)
    summary["total_wall_time_s"] = total_elapsed

    # Save master summary
    summary_path = output_dir / "benchmark_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Print table
    print_summary_table(summary)
    print(f"  ✓  Saved: {summary_path}")
    print(f"  ✓  Total wall time: {total_elapsed}s\n")


if __name__ == "__main__":
    main()
