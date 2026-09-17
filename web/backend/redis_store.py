"""
redis_store.py — Redis (or in-memory fallback) is the GEOReady database.

Users persist with no TTL:
  geo:user:email:{email} → user JSON
  geo:user:id:{user_id}  → email

Jobs persist per account so one user can keep many websites:
  geo:job:{job_id}:status|url|progress|report|error|user|meta
  geo:user:{user_id}:jobs → JSON list of job ids, newest first
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
TTL = 3600  # leftover for any short-lived keys; user jobs do not expire
MAX_USER_JOBS = 80

# In-memory fallback so local demo works without Redis/Upstash.
_memory: dict[str, tuple[str, float]] = {}
_use_memory = False
_client: Any = None


class _MemoryRedis:
    """Minimal Redis-compatible store used when Redis is unreachable."""

    def ping(self) -> bool:
        return True

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        expires = time.time() + ex if ex is not None else float("inf")
        _memory[key] = (value, expires)

    def get(self, key: str) -> str | None:
        item = _memory.get(key)
        if not item:
            return None
        value, expires = item
        if time.time() > expires:
            _memory.pop(key, None)
            return None
        return value

    def pipeline(self):
        return _MemoryPipeline(self)


class _MemoryPipeline:
    def __init__(self, store: _MemoryRedis):
        self.store = store
        self.ops: list[tuple] = []

    def set(self, key: str, value: str, ex: int | None = None):
        self.ops.append((key, value, ex))
        return self

    def execute(self):
        for key, value, ex in self.ops:
            self.store.set(key, value, ex=ex)
        self.ops.clear()


def get_client():
    global _client, _use_memory
    if _client is not None:
        return _client
    try:
        import redis
        client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        _client = client
        print("✅ Using Redis at", REDIS_URL)
        return _client
    except Exception as e:
        _use_memory = True
        _client = _MemoryRedis()
        print(f"⚠️  Redis unavailable ({e}); using in-memory job store")
        return _client

SKILLS = [
    "crawlability",
    "render",
    "schema",
    "entity",
    "content",
    "eeeat",
    "engagement",
    "rsl",
    "opengraph",
    "technical",
]

SKILL_LABELS = {
    "crawlability": "Crawlability Probe",
    "render": "Render Gap Detector",
    "schema": "Structured Data Auditor",
    "entity": "Entity Corroboration",
    "content": "Content Extractability",
    "eeeat": "E-E-A-T Signals",
    "engagement": "Engagement Analyzer",
    "rsl": "RSL Licensing Checker",
    "opengraph": "OpenGraph Auditor",
    "technical": "Technical SEO Probe",
}


def domain_from_url(url: str) -> str:
    try:
        host = urlparse(url if "://" in url else f"https://{url}").hostname or url
        return host.replace("www.", "")
    except Exception:
        return (url or "").replace("www.", "")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_meta(job_id: str, **fields: Any) -> None:
    r = get_client()
    key = f"geo:job:{job_id}:meta"
    raw = r.get(key)
    meta = json.loads(raw) if raw else {"job_id": job_id}
    meta.update({k: v for k, v in fields.items() if v is not None})
    meta["job_id"] = job_id
    r.set(key, json.dumps(meta))


def add_user_job(user_id: str, job_id: str) -> None:
    r = get_client()
    key = f"geo:user:{user_id}:jobs"
    raw = r.get(key)
    ids = json.loads(raw) if raw else []
    ids = [job_id] + [i for i in ids if i != job_id]
    r.set(key, json.dumps(ids[:MAX_USER_JOBS]))


def init_job(job_id: str, url: str, user_id: str | None = None) -> None:
    r = get_client()
    domain = domain_from_url(url)
    created = _now()
    pipe = r.pipeline()
    pipe.set(f"geo:job:{job_id}:status", "queued")
    pipe.set(f"geo:job:{job_id}:url", url)
    pipe.set(f"geo:job:{job_id}:progress", json.dumps({s: "pending" for s in SKILLS}))
    if user_id:
        pipe.set(f"geo:job:{job_id}:user", user_id)
    pipe.execute()
    _write_meta(
        job_id,
        url=url,
        domain=domain,
        status="queued",
        user_id=user_id,
        created_at=created,
        score=None,
        findings=None,
    )
    if user_id:
        add_user_job(user_id, job_id)


def set_status(job_id: str, status: str) -> None:
    r = get_client()
    r.set(f"geo:job:{job_id}:status", status)
    _write_meta(job_id, status=status)


def set_skill_status(job_id: str, skill: str, status: str) -> None:
    r = get_client()
    key = f"geo:job:{job_id}:progress"
    raw = r.get(key)
    progress = json.loads(raw) if raw else {s: "pending" for s in SKILLS}
    progress[skill] = status
    r.set(key, json.dumps(progress))


def set_report(job_id: str, report: dict) -> None:
    r = get_client()
    r.set(f"geo:job:{job_id}:report", json.dumps(report))
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    url = r.get(f"geo:job:{job_id}:url") or ""
    _write_meta(
        job_id,
        status="done",
        domain=(report.get("site") or domain_from_url(url)).replace("www.", ""),
        url=url,
        score=report.get("overall_score"),
        findings=summary.get("total_findings"),
    )


def set_error(job_id: str, error: str) -> None:
    r = get_client()
    pipe = r.pipeline()
    pipe.set(f"geo:job:{job_id}:status", "error")
    pipe.set(f"geo:job:{job_id}:error", error)
    pipe.execute()
    _write_meta(job_id, status="error")


def get_job_state(job_id: str) -> dict | None:
    r = get_client()
    status = r.get(f"geo:job:{job_id}:status")
    if status is None:
        return None
    progress_raw = r.get(f"geo:job:{job_id}:progress")
    report_raw = r.get(f"geo:job:{job_id}:report")
    error = r.get(f"geo:job:{job_id}:error")
    url = r.get(f"geo:job:{job_id}:url")
    owner = r.get(f"geo:job:{job_id}:user")

    progress = json.loads(progress_raw) if progress_raw else {}
    done_count = sum(1 for v in progress.values() if v == "done")

    return {
        "job_id": job_id,
        "status": status,
        "url": url,
        "user_id": owner,
        "progress": progress,
        "skill_labels": SKILL_LABELS,
        "done_count": done_count,
        "total_count": len(SKILLS),
        "report": json.loads(report_raw) if report_raw else None,
        "error": error,
    }


def get_job_summary(job_id: str) -> dict | None:
    r = get_client()
    status = r.get(f"geo:job:{job_id}:status")
    if status is None:
        return None
    raw = r.get(f"geo:job:{job_id}:meta")
    if raw:
        meta = json.loads(raw)
        meta["status"] = status
        return meta
    url = r.get(f"geo:job:{job_id}:url") or ""
    report_raw = r.get(f"geo:job:{job_id}:report")
    report = json.loads(report_raw) if report_raw else {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "job_id": job_id,
        "url": url,
        "domain": (report.get("site") or domain_from_url(url)).replace("www.", ""),
        "status": status,
        "score": report.get("overall_score"),
        "findings": summary.get("total_findings"),
        "created_at": None,
    }


def list_user_sites(user_id: str) -> list[dict]:
    r = get_client()
    raw = r.get(f"geo:user:{user_id}:jobs")
    ids = json.loads(raw) if raw else []
    sites: list[dict] = []
    seen: set[str] = set()
    for job_id in ids:
        summary = get_job_summary(job_id)
        if not summary:
            continue
        domain = (summary.get("domain") or "").lower()
        if not domain or domain in seen:
            continue
        seen.add(domain)
        sites.append(summary)
    return sites


# ── Users (no TTL) ─────────────────────────────────────────────────────────

def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name") or "",
        "created_at": user.get("created_at"),
    }


def create_user(email: str, password_hash: str, name: str = "") -> dict | None:
    r = get_client()
    key = f"geo:user:email:{email}"
    if r.get(key):
        return None
    import uuid
    from datetime import datetime, timezone

    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    r.set(key, json.dumps(user))
    r.set(f"geo:user:id:{user['id']}", email)
    return user


def get_user_by_email(email: str) -> dict | None:
    r = get_client()
    raw = r.get(f"geo:user:email:{email}")
    return json.loads(raw) if raw else None


def get_user_by_id(user_id: str) -> dict | None:
    r = get_client()
    email = r.get(f"geo:user:id:{user_id}")
    if not email:
        return None
    return get_user_by_email(email)


def public_user(user: dict) -> dict:
    return _public_user(user)
