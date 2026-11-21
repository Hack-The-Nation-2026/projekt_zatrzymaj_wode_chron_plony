"""Zapisuje gotowy wynik działki do katalogu demo/ (serwer wczytuje go przy starcie).

Działki demo działają bez internetu i bez limitów API, więc zabezpieczają prezentację.

    .venv/bin/python -m wodnik.demo --dzialka 101609_2.0011.352 --data 2026-06-15 \
        --uprawa pszenica_ozima --tytul "Łazisko, pszenica ozima, 15.06.2026"
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date
from pathlib import Path

from . import analysis, crops, output

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"


def _clean(obj):
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="wodnik.demo", description=__doc__.splitlines()[0])
    ap.add_argument("--dzialka", required=True)
    ap.add_argument("--data", required=True, help="RRRR-MM-DD")
    ap.add_argument("--uprawa", default="pszenica_ozima", choices=sorted(crops.CROPS))
    ap.add_argument("--tytul", help="nazwa widoczna na liście demo")
    a = ap.parse_args(argv)

    on = date.fromisoformat(a.data)
    rep = analysis.analyse(parcel_id=a.dzialka, on=on, crop_key=a.uprawa)
    slug = re.sub(r"[^a-z0-9]+", "_", f"{rep.parcel['obreb']}_{a.dzialka.split('.')[-1]}_{on}".lower()).strip("_")
    title = a.tytul or f"{rep.parcel['obreb']}, {rep.crop}, {on.strftime('%d.%m.%Y')}"
    DEMO_DIR.mkdir(exist_ok=True)
    body = {"request": {"parcel_id": a.dzialka, "date": on.isoformat(), "crop": a.uprawa},
            "title": title, "report": _clean(rep.to_dict())}
    (DEMO_DIR / f"{slug}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (DEMO_DIR / f"{slug}.geojson").write_text(json.dumps(_clean(output.geojson(rep)), ensure_ascii=False),
                                              encoding="utf-8")
    print(f"Zapisano demo/{slug}.json – ryzyko: {rep.risk_level}. Zrestartuj serwer, żeby je wczytał.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
