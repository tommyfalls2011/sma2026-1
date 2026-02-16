"""User auth, subscription, saved designs, history, and status endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import List
import uuid

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


@router.post("/subscription/upgrade")
async def upgrade_subscription(upgrade: SubscriptionUpdate, user: dict = Depends(require_user)):
    if upgrade.tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    tier_info = SUBSCRIPTION_TIERS[upgrade.tier]
    payment = PaymentRecord(user_id=user["id"], amount=tier_info["price"], tier=upgrade.tier, payment_method=upgrade.payment_method, payment_reference=upgrade.payment_reference, status="pending")
    await db.payments.insert_one(payment.dict())
    duration_days = tier_info.get("duration_days", 30)
    expires = datetime.utcnow() + timedelta(days=duration_days)
    await db.users.update_one({"id": user["id"]}, {"$set": {"subscription_tier": upgrade.tier, "subscription_expires": expires, "is_trial": False}})
    await db.payments.update_one({"id": payment.id}, {"$set": {"status": "completed"}})
    return {"success": True, "message": f"Upgraded to {tier_info['name']}", "subscription_tier": upgrade.tier, "subscription_expires": expires, "max_elements": tier_info["max_elements"]}


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
    design = SavedDesign(user_id=user["id"], name=request.name, description=request.description, design_data=request.design_data)
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
    return {"id": design["id"], "name": design["name"], "description": design.get("description", ""), "design_data": design["design_data"], "created_at": design["created_at"]}


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
