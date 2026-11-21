"""Testy „co da retencja” (wymiarowanie na ulewę) na danych syntetycznych, bez sieci.

Uruchomienie: .venv/bin/python tests/test_whatif.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wodnik import crops, weather, whatif  # noqa: E402
from wodnik.soil import Soil  # noqa: E402

ON = date(2026, 6, 15)
N = 151
SOIL = Soil(62.0, 17.0, 2.0, 0.236, 0.13, "piasek gliniasty / glina lekka", "lekka")


def test_scs_cn_runoff():
    # TR-55: dla CN = 75 (S ≈ 84,7 mm, Ia ≈ 16,9 mm) opad 50 mm daje ok. 9,3 mm spływu, 15 mm – zero
    q = whatif.runoff([15.0, 50.0], 75)
    assert q[0] == 0.0 and abs(q[1] - 9.3) < 0.2
    assert whatif.curve_number("kukurydza", SOIL) > whatif.curve_number("pszenica_ozima", SOIL)
    assert whatif.curve_number("uzytki_zielone", SOIL) < whatif.curve_number("pszenica_ozima", SOIL)
    assert whatif.hydrologic_group(Soil(20, 40, 1, 0.3, 0.2, "", "ciężka")) == "D"


def test_sizing_and_organic_matter():
    dates = [ON - timedelta(days=N - 1 - i) for i in range(N)]
    ser = weather.Series(dates=dates, precip=np.where(np.arange(N) % 5 == 0, 6.0, 0.0),
                         et0=np.full(N, 3.5), tmax=np.full(N, 22.0))
    yrs = list(range(2016, 2026))
    clim = weather.Climate(yrs, np.zeros(10), np.zeros(10), np.zeros(10),
                           [np.full(30, 1.0) for _ in yrs], [np.full(30, 4.0) for _ in yrs])
    terr = SimpleNamespace(inflow_area_ha=8.0, slope_mean_pct=1.9,
                           outflow_points=[object(), object()], depressions=[SimpleNamespace(value=500.0)])
    crop = crops.get("pszenica_ozima")
    w = whatif.run(ser, crop, SOIL, SOIL.awc, N - 1, ON, clim, None, None, 75, 3.0, terr)
    big = w["storms"][-1]
    assert big["rain_mm"] == 50 and abs(big["volume_parcel_m3"] - 9.3 * 3.0 * 10) < 10
    assert big["volume_total_m3"] > big["volume_parcel_m3"]  # woda z sąsiednich pól
    keys = [m["key"] for m in w["measures"]]
    assert keys == ["wal", "oczko", "materia"]
    wal = w["measures"][0]
    per_m = 0.3 ** 2 / (2 * 0.019)
    assert abs(wal["value"] - big["volume_total_m3"] / per_m) < 2
    assert w["measures"][2]["value"] > 0  # więcej materii organicznej = większa pojemność wodna
    assert w["root_zone"]["taw_after_mm"] > w["root_zone"]["taw_before_mm"]
    # bez terenu nie wymiarujemy wału ani oczka
    w2 = whatif.run(ser, crop, SOIL, SOIL.awc, N - 1, ON, clim, None, None, 75, 3.0, None)
    assert [m["key"] for m in w2["measures"]] == ["materia"]


if __name__ == "__main__":
    test_scs_cn_runoff()
    test_sizing_and_organic_matter()
    print("OK")
