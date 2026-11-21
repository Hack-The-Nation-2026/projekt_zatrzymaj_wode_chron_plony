"""Właściwości gleby z SoilGrids 2.0 (ISRIC, rozdzielczość 250 m, CC BY 4.0).

Pojemność wodną liczymy funkcją pedotransferową Saxton & Rawls (2006)
z udziału piasku, iłu i materii organicznej.
"""

from __future__ import annotations

from dataclasses import dataclass

from .http import DataSourceError, get_json

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
_DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm"]
_THICK = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15, "30-60cm": 30, "60-100cm": 40}


@dataclass
class Soil:
    sand_pct: float
    clay_pct: float
    soc_pct: float  # węgiel organiczny w warstwie 0–30 cm
    fc: float  # polowa pojemność wodna θ33 [m³/m³]
    wp: float  # punkt trwałego więdnięcia θ1500 [m³/m³]
    texture_label: str
    category: str  # "lekka" / "średnia" / "ciężka" (zbliżone do kategorii agronomicznych)

    @property
    def awc(self) -> float:
        return max(0.03, self.fc - self.wp)

    @property
    def awc_mm_per_m(self) -> float:
        return self.awc * 1000


def saxton_rawls(sand: float, clay: float, om: float) -> tuple[float, float]:
    """sand, clay jako ułamki (0–1), om = materia organiczna w %. Zwraca (θ33, θ1500)."""
    s, c = sand, clay
    t1500t = -0.024 * s + 0.487 * c + 0.006 * om + 0.005 * s * om - 0.013 * c * om + 0.068 * s * c + 0.031
    t1500 = t1500t + (0.14 * t1500t - 0.02)
    t33t = -0.251 * s + 0.195 * c + 0.011 * om + 0.006 * s * om - 0.027 * c * om + 0.452 * s * c + 0.299
    t33 = t33t + (1.283 * t33t ** 2 - 0.374 * t33t - 0.015)
    return t33, t1500


def _classify(sand: float, clay: float) -> tuple[str, str]:
    if sand >= 70 and clay < 10:
        return "piasek luźny / słabogliniasty", "lekka"
    if sand >= 50 and clay < 20:
        return "piasek gliniasty / glina lekka", "lekka"
    if clay >= 35:
        return "glina ciężka / ił", "ciężka"
    if clay >= 20:
        return "glina średnia", "średnia"
    return "glina lekka / pył", "średnia"


def at_point(lat: float, lon: float) -> Soil:
    params = [("lon", f"{lon:.5f}"), ("lat", f"{lat:.5f}"), ("value", "mean")]
    params += [("property", p) for p in ("sand", "clay", "soc")]
    params += [("depth", d) for d in _DEPTHS]
    from urllib.parse import urlencode

    data = get_json(SOILGRIDS_URL + "?" + urlencode(params), timeout=120)
    layers = {l["name"]: l for l in data["properties"]["layers"]}

    def avg(prop: str, depths: list) -> float | None:
        layer = layers.get(prop)
        if not layer:
            return None
        factor = layer["unit_measure"]["d_factor"]
        tot, w = 0.0, 0
        for d in layer["depths"]:
            if d["label"] in depths and d["values"].get("mean") is not None:
                tot += d["values"]["mean"] / factor * _THICK[d["label"]]
                w += _THICK[d["label"]]
        return tot / w if w else None

    sand = avg("sand", _DEPTHS)  # %
    clay = avg("clay", _DEPTHS)  # %
    soc = avg("soc", _DEPTHS[:3])  # g/kg
    if sand is None or clay is None:
        raise DataSourceError("SoilGrids nie ma danych dla tego punktu (np. teren zabudowany lub woda).")
    soc_pct = (soc or 10.0) / 10.0
    fc, wp = saxton_rawls(sand / 100, clay / 100, soc_pct * 1.724)
    label, cat = _classify(sand, clay)
    return Soil(round(sand, 1), round(clay, 1), round(soc_pct, 2), round(fc, 3), round(wp, 3), label, cat)
