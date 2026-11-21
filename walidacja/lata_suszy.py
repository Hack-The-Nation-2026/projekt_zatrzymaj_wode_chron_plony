"""Sprawdzenie Wodnika na znanych latach suszy (2015, 2018, 2019, 2022 wg IUNG) na tle pozostałych lat 2015–2023.

Dla każdej działki i roku liczymy pełną analizę na 15 czerwca (pszenica ozima, okres krytyczny) i zapisujemy
poziom ryzyka, punkty ryzyka, dni stresu i percentyl bilansu wody. Wynik: walidacja/wyniki.csv i podsumowanie.

Uruchomienie: .venv/bin/python walidacja/lata_suszy.py   (ok. 30–60 min przy pierwszym uruchomieniu)
"""

import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("WODNIK_SOURCE_BUDGET", "30")
from wodnik import analysis  # noqa: E402

DROUGHT_YEARS = {2015, 2018, 2019, 2022}
YEARS = range(2015, 2024)
PARCELS = {  # działki z różnych regionów (te same co w testach regionów)
    "łódzkie (Łazisko)": "101609_2.0011.352",
    "kujawsko-pomorskie (Inowrocław)": "040704_2.0037.90/2",
    "lubelskie (Hrubieszów)": "060408_2.0139.1051/2",
    "podlaskie (Wysokie Mazowieckie)": "201310_2.0004.1034/2",
    "opolskie (Głogówek)": "161002_5.0050.597",
    "małopolskie (Miechów)": "120805_4.0001.465/11",
    "warmińsko-mazurskie (Kętrzyn)": "280801_1.0004.406",
    "pomorskie (Kościerzyna)": "220604_2.0024.118/10",
}
OUT = ROOT / "walidacja" / "wyniki.csv"
FIELDS = ["region", "dzialka", "rok", "rok_suszy", "ryzyko", "punkty", "stres_pkt", "odchylenie_pkt", "dni_stresu_30", "wyczerpanie_mm", "RAW_mm",
          "bilans60_mm", "bilans60_percentyl", "wilgotnosc_percentyl", "satelita", "sekundy", "blad"]


def one(region, pid, year):
    t = time.time()
    row = {"region": region, "dzialka": pid, "rok": year, "rok_suszy": int(year in DROUGHT_YEARS)}
    try:
        r = analysis.analyse(parcel_id=pid, on=date(year, 6, 15), crop_key="pszenica_ozima").to_dict()
        raw = r["raw"]
        row.update(ryzyko=r["risk_level"], punkty=raw["wynik_ryzyka_pkt"],
                   stres_pkt=raw["ryzyko_skladniki"]["stres_pkt"], odchylenie_pkt=raw["ryzyko_skladniki"]["odchylenie_pkt"], dni_stresu_30=raw["dni_stresu_30d"],
                   wyczerpanie_mm=raw["wyczerpanie_mm"], RAW_mm=raw["RAW_mm"], bilans60_mm=raw["kbw60_mm"],
                   bilans60_percentyl=raw["kbw60_percentyl"], wilgotnosc_percentyl=raw["wilgotnosc_percentyl"],
                   satelita=int(bool(raw["satelita"])))
    except Exception as exc:  # noqa: BLE001
        row["blad"] = repr(exc)[:200]
    row["sekundy"] = round(time.time() - t)
    print(row, flush=True)
    return row


if __name__ == "__main__":
    jobs = [(reg, pid, y) for reg, pid in PARCELS.items() for y in YEARS]
    with ThreadPoolExecutor(max_workers=3) as ex:
        rows = list(ex.map(lambda j: one(*j), jobs))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("Zapisano", OUT)
    os._exit(0)  # nie czekamy na pobieranie w tle
