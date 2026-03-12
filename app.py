import html
import secrets
import sqlite3
from datetime import datetime
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lorcana.db"
SESSION_COOKIE = "lorcana_session"

sessions = {}


def init_db(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tournament_name TEXT NOT NULL,
            round_name TEXT NOT NULL,
            opponent_deck_name TEXT NOT NULL,
            opponent_colors TEXT NOT NULL,
            score TEXT NOT NULL,
            toss_winner TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def layout(content: str, username: str | None = None, flash: str = "") -> bytes:
    nav = (
        f"{html.escape(username)} · <a href='/logout'>Déconnexion</a>"
        if username
        else "<a href='/login'>Connexion</a> / <a href='/register'>Inscription</a>"
    )
    flash_html = f"<div class='flash'>{html.escape(flash)}</div>" if flash else ""
    page = f"""<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Lorcana Tracker</title>
<style>
body {{font-family: Arial, sans-serif; margin:0; background:#f4f6fb; color:#1b1f33;}}
header {{background:#1b1f33;color:#fff;padding:1rem 2rem;display:flex;justify-content:space-between;}}
main {{max-width:980px;margin:2rem auto;background:#fff;padding:1.5rem;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08);}}
input,select,textarea{{padding:.6rem;border:1px solid #ccd4e2;border-radius:6px;margin-bottom:.6rem;width:100%;box-sizing:border-box}}
button{{background:#2a6ef5;color:#fff;border:none;padding:.7rem 1rem;border-radius:6px;cursor:pointer}}
table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #e6e9f2;padding:.5rem;text-align:left}}
a{{color:#9ec0ff;text-decoration:none}} .flash{{background:#e4f4ff;padding:.5rem 1rem;border-radius:6px;margin-bottom:1rem}}
.cta-row{{display:flex;gap:.8rem;flex-wrap:wrap;margin-top:1rem}}
.cta{{display:inline-block;background:#2a6ef5;color:#fff !important;padding:.65rem 1rem;border-radius:8px}}
.cta-secondary{{background:#1b1f33}}
</style></head><body><header><strong>Lorcana Tournament Tracker</strong><nav>{nav}</nav></header><main>{flash_html}{content}</main></body></html>"""
    return page.encode("utf-8")


class LorcanaHandler(BaseHTTPRequestHandler):
    db_path = DB_PATH

    def db(self):
        return sqlite3.connect(self.db_path)

    def current_user(self):
        raw = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(raw)
        token = jar.get(SESSION_COOKIE)
        if not token:
            return None
        user_id = sessions.get(token.value)
        if not user_id:
            return None
        conn = self.db()
        row = conn.execute("SELECT id, username FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return row

    def parse_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(body)
        return {k: v[0].strip() for k, v in parsed.items()}

    def redirect(self, location, cookie_header=None):
        self.send_response(303)
        self.send_header("Location", location)
        if cookie_header:
            self.send_header("Set-Cookie", cookie_header)
        self.end_headers()

    def send_html(self, data: bytes, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        user = self.current_user()

        if path == "/":
            if user:
                return self.redirect("/dashboard")
            body = """
            <h1>Bienvenue joueur de Lorcana 👋</h1>
            <p>Enregistre tes parties de tournoi, deck adverse, score et toss.</p>
            <div class='cta-row'>
              <a class='cta' href='/login'>Se connecter</a>
              <a class='cta cta-secondary' href='/register'>Créer un compte</a>
            </div>
            """
            return self.send_html(layout(body))

        if path == "/register":
            body = """
            <h2>Créer un profil joueur</h2>
            <form method='post'>
            <input name='username' placeholder="Nom d'utilisateur" required>
            <input type='password' name='password' placeholder='Mot de passe' required>
            <button type='submit'>Créer mon compte</button></form>
            """
            return self.send_html(layout(body))

        if path == "/login":
            body = """
            <h2>Connexion</h2>
            <form method='post'>
            <input name='username' placeholder="Nom d'utilisateur" required>
            <input type='password' name='password' placeholder='Mot de passe' required>
            <button type='submit'>Se connecter</button></form>
            """
            return self.send_html(layout(body))

        if path == "/logout":
            raw = self.headers.get("Cookie", "")
            jar = cookies.SimpleCookie(raw)
            token = jar.get(SESSION_COOKIE)
            if token:
                sessions.pop(token.value, None)
            return self.redirect("/", f"{SESSION_COOKIE}=; Path=/; Max-Age=0")

        if path == "/dashboard":
            if not user:
                return self.redirect("/login")
            conn = self.db()
            rows = conn.execute(
                "SELECT tournament_name, round_name, opponent_deck_name, opponent_colors, score, toss_winner, created_at FROM matches WHERE user_id=? ORDER BY id DESC",
                (user[0],),
            ).fetchall()
            conn.close()
            table_rows = "".join(
                f"<tr><td>{html.escape(r[0])}</td><td>{html.escape(r[1])}</td><td>{html.escape(r[2])}</td><td>{html.escape(r[3])}</td><td>{html.escape(r[4])}</td><td>{html.escape(r[5])}</td><td>{html.escape(r[6])}</td></tr>"
                for r in rows
            ) or "<tr><td colspan='7'>Aucune partie enregistrée.</td></tr>"
            body = f"""
            <h2>Mes parties de tournoi</h2>
            <form method='post'>
            <input name='tournament_name' placeholder='Nom du tournoi' required>
            <input name='round_name' placeholder='Round (ex: Ronde 1)' required>
            <input name='opponent_deck_name' placeholder='Deck adverse' required>
            <input name='opponent_colors' placeholder='Couleurs (ex: Améthyste / Rubis)' required>
            <input name='score' placeholder='Score (ex: 2-1)' required>
            <select name='toss_winner' required><option value=''>Qui avait le toss ?</option><option>Moi</option><option>Adversaire</option></select>
            <textarea name='notes' placeholder='Notes optionnelles'></textarea>
            <button type='submit'>Enregistrer la partie</button></form>
            <table><thead><tr><th>Tournoi</th><th>Round</th><th>Deck adverse</th><th>Couleurs</th><th>Score</th><th>Toss</th><th>Date</th></tr></thead><tbody>{table_rows}</tbody></table>
            """
            return self.send_html(layout(body, username=user[1]))

        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        user = self.current_user()
        form = self.parse_form()

        if path == "/register":
            username = form.get("username", "")
            password = form.get("password", "")
            if not username or not password:
                return self.send_html(layout("<p>Champs requis.</p>", flash="Champs requis."), 400)
            conn = self.db()
            try:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                return self.send_html(layout("<p>Utilisateur existe déjà.</p>", flash="Utilisateur existe déjà."), 400)
            conn.close()
            return self.redirect("/login")

        if path == "/login":
            username = form.get("username", "")
            password = form.get("password", "")
            conn = self.db()
            row = conn.execute(
                "SELECT id FROM users WHERE username=? AND password=?", (username, password)
            ).fetchone()
            conn.close()
            if not row:
                return self.send_html(layout("<p>Identifiants invalides.</p>", flash="Identifiants invalides."), 401)
            token = secrets.token_hex(16)
            sessions[token] = row[0]
            return self.redirect("/dashboard", f"{SESSION_COOKIE}={token}; Path=/; HttpOnly")

        if path == "/dashboard":
            if not user:
                return self.redirect("/login")
            required = [
                "tournament_name",
                "round_name",
                "opponent_deck_name",
                "opponent_colors",
                "score",
                "toss_winner",
            ]
            if not all(form.get(key) for key in required):
                return self.send_html(layout("<p>Données manquantes.</p>", username=user[1], flash="Tous les champs sauf notes sont obligatoires."), 400)
            conn = self.db()
            conn.execute(
                """
                INSERT INTO matches (user_id, tournament_name, round_name, opponent_deck_name, opponent_colors, score, toss_winner, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user[0],
                    form["tournament_name"],
                    form["round_name"],
                    form["opponent_deck_name"],
                    form["opponent_colors"],
                    form["score"],
                    form["toss_winner"],
                    form.get("notes", ""),
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                ),
            )
            conn.commit()
            conn.close()
            return self.redirect("/dashboard")

        self.send_error(404)


def run_server(host="0.0.0.0", port=5000, db_path=DB_PATH):
    init_db(db_path)
    LorcanaHandler.db_path = db_path
    server = ThreadingHTTPServer((host, port), LorcanaHandler)
    print(f"Server running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
