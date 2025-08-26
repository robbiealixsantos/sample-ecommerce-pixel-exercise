from app import db, Product, app

SAMPLE_PRODUCTS = [
    dict(name="Cozy Hoodie", description="A warm, comfy hoodie.", price_cents=4999, image_url="https://picsum.photos/seed/hoodie/600/400", inventory=25),
    dict(name="Classic Sneakers", description="Everyday sneakers.", price_cents=6999, image_url="https://picsum.photos/seed/sneakers/600/400", inventory=30),
    dict(name="Beanie", description="Soft knit beanie.", price_cents=1999, image_url="https://picsum.photos/seed/beanie/600/400", inventory=50),
    dict(name="Insulated Bottle", description="Keeps drinks cold or hot.", price_cents=2499, image_url="https://picsum.photos/seed/bottle/600/400", inventory=40),
]

def run_seed():
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            for p in SAMPLE_PRODUCTS:
                db.session.add(Product(**p))
            db.session.commit()
            print(f"Seeded {len(SAMPLE_PRODUCTS)} products.")
        else:
            print("Products already exist. Skipping seed.")

if __name__ == "__main__":
    run_seed()
