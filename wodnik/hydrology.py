"""Dane hydrologiczne i krajobrazowe wokół działki z BDOT10k (GUGiK):
rowy melioracyjne, rzeki i strumienie, kanały, wody powierzchniowe, mokradła, lasy i zadrzewienia.

Źródło: usługa WMS „kompozycja BDOT10k” w Geoportalu (dane otwarte GUGiK). Wektorowe zapytania
punktowe do BDOT10k nie są publicznie dostępne (WFS udostępnia tylko paczki powiatowe), dlatego
pobieramy obraz każdej warstwy w układzie PUWG 1992 (EPSG:2180) dla otoczenia działki i liczymy
odległości transformatą odległości na siatce (rozdzielczość 2–4 m). Dokładność odległości: ok. ±1 piksel.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from scipy import ndimage

from .http import DataSourceError, get_bytes
from .parcel import Parcel

WMS_URL = "https://mapy.geoportal.gov.pl/wss/service/pub/guest/kompozycja_BDOT10k_WMS/MapServer/WMSServer"
RADIUS_M = 500
MAX_PX = 2000
LAYERS = {
    "rowy": "row",                      # rów melioracyjny
    "cieki": "rz,rzOk,kan,kanOkr",      # rzeka/strumień (też okresowy), kanał (też okresowy)
    "wody": "WPow",                     # woda powierzchniowa (stawy, jeziora, zbiorniki)
    "mokradla": "Mo",
    "lasy": "TLes",                     # teren leśny i zadrzewiony
}
KIND_PL = {"rowy": "rów melioracyjny", "cieki": "rzeka, strumień lub kanał", "wody": "woda powierzchniowa",
           "mokradla": "mokradło", "lasy": "las lub zadrzewienie"}


@dataclass
class Hydrology:
    source: str
    distance_m: dict = field(default_factory=dict)  # najbliższa odległość od granicy działki do obiektu danej grupy
    count_500m: dict = field(default_factory=dict)  # liczba oddzielnych obiektów w promieniu 500 m
    resolution_m: float = 2.0
    _dist: dict = field(default_factory=dict, repr=False)  # mapy odległości [m] do dopytań punktowych
    _transform: object = field(default=None, repr=False)

    def near(self, group: str, max_m: float) -> bool:
        d = self.distance_m.get(group)
        return d is not None and d <= max_m

    def at_point(self, group: str, x: float, y: float) -> float | None:
        """Odległość [m] od punktu (EPSG:2180) do najbliższego obiektu grupy (None = poza obszarem/brak)."""
        dist = self._dist.get(group)
        if dist is None or self._transform is None:
            return None
        col, row = ~self._transform * (x, y)
        r, c = int(row), int(col)
        if 0 <= r < dist.shape[0] and 0 <= c < dist.shape[1] and np.isfinite(dist[r, c]):
            return float(dist[r, c])
        return None


def _layer_mask(layers: str, bbox, w: int, h: int) -> np.ndarray:
    minx, miny, maxx, maxy = bbox
    data = get_bytes(WMS_URL, {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layers, "STYLES": "",
        "CRS": "EPSG:2180", "BBOX": f"{miny:.1f},{minx:.1f},{maxy:.1f},{maxx:.1f}",  # WMS 1.3.0: oś północna pierwsza
        "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/png", "TRANSPARENT": "TRUE",
    }, timeout=30)
    if not data.startswith(b"\x89PNG"):
        raise DataSourceError(f"Usługa BDOT10k nie zwróciła obrazu dla warstwy {layers}: {data[:150]!r}")
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # PNG bez georeferencji – położenie znamy z zapytania
        with MemoryFile(data) as mem, mem.open() as src:
            img = src.read()
    alpha = img[-1] if img.shape[0] in (2, 4) else img.sum(axis=0)
    return alpha > 0


def analyse(parcel: Parcel) -> Hydrology:
    minx, miny, maxx, maxy = parcel.geom_2180.buffer(RADIUS_M).bounds
    res = max(2.0, max(maxx - minx, maxy - miny) / MAX_PX)
    w, h = int(np.ceil((maxx - minx) / res)), int(np.ceil((maxy - miny) / res))
    maxx, maxy = minx + w * res, miny + h * res
    bbox = (minx, miny, maxx, maxy)
    tr = from_bounds(minx, miny, maxx, maxy, w, h)

    with ThreadPoolExecutor(max_workers=len(LAYERS)) as ex:
        futs = {g: ex.submit(_layer_mask, lyr, bbox, w, h) for g, lyr in LAYERS.items()}
        masks = {g: f.result() for g, f in futs.items()}

    parcel_mask = rasterize([(parcel.geom_2180, 1)], out_shape=(h, w), transform=tr, fill=0,
                            dtype="uint8").astype(bool)
    if not parcel_mask.any():
        raise DataSourceError("Nie udało się nałożyć działki na siatkę danych hydrologicznych.")
    zone = ndimage.binary_dilation(parcel_mask, iterations=int(RADIUS_M / res))

    hy = Hydrology(source="BDOT10k (GUGiK), usługa WMS kompozycja_BDOT10k_WMS", resolution_m=round(res, 1),
                   _transform=tr)
    for g, m in masks.items():
        if m.any():
            dist = ndimage.distance_transform_edt(~m) * res
            hy._dist[g] = dist
            hy.distance_m[g] = round(float(dist[parcel_mask].min()))
            if g in ("wody", "mokradla"):  # obiekty powierzchniowe; linie (rowy, cieki) rysowane przerywaną kreską
                labels, n = ndimage.label(m & zone)  # rozpadają się na fragmenty, więc ich nie liczymy
                hy.count_500m[g] = int(n)
        else:
            hy.distance_m[g] = None
            if g in ("wody", "mokradla"):
                hy.count_500m[g] = 0
    return hy


def describe(hy: Hydrology) -> list[str]:
    """Krótkie opisy do uzasadnień w raporcie."""
    out = []
    for g, kind in KIND_PL.items():
        d = hy.distance_m.get(g)
        if d is None:
            out.append(f"{kind}: brak w promieniu {RADIUS_M} m")
        elif d == 0:
            out.append(f"{kind}: na działce lub na jej granicy")
        else:
            out.append(f"{kind}: najbliżej {d} m od działki")
    return out
