import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

# ---------- Config ----------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///catalog.db")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")  # mude em produção!
db = SQLAlchemy(app)

# ---------- Models ----------
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price_cents = db.Column(db.Integer, nullable=False)  # armazene em centavos
    category = db.Column(db.String(80), nullable=False)
    photo_url = db.Column(db.String(300))
    active = db.Column(db.Boolean, default=True)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(120), default="Seu Negócio")
    whatsapp_number = db.Column(db.String(20), default="55SEUNUMERO")  # 55DDDNUMERO
    address = db.Column(db.String(200), default="")
    logo_url = db.Column(db.String(300), default="")

def get_settings():
    s = Settings.query.first()
    if not s:
        s = Settings()
        db.session.add(s)
        db.session.commit()
    return s

# ---------- Utils ----------
def logged_in():
    return session.get("admin") is True

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

# ---------- Routes (Public) ----------
@app.route("/")
def index():
    products = Product.query.filter_by(active=True).all()
    cats = {}
    for p in products:
        cats.setdefault(p.category, []).append(p)
    s = get_settings()
    return render_template("index.html", cats=cats, s=s)

# ---------- Routes (Admin Auth) ----------
@app.get("/admin/login")
def login():
    return render_template("login.html")

@app.post("/admin/login")
def do_login():
    pwd = request.form.get("password","")
    if pwd == ADMIN_PASSWORD:
        session["admin"] = True
        flash("Login efetuado.", "success")
        return redirect(url_for("admin"))
    flash("Senha incorreta.", "danger")
    return redirect(url_for("login"))

@app.get("/admin/logout")
def logout():
    session.clear()
    flash("Logout efetuado.", "info")
    return redirect(url_for("login"))

# ---------- Routes (Admin CRUD) ----------
@app.get("/admin")
@login_required
def admin():
    s = get_settings()
    return render_template("admin.html", products=Product.query.order_by(Product.category, Product.name).all(), s=s)

@app.post("/admin/product")
@login_required
def create_product():
    name = request.form["name"].strip()
    price = int(round(float(request.form["price"].replace(",", ".")) * 100))
    category = request.form["category"].strip()
    photo_url = request.form.get("photo_url", "").strip()
    db.session.add(Product(name=name, price_cents=price, category=category, photo_url=photo_url, active=True))
    db.session.commit()
    flash("Produto criado.", "success")
    return redirect(url_for("admin"))

@app.post("/admin/product/<int:pid>/toggle")
@login_required
def toggle_product(pid):
    p = Product.query.get_or_404(pid)
    p.active = not p.active
    db.session.commit()
    flash("Produto atualizado.", "success")
    return redirect(url_for("admin"))

@app.post("/admin/product/<int:pid>/delete")
@login_required
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash("Produto removido.", "warning")
    return redirect(url_for("admin"))

@app.post("/admin/settings")
@login_required
def update_settings():
    s = get_settings()
    s.business_name = request.form.get("business_name","").strip() or s.business_name
    s.whatsapp_number = request.form.get("whatsapp_number","").strip() or s.whatsapp_number
    s.address = request.form.get("address","").strip()
    s.logo_url = request.form.get("logo_url","").strip()
    db.session.commit()
    flash("Configurações salvas.", "success")
    return redirect(url_for("admin"))

# ---------- CLI helpers ----------
@app.cli.command("init-db")
def init_db():
    """Inicializa o banco com alguns exemplos."""
    db.create_all()
    if not Settings.query.first():
        db.session.add(Settings())
    if Product.query.count() == 0:
        db.session.add_all([
            Product(name="Pizza Margherita", price_cents=3990, category="Pizzas",
                    photo_url="https://images.unsplash.com/photo-1548365328-9f547fb09530?q=80&w=600&auto=format&fit=crop"),
            Product(name="Coca-Cola 350ml", price_cents=700, category="Bebidas",
                    photo_url="https://images.unsplash.com/photo-1613478223719-6c2e1c79e93e?q=80&w=600&auto=format&fit=crop"),
        ])
    db.session.commit()
    print("Banco inicializado.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
