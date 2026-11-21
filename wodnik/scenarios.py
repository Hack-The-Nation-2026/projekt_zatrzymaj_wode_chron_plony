"""Scenariusze na najbliższe tygodnie: „co będzie z wodą w glebie, jeśli pogoda będzie taka jak w roku X”.

Metoda (prognoza zespołowa z danych historycznych, ang. ensemble streamflow prediction):
1. Startujemy z dzisiejszego stanu strefy korzeniowej z bilansu FAO-56 (wyczerpanie Dr).
2. Kolejne dni symulujemy tym samym bilansem, z opadem i ET₀ z tych samych dni kalendarzowych
   w każdym z lat referencyjnych (1995–2025). Każdy rok to jeden równie prawdopodobny scenariusz.
3. Gdy dla daty jest prognoza pogody, pierwsze dni bierzemy z prognozy (wspólne dla wszystkich scenariuszy).
Wynik: prawdopodobieństwo stresu wodnego w 14 i 30 dni, typowy dzień jego początku,
ilość wody potrzebna, by stresu uniknąć, oraz pasmo przebiegu zapasu wody (do wykresu).

Ograniczenia: zakłada, że przyszła pogoda przypomina tę z ostatnich 31 lat (ocieplenie klimatu
może sprawiać, że wynik jest nieco zbyt optymistyczny); nie korzysta z prognoz sezonowych.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from .crops import Crop


@dataclass
class Outlook:
    horizon_days: int
    years: int
    start_depletion_mm: float
    raw_mm: float
    taw_mm: float
    in_stress_now: bool
    p_stress_14: float  # udział scenariuszy ze stresem (Dr > RAW) w ciągu 14 dni
    p_stress_30: float
    p_severe_30: float  # silny stres: Ks < 0,5 (roślina zużywa mniej niż połowę potrzebnej wody)
    p_recovery_30: float  # gdy stres jest już teraz: udział scenariuszy, w których ustępuje
    median_onset_day: int | None  # typowy dzień początku stresu (wśród scenariuszy, w których wystąpi)
    water_needed_p50_mm: float  # woda potrzebna, by utrzymać Dr ≤ RAW przez cały horyzont
    water_needed_p90_mm: float  # to samo w suchym scenariuszu (90. percentyl)
    forecast_days_used: int
    level: str  # niskie / umiarkowane / wysokie
    summary: str
    envelope: list = field(default_factory=list)  # [{day, date, p10, p50, p90}] – zapas wody do wykresu


def _simulate(dr0: float, p: np.ndarray, e: np.ndarray, kc: np.ndarray, taw: float, raw: float, crop_p: float):
    """Bilans FAO-56 do przodu. Zwraca (przebieg Dr, przebieg Ks, woda potrzebna do uniknięcia stresu)."""
    n = len(p)
    drs, kss = np.zeros(n), np.zeros(n)
    dr = dr0
    # wariant „z nawadnianiem”: dolewamy wodę, gdy Dr przekroczy RAW (miara potrzeby wody)
    dr_irr, need = dr0, 0.0
    for i in range(n):
        etc = kc[i] * e[i]
        ks = 1.0 if dr <= raw else max(0.0, (taw - dr) / ((1 - crop_p) * taw))
        dr = min(taw, max(0.0, dr - p[i] + ks * etc))
        drs[i], kss[i] = dr, ks
        dr_irr = max(0.0, dr_irr - p[i] + etc)
        if dr_irr > raw:
            need += dr_irr - raw
            dr_irr = raw
    if dr0 > raw:  # stres już teraz: najpierw trzeba uzupełnić do progu
        need += dr0 - raw
    return drs, kss, need


def run(on: date, dr0: float, taw: float, raw: float, crop: Crop,
        hist_p: list, hist_e: list, years: list,
        fc_p: np.ndarray | None = None, fc_e: np.ndarray | None = None,
        horizon: int = 30) -> Outlook | None:
    if not hist_p:
        return None
    dates = [on + timedelta(days=i + 1) for i in range(horizon)]
    kc = np.array([crop.kc[d.month - 1] for d in dates])
    nfc = 0 if fc_p is None else min(len(fc_p), horizon)

    runs = []
    for p, e in zip(hist_p, hist_e):
        p, e = np.array(p[:horizon], dtype=float), np.array(e[:horizon], dtype=float)
        if len(p) < horizon:
            continue
        if nfc:  # pierwsze dni z prognozy, dalej z roku historycznego
            p[:nfc], e[:nfc] = fc_p[:nfc], fc_e[:nfc]
        runs.append(_simulate(dr0, p, e, kc, taw, raw, crop.p))
    if not runs:
        return None

    n = len(runs)
    drs = np.array([r[0] for r in runs])
    kss = np.array([r[1] for r in runs])
    need = np.array([r[2] for r in runs])
    stressed = drs > raw
    in_stress_now = dr0 > raw

    def share(mask) -> float:
        return round(float(np.mean(mask)), 2)

    p14 = share(stressed[:, :14].any(axis=1))
    p30 = share(stressed.any(axis=1))
    severe = share((kss < 0.5).any(axis=1))
    recovery = share((~stressed).any(axis=1)) if in_stress_now else 0.0
    onsets = [int(np.argmax(s)) + 1 for s in stressed if s.any()]
    median_onset = int(np.median(onsets)) if onsets and not in_stress_now else None

    if p30 >= 0.6 or severe >= 0.4:
        level = "wysokie"
    elif p30 >= 0.3:
        level = "umiarkowane"
    else:
        level = "niskie"

    k = lambda share_: int(round(share_ * n))  # noqa: E731
    if in_stress_now:
        summary = (f"Roślina jest już w stresie wodnym. W {k(recovery)} z {n} scenariuszy pogodowych stres ustąpi "
                   f"w ciągu {horizon} dni, a w {k(severe)} z {n} stanie się silny.")
    else:
        summary = (f"W {k(p14)} z {n} scenariuszy pogodowych roślina wejdzie w stres wodny w ciągu 14 dni, "
                   f"a w {k(p30)} z {n} w ciągu {horizon} dni.")
        if median_onset:
            summary += f" Gdy stres wystąpi, zwykle zaczyna się po ok. {median_onset} dniach."
    p50, p90 = float(np.percentile(need, 50)), float(np.percentile(need, 90))

    env = []
    for i, d in enumerate(dates):
        col = drs[:, i]
        env.append({"day": i + 1, "date": d.isoformat(),
                    "p10": round(float(np.percentile(col, 10)), 1),
                    "p50": round(float(np.percentile(col, 50)), 1),
                    "p90": round(float(np.percentile(col, 90)), 1)})

    return Outlook(horizon, n, round(dr0, 1), round(raw, 1), round(taw, 1), in_stress_now,
                   p14, p30, severe, recovery, median_onset, round(p50, 1), round(p90, 1), nfc,
                   level, summary, env)
