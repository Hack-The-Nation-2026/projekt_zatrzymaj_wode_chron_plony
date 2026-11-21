"""Stan roślin z satelitów Sentinel-2 (Copernicus, poziom L2A – odbicie od powierzchni).

Źródło: publiczny katalog STAC Earth Search (Element 84) z plikami COG w AWS Open Data.
Nie wymaga konta. Czytamy tylko wycinek obejmujący działkę.

Wskaźniki:
- NDVI = (NIR − RED) / (NIR + RED)         – „zieloność”, ilość aktywnej biomasy
- NDMI = (NIR − SWIR1) / (NIR + SWIR1)     – zawartość wody w roślinach (ang. moisture index)
Chmury, cienie i śnieg odrzucamy maską SCL (klasyfikacja sceny ESA).
Progi interpretacji są heurystyczne i opisane w dokumentacji; wynik zawsze traktujemy
jako potwierdzenie innych danych, nie samodzielną diagnozę (zgodnie z materiałem KOWR).
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.warp import transform_bounds, transform_geom
from rasterio.windows import from_bounds

from .http import CACHE_DIR, OFFLINE, DataSourceError, get_json
from .parcel import Parcel

STAC_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"
LOOKBACK_DAYS = 30
MIN_VALID = 0.6  # minimalny udział działki bez chmur
VALID_SCL = (4, 5, 7)  # roślinność, gleba odkryta, niesklasyfikowane
SAT_CACHE = CACHE_DIR.parent / "sat"
_GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", AWS_NO_SIGN_REQUEST="YES",
                 GDAL_HTTP_MAX_RETRY="2", GDAL_HTTP_RETRY_DELAY="1", GDAL_HTTP_TIMEOUT="30",
                 CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")


@dataclass
class Scene:
    date: str
    scene_id: str
    valid_share: float  # udział działki widoczny bez chmur
    ndvi: float
    ndmi: float
    ndmi_p10: float
    dry_lat: float | None = None  # środek najsuchszych 10% działki
    dry_lon: float | None = None


@dataclass
class SatelliteResult:
    current: Scene | None
    previous: Scene | None
    scenes_checked: int


def _search(parcel: Parcel, start: date, end: date) -> list:
    body = {
        "collections": [COLLECTION],
        "intersects": parcel.geom_wgs84.__geo_interface__,
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "limit": 50,
        "query": {"eo:cloud_cover": {"lt": 85}},
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
    }
    import requests

    try:
        resp = requests.post(STAC_URL, json=body, timeout=60)
        resp.raise_for_status()
        feats = resp.json().get("features", [])
    except Exception as exc:  # sieć / katalog
        raise DataSourceError(f"Katalog Sentinel-2 nie odpowiedział: {exc}") from exc
    # Ta sama data bywa przetworzona dwa razy (…_0_L2A, …_1_L2A): bierzemy nowsze przetworzenie.
    best = {}
    for f in feats:
        key = (f["properties"]["datetime"][:10], f["id"].split("_")[1])
        if key not in best or f["id"] > best[key]["id"]:
            best[key] = f
    return sorted(best.values(), key=lambda f: f["properties"]["datetime"], reverse=True)


def _band(asset: dict, bounds_wgs84, out_shape=None, ref=None, offset_applied=False):
    """Czyta wycinek pasma; zwraca (odbicie jako float, transform, crs)."""
    rb = (asset.get("raster:bands") or [{}])[0]
    scale = rb.get("scale", 0.0001)
    # Earth Search zapisuje dane już po korekcie przesunięcia L2A (earthsearch:boa_offset_applied).
    # Wtedy nie odejmujemy go drugi raz, choć metadane pasma nadal je podają.
    offset = 0.0 if offset_applied else rb.get("offset", 0.0)
    with rasterio.open(asset["href"]) as src:
        full = rasterio.windows.Window(0, 0, src.width, src.height)
        if ref is None:
            bb = transform_bounds(4326, src.crs, *bounds_wgs84)
            win = from_bounds(*bb, transform=src.transform).round_offsets().round_lengths()
            win = win.intersection(full)  # bez czytania poza plikiem (tryb boundless jest bardzo wolny)
        else:
            win = from_bounds(*ref["bounds"], transform=src.transform)
        kw = {"out_shape": out_shape, "resampling": Resampling.average} if out_shape else {}
        data = src.read(1, window=win, **kw)
        transform = src.window_transform(win)
        if out_shape:
            transform = rasterio.Affine(transform.a * win.width / out_shape[1], 0, transform.c,
                                        0, transform.e * win.height / out_shape[0], transform.f)
        win_bounds = rasterio.windows.bounds(win, src.transform)
        raw = data.astype("float64")
        nodata = raw == 0
        refl = raw * scale + offset
        refl[nodata] = np.nan
        return refl, data, transform, src.crs, win_bounds


def _read_scene(item: dict, parcel: Parcel) -> Scene | None:
    a = item["assets"]
    bounds = parcel.geom_wgs84.bounds
    from shapely.geometry import mapping, shape as shp

    day = item["properties"]["datetime"][:10]
    with rasterio.Env(**_GDAL_ENV):
        _, scl, tr, crs, wb = _band(a["scl"], bounds)
        shape = scl.shape
        geom = transform_geom("EPSG:4326", crs, parcel.geom_wgs84.__geo_interface__)
        inner = shp(geom).buffer(-10)  # odsuwamy się od miedzy, żeby nie mieszać pikseli z sąsiadami
        use = inner if not inner.is_empty and inner.area > 1200 else shp(geom)
        mask = rasterize([(mapping(use), 1)], out_shape=shape, transform=tr, fill=0, dtype="uint8").astype(bool)
        if mask.sum() == 0:
            return None
        scl_ok = mask & np.isin(scl, VALID_SCL)
        if scl_ok.sum() / mask.sum() < MIN_VALID:  # za dużo chmur: nie pobieramy pozostałych pasm
            return Scene(day, item["id"], round(float(scl_ok.sum() / mask.sum()), 2),
                         float("nan"), float("nan"), float("nan"))
        ref = {"bounds": wb}
        with ThreadPoolExecutor(max_workers=3) as ex:
            applied = bool(item["properties"].get("earthsearch:boa_offset_applied", False))
            futs = {k: ex.submit(_band, a[k], bounds, shape, ref, applied) for k in ("red", "nir", "swir16")}
            red, nir, swir = (futs[k].result()[0] for k in ("red", "nir", "swir16"))

    # Po korekcie przesunięcia L2A bardzo ciemne piksele mogą mieć odbicie ≤ 0: przycinamy,
    # a wartości wskaźników spoza zakresu −1..1 odrzucamy.
    red, nir, swir = (np.clip(b, 1e-4, None) for b in (red, nir, swir))
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / (nir + red)
        ndmi = (nir - swir) / (nir + swir)
    clear = scl_ok & np.isfinite(ndvi) & np.isfinite(ndmi) & (np.abs(ndvi) <= 1) & (np.abs(ndmi) <= 1)
    valid_share = float(clear.sum() / mask.sum())
    if clear.sum() < 3:
        return Scene(day, item["id"], round(valid_share, 2), float("nan"), float("nan"), float("nan"))
    v_ndvi, v_ndmi = ndvi[clear], ndmi[clear]
    p10 = float(np.nanpercentile(v_ndmi, 10))
    dry = clear & (ndmi <= p10)
    dry_lat = dry_lon = None
    if dry.sum() >= 1:
        rows, cols = np.nonzero(dry)
        x, y = tr * (cols.mean() + 0.5, rows.mean() + 0.5)
        from pyproj import Transformer

        lon, lat = Transformer.from_crs(crs, 4326, always_xy=True).transform(x, y)
        dry_lat, dry_lon = round(lat, 6), round(lon, 6)
    return Scene(day, item["id"], round(valid_share, 2),
                 round(float(np.nanmean(v_ndvi)), 3), round(float(np.nanmean(v_ndmi)), 3),
                 round(p10, 3), dry_lat, dry_lon)


def analyse(parcel: Parcel, on: date) -> SatelliteResult:
    """Najnowsza bezchmurna scena do daty `on` (do 30 dni wstecz) i scena ok. 2–5 tygodni wcześniejsza."""
    cache_file = SAT_CACHE / f"{parcel.id.replace('/', '-')}_{on.isoformat()}.json"
    if cache_file.exists():
        d = json.loads(cache_file.read_text())
        return SatelliteResult(Scene(**d["current"]) if d["current"] else None,
                               Scene(**d["previous"]) if d["previous"] else None, d["scenes_checked"])
    if OFFLINE:
        raise DataSourceError("Brak zapisanych danych satelitarnych (tryb offline).")

    items = _search(parcel, on - timedelta(days=LOOKBACK_DAYS + 35), on)
    current, previous, checked = None, None, 0
    for it in items:
        d = date.fromisoformat(it["properties"]["datetime"][:10])
        if current is None and d < on - timedelta(days=LOOKBACK_DAYS):
            break
        if current is not None:
            gap = (date.fromisoformat(current.date) - d).days
            if gap < 12:
                continue
            if gap > 40:
                break
        checked += 1
        sc = _read_scene(it, parcel)
        if sc is None or sc.valid_share < MIN_VALID or np.isnan(sc.ndvi):
            continue
        if current is None:
            current = sc
        else:
            previous = sc
            break
        if checked >= 5:
            break

    res = SatelliteResult(current, previous, checked)
    SAT_CACHE.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"current": asdict(current) if current else None,
                                      "previous": asdict(previous) if previous else None,
                                      "scenes_checked": checked}))
    return res
