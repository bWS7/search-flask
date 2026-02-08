from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt
import psycopg
from psycopg import rows
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 🔌 Conexão com banco (Render / Neon)
conn = psycopg.connect(
    "postgresql://bruno:8caQl5A5aIpd07c6oFUgG4UEUF9ds8G2@dpg-d632lrugpgdc739thkr0-a.oregon-postgres.render.com/sa_r2pm"
)

# 👤 Classe do usuário
class Usuario(UserMixin):
    def __init__(self, id, nome, email):
        self.id = id
        self.nome = nome
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, nome, email FROM usuarios WHERE id = %s",
            (user_id,)
        )
        u = cur.fetchone()

    if u:
        return Usuario(u[0], u[1], u[2])
    return None

# 🏠 Página principal
@app.route("/")
@login_required
def index():
    return render_template("index.html")

# 🔐 Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nome, email, senha_hash
                FROM usuarios
                WHERE email = %s AND ativo = TRUE
            """, (email,))
            u = cur.fetchone()

        if u and bcrypt.check_password_hash(u[3], senha):
            user = Usuario(u[0], u[1], u[2])
            login_user(user)
            return redirect(url_for("index"))

        return "Login inválido"

    return render_template("login.html")

# 🚪 Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# 🔍 Busca protegida
@app.route("/buscar")
@login_required
def buscar():
    termo = request.args.get("q", "").strip()

    if not termo:
        return jsonify([])

    with conn.cursor(row_factory=rows.dict_row) as cur:
        cur.execute("""
            SELECT id, colaborador, email, cnpj, cadastro_uau
            FROM colaboradores
            WHERE
                colaborador ILIKE %s
                OR email ILIKE %s
                OR cnpj ILIKE %s
            ORDER BY colaborador
            LIMIT 30
        """, (
            f"%{termo}%",
            f"%{termo}%",
            f"%{termo}%"
        ))

        dados = cur.fetchall()

    return jsonify(dados)

if __name__ == "__main__":
    app.run(debug=True)
