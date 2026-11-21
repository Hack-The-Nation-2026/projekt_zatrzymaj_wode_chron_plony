"""Testy kont i historii raportów na tymczasowej bazie (bez sieci).

Uruchomienie: .venv/bin/python -m pytest -q   (albo: .venv/bin/python tests/test_accounts.py)
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ["WODNIK_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api import accounts  # noqa: E402

accounts.init()

REPORT = {"parcel": {"id": "101609_2.0011.352", "obreb": "Łazisko", "gmina": "Tomaszów Mazowiecki"},
          "date": "2026-06-15", "crop": "pszenica ozima", "risk_level": "wysokie"}


def _raises(code, fn, *args):
    try:
        fn(*args)
    except accounts.AccountError as exc:
        assert exc.code == code, exc.code
    else:
        raise AssertionError(f"oczekiwano błędu {code}")


def test_register_login_logout():
    u = accounts.register("Anna@Example.com", "dobrehaslo", "Anna")
    assert u["email"] == "anna@example.com" and u["name"] == "Anna"
    _raises("EMAIL_TAKEN", accounts.register, "anna@example.com", "innehaslo1")
    _raises("INVALID_INPUT", accounts.register, "nie-email", "dobrehaslo")
    _raises("INVALID_INPUT", accounts.register, "b@example.com", "krotkie")
    _raises("BAD_CREDENTIALS", accounts.login, "anna@example.com", "zlehaslo1")
    _raises("BAD_CREDENTIALS", accounts.login, "nikt@example.com", "dobrehaslo")
    token, user = accounts.login("ANNA@example.com", "dobrehaslo")
    assert accounts.user_for_token(token)["id"] == user["id"]
    accounts.logout(token)
    assert accounts.user_for_token(token) is None
    assert accounts.user_for_token("zmyslony-token") is None


def test_history_is_private_and_deduplicated():
    a = accounts.register("ola@example.com", "dobrehaslo")["id"]
    b = accounts.register("piotr@example.com", "dobrehaslo")["id"]
    rid = accounts.save_report(a, "job1", REPORT)
    assert accounts.save_report(a, "job1", REPORT) == rid  # ta sama analiza tylko raz
    accounts.save_report(a, "job2", {**REPORT, "date": "2026-07-01"})
    hist = accounts.list_reports(a)
    assert [h["analysis_id"] for h in hist] == ["job2", "job1"]  # najnowsze pierwsze
    assert hist[1]["place"] == "Łazisko, gm. Tomaszów Mazowiecki"
    assert accounts.get_report(a, rid)["report"]["risk_level"] == "wysokie"
    assert accounts.get_report(b, rid) is None and accounts.list_reports(b) == []
    assert not accounts.delete_report(b, rid)
    assert accounts.delete_report(a, rid)
    assert len(accounts.list_reports(a)) == 1


if __name__ == "__main__":
    test_register_login_logout()
    test_history_is_private_and_deduplicated()
    print("OK")
