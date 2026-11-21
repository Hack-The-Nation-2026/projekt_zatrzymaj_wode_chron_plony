"""Raport tekstowy dla rolnika oraz GeoJSON do mapy."""

from __future__ import annotations

import json
from datetime import date

from .analysis import Report


def _items(lines: list, items, numbered: bool = True) -> None:
    for n, it in enumerate(items, 1):
        head = f"{n}. " if numbered else "• "
        lines.append(f"  {head}{it.title}")
        lines.append(f"     {it.detail}")
        if it.location:
            lines.append(f"     Miejsce: {it.location['lat']}, {it.location['lon']}  ({it.location['maps']})")
        if it.because:
            lines.append(f"     Dlaczego: {'; '.join(it.because)}")
        lines.append(f"     Pewność: {it.confidence}")


def text(r: Report) -> str:
    p = r.parcel
    d = date.fromisoformat(r.date).strftime("%d.%m.%Y")
    L = [
        "=" * 78,
        f"WODNIK · działka {p['id']} · {p['obreb']}, gm. {p['gmina']} · {str(p['powierzchnia_ha']).replace('.', ',')} ha",
        f"Data analizy: {d} · uprawa: {r.crop}",
        "=" * 78,
        "",
        f"RYZYKO SUSZY: {r.risk_level.upper()}",
        f"  {r.risk_summary}",
        "",
        "1. OCENA SYTUACJI WODNEJ",
    ]
    _items(L, r.assessment, numbered=False)
    L += ["", "2. PRZYCZYNY"]
    if r.main_cause:
        L.append(f"  Główna przyczyna: {r.main_cause}")
    for c in r.causes:
        L.append(f"  • {c.name}: {c.strength}  ({'; '.join(c.because)})")
    L += ["", "3. RETENCJA – zatrzymaj wodę"]
    _items(L, r.retention)
    L += ["", "4. AGROTECHNIKA – ogranicz straty wody"]
    _items(L, r.agrotechnics)
    L += ["", "5. NAWADNIANIE – dopiero na końcu"]
    _items(L, r.irrigation)
    L += ["", f"PEWNOŚĆ CAŁEJ ANALIZY: {r.confidence}", "Ograniczenia:"]
    L += [f"  – {u}" for u in r.uncertainty]
    L += ["", "Źródła danych:"] + [f"  – {s}" for s in r.data_sources]
    return "\n".join(L)


def geojson(r: Report) -> dict:
    feats = [{"type": "Feature", "geometry": r.parcel["geometria_wgs84"],
              "properties": {"rodzaj": "dzialka", "id": r.parcel["id"], "ryzyko": r.risk_level}}]
    for group in (r.retention,):
        for it in group:
            if it.location:
                feats.append({"type": "Feature",
                              "geometry": {"type": "Point", "coordinates": [it.location["lon"], it.location["lat"]]},
                              "properties": {"rodzaj": "rekomendacja", "tytul": it.title, "opis": it.detail}})
    return {"type": "FeatureCollection", "features": feats}


def dump_json(obj, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
