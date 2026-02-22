"""User auth, subscription, saved designs, history, and status endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from typing import List
import uuid
import os
import httpx
import base64
import stripe
import logging

from config import db, ADMIN_EMAIL, SUBSCRIPTION_TIERS, PAYMENT_CONFIG
from models import (
    UserCreate, UserLogin, SubscriptionUpdate, PaymentRecord,
    SaveDesignRequest, SaveDesignResponse, SavedDesign,
    ForgotPasswordRequest, ResetPasswordRequest,
    StatusCheck, StatusCheckCreate, CalculationRecord,
)
from auth import (
    security, hash_password, verify_password, create_token,
    require_user, check_subscription_active,
)
from services.email_service import send_email, email_wrapper
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Auth ──

@router.post("/auth/register")
async def register_user(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    is_admin = user_data.email.lower() == ADMIN_EMAIL.lower()
    tier = "admin" if is_admin else "trial"
    user = {
        "id": str(uuid.uuid4()), "email": user_data.email.lower(),
        "password": hash_password(user_data.password), "name": user_data.name,
        "subscription_tier": tier,
        "subscription_expires": datetime.utcnow() + timedelta(days=36500) if is_admin else None,
        "is_trial": not is_admin,
        "trial_started": datetime.utcnow() if not is_admin else None,
        "created_at": datetime.utcnow()
    }
    await db.users.insert_one(user)
    token = create_token(user["id"], user["email"])
    welcome_html = email_wrapper("Welcome!", f"""
        <h2 style="color:#fff;">Welcome to SMA Antenna Calc, {user_data.name}!</h2>
        <p style="color:#ccc;line-height:1.6;">Your account has been created. You have a <strong style="color:#FF9800;">free trial</strong> to explore the app.</p>
        <p style="color:#ccc;">Enjoy the app and 73!</p>
    """)
    await send_email(user["email"], "Welcome to SMA Antenna Calc!", welcome_html)
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "name": user["name"], "subscription_tier": user["subscription_tier"], "subscription_expires": user["subscription_expires"], "is_trial": user["is_trial"], "trial_started": user["trial_started"]}}


@router.post("/auth/login")
async def login_user(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], user["email"])
    is_active, tier_info, status_msg = check_subscription_active(user)
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "name": user["name"], "subscription_tier": user["subscription_tier"], "subscription_expires": user.get("subscription_expires"), "is_trial": user.get("is_trial", False), "trial_started": user.get("trial_started"), "is_active": is_active, "status_message": status_msg}}


@router.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    user = await db.users.find_one({"email": req.email.lower()})
    if not user:
        return {"message": "If that email exists, a reset link has been sent."}
    reset_token = str(uuid.uuid4())
    await db.password_resets.insert_one({"user_id": user["id"], "email": user["email"], "token": reset_token, "created_at": datetime.utcnow(), "expires_at": datetime.utcnow() + timedelta(hours=1), "used": False})
    reset_html = email_wrapper("Password Reset", f"""
        <h2 style="color:#fff;">Password Reset Requested</h2>
        <p style="color:#ccc;">Use this code in the app:</p>
        <div style="text-align:center;margin:20px 0;">
            <div style="display:inline-block;background:#4CAF50;color:#000;font-size:24px;font-weight:bold;padding:15px 30px;border-radius:8px;letter-spacing:4px;">{reset_token[:8].upper()}</div>
        </div>
        <p style="color:#aaa;font-size:12px;">This code expires in 1 hour.</p>
    """)
    await send_email(user["email"], "SMA Antenna Calc - Password Reset", reset_html)
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    resets = await db.password_resets.find({"used": False}).to_list(100)
    reset_entry = None
    for r in resets:
        if r["token"][:8].upper() == req.token.strip().upper():
            reset_entry = r
            break
    if not reset_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    if datetime.utcnow() > reset_entry["expires_at"]:
        raise HTTPException(status_code=400, detail="Reset code has expired")
    new_hash = hash_password(req.new_password)
    await db.users.update_one({"id": reset_entry["user_id"]}, {"$set": {"password": new_hash}})
    await db.password_resets.update_one({"_id": reset_entry["_id"]}, {"$set": {"used": True}})
    confirm_html = email_wrapper("Password Changed", '<h2 style="color:#fff;">Password Updated</h2><p style="color:#ccc;">Your password has been successfully changed.</p>')
    await send_email(reset_entry["email"], "SMA Antenna Calc - Password Changed", confirm_html)
    return {"message": "Password has been reset successfully"}


@router.post("/auth/send-receipt")
async def send_subscription_receipt(user: dict = Depends(require_user)):
    tier = user.get("subscription_tier", "trial")
    expires = user.get("subscription_expires")
    expires_str = expires.strftime("%B %d, %Y") if expires else "N/A"
    receipt_html = email_wrapper("Subscription Receipt", f"""
        <h2 style="color:#fff;">Subscription Confirmation</h2>
        <table style="width:100%;border-collapse:collapse;margin:20px 0;">
            <tr style="border-bottom:1px solid #333;"><td style="padding:10px;color:#888;">Account</td><td style="padding:10px;color:#fff;">{user['email']}</td></tr>
            <tr style="border-bottom:1px solid #333;"><td style="padding:10px;color:#888;">Plan</td><td style="padding:10px;color:#4CAF50;font-weight:bold;">{tier.upper()}</td></tr>
            <tr style="border-bottom:1px solid #333;"><td style="padding:10px;color:#888;">Valid Until</td><td style="padding:10px;color:#fff;">{expires_str}</td></tr>
            <tr><td style="padding:10px;color:#888;">Status</td><td style="padding:10px;color:#4CAF50;">Active</td></tr>
        </table>
    """)
    sent = await send_email(user["email"], "SMA Antenna Calc - Subscription Receipt", receipt_html)
    if sent:
        return {"message": "Receipt sent to your email"}
    raise HTTPException(status_code=500, detail="Failed to send receipt email")


@router.get("/auth/me")
async def get_current_user_info(user: dict = Depends(require_user)):
    is_active, tier_info, status_msg = check_subscription_active(user)
    return {"id": user["id"], "email": user["email"], "name": user["name"], "subscription_tier": user["subscription_tier"], "subscription_expires": user.get("subscription_expires"), "is_trial": user.get("is_trial", False), "trial_started": user.get("trial_started"), "is_active": is_active, "status_message": status_msg, "tier_info": tier_info, "max_elements": tier_info["max_elements"] if tier_info else 3}


# ── Subscription ──

@router.get("/subscription/tiers")
async def get_subscription_tiers():
    tiers = {k: v for k, v in SUBSCRIPTION_TIERS.items() if k != "admin"}
    return {"tiers": tiers, "payment_methods": PAYMENT_CONFIG}


PAYPAL_API_URL = "https://api-m.paypal.com"


async def get_payment_credentials(provider: str):
    """Get payment credentials from DB first, fall back to env vars."""
    cred = await db.payment_credentials.find_one({"provider": provider}, {"_id": 0})
    if cred:
        return cred
    if provider == "paypal":
        cid = os.environ.get("PAYPAL_CLIENT_ID", "")
        sec = os.environ.get("PAYPAL_SECRET", "")
        if cid and sec:
            return {"provider": "paypal", "client_id": cid, "secret": sec}
    elif provider == "stripe":
        key = os.environ.get("STRIPE_API_KEY", "")
        if key:
            return {"provider": "stripe", "api_key": key}
    return None


async def get_paypal_token():
    cred = await get_payment_credentials("paypal")
    if not cred or not cred.get("client_id") or not cred.get("secret"):
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PAYPAL_API_URL}/v1/oauth2/token",
            auth=(cred["client_id"], cred["secret"]),
            data={"grant_type": "client_credentials"},
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    return None


# ── Stripe Recurring Subscription Helpers ──

def _init_stripe():
    """Initialize stripe SDK with the correct API key and base."""
    key = os.environ.get("STRIPE_API_KEY", "")
    stripe.api_key = key
    if "sk_test_emergent" in key:
        stripe.api_base = "https://integrations.emergentagent.com/stripe"
    return key


async def ensure_stripe_prices():
    """Create or retrieve Stripe recurring Prices for each tier. Cache in DB."""
    key = _init_stripe()
    if not key:
        return {}

    # Check DB cache first
    cached = await db.stripe_prices.find_one({"type": "recurring_prices"}, {"_id": 0})
    if cached and cached.get("prices"):
        return cached["prices"]

    prices = {}
    tier_configs = {
        "bronze_monthly": {"amount": 3999, "interval": "month", "name": "Bronze Monthly"},
        "bronze_yearly": {"amount": 40000, "interval": "year", "name": "Bronze Yearly"},
        "silver_monthly": {"amount": 5999, "interval": "month", "name": "Silver Monthly"},
        "silver_yearly": {"amount": 67500, "interval": "year", "name": "Silver Yearly"},
        "gold_monthly": {"amount": 9999, "interval": "month", "name": "Gold Monthly"},
        "gold_yearly": {"amount": 105000, "interval": "year", "name": "Gold Yearly"},
    }

    for tier_key, cfg in tier_configs.items():
        try:
            # Use the current price from SUBSCRIPTION_TIERS if available
            tier_info = SUBSCRIPTION_TIERS.get(tier_key, {})
            amount_cents = int(tier_info.get("price", cfg["amount"] / 100) * 100)
            price = stripe.Price.create(
                unit_amount=amount_cents,
                currency="usd",
                recurring={"interval": cfg["interval"]},
                product_data={"name": f"SMA Antenna Calc - {cfg['name']}"},
            )
            prices[tier_key] = price.id
            logger.info(f"Created Stripe recurring price for {tier_key}: {price.id}")
        except Exception as e:
            logger.error(f"Failed to create Stripe price for {tier_key}: {e}")

    if prices:
        await db.stripe_prices.update_one(
            {"type": "recurring_prices"},
            {"$set": {"type": "recurring_prices", "prices": prices, "updated_at": datetime.utcnow().isoformat()}},
            upsert=True,
        )
    return prices


async def get_stripe_price_id(tier_key: str) -> str:
    """Get the Stripe Price ID for a given tier."""
    cached = await db.stripe_prices.find_one({"type": "recurring_prices"}, {"_id": 0})
    if cached and cached.get("prices", {}).get(tier_key):
        return cached["prices"][tier_key]
    # Try to create them
    prices = await ensure_stripe_prices()
    return prices.get(tier_key, "")


@router.post("/subscription/upgrade")
async def upgrade_subscription(upgrade: SubscriptionUpdate, user: dict = Depends(require_user)):
    """Legacy endpoint for manual payment methods — creates pending request."""
    if upgrade.tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    tier_info = SUBSCRIPTION_TIERS[upgrade.tier]
    pending_request = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_email": user["email"],
        "user_name": user.get("name", ""),
        "tier": upgrade.tier,
        "tier_name": tier_info["name"],
        "amount": tier_info["price"],
        "payment_method": upgrade.payment_method,
        "payment_reference": upgrade.payment_reference,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.pending_upgrades.insert_one(pending_request)
    return {
        "success": True,
        "message": f"Upgrade request submitted for {tier_info['name']}. Your account will be upgraded once payment is verified by admin.",
        "status": "pending",
        "request_id": pending_request["id"],
    }


@router.post("/subscription/paypal-checkout")
async def paypal_subscription_checkout(data: dict, request: Request, user: dict = Depends(require_user)):
    """Create a PayPal order — user gets redirected to PayPal to pay."""
    tier_key = data.get("tier")
    if not tier_key or tier_key not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    origin_url = data.get("origin_url", "")
    if not origin_url:
        raise HTTPException(status_code=400, detail="origin_url required")

    tier_info = SUBSCRIPTION_TIERS[tier_key]
    amount = str(tier_info["price"])

    access_token = await get_paypal_token()
    if not access_token:
        raise HTTPException(status_code=500, detail="PayPal not configured")

    # Use backend route as return URL so it works for both mobile and web
    host_url = str(request.base_url).rstrip("/")
    order_data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value": amount},
            "description": f"SMA Antenna Calc — {tier_info['name']} Subscription",
        }],
        "application_context": {
            "return_url": f"{host_url}/api/subscription/paypal-return",
            "cancel_url": f"{origin_url}/subscription?payment=cancelled",
            "brand_name": "SMA Antenna Calculator",
            "user_action": "PAY_NOW",
        },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PAYPAL_API_URL}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=order_data,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"PayPal error: {resp.text}")

    pp_order = resp.json()
    order_id = pp_order["id"]
    approve_url = next((l["href"] for l in pp_order.get("links", []) if l["rel"] == "approve"), None)
    if not approve_url:
        raise HTTPException(status_code=500, detail="No PayPal approval URL")

    # Fix return URL with actual order ID
    return_url = f"{origin_url}/subscription?paypal_order_id={order_id}&payment=paypal_success"

    # Store transaction
    txn = {
        "id": str(uuid.uuid4()),
        "paypal_order_id": order_id,
        "user_id": user["id"],
        "user_email": user["email"],
        "tier": tier_key,
        "tier_name": tier_info["name"],
        "amount": float(amount),
        "payment_method": "paypal",
        "payment_status": "created",
        "status": "initiated",
        "type": "subscription",
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.payment_transactions.insert_one(txn)

    return {"url": approve_url, "order_id": order_id}


@router.get("/subscription/paypal-return", response_class=HTMLResponse)
async def paypal_return(token: str = "", PayerID: str = ""):
    """Handle PayPal redirect after payment — captures payment and shows success page."""
    order_id = token  # PayPal passes order_id as 'token' param
    if not order_id:
        return HTMLResponse(_paypal_result_page("Payment Error", "No order ID received from PayPal.", False))

    # Capture the payment
    access_token = await get_paypal_token()
    if not access_token:
        return HTMLResponse(_paypal_result_page("Configuration Error", "PayPal is not configured. Please contact support.", False))

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={},
        )

    capture_data = resp.json()
    capture_status = capture_data.get("status", "")

    if capture_status != "COMPLETED":
        return HTMLResponse(_paypal_result_page("Payment Incomplete", f"PayPal payment status: {capture_status}. Please try again or contact support.", False))

    # Find and update transaction
    txn = await db.payment_transactions.find_one({"paypal_order_id": order_id, "type": "subscription"})
    if not txn:
        return HTMLResponse(_paypal_result_page("Payment Received", "Your payment was successful! Your account will be upgraded shortly. You can close this page and return to the app.", True))

    if txn.get("payment_status") == "paid":
        tier_name = txn.get("tier_name", "your plan")
        return HTMLResponse(_paypal_result_page("Already Upgraded", f"You're already on {tier_name}! Close this page and return to the app.", True))

    # Upgrade the user
    tier_key = txn["tier"]
    tier_info = SUBSCRIPTION_TIERS.get(tier_key, {})
    duration_days = tier_info.get("duration_days", 30)
    expires = datetime.utcnow() + timedelta(days=duration_days)
    tier_name = tier_info.get("name", tier_key)

    await db.users.update_one(
        {"id": txn["user_id"]},
        {"$set": {"subscription_tier": tier_key, "subscription_expires": expires, "is_trial": False}},
    )
    await db.payment_transactions.update_one(
        {"paypal_order_id": order_id, "type": "subscription"},
        {"$set": {"payment_status": "paid", "status": "complete", "updated_at": datetime.utcnow().isoformat()}},
    )

    return HTMLResponse(_paypal_result_page("Payment Successful!", f"You've been upgraded to {tier_name}! Close this page and return to the app.", True))


def _paypal_result_page(title: str, message: str, success: bool) -> str:
    color = "#4CAF50" if success else "#f44336"
    icon = "&#10004;" if success else "&#10008;"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - SMA Antenna Calc</title>
<style>
body{{margin:0;padding:40px 20px;background:#121212;color:#fff;font-family:-apple-system,system-ui,sans-serif;text-align:center;}}
.card{{max-width:400px;margin:60px auto;background:#1E1E1E;border-radius:16px;padding:40px 24px;border:2px solid {color};}}
.icon{{font-size:64px;color:{color};margin-bottom:16px;}}
h1{{font-size:22px;color:{color};margin:0 0 12px;}}
p{{font-size:15px;color:#aaa;line-height:1.5;margin:0 0 24px;}}
.btn{{display:inline-block;background:{color};color:#fff;padding:14px 28px;border-radius:12px;text-decoration:none;font-weight:600;font-size:16px;}}
</style></head><body>
<div class="card">
<div class="icon">{icon}</div>
<h1>{title}</h1>
<p>{message}</p>
<a class="btn" href="javascript:window.close()">Close This Page</a>
</div></body></html>"""


@router.post("/subscription/paypal-capture/{order_id}")
async def paypal_capture_order(order_id: str, user: dict = Depends(require_user)):
    """Capture a PayPal order after user approves — upgrades user if successful."""
    access_token = await get_paypal_token()
    if not access_token:
        raise HTTPException(status_code=500, detail="PayPal not configured")

    # Capture the payment
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={},
        )

    capture_data = resp.json()
    capture_status = capture_data.get("status", "")

    if capture_status != "COMPLETED":
        return {"success": False, "status": capture_status, "message": "Payment not completed"}

    # Find the transaction
    txn = await db.payment_transactions.find_one(
        {"paypal_order_id": order_id, "type": "subscription"}, {"_id": 0}
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.get("payment_status") == "paid":
        return {"success": True, "status": "already_upgraded", "tier_name": txn.get("tier_name")}

    # Upgrade the user
    tier_key = txn["tier"]
    tier_info = SUBSCRIPTION_TIERS.get(tier_key, {})
    duration_days = tier_info.get("duration_days", 30)
    expires = datetime.utcnow() + timedelta(days=duration_days)

    await db.users.update_one(
        {"id": txn["user_id"]},
        {"$set": {"subscription_tier": tier_key, "subscription_expires": expires, "is_trial": False}},
    )

    # Mark transaction as paid
    await db.payment_transactions.update_one(
        {"paypal_order_id": order_id, "type": "subscription"},
        {"$set": {"payment_status": "paid", "status": "complete", "updated_at": datetime.utcnow().isoformat()}},
    )

    return {"success": True, "status": "completed", "tier_name": txn.get("tier_name")}


@router.get("/subscription/pending")
async def get_pending_upgrade(user: dict = Depends(require_user)):
    pending = await db.pending_upgrades.find_one(
        {"user_id": user["id"], "status": "pending"}, {"_id": 0}
    )
    return {"pending": pending}


@router.post("/subscription/stripe-checkout")
async def stripe_subscription_checkout(data: dict, request: Request, user: dict = Depends(require_user)):
    tier_key = data.get("tier")
    if not tier_key or tier_key not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    origin_url = data.get("origin_url", "")
    if not origin_url:
        raise HTTPException(status_code=400, detail="origin_url required")
    tier_info = SUBSCRIPTION_TIERS[tier_key]
    amount = float(tier_info["price"])

    # Use Stripe subscription mode for recurring billing
    key = _init_stripe()
    if not key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    price_id = await get_stripe_price_id(tier_key)
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe recurring price not configured for this tier")

    success_url = f"{origin_url}/subscription?session_id={{CHECKOUT_SESSION_ID}}&payment=success"
    cancel_url = f"{origin_url}/subscription?payment=cancelled"

    # Find or create Stripe customer for this user
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            name=user.get("name", ""),
            metadata={"user_id": user["id"]},
        )
        customer_id = customer.id
        await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer_id}})

    # If user already has an active Stripe subscription, cancel the old one first
    old_sub_id = user.get("stripe_subscription_id")
    if old_sub_id:
        try:
            stripe.Subscription.cancel(old_sub_id)
        except Exception:
            pass  # Old sub may already be cancelled

    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "user_email": user["email"],
            "tier": tier_key,
            "tier_name": tier_info["name"],
            "type": "subscription",
            "webhook_url": webhook_url,
        },
    )

    # Record the pending transaction
    txn = {
        "id": str(uuid.uuid4()),
        "session_id": session.id,
        "user_id": user["id"],
        "user_email": user["email"],
        "tier": tier_key,
        "tier_name": tier_info["name"],
        "amount": amount,
        "payment_method": "stripe",
        "payment_status": "pending",
        "status": "initiated",
        "type": "subscription",
        "billing_mode": "recurring",
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.payment_transactions.insert_one(txn)
    return {"url": session.url, "session_id": session.id}


@router.get("/subscription/stripe-status/{session_id}")
async def stripe_subscription_status(session_id: str, user: dict = Depends(require_user)):
    key = _init_stripe()
    if not key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")

    payment_status = session.payment_status  # 'paid', 'unpaid', 'no_payment_required'
    stripe_sub_id = getattr(session, "subscription", None)

    txn = await db.payment_transactions.find_one({"session_id": session_id, "type": "subscription"}, {"_id": 0})
    if payment_status == "paid" and txn and txn.get("payment_status") != "paid":
        tier_key = txn.get("tier", "")
        tier_info = SUBSCRIPTION_TIERS.get(tier_key, {})
        duration_days = tier_info.get("duration_days", 30)
        expires = datetime.utcnow() + timedelta(days=duration_days)

        # Store Stripe subscription ID on user for future management
        update_fields = {
            "subscription_tier": tier_key,
            "subscription_expires": expires,
            "is_trial": False,
            "auto_renew": True,
            "billing_method": "stripe",
        }
        if stripe_sub_id:
            update_fields["stripe_subscription_id"] = stripe_sub_id
        await db.users.update_one({"id": txn["user_id"]}, {"$set": update_fields})

        # Mark transaction as paid
        txn_update = {
            "payment_status": "paid",
            "status": "complete",
            "billing_mode": "recurring",
            "updated_at": datetime.utcnow().isoformat(),
        }
        if stripe_sub_id:
            txn_update["stripe_subscription_id"] = stripe_sub_id
        await db.payment_transactions.update_one(
            {"session_id": session_id, "type": "subscription"},
            {"$set": txn_update},
        )
    return {
        "status": "complete" if payment_status == "paid" else "pending",
        "payment_status": payment_status,
        "amount_total": session.amount_total / 100 if session.amount_total else 0,
        "tier": txn.get("tier") if txn else None,
        "tier_name": txn.get("tier_name") if txn else None,
        "auto_renew": True,
    }


@router.post("/subscription/cancel")
async def cancel_subscription(user: dict = Depends(require_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"subscription_tier": "trial", "subscription_expires": None, "is_trial": False, "cancelled_at": datetime.utcnow()}})
    return {"success": True, "message": "Subscription cancelled. You can renew anytime."}


@router.get("/subscription/status")
async def get_subscription_status(user: dict = Depends(require_user)):
    is_active, tier_info, status_msg = check_subscription_active(user)
    trial_remaining = None
    if user.get("is_trial") and user.get("trial_started"):
        trial_started = user["trial_started"]
        if isinstance(trial_started, str):
            trial_started = datetime.fromisoformat(trial_started.replace('Z', '+00:00'))
        elapsed = datetime.utcnow() - trial_started.replace(tzinfo=None)
        remaining = timedelta(hours=1) - elapsed
        trial_remaining = max(0, remaining.total_seconds())
    return {"is_active": is_active, "status_message": status_msg, "tier": user["subscription_tier"], "tier_info": tier_info, "expires": user.get("subscription_expires"), "trial_remaining_seconds": trial_remaining, "max_elements": tier_info["max_elements"] if tier_info else 3}


# ── Saved Designs ──

@router.post("/designs/save", response_model=SaveDesignResponse)
async def save_design(request: SaveDesignRequest, user: dict = Depends(require_user)):
    design = SavedDesign(user_id=user["id"], name=request.name, description=request.description, design_data=request.design_data, spacing_state=request.spacing_state)
    await db.saved_designs.insert_one(design.dict())
    return SaveDesignResponse(id=design.id, name=design.name, message="Design saved successfully")


@router.get("/designs")
async def get_user_designs(user: dict = Depends(require_user)):
    designs = await db.saved_designs.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    return [{"id": d["id"], "name": d["name"], "description": d.get("description", ""), "created_at": d["created_at"], "updated_at": d.get("updated_at", d["created_at"])} for d in designs]


@router.get("/designs/{design_id}")
async def get_design(design_id: str, user: dict = Depends(require_user)):
    design = await db.saved_designs.find_one({"id": design_id, "user_id": user["id"]})
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return {"id": design["id"], "name": design["name"], "description": design.get("description", ""), "design_data": design["design_data"], "spacing_state": design.get("spacing_state"), "created_at": design["created_at"]}


@router.delete("/designs/{design_id}")
async def delete_design(design_id: str, user: dict = Depends(require_user)):
    result = await db.saved_designs.delete_one({"id": design_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Design not found")
    return {"message": "Design deleted successfully"}


# ── History & Status ──

@router.get("/history", response_model=List[CalculationRecord])
async def get_calculation_history():
    records = await db.calculations.find().sort("timestamp", -1).limit(20).to_list(20)
    return [CalculationRecord(**record) for record in records]


@router.delete("/history")
async def clear_history():
    result = await db.calculations.delete_many({})
    return {"deleted_count": result.deleted_count}


@router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.dict())
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj


@router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**sc) for sc in status_checks]
