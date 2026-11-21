"""Analiza w sekwencji KOWR:
ocena sytuacji wodnej → przyczyny → retencja → agrotechnika → ewentualne nawadnianie.

Każdy wniosek ma uzasadnienie (konkretne wartości i źródła) oraz poziom pewności.
Logika jest regułowa i jawna: progi są opisane w kodzie i w dokumentacji.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

import numpy as np

from . import crops, parcel as parcel_mod, satellite, soil as soil_mod, terrain as terrain_mod, waterbalance, weather
from .http import DataSourceError

HISTORY_DAYS = 150
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

    def to_dict(self) -> dict:
        return asdict(self)


def _loc(spot) -> dict:
    return {"lat": round(spot.lat, 6), "lon": round(spot.lon, 6),
            "maps": f"https://www.google.com/maps?q={spot.lat:.6f},{spot.lon:.6f}"}


STEPS = [("parcel", "Granice działki"), ("weather", "Pogoda z ostatnich miesięcy"), ("soil", "Gleba"),
         ("terrain", "Ukształtowanie terenu"), ("satellite", "Zdjęcia satelitarne"),
         ("analysis", "Wnioski i zalecenia")]


def analyse(parcel_id: str | None = None, point: tuple | None = None, on: date | None = None,
            crop_key: str = "pszenica_ozima", today: date | None = None, progress=None) -> Report:
    """`progress(step)` jest wołane na początku każdego etapu (klucze z STEPS)."""
    today = today or date.today()
    on = on or today
    crop = crops.get(crop_key)
    uncertainty: list[str] = []
    sources: list[str] = ["GUGiK – Usługa Lokalizacji Działek Katastralnych (ULDK)"]

    def step(name: str) -> None:
        if progress:
            progress(name)

    # --- Dane wejściowe ---------------------------------------------------------
    step("parcel")
    p = parcel_mod.by_id(parcel_id) if parcel_id else parcel_mod.by_point(*point)
    lat, lon = p.centroid_latlon
    step("weather")

    end = on + timedelta(days=7) if on >= today - timedelta(days=weather.ARCHIVE_LAG_DAYS) else on
    series = weather.daily_series(lat, lon, on - timedelta(days=HISTORY_DAYS), end, today=today)
    sources += series.sources
    if on not in series.dates:
        raise DataSourceError(f"Brak danych pogodowych dla daty {on}.")
    i_on = series.dates.index(on)
    clim = weather.climatology(lat, lon, on)
    sources.append(f"Open-Meteo archive – tło wieloletnie {weather.CLIMATE_YEARS[0]}–{weather.CLIMATE_YEARS[1]} (ERA5/ERA5-Land)")

    step("soil")
    try:
        soil = soil_mod.at_point(lat, lon)
        sources.append("ISRIC SoilGrids 2.0 (uziarnienie, węgiel organiczny) + funkcja Saxton & Rawls (2006)")
    except DataSourceError as exc:
        soil = None
        uncertainty.append(f"Brak danych glebowych ({exc}); przyjęto glebę średnią.")

    step("terrain")
    try:
        terr = terrain_mod.analyse(p)
        sources.append("GUGiK – Numeryczny Model Terenu z LIDAR (1 m), usługa WCS")
    except DataSourceError as exc:
        terr = None
        uncertainty.append(f"Analiza terenu niedostępna: {exc}")

    step("satellite")
    try:
        sat = satellite.analyse(p, on)
        sources.append("Copernicus Sentinel-2 L2A (katalog Earth Search, AWS Open Data) – NDVI, NDMI")
    except Exception as exc:  # sieć, katalog STAC, odczyt rastrów – satelita jest uzupełnieniem, nie warunkiem
        sat = None
        uncertainty.append(f"Dane satelitarne niedostępne: {exc}")
    step("analysis")

    awc = soil.awc if soil else 0.14
    bal = waterbalance.run(series, crop, awc, i_on)

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

    # --- 1. Ocena sytuacji wodnej -------------------------------------------------
    score = 0
    if dr > raw:
        score += 2
    if dr > 0.8 * taw:
        score += 1
    if pct60 <= 10:
        score += 2
    elif pct60 <= 25:
        score += 1
    if pct_sm <= 10:
        score += 2
    elif pct_sm <= 25:
        score += 1
    # Satelita: zawartość wody w roślinach (NDMI) i zmiana zieloności (NDVI) między zdjęciami.
    # Progi heurystyczne: NDMI ≥ 0,2 dobre uwodnienie, 0–0,2 umiarkowane, < 0 niskie (przy NDVI ≥ 0,4).
    sc = sat.current if sat else None
    ndvi_change = (sc.ndvi - sat.previous.ndvi) if sc and sat.previous else None
    growing = on.month in range(4, 10)
    if sc and growing and sc.ndvi >= 0.4:
        if sc.ndmi < 0:
            score += 1
        elif sc.ndmi < 0.2 and ndvi_change is not None and ndvi_change <= -0.1:
            score += 1
    if in_critical and score >= 2:
        score += 1
    risk = "wysokie" if score >= 5 else "umiarkowane" if score >= 3 else "niskie"

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
             f"{weather.CLIMATE_YEARS[0]}–{weather.CLIMATE_YEARS[1]}.",
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
        because = [f"Sentinel-2, {num(sc.valid_share * 100)}% działki bez chmur",
                   f"najsuchsze 10% pola: NDMI ≤ {num(sc.ndmi_p10, 2)} (miejsce zaznaczone na mapie)",
                   "progi heurystyczne; spadek zieloności może też oznaczać naturalne dojrzewanie"]
        if (on - sdate).days > 10:
            because.append(f"zdjęcie sprzed {(on - sdate).days} dni (nowsze były zachmurzone)")
        loc = ({"lat": sc.dry_lat, "lon": sc.dry_lon,
                "maps": f"https://www.google.com/maps?q={sc.dry_lat},{sc.dry_lon}"} if sc.dry_lat else None)
        assessment.insert(3, Item("Stan roślin z satelity (Sentinel-2)", detail, because,
                                  "średnia" if sc.valid_share >= 0.8 else "niska", loc))
    else:
        assessment.insert(3, Item("Stan roślin z satelity (Sentinel-2)",
                                  "Brak bezchmurnego zdjęcia działki z ostatnich 30 dni.",
                                  ["Sentinel-2 przelatuje co 2–5 dni, ale chmury często zasłaniają pole"], "niska"))
    if fc_p is not None:
        assessment.append(Item("Prognoza na 7 dni",
                               f"Opad ok. {num(fc_p)} mm, parowanie ok. {num(fc_e)} mm.",
                               ["prognoza numeryczna, niepewność rośnie z każdym dniem"], "niska"))
    risk_summary = {
        "wysokie": "Rośliny odczuwają niedobór wody, a sytuacja jest wyraźnie gorsza niż zwykle w tym terminie.",
        "umiarkowane": "Zapas wody się kurczy; warto działać zanim pojawi się wyraźny stres.",
        "niskie": "Obecnie brak wyraźnego niedoboru wody; warto budować odporność na kolejne susze.",
    }[risk]

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
            retention.append(Item(
                "Zatrzymaj wodę w miejscu odpływu",
                "Woda opuszcza działkę w tym punkcie. Jeśli jest tu rów: zastawka lub próg piętrzący. "
                "Jeśli nie: niski wał lub pas zadarniony z płytkim obniżeniem, które spowolni odpływ.",
                [spot.note, "kierunki spływu z NMT (LIDAR), algorytm D8",
                 "BDOT10k (rowy) jeszcze nie podłączony: sprawdź w terenie, czy jest rów"],
                "średnia", _loc(spot), priority=1 if k == 0 else 2))
        for spot in terr.depressions[:2]:
            retention.append(Item(
                "Oczko wodne lub mokradło w naturalnym obniżeniu",
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
    retention.append(Item(
        "Jeśli działka jest zmeliorowana: steruj odpływem",
        "Zamknięcie zastawek na rowach i studzienek drenarskich po roztopach i wiosennych deszczach "
        "zatrzymuje wodę w profilu glebowym na okres wegetacji.",
        ["dane o urządzeniach melioracyjnych nie są publicznie dostępne w jednym źródle"], "niska", priority=3))

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
        irrigation.append(Item(
            "Nawadnianie nie jest teraz potrzebne",
            "Zapas wody w glebie jest powyżej progu stresu dla tej uprawy.",
            [f"wyczerpanie {num(dr)} mm ≤ próg {num(raw)} mm"], "średnia", priority=3))

    # --- Niepewność ----------------------------------------------------------------------
    uncertainty += [
        "Pogoda pochodzi z reanalizy (siatka ok. 9–25 km): lokalne burze mogą dać inny opad niż w modelu.",
        "Gleba z modelu SoilGrids (250 m) – docelowo mapa glebowo-rolnicza IUNG lub dane z badań gleby rolnika.",
        "Bilans wodny zakłada pełne uwilgotnienie gleby na początku okresu i miesięczne Kc wg FAO-56.",
        "Wskaźniki satelitarne (NDVI, NDMI) oceniamy progami heurystycznymi; piksel 10–20 m, chmury mogą ograniczać dostępność zdjęć.",
        "Rowy i urządzenia melioracyjne nie są jeszcze uwzględnione (BDOT10k – w planie).",
    ]
    if uncertainty_crop:
        uncertainty.insert(0, uncertainty_crop)
    overall = "średnia" if soil and terr else "niska"

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
             "wynik_ryzyka_pkt": score},
    )
