import os

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt

import psycopg
from psycopg.rows import dict_row


# =========================
# APP CONFIG
# =========================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# =========================
# DATABASE
# =========================
# ✅ No Render, o ideal é setar DATABASE_URL em Environment Variables
# Ex: postgresql://user:pass@host:port/dbname
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://bruno:8caQl5A5aIpd07c6oFUgG4UEUF9ds8G2@dpg-d632lrugpgdc739thkr0-a.oregon-postgres.render.com/sa_r2pm"
)

def get_conn():
    """
    Abre uma conexão nova por request/uso.
    Em apps pequenos isso é ok. Se crescer, a gente põe pool.
    """
    return psycopg.connect(DATABASE_URL)


# =========================
# AUTH MODEL
# =========================
class Usuario(UserMixin):
    def __init__(self, id, nome, email):
        self.id = str(id)
        self.nome = nome
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nome, email FROM usuarios WHERE id = %s", (user_id,))
            u = cur.fetchone()

    if u:
        return Usuario(u[0], u[1], u[2])
    return None


# =========================
# ROUTES
# =========================

# ✅ Healthcheck pro Render (opcional, mas ajuda muito)
@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        if not email or not senha:
            return render_template("login.html", error="Informe email e senha")

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, nome, email, senha_hash
                    FROM usuarios
                    WHERE email = %s AND ativo = TRUE
                """, (email,))
                u = cur.fetchone()

        if u and bcrypt.check_password_hash(u[3], senha):
            login_user(Usuario(u[0], u[1], u[2]))
            return redirect(url_for("index"))

        return render_template("login.html", error="Login inválido")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/buscar")
@login_required
def buscar():
    termo = request.args.get("q", "").strip()
    if not termo:
        return jsonify([])

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT id, colaborador, email, cnpj, cadastro_uau
                FROM colaboradores
                WHERE
                    colaborador ILIKE %s
                    OR email ILIKE %s
                    OR cnpj ILIKE %s
                ORDER BY colaborador
                LIMIT 30
            """, (f"%{termo}%", f"%{termo}%", f"%{termo}%"))
            dados = cur.fetchall()

    # dict_row já retorna dict-like -> jsonify aceita direto
    return jsonify(dados)


# =========================
# LOCAL RUN
# =========================
if __name__ == "__main__":
    # Render usa gunicorn (não cai aqui), mas local cai.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
