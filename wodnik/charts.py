"""Wykresy SVG do raportu do druku (bez bibliotek; działają w przeglądarce, wydruku i PDF).

Wejście: pole `charts` z Report.to_dict() (analysis._charts) i opcjonalnie `scenarios`.
Kolory jasne, czytelne także w druku czarno-białym (linie różnią się kształtem, nie tylko kolorem).
"""

from __future__ import annotations

from datetime import date
from html import escape

W, H = 720, 230
L, R, T, B = 46, 14, 28, 30
INK, MUTED, GRID = "#1b2e30", "#5b6b6d", "#e3e8e4"
WATER, STRESS, RAIN, ET, BAD, OK = "#1d5f9a", "#c0392b", "#2f7fc1", "#e08a1e", "#c0392b", "#4a9d3f"


def _svg(body: str, label: str, h: int = H) -> str:
    return (f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{escape(label)}" '
            f'style="font:11px system-ui,Arial,sans-serif;max-width:{W}px">{body}</svg>')


def _txt(x, y, s, anchor="start", color=MUTED, extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" text-anchor="{anchor}" {extra}>{escape(str(s))}</text>'


def _month_ticks(dates: list, x) -> str:
    """Podpisy osi czasu na pierwszym dniu każdego miesiąca."""
    out = []
    for i, d in enumerate(dates):
        if d.day == 1:
            out.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{T}" y2="{H - B}" stroke="{GRID}"/>')
            out.append(_txt(x(i), H - B + 16, d.strftime("%d.%m"), "middle"))
    return "".join(out)


def water(c: dict, scenarios: dict | None = None) -> str:
    """Zapas wody dostępnej dla roślin: ostatnie miesiące (linia) i 30 dni scenariuszy (pasmo)."""
    dd = c["daily"]
    dates = [date.fromisoformat(s) for s in dd["dates"]]
    left = dd["water_left_mm"]
    taw, stress = dd["taw_mm"] or 1, dd["stress_below_mm"]
    env = (scenarios or {}).get("envelope") or []
    n = len(dates) + len(env)
    x = lambda i: L + i / max(1, n - 1) * (W - L - R)
    y = lambda v: T + (1 - max(0.0, min(taw, v)) / taw) * (H - T - B)

    parts = [f'<rect x="{L}" y="{y(stress):.1f}" width="{W - L - R}" height="{H - B - y(stress):.1f}" fill="#fbe9e7"/>']
    for t in (0, round(taw / 2), round(taw)):
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}"/>')
        parts.append(_txt(L - 6, y(t) + 4, t, "end"))
    parts.append(_month_ticks(dates, x))
    parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(stress):.1f}" y2="{y(stress):.1f}" stroke="{STRESS}" '
                 f'stroke-dasharray="5 4"/>')
    parts.append(_txt(L + 4, y(stress) + 13, "poniżej: roślina w stresie wodnym", color=STRESS))
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(left) if v is not None)
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{WATER}" stroke-width="2.2"/>')

    i_now = len(dates) - 1
    parts.append(f'<line x1="{x(i_now):.1f}" x2="{x(i_now):.1f}" y1="{T}" y2="{H - B}" stroke="{INK}"/>')
    parts.append(_txt(x(i_now) - 4, T + 12, "dziś", "end", INK, 'font-weight="700"'))
    if env:
        k = lambda j: i_now + j  # dzień j scenariusza
        band = (" ".join(f"{x(k(e['day'])):.1f},{y(taw - e['p10']):.1f}" for e in env) + " " +
                " ".join(f"{x(k(e['day'])):.1f},{y(taw - e['p90']):.1f}" for e in reversed(env)))
        med = " ".join(f"{x(k(e['day'])):.1f},{y(taw - e['p50']):.1f}" for e in env)
        parts.append(f'<polygon points="{band}" fill="{WATER}" opacity="0.18"/>')
        parts.append(f'<polyline points="{x(i_now):.1f},{y(left[-1] or 0):.1f} {med}" fill="none" stroke="{WATER}" '
                     f'stroke-width="2" stroke-dasharray="6 3"/>')
        parts.append(_txt(W - R, 12, "30 dni: scenariusze", "end"))
    parts.append(_txt(L - 6, 12, "mm", "end"))
    return _svg("".join(parts), "Zapas wody w glebie dostępnej dla roślin w ostatnich miesiącach i scenariusze na 30 dni")


def rain_et(c: dict) -> str:
    """Opad dzienny (słupki) i parowanie referencyjne ET0 (linia) w tym samym okresie."""
    dd = c["daily"]
    dates = [date.fromisoformat(s) for s in dd["dates"]]
    p = [v or 0 for v in dd["precip_mm"]]
    e = [v or 0 for v in dd["et0_mm"]]
    top = max(10.0, max(p + e) * 1.1)
    n = len(dates)
    x = lambda i: L + (i + 0.5) / n * (W - L - R)
    y = lambda v: T + (1 - min(top, v) / top) * (H - T - B)
    bw = max(1.0, (W - L - R) / n * 0.75)
    parts = []
    for t in (0, round(top / 2), round(top)):
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}"/>')
        parts.append(_txt(L - 6, y(t) + 4, t, "end"))
    parts.append(_month_ticks(dates, x))
    parts += [f'<rect x="{x(i) - bw / 2:.1f}" y="{y(v):.1f}" width="{bw:.1f}" height="{y(0) - y(v):.1f}" fill="{RAIN}"/>'
              for i, v in enumerate(p) if v > 0]
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(e))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{ET}" stroke-width="2"/>')
    sp, se = sum(p), sum(e)
    parts.append(_txt(W - R, 12, f"opad {sp:.0f} mm · parowanie {se:.0f} mm · bilans {sp - se:+.0f} mm".replace(".", ","),
                      "end", INK))
    parts.append(f'<rect x="{L + 4}" y="3" width="10" height="10" fill="{RAIN}"/>' + _txt(L + 18, 12, "opad"))
    parts.append(f'<line x1="{L + 60}" x2="{L + 74}" y1="8" y2="8" stroke="{ET}" stroke-width="2"/>'
                 + _txt(L + 78, 12, "parowanie (ET0)"))
    parts.append(_txt(L - 6, 12, "mm/d", "end"))
    return _svg("".join(parts), "Opad dzienny i parowanie w ostatnich miesiącach")


def years(c: dict) -> str:
    """Bilans opad − parowanie z 60 dni w kolejnych latach; rok analizy wyróżniony."""
    yy = c["years"]
    items = [i for i in yy["items"] if i["kbw60_mm"] is not None]
    if not items:
        return ""
    h = 200
    vals = [i["kbw60_mm"] for i in items] + [yy["deficit_threshold_mm"], 0]
    lo, hi = min(vals) * 1.1, max(max(vals) * 1.1, 10)
    n = len(items)
    x = lambda i: L + (i + 0.5) / n * (W - L - R)
    y = lambda v: T + (hi - v) / (hi - lo) * (h - T - B)
    bw = (W - L - R) / n * 0.62
    parts = [f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{INK}"/>',
             _txt(L - 6, y(0) + 4, 0, "end")]
    thr = yy["deficit_threshold_mm"]
    parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(thr):.1f}" y2="{y(thr):.1f}" stroke="{BAD}" stroke-dasharray="5 4"/>')
    parts.append(_txt(L - 6, y(thr) + 4, f"{thr:.0f}", "end", BAD))
    for i, it in enumerate(items):
        v = it["kbw60_mm"]
        color = INK if it["current"] else (BAD if v <= thr else "#9bb7a0")
        y0, y1 = sorted((y(0), y(v)))
        parts.append(f'<rect x="{x(i) - bw / 2:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{max(1, y1 - y0):.1f}" fill="{color}"/>')
        label = f"{it['year']}" + (" (ten rok)" if it["current"] else "")
        parts.append(_txt(x(i), h - B + 14, label, "middle", INK if it["current"] else MUTED,
                          'font-weight="700"' if it["current"] else ""))
        parts.append(_txt(x(i), (y1 + 12) if v < 0 else (y0 - 4), f"{v:.0f}", "middle"))
    parts.append(_txt(L - 6, 12, "mm", "end"))
    return _svg("".join(parts), "Bilans wody z 60 dni w tym roku na tle poprzednich lat", h)
