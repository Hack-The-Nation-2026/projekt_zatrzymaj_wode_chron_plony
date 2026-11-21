"""Pobieranie danych z prostą pamięcią podręczną na dysku.

Każda odpowiedź jest zapisywana w katalogu .cache/http, więc raz przeliczona
działka działa potem także bez internetu (ważne na demo).
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

CACHE_DIR = Path(os.environ.get("WODNIK_CACHE", Path(__file__).resolve().parent.parent / ".cache" / "http"))
OFFLINE = os.environ.get("WODNIK_OFFLINE") == "1"
USER_AGENT = "wodnik-prototyp/0.1 (HackNation 2026)"


class DataSourceError(RuntimeError):
    """Źródło danych nie odpowiedziało lub zwróciło błąd."""


def _cache_path(url: str) -> Path:
    return CACHE_DIR / hashlib.sha1(url.encode("utf-8")).hexdigest()


def get_bytes(base: str, params: dict | None = None, timeout: int = 90, retries: int = 2) -> bytes:
    url = base + ("?" + urlencode(params, safe="(),:") if params else "")
    path = _cache_path(url)
    if path.exists():
        return path.read_bytes()
    if OFFLINE:
        raise DataSourceError(f"Brak danych w pamięci podręcznej (tryb offline): {base}")

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 200:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                path.write_bytes(resp.content)
                return resp.content
            last_err = DataSourceError(f"{base} zwrócił HTTP {resp.status_code}: {resp.text[:200]}")
        except requests.RequestException as exc:  # sieć, timeout
            last_err = exc
        time.sleep(1.5 * (attempt + 1))
    raise DataSourceError(f"Nie udało się pobrać danych z {base}: {last_err}")


def get_text(base: str, params: dict | None = None, **kw) -> str:
    return get_bytes(base, params, **kw).decode("utf-8")


def get_json(base: str, params: dict | None = None, **kw):
    import json

    return json.loads(get_text(base, params, **kw))
