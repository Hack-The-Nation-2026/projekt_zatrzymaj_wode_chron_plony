# Walidacja: znane lata suszy

Analiza na 15 czerwca (pszenica ozima, okres krytyczny) dla 8 działek z 8 województw w latach 2015–2023.
Lata suszy wg IUNG-PIB i doniesień o suszy rolniczej: 2015, 2018, 2019, 2022. Pozostałe lata to nie „lata mokre”:
lokalnie też mogła w nich występować susza, więc porównanie jest ostrożne.

Poziom ryzyka po kalibracji (21.11.2026): co najmniej umiarkowane wymaga odchylenia od normy z ostatnich 10 lat
(bilans, wilgotność gleby, stan roślin) albo wyczerpania ponad 80% wody w strefie korzeni. Zasada wynika z metody,
progi nie były dopasowywane do tych wyników; ale sprawdzamy ją na tych samych danych, które pokazały problem,
więc wynik po kalibracji jest optymistyczny.

| | Lata suszy | Pozostałe lata |
|---|---|---|
| liczba analiz | 32 | 40 |
| ryzyko umiarkowane lub wysokie (po kalibracji) | **88%** | 78% |
| ryzyko wysokie (po kalibracji) | **66%** | 55% |
| ryzyko umiarkowane lub wysokie (przed kalibracją) | 97% | 92% |
| ryzyko wysokie (przed kalibracją) | 66% | 55% |
| średnie punkty ryzyka (0–9) | 5,3 | 4,6 |
| średnio dni stresu w ostatnich 30 dniach | 19 | 14 |
| średni bilans opad − parowanie z 60 dni | −106 mm | −82 mm |

W 7 z 8 działek lata suszy mają średnio więcej punktów ryzyka niż pozostałe lata.

Po kalibracji:

| Rok | Susza wg IUNG | ryzyko umiarkowane lub wysokie | ryzyko wysokie | średnie punkty |
|---|---|---|---|---|
| 2015 | tak | 75% | 50% | 4,5 |
| 2016 | – | 50% | 25% | 4,4 |
| 2017 | – | 100% | 75% | 5,0 |
| 2018 | tak | 100% | 100% | 7,5 |
| 2019 | tak | 100% | 62% | 5,0 |
| 2020 | – | 62% | 25% | 3,4 |
| 2021 | – | 88% | 75% | 4,5 |
| 2022 | tak | 75% | 50% | 4,2 |
| 2023 | – | 88% | 75% | 5,8 |

Analiz z błędem (pominięte): 0. Dane: `walidacja/wyniki.csv`, skrypt: `walidacja/lata_suszy.py`.

Ograniczenia: mała próba (8 działek), jedna data w roku, etykiety lat suszy są krajowe, a susza bywa
lokalna. To sprawdzenie spójności, nie pełna walidacja; docelowo porównanie z gminnymi danymi SMSR IUNG.
