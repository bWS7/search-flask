from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt
import psycopg2
import psycopg2.extras
import os

# ================= APP =================

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ================= BANCO =================

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://bruno:8caQl5A5aIpd07c6oFUgG4UEUF9ds8G2@dpg-d632lrugpgdc739thkr0-a.oregon-postgres.render.com/sa_r2pm"
)

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ================= USUÁRIO =================

class Usuario(UserMixin):
    def __init__(self, id, nome, email):
        self.id = id
        self.nome = nome
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nome, email FROM usuarios WHERE id = %s",
        (user_id,)
    )
    u = cur.fetchone()
    cur.close()
    conn.close()

    if u:
        return Usuario(u[0], u[1], u[2])
    return None

# ================= ROTAS =================

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, email, senha_hash
            FROM usuarios
            WHERE email = %s AND ativo = TRUE
        """, (email,))
        u = cur.fetchone()
        cur.close()
        conn.close()

        if u and bcrypt.check_password_hash(u[3], senha):
            user = Usuario(u[0], u[1], u[2])
            login_user(user)
            return redirect(url_for("index"))

        return "Login inválido", 401

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

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
    cur.close()
    conn.close()

    return jsonify(dados)

# ================= START =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
