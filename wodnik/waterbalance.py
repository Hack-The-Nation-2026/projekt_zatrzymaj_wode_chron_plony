"""Dobowy bilans wody w strefie korzeniowej wg FAO-56 (rozdz. 8, single crop coefficient).

Dr  – wyczerpanie wody w strefie korzeniowej [mm] (0 = polowa pojemność wodna)
TAW – całkowita woda dostępna = 1000 · (θFC − θWP) · Zr
RAW – woda łatwo dostępna = p · TAW
Ks  – współczynnik stresu wodnego (1 = brak stresu)
Założenie startowe: na początku okresu gleba jest przy polowej pojemności wodnej
(typowe po zimie; dla dat jesiennych to uproszczenie – opisane w niepewności).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .crops import Crop
from .weather import Series


@dataclass
class BalanceResult:
    taw: float
    raw: float
    depletion: np.ndarray  # Dr na koniec każdego dnia
    ks: np.ndarray
    etc: np.ndarray
    eta: np.ndarray
    deep_percolation: float  # woda, która przeszła poniżej korzeni [mm]
    stress_days: int  # dni z Ks < 1 w ostatnich 30 dniach


def run(series: Series, crop: Crop, awc_m3m3: float, upto_index: int) -> BalanceResult:
    taw = 1000.0 * awc_m3m3 * crop.zr
    raw = crop.p * taw
    n = upto_index + 1
    dr = 0.0
    dep, kss, etcs, etas = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    dp_total = 0.0
    for i in range(n):
        kc = crop.kc[series.dates[i].month - 1]
        etc = kc * (0.0 if np.isnan(series.et0[i]) else series.et0[i])
        p = 0.0 if np.isnan(series.precip[i]) else series.precip[i]
        ks = 1.0 if dr <= raw else max(0.0, (taw - dr) / ((1 - crop.p) * taw))
        eta = ks * etc
        dr = dr - p + eta
        if dr < 0:
            dp_total += -dr
            dr = 0.0
        dr = min(dr, taw)
        dep[i], kss[i], etcs[i], etas[i] = dr, ks, etc, eta
    return BalanceResult(taw, raw, dep, kss, etcs, etas, dp_total, int((kss[-30:] < 0.999).sum()))
