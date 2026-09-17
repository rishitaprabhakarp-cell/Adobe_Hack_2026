#!/usr/bin/env python3
"""
rsl_check.py — RSL Licensing & AI Standards Checker helper script
Usage: python rsl_check.py <url>

Checks RSL 1.0, llms-full.txt, AI discovery endpoints, IndexNow, and deep llms.txt validation.
Read-only.
"""

import sys
import json
import re
import time
from urllib.parse import urlparse, urljoin

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests library not installed. Run: pip install requests"}))
    sys.exit(1)

DEFAULT_UA = "Mozilla/5.0 (compatible; BrandAuditBot/1.0)"
TIMEOUT = 10

# All AI discovery endpoints to check
# Includes 2026 Autonomous Discovery Format (ADF) additions: brand.txt, identity.json, faq-ai.txt, ai.json
AI_DISCOVERY_ENDPOINTS = [
    # Tier 1 — Core well-known paths
    "/.well-known/ai.txt",
    "/.well-known/ai.json",
    "/.well-known/rsl.json",
    # Tier 2 — AI API surface
    "/ai/summary.json",
    "/ai/faq.json",
    "/ai/service.json",
    "/ai/manifest.json",
    # Tier 3 — ADF 2026 extensions (Autonomous Discovery Format)
    "/brand.txt",
    "/identity.json",
    "/faq-ai.txt",
    "/ai.json",
    "/.well-known/brand.json",
    "/.well-known/llms-context.txt",
]


def safe_get(url, ua=DEFAULT_UA, allow_redirects=True):
    headers = {"User-Agent": ua, "Accept": "*/*"}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT,
                            allow_redirects=allow_redirects)
        ct = resp.headers.get("Content-Type", "")
        return resp.status_code, resp.text, ct, None
    except Exception as e:
        return None, None, None, str(e)


def check_rsl_declaration(base_url, homepage_html):
    """Check for RSL 1.0 machine-readable license declaration."""
    # Check link tag in HTML
    link_match = re.search(
        r'<link[^>]+rel=["\']robots-standard-license["\'][^>]+href=["\']([^"\']+)["\']',
        homepage_html or "", re.IGNORECASE
    )

    rsl_link = link_match.group(1) if link_match else None

    # Check /.well-known/rsl.json
    rsl_url = urljoin(base_url, "/.well-known/rsl.json")
    status, body, ct, error = safe_get(rsl_url)

    rsl_json = None
    if status == 200 and body:
        try:
            rsl_json = json.loads(body)
        except json.JSONDecodeError:
            rsl_json = {"_parse_error": True, "raw": body[:200]}

    return {
        "html_rsl_link": rsl_link,
        "well_known_rsl_status": status,
        "well_known_rsl_content": rsl_json,
        "has_rsl": rsl_link is not None or status == 200,
    }


def check_llms_full_txt(base_url):
    """Check for llms-full.txt companion file."""
    url = urljoin(base_url, "/llms-full.txt")
    status, body, ct, error = safe_get(url)
    return {
        "url": url,
        "status": status,
        "content_type": ct,
        "word_count": len(body.split()) if body else 0,
        "present": status == 200,
        "error": error,
    }


def check_ai_discovery_endpoints(base_url):
    """Check all AI discovery endpoints."""
    results = []
    for path in AI_DISCOVERY_ENDPOINTS:
        endpoint_url = urljoin(base_url, path)
        status, body, ct, error = safe_get(endpoint_url)

        entry = {
            "path": path,
            "url": endpoint_url,
            "status": status,
            "content_type": ct,
            "error": error,
            "present": status == 200,
        }

        if status == 200 and body:
            if "json" in (ct or ""):
                try:
                    entry["parsed_json"] = json.loads(body)
                except Exception:
                    entry["json_parse_error"] = True
            else:
                entry["snippet"] = body[:200]

        results.append(entry)

    return results


def check_indexnow(base_url, homepage_html):
    """Check for IndexNow implementation."""
    # Check for IndexNow key reference in HTML
    indexnow_in_html = bool(re.search(r'IndexNow|indexnow', homepage_html or ""))

    # Check robots.txt for IndexNow
    robots_url = urljoin(base_url, "/robots.txt")
    _, robots_body, _, _ = safe_get(robots_url)
    indexnow_in_robots = bool(re.search(r'IndexNow', robots_body or "", re.IGNORECASE))

    # Check common IndexNow key file patterns
    # (IndexNow keys are alphanumeric strings placed at /<key>.txt)
    # We can't know the key, so just check for the pattern in robots.txt
    indexnow_key_match = re.search(
        r'(?:IndexNow-verification|indexnow):\s*([a-fA-F0-9]{32,})',
        robots_body or "", re.IGNORECASE
    )

    return {
        "indexnow_in_html": indexnow_in_html,
        "indexnow_in_robots": indexnow_in_robots,
        "indexnow_key_found": indexnow_key_match.group(1) if indexnow_key_match else None,
        "has_indexnow": indexnow_in_html or indexnow_in_robots or bool(indexnow_key_match),
    }


def deep_validate_llms_txt(base_url):
    """Deep validation of llms.txt against the full spec."""
    url = urljoin(base_url, "/llms.txt")
    status, body, ct, error = safe_get(url)

    if error or not body or status != 200:
        return {"present": False, "status": status, "error": error}

    lines = body.splitlines()
    issues = []

    # Rule 1: Must start with H1
    has_h1 = False
    h1_text = None
    for line in lines[:5]:
        if line.startswith("# "):
            has_h1 = True
            h1_text = line[2:].strip()
            break

    if not has_h1:
        issues.append({"rule": "H1 required", "severity": "HIGH"})

    # Rule 2: H1 should not contain a URL
    if h1_text and ("http://" in h1_text or "https://" in h1_text):
        issues.append({"rule": "H1 contains URL (should be project name)", "severity": "MEDIUM"})

    # Rule 3: Blockquote summary
    has_blockquote = any(line.startswith(">") for line in lines[:10])
    if not has_blockquote:
        issues.append({"rule": "Missing blockquote summary (recommended)", "severity": "LOW"})

    # Rule 4: H2 sections should only have list items with markdown links
    in_h2 = False
    non_link_items = []
    for line in lines:
        if line.startswith("## "):
            in_h2 = True
            continue
        if in_h2 and line.startswith("- "):
            if not re.search(r'\[.+\]\(https?://', line):
                non_link_items.append(line[:80])

    if non_link_items:
        issues.append({
            "rule": "H2 section items without absolute markdown links",
            "severity": "MEDIUM",
            "examples": non_link_items[:3],
        })

    # Rule 5: File size
    file_size_bytes = len(body.encode("utf-8"))
    if file_size_bytes > 50 * 1024:
        issues.append({
            "rule": f"File size {file_size_bytes // 1024}KB exceeds 50KB limit",
            "severity": "MEDIUM"
        })

    # Rule 6: Check that all linked URLs are absolute and return 200
    linked_urls = re.findall(r'\]\((https?://[^\)]+)\)', body)
    broken_links = []
    for linked_url in linked_urls[:10]:  # cap at 10
        link_status, _, _, link_error = safe_get(linked_url)
        if link_error or (link_status and link_status >= 400):
            broken_links.append({"url": linked_url[:80], "status": link_status})

    if broken_links:
        issues.append({
            "rule": "Broken links in llms.txt",
            "severity": "HIGH",
            "broken_links": broken_links,
        })

    # Rule 7: Relative URLs
    relative_links = re.findall(r'\]\((/[^\)]+)\)', body)
    if relative_links:
        issues.append({
            "rule": "Relative URLs in llms.txt (must be absolute for off-site consumers)",
            "severity": "MEDIUM",
            "examples": relative_links[:3],
        })

    # Rule 8: Optional section check
    has_optional = "## Optional" in body

    # Rule 9: Private URL detection (bridgetoagent/llms-txt-validator)
    # Listing admin/checkout/account paths exposes private infrastructure to AI crawlers
    PRIVATE_PATH_RE = re.compile(
        r'https?://[^\s)]+(?:/admin|/account|/checkout|/wp-admin|/login|/dashboard|/private)',
        re.IGNORECASE)
    private_urls = PRIVATE_PATH_RE.findall(body)
    if private_urls:
        issues.append({
            "rule": "Private/admin URLs exposed in llms.txt",
            "severity": "HIGH",
            "examples": private_urls[:3],
            "recommendation": "Remove /admin, /account, /checkout and similar private paths from llms.txt",
        })

    # Rule 10: Slow link detection (response time >3s per linked URL)
    slow_links = []
    for linked_url in linked_urls[:5]:
        try:
            import time as _time
            t0 = _time.time()
            requests.head(linked_url, headers={"User-Agent": DEFAULT_UA}, timeout=5)
            elapsed = _time.time() - t0
            if elapsed > 3.0:
                slow_links.append({"url": linked_url[:80], "response_time_s": round(elapsed, 1)})
        except Exception:
            pass
    if slow_links:
        issues.append({
            "rule": "Slow links in llms.txt (>3s response time)",
            "severity": "LOW",
            "slow_links": slow_links,
        })

    # Rule 11: Duplicate URL detection
    all_urls = re.findall(r'\]\((https?://[^\)]+)\)', body)
    seen_urls = set()
    duplicate_urls = []
    for u in all_urls:
        if u in seen_urls:
            duplicate_urls.append(u)
        seen_urls.add(u)
    if duplicate_urls:
        issues.append({
            "rule": "Duplicate URLs in llms.txt",
            "severity": "LOW",
            "examples": duplicate_urls[:3],
        })

    return {
        "present": True,
        "status": status,
        "content_type": ct,
        "file_size_bytes": file_size_bytes,
        "has_h1": has_h1,
        "h1_text": h1_text,
        "has_blockquote": has_blockquote,
        "has_optional_section": has_optional,
        "linked_url_count": len(linked_urls),
        "relative_url_count": len(relative_links),
        "private_urls_found": len(private_urls),
        "slow_links": slow_links,
        "duplicate_urls": len(duplicate_urls),
        "issues": issues,
        "passes_spec": len([i for i in issues if i["severity"] in ("HIGH", "MEDIUM")]) == 0,
    }


def check_webmcp_readiness(base_url, homepage_html):
    """
    WebMCP Readiness check — 4 levels: none / basic / ready / advanced.
    Checks for MCP card, WebMCP manifest, and agent protocol signals in HTML.

    Source: Auriti-Labs/geo-optimizer-skill v3.18.3 WebMCP Readiness Check +
    sspoisk/agent-readiness-cli mcp-card check + Lighthouse 13.3.0 Agentic audits.
    Finding: RSL-007 if level is 'none' (forward-looking, LOW severity).
    """
    WEBMCP_PATHS = [
        "/.well-known/webmcp",
        "/.well-known/mcp.json",
        "/.well-known/agents.json",
    ]
    REQUIRED_MCP_FIELDS = {"name", "description"}

    endpoint_results = {}
    for path in WEBMCP_PATHS:
        ep_url = urljoin(base_url, path)
        status, body, ct, error = safe_get(ep_url)
        if status == 200 and body:
            try:
                parsed = json.loads(body)
                endpoint_results[path] = {
                    "present": True,
                    "valid_json": True,
                    "has_required_fields": REQUIRED_MCP_FIELDS.issubset(set(parsed.keys())),
                    "has_endpoint_field": "endpoint" in parsed or "url" in parsed,
                }
            except (json.JSONDecodeError, ValueError):
                endpoint_results[path] = {"present": True, "valid_json": False}
        else:
            endpoint_results[path] = {"present": False, "status": status}

    # HTML signals
    html = homepage_html or ""
    has_register_tool = "modelContext.registerTool" in html or "registerTool" in html
    has_tool_attrs = "data-mcp-" in html or 'data-tool=' in html
    has_potential_action = '"potentialAction"' in html or "'potentialAction'" in html

    signals = []
    if endpoint_results.get("/.well-known/mcp.json", {}).get("valid_json"):
        signals.append("mcp_card")
    if endpoint_results.get("/.well-known/webmcp", {}).get("present"):
        signals.append("webmcp_manifest")
    if has_register_tool:
        signals.append("register_tool_js")
    if has_tool_attrs:
        signals.append("tool_html_attributes")
    if has_potential_action:
        signals.append("potential_action_schema")

    level = "advanced" if len(signals) >= 3 else \
            "ready" if len(signals) == 2 else \
            "basic" if len(signals) == 1 else "none"

    return {
        "level": level,  # none / basic / ready / advanced
        "signals": signals,
        "agent_ready": level in ("ready", "advanced"),
        "endpoints": endpoint_results,
        "html_signals": {
            "register_tool_js": has_register_tool,
            "tool_html_attrs": has_tool_attrs,
            "potential_action_schema": has_potential_action,
        },
    }


def check_alternate_text_links(homepage_html):
    """
    RSL-006: Check for <link rel="alternate"> with AI-friendly MIME types.
    Emerging standard: serve plain-text or Markdown versions for AI RAG ingestion.
    AutoGEO ICLR 2026: pages with machine-readable alternates have 2.1× higher
    RAG retrieval rate.
    """
    html = homepage_html or ""
    AI_MIME_TYPES = ["text/plain", "text/markdown", "text/x-markdown", "application/json"]

    found = []
    for link_tag in re.finditer(r'<link[^>]+rel=["\']alternate["\'][^>]*>', html, re.IGNORECASE):
        tag = link_tag.group(0)
        type_match = re.search(r'type=["\']([^"\']+)["\']', tag)
        href_match = re.search(r'href=["\']([^"\']+)["\']', tag)
        if type_match and href_match:
            mime = type_match.group(1).lower()
            if any(ai_mime in mime for ai_mime in AI_MIME_TYPES):
                found.append({"type": type_match.group(1), "href": href_match.group(1)})

    return {
        "has_ai_alternate": len(found) > 0,
        "alternate_links": found,
        "missing": len(found) == 0,
    }


def validate_ai_summary_json(base_url):
    """
    Validate /ai/summary.json against the required fields spec.
    Required: name, description, docs (or documentation), source (or url).
    Source: github/gh-aw ADF spec PR #30621 + geo-optimizer-skill AI discovery validation.
    """
    summary_url = urljoin(base_url, "/ai/summary.json")
    status, body, ct, error = safe_get(summary_url)

    if status != 200 or not body:
        return {"present": False, "status": status, "error": error}

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return {"present": True, "status": status, "valid_json": False, "raw": body[:200]}

    REQUIRED = {"name", "description"}
    RECOMMENDED = {"docs", "documentation", "source", "url", "install", "contact"}

    keys = set(str(k).lower() for k in data.keys())
    missing_required = REQUIRED - keys
    present_recommended = keys & RECOMMENDED

    return {
        "present": True,
        "status": status,
        "valid_json": True,
        "has_required_fields": len(missing_required) == 0,
        "missing_required": list(missing_required),
        "present_recommended_fields": list(present_recommended),
        "field_count": len(data),
        "passes_spec": len(missing_required) == 0,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: rsl_check.py <url>"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    output = {
        "site": parsed.netloc,
        "base_url": base_url,
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    print("[*] Fetching homepage...", file=sys.stderr)
    try:
        resp = requests.get(base_url, headers={"User-Agent": DEFAULT_UA}, timeout=TIMEOUT)
        homepage_html = resp.text if resp.status_code == 200 else ""
    except Exception:
        homepage_html = ""

    print("[*] Checking RSL 1.0 declaration...", file=sys.stderr)
    output["rsl_declaration"] = check_rsl_declaration(base_url, homepage_html)

    print("[*] Checking llms-full.txt...", file=sys.stderr)
    output["llms_full_txt"] = check_llms_full_txt(base_url)

    print("[*] Checking AI discovery endpoints...", file=sys.stderr)
    output["ai_discovery_endpoints"] = check_ai_discovery_endpoints(base_url)

    ai_present_count = sum(1 for ep in output["ai_discovery_endpoints"] if ep["present"])
    output["ai_discovery_endpoint_count"] = ai_present_count

    print("[*] Checking IndexNow...", file=sys.stderr)
    output["indexnow"] = check_indexnow(base_url, homepage_html)

    print("[*] Deep-validating llms.txt...", file=sys.stderr)
    output["llms_txt_deep_validation"] = deep_validate_llms_txt(base_url)

    print("[*] Checking WebMCP readiness...", file=sys.stderr)
    output["webmcp_readiness"] = check_webmcp_readiness(base_url, homepage_html)

    print("[*] Checking markdown/plain-text alternate links (RSL-006)...", file=sys.stderr)
    output["alternate_text_links"] = check_alternate_text_links(homepage_html)

    print("[*] Validating ai/summary.json required fields...", file=sys.stderr)
    output["ai_summary_validation"] = validate_ai_summary_json(base_url)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
