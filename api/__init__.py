
"""Serwer HTTP Wodnika. Przy imporcie wczytujemy plik .env z katalogu projektu (np. OPENAI_API_KEY)."""

import os as _os
from pathlib import Path as _Path


def _load_env_file(path: _Path) -> None:
    """Prosty odczyt pliku .env (KLUCZ=wartość) bez dodatkowych bibliotek; zmienne już ustawione mają pierwszeństwo."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                _os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env_file(_Path(__file__).resolve().parent.parent / ".env")
