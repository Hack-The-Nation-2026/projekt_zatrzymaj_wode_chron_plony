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
# Tło wieloletnie: 10 pełnych lat poprzedzających rok analizy (wymóg zadania KOWR: „dane za ostatnie 10 lat”).
CLIMATE_YEARS_BACK = 10


def climate_years(target: date) -> list[int]:
    return list(range(target.year - CLIMATE_YEARS_BACK, target.year))

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
    # Przyciągamy punkt do siatki 0,1° (rozdzielczość ERA5-Land): dane i tak pochodzą z najbliższego
    # węzła siatki, a sąsiednie działki trafiają wtedy w ten sam wpis cache (mniej zapytań do limitu API).
    lat, lon = round(lat * 10) / 10, round(lon * 10) / 10
    return get_json(url, {
        "latitude": f"{lat:.2f}", "longitude": f"{lon:.2f}",
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


SCENARIO_DAYS = 30  # horyzont scenariuszy „co dalej” (dni po dacie analizy)


@dataclass
class Climate:
    """Te same okna kalendarzowe w latach referencyjnych."""

    years: list
    kbw30: np.ndarray
    kbw60: np.ndarray
    soil_moisture: np.ndarray  # średnia z ±7 dni wokół daty
    future_precip: list = field(default_factory=list)  # na rok: opad w dniach 1..SCENARIO_DAYS po dacie
    future_et0: list = field(default_factory=list)


def _year_window(lat: float, lon: float, d: date):
    """Okno z jednego roku: 60 dni przed datą (bilans 30/60 dni), wilgotność ±7 dni
    oraz SCENARIO_DAYS dni po dacie (pogoda do scenariuszy)."""
    raw = _fetch(ARCHIVE_URL, lat, lon, d - timedelta(days=59), d + timedelta(days=SCENARIO_DAYS),
                 "precipitation_sum,et0_fao_evapotranspiration,soil_moisture_0_to_100cm_mean")
    p = _to_arr(raw["precipitation_sum"])
    e = _to_arr(raw["et0_fao_evapotranspiration"])
    sm = _to_arr(raw["soil_moisture_0_to_100cm_mean"])
    i = 59  # indeks daty docelowej w oknie
    return (float(np.nansum(p[i - 29:i + 1] - e[i - 29:i + 1])),
            float(np.nansum(p[:i + 1] - e[:i + 1])),
            float(np.nanmean(sm[i - 7:i + 8])),
            np.nan_to_num(p[i + 1:i + 1 + SCENARIO_DAYS]),
            np.nan_to_num(e[i + 1:i + 1 + SCENARIO_DAYS]))


def climatology(lat: float, lon: float, target: date) -> Climate:
    """Tło wieloletnie z 10 lat przed rokiem analizy: z każdego roku pobieramy tylko potrzebne okno
    (mniejsze zużycie limitu darmowego API, a każde okno trafia osobno do cache)."""
    from concurrent.futures import ThreadPoolExecutor

    days = []
    for y in climate_years(target):
        try:
            days.append(target.replace(year=y))
        except ValueError:  # 29 lutego
            days.append(target.replace(year=y, day=28))
    with ThreadPoolExecutor(max_workers=10) as ex:
        rows = list(ex.map(lambda d: _year_window(lat, lon, d), days))
    k30, k60, smv, fp, fe = zip(*rows)
    return Climate([d.year for d in days], np.array(k30), np.array(k60), np.array(smv), list(fp), list(fe))


def percentile_of(value: float, sample: np.ndarray) -> float:
    """Jaki odsetek lat referencyjnych miał wartość niższą lub równą (0–100)."""
    s = sample[~np.isnan(sample)]
    if len(s) == 0 or value is None or np.isnan(value):
        return float("nan")
    return float((s <= value).sum()) / len(s) * 100
