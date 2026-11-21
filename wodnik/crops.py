"""Parametry upraw wg FAO-56 (Allen i in.), uproszczone do miesięcy dla warunków Polski.

Kc  – współczynnik uprawowy (ETc = Kc · ET0), wartości miesięczne (sty..gru)
zr  – efektywna głębokość systemu korzeniowego [m]
p   – udział wody łatwo dostępnej (RAW = p · TAW)
Wartości są przybliżeniem tabel FAO-56 z kalendarzem typowym dla Polski;
w dokumentacji opisujemy je jako założenie do weryfikacji z ekspertami.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Crop:
    key: str
    name: str
    kc: tuple  # 12 wartości, styczeń..grudzień
    zr: float
    p: float
    critical_months: tuple  # miesiące największej wrażliwości na niedobór wody
    critical_label: str
    irrigation_usually_profitable: bool


CROPS = {
    c.key: c
    for c in [
        Crop("pszenica_ozima", "pszenica ozima",
             (0.4, 0.4, 0.5, 0.8, 1.1, 1.15, 0.7, 0.3, 0.5, 0.6, 0.5, 0.4), 1.0, 0.55,
             (5, 6), "strzelanie w źdźbło – kłoszenie (maj–czerwiec)", False),
        Crop("jeczmien_jary", "jęczmień jary",
             (0.3, 0.3, 0.3, 0.6, 1.1, 1.15, 0.6, 0.3, 0.3, 0.3, 0.3, 0.3), 0.8, 0.55,
             (5, 6), "krzewienie – kłoszenie (maj–czerwiec)", False),
        Crop("rzepak_ozimy", "rzepak ozimy",
             (0.4, 0.4, 0.6, 1.0, 1.15, 1.0, 0.5, 0.3, 0.6, 0.7, 0.5, 0.4), 1.0, 0.6,
             (4, 5, 6), "kwitnienie – zawiązywanie łuszczyn (kwiecień–czerwiec)", False),
        Crop("kukurydza", "kukurydza",
             (0.3, 0.3, 0.3, 0.3, 0.4, 0.8, 1.15, 1.15, 0.9, 0.5, 0.3, 0.3), 1.0, 0.55,
             (7, 8), "wiechowanie – nalewanie ziarna (lipiec–sierpień)", False),
        Crop("ziemniaki", "ziemniaki",
             (0.3, 0.3, 0.3, 0.3, 0.5, 1.0, 1.1, 0.9, 0.7, 0.3, 0.3, 0.3), 0.5, 0.35,
             (6, 7), "zawiązywanie bulw (czerwiec–lipiec)", True),
        Crop("burak_cukrowy", "burak cukrowy",
             (0.3, 0.3, 0.3, 0.35, 0.6, 1.0, 1.15, 1.15, 1.0, 0.8, 0.3, 0.3), 0.8, 0.55,
             (7, 8), "intensywny przyrost korzeni (lipiec–sierpień)", True),
        Crop("uzytki_zielone", "trwałe użytki zielone",
             (0.4, 0.4, 0.6, 0.9, 1.0, 1.0, 1.0, 1.0, 1.0, 0.9, 0.6, 0.4), 0.4, 0.5,
             (5, 6, 7, 8), "odrastanie po pokosach (maj–sierpień)", False),
    ]
}


def get(key: str) -> Crop:
    try:
        return CROPS[key]
    except KeyError:
        raise ValueError(f"Nieznana uprawa '{key}'. Dostępne: {', '.join(CROPS)}") from None
