"""Slim entry point – wires up all modular routers."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import logging
import os
import json
import uuid
import stripe
from datetime import datetime, timezone, timedelta

from config import client, store_db, db, UPLOAD_DIR, SUBSCRIPTION_TIERS
from auth import load_settings_from_db
from routes.antenna import router as antenna_router
from routes.user import router as user_router, ensure_stripe_prices
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
    if "sk_test_emergent" in stripe_key:
        stripe.api_base = "https://integrations.emergentagent.com/stripe"

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(body, sig, webhook_secret)
        else:
            event = json.loads(body)
        event_type = event.get("type") if isinstance(event, dict) else event.type
        logger.info(f"Stripe webhook received: {event_type}")

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
            metadata = (
                session_data.get("metadata", {})
                if isinstance(session_data, dict)
                else (session_data.metadata or {})
            )
            stripe_sub_id = (
                session_data.get("subscription")
                if isinstance(session_data, dict)
                else getattr(session_data, "subscription", None)
            )
            stripe_customer_id = (
                session_data.get("customer")
                if isinstance(session_data, dict)
                else getattr(session_data, "customer", None)
            )

            if payment_status == "paid" and session_id:
                # Handle store payments
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
                # Handle subscription payments
                sub_txn = await db.payment_transactions.find_one(
                    {"session_id": session_id, "type": "subscription", "payment_status": {"$ne": "paid"}}
                )
                if sub_txn:
                    tier_key = metadata.get("tier") or sub_txn.get("tier", "")
                    tier_info = SUBSCRIPTION_TIERS.get(tier_key, {})
                    duration_days = tier_info.get("duration_days", 30)
                    expires = datetime.now(timezone.utc) + timedelta(days=duration_days)
                    user_update = {
                        "subscription_tier": tier_key,
                        "subscription_expires": expires,
                        "is_trial": False,
                        "auto_renew": True,
                        "billing_method": "stripe",
                    }
                    if stripe_sub_id:
                        user_update["stripe_subscription_id"] = stripe_sub_id
                    if stripe_customer_id:
                        user_update["stripe_customer_id"] = stripe_customer_id
                    await db.users.update_one(
                        {"id": sub_txn["user_id"]},
                        {"$set": user_update},
                    )
                    txn_update = {
                        "payment_status": "paid",
                        "status": "complete",
                        "billing_mode": "recurring",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    if stripe_sub_id:
                        txn_update["stripe_subscription_id"] = stripe_sub_id
                    await db.payment_transactions.update_one(
                        {"session_id": session_id, "type": "subscription"},
                        {"$set": txn_update},
                    )
                    logger.info(f"Subscription activated for user {sub_txn['user_id']} tier={tier_key}")

        # Handle recurring invoice payments (auto-renewal)
        elif event_type == "invoice.paid":
            invoice_data = (
                event.get("data", {}).get("object", {})
                if isinstance(event, dict)
                else event.data.object
            )
            sub_id = (
                invoice_data.get("subscription")
                if isinstance(invoice_data, dict)
                else getattr(invoice_data, "subscription", None)
            )
            billing_reason = (
                invoice_data.get("billing_reason")
                if isinstance(invoice_data, dict)
                else getattr(invoice_data, "billing_reason", None)
            )
            # Only handle renewals, not the initial subscription
            if sub_id and billing_reason == "subscription_cycle":
                user = await db.users.find_one({"stripe_subscription_id": sub_id})
                if user:
                    tier_key = user.get("subscription_tier", "")
                    tier_info = SUBSCRIPTION_TIERS.get(tier_key, {})
                    duration_days = tier_info.get("duration_days", 30)
                    expires = datetime.now(timezone.utc) + timedelta(days=duration_days)
                    await db.users.update_one(
                        {"id": user["id"]},
                        {"$set": {"subscription_expires": expires, "auto_renew": True}},
                    )
                    # Record the renewal transaction
                    amount = (
                        (invoice_data.get("amount_paid", 0) if isinstance(invoice_data, dict) else getattr(invoice_data, "amount_paid", 0)) / 100
                    )
                    renewal_txn = {
                        "id": str(uuid.uuid4()),
                        "user_id": user["id"],
                        "user_email": user["email"],
                        "tier": tier_key,
                        "tier_name": tier_info.get("name", tier_key),
                        "amount": amount,
                        "payment_method": "stripe",
                        "payment_status": "paid",
                        "status": "complete",
                        "type": "subscription",
                        "billing_mode": "recurring_renewal",
                        "stripe_subscription_id": sub_id,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.payment_transactions.insert_one(renewal_txn)
                    logger.info(f"Subscription renewed for user {user['id']} tier={tier_key} expires={expires}")

        # Handle subscription cancellation
        elif event_type == "customer.subscription.deleted":
            sub_data = (
                event.get("data", {}).get("object", {})
                if isinstance(event, dict)
                else event.data.object
            )
            sub_id = (
                sub_data.get("id")
                if isinstance(sub_data, dict)
                else sub_data.id
            )
            if sub_id:
                user = await db.users.find_one({"stripe_subscription_id": sub_id})
                if user:
                    await db.users.update_one(
                        {"id": user["id"]},
                        {"$set": {"auto_renew": False, "stripe_subscription_id": None}},
                    )
                    logger.info(f"Subscription cancelled for user {user['id']}")

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
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
    # Initialize Stripe recurring prices for subscription billing
    try:
        await ensure_stripe_prices()
        logger.info("Stripe recurring prices initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Stripe prices (non-fatal): {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
