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


def _parcel_map_svg(d: dict) -> str:
    """Rysuje szkic SVG konturu działki (WKT/GeoJSON) wraz z punktami zaleceń/oceny."""
    import math
    from html import escape as e

    geom = (d.get("parcel") or {}).get("geometria_wgs84")
    if not geom:
        return ""
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    rings = []
    if gtype == "Polygon":
        rings = coords
    elif gtype == "MultiPolygon":
        for poly in coords:
            rings.extend(poly)
    pts = [pt for ring in rings for pt in ring if isinstance(pt, (list, tuple)) and len(pt) >= 2]
    if len(pts) < 3:
        return ""

    lons = [pt[0] for pt in pts]
    lats = [pt[1] for pt in pts]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    clat = (min_lat + max_lat) / 2.0
    cos_lat = max(0.2, math.cos(math.radians(clat)))

    spots = []
    for kind, label_prefix, color, lst in (
        ("ocena", "Najsuchsze miejsce", "#c0392b", d.get("assessment") or []),
        ("retencja", "Retencja", "#1d5f9a", d.get("retention") or []),
    ):
        for it in lst:
            loc = it.get("location")
            if loc and loc.get("lat") is not None and loc.get("lon") is not None:
                spots.append((float(loc["lon"]), float(loc["lat"]), f"{label_prefix}: {it.get('title', '')}", color))

    all_lons = lons + [s[0] for s in spots]
    all_lats = lats + [s[1] for s in spots]
    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)

    dx = max((max_lon - min_lon) * cos_lat, 1e-5)
    dy = max(max_lat - min_lat, 1e-5)
    w, h, pad = 260, 170, 20
    scale = min((w - 2 * pad) / dx, (h - 2 * pad) / dy)
    ox = (w - dx * scale) / 2.0
    oy = (h - dy * scale) / 2.0

    def proj(lon, lat):
        x = ox + (lon - min_lon) * cos_lat * scale
        y = h - (oy + (lat - min_lat) * scale)
        return x, y

    polys = []
    for ring in rings:
        if len(ring) >= 3:
            p_str = " ".join(f"{proj(pt[0], pt[1])[0]:.1f},{proj(pt[0], pt[1])[1]:.1f}" for pt in ring)
            polys.append(f'<polygon points="{p_str}" fill="#e6f0e6" stroke="#4a9d3f" stroke-width="2"/>')

    markers = []
    for idx, (lon, lat, title, color) in enumerate(spots, 1):
        x, y = proj(lon, lat)
        markers.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{color}" stroke="#fff" stroke-width="1.5">'
            f'<title>{e(title)}</title></circle>'
            f'<text x="{x + 8:.1f}" y="{y + 4:.1f}" font-size="10" font-weight="700" fill="{color}">#{idx}</text>'
        )

    legend = "".join(
        f"<div style='font-size:11.5px;color:#334;margin-top:2px'>"
        f"<b style='color:{c}'>#{i}</b> ({lat:.5f}, {lon:.5f}) – {e(t)}</div>"
        for i, (lon, lat, t, c) in enumerate(spots, 1)
    )
    north = (f'<g transform="translate({w - 18},18)" fill="#5b6b6d" font-size="9" font-weight="700">'
             '<path d="M0,-8 L4,2 L0,0 L-4,2 Z" fill="#5b6b6d"/><text x="0" y="11" text-anchor="middle">N</text></g>')
    svg = (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Szkic granic działki" '
           f'style="background:#fafcfa;border:1px solid #d8e0da;border-radius:6px;flex-shrink:0">'
           f'{"".join(polys)}{"".join(markers)}{north}</svg>')
    return (f"<div style='display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin:10px 0'>"
            f"{svg}<div style='flex:1;min-width:220px'>"
            f"<div style='font-size:12.5px;font-weight:700;color:#1b2e30'>Szkic granic działki i wskazanych punktów</div>"
            f"<div style='font-size:12px;color:#555'>Środek działki: {d['parcel']['srodek']['lat']}, {d['parcel']['srodek']['lon']}</div>"
            f"{legend or '<div style=\"font-size:12px;color:#555;margin-top:3px\">Kontur działki z GUGiK ULDK.</div>'}"
            f"</div></div>")


def html_report(d: dict) -> str:
    """Raport do druku / zapisu jako PDF, budowany z wyniku w formacie Report.to_dict()."""
    from datetime import datetime
    from html import escape as e

    p = d["parcel"]
    d_obj = date.fromisoformat(d["date"])
    day = d_obj.strftime("%d.%m.%Y")
    gen = d.get("generated_at") or ""
    gen_date = None
    try:
        gen_dt = datetime.fromisoformat(gen)
        gen_date = gen_dt.date()
        gen = gen_dt.strftime("%d.%m.%Y %H:%M UTC")
    except ValueError:
        pass

    raw = d.get("raw") or {}
    dr = raw.get("wyczerpanie_mm")
    raw_thr = raw.get("RAW_mm")
    taw = raw.get("TAW_mm")
    pct60 = raw.get("kbw60_percentyl")
    in_stress = (dr is not None and raw_thr is not None and dr > raw_thr)
    severe_stress = (dr is not None and taw is not None and dr > 0.8 * taw)
    if severe_stress:
        crop_stress_lbl = f"silny stres wodny (wyczerpane {str(dr).replace('.', ',')} mm przy progu {str(raw_thr).replace('.', ',')} mm)"
    elif in_stress:
        crop_stress_lbl = f"w stresie wodnym (wyczerpane {str(dr).replace('.', ',')} mm przy progu {str(raw_thr).replace('.', ',')} mm)"
    elif dr is not None and raw_thr is not None:
        crop_stress_lbl = f"bez stresu wodnego (wyczerpane {str(dr).replace('.', ',')} mm, próg stresu {str(raw_thr).replace('.', ',')} mm)"
    else:
        crop_stress_lbl = "brak danych bilansu"

    norm_note = (f" (bilans 60-dniowy na poziomie {str(round(pct60)).replace('.', ',')}. percentyla z ostatnich lat)"
                 if pct60 is not None else "")

    missing_sources = []
    if raw.get("teren") is None:
        missing_sources.append("brak analizy rzeźby terenu (NMT)")
    if raw.get("gleba") is None:
        missing_sources.append("brak lokalnych danych glebowych")
    if raw.get("satelita") is None:
        missing_sources.append("brak aktualnego bezchmurnego zdjęcia satelitarnego")
    if raw.get("hydrologia") is None:
        missing_sources.append("brak danych o rowach i ciekach (BDOT10k)")

    conf_val = d.get("confidence", "")
    if conf_val == "niska" and missing_sources:
        conf_explain = f"{e(conf_val)} ({e(', '.join(missing_sources))}; dane glebowe z siatki 250 m)"
    else:
        conf_explain = f"{e(conf_val)} (dane glebowe z modelu SoilGrids 250 m i pogoda z siatki 9–25 km)"

    hist_banner = ""
    if gen_date and (gen_date - d_obj).days > 14:
        hist_banner = (f"<p class='meta' style='color:#8a5a00;margin:4px 0 0'><b>Uwaga (analiza archiwalna):</b> "
                       f"raport dotyczy stanu na dzień <b>{day}</b> (wygenerowano {e(gen)}). "
                       f"Zalecenia z określeniem „teraz” odnoszą się do daty analizy.</p>")

    sc = d.get("scenarios")
    outlook_line = (f"<div style='margin-top:3px'><b>Prognoza na {sc['horizon_days']} dni ({sc['years']} scenariuszy):</b> "
                    f"ryzyko w najbliższych tygodniach <b>{e(sc['level'])}</b></div>") if sc else ""

    parcel_map = _parcel_map_svg(d)

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
        dates_list = (ch.get("daily") or {}).get("dates") or []
        d_span = (f" (okres {date.fromisoformat(dates_list[0]).strftime('%d.%m.%Y')} – "
                  f"{date.fromisoformat(dates_list[-1]).strftime('%d.%m.%Y')}, {len(dates_list)} dni)"
                  if len(dates_list) >= 2 else "")
        graphs = (
            "<h3 class='gt'>Woda w glebie: ostatnie miesiące i najbliższe 30 dni</h3>"
            f"<div class='chart'>{charts.water(ch, sc)}</div>"
            "<p class='meta'>Zapas wody dostępnej dla roślin w strefie korzeni (bilans FAO-56). Linia przerywana po prawej "
            "pokazuje typowy przebieg (medianę), a szersze pasmo – rozrzut między suchymi a deszczowymi latami historycznymi.</p>"
            f"<h3 class='gt'>Opad i parowanie dzień po dniu{e(d_span)}</h3>"
            f"<div class='chart'>{charts.rain_et(ch)}</div>"
            "<p class='meta'>Suma opadu i parowania na tym wykresie obejmuje cały okres symulacji bilansu wodnego (ok. 5 miesięcy); "
            "wskaźnik KBW w tekście dotyczy ostatnich 30 lub 60 dni przed datą analizy.</p>"
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
    glossary = (
        "<div class='box' style='font-size:12px;color:#334;break-inside:avoid'>"
        "<b>Słowniczek skrótów w raporcie:</b> "
        "<b>KBW</b> – klimatyczny bilans wodny (opad minus parowanie); "
        "<b>ET0</b> – parowanie referencyjne (ile wody wyparowałoby z dobrze uwodnionej roślinności); "
        "<b>FAO-56 / Kc</b> – standard obliczania potrzeb wodnych upraw ze współczynnikiem rozwojowym rośliny (Kc); "
        "<b>NDVI / NDMI</b> – satelitarne wskaźniki zieloności (kondycji) i uwodnienia liści; "
        "<b>SCS-CN</b> – metoda obliczania, jaka część ulewy spływa po powierzchni pola; "
        "<b>retencja użyteczna (mm/m)</b> – ilość wody, jaką metr głębokości gleby potrafi zatrzymać dla roślin "
        "(gleby lekkie ok. 80–120 mm/m, średnie 130–180 mm/m, ciężkie powyżej 180 mm/m)."
        "</div>"
    )
    return f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<title>Wodnik – raport {e(p['id'])} {e(d['date'])}</title>
<style>
@page{{margin:14mm}}
body{{font:13.5px/1.42 system-ui,Arial,sans-serif;color:#1b2e30;max-width:820px;margin:20px auto;padding:0 16px}}
h1{{font-size:21px;margin:0}} h2{{font-size:16.5px;margin:18px 0 6px;border-bottom:2px solid #4a9d3f;padding-bottom:3px;break-after:avoid}}
h3{{font-size:13.5px;margin:0 0 2px;break-after:avoid}} .it{{margin:6px 0;padding-left:10px;border-left:3px solid #c9d8cc;break-inside:avoid}}
.it p{{margin:2px 0}} .why,.conf,.meta{{color:#555;font-size:12px}} .risk{{font-size:16.5px;font-weight:700}}
.box{{background:#f4f6f2;border:1px solid #d8e0da;border-radius:8px;padding:10px 12px;margin:8px 0;break-inside:avoid}}
.chart{{margin:6px 0 2px;break-inside:avoid}} h3.gt{{margin:12px 0 2px;break-after:avoid}}
ul{{margin:6px 0;padding-left:20px}} li{{margin:2px 0}}
.btn{{margin:10px 0}} @media print{{.btn{{display:none}} body{{margin:0;padding:0}}}}
</style></head><body>
<button class="btn" onclick="window.print()">Drukuj / zapisz jako PDF</button>
<h1>Wodnik – raport sytuacji wodnej działki</h1>
<p class="meta">Działka {e(p['id'])} · {e(p['obreb'])}, gm. {e(p['gmina'])}, {e(p['wojewodztwo'])} · {p['powierzchnia_ha']} ha<br>
Data analizy: {day} · uprawa: {e(d['crop'])} · raport wygenerowany: {e(gen)}</p>
{hist_banner}
<div class="box">
  <div class="risk">Susza na tle normy wieloletniej: {e(d['risk_level'])}{e(norm_note)}</div>
  <div style="font-size:14.5px;margin-top:3px"><b>Stan wodny uprawy w dniu analizy ({day}):</b> {e(crop_stress_lbl)}</div>
  {outlook_line}
  <p style="margin:6px 0 4px">{e(d['risk_summary'])}</p>
  <p class="meta" style="margin:0"><b>Pewność całej analizy:</b> {conf_explain}{' · <b>główna przyczyna:</b> ' + e(d['main_cause']) if d.get('main_cause') else ''}</p>
</div>
{parcel_map}
<h2>1. Ocena sytuacji wodnej</h2>{items(d['assessment'])}
{graphs}
{scen}
{whatif_html}
<h2>2. Przyczyny</h2><ul>{causes}</ul>
<h2>3. Retencja – zatrzymaj wodę</h2>{items(d['retention'])}
<h2>4. Agrotechnika – ogranicz straty wody</h2>{items(d['agrotechnics'])}
<h2>5. Nawadnianie – dopiero na końcu</h2>{items(d['irrigation'])}
{glossary}
<div style="break-inside:avoid">
<h2>Ograniczenia raportu</h2><ul>{''.join(f'<li>{e(u)}</li>' for u in d['uncertainty'])}</ul>
<h2>Źródła danych</h2><ul>{''.join(f'<li>{e(s)}</li>' for s in d['data_sources'])}</ul>
<p class="meta">Raport wygenerowany automatycznie przez prototyp Wodnik (HackNation 2026) na podstawie danych publicznych.
Zalecenia wymagają sprawdzenia w terenie; nie zastępują porady doradcy rolniczego.</p>
</div>
</body></html>"""


def pdf_report(d: dict) -> bytes:
    """Renderuje dokładnie ten sam raport HTML (z wykresami SVG i mapą) do pliku PDF (bytes)."""
    import os
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    html = html_report(d)
    candidates = [
        os.environ.get("WODNIK_BROWSER"),
        shutil.which("msedge"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    browser = next((b for b in candidates if b and Path(b).exists()), None)
    if not browser:
        raise RuntimeError("Brak przeglądarki Chromium/Edge na serwerze do wygenerowania PDF.")

    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "raport.html"
        pdf_path = Path(tmp) / "raport.pdf"
        profile_dir = Path(tmp) / "profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={profile_dir}",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        if not pdf_path.exists():
            raise RuntimeError("Przeglądarka nie zapisała pliku PDF.")
        return pdf_path.read_bytes()
