"""
runner.py — Runs all 10 GEO audit skill scripts in parallel for a given URL.
Writes per-skill progress to Redis as each script completes.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from redis_store import set_skill_status, set_status, set_report, set_error, SKILLS

# Path to the skills directory (relative to this file's location)
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Adobe_Hack_2026/
SKILLS_DIR = BASE_DIR / "skills"
GENERATE_REPORT = BASE_DIR / "Research" / "generate_report.py"

SKILL_SCRIPTS = {
    "crawlability": SKILLS_DIR / "crawlability-probe" / "scripts" / "crawlability_check.py",
    "render":       SKILLS_DIR / "render-gap-detector" / "scripts" / "render_check.py",
    "schema":       SKILLS_DIR / "structured-data-auditor" / "scripts" / "schema_audit.py",
    "entity":       SKILLS_DIR / "entity-corroboration-checker" / "scripts" / "entity_check.py",
    "content":      SKILLS_DIR / "content-extractability-auditor" / "scripts" / "content_check.py",
    "eeeat":        SKILLS_DIR / "eeeat-signal-checker" / "scripts" / "eeeat_check.py",
    "engagement":   SKILLS_DIR / "engagement-analyzer" / "scripts" / "engagement_check.py",
    "rsl":          SKILLS_DIR / "rsl-licensing-checker" / "scripts" / "rsl_check.py",
    "opengraph":    SKILLS_DIR / "opengraph-meta-auditor" / "scripts" / "og_audit.py",
    "technical":    SKILLS_DIR / "technical-seo-probe" / "scripts" / "technical_check.py",
}

SKILL_OUTPUT_FILES = {
    "crawlability": "crawlability.json",
    "render":       "render.json",
    "schema":       "schema.json",
    "entity":       "entity.json",
    "content":      "content.json",
    "eeeat":        "eeeat.json",
    "engagement":   "engagement.json",
    "rsl":          "rsl.json",
    "opengraph":    "opengraph.json",
    "technical":    "technical.json",
}

PYTHON = sys.executable


def _extract_json(raw: str) -> dict | None:
    """Parse JSON even if a script printed progress logs before the payload."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None


async def run_skill(skill: str, url: str, output_dir: Path, job_id: str) -> bool:
    """Run a single skill script, write output to output_dir/<skill>.json."""
    script = SKILL_SCRIPTS[skill]
    out_file = output_dir / SKILL_OUTPUT_FILES[skill]

    set_skill_status(job_id, skill, "running")

    try:
        proc = await asyncio.create_subprocess_exec(
            PYTHON, str(script), url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        raw = stdout.decode(errors="replace").strip()
        data = _extract_json(raw)

        if data is not None:
            out_file.write_text(json.dumps(data))
            set_skill_status(job_id, skill, "done")
            return True
        else:
            set_skill_status(job_id, skill, "error")
            return False
    except (asyncio.TimeoutError, Exception):
        set_skill_status(job_id, skill, "error")
        return False


async def run_audit(job_id: str, url: str) -> None:
    """Run all 10 skills in parallel, then generate the unified report."""
    set_status(job_id, "running")

    with tempfile.TemporaryDirectory(prefix=f"geordy_{job_id}_") as tmpdir:
        output_dir = Path(tmpdir)

        # Run all 10 skills in parallel
        tasks = [run_skill(skill, url, output_dir, job_id) for skill in SKILLS]
        await asyncio.gather(*tasks)

        # Generate unified report
        try:
            proc = await asyncio.create_subprocess_exec(
                PYTHON, str(GENERATE_REPORT), str(output_dir),
                "--format", "json",
                "--output-dir", str(output_dir / "report"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(proc.communicate(), timeout=60)

            # Find the generated JSON report
            report_dir = output_dir / "report"
            json_files = list(report_dir.glob("*.json")) if report_dir.exists() else []

            if json_files:
                report = json.loads(json_files[0].read_text())
                set_report(job_id, report)
                set_status(job_id, "done")
            else:
                set_error(job_id, "Report generation produced no output file.")
        except Exception as e:
            set_error(job_id, f"Report generation failed: {e}")
