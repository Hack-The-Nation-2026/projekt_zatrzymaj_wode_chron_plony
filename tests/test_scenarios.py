"""Testy scenariuszy na syntetycznej pogodzie (bez sieci).

Uruchomienie: .venv/bin/python -m pytest -q   (albo: .venv/bin/python tests/test_scenarios.py)
"""

import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wodnik import crops, scenarios  # noqa: E402

WHEAT = crops.get("pszenica_ozima")
ON = date(2026, 6, 1)  # czerwiec: Kc pszenicy 1,15
TAW, RAW = 106.0, 58.3
N = 30


def _years(rain_mm_per_day: list, et0: float = 4.0):
    """Jeden „rok” na każdą wartość dziennego opadu, stałe ET₀."""
    return ([np.full(N, r) for r in rain_mm_per_day], [np.full(N, et0) for _ in rain_mm_per_day],
            list(range(1995, 1995 + len(rain_mm_per_day))))


def test_dry_years_give_stress_and_high_level():
    p, e, y = _years([0.0] * 31)  # 31 lat bez deszczu
    o = scenarios.run(ON, 20.0, TAW, RAW, WHEAT, p, e, y)
    assert o.p_stress_30 == 1.0
    assert o.level == "wysokie"
    # ETc = 1,15 · 4 = 4,6 mm/d, od 20 mm do progu 58,3 mm → stres ok. 9. dnia
    assert o.median_onset_day == 9
    assert o.water_needed_p50_mm > 0


def test_wet_years_give_no_stress():
    p, e, y = _years([6.0] * 31)  # opad większy niż zużycie
    o = scenarios.run(ON, 20.0, TAW, RAW, WHEAT, p, e, y)
    assert o.p_stress_30 == 0.0
    assert o.level == "niskie"
    assert o.water_needed_p90_mm == 0.0


def test_mixed_years_probability_matches_share_of_dry_years():
    p, e, y = _years([0.0] * 10 + [6.0] * 21)  # 10 suchych z 31
    o = scenarios.run(ON, 20.0, TAW, RAW, WHEAT, p, e, y)
    assert abs(o.p_stress_30 - round(10 / 31, 2)) < 0.011
    assert o.level == "umiarkowane"


def test_already_stressed_reports_recovery():
    p, e, y = _years([0.0] * 20 + [8.0] * 11)
    o = scenarios.run(ON, 70.0, TAW, RAW, WHEAT, p, e, y)
    assert o.in_stress_now
    assert abs(o.p_recovery_30 - round(11 / 31, 2)) < 0.011
    assert "już w stresie" in o.summary


def test_forecast_overrides_first_days():
    p, e, y = _years([6.0] * 31)  # mokre lata…
    fc_p, fc_e = np.zeros(7), np.full(7, 6.0)  # …ale prognoza: tydzień upału bez deszczu
    o = scenarios.run(ON, 40.0, TAW, RAW, WHEAT, p, e, y, fc_p, fc_e)
    assert o.forecast_days_used == 7
    assert o.p_stress_14 == 1.0  # 40 + 7·6,9 mm > RAW w każdym scenariuszu


def test_envelope_is_ordered():
    p, e, y = _years(list(np.linspace(0, 6, 31)))
    o = scenarios.run(ON, 20.0, TAW, RAW, WHEAT, p, e, y)
    assert len(o.envelope) == N
    assert all(d["p10"] <= d["p50"] <= d["p90"] for d in o.envelope)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
