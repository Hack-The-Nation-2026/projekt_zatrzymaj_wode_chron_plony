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
    for kind, group in (("ocena", r.assessment), ("retencja", r.retention), ("agrotechnika", r.agrotechnics)):
        for it in group:
            if it.location:
                feats.append({"type": "Feature",
                              "geometry": {"type": "Point", "coordinates": [it.location["lon"], it.location["lat"]]},
                              "properties": {"rodzaj": kind, "tytul": it.title, "opis": it.detail}})
    return {"type": "FeatureCollection", "features": feats}


def dump_json(obj, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)


def html_report(d: dict) -> str:
    """Raport do druku / zapisu jako PDF, budowany z wyniku w formacie Report.to_dict()."""
    from datetime import datetime
    from html import escape as e

    p = d["parcel"]
    day = date.fromisoformat(d["date"]).strftime("%d.%m.%Y")
    gen = d.get("generated_at") or ""
    try:
        gen = datetime.fromisoformat(gen).strftime("%d.%m.%Y %H:%M UTC")
    except ValueError:
        pass

    def items(lst):
        out = []
        for it in lst:
            loc = it.get("location")
            out.append(
                f"<div class='it'><h3>{e(it['title'])}</h3><p>{e(it['detail'])}</p>"
                + (f"<p class='why'><b>Dlaczego:</b> {e('; '.join(it.get('because') or []))}</p>" if it.get("because") else "")
                + (f"<p class='why'><b>Miejsce:</b> {loc['lat']}, {loc['lon']}</p>" if loc else "")
                + f"<p class='conf'>Pewność: {e(it.get('confidence', ''))}</p></div>")
        return "".join(out) or "<p>Brak.</p>"

    causes = "".join(f"<li><b>{e(c['name'])}</b>: {e(c['strength'])} ({e('; '.join(c['because']))})</li>"
                     for c in d.get("causes", []))
    sc = d.get("scenarios")
    scen = (f"<h2>Co dalej: najbliższe {sc['horizon_days']} dni</h2><p>{e(sc['summary'])} "
            f"Woda potrzebna, by uniknąć stresu: ok. {sc['water_needed_p50_mm']} mm "
            f"(w suchym scenariuszu {sc['water_needed_p90_mm']} mm). Ryzyko w najbliższych tygodniach: "
            f"<b>{e(sc['level'])}</b>. Scenariusze z pogody lat {e(sc.get('period', ''))}.</p>") if sc else ""
    graphs = ""
    ch = d.get("charts")
    if ch:
        from . import charts

        yrs = charts.years(ch)
        graphs = (
            "<h3 class='gt'>Woda w glebie: ostatnie miesiące i najbliższe 30 dni</h3>"
            f"<div class='chart'>{charts.water(ch, sc)}</div>"
            "<p class='meta'>Zapas wody dostępnej dla roślin w strefie korzeni (bilans FAO-56). Linia przerywana i pasmo "
            "po prawej: typowy przebieg i rozrzut scenariuszy pogodowych.</p>"
            "<h3 class='gt'>Opad i parowanie dzień po dniu</h3>"
            f"<div class='chart'>{charts.rain_et(ch)}</div>"
            + (f"<h3 class='gt'>Ten rok na tle poprzednich lat</h3><div class='chart'>{yrs}</div>"
               f"<p class='meta'>{e(ch['years']['label'])}; czerwona linia przerywana: próg roku z wyraźnym deficytem, czerwone słupki: lata poniżej progu.</p>" if yrs else ""))
    wi = d.get("what_if")
    whatif_html = ""
    if wi:
        storms = "".join(f"<li>ulewa {st['rain_mm']:.0f} mm: spływ ok. {st['volume_total_m3']:.0f} m³ "
                         f"(z działki {st['volume_parcel_m3']:.0f} m³, z sąsiednich pól {st['volume_inflow_m3']:.0f} m³)</li>"
                         for st in wi["storms"])
        meas = "".join(f"<div class='it'><h3>{e(m['name'])}: {str(m['value']).replace('.', ',')} {e(m['unit'])}</h3>"
                       f"<p>{e(m['detail'])}</p></div>" for m in wi["measures"])
        whatif_html = (f"<h2>Co da retencja na tej działce</h2><p>{e(wi['summary'])}</p><ul>{storms}</ul>{meas}"
                       f"<p class='meta'>Założenia: {e(' '.join(wi['assumptions']))}</p>")
    return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<title>Wodnik – raport {e(p['id'])} {e(d['date'])}</title>
<style>
body{{font:14px/1.45 system-ui,Arial,sans-serif;color:#1b2e30;max-width:820px;margin:24px auto;padding:0 16px}}
h1{{font-size:22px;margin:0}} h2{{font-size:17px;margin:22px 0 6px;border-bottom:2px solid #4a9d3f;padding-bottom:3px}}
h3{{font-size:14px;margin:0 0 2px}} .it{{margin:8px 0;padding-left:10px;border-left:3px solid #c9d8cc}}
.it p{{margin:2px 0}} .why,.conf,.meta{{color:#555;font-size:12.5px}} .risk{{font-size:18px;font-weight:700}}
.box{{background:#f4f6f2;border:1px solid #d8e0da;border-radius:8px;padding:10px 12px;margin:10px 0}}
.chart{{margin:6px 0 2px;break-inside:avoid}} h3.gt{{margin:14px 0 2px}}
.btn{{margin:12px 0}} @media print{{.btn{{display:none}} body{{margin:0}}}}
</style></head><body>
<button class="btn" onclick="window.print()">Drukuj / zapisz jako PDF</button>
<h1>Wodnik – raport sytuacji wodnej działki</h1>
<p class="meta">Działka {e(p['id'])} · {e(p['obreb'])}, gm. {e(p['gmina'])}, {e(p['wojewodztwo'])} · {p['powierzchnia_ha']} ha<br>
Data analizy: {day} · uprawa: {e(d['crop'])} · raport wygenerowany: {e(gen)}</p>
<div class="box"><div class="risk">Ryzyko suszy: {e(d['risk_level'])}</div><p>{e(d['risk_summary'])}</p>
<p class="meta">Pewność całej analizy: {e(d['confidence'])}{' · główna przyczyna: ' + e(d['main_cause']) if d.get('main_cause') else ''}</p></div>
<h2>1. Ocena sytuacji wodnej</h2>{items(d['assessment'])}
{graphs}
{scen}
{whatif_html}
<h2>2. Przyczyny</h2><ul>{causes}</ul>
<h2>3. Retencja – zatrzymaj wodę</h2>{items(d['retention'])}
<h2>4. Agrotechnika – ogranicz straty wody</h2>{items(d['agrotechnics'])}
<h2>5. Nawadnianie – dopiero na końcu</h2>{items(d['irrigation'])}
<h2>Ograniczenia raportu</h2><ul>{''.join(f'<li>{e(u)}</li>' for u in d['uncertainty'])}</ul>
<h2>Źródła danych</h2><ul>{''.join(f'<li>{e(s)}</li>' for s in d['data_sources'])}</ul>
<p class="meta">Raport wygenerowany automatycznie przez prototyp Wodnik (HackNation 2026) na podstawie danych publicznych.
Zalecenia wymagają sprawdzenia w terenie; nie zastępują porady doradcy rolniczego.</p>
</body></html>"""
