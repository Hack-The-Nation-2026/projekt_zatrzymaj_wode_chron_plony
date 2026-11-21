"""Testy danych do wykresów i wykresów SVG w raporcie do druku (syntetyczna pogoda, bez sieci).

Uruchomienie: .venv/bin/python tests/test_charts.py
"""

import sys
import xml.dom.minidom
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wodnik import analysis, charts, crops, waterbalance, weather  # noqa: E402

ON = date(2026, 6, 15)
N = 151


def _data():
    dates = [ON - timedelta(days=N - 1 - i) for i in range(N)]
    precip = np.where(np.arange(N) % 6 == 0, 8.0, 0.0)
    precip[5] = np.nan  # brak danych z jednego dnia nie może zepsuć wykresu
    et0 = np.full(N, 3.0)
    ser = weather.Series(dates=dates, precip=precip, et0=et0, tmax=np.full(N, 22.0))
    bal = waterbalance.run(ser, crops.get("pszenica_ozima"), 0.106, N - 1)
    yrs = list(range(2016, 2026))
    clim = weather.Climate(yrs, np.zeros(10), np.linspace(-150, 50, 10), np.full(10, 0.2))
    return ser, bal, clim, analysis._charts(ser, bal, clim, N - 1, -120.0, ON)


def test_chart_data():
    ser, bal, clim, c = _data()
    d = c["daily"]
    assert len(d["dates"]) == len(d["precip_mm"]) == len(d["et0_mm"]) == len(d["water_left_mm"]) == N
    assert d["dates"][-1] == ON.isoformat()
    assert d["precip_mm"][5] is None  # NaN → null (poprawny JSON)
    assert all(0 <= v <= d["taw_mm"] for v in d["water_left_mm"])
    assert d["stress_below_mm"] == round(bal.taw - bal.raw, 1)
    items = c["years"]["items"]
    assert [i["year"] for i in items] == list(range(2016, 2027))
    assert items[-1] == {"year": 2026, "kbw60_mm": -120.0, "current": True}


def test_svgs_are_valid_xml():
    *_, c = _data()
    scen = {"envelope": [{"day": k, "p10": 30.0, "p50": 50.0, "p90": 70.0} for k in range(1, 31)]}
    for svg in (charts.water(c, scen), charts.water(c), charts.rain_et(c), charts.years(c)):
        assert svg.startswith("<svg")
        xml.dom.minidom.parseString(svg)  # rzuca wyjątek przy błędnym SVG
    assert "dziś" in charts.water(c) and "(ten rok)" in charts.years(c)


if __name__ == "__main__":
    test_chart_data()
    test_svgs_are_valid_xml()
    print("OK")
