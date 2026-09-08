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
        "issues": issues,
        "passes_spec": len([i for i in issues if i["severity"] in ("HIGH", "MEDIUM")]) == 0,
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

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
