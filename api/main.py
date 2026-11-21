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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from wodnik import __version__, analysis, crops, output, parcel
from wodnik.http import OFFLINE, DataSourceError

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
PARCEL_ID_RE = re.compile(r"^\d{6}_\d\.\d{4}(\.[\w/-]+){1,2}$")
POLAND_BBOX = (14.0, 49.0, 24.2, 55.0)  # lon_min, lat_min, lon_max, lat_max

app = FastAPI(title="Wodnik API", version=__version__,
              description="Analiza sytuacji wodnej działki rolnej (HackNation 2026, zadanie KOWR).")
app.add_middleware(CORSMiddleware, allow_origins=[os.environ.get("WODNIK_CORS_ORIGIN", "*")],
                   allow_methods=["GET", "POST"], allow_headers=["*"])

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


# --- endpointy ----------------------------------------------------------------------

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": __version__, "offline_mode": OFFLINE, "jobs": len(_jobs)}


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

    def progress(step: str) -> None:
        for s in job["progress"]:
            if s["state"] == "running":
                s["state"] = "done"
            if s["step"] == step:
                s["state"] = "running"

    t0 = time.time()
    try:
        rep = analysis.analyse(parcel_id=req.parcel_id,
                               point=(req.point.lat, req.point.lon) if req.point else None,
                               on=req.date, crop_key=req.crop, progress=progress)
        for s in job["progress"]:
            s["state"] = "done"
        job["report_obj"] = rep
        job["report"] = _clean(rep.to_dict())
        job["meta"] = {"computed_ms": int((time.time() - t0) * 1000)}
        job["status"] = "done"
    except Exception as exc:  # błąd trafia do klienta w ustalonym formacie
        job["status"] = "failed"
        job["error"] = _error_from(exc)
        for s in job["progress"]:
            if s["state"] == "running":
                s["state"] = "failed"


@app.post("/api/v1/analyses", status_code=202)
def start_analysis(req: AnalysisRequest):
    on = req.date or date.today()
    key = hashlib.sha1(f"{req.parcel_id}|{req.point}|{on}|{req.crop}".encode()).hexdigest()
    with _lock:
        existing = _by_key.get(key)
        if existing and _jobs[existing]["status"] in ("running", "done"):
            return {"id": existing, "status": _jobs[existing]["status"],
                    "poll_url": f"/api/v1/analyses/{existing}"}
        job_id = uuid.uuid4().hex[:10]
        _jobs[job_id] = {"id": job_id, "status": "running", "created": time.time(),
                         "progress": [{"step": k, "label": lbl, "state": "pending"} for k, lbl in analysis.STEPS]}
        _by_key[key] = job_id
    _executor.submit(_run, job_id, req)
    return {"id": job_id, "status": "running", "poll_url": f"/api/v1/analyses/{job_id}"}


@app.get("/api/v1/analyses/{job_id}")
def get_analysis(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        _err(404, "NOT_FOUND", "Nie ma takiej analizy.")
    return {k: v for k, v in job.items() if k not in ("report_obj", "created", "geojson")}


@app.get("/api/v1/analyses/{job_id}/geojson")
def get_geojson(job_id: str):
    job = _jobs.get(job_id)
    if not job or job["status"] != "done":
        _err(404, "NOT_FOUND", "Analiza nie istnieje lub jeszcze trwa.")
    return job.get("geojson") or _clean(output.geojson(job["report_obj"]))


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


# Interfejs webowy (statyczne pliki) – musi być na końcu, bo przechwytuje wszystkie inne ścieżki.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
