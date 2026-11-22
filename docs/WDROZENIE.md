# Wdrożenie (demo online)

Wersja demo stoi w dwóch miejscach: interfejs na **Vercelu**, API na **FastAPI Cloud**.
Front nie zna adresu API — wysyła zapytania pod `/api/...`, a `web/vercel.json` przekierowuje
je na backend. Dzięki temu backend jest jeden i nie trzeba go wpisywać do kodu frontu ani
przebudowywać go przy zmianie adresu API.

| Co | Adres |
|---|---|
| Aplikacja (front) | <https://wodnik.vercel.app> |
| API | <https://wodnik-api.fastapicloud.dev> |
| Dokumentacja API | <https://wodnik-api.fastapicloud.dev/docs> |

Kolejność ma znaczenie: najpierw API, potem front. Adres frontu jest potrzebny, żeby wpuścić go
przez CORS, a adres API, żeby przekierować na niego `/api/...` z frontu.

## Zmienne środowiskowe

Sekrety trzymamy w FastAPI Cloud, nie w repozytorium. `.env` (lokalny) i `pyproject.toml`
z opisem zależności są w `.gitignore` albo nie zawierają wartości.

| Zmienna | Gdzie | Do czego |
|---|---|---|
| `OPENAI_API_KEY` | FastAPI Cloud (sekret) | Asystent AI. Bez niego czat odpowiada skrótem z raportu. |
| `WODNIK_CHAT_MODEL` | FastAPI Cloud | Model asystenta (domyślnie `gpt-5.4-mini`). |
| `WODNIK_CORS_ORIGIN` | FastAPI Cloud | Adres frontu na liście CORS: `https://wodnik.vercel.app`. |
| `WODNIK_DB` | FastAPI Cloud → `/tmp/wodnik.db` | Baza kont. W chmurze katalog z kodem jest tylko do odczytu, więc baza trafia do `/tmp` (ulotna). |
| `WODNIK_CACHE` | FastAPI Cloud → `/tmp/wodnik-cache` | Pamięć podręczna odpowiedzi źródeł danych (j.w.). |

Front nie potrzebuje własnych zmiennych: adres API jest przekierowaniem w `web/vercel.json`.

## Wdrożenie ręczne

```bash
# API
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/fastapi cloud login                 # device flow w przeglądarce
.venv/bin/fastapi deploy                      # wejście api.main:app jest w pyproject.toml

# Front
cd web
vercel link --yes --scope kvbcs-projects --project wodnik
vercel deploy --prod --yes --scope kvbcs-projects
```

`fastapi cloud apps create --name wodnik-api --team-id <id> --link` i `vercel link` uruchamia się
raz. Kolejne wdrożenia robią się same z pusha na `main`.

## Wdrożenia z GitHuba

- `.github/workflows/deploy.yml` — API na FastAPI Cloud. Uruchamia się, gdy push dotknie `api/`,
  `wodnik/`, `demo/`, `pyproject.toml`, `requirements.txt` albo `.python-version`. Potrzebuje
  sekretów `FASTAPI_CLOUD_APP_ID` i `FASTAPI_CLOUD_TOKEN` (ustawione).
- `.github/workflows/deploy-front.yml` — front na Vercelu. Uruchamia się, gdy push dotknie `web/`.
  Potrzebuje `VERCEL_TOKEN`, `VERCEL_ORG_ID` i `VERCEL_PROJECT_ID`. `VERCEL_ORG_ID`
  i `VERCEL_PROJECT_ID` są ustawione; brakuje jeszcze `VERCEL_TOKEN`.

Vercel nie wdraża tu frontu przez własną integrację z GitHubem. Prywatne repozytorium w organizacji
wymaga płatnego planu, a konto jest na Hobby. Dlatego deploy robi workflow z katalogu `web/`
i wskazuje projekt przez `VERCEL_ORG_ID` oraz `VERCEL_PROJECT_ID`.

## Ograniczenia demo

- **PDF raportu** potrzebuje przeglądarki Chromium na serwerze. Obraz FastAPI Cloud jej nie ma,
  więc `GET /analyses/{id}/raport.pdf` zwraca błąd `PDF_ERROR`. Raport do druku działa jako HTML
  (`GET /analyses/{id}/raport`) i to on jest przyciskiem „Drukuj”.
- **Baza kont** w `/tmp` jest ulotna — po restarcie instancji konta i historia raportów znikają.
  Analiza działki działa dalej, bo działki demo są policzone z góry w `demo/`.
- **Rasterio i scipy** ciągną duży obraz, więc pierwszy build w FastAPI Cloud trwa kilka minut.
- Aplikacja w chmurze ma `WODNIK_OFFLINE=0`, więc dla działek spoza demo pobiera dane na bieżąco.
  Gdy zewnętrzne źródło jest niedostępne, raport i tak powstaje, z niższą pewnością.
