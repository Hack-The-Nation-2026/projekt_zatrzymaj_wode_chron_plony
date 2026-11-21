"""Analiza terenu z Numerycznego Modelu Terenu (GUGiK, LIDAR, siatka 1 m, usługa WCS).

Kroki: wycinek NMT z buforem → uśrednienie do 5 m → wypełnienie zagłębień
(priority-flood) → kierunki spływu D8 → akumulacja spływu.
Wynik: spadki, miejsca, którędy woda opuszcza działkę, naturalne zagłębienia
(kandydaci na oczko wodne / retencję) oraz dopływ wody spoza działki.
"""

from __future__ import annotations

import heapq
import io
from dataclasses import dataclass, field

import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy import ndimage

from .http import DataSourceError, get_bytes
from .parcel import Parcel, to_latlon

WCS_URL = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModelFormatTIFF"
COVERAGE = "DTM_PL-KRON86-NH_TIFF"
BUFFER_M = 150
CELL_M = 5
MAX_SIDE_M = 2500

# sąsiedzi D8: (dy, dx, odległość)
_NB = [(-1, -1, 1.414), (-1, 0, 1.0), (-1, 1, 1.414), (0, -1, 1.0),
       (0, 1, 1.0), (1, -1, 1.414), (1, 0, 1.0), (1, 1, 1.414)]


@dataclass
class Spot:
    lat: float
    lon: float
    kind: str
    value: float  # znaczenie zależne od rodzaju (ha zlewni / m³ objętości)
    note: str = ""


@dataclass
class Terrain:
    elev_min: float
    elev_max: float
    slope_mean_pct: float
    slope_p90_pct: float
    steep_share_pct: float  # udział powierzchni o spadku > 5%
    outflow_points: list = field(default_factory=list)
    depressions: list = field(default_factory=list)
    inflow_area_ha: float = 0.0  # zlewnia spoza działki, która spływa na działkę
    concentrated_flow_share_pct: float = 0.0  # udział działki na liniach skoncentrowanego spływu


def _download_dem(parcel: Parcel):
    minx, miny, maxx, maxy = parcel.geom_2180.bounds
    minx, miny, maxx, maxy = minx - BUFFER_M, miny - BUFFER_M, maxx + BUFFER_M, maxy + BUFFER_M
    if maxx - minx > MAX_SIDE_M or maxy - miny > MAX_SIDE_M:
        raise DataSourceError("Działka jest za duża dla prototypu (bok > 2,2 km).")
    minx, miny = np.floor(minx), np.floor(miny)
    maxx, maxy = np.ceil(maxx), np.ceil(maxy)
    # Parametr SUBSET występuje dwa razy (oś x i y), więc URL składamy ręcznie.
    # Oś x = easting, y = northing w układzie PUWG 1992 (EPSG:2180).
    data = get_bytes(
        WCS_URL + f"?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID={COVERAGE}"
        f"&FORMAT=image/tiff&SUBSET=x({minx:.0f},{maxx:.0f})&SUBSET=y({miny:.0f},{maxy:.0f})",
        timeout=180)
    if not data.startswith(b"II") and not data.startswith(b"MM"):
        raise DataSourceError(f"Usługa NMT nie zwróciła pliku TIFF: {data[:200]!r}")
    with rasterio.open(io.BytesIO(data)) as src:
        dem = src.read(1).astype(np.float64)
        transform = src.transform
        if src.nodata is not None:
            dem[dem == src.nodata] = np.nan
    dem[(dem < -100) | (dem > 3000)] = np.nan
    return dem, transform


def _aggregate(dem: np.ndarray, transform, k: int):
    h, w = (dem.shape[0] // k) * k, (dem.shape[1] // k) * k
    blocks = dem[:h, :w].reshape(h // k, k, w // k, k)
    agg = np.nanmean(blocks, axis=(1, 3))
    return agg, transform * transform.scale(k, k)


def _fill(dem: np.ndarray, eps: float = 1e-4) -> np.ndarray:
    """Priority-flood (Barnes i in. 2014) z małym spadkiem na płaskich, by woda zawsze odpływała."""
    h, w = dem.shape
    filled = np.where(np.isnan(dem), np.nanmin(dem), dem).copy()
    done = np.zeros_like(filled, dtype=bool)
    pq: list = []
    for y in range(h):
        for x in (0, w - 1):
            heapq.heappush(pq, (filled[y, x], y, x)); done[y, x] = True
    for x in range(1, w - 1):
        for y in (0, h - 1):
            heapq.heappush(pq, (filled[y, x], y, x)); done[y, x] = True
    while pq:
        z, y, x = heapq.heappop(pq)
        for dy, dx, _ in _NB:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not done[ny, nx]:
                done[ny, nx] = True
                if filled[ny, nx] <= z:
                    filled[ny, nx] = z + eps
                heapq.heappush(pq, (filled[ny, nx], ny, nx))
    return filled


def _d8(filled: np.ndarray) -> np.ndarray:
    """Indeks (0–7) sąsiada o największym spadku, -1 gdy brak (brzeg)."""
    h, w = filled.shape
    best = np.full((h, w), -1, dtype=np.int8)
    best_slope = np.zeros((h, w))
    pad = np.pad(filled, 1, mode="constant", constant_values=np.inf)
    for k, (dy, dx, dist) in enumerate(_NB):
        nb = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        slope = (filled - nb) / dist
        better = slope > best_slope
        best[better] = k
        best_slope[better] = slope[better]
    return best


def _accumulate(filled: np.ndarray, fdir: np.ndarray) -> np.ndarray:
    h, w = filled.shape
    acc = np.ones((h, w))
    order = np.argsort(filled, axis=None)[::-1]
    for flat in order:
        y, x = divmod(int(flat), w)
        k = fdir[y, x]
        if k < 0:
            continue
        dy, dx, _ = _NB[k]
        ny, nx = y + dy, x + dx
        if 0 <= ny < h and 0 <= nx < w:
            acc[ny, nx] += acc[y, x]
    return acc


def analyse(parcel: Parcel) -> Terrain:
    dem1, tr1 = _download_dem(parcel)
    dem, tr = _aggregate(dem1, tr1, CELL_M)
    cell_area = CELL_M * CELL_M
    mask = rasterize([(parcel.geom_2180, 1)], out_shape=dem.shape, transform=tr, fill=0, dtype="uint8").astype(bool)
    if mask.sum() < 4:
        raise DataSourceError("Działka jest za mała dla analizy terenu (poniżej ~100 m²).")

    gy, gx = np.gradient(np.where(np.isnan(dem), np.nanmean(dem), dem), CELL_M)
    slope = np.hypot(gx, gy) * 100
    inside = slope[mask]

    filled = _fill(dem)
    fdir = _d8(filled)
    acc = _accumulate(filled, fdir)  # liczba komórek zlewni

    def xy_to_latlon(row, col):
        x, y = tr * (col + 0.5, row + 0.5)
        return to_latlon(x, y)

    # Miejsca, którędy woda opuszcza działkę: komórka w działce, której spływ trafia poza działkę.
    h, w = dem.shape
    outs = []
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        k = fdir[y, x]
        if k < 0:
            continue
        dy, dx, _ = _NB[k]
        ny, nx = y + dy, x + dx
        if not (0 <= ny < h and 0 <= nx < w) or not mask[ny, nx]:
            outs.append((acc[y, x] * cell_area / 10_000, y, x))
    outs.sort(reverse=True)
    outflow = []
    for area_ha, y, x in outs[:3]:
        if area_ha < 0.3:
            break
        lat, lon = xy_to_latlon(y, x)
        outflow.append(Spot(lat, lon, "odpływ", round(area_ha, 2),
                            "punkt, którym spływa woda z ok. %s ha zlewni" % f"{area_ha:.1f}".replace(".", ",")))

    # Dopływ spoza działki: komórki tuż poza działką, które spływają do działki.
    inflow_cells = 0.0
    for y in range(h):
        for x in range(w):
            if mask[y, x]:
                continue
            k = fdir[y, x]
            if k < 0:
                continue
            dy, dx, _ = _NB[k]
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx]:
                inflow_cells += acc[y, x]
    inflow_ha = inflow_cells * cell_area / 10_000

    # Naturalne zagłębienia (wypełnienie > 10 cm) w działce i tuż przy niej.
    depth = filled - np.where(np.isnan(dem), filled, dem)
    near = ndimage.binary_dilation(mask, iterations=4)
    labels, n = ndimage.label((depth > 0.10) & near)
    deps = []
    for lab in range(1, n + 1):
        sel = labels == lab
        cells = int(sel.sum())
        if cells < 4:  # < 100 m²
            continue
        vol = float(depth[sel].sum() * cell_area)
        cy, cx = ndimage.center_of_mass(sel)
        lat, lon = xy_to_latlon(cy, cx)
        deps.append(Spot(lat, lon, "zagłębienie", round(vol),
                         "obniżenie ok. %d m², maks. głębokość %s m"
                         % (cells * cell_area, f"{float(depth[sel].max()):.1f}".replace(".", ","))))
    deps.sort(key=lambda s: -s.value)

    conc = (acc * cell_area >= 5000) & mask  # linie spływu ze zlewni ≥ 0,5 ha
    return Terrain(
        elev_min=round(float(np.nanmin(dem[mask])), 1),
        elev_max=round(float(np.nanmax(dem[mask])), 1),
        slope_mean_pct=round(float(np.nanmean(inside)), 1),
        slope_p90_pct=round(float(np.nanpercentile(inside, 90)), 1),
        steep_share_pct=round(float((inside > 5).mean() * 100), 1),
        outflow_points=outflow,
        depressions=deps[:3],
        inflow_area_ha=round(inflow_ha, 2),
        concentrated_flow_share_pct=round(float(conc.sum() / mask.sum() * 100), 1),
    )
