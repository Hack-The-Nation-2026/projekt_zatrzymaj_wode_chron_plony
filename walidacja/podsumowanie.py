"""Podsumowanie walidacji z walidacja/wyniki.csv → walidacja/WYNIKI.md (tabela do README i prezentacji).

Uruchomienie: .venv/bin/python walidacja/podsumowanie.py
"""

import csv
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
LEVEL = {"niskie": 0, "umiarkowane": 1, "wysokie": 2}


def pct(x):
    return f"{round(100 * x)}%"


def main():
    rows = [r for r in csv.DictReader((ROOT / "wyniki.csv").open(encoding="utf-8")) if not r["blad"]]
    errors = sum(1 for r in csv.DictReader((ROOT / "wyniki.csv").open(encoding="utf-8")) if r["blad"])
    dry = [r for r in rows if r["rok_suszy"] == "1"]
    other = [r for r in rows if r["rok_suszy"] == "0"]

    def old_level(r):  # zasada sprzed kalibracji: same punkty (≥5 wysokie, ≥3 umiarkowane)
        pts = float(r["punkty"])
        return "wysokie" if pts >= 5 else "umiarkowane" if pts >= 3 else "niskie"

    def stats(rs, level=lambda r: r["ryzyko"]):
        flagged = [r for r in rs if level(r) in ("umiarkowane", "wysokie")]
        high = [r for r in rs if level(r) == "wysokie"]
        return {"n": len(rs), "flagged": len(flagged) / len(rs) if rs else 0, "high": len(high) / len(rs) if rs else 0,
                "points": mean(float(r["punkty"]) for r in rs) if rs else 0,
                "stress": mean(float(r["dni_stresu_30"]) for r in rs) if rs else 0,
                "kbw": mean(float(r["bilans60_mm"]) for r in rs) if rs else 0}

    sd, so = stats(dry), stats(other)
    od, oo = stats(dry, old_level), stats(other, old_level)

    # Czy w każdej działce lata suszy mają średnio więcej punktów ryzyka niż pozostałe?
    per_parcel = []
    for reg in sorted({r["region"] for r in rows}):
        d = [float(r["punkty"]) for r in dry if r["region"] == reg]
        o = [float(r["punkty"]) for r in other if r["region"] == reg]
        if d and o:
            per_parcel.append((reg, mean(d), mean(o)))
    better = sum(1 for _, d, o in per_parcel if d > o)

    by_year = []
    for y in sorted({r["rok"] for r in rows}):
        rs = [r for r in rows if r["rok"] == y]
        by_year.append((y, rs[0]["rok_suszy"] == "1", stats(rs)))

    lines = [
        "# Walidacja: znane lata suszy",
        "",
        "Analiza na 15 czerwca (pszenica ozima, okres krytyczny) dla 8 działek z 8 województw w latach 2015–2023.",
        "Lata suszy wg IUNG-PIB i doniesień o suszy rolniczej: 2015, 2018, 2019, 2022. Pozostałe lata to nie „lata mokre”:",
        "lokalnie też mogła w nich występować susza, więc porównanie jest ostrożne.",
        "",
        "Poziom ryzyka po kalibracji (21.11.2026): co najmniej umiarkowane wymaga odchylenia od normy z ostatnich 10 lat",
        "(bilans, wilgotność gleby, stan roślin) albo wyczerpania ponad 80% wody w strefie korzeni. Zasada wynika z metody,",
        "progi nie były dopasowywane do tych wyników; ale sprawdzamy ją na tych samych danych, które pokazały problem,",
        "więc wynik po kalibracji jest optymistyczny.",
        "",
        "| | Lata suszy | Pozostałe lata |",
        "|---|---|---|",
        f"| liczba analiz | {sd['n']} | {so['n']} |",
        f"| ryzyko umiarkowane lub wysokie (po kalibracji) | **{pct(sd['flagged'])}** | {pct(so['flagged'])} |",
        f"| ryzyko wysokie (po kalibracji) | **{pct(sd['high'])}** | {pct(so['high'])} |",
        f"| ryzyko umiarkowane lub wysokie (przed kalibracją) | {pct(od['flagged'])} | {pct(oo['flagged'])} |",
        f"| ryzyko wysokie (przed kalibracją) | {pct(od['high'])} | {pct(oo['high'])} |",
        f"| średnie punkty ryzyka (0–9) | {sd['points']:.1f} | {so['points']:.1f} |".replace(".", ","),
        f"| średnio dni stresu w ostatnich 30 dniach | {sd['stress']:.0f} | {so['stress']:.0f} |",
        f"| średni bilans opad − parowanie z 60 dni | {sd['kbw']:.0f} mm | {so['kbw']:.0f} mm |".replace("-", "−"),
        "",
        f"W {better} z {len(per_parcel)} działek lata suszy mają średnio więcej punktów ryzyka niż pozostałe lata.",
        "",
        "Po kalibracji:",
        "",
        "| Rok | Susza wg IUNG | ryzyko umiarkowane lub wysokie | ryzyko wysokie | średnie punkty |",
        "|---|---|---|---|---|",
    ]
    for y, is_dry, s in by_year:
        lines.append(f"| {y} | {'tak' if is_dry else '–'} | {pct(s['flagged'])} | {pct(s['high'])} | "
                     f"{s['points']:.1f} |".replace(".", ","))
    lines += ["", f"Analiz z błędem (pominięte): {errors}. Dane: `walidacja/wyniki.csv`, skrypt: `walidacja/lata_suszy.py`.",
              "", "Ograniczenia: mała próba (8 działek), jedna data w roku, etykiety lat suszy są krajowe, a susza bywa",
              "lokalna. To sprawdzenie spójności, nie pełna walidacja; docelowo porównanie z gminnymi danymi SMSR IUNG."]
    (ROOT / "WYNIKI.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
