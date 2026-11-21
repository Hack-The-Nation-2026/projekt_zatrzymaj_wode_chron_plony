"""Uruchomienie z wiersza poleceń.

Przykłady:
  python -m wodnik --dzialka 101609_2.0011.352 --data 2026-06-15 --uprawa pszenica_ozima
  python -m wodnik --punkt 51.545,19.949 --uprawa ziemniaki --json wynik.json --geojson mapa.geojson
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from . import analysis, crops, output
from .http import DataSourceError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="wodnik", description="Analiza sytuacji wodnej działki rolnej.")
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--dzialka", help="identyfikator działki, np. 101609_2.0011.352")
    where.add_argument("--punkt", help="współrzędne 'lat,lon' punktu na działce (WGS84)")
    ap.add_argument("--data", help="data analizy RRRR-MM-DD (domyślnie dziś)")
    ap.add_argument("--uprawa", default="pszenica_ozima", choices=sorted(crops.CROPS))
    ap.add_argument("--json", help="zapisz pełny wynik do pliku JSON")
    ap.add_argument("--geojson", help="zapisz działkę i miejsca rekomendacji do GeoJSON")
    a = ap.parse_args(argv)

    point = None
    if a.punkt:
        try:
            lat, lon = (float(v) for v in a.punkt.split(","))
            point = (lat, lon)
        except ValueError:
            ap.error("--punkt podaj jako 'lat,lon', np. 51.545,19.949")
    try:
        on = date.fromisoformat(a.data) if a.data else None
    except ValueError:
        ap.error("--data podaj jako RRRR-MM-DD")

    try:
        rep = analysis.analyse(parcel_id=a.dzialka, point=point, on=on, crop_key=a.uprawa)
    except (DataSourceError, ValueError) as exc:
        print(f"Błąd: {exc}", file=sys.stderr)
        return 1

    print(output.text(rep))
    if a.json:
        output.dump_json(rep.to_dict(), a.json)
    if a.geojson:
        output.dump_json(output.geojson(rep), a.geojson)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
