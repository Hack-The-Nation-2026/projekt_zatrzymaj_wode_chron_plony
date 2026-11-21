"""„Co da retencja”: wymiarowanie działań na ulewę i efekt materii organicznej w glebie.

Dlaczego ulewa, a nie cały sezon: opad z ERA5 to średnia dobowa dla obszaru ok. 9–25 km, więc rzadko przekracza
15–20 mm na dobę. Przy takich wartościach metoda SCS-CN nie daje spływu, choć w rzeczywistości lokalne ulewy
spływają z pól. Dlatego działania retencyjne liczymy dla pojedynczej ulewy (30 i 50 mm na dobę):

- spływ Q [mm] metodą SCS-CN (USDA NRCS, TR-55; CN z grupy hydrologicznej gleby i rodzaju uprawy, wilgotność
  przeciętna AMC II), objętość = Q × powierzchnia, osobno z działki i z jej zlewni zewnętrznej (z NMT);
- wał lub próg w miejscu odpływu: na stoku o spadku s wał o wysokości h zatrzymuje ok. h² / (2·s) m³ na metr
  długości (trójkątny przekrój wody za wałem); stąd potrzebna długość wału;
- naturalne obniżenie (z NMT): objętość, którą można wykorzystać na oczko wodne lub mokradło.

Materia organiczna (międzyplony, resztki, nawozy naturalne): +OM_GAIN_PCT pkt proc. po kilku latach; nowa
pojemność wodna wg Saxton & Rawls (2006) i ten sam bilans FAO-56 oraz scenariusze co w raporcie.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from . import scenarios, waterbalance
from .soil import saxton_rawls

DESIGN_RAINS_MM = (30.0, 50.0)
BERM_HEIGHT_M = 0.3
OM_GAIN_PCT = 1.0
MIN_SLOPE = 0.005  # na płaskim terenie wał zatrzymuje wodę na dużej powierzchni; ograniczamy przybliżenie

# CN dla dobrych warunków hydrologicznych (TR-55, tab. 2-2b/2-2c)
_CN = {
    "row": {"A": 67, "B": 78, "C": 85, "D": 89},      # uprawy rzędowe: kukurydza, ziemniaki, buraki
    "grain": {"A": 63, "B": 75, "C": 83, "D": 87},    # zboża i rzepak
    "meadow": {"A": 30, "B": 58, "C": 71, "D": 78},   # łąki i pastwiska
}
_LANDUSE = {"kukurydza": "row", "ziemniaki": "row", "burak_cukrowy": "row", "uzytki_zielone": "meadow"}


def hydrologic_group(soil) -> str:
    """Grupa hydrologiczna gleby (A: przepuszczalna … D: słabo przepuszczalna) z uziarnienia."""
    if soil is None:
        return "B"
    if soil.clay_pct >= 35:
        return "D"
    if soil.clay_pct >= 20:
        return "C"
    if soil.sand_pct >= 70:
        return "A"
    return "B"


def curve_number(crop_key: str, soil) -> int:
    return _CN[_LANDUSE.get(crop_key, "grain")][hydrologic_group(soil)]


def runoff(p, cn: int) -> np.ndarray:
    """Spływ dobowy Q [mm] z opadu P [mm] wg SCS-CN (Ia = 0,2 S)."""
    p = np.nan_to_num(np.asarray(p, dtype=float))
    s = 25400.0 / cn - 254.0
    ia = 0.2 * s
    return np.where(p > ia, (p - ia) ** 2 / (p + 0.8 * s), 0.0)


def infiltrated(p, cn: int) -> np.ndarray:
    """Woda zasilająca strefę korzeniową: opad − spływ."""
    p = np.nan_to_num(np.asarray(p, dtype=float))
    return p - runoff(p, cn)


def _awc(soil, om_gain: float) -> float:
    fc, wp = saxton_rawls(soil.sand_pct / 100, soil.clay_pct / 100, soil.soc_pct * 1.724 + om_gain)
    return max(0.02, fc - wp)


def _pl(x, d=1) -> str:
    """Liczba po polsku: przecinek dziesiętny."""
    return f"{x:.{d}f}".replace(".", ",")


def _r(x, d=0):
    return None if x is None else round(float(x), d)


def run(series, crop, soil, awc0: float, i_on: int, on, clim, fc_p, fc_e, cn: int,
        parcel_ha: float, terr=None, horizon: int = 30) -> dict | None:
    """`series` – pogoda z opadem surowym; `terr` – wynik analizy terenu (albo None)."""
    inflow_ha = float(terr.inflow_area_ha) if terr else 0.0
    slope = max(MIN_SLOPE, (terr.slope_mean_pct / 100.0) if terr else 0.02)

    storms = []
    for rain in DESIGN_RAINS_MM:
        q = float(runoff([rain], cn)[0])
        v_parcel = q * parcel_ha * 10.0  # mm × ha → m³
        v_in = q * inflow_ha * 10.0
        storms.append({"rain_mm": rain, "runoff_mm": _r(q, 1), "volume_parcel_m3": _r(v_parcel),
                       "volume_inflow_m3": _r(v_in), "volume_total_m3": _r(v_parcel + v_in)})

    measures = []
    big = storms[-1]
    per_m = BERM_HEIGHT_M ** 2 / (2 * slope)  # m³ na metr wału
    if terr and terr.outflow_points and big["volume_total_m3"]:
        length = big["volume_total_m3"] / per_m
        measures.append({
            "key": "wal", "name": "Wał lub próg w miejscu odpływu",
            "value": _r(length), "unit": "m",
            "detail": (f"Przy ulewie {big['rain_mm']:.0f} mm z działki i z sąsiednich pól spłynie ok. "
                       f"{big['volume_total_m3']:.0f} m³ wody. Wał wysokości {BERM_HEIGHT_M * 100:.0f} cm przy spadku "
                       f"{_pl(slope * 100)}% zatrzyma ok. {_pl(per_m)} m³ na metr, więc na całą tę wodę potrzeba ok. "
                       f"{length:.0f} m wału "
                       + ("w punkcie odpływu." if len(terr.outflow_points) == 1
                          else f"w {len(terr.outflow_points)} punktach odpływu.")),
        })
    if terr and terr.depressions:
        cap = float(sum(s.value for s in terr.depressions))
        share = cap / big["volume_total_m3"] if big["volume_total_m3"] else None
        measures.append({
            "key": "oczko", "name": "Oczko wodne lub mokradło w naturalnym obniżeniu",
            "value": _r(cap), "unit": "m³",
            "detail": (f"Naturalne obniżenia na działce mieszczą ok. {cap:.0f} m³ wody"
                       + ("." if not share else f", czyli cały spływ z ulewy {big['rain_mm']:.0f} mm." if share >= 1
                          else f", czyli ok. {share * 100:.0f}% spływu z ulewy {big['rain_mm']:.0f} mm.")),
        })

    root = None
    if soil is not None:
        awc1 = _awc(soil, OM_GAIN_PCT)
        s_in = replace(series, precip=infiltrated(series.precip, cn))
        b0 = waterbalance.run(s_in, crop, awc0, i_on)
        b1 = waterbalance.run(s_in, crop, awc1, i_on)
        hist = [infiltrated(x, cn) for x in clim.future_precip]
        fp = infiltrated(fc_p, cn) if fc_p is not None else None
        o0 = scenarios.run(on, float(b0.depletion[-1]), b0.taw, b0.raw, crop, hist, clim.future_et0, clim.years, fp, fc_e, horizon)
        o1 = scenarios.run(on, float(b1.depletion[-1]), b1.taw, b1.raw, crop, hist, clim.future_et0, clim.years, fp, fc_e, horizon)
        root = {
            "taw_before_mm": _r(b0.taw, 1), "taw_after_mm": _r(b1.taw, 1),
            "water_left_before_mm": _r(b0.taw - b0.depletion[-1], 1), "water_left_after_mm": _r(b1.taw - b1.depletion[-1], 1),
            "stress_days_season_before": int((b0.ks < 0.999).sum()), "stress_days_season_after": int((b1.ks < 0.999).sum()),
            "p_stress_30_before": o0.p_stress_30 if o0 else None, "p_stress_30_after": o1.p_stress_30 if o1 else None,
        }
        gain = root["taw_after_mm"] - root["taw_before_mm"]
        measures.append({
            "key": "materia", "name": "Więcej materii organicznej (międzyplony, resztki pożniwne)",
            "value": _r(gain, 1), "unit": "mm",
            "detail": (f"Po kilku latach (+{OM_GAIN_PCT:.0f} pkt proc. materii organicznej) gleba zmieści ok. {gain:.0f} mm "
                       f"wody więcej w strefie korzeni ({root['taw_before_mm']:.0f} → {root['taw_after_mm']:.0f} mm). "
                       f"W tym sezonie: dni stresu {root['stress_days_season_after']} zamiast {root['stress_days_season_before']}."),
        })

    if not measures:
        return None
    return {
        "storms": storms, "measures": measures, "root_zone": root,
        "curve_number": cn, "hydrologic_group": hydrologic_group(soil),
        "parcel_ha": _r(parcel_ha, 2), "inflow_ha": _r(inflow_ha, 2), "slope_pct": _r(slope * 100, 1),
        "summary": _summary(storms, measures),
        "assumptions": [
            f"Spływ z ulewy metodą SCS-CN (USDA, TR-55), CN = {cn} (gleba grupy {hydrologic_group(soil)}, "
            f"{'uprawa rzędowa' if _LANDUSE.get(crop.key) == 'row' else 'łąka' if _LANDUSE.get(crop.key) == 'meadow' else 'zboża i rzepak'}, "
            "przeciętna wilgotność gleby); dla sąsiednich pól przyjęto ten sam CN.",
            "Ulewa 30 i 50 mm na dobę to przykłady silnych opadów, nie prognoza; dobowe dane ERA5 (średnia dla obszaru "
            "9–25 km) nie pokazują lokalnych ulew, dlatego nie liczymy spływu z historii pogody.",
            f"Wał: wysokość {BERM_HEIGHT_M * 100:.0f} cm, objętość h²/(2·spadek) na metr; obniżenia i zlewnia z NMT (siatka 5 m).",
            f"Materia organiczna +{OM_GAIN_PCT:.0f} pkt proc.; pojemność wodna wg Saxton & Rawls (2006); efekt długofalowy.",
            "Przed budową wału, zastawki lub oczka sprawdź wymogi Prawa wodnego i skonsultuj się z doradcą ODR.",
        ],
    }


def _summary(storms, measures) -> str:
    big = storms[-1]
    parts = []
    if big["volume_total_m3"]:
        parts.append(f"Przy ulewie {big['rain_mm']:.0f} mm z działki"
                     + (" i sąsiednich pól" if big["volume_inflow_m3"] else "")
                     + f" spłynie ok. {big['volume_total_m3']:.0f} m³ wody (tyle, ile mieści ok. "
                     f"{big['volume_total_m3'] / 10:.0f} beczkowozów po 10 m³).")
    else:
        parts.append(f"Nawet przy ulewie {big['rain_mm']:.0f} mm z tej działki praktycznie nic nie spływa: "
                     "gleba przyjmuje wodę.")
    for m in measures:
        if m["key"] == "wal":
            parts.append(f"Zatrzyma ją ok. {m['value']:.0f} m wału o wysokości {BERM_HEIGHT_M * 100:.0f} cm.")
        elif m["key"] == "materia" and m["value"]:
            parts.append(f"Więcej materii organicznej to ok. {m['value']:.0f} mm wody więcej w glebie przy każdym deszczu.")
    return " ".join(parts)
