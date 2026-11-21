"""Granice działki ewidencyjnej z usługi ULDK (GUGiK)."""

from __future__ import annotations

from dataclasses import dataclass

from pyproj import Transformer
from shapely import wkt
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from .http import DataSourceError, get_text

ULDK_URL = "https://uldk.gugik.gov.pl/"
_FIELDS = "id,voivodeship,county,commune,region,parcel,geom_wkt"
_TO_WGS84 = Transformer.from_crs(2180, 4326, always_xy=True)
_TO_PL92 = Transformer.from_crs(4326, 2180, always_xy=True)


@dataclass
class Parcel:
    id: str
    voivodeship: str
    county: str
    commune: str
    region: str  # obręb
    number: str
    geom_2180: BaseGeometry  # PUWG 1992, metry

    @property
    def geom_wgs84(self) -> BaseGeometry:
        return transform(_TO_WGS84.transform, self.geom_2180)

    @property
    def area_ha(self) -> float:
        return self.geom_2180.area / 10_000

    @property
    def centroid_latlon(self) -> tuple[float, float]:
        c = self.geom_wgs84.centroid
        return c.y, c.x


def _parse(text: str) -> Parcel:
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != "0" or len(lines) < 2:
        raise DataSourceError(f"ULDK nie znalazł działki: {text.strip()[:200]}")
    parts = lines[1].split("|")
    if len(parts) < 7:
        raise DataSourceError(f"Nieoczekiwana odpowiedź ULDK: {lines[1][:200]}")
    geom_txt = parts[-1].split(";", 1)[-1]  # obcina prefiks "SRID=2180;"
    return Parcel(
        id=parts[0], voivodeship=parts[1], county=parts[2], commune=parts[3],
        region=parts[4], number=parts[5], geom_2180=wkt.loads(geom_txt),
    )


def by_id(parcel_id: str) -> Parcel:
    """Pełny identyfikator, np. 101609_2.0011.352 (TERYT_gminy.obręb.numer)."""
    return _parse(get_text(ULDK_URL, {"request": "GetParcelById", "id": parcel_id.strip(),
                                      "result": _FIELDS, "srid": "2180"}))


def by_point(lat: float, lon: float) -> Parcel:
    """Działka, na której leży punkt (współrzędne WGS84)."""
    x, y = _TO_PL92.transform(lon, lat)
    return _parse(get_text(ULDK_URL, {"request": "GetParcelByXY", "xy": f"{x:.2f},{y:.2f}",
                                      "result": _FIELDS, "srid": "2180"}))


def to_latlon(x: float, y: float) -> tuple[float, float]:
    lon, lat = _TO_WGS84.transform(x, y)
    return lat, lon
