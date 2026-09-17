"""
main.py — GEOReady FastAPI backend
===================================
Endpoints:
  POST /api/auth/register  → { email, password, name? } → { access_token, user }
  POST /api/auth/login     → { email, password } → { access_token, user }
  GET  /api/auth/me        → current user (Bearer JWT)
  GET  /api/audits         → sites for the current user
  POST /api/audit          → { url } → { job_id }  (auth required)
  GET  /api/audit/{job_id} → job state + report when done
  GET  /health             → { ok: true }

Run:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import auth
import redis_store
from runner import run_audit

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        r = redis_store.get_client()
        r.ping()
        if redis_store._use_memory:
            print("⚠️  Using in-memory job store (Redis not running)")
        else:
            print("✅ Redis connected")
    except Exception as e:
        print(f"⚠️  Job store not available: {e}")
    yield


app = FastAPI(title="GEOReady API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response models ────────────────────────────────────────────────

class AuditRequest(BaseModel):
    url: str


class AuditResponse(BaseModel):
    job_id: str
    message: str


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str = ""
    created_at: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Helpers ────────────────────────────────────────────────────────────────

def normalise_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _token_payload(user: dict) -> dict:
    public = redis_store.public_user(user)
    return {
        "access_token": auth.create_token(user),
        "token_type": "bearer",
        "user": public,
    }


# ── Auth ───────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    email = auth.normalize_email(body.email)
    if not auth.valid_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    name = (body.name or "").strip() or email.split("@")[0]
    user = redis_store.create_user(email, auth.hash_password(body.password), name)
    if user is None:
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    return _token_payload(user)


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    email = auth.normalize_email(body.email)
    user = redis_store.get_user_by_email(email)
    if not user or not auth.verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_payload(user)


@app.get("/api/auth/me", response_model=UserOut)
async def me(user: dict = Depends(auth.get_current_user)):
    return user


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/api/audit", response_model=AuditResponse)
async def start_audit(
    body: AuditRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(auth.get_current_user),
):
    url = normalise_url(body.url)
    job_id = str(uuid.uuid4())

    redis_store.init_job(job_id, url, user["id"])

    background_tasks.add_task(_run_audit_task, job_id, url)

    return AuditResponse(
        job_id=job_id,
        message=f"Audit started for {url}. Poll /api/audit/{job_id} for status.",
    )


async def _run_audit_task(job_id: str, url: str):
    await run_audit(job_id, url)


@app.get("/api/audits")
async def list_audits(user: dict = Depends(auth.get_current_user)):
    return {"sites": redis_store.list_user_sites(user["id"])}


@app.get("/api/audit/{job_id}")
async def get_audit_status(job_id: str):
    state = redis_store.get_job_state(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    return state
