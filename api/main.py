"""Serwer HTTP Wodnika (FastAPI). Opis endpointów: docs/API.md.

Uruchomienie:
    .venv/bin/uvicorn api.main:app --reload --port 8000
Interfejs: http://localhost:8000/   Dokumentacja OpenAPI: http://localhost:8000/docs
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from wodnik import __version__, analysis, crops, output, parcel
from wodnik.http import OFFLINE, DataSourceError

from . import accounts, chat

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

PARCEL_ID_RE = re.compile(r"^\d{6}_\d\.\d{4}(\.[\w/-]+){1,2}$")
POLAND_BBOX = (14.0, 49.0, 24.2, 55.0)  # lon_min, lat_min, lon_max, lat_max

app = FastAPI(title="Wodnik API", version=__version__,
              description="Analiza sytuacji wodnej działki rolnej (HackNation 2026, zadanie KOWR).")
app.add_middleware(CORSMiddleware, allow_origins=[os.environ.get("WODNIK_CORS_ORIGIN", "*")],
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])

_executor = ThreadPoolExecutor(max_workers=2)
_jobs: dict[str, dict] = {}
_by_key: dict[str, str] = {}
_lock = threading.Lock()


# --- pomocnicze -----------------------------------------------------------------

def _err(status: int, code: str, message: str, hint: str | None = None):
    raise HTTPException(status_code=status, detail={"code": code, "message": message, "hint": hint})


@app.exception_handler(HTTPException)
async def _http_error(_, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


def _clean(obj):
    """JSON nie zna NaN/Infinity: zamieniamy je na null."""
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def _in_poland(lat: float, lon: float) -> bool:
    return POLAND_BBOX[0] <= lon <= POLAND_BBOX[2] and POLAND_BBOX[1] <= lat <= POLAND_BBOX[3]


def _error_from(exc: Exception) -> dict:
    msg = str(exc)
    if "nie znalazł działki" in msg:
        return {"code": "PARCEL_NOT_FOUND", "message": "Nie znaleziono działki.", "hint": "Dotknij działki na mapie."}
    if "za duża" in msg:
        return {"code": "PARCEL_TOO_LARGE", "message": msg, "hint": "Wybierz mniejszą działkę."}
    if "HTTP 429" in msg:
        return {"code": "SOURCE_RATE_LIMITED",
                "message": "Serwis z danymi pogodowymi chwilowo odrzuca zapytania (przekroczony limit darmowego planu).",
                "hint": "Spróbuj później albo wybierz przykładową działkę (działa z zapisanych danych)."}
    if isinstance(exc, ValueError):
        return {"code": "INVALID_INPUT", "message": msg}
    if isinstance(exc, DataSourceError):
        return {"code": "SOURCE_UNAVAILABLE", "message": msg}
    return {"code": "INTERNAL", "message": "Nieoczekiwany błąd analizy."}


# --- modele wejścia ----------------------------------------------------------------

class Point(BaseModel):
    lat: float
    lon: float


class AnalysisRequest(BaseModel):
    parcel_id: Optional[str] = Field(None, examples=["101609_2.0011.352"])
    point: Optional[Point] = None
    date: Optional[dt.date] = None  # pole nazywa się jak typ, więc typ podajemy przez moduł
    crop: str = "pszenica_ozima"

    @field_validator("parcel_id")
    @classmethod
    def _pid(cls, v):
        if v is not None and not PARCEL_ID_RE.match(v.strip()):
            raise ValueError("Nieprawidłowy identyfikator działki (np. 101609_2.0011.352).")
        return v.strip() if v else v

    @field_validator("crop")
    @classmethod
    def _crop(cls, v):
        if v not in crops.CROPS:
            raise ValueError(f"Nieznana uprawa. Dostępne: {', '.join(crops.CROPS)}")
        return v

    @field_validator("date")
    @classmethod
    def _date(cls, v):
        if v is not None and not (date(1995, 3, 1) <= v <= date.today() + timedelta(days=7)):
            raise ValueError("Data musi być między 1995 a dniem dzisiejszym + 7 dni.")
        return v

    @model_validator(mode="after")
    def _where(self):
        if not self.parcel_id and not self.point:
            raise ValueError("Podaj parcel_id albo point.")
        if self.point and not _in_poland(self.point.lat, self.point.lon):
            raise ValueError("Punkt leży poza Polską.")
        return self


# --- konta użytkowników ---------------------------------------------------------------

accounts.init()


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=254, examples=["jan@example.com"])
    password: str = Field(..., max_length=200)
    name: Optional[str] = Field(None, max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=200)


def _bearer(authorization: Optional[str]) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    return accounts.user_for_token(_bearer(authorization))


def current_user(user: Optional[dict] = Depends(current_user_optional)) -> dict:
    if not user:
        _err(401, "UNAUTHORIZED", "Zaloguj się, aby zobaczyć tę stronę.")
    return user


def _account_error(exc: accounts.AccountError):
    status = {"EMAIL_TAKEN": 409, "BAD_CREDENTIALS": 401}.get(exc.code, 400)
    _err(status, exc.code, str(exc))


@app.post("/api/v1/auth/register", status_code=201)
def register(req: RegisterRequest, request: Request):
    if _rate_limited("auth:" + (request.client.host if request.client else "?")):
        _err(429, "RATE_LIMITED", "Za dużo prób w krótkim czasie.", "Spróbuj ponownie za minutę.")
    try:
        accounts.register(req.email, req.password, req.name)
        token, user = accounts.login(req.email, req.password)
    except accounts.AccountError as exc:
        _account_error(exc)
    return {"token": token, "user": user}


@app.post("/api/v1/auth/login")
def login(req: LoginRequest, request: Request):
    if _rate_limited("auth:" + (request.client.host if request.client else "?")):
        _err(429, "RATE_LIMITED", "Za dużo prób logowania.", "Spróbuj ponownie za minutę.")
    try:
        token, user = accounts.login(req.email, req.password)
    except accounts.AccountError as exc:
        _account_error(exc)
    return {"token": token, "user": user}


@app.post("/api/v1/auth/logout", status_code=204)
def logout(authorization: Optional[str] = Header(None)):
    token = _bearer(authorization)
    if token:
        accounts.logout(token)


@app.get("/api/v1/me")
def me(user: dict = Depends(current_user)):
    return {**user, "reports_count": len(accounts.list_reports(user["id"], limit=10_000))}


@app.get("/api/v1/me/reports")
def my_reports(user: dict = Depends(current_user)):
    return accounts.list_reports(user["id"])


def _my_report(user: dict, report_id: int) -> dict:
    r = accounts.get_report(user["id"], report_id)
    if not r:
        _err(404, "NOT_FOUND", "Nie ma takiego raportu w Twojej historii.")
    return r


@app.get("/api/v1/me/reports/{report_id}")
def my_report(report_id: int, user: dict = Depends(current_user)):
    return _my_report(user, report_id)


@app.get("/api/v1/me/reports/{report_id}/raport", response_class=HTMLResponse)
def my_report_html(report_id: int, user: dict = Depends(current_user)):
    return HTMLResponse(output.html_report(_my_report(user, report_id)["report"]))


@app.delete("/api/v1/me/reports/{report_id}", status_code=204)
def delete_my_report(report_id: int, user: dict = Depends(current_user)):
    if not accounts.delete_report(user["id"], report_id):
        _err(404, "NOT_FOUND", "Nie ma takiego raportu w Twojej historii.")


@app.post("/api/v1/me/reports", status_code=201)
def save_to_history(body: dict, user: dict = Depends(current_user)):
    """Ręczne dopisanie gotowej analizy (np. działki demo) do historii: {"analysis_id": "..."}."""
    job = _jobs.get(str(body.get("analysis_id", "")))
    if not job or job["status"] != "done":
        _err(404, "NOT_FOUND", "Analiza nie istnieje lub jeszcze trwa.")
    return {"id": accounts.save_report(user["id"], job["id"], job["report"])}


def _save_for_owners(job: dict) -> None:
    for uid in list(job.get("owners", ())):
        try:
            accounts.save_report(uid, job["id"], job["report"])
        except Exception:  # historia nie może zepsuć samej analizy
            pass


# --- asystent (czat) ----------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=40)
    analysis_id: Optional[str] = Field(None, max_length=80)  # wynik z bieżącej sesji serwera
    report_id: Optional[int] = None  # albo raport z historii zalogowanego użytkownika


@app.post("/api/v1/chat")
def chat_reply(req: ChatRequest, request: Request, user: Optional[dict] = Depends(current_user_optional)):
    """Asystent z radami; gdy podano analizę lub raport z historii, odpowiada na jego podstawie."""
    if _rate_limited("chat:" + (request.client.host if request.client else "?")):
        _err(429, "RATE_LIMITED", "Za dużo pytań w krótkim czasie.", "Spróbuj ponownie za minutę.")
    report = None
    if req.report_id is not None:
        if not user:
            _err(401, "UNAUTHORIZED", "Zaloguj się, aby rozmawiać o raporcie z historii.")
        report = _my_report(user, req.report_id)["report"]
    elif req.analysis_id:
        job = _jobs.get(req.analysis_id)
        if not job or job["status"] != "done":
            _err(404, "NOT_FOUND", "Analiza nie istnieje lub jeszcze trwa.")
        report = job["report"]
    try:
        text, source = chat.reply([m.model_dump() for m in req.messages], report)
    except ValueError as exc:
        _err(400, "INVALID_INPUT", str(exc))
    return {"reply": text, "source": source, "model": chat.MODEL if source == "ai" else None}


# --- endpointy ----------------------------------------------------------------------

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": __version__, "offline_mode": OFFLINE, "jobs": len(_jobs),
            "chat_ai": bool(os.environ.get("OPENAI_API_KEY"))}


@app.get("/api/v1/crops")
def list_crops():
    return [{"key": c.key, "name": c.name, "critical_label": c.critical_label} for c in crops.CROPS.values()]


def _parcel_json(p: parcel.Parcel) -> dict:
    lat, lon = p.centroid_latlon
    return {"id": p.id, "commune": p.commune, "region": p.region, "county": p.county,
            "voivodeship": p.voivodeship, "area_ha": round(p.area_ha, 2),
            "center": {"lat": round(lat, 6), "lon": round(lon, 6)},
            "geometry": p.geom_wgs84.__geo_interface__}


@app.get("/api/v1/parcels/resolve")
def resolve_parcel(lat: float, lon: float):
    if not _in_poland(lat, lon):
        _err(400, "INVALID_INPUT", "Punkt leży poza Polską.")
    try:
        return _clean(_parcel_json(parcel.by_point(lat, lon)))
    except DataSourceError as exc:
        e = _error_from(exc)
        _err(404 if e["code"] == "PARCEL_NOT_FOUND" else 502, e["code"], e["message"], e.get("hint"))


@app.get("/api/v1/parcels/by-id")
def parcel_by_id(id: str):
    if not PARCEL_ID_RE.match(id.strip()):
        _err(400, "INVALID_INPUT", "Nieprawidłowy identyfikator działki (np. 101609_2.0011.352).")
    try:
        return _clean(_parcel_json(parcel.by_id(id)))
    except DataSourceError as exc:
        e = _error_from(exc)
        _err(404 if e["code"] == "PARCEL_NOT_FOUND" else 502, e["code"], e["message"], e.get("hint"))


def _run(job_id: str, req: AnalysisRequest) -> None:
    job = _jobs[job_id]

    def progress(step: str, state: str = "running") -> None:
        # Etapy pobierania danych biegną równolegle, więc każdy etap ma własny stan.
        for s in job["progress"]:
            if s["step"] == step:
                s["state"] = state

    t0 = time.time()
    try:
        rep = analysis.analyse(parcel_id=req.parcel_id,
                               point=(req.point.lat, req.point.lon) if req.point else None,
                               on=req.date, crop_key=req.crop, progress=progress)
        for s in job["progress"]:
            if s["state"] != "failed":  # źródło pominięte (brak czasu lub błąd) zostaje oznaczone
                s["state"] = "done"
        job["report_obj"] = rep
        job["report"] = _clean(rep.to_dict())
        job["meta"] = {"computed_ms": int((time.time() - t0) * 1000)}
        job["status"] = "done"
        _save_for_owners(job)
    except Exception as exc:  # błąd trafia do klienta w ustalonym formacie
        job["status"] = "failed"
        job["error"] = _error_from(exc)
        for s in job["progress"]:
            if s["state"] == "running":
                s["state"] = "failed"


RATE_LIMIT_PER_MIN = int(os.environ.get("WODNIK_RATE_LIMIT", "20"))
MAX_JOBS = 300
_hits: dict[str, list] = {}


def _rate_limited(ip: str) -> bool:
    """Prosty limit nowych analiz na adres IP (chroni też limity zewnętrznych źródeł danych)."""
    now = time.time()
    hits = [t for t in _hits.get(ip, []) if now - t < 60]
    _hits[ip] = hits
    if len(hits) >= RATE_LIMIT_PER_MIN:
        return True
    hits.append(now)
    return False


def _prune_jobs() -> None:
    """Pamięć serwera: zostawiamy najnowsze zadania (działki demo zostają zawsze)."""
    finished = sorted((j for j in _jobs.values() if not j.get("demo") and j["status"] != "running"),
                      key=lambda j: j["created"])
    for j in finished[: max(0, len(_jobs) - MAX_JOBS)]:
        _jobs.pop(j["id"], None)
        for k, v in list(_by_key.items()):
            if v == j["id"]:
                _by_key.pop(k, None)


@app.post("/api/v1/analyses", status_code=202)
def start_analysis(req: AnalysisRequest, request: Request,
                   user: Optional[dict] = Depends(current_user_optional)):
    """Zalogowany użytkownik (nagłówek Authorization: Bearer) dostaje wynik także w swojej historii."""
    on = req.date or date.today()
    key = hashlib.sha1(f"{req.parcel_id}|{req.point}|{on}|{req.crop}".encode()).hexdigest()
    with _lock:
        existing = _by_key.get(key)
        if existing and _jobs[existing]["status"] in ("running", "done"):
            job = _jobs[existing]
            if user:
                job.setdefault("owners", set()).add(user["id"])
                if job["status"] == "done":
                    accounts.save_report(user["id"], job["id"], job["report"])
            return {"id": existing, "status": _jobs[existing]["status"],
                    "poll_url": f"/api/v1/analyses/{existing}"}
        if _rate_limited(request.client.host if request.client else "?"):
            _err(429, "RATE_LIMITED", "Za dużo analiz w krótkim czasie.", "Spróbuj ponownie za minutę.")
        _prune_jobs()
        job_id = uuid.uuid4().hex[:10]
        _jobs[job_id] = {"id": job_id, "status": "running", "created": time.time(),
                         "progress": [{"step": k, "label": lbl, "state": "pending"} for k, lbl in analysis.STEPS],
                         "owners": {user["id"]} if user else set()}
        _by_key[key] = job_id
    _executor.submit(_run, job_id, req)
    return {"id": job_id, "status": "running", "poll_url": f"/api/v1/analyses/{job_id}"}


@app.get("/api/v1/analyses/{job_id}")
def get_analysis(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        _err(404, "NOT_FOUND", "Nie ma takiej analizy.")
    return {k: v for k, v in job.items() if k not in ("report_obj", "created", "geojson", "owners")}


@app.get("/api/v1/analyses/{job_id}/geojson")
def get_geojson(job_id: str):
    job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        _err(404, "NOT_FOUND", "Analiza nie istnieje lub jeszcze trwa.")
    return job.get("geojson") or _clean(output.geojson(job["report_obj"]))


@app.get("/api/v1/analyses/{job_id}/raport", response_class=HTMLResponse)
def get_report_html(job_id: str):
    """Raport do wydruku lub zapisu jako PDF (Ctrl+P → „Zapisz jako PDF”). Działa niezależnie od frontendu."""
    job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        _err(404, "NOT_FOUND", "Analiza nie istnieje lub jeszcze trwa.")
    return HTMLResponse(output.html_report(job["report"]))


# --- działki demo: gotowe wyniki z katalogu demo/, działają bez sieci i bez limitów API ---------

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"
_demos: list[dict] = []


def _load_demos() -> None:
    import json

    for f in sorted(DEMO_DIR.glob("*.json")) if DEMO_DIR.exists() else []:
        d = json.loads(f.read_text(encoding="utf-8"))
        rq = d["request"]
        job_id = "demo-" + f.stem
        gj = f.with_suffix(".geojson")
        _jobs[job_id] = {"id": job_id, "status": "done", "created": 0, "demo": True,
                         "progress": [{"step": k, "label": lbl, "state": "done"} for k, lbl in analysis.STEPS],
                         "report": d["report"], "meta": {"computed_ms": 0, "source": "demo"},
                         "geojson": json.loads(gj.read_text(encoding="utf-8")) if gj.exists() else None}
        _by_key[hashlib.sha1(f"{rq['parcel_id']}|None|{rq['date']}|{rq['crop']}".encode()).hexdigest()] = job_id
        _demos.append({"id": job_id, "title": d.get("title", f.stem), **rq})


_load_demos()


@app.get("/api/v1/demo")
def list_demos():
    return _demos


# Interfejsy webowe (statyczne pliki) – muszą być na końcu, bo przechwytują pozostałe ścieżki.
#  /prosty/ – prosty widok techniczny z mapą (web-simple/)
#  /        – główny interfejs React (web/dist/ po `npm run build`)
SIMPLE_DIR = WEB_DIR.parent / "web-simple"
DIST_DIR = WEB_DIR / "dist"
if SIMPLE_DIR.exists():
    app.mount("/prosty", StaticFiles(directory=SIMPLE_DIR, html=True), name="web-simple")
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="web")
elif SIMPLE_DIR.exists():
    app.mount("/", StaticFiles(directory=SIMPLE_DIR, html=True), name="web-fallback")
