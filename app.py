import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

def normalize_database_url(db_url: str) -> str:
    if db_url and db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql://", 1)
    return db_url

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
    db_url = normalize_database_url(os.environ.get("DATABASE_URL", "sqlite:///app.db"))
    if db_url.startswith("postgresql://") and "sslmode=" not in db_url:
        db_url += ("&" if "?" in db_url else "?") + "sslmode=require"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    return app

app = create_app()
db = SQLAlchemy(app)

@app.context_processor
def inject_utilities():
    def money(cents): return f"${(cents or 0)/100:.2f}"
    return dict(money=money)

@app.context_processor
def inject_pixels_and_flags():
    def flag(name, default="false"):
        return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")
    return dict(
        META_PIXEL_ID=os.environ.get("META_PIXEL_ID", ""),
        TIKTOK_PIXEL_ID=os.environ.get("TIKTOK_PIXEL_ID", ""),
        SNAP_PIXEL_ID=os.environ.get("SNAP_PIXEL_ID", ""),
        CURRENCY=os.environ.get("CURRENCY", "USD"),
        SCENARIO_SKIP_CHECKOUT_PIXELS=flag("SCENARIO_SKIP_CHECKOUT_PIXELS"),
        SCENARIO_DEFER_FIRST_LOAD_AFTER_CONSENT=flag("SCENARIO_DEFER_FIRST_LOAD_AFTER_CONSENT"),
        SCENARIO_NO_SNAP_PII=flag("SCENARIO_NO_SNAP_PII", "true"),
        SCENARIO_NO_SNAP_VALUES=flag("SCENARIO_NO_SNAP_VALUES", "true"),
    )

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    price_cents = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=True)
    inventory = db.Column(db.Integer, nullable=False, default=0)
    def price_display(self): return f"${self.price_cents/100:.2f}"

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(250), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    total_cents = db.Column(db.Integer, nullable=False, default=0)

class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_cents = db.Column(db.Integer, nullable=False, default=0)

def setup_db():
    with app.app_context():
        db.create_all()
        # Optional seed-on-start (idempotent)
        if db.session.query(func.count(Product.id)).scalar() == 0:
            sample_products = [
                Product(name="Cozy Hoodie", description="A warm, comfy hoodie.", price_cents=4999, image_url="https://picsum.photos/seed/hoodie/600/400", inventory=25),
                Product(name="Classic Sneakers", description="Everyday sneakers.", price_cents=6999, image_url="https://picsum.photos/seed/sneakers/600/400", inventory=30),
                Product(name="Beanie", description="Soft knit beanie.", price_cents=1999, image_url="https://picsum.photos/seed/beanie/600/400", inventory=50),
                Product(name="Insulated Bottle", description="Keeps drinks cold or hot.", price_cents=2499, image_url="https://picsum.photos/seed/bottle/600/400", inventory=40),
            ]
            db.session.add_all(sample_products)
            db.session.commit()

setup_db()

def get_cart(): return session.setdefault("cart", {})
def save_cart(cart): session["cart"]=cart; session.modified=True

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    query = Product.query
    if q:
        like = f"%{q}%"
        query = query.filter((Product.name.ilike(like)) | (Product.description.ilike(like)))
    products = query.order_by(Product.id.desc()).all()
    return render_template("index.html", products=products, q=q)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product.html", product=product)

@app.route("/cart")
def view_cart():
    cart = get_cart()
    items, subtotal = [], 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if not product: continue
        line_total = product.price_cents * qty
        subtotal += line_total
        items.append({"product": product, "qty": qty, "line_total": line_total})
    return render_template("cart.html", items=items, subtotal=subtotal)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    pid = request.form.get("product_id"); qty = int(request.form.get("quantity","1"))
    if not pid: flash("Invalid product.","error"); return redirect(url_for("index"))
    product = Product.query.get(pid)
    if not product: flash("Product not found.","error"); return redirect(url_for("index"))
    if qty < 1: qty = 1
    cart = get_cart(); cart[str(pid)] = cart.get(str(pid),0)+qty; save_cart(cart)
    flash(f"Added {qty} × {product.name} to cart.","success")
    return redirect(request.referrer or url_for("index"))

@app.route("/remove_from_cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = get_cart(); cart.pop(str(product_id), None); save_cart(cart)
    flash("Removed item from cart.","success")
    return redirect(url_for("view_cart"))

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.","error")
        return redirect(url_for("index"))
    items, subtotal = [], 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if not product: continue
        line_total = product.price_cents*qty; subtotal+=line_total
        items.append({"product": product, "qty": qty, "line_total": line_total})
    if request.method == "POST":
        required = [request.form.get(k,"").strip() for k in ["name","email","address","city","state","postal"]]
        if not all(required):
            flash("Please fill out all fields.","error")
            return render_template("checkout.html", items=items, subtotal=subtotal)
        order = Order(customer_name=request.form["name"], customer_email=request.form["email"],
                      address=request.form["address"], city=request.form["city"],
                      state=request.form["state"], postal_code=request.form["postal"],
                      total_cents=subtotal)
        db.session.add(order); db.session.flush()
        for it in items:
            db.session.add(OrderItem(order_id=order.id, product_id=it["product"].id, quantity=it["qty"], price_cents=it["product"].price_cents))
        db.session.commit()
        session["cart"] = {}
        flash("Order placed! (Mock checkout)","success")
        return redirect(url_for("order_success", order_id=order.id))
    return render_template("checkout.html", items=items, subtotal=subtotal)

@app.route("/success/<int:order_id>")
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("success.html", order=order)

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
