# Raport AI

Na końcu analizy rolnik dostaje **raport napisany prostym językiem**: co się dzieje na jego działce, co zrobić najpierw i na co uważać. Piszemy go modelem Claude, ale tylko jako „tłumacza” gotowego wyniku. Całą analizę, liczby i rekomendacje nadal liczy kod ([ARCHITEKTURA.md](ARCHITEKTURA.md)).

## Po co raport AI

| Problem | Jak pomaga raport |
|---|---|
| Wynik ma 15–20 pozycji z uzasadnieniami: dla rolnika to dużo | 150–200 słów: co jest, co robić najpierw, dlaczego |
| Język techniczny (percentyl, TAW, akumulacja spływu) | zwykłe zdania w stylu rozmowy z doradcą |
| Trzeba coś dać doradcy lub urzędowi | raport do druku lub PDF, z listą źródeł i ograniczeń |
| Jury ocenia „prostotę obsługi” i „wartość praktyczną” | jedno zdanie na górze, które każdy rozumie |

## Zasady (ważne dla kryterium „wiarygodność rekomendacji”)

1. **AI niczego nie liczy i nie wymyśla.** Dostaje obiekt `Report` jako jedyne źródło prawdy. Nie dodaje własnych porad, dotacji, przepisów ani liczb.
2. **Raport zawsze ma wersję bez AI.** Gdy usługa jest niedostępna, odpowiedź jest odrzucona albo model odmówi, pokazujemy szablon z `output.text()` (pole `source: "template"` w API).
3. **Etykieta „napisane przez AI” jest zawsze widoczna**, razem z datą i modelem.
4. **Niepewność przechodzi do raportu.** Poziom pewności i najważniejsze ograniczenia muszą się w nim znaleźć.
5. **Kolejność KOWR jest zachowana:** nawadnianie jest wspomniane na końcu i nie wyprzedza retencji.
6. **Do modelu nie wysyłamy danych osobowych.** Wysyłamy wynik analizy (ID działki to publiczny numer ewidencyjny, bez właściciela).

## Przepływ

```
 Report (JSON z analizy)
        │
        ▼
 wodnik/ai_report.py
   1. buduje prompt: instrukcja + Report jako dane
   2. wywołuje Claude, odpowiedź w ustalonym schemacie JSON
   3. KONTROLA: czy każda liczba z tekstu jest w Report?
   4. składa markdown
        │            │
     ok │            │ błąd / odmowa / brak usługi
        ▼            ▼
   source: "ai"   source: "template"  (output.text)
```

## Format odpowiedzi modelu

Model zwraca JSON o stałej strukturze (wymuszony schematem), z którego kod składa markdown. Dzięki temu układ raportu jest przewidywalny, a każdą sekcję da się osobno sprawdzić.

```json
{
  "podsumowanie": "2–3 zdania: jakie jest ryzyko, jaka główna przyczyna.",
  "co_zrobic_najpierw": [
    { "krok": "Zatrzymaj wodę w miejscu odpływu", "dlaczego": "Z działki odpływa woda z ok. 1,5 ha zlewni." }
  ],
  "dlaczego_tak": "Krótko o danych, z których wynika wniosek.",
  "na_co_uwazac": ["Pewność analizy jest średnia: gleba z modelu, nie z badania."],
  "nawadnianie": "Zdanie o nawadnianiu (zawsze na końcu).",
  "uzyte_liczby": ["69 mm", "58 mm", "1,5 ha"]
}
```

Pole `uzyte_liczby` jest potrzebne do kontroli (niżej).

## Prompt (szkic)

**System** (stały, więc nadaje się do cache'owania):

```
Jesteś doradcą rolniczym piszącym krótki raport dla rolnika w Polsce.
Dostajesz wynik analizy wodnej działki w formacie JSON. To jedyne źródło faktów.

Zasady:
- Używaj wyłącznie informacji i liczb z JSON. Liczby przepisuj dokładnie.
- Nie dodawaj porad, dotacji, przepisów ani przyczyn, których nie ma w JSON.
- Pisz prostym językiem, krótkimi zdaniami, bez żargonu. Zamiast "percentyl" pisz "tak sucho było w X% lat".
- Zachowaj kolejność: ryzyko → przyczyna → retencja → agrotechnika → nawadnianie na końcu.
- Zawsze wspomnij o poziomie pewności i najważniejszym ograniczeniu.
- Nie obiecuj efektów i nie podawaj kosztów. Jeśli czegoś nie wiesz, napisz, że to wymaga sprawdzenia w terenie.
- Styl "rolnik": ok. 200 słów. Styl "doradca": ok. 500 słów, z odwołaniem do źródeł danych.
```

**Użytkownik** (zmienny): obiekt `Report` jako JSON, bez pól niepotrzebnych (`geometria_wgs84`, `raw.gleba`, dane geometryczne), żeby ograniczyć koszt i ryzyko pomyłek.

## Kontrola liczb (zabezpieczenie przed zmyślaniem)

Po odpowiedzi kod sprawdza, że **każda liczba w tekście występuje w `Report`**:

1. Zbierz wszystkie liczby z tekstu raportu (regex z obsługą przecinka dziesiętnego i minusa).
2. Zbierz dozwolone liczby z `Report` (wartości w `detail`, `because`, `raw`, `parcel`), w zapisie z przecinkiem i z kropką.
3. Liczba spoza zbioru (poza prostymi: numery kroków 1–5, „2–3 dawki”) → raport odrzucony, zwracamy szablon i logujemy przypadek.
4. Dodatkowo sprawdzamy, że `uzyte_liczby` zgadza się z liczbami w tekście.

Ograniczenie: kontrola wykrywa **zmyślone liczby**, ale nie wykryje złego wniosku opartego na prawdziwych liczbach. Dlatego sekcja „Co zrobić” bierze tytuły kroków z `Report`, a model dopisuje tylko wyjaśnienie, i dlatego raport przechodzi przegląd ręczny (niżej).

## Szkic kodu `wodnik/ai_report.py`

Szkic do weryfikacji przy implementacji z aktualną dokumentacją SDK (`pip install anthropic`). Klucz czytany z `ANTHROPIC_API_KEY`.

```python
import json, os
import anthropic

MODEL = os.environ.get("WODNIK_AI_MODEL", "claude-opus-5-5")
client = anthropic.Anthropic()  # ANTHROPIC_API_KEY ze środowiska

SCHEMA = {  # pola jak w sekcji „Format odpowiedzi modelu”
    "type": "object", "additionalProperties": False,
    "required": ["podsumowanie", "co_zrobic_najpierw", "dlaczego_tak",
                 "na_co_uwazac", "nawadnianie", "uzyte_liczby"],
    "properties": {
        "podsumowanie": {"type": "string"},
        "co_zrobic_najpierw": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["krok", "dlaczego"],
            "properties": {"krok": {"type": "string"}, "dlaczego": {"type": "string"}}}},
        "dlaczego_tak": {"type": "string"},
        "na_co_uwazac": {"type": "array", "items": {"type": "string"}},
        "nawadnianie": {"type": "string"},
        "uzyte_liczby": {"type": "array", "items": {"type": "string"}},
    },
}

def generate(report: dict, style: str = "rolnik") -> dict | None:
    """Zwraca sparsowany raport albo None (wtedy wołający używa szablonu)."""
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=8000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",                       # automatyczny zapasowy model przy odmowie
            output_config={"effort": "low",            # prosty tekst, bez głębokiego myślenia
                           "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM_PROMPT + f"\nStyl: {style}.",
            messages=[{"role": "user", "content": json.dumps(slim(report), ensure_ascii=False)}],
        )
    except anthropic.APIError:
        return None
    if resp.stop_reason == "refusal":
        return None
    text = next(b.text for b in resp.content if b.type == "text")
    out = json.loads(text)
    return out if numbers_verified(out, report) else None
```

Uwagi do modelu Claude:
- **Model jest konfigurowalny** (`WODNIK_AI_MODEL`). Domyślnie najnowszy Opus; do tańszego raportu można przełączyć na lżejszy model bez zmian w kodzie.
- **Nie ustawiamy `temperature`** (nowsze modele jej nie przyjmują). Powtarzalność zapewnia schemat odpowiedzi i kontrola liczb.
- **`fallbacks`**: przy odmowie klasyfikatora bezpieczeństwa API samo ponawia zapytanie na zapasowym modelu. Gdyby i to się nie udało, wracamy do szablonu.
- Na platformach bez tej funkcji (np. Bedrock) trzeba użyć klienckiego middleware z SDK.

## Koszt i wydajność

- Raport jest krótki (kilkaset tokenów wyjścia) i generowany **na żądanie**, nie przy każdej analizie.
- Wynik cache'ujemy po `analysis_id + style + length`, więc ponowne wejście na ekran nic nie kosztuje.
- System prompt jest stały, więc kwalifikuje się do cache'owania po stronie API przy większym ruchu.
- Limit w serwerze: np. 5 raportów na minutę na IP (patrz [API.md](API.md)).

## Test i jakość

Przed demo przeglądamy raporty z 3 działek z `demo/` ręcznie według listy:

| Kryterium | Pytanie |
|---|---|
| Zgodność liczb | czy wszystkie liczby są z analizy (kontrola automatyczna + oko) |
| Brak dodatków | czy nie ma porad ani faktów spoza `Report` |
| Kolejność KOWR | czy nawadnianie jest na końcu |
| Niepewność | czy raport mówi o pewności i ograniczeniach |
| Zrozumiałość | czy rolnik bez przygotowania zrozumie bez objaśnień |

Automatycznie w testach: kontrola liczb na przykładach poprawnych i celowo zepsutych (podmieniona liczba → raport odrzucony) oraz zachowanie przy błędzie API (musi wrócić szablon, nie wyjątek).

## Zgodność z regulaminem

- Regulamin dopuszcza narzędzia AI **pod warunkiem wskazania ich w dokumentacji z warunkami licencji**. Raport AI jest opisany tutaj i w README (komponent: Anthropic API, warunki komercyjne Anthropic).
- Moduł jest **opcjonalny i wymienialny**: bez klucza API Wodnik działa w pełni, a raport jest szablonowy. Dzięki temu KOWR może przejąć rozwiązanie i podłączyć własnego dostawcę lub własny klucz.
- Klucz API nie trafia do repozytorium ani do przekazywanego kodu (zmienna środowiskowa).

## Rozwój (po hackathonie)

- Wersja „doradca” z odnośnikami do źródeł i wskazaniem, które dane warto uzupełnić.
- Raport porównawczy: ta sama działka w kilku latach (np. susza 2018 i 2023).
- Dopasowanie do dotacji (KOWR, ARiMR, ekoschematy) po zbudowaniu zweryfikowanej bazy programów. Do tego czasu AI **nie podaje** nazw dotacji, bo nie ma ich w `Report`.
