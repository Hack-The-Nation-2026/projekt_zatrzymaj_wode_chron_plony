"""Analiza w sekwencji KOWR:
ocena sytuacji wodnej → przyczyny → retencja → agrotechnika → ewentualne nawadnianie.

Każdy wniosek ma uzasadnienie (konkretne wartości i źródła) oraz poziom pewności.
Logika jest regułowa i jawna: progi są opisane w kodzie i w dokumentacji.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date, timedelta

import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

import numpy as np

from . import (crops, hydrology, parcel as parcel_mod, satellite, scenarios, soil as soil_mod,
               terrain as terrain_mod, waterbalance, weather, whatif)
from .http import DataSourceError

HISTORY_DAYS = 150
# Budżet czasu na źródła opcjonalne (teren, rowy, gleba, satelita), liczony od startu pobierania.
# Źródło, które nie zdąży, pomijamy w tym raporcie (opis w niepewności), a pobieranie trwa dalej w tle
# i trafia do pamięci podręcznej, więc kolejna analiza tej działki jest pełna.
SOURCE_BUDGET_S = float(os.environ.get("WODNIK_SOURCE_BUDGET", "60"))
_POOL = ThreadPoolExecutor(max_workers=16, thread_name_prefix="wodnik-src")
DEFICIT_YEAR_KBW60 = -100.0  # mm; próg „roku z wyraźnym deficytem” (heurystyka, do kalibracji z IUNG)


def num(x: float, nd: int = 0) -> str:
    """Liczba w zapisie polskim (przecinek dziesiętny)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "b.d."
    s = f"{x:.{nd}f}".replace(".", ",")
    return s.replace("-", "−")


@dataclass
class Item:
    """Rekomendacja lub wniosek z uzasadnieniem."""

    title: str
    detail: str
    because: list = field(default_factory=list)
    confidence: str = "średnia"  # wysoka / średnia / niska
    location: dict | None = None
    priority: int = 2  # 1 = najważniejsze


@dataclass
class Cause:
    key: str
    name: str
    strength: str  # silna / umiarkowana / słaba
    score: int
    because: list = field(default_factory=list)


@dataclass
class Report:
    parcel: dict
    date: str
    crop: str
    risk_level: str
    risk_summary: str
    assessment: list
    causes: list
    main_cause: str | None
    retention: list
    agrotechnics: list
    irrigation: list
    uncertainty: list
    confidence: str
    data_sources: list
    raw: dict
    scenarios: dict | None = None  # „co dalej”: 30 dni, scenariusze z 10 lat (scenarios.Outlook)
    generated_at: str = ""  # kiedy policzono raport (UTC, ISO 8601)
    charts: dict | None = None  # dane do wykresów: przebieg dzienny i tło wieloletnie (_charts)
    what_if: dict | None = None  # „co da retencja”: porównanie wariantów działań (whatif.run)

    def to_dict(self) -> dict:
        return asdict(self)


def _r(x, d=1):
    x = float(x)
    return None if np.isnan(x) else round(x, d)


def _charts(series, bal, clim, i_on: int, kbw60: float, on) -> dict:
    """Dane do wykresów w raporcie (wszystko w mm, dzień po dniu do daty analizy włącznie).

    daily: opad, parowanie referencyjne (ET0) i zapas wody dostępnej dla roślin (TAW − Dr);
    years: bilans opad − parowanie z 60 dni przed tą samą datą w latach tła i w roku analizy.
    """
    dates = series.dates[: i_on + 1]
    return {
        "daily": {
            "dates": [d.isoformat() for d in dates],
            "precip_mm": [_r(v) for v in series.precip[: i_on + 1]],
            "et0_mm": [_r(v) for v in series.et0[: i_on + 1]],
            "water_left_mm": [_r(bal.taw - v) for v in bal.depletion],
            "taw_mm": _r(bal.taw),
            "stress_below_mm": _r(bal.taw - bal.raw),  # poniżej tego zapasu roślina jest w stresie
        },
        "years": {
            "items": [{"year": y, "kbw60_mm": _r(v), "current": False} for y, v in zip(clim.years, clim.kbw60)]
                     + [{"year": on.year, "kbw60_mm": _r(kbw60), "current": True}],
            "deficit_threshold_mm": DEFICIT_YEAR_KBW60,
            "label": f"bilans opad − parowanie z 60 dni przed {on.strftime('%d.%m')}",
        },
    }


_SIDES = ["północnym", "północno-wschodnim", "wschodnim", "południowo-wschodnim",
          "południowym", "południowo-zachodnim", "zachodnim", "północno-zachodnim"]


def _side(p, spot) -> str:
    """Kierunek punktu względem środka działki, np. „północnym” (do opisu „na północnym krańcu”)."""
    import math

    clat, clon = p.centroid_latlon
    dx = (spot.lon - clon) * math.cos(math.radians(clat))
    dy = spot.lat - clat
    ang = (math.degrees(math.atan2(dx, dy)) + 360) % 360  # 0 = północ, zgodnie z ruchem wskazówek
    return _SIDES[int((ang + 22.5) // 45) % 8]


def _side_f(p, spot) -> str:
    """Kierunek w rodzaju żeńskim, np. „wschodnia” (do „wschodnia część działki”)."""
    w = _side(p, spot)
    return w[:-2] + "a" if w.endswith("ym") else w[:-1] + "a"


def _loc(spot) -> dict:
    return {"lat": round(spot.lat, 6), "lon": round(spot.lon, 6),
            "maps": f"https://www.google.com/maps?q={spot.lat:.6f},{spot.lon:.6f}"}


STEPS = [("parcel", "Granice działki"), ("weather", "Pogoda: ostatnie miesiące i 10 lat wstecz"),
         ("soil", "Gleba"), ("terrain", "Ukształtowanie terenu"),
         ("hydrology", "Cieki, rowy i zbiorniki (BDOT10k)"), ("satellite", "Zdjęcia satelitarne"),
         ("analysis", "Wnioski i zalecenia")]


def analyse(parcel_id: str | None = None, point: tuple | None = None, on: date | None = None,
            crop_key: str = "pszenica_ozima", today: date | None = None, progress=None) -> Report:
    """`progress(step, state)` informuje o etapach (klucze z STEPS; state: "running" albo "done").
    Etapy pobierania danych biegną równolegle."""
    today = today or date.today()
    on = on or today
    crop = crops.get(crop_key)
    uncertainty: list[str] = []
    sources: list[str] = ["GUGiK – Usługa Lokalizacji Działek Katastralnych (ULDK)"]

    skipped: set = set()  # źródła pominięte po przekroczeniu budżetu czasu (ich późne „done” ignorujemy)

    def step(name: str, state: str = "running") -> None:
        if progress and (name not in skipped or state == "failed"):
            progress(name, state)

    # --- Dane wejściowe ---------------------------------------------------------
    step("parcel")
    p = parcel_mod.by_id(parcel_id) if parcel_id else parcel_mod.by_point(*point)
    lat, lon = p.centroid_latlon
    step("parcel", "done")
    end = on + timedelta(days=7) if on >= today - timedelta(days=weather.ARCHIVE_LAG_DAYS) else on

    # Źródła danych są od siebie niezależne, więc pobieramy je równolegle (cel: wynik w ≤ 30 s).
    # Pogoda jest konieczna (błąd przerywa analizę); pozostałe źródła są opcjonalne – ich brak
    # obniża pewność i jest wprost opisany w raporcie.
    def task(name, fn, optional=True):
        step(name)
        try:
            out = fn()
        except Exception as exc:  # noqa: BLE001 – opcjonalne źródło nie może zatrzymać analizy
            step(name, "failed")
            if not optional:
                raise
            return None, exc
        step(name, "done")
        return out, None

    def get_weather():
        with ThreadPoolExecutor(max_workers=2) as ex2:
            fs = ex2.submit(weather.daily_series, lat, lon, on - timedelta(days=HISTORY_DAYS), end, today)
            fc = ex2.submit(weather.climatology, lat, lon, on)
            return fs.result(), fc.result()

    t_start = time.monotonic()
    f_weather = _POOL.submit(task, "weather", get_weather, False)
    f_soil = _POOL.submit(task, "soil", lambda: soil_mod.near(lat, lon))
    f_terr = _POOL.submit(task, "terrain", lambda: terrain_mod.analyse(p))
    f_hydro = _POOL.submit(task, "hydrology", lambda: hydrology.analyse(p))
    f_sat = _POOL.submit(task, "satellite", lambda: satellite.analyse(p, on))
    (series, clim), _ = f_weather.result()  # pogoda jest konieczna (ma własne limity czasu)

    def within_budget(f, name):
        try:
            return f.result(timeout=max(0.0, t_start + SOURCE_BUDGET_S - time.monotonic()))
        except FuturesTimeout:
            skipped.add(name)
            step(name, "failed")
            return None, DataSourceError(
                f"usługa nie odpowiedziała w {SOURCE_BUDGET_S:.0f} s; dane pobierają się w tle, "
                "więc ponowna analiza tej działki będzie pełniejsza")

    soil, e_soil = within_budget(f_soil, "soil")
    terr, e_terr = within_budget(f_terr, "terrain")
    hydro, e_hydro = within_budget(f_hydro, "hydrology")
    sat, e_sat = within_budget(f_sat, "satellite")

    sources += series.sources
    if on not in series.dates:
        raise DataSourceError(f"Brak danych pogodowych dla daty {on}.")
    i_on = series.dates.index(on)
    period = f"{clim.years[0]}–{clim.years[-1]}"
    sources.append(f"Open-Meteo archive – tło wieloletnie {period} (ERA5/ERA5-Land)")
    if soil:
        sources.append("ISRIC SoilGrids 2.0 (uziarnienie, węgiel organiczny) + funkcja Saxton & Rawls (2006)")
    else:
        uncertainty.append(f"Brak danych glebowych ({e_soil}); przyjęto glebę średnią.")
    if terr:
        sources.append("GUGiK – Numeryczny Model Terenu z LIDAR (1 m), usługa WCS")
        if terr.partial:
            uncertainty.append("Działka jest bardzo duża: analiza terenu objęła jej środkowy fragment "
                               "(ok. 2,5 × 2,5 km); punkty odpływu na pozostałej części nie są wskazane.")
    else:
        uncertainty.append(f"Analiza terenu niedostępna: {e_terr}")
    if hydro:
        sources.append("GUGiK – BDOT10k (rowy, cieki, wody powierzchniowe, mokradła, lasy), usługa WMS")
    else:
        uncertainty.append(f"Dane hydrologiczne (BDOT10k) niedostępne: {e_hydro}")
    if sat:
        sources.append("Copernicus Sentinel-2 L2A (katalog Earth Search, AWS Open Data) – NDVI, NDMI")
    else:
        uncertainty.append(f"Dane satelitarne niedostępne: {e_sat}")
    step("analysis")

    awc = soil.awc if soil else 0.14
    # Spływ powierzchniowy (SCS-CN): woda, która spłynęła z pola, nie zasila strefy korzeniowej.
    cn = whatif.curve_number(crop.key, soil)
    series_in = replace(series, precip=whatif.infiltrated(series.precip, cn))
    bal = waterbalance.run(series_in, crop, awc, i_on)

    P = series.precip[: i_on + 1]
    E = series.et0[: i_on + 1]
    kbw30 = float(np.nansum(P[-30:] - E[-30:]))
    kbw60 = float(np.nansum(P[-60:] - E[-60:]))
    p30 = float(np.nansum(P[-30:]))
    pct30 = weather.percentile_of(kbw30, clim.kbw30)
    pct60 = weather.percentile_of(kbw60, clim.kbw60)
    sm = float(series.soil_moisture[i_on]) if series.soil_moisture is not None else float("nan")
    pct_sm = weather.percentile_of(sm, clim.soil_moisture)
    hot_days = int((series.tmax[max(0, i_on - 29): i_on + 1] >= 30).sum())
    deficit_years = int((clim.kbw60 <= DEFICIT_YEAR_KBW60).sum())
    n_years = len(clim.years)
    dr, taw, raw = float(bal.depletion[-1]), bal.taw, bal.raw
    ks = float(bal.ks[-1])
    in_critical = on.month in crop.critical_months

    fc_p = fc_e = None
    if end > on:
        fc_p = float(np.nansum(series.precip[i_on + 1:]))
        fc_e = float(np.nansum(series.et0[i_on + 1:]))

    # Scenariusze „co dalej” (30 dni): bilans FAO-56 do przodu z pogodą z każdego z 10 lat tła;
    # dla dat bieżących pierwsze dni z prognozy.
    outlook = scenarios.run(
        on, dr, taw, raw, crop, [whatif.infiltrated(x, cn) for x in clim.future_precip], clim.future_et0, clim.years,
        whatif.infiltrated(series.precip[i_on + 1:], cn) if end > on else None,
        np.nan_to_num(series.et0[i_on + 1:]) if end > on else None,
        horizon=weather.SCENARIO_DAYS)

    # --- 1. Ocena sytuacji wodnej -------------------------------------------------
    stress_pts = 0  # niedobór wody w strefie korzeni wg bilansu FAO-56 (stan bezwzględny)
    anomaly_pts = 0  # odchylenie od normy: bilans, wilgotność gleby, stan roślin na tle lat i uprawy
    if dr > raw:
        stress_pts += 2
    if dr > 0.8 * taw:
        stress_pts += 1
    if pct60 <= 10:
        anomaly_pts += 2
    elif pct60 <= 25:
        anomaly_pts += 1
    if pct_sm <= 10:
        anomaly_pts += 2
    elif pct_sm <= 25:
        anomaly_pts += 1
    # Satelita: zawartość wody w roślinach (NDMI) i zmiana zieloności (NDVI) między zdjęciami.
    # Progi heurystyczne: NDMI ≥ 0,2 dobre uwodnienie, 0–0,2 umiarkowane, < 0 niskie (przy NDVI ≥ 0,4).
    # Interpretacja zależy od uprawy (crops.NDVI_EXPECTED, crops.SENESCENCE): spadek zieloności
    # w okresie dojrzewania lub po pokosie jest naturalny i nie jest liczony jako objaw suszy.
    sc = sat.current if sat else None
    ndvi_change = (sc.ndvi - sat.previous.ndvi) if sc and sat.previous else None
    sat_month = date.fromisoformat(sc.date).month if sc else on.month
    growing = sat_month in range(4, 10)
    ripening = sat_month in crops.SENESCENCE.get(crop.key, ())
    mowing = sat_month in crops.MOWING_POSSIBLE.get(crop.key, ())
    expected = crops.NDVI_EXPECTED.get(crop.key, {}).get(sat_month)
    below_expected = bool(sc and expected and sc.ndvi < expected[0])
    if sc and growing and not ripening:
        if sc.ndvi >= 0.4 and sc.ndmi < 0:
            anomaly_pts += 1
        elif below_expected and not mowing:
            anomaly_pts += 1  # zieloność niższa niż typowa dla tej uprawy w tym miesiącu
        elif sc.ndmi < 0.2 and ndvi_change is not None and ndvi_change <= -0.1 and not mowing:
            anomaly_pts += 1
    score = stress_pts + anomaly_pts
    if in_critical and score >= 2:
        score += 1
    # Poziom ryzyka oznacza suszę na tle tego, co normalne dla tego miejsca. Walidacja na latach 2015–2023
    # (walidacja/WYNIKI.md) pokazała, że sam stres w bilansie FAO-56 w okresie wegetacji występuje prawie
    # zawsze (model nie uwzględnia podsiąku), więc ryzyko co najmniej umiarkowane wymaga odchylenia od
    # normy z ostatnich 10 lat albo bardzo głębokiego wyczerpania wody (powyżej 80% zapasu).
    severe_depletion = dr > 0.8 * taw
    if score >= 5 and anomaly_pts >= 1:
        risk = "wysokie"
    elif score >= 3 and (anomaly_pts >= 1 or severe_depletion):
        risk = "umiarkowane"
    else:
        risk = "niskie"

    assessment = [
        Item("Zapas wody w strefie korzeniowej",
             f"Wyczerpane ok. {num(dr)} mm z {num(taw)} mm wody dostępnej dla roślin "
             f"(próg stresu: {num(raw)} mm). " +
             ("Roślina jest w stresie wodnym." if dr > raw else "Roślina nie jest jeszcze w stresie wodnym."),
             [f"bilans dobowy FAO-56 od {series.dates[0].strftime('%d.%m.%Y')}",
              f"{crop.name}: Kc z miesiąca, korzenie {num(crop.zr, 1)} m",
              f"retencja użyteczna gleby {num(awc * 1000)} mm/m"],
             "średnia"),
        Item("Klimatyczny bilans wodny (opad − parowanie)",
             f"Ostatnie 30 dni: {num(kbw30)} mm, ostatnie 60 dni: {num(kbw60)} mm. "
             f"Bilans 60-dniowy tak niski lub niższy wystąpił w tym terminie w {num(pct60)}% lat "
             f"{period}.",
             [f"opad 30 dni: {num(p30)} mm", f"dni z temp. ≥ 30°C w 30 dniach: {hot_days}"],
             "średnia"),
        Item("Wilgotność gleby (model ERA5-Land, 0–100 cm)",
             f"{num(sm, 3)} m³/m³: tak sucho lub bardziej było w tym terminie w {num(pct_sm)}% lat."
             if not np.isnan(sm) else
             "Brak danych dla tej daty: reanaliza ERA5-Land ma ok. 6 dni opóźnienia.",
             ["niezależny wskaźnik z reanalizy, siatka ok. 9 km"], "średnia" if not np.isnan(sm) else "niska"),
        Item("Skłonność miejsca do suszy (tło wieloletnie)",
             f"W {deficit_years} z {n_years} lat bilans 60-dniowy w tym terminie spadał poniżej "
             f"{num(DEFICIT_YEAR_KBW60)} mm.",
             ["odróżnia bieżącą suszę od stałej podatności miejsca"], "średnia"),
    ]
    if sc:
        lvl = "niska" if sc.ndmi < 0 else "umiarkowana" if sc.ndmi < 0.2 else "dobra"
        sdate = date.fromisoformat(sc.date)
        detail = (f"Zdjęcie z {sdate.strftime('%d.%m.%Y')}: zieloność (NDVI) {num(sc.ndvi, 2)}, "
                  f"zawartość wody w roślinach (NDMI) {num(sc.ndmi, 2)}, czyli {lvl}.")
        if sat.previous:
            pdate = date.fromisoformat(sat.previous.date).strftime("%d.%m.%Y")
            detail += (f" Od {pdate} zieloność zmieniła się o {num(ndvi_change, 2)}, "
                       f"a woda w roślinach o {num(sc.ndmi - sat.previous.ndmi, 2)}.")
        if expected:
            detail += (f" Typowa zieloność uprawy {crop.name} w tym miesiącu to ok. {num(expected[0], 2)}–"
                       f"{num(expected[1], 2)}: " + ("obecna jest niższa, co wskazuje na osłabienie roślin."
                                                     if below_expected else "obecna mieści się w normie lub jest wyższa."))
        if sc.ndvi < 0.3 and growing and not ripening:
            detail += (" Bardzo niska zieloność w sezonie może też oznaczać, że pole jest po zbiorze albo rośnie "
                       "na nim inna uprawa niż wybrana: sprawdź wybór uprawy.")
        if ripening:
            detail += f" To okres dojrzewania i zbioru uprawy {crop.name}: spadek zieloności jest naturalny."
        elif mowing:
            detail += " Na użytkach zielonych spadek zieloności może wynikać z pokosu."
        because = [f"Sentinel-2, {num(sc.valid_share * 100)}% działki bez chmur",
                   f"najsuchsze 10% pola: NDMI ≤ {num(sc.ndmi_p10, 2)} (miejsce zaznaczone na mapie)",
                   f"interpretacja dla uprawy: {crop.name} (orientacyjne zakresy NDVI, do kalibracji)"]
        if (on - sdate).days > 10:
            because.append(f"zdjęcie sprzed {(on - sdate).days} dni (nowsze były zachmurzone)")
        loc = ({"lat": sc.dry_lat, "lon": sc.dry_lon,
                "maps": f"https://www.google.com/maps?q={sc.dry_lat},{sc.dry_lon}"} if sc.dry_lat else None)
        assessment.insert(3, Item("Stan roślin z satelity (Sentinel-2)", detail, because,
                                  "średnia" if sc.valid_share >= 0.8 else "niska", loc))
    else:
        assessment.insert(3, Item("Stan roślin z satelity (Sentinel-2)",
                                  "Brak bezchmurnego zdjęcia działki z ostatnich 30 dni."
                                  if sat else "Dane satelitarne były niedostępne podczas analizy.",
                                  ["Sentinel-2 przelatuje co 2–5 dni, ale chmury często zasłaniają pole"], "niska"))
    if hydro:
        assessment.append(Item(
            "Woda w otoczeniu działki (BDOT10k)",
            ("Przy działce lub na jej granicy biegnie rów melioracyjny. " if hydro.near("rowy", 15) else "") +
            f"W promieniu 500 m: zbiorniki i oczka: {hydro.count_500m.get('wody', 0)}, "
            f"mokradła: {hydro.count_500m.get('mokradla', 0)}.",
            hydrology.describe(hydro), "średnia"))
    if outlook:
        why = [f"start: wyczerpanie {num(dr)} mm, próg stresu {num(raw)} mm",
               f"pogoda z tych samych dni w {outlook.years} latach {period}",
               "zakłada pogodę podobną do ostatnich lat; przy ocieplaniu się klimatu wynik może być zbyt optymistyczny"]
        if outlook.forecast_days_used:
            why.insert(2, f"pierwsze {outlook.forecast_days_used} dni z prognozy pogody")
        assessment.append(Item(f"Co dalej: najbliższe {outlook.horizon_days} dni ({outlook.years} scenariuszy pogodowych)",
                               outlook.summary + f" Ryzyko w najbliższych tygodniach: {outlook.level}.",
                               why, "średnia"))
    if fc_p is not None:
        assessment.append(Item("Prognoza na 7 dni",
                               f"Opad ok. {num(fc_p)} mm, parowanie ok. {num(fc_e)} mm.",
                               ["prognoza numeryczna, niepewność rośnie z każdym dniem"], "niska"))
    risk_summary = {
        "wysokie": "Rośliny odczuwają niedobór wody, a sytuacja jest gorsza niż zwykle w tym terminie.",
        "umiarkowane": "Zapas wody się kurczy; warto działać zanim pojawi się wyraźny stres.",
        "niskie": "Obecnie brak wyraźnego niedoboru wody; warto budować odporność na kolejne susze.",
    }[risk]
    if risk == "wysokie" and pct60 > 25 and pct_sm > 25:
        # Wysokie ryzyko z powodu stresu roślin i stanu upraw, choć bilans nie odbiega od ostatnich lat.
        risk_summary = ("Rośliny odczuwają wyraźny niedobór wody w ważnym okresie; w ostatnich latach w tym terminie "
                        "bywało podobnie, więc to miejsce jest szczególnie narażone na suszę.")
    if risk == "umiarkowane" and dr > raw:
        # Roślina już jest w stresie, ale w ostatnich latach w tym terminie bywało podobnie: nie piszemy „zanim”.
        risk_summary = ("Rośliny już odczuwają niedobór wody, ale w ostatnich latach w tym terminie bywało podobnie "
                        "lub gorzej; warto działać teraz i budować odporność na kolejne susze.")
    if risk == "niskie" and dr > raw:
        # Stres w bilansie, ale typowy dla tego miejsca i terminu: niskie ryzyko suszy, nie „brak niedoboru”.
        risk_summary = ("Rośliny odczuwają niedobór wody typowy dla tego terminu w ostatnich latach, bez oznak "
                        "wyjątkowej suszy; warto budować odporność na kolejne susze.")
    if risk != "wysokie" and outlook and outlook.level == "wysokie":
        risk_summary += " Uwaga: w scenariuszach na najbliższe 30 dni ryzyko stresu jest wysokie."

    # --- 2. Przyczyny ----------------------------------------------------------------
    causes: list[Cause] = []
    s_met = (2 if pct60 <= 10 else 1 if pct60 <= 25 else 0) + (1 if hot_days >= 5 else 0)
    causes.append(Cause("meteo", "Niedobór opadów i wysoka temperatura",
                        "silna" if s_met >= 2 else "umiarkowana" if s_met == 1 else "słaba", s_met,
                        [f"bilans 60 dni {num(kbw60)} mm (percentyl {num(pct60)})", f"dni upalnych: {hot_days}"]))
    if soil:
        s_soil = (2 if soil.category == "lekka" else 0) + (1 if soil.awc_mm_per_m < 120 else 0) + (1 if soil.soc_pct < 1.0 else 0)
        causes.append(Cause("gleba", "Gleba słabo magazynuje wodę",
                            "silna" if s_soil >= 3 else "umiarkowana" if s_soil >= 1 else "słaba", s_soil,
                            [f"{soil.texture_label}: piasek {num(soil.sand_pct)}%, ił {num(soil.clay_pct)}%",
                             f"retencja użyteczna {num(soil.awc_mm_per_m)} mm/m",
                             f"węgiel organiczny {num(soil.soc_pct, 1)}%"]))
    if terr:
        out_ha = sum(s.value for s in terr.outflow_points)
        s_run = (2 if terr.slope_mean_pct > 4 or terr.steep_share_pct > 20 else 1 if terr.slope_mean_pct > 2 else 0) \
            + (1 if terr.concentrated_flow_share_pct > 5 else 0) + (1 if out_ha > 1 else 0)
        causes.append(Cause("splyw", "Woda szybko odpływa z pola",
                            "silna" if s_run >= 3 else "umiarkowana" if s_run >= 1 else "słaba", s_run,
                            [f"średni spadek {num(terr.slope_mean_pct, 1)}%, 10% działki > {num(terr.slope_p90_pct, 1)}%",
                             f"deniwelacja {num(terr.elev_max - terr.elev_min, 1)} m",
                             f"linie skoncentrowanego spływu: {num(terr.concentrated_flow_share_pct, 1)}% działki",
                             f"punkty odpływu: {len(terr.outflow_points)}"]))
        # Materiał naukowy KOWR: brak elementów krajobrazu spowalniających obieg wody (oczka, mokradła,
        # zadrzewienia) nasila odpływ.
        if hydro and not hydro.near("lasy", 100) and not hydro.count_500m.get("wody") \
                and not hydro.count_500m.get("mokradla"):
            c = causes[-1]
            c.score += 1
            c.strength = "silna" if c.score >= 3 else "umiarkowana"
            c.because.append("w otoczeniu brak zadrzewień, oczek i mokradeł spowalniających odpływ (BDOT10k)")
    causes.sort(key=lambda c: -c.score)
    main = causes[0] if causes and causes[0].score > 0 else None
    if in_critical:
        uncertainty_crop = f"Termin przypada na okres krytyczny dla uprawy: {crop.critical_label}."
    else:
        uncertainty_crop = None

    # --- 3. Retencja ------------------------------------------------------------------
    retention: list[Item] = []
    if terr:
        for k, spot in enumerate(terr.outflow_points[:2]):
            where = _side(p, spot)
            x, y = parcel_mod.to_pl92(spot.lat, spot.lon)
            d_row = hydro.at_point("rowy", x, y) if hydro else None
            d_ciek = hydro.at_point("cieki", x, y) if hydro else None
            why = [spot.note, "kierunki spływu z NMT (LIDAR), algorytm D8"]
            if d_row is not None and d_row <= 30:
                title = f"Zastawka na rowie przy odpływie ({where})"
                detail = (f"Woda opuszcza działkę na jej {where} krańcu, a ok. {num(d_row)} m dalej biegnie rów "
                          "melioracyjny. Zastawka lub próg piętrzący na rowie zatrzyma wodę w okolicy pola "
                          "(uzgodnij ze spółką wodną lub Wodami Polskimi).")
                why.append(f"rów melioracyjny {num(d_row)} m od punktu odpływu (BDOT10k)")
            elif d_ciek is not None and d_ciek <= 30:
                title = f"Spowolnij odpływ do cieku ({where})"
                detail = (f"Woda z działki trafia na jej {where} krańcu do cieku oddalonego o ok. {num(d_ciek)} m. "
                          "Pas zadarniony lub zadrzewiony przy brzegu spowolni odpływ i zatrzyma glebę.")
                why.append(f"ciek {num(d_ciek)} m od punktu odpływu (BDOT10k)")
            else:
                title = f"Zatrzymaj wodę w miejscu odpływu ({where})"
                detail = (f"Woda opuszcza działkę na jej {where} krańcu. Nie ma tu rowu w BDOT10k, więc najlepiej "
                          "sprawdzi się niski wał, próg lub pas zadarniony z płytkim obniżeniem, które spowolni odpływ.")
                why.append("brak rowu ani cieku w promieniu 30 m (BDOT10k)" if hydro
                           else "brak danych BDOT10k: sprawdź w terenie, czy jest rów")
            retention.append(Item(title, detail, why, "średnia", _loc(spot), priority=1 if k == 0 else 2))
        for spot in terr.depressions[:2]:
            retention.append(Item(
                f"Oczko wodne lub mokradło w naturalnym obniżeniu ({_side_f(p, spot)} część działki)",
                f"Teren sam zbiera tu wodę (ok. {num(spot.value)} m³ pojemności zagłębienia). "
                "Pogłębienie lub ochrona obniżenia daje retencję niskim kosztem.",
                [spot.note, "analiza zagłębień na NMT 5 m"], "średnia", _loc(spot), priority=1))
        if terr.slope_mean_pct > 2 or terr.concentrated_flow_share_pct > 5:
            retention.append(Item(
                "Pas buforowy w poprzek spadku i zadarnienie linii spływu",
                "Trwały pas trawy, krzewów lub zadrzewień w poprzek kierunku spływu spowalnia wodę "
                "i ogranicza erozję. Linie, którymi woda spływa skupiona, warto zadarnić.",
                [f"średni spadek {num(terr.slope_mean_pct, 1)}%",
                 f"skoncentrowany spływ na {num(terr.concentrated_flow_share_pct, 1)}% działki"],
                "średnia", priority=2))
        if terr.inflow_area_ha > p.area_ha * 0.5:
            retention.append(Item(
                "Spowolnij wodę napływającą z sąsiednich pól",
                f"Na działkę spływa woda z ok. {num(terr.inflow_area_ha, 1)} ha spoza niej. "
                "Miedza, pas zadrzewień lub płytki rów rozsączający na górnej granicy zatrzyma ją na polu "
                "zamiast pozwolić jej przepłynąć. Najlepiej wspólnie z sąsiadami lub spółką wodną.",
                [f"zlewnia zewnętrzna {num(terr.inflow_area_ha, 1)} ha wobec {num(p.area_ha, 1)} ha działki"],
                "średnia", priority=2))
    if hydro:
        d_row, d_ciek = hydro.distance_m.get("rowy"), hydro.distance_m.get("cieki")
        if (d_row is not None and d_row <= 100) or (d_ciek is not None and d_ciek <= 200):
            what = (f"rów melioracyjny {num(d_row)} m od działki" if d_row is not None and d_row <= 100
                    else f"ciek {num(d_ciek)} m od działki")
            retention.append(Item(
                "Retencja w rowach i ciekach w otoczeniu",
                f"W pobliżu jest {what}. Okresowe piętrzenie wody (zastawki sterowane wiosną i po ulewach) "
                "podniesie poziom wód gruntowych pod polem. To działanie dla spółki wodnej lub gminy, "
                "często z dofinansowaniem.",
                hydrology.describe(hydro), "średnia", priority=2))
        if not hydro.near("lasy", 100):
            retention.append(Item(
                "Zadrzewienia śródpolne lub pas krzewów",
                "W pobliżu działki brakuje zadrzewień. Pas drzew i krzewów wzdłuż granicy pola ogranicza wiatr, "
                "parowanie i spływ, a z czasem zwiększa retencję krajobrazu.",
                [f"najbliższy las lub zadrzewienie: {num(hydro.distance_m['lasy'])} m" if hydro.distance_m.get("lasy")
                 is not None else "brak lasów i zadrzewień w promieniu 500 m (BDOT10k)",
                 "zalecenie NWRM (KE 2014): retencja krajobrazowa"], "średnia", priority=3))
        if hydro.near("mokradla", 300):
            retention.append(Item(
                "Chroń mokradło w pobliżu",
                f"Ok. {num(hydro.distance_m['mokradla'])} m od działki jest mokradło. Nie odwadniaj go: mokradła "
                "magazynują wodę i oddają ją w czasie suszy.",
                ["mokradło w BDOT10k"], "średnia", priority=3))
    retention.append(Item(
        "Jeśli działka jest zmeliorowana: steruj odpływem",
        "Zamknięcie zastawek na rowach i studzienek drenarskich po roztopach i wiosennych deszczach "
        "zatrzymuje wodę w profilu glebowym na okres wegetacji.",
        ["sieć drenarska pod polem nie jest w danych publicznych (BDOT10k zawiera tylko rowy otwarte)"],
        "niska", priority=3))

    # --- 4. Agrotechnika ----------------------------------------------------------------
    agro: list[Item] = []
    weak_soil = soil is not None and (soil.category == "lekka" or soil.awc_mm_per_m < 120 or soil.soc_pct < 1.5)
    if weak_soil or soil is None:
        agro.append(Item(
            "Więcej materii organicznej: międzyplony i resztki pożniwne",
            "Każdy punkt procentowy próchnicy zwiększa pojemność wodną gleby. Międzyplony, pozostawianie "
            "słomy i nawozy naturalne to najtańsza „retencja” na lekkich glebach.",
            [f"gleba {soil.category}, retencja użyteczna {num(soil.awc_mm_per_m)} mm/m" if soil else "brak danych glebowych",
             "Minasny i in. 2017 (4 per mille); materiał KOWR"], "średnia", priority=1))
    agro.append(Item(
        "Uprawa ograniczająca parowanie",
        "Uproszczona uprawa (bez orki lub płytsza), mulcz z resztek i szybkie przykrycie gleby "
        "po zbiorze zmniejszają straty wody z powierzchni.",
        ["zgodne z zasadami naturalnej retencji (NWRM, KE 2014)"], "średnia", priority=2))
    if risk != "niskie" and on.month in (3, 4, 5, 6, 7, 8):
        agro.append(Item(
            "W czasie suszy: nie przesuszaj gleby zabiegami",
            "Odłóż zabiegi spulchniające i uprawki, które otwierają glebę i przyspieszają parowanie.",
            [f"ryzyko suszy: {risk}"], "średnia", priority=1))
    if soil is not None and soil.category == "lekka" and deficit_years >= n_years * 0.3:
        agro.append(Item(
            "Dobór gatunków i odmian odpornych na suszę",
            "Na lekkiej glebie z częstymi deficytami wody rozważ gatunki i odmiany o mniejszych wymaganiach "
            "wodnych (np. żyto, pszenżyto) oraz wcześniejsze terminy siewu.",
            [f"deficyt w {deficit_years} z {n_years} lat", f"gleba {soil.category}"], "niska", priority=3))

    # --- 5. Nawadnianie (na końcu) ----------------------------------------------------
    irrigation: list[Item] = []
    if dr > raw:
        dose = dr - 0.2 * taw
        why = [f"wyczerpanie {num(dr)} mm > próg stresu {num(raw)} mm"]
        if outlook:
            why.append(f"by uniknąć stresu przez {outlook.horizon_days} dni: ok. {num(outlook.water_needed_p50_mm)} mm "
                       f"(w suchym scenariuszu {num(outlook.water_needed_p90_mm)} mm)")
        if fc_p is not None and fc_p >= dr * 0.6:
            irrigation.append(Item(
                "Wstrzymaj się z nawadnianiem",
                f"Prognoza zapowiada ok. {num(fc_p)} mm opadu w 7 dni, co może w dużej części uzupełnić niedobór.",
                why + [f"prognoza opadu {num(fc_p)} mm"], "niska", priority=1))
        elif crop.irrigation_usually_profitable:
            irrigation.append(Item(
                "Nawadnianie uzasadnione, po działaniach retencyjnych",
                f"Do uzupełnienia ok. {num(dose)} mm (ok. {num(dose * 10)} m³/ha). "
                "Podawaj w 2–3 dawkach, rano lub wieczorem. Sprawdź wymogi Prawa wodnego "
                "(zgłoszenie lub pozwolenie wodnoprawne) przed poborem wody.",
                why + ([uncertainty_crop] if uncertainty_crop else []) +
                ["uprawa, dla której nawadnianie jest zwykle opłacalne"],
                "średnia", priority=2))
        elif in_critical:
            irrigation.append(Item(
                "Tylko jeśli masz już instalację: teraz jest okres krytyczny",
                f"Niedobór ok. {num(dose)} mm (ok. {num(dose * 10)} m³/ha) przypada na okres największej "
                "wrażliwości uprawy. Dla tej uprawy budowa nawadniania rzadko się zwraca, ale istniejącą "
                "instalację warto użyć teraz, w 2–3 dawkach. Sprawdź wymogi Prawa wodnego przed poborem wody.",
                why + [uncertainty_crop], "średnia", priority=2))
        else:
            irrigation.append(Item(
                "Nawadnianie zwykle nieopłacalne dla tej uprawy",
                f"Niedobór ok. {num(dose)} mm, ale dla tej uprawy poza okresem krytycznym koszt nawadniania "
                "rzadko się zwraca. Priorytetem jest retencja i agrotechnika.",
                why, "średnia", priority=3))
    else:
        detail = "Zapas wody w glebie jest powyżej progu stresu dla tej uprawy."
        why = [f"wyczerpanie {num(dr)} mm ≤ próg {num(raw)} mm"]
        if outlook and outlook.p_stress_30 >= 0.5:
            detail += (f" Ale w {int(round(outlook.p_stress_30 * outlook.years))} z {outlook.years} scenariuszy stres "
                       f"pojawi się w ciągu {outlook.horizon_days} dni: zaplanuj działania z kroków 3–4 już teraz.")
            why.append(f"woda potrzebna w {outlook.horizon_days} dni: ok. {num(outlook.water_needed_p50_mm)} mm "
                       f"(w suchym scenariuszu {num(outlook.water_needed_p90_mm)} mm)")
        irrigation.append(Item("Nawadnianie nie jest teraz potrzebne", detail, why, "średnia", priority=3))

    # --- Niepewność ----------------------------------------------------------------------
    uncertainty += [
        "Pogoda pochodzi z reanalizy (siatka ok. 9–25 km): lokalne burze mogą dać inny opad niż w modelu.",
        "Gleba z modelu SoilGrids (250 m) – docelowo mapa glebowo-rolnicza IUNG lub dane z badań gleby rolnika.",
        "Bilans wodny zakłada pełne uwilgotnienie gleby na początku okresu i miesięczne Kc wg FAO-56.",
        "Wskaźniki satelitarne (NDVI, NDMI) oceniamy progami heurystycznymi; piksel 10–20 m, chmury mogą ograniczać dostępność zdjęć.",
        "Rowy, cieki i zbiorniki z BDOT10k odczytujemy z obrazu mapy (dokładność ok. ±2–4 m); "
        "drenaż podziemny i stan urządzeń melioracyjnych nie są znane.",
        f"Scenariusze na 30 dni zakładają pogodę jak w latach {period}; nie są prognozą konkretnej pogody.",
    ]
    if uncertainty_crop:
        uncertainty.insert(0, uncertainty_crop)
    overall = "średnia" if soil and terr else "niska"

    # „Co da retencja”: ten sam bilans i te same scenariusze z działaniami na działce (wodnik/whatif.py)
    try:
        what = whatif.run(series, crop, soil, awc, i_on, on, clim,
                          series.precip[i_on + 1:] if end > on else None,
                          np.nan_to_num(series.et0[i_on + 1:]) if end > on else None,
                          cn, p.area_ha, terr)
    except Exception:  # noqa: BLE001 – symulacja jest dodatkiem, nie może zatrzymać raportu
        what = None

    return Report(
        parcel={"id": p.id, "gmina": p.commune, "obreb": p.region, "powiat": p.county,
                "wojewodztwo": p.voivodeship, "powierzchnia_ha": round(p.area_ha, 2),
                "srodek": {"lat": round(lat, 6), "lon": round(lon, 6)},
                "geometria_wgs84": p.geom_wgs84.__geo_interface__},
        date=on.isoformat(), crop=crop.name, risk_level=risk, risk_summary=risk_summary,
        assessment=assessment, causes=causes, main_cause=main.name if main else None,
        retention=sorted(retention, key=lambda r: r.priority),
        agrotechnics=sorted(agro, key=lambda r: r.priority),
        irrigation=irrigation, uncertainty=uncertainty, confidence=overall,
        data_sources=sources,
        raw={"kbw30_mm": round(kbw30, 1), "kbw60_mm": round(kbw60, 1), "kbw60_percentyl": round(pct60, 1),
             "kbw30_percentyl": round(pct30, 1), "wilgotnosc_gleby_m3m3": round(sm, 3),
             "wilgotnosc_percentyl": round(pct_sm, 1), "dni_upalne_30d": hot_days,
             "wyczerpanie_mm": round(dr, 1), "TAW_mm": round(taw, 1), "RAW_mm": round(raw, 1), "Ks": round(ks, 2),
             "dni_stresu_30d": bal.stress_days, "lata_z_deficytem": deficit_years, "lata_referencyjne": n_years,
             "gleba": asdict(soil) if soil else None, "teren": asdict(terr) if terr else None,
             "satelita": asdict(sat) if sat else None,
             "hydrologia": {"odleglosc_m": hydro.distance_m, "liczba_500m": hydro.count_500m,
                            "rozdzielczosc_m": hydro.resolution_m} if hydro else None,
             "okres_tla": period,
             "scenariusze_pkt": {"p_stres_14": outlook.p_stress_14, "p_stres_30": outlook.p_stress_30}
             if outlook else None,
             "wynik_ryzyka_pkt": score,
             "ryzyko_skladniki": {"stres_pkt": stress_pts, "odchylenie_pkt": anomaly_pts,
                                  "okres_krytyczny_pkt": score - stress_pts - anomaly_pts}},
        scenarios={**asdict(outlook), "period": period} if outlook else None,
        charts=_charts(series, bal, clim, i_on, kbw60, on),
        what_if=what,
        generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        .replace(microsecond=0).isoformat(),
    )
