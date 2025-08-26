# Mock E‑commerce (Flask) — Heroku + Cookie Consent + Pixels

Minimal shop with catalog, cart, mock checkout, **cookie consent**, and **placeholder pixels** for Meta/TikTok/Snap.

### Events wired
- ViewContent (product detail page load)
- AddToCart (add-to-cart submit)
- InitiateCheckout (checkout page load)
- AddPaymentInfo (checkout submit)
- Purchase/CompletePayment (success page load)

### Troubleshooting scenarios (env vars)
1. `SCENARIO_SKIP_CHECKOUT_PIXELS=true` — **do not** load pixels on `/checkout`, but load again on the purchase page
2. `SCENARIO_DEFER_FIRST_LOAD_AFTER_CONSENT=true` — even with consent accepted, pixels do **not** load on the first page load; they load after you reload the page (uses `sessionStorage`)
3. `SCENARIO_NO_SNAP_PII=true` — never send PII to Snap (PII allowed for Meta/TikTok)
4. `SCENARIO_NO_SNAP_VALUES=true` — do **not** send content_id/item_id/price/value/currency to Snap (Meta/TikTok get full payloads)

> **Note:** This project intentionally keeps Snap payloads minimal to simulate missing values/PII. Meta/TikTok include `content_id/item_id`, `price`, `value`, and `currency` where applicable.

## Local run
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional pixel IDs
export META_PIXEL_ID=REPLACE_ME
export TIKTOK_PIXEL_ID=REPLACE_ME
export SNAP_PIXEL_ID=REPLACE_ME
export CURRENCY=USD

# Scenarios (optional)
export SCENARIO_SKIP_CHECKOUT_PIXELS=false
export SCENARIO_DEFER_FIRST_LOAD_AFTER_CONSENT=false
export SCENARIO_NO_SNAP_PII=true
export SCENARIO_NO_SNAP_VALUES=true

python seed.py
flask --app app run --debug
```

## Deploy to Heroku
```bash
heroku login
heroku create your-app-name
heroku buildpacks:set heroku/python
heroku addons:create heroku-postgresql:hobby-dev

git init && git add . && git commit -m "init consent + pixels"
heroku git:remote -a your-app-name
git push heroku HEAD:main

heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
heroku config:set META_PIXEL_ID=REPLACE_ME TIKTOK_PIXEL_ID=REPLACE_ME SNAP_PIXEL_ID=REPLACE_ME CURRENCY=USD
# Optional scenarios:
# heroku config:set SCENARIO_SKIP_CHECKOUT_PIXELS=true
# heroku config:set SCENARIO_DEFER_FIRST_LOAD_AFTER_CONSENT=true
# heroku config:set SCENARIO_NO_SNAP_PII=true
# heroku config:set SCENARIO_NO_SNAP_VALUES=true

heroku run python seed.py
```
