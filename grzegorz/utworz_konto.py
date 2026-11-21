"""Zakłada konto testowe Grzegorza w lokalnej bazie (data/wodnik.db) i dodaje do historii raport demo z Łaziska.

Uruchomienie z katalogu projektu: .venv/bin/python grzegorz/utworz_konto.py
Działa bez uruchomionego serwera. Ponowne uruchomienie niczego nie psuje.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from api import accounts  # noqa: E402

EMAIL = "grzegorz@wodnik.test"
PASSWORD = "wodnik-grzegorz-2026"  # tylko do testów lokalnych
NAME = "Grzegorz"


def main() -> None:
    accounts.init()
    try:
        user = accounts.register(EMAIL, PASSWORD, NAME)
        print(f"Założono konto {EMAIL}.")
    except accounts.AccountError as exc:
        if exc.code != "EMAIL_TAKEN":
            raise
        _, user = accounts.login(EMAIL, PASSWORD)
        print(f"Konto {EMAIL} już istnieje.")
    demo = next((ROOT / "demo").glob("*.json"), None)
    if demo:
        report = json.loads(demo.read_text(encoding="utf-8"))["report"]
        accounts.save_report(user["id"], "demo-" + demo.stem, report)
        print("W historii jest raport demo:", report["parcel"]["obreb"], report["date"])
    print("Zaloguj się na http://localhost:8000 (dane w grzegorz/README.md).")


if __name__ == "__main__":
    main()
