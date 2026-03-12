import http.client
import socket
import sqlite3
import threading
import time
from pathlib import Path

from app import compute_stats, parse_score, run_server


def request(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read()
    out = (response.status, dict(response.getheaders()), data)
    conn.close()
    return out


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_user_isolation_and_match_storage(tmp_path):
    port = get_free_port()
    db_path = Path(tmp_path) / "test.db"
    thread = threading.Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": port, "db_path": db_path}, daemon=True)
    thread.start()
    time.sleep(0.5)

    payload = "username=alice&password=secret"
    status, _, _ = request(port, "POST", "/register", payload, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status == 303

    status, headers, _ = request(port, "POST", "/login", payload, {"Content-Type": "application/x-www-form-urlencoded"})
    assert status == 303
    cookie = headers["Set-Cookie"]

    match_payload = (
        "tournament_name=Store+Championship&round_name=Ronde+1&opponent_deck_name=Ruby+Control"
        "&opponent_colors=Rubis%2FSaphir&score=2-1&toss_winner=Moi&notes=ok"
    )
    status, _, _ = request(
        port,
        "POST",
        "/dashboard",
        match_payload,
        {"Content-Type": "application/x-www-form-urlencoded", "Cookie": cookie},
    )
    assert status == 303

    status, _, body = request(port, "GET", "/dashboard", headers={"Cookie": cookie})
    assert status == 200
    assert b"Store Championship" in body

    payload_bob = "username=bob&password=secret"
    request(port, "POST", "/register", payload_bob, {"Content-Type": "application/x-www-form-urlencoded"})
    _, headers_bob, _ = request(port, "POST", "/login", payload_bob, {"Content-Type": "application/x-www-form-urlencoded"})
    cookie_bob = headers_bob["Set-Cookie"]
    status, _, body = request(port, "GET", "/dashboard", headers={"Cookie": cookie_bob})
    assert status == 200
    assert b"Store Championship" not in body

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    conn.close()
    assert count == 1


def test_homepage_has_clear_login_call_to_action(tmp_path):
    port = get_free_port()
    db_path = Path(tmp_path) / "test.db"
    thread = threading.Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": port, "db_path": db_path}, daemon=True)
    thread.start()
    time.sleep(0.5)

    status, _, body = request(port, "GET", "/")
    assert status == 200
    assert b"href='/login'" in body
    assert b"Se connecter" in body


def test_score_parsing_and_dashboard_stats_computation():
    assert parse_score("2-1") == (2, 1)
    assert parse_score(" 0 - 2 ") == (0, 2)
    assert parse_score("x-y") is None

    rows = [
        ("Tournoi A", "Ronde 1", "Ruby", "Rubis", "2-0", "Moi", "01/01/2026 09:00"),
        ("Tournoi A", "Ronde 2", "Sapphire", "Saphir", "1-2", "Adversaire", "01/01/2026 10:00"),
        ("Tournoi B", "Ronde 1", "Steel", "Acier", "2-1", "Moi", "02/01/2026 11:00"),
    ]
    stats = compute_stats(rows)

    assert stats["total"] == 3
    assert stats["wins"] == 2
    assert stats["losses"] == 1
    assert stats["winrate"] == 66.7
    assert stats["tossrate"] == 66.7
