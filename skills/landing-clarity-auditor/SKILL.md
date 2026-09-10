---
name: landing-clarity-auditor
description: Audits the first-5-second landing experience for AI-referred visitors. Checks H1 presence and conciseness (RC24), navigation item count against Miller's Law max of 7 (RC25), above-fold CTA density (RC28), and AI-referrer handling signals such as utm_source detection, document.referrer logic, or a dedicated /from/ai page (RC30). Use after crawlability-probe and before report generation to surface engagement-layer gaps.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# Landing Clarity Auditor

## When to use

Run after crawlability confirms the site is reachable. Targets the engagement dimension — specifically why AI-referred visitors bounce within the first 5 seconds.

## Output

Returns `findings[]` (RC24, RC25, RC28, RC30 IDs) and `checks{}` with raw signal data.
