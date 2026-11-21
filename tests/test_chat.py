"""Testy asystenta bez modelu językowego (bez sieci i bez klucza OpenAI).

Uruchomienie: .venv/bin/python tests/test_chat.py
"""

import json
import os
import sys
from pathlib import Path

os.environ.pop("OPENAI_API_KEY", None)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["OPENAI_API_KEY"] = ""  # pusty klucz z .env nie może włączyć modelu
from api import chat  # noqa: E402

os.environ.pop("OPENAI_API_KEY", None)
REPORT = json.loads(next((ROOT / "demo").glob("*.json")).read_text(encoding="utf-8"))["report"]


def test_context_is_compact_and_has_key_facts():
    ctx = chat.report_context(REPORT)
    data = json.loads(ctx)
    assert data["ryzyko_suszy"] == REPORT["risk_level"]
    assert data["dzialka"]["id"] == REPORT["parcel"]["id"]
    assert "geometria" not in ctx and "dates" not in ctx  # bez geometrii i serii dziennych
    assert len(ctx) < 20000


def test_fallback_without_key():
    text, source = chat.reply([{"role": "user", "content": "Co zrobić najpierw?"}], REPORT)
    assert source == "fallback"
    assert REPORT["risk_level"] in text and "Najpierw warto" in text
    text, source = chat.reply([{"role": "user", "content": "Cześć"}], None)
    assert source == "fallback" and "analizę" in text


def test_message_validation():
    for bad in ([], [{"role": "assistant", "content": "x"}], [{"role": "user", "content": "   "}]):
        try:
            chat.reply(bad, REPORT)
        except ValueError:
            continue
        raise AssertionError(f"oczekiwano ValueError dla {bad}")
    long = [{"role": "user", "content": "a" * 10000}]
    assert chat._clean_messages(long)[0][1] == "a" * chat.MAX_CHARS


if __name__ == "__main__":
    test_context_is_compact_and_has_key_facts()
    test_fallback_without_key()
    test_message_validation()
    print("OK")
