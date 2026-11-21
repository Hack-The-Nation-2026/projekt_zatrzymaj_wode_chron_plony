"""Dane meteorologiczne i wilgotność gleby z Open-Meteo (reanaliza ERA5 / ERA5-Land).

- archive-api: dane historyczne (ok. 5 dni opóźnienia), 1940 → dziś
- api (forecast): ostatnie dni i prognoza 7 dni, gdy wybrana data jest świeża
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from .http import get_json

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_LAG_DAYS = 6
CLIMATE_YEARS = (1995, 2025)

DAILY = "precipitation_sum,et0_fao_evapotranspiration,temperature_2m_max"


@dataclass
class Series:
    dates: list
    precip: np.ndarray
    et0: np.ndarray
    tmax: np.ndarray
    soil_moisture: np.ndarray | None = None  # m³/m³, warstwa 0–100 cm
    sources: list = field(default_factory=list)


def _to_arr(values) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=float)


def _fetch(url: str, lat: float, lon: float, start: date, end: date, daily: str) -> dict:
    return get_json(url, {
        "latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}",
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": daily, "timezone": "Europe/Warsaw",
    })["daily"]


def daily_series(lat: float, lon: float, start: date, end: date, today: date | None = None) -> Series:
    """Szereg dzienny od start do end; świeże dni dociąga z API prognostycznego."""
    today = today or date.today()
    archive_end = min(end, today - timedelta(days=ARCHIVE_LAG_DAYS))
    parts, sources = [], []
    if start <= archive_end:
        parts.append(_fetch(ARCHIVE_URL, lat, lon, start, archive_end, DAILY + ",soil_moisture_0_to_100cm_mean"))
        sources.append("Open-Meteo archive (ERA5/ERA5-Land)")
    if end > archive_end:
        fstart = max(start, archive_end + timedelta(days=1))
        fend = min(end, today + timedelta(days=15))
        if fstart <= fend:
            parts.append(_fetch(FORECAST_URL, lat, lon, fstart, fend, DAILY + ",soil_moisture_0_to_100cm_mean"))
            sources.append("Open-Meteo forecast (modele numeryczne, w tym prognoza)")

    dates, p, e, t, sm = [], [], [], [], []
    for k, d in enumerate(parts):
        dates += d["time"]
        p += d["precipitation_sum"]
        e += d["et0_fao_evapotranspiration"]
        t += d["temperature_2m_max"]
        # Wilgotność gleby bierzemy tylko z reanalizy ERA5-Land: model prognostyczny ma inną
        # parametryzację gleby, więc jego wartości nie są porównywalne z tłem wieloletnim.
        from_archive = k == 0 and start <= archive_end
        sm += (d.get("soil_moisture_0_to_100cm_mean") if from_archive else None) or [None] * len(d["time"])
    return Series([date.fromisoformat(x) for x in dates], _to_arr(p), _to_arr(e), _to_arr(t), _to_arr(sm), sources)


@dataclass
class Climate:
    """Te same okna kalendarzowe w latach referencyjnych."""

    years: list
    kbw30: np.ndarray
    kbw60: np.ndarray
    soil_moisture: np.ndarray  # średnia z ±7 dni wokół daty


def climatology(lat: float, lon: float, target: date) -> Climate:
    y0, y1 = CLIMATE_YEARS
    raw = _fetch(ARCHIVE_URL, lat, lon, date(y0, 1, 1), date(y1, 12, 31),
                 "precipitation_sum,et0_fao_evapotranspiration,soil_moisture_0_to_100cm_mean")
    days = [date.fromisoformat(x) for x in raw["time"]]
    idx = {d: i for i, d in enumerate(days)}
    p = _to_arr(raw["precipitation_sum"])
    e = _to_arr(raw["et0_fao_evapotranspiration"])
    sm = _to_arr(raw["soil_moisture_0_to_100cm_mean"])

    years, k30, k60, smv = [], [], [], []
    for y in range(y0, y1 + 1):
        try:
            d = target.replace(year=y)
        except ValueError:  # 29 lutego
            d = target.replace(year=y, day=28)
        if d not in idx or (d - timedelta(days=60)) not in idx:
            continue
        i = idx[d]
        years.append(y)
        k30.append(np.nansum(p[i - 29:i + 1] - e[i - 29:i + 1]))
        k60.append(np.nansum(p[i - 59:i + 1] - e[i - 59:i + 1]))
        smv.append(np.nanmean(sm[max(0, i - 7):i + 8]))
    return Climate(years, np.array(k30), np.array(k60), np.array(smv))


def percentile_of(value: float, sample: np.ndarray) -> float:
    """Jaki odsetek lat referencyjnych miał wartość niższą lub równą (0–100)."""
    s = sample[~np.isnan(sample)]
    if len(s) == 0 or value is None or np.isnan(value):
        return float("nan")
    return float((s <= value).sum()) / len(s) * 100
