"""Slim entry point – wires up all modular routers."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import logging
import os
import json
import stripe
from datetime import datetime, timezone, timedelta

from config import client, store_db, db, UPLOAD_DIR, SUBSCRIPTION_TIERS
from auth import load_settings_from_db
from routes.antenna import router as antenna_router
from routes.user import router as user_router
from routes.admin import router as admin_router
from routes.public import router as public_router
from routes.store import router as store_router, seed_store_products

app = FastAPI()

# ── Route routers (all prefixed with /api) ──
app.include_router(public_router, prefix="/api")
app.include_router(antenna_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(store_router, prefix="/api")


# ── Stripe Webhook (needs raw body, mounted directly on app) ──
@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    stripe_key = os.environ.get("STRIPE_API_KEY", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    stripe.api_key = stripe_key
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(body, sig, webhook_secret)
        else:
            event = json.loads(body)
        event_type = event.get("type") if isinstance(event, dict) else event.type
        if event_type == "checkout.session.completed":
            session_data = (
                event.get("data", {}).get("object", {})
                if isinstance(event, dict)
                else event.data.object
            )
            session_id = (
                session_data.get("id")
                if isinstance(session_data, dict)
                else session_data.id
            )
            payment_status = (
                session_data.get("payment_status")
                if isinstance(session_data, dict)
                else session_data.payment_status
            )
            if payment_status == "paid" and session_id:
                await store_db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {
                        "$set": {
                            "payment_status": "paid",
                            "status": "complete",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    },
                )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── Static file serving for uploads ──
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifecycle ──
@app.on_event("startup")
async def startup_load_settings():
    await load_settings_from_db()
    await seed_store_products()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
