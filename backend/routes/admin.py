"""Admin endpoints: pricing, users, designs, discounts, notifications, tutorial, designer-info."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import uuid
import asyncio

from config import db, ADMIN_EMAIL, SUBSCRIPTION_TIERS, PAYMENT_CONFIG, RESEND_API_KEY
from models import (
    PricingUpdate, PaymentConfigUpdate, UserRoleUpdate, AdminCreateUser,
    DiscountCreate, SendUpdateEmail, UpdateTutorialRequest,
)
from auth import security, require_admin, require_user, hash_password
from services.email_service import send_email, email_wrapper, generate_qr_base64
from config import DEFAULT_TUTORIAL_CONTENT, DEFAULT_DESIGNER_INFO, SENDER_EMAIL

router = APIRouter()


# ── Pricing ──

@router.get("/admin/pricing")
async def get_admin_pricing(admin: dict = Depends(require_admin)):
    return {
        "bronze": {"monthly_price": SUBSCRIPTION_TIERS["bronze_monthly"]["price"], "yearly_price": SUBSCRIPTION_TIERS["bronze_yearly"]["price"], "max_elements": SUBSCRIPTION_TIERS["bronze_monthly"]["max_elements"], "features": SUBSCRIPTION_TIERS["bronze_monthly"].get("features", [])},
        "silver": {"monthly_price": SUBSCRIPTION_TIERS["silver_monthly"]["price"], "yearly_price": SUBSCRIPTION_TIERS["silver_yearly"]["price"], "max_elements": SUBSCRIPTION_TIERS["silver_monthly"]["max_elements"], "features": SUBSCRIPTION_TIERS["silver_monthly"].get("features", [])},
        "gold": {"monthly_price": SUBSCRIPTION_TIERS["gold_monthly"]["price"], "yearly_price": SUBSCRIPTION_TIERS["gold_yearly"]["price"], "max_elements": SUBSCRIPTION_TIERS["gold_monthly"]["max_elements"], "features": SUBSCRIPTION_TIERS["gold_monthly"].get("features", [])},
        "payment": {"paypal_email": PAYMENT_CONFIG["paypal"]["email"], "cashapp_tag": PAYMENT_CONFIG["cashapp"]["tag"]}
    }

@router.put("/admin/pricing")
async def update_pricing(pricing: PricingUpdate, admin: dict = Depends(require_admin)):
    SUBSCRIPTION_TIERS["bronze_monthly"]["price"] = pricing.bronze_monthly_price
    SUBSCRIPTION_TIERS["bronze_monthly"]["max_elements"] = pricing.bronze_max_elements
    SUBSCRIPTION_TIERS["bronze_monthly"]["features"] = pricing.bronze_features
    SUBSCRIPTION_TIERS["bronze_monthly"]["description"] = f"${pricing.bronze_monthly_price}/month - {pricing.bronze_max_elements} elements max"
    SUBSCRIPTION_TIERS["bronze_yearly"]["price"] = pricing.bronze_yearly_price
    SUBSCRIPTION_TIERS["bronze_yearly"]["max_elements"] = pricing.bronze_max_elements
    SUBSCRIPTION_TIERS["bronze_yearly"]["features"] = pricing.bronze_features
    yearly_savings = round((pricing.bronze_monthly_price * 12) - pricing.bronze_yearly_price, 0)
    SUBSCRIPTION_TIERS["bronze_yearly"]["description"] = f"${pricing.bronze_yearly_price}/year - {pricing.bronze_max_elements} elements (Save ${yearly_savings}!)"
    SUBSCRIPTION_TIERS["silver_monthly"]["price"] = pricing.silver_monthly_price
    SUBSCRIPTION_TIERS["silver_monthly"]["max_elements"] = pricing.silver_max_elements
    SUBSCRIPTION_TIERS["silver_monthly"]["features"] = pricing.silver_features
    SUBSCRIPTION_TIERS["silver_monthly"]["description"] = f"${pricing.silver_monthly_price}/month - {pricing.silver_max_elements} elements max"
    SUBSCRIPTION_TIERS["silver_yearly"]["price"] = pricing.silver_yearly_price
    SUBSCRIPTION_TIERS["silver_yearly"]["max_elements"] = pricing.silver_max_elements
    SUBSCRIPTION_TIERS["silver_yearly"]["features"] = pricing.silver_features
    yearly_savings = round((pricing.silver_monthly_price * 12) - pricing.silver_yearly_price, 0)
    SUBSCRIPTION_TIERS["silver_yearly"]["description"] = f"${pricing.silver_yearly_price}/year - {pricing.silver_max_elements} elements (Save ${yearly_savings}!)"
    SUBSCRIPTION_TIERS["gold_monthly"]["price"] = pricing.gold_monthly_price
    SUBSCRIPTION_TIERS["gold_monthly"]["max_elements"] = pricing.gold_max_elements
    SUBSCRIPTION_TIERS["gold_monthly"]["features"] = pricing.gold_features
    SUBSCRIPTION_TIERS["gold_monthly"]["description"] = f"${pricing.gold_monthly_price}/month - All features"
    SUBSCRIPTION_TIERS["gold_yearly"]["price"] = pricing.gold_yearly_price
    SUBSCRIPTION_TIERS["gold_yearly"]["max_elements"] = pricing.gold_max_elements
    SUBSCRIPTION_TIERS["gold_yearly"]["features"] = pricing.gold_features
    yearly_savings = round((pricing.gold_monthly_price * 12) - pricing.gold_yearly_price, 0)
    SUBSCRIPTION_TIERS["gold_yearly"]["description"] = f"${pricing.gold_yearly_price}/year - All features (Save ${yearly_savings}!)"
    await db.settings.update_one({"type": "pricing"}, {"$set": {"type": "pricing", "bronze_monthly_price": pricing.bronze_monthly_price, "bronze_yearly_price": pricing.bronze_yearly_price, "bronze_max_elements": pricing.bronze_max_elements, "bronze_features": pricing.bronze_features, "silver_monthly_price": pricing.silver_monthly_price, "silver_yearly_price": pricing.silver_yearly_price, "silver_max_elements": pricing.silver_max_elements, "silver_features": pricing.silver_features, "gold_monthly_price": pricing.gold_monthly_price, "gold_yearly_price": pricing.gold_yearly_price, "gold_max_elements": pricing.gold_max_elements, "gold_features": pricing.gold_features, "updated_at": datetime.utcnow()}}, upsert=True)
    return {"success": True, "message": "Pricing updated successfully"}

@router.put("/admin/payment")
async def update_payment_config(config: PaymentConfigUpdate, admin: dict = Depends(require_admin)):
    PAYMENT_CONFIG["paypal"]["email"] = config.paypal_email
    PAYMENT_CONFIG["cashapp"]["tag"] = config.cashapp_tag
    await db.settings.update_one({"type": "payment"}, {"$set": {"type": "payment", "paypal_email": config.paypal_email, "cashapp_tag": config.cashapp_tag, "updated_at": datetime.utcnow()}}, upsert=True)
    return {"success": True, "message": "Payment config updated successfully"}


# ── Users ──

@router.get("/admin/users")
async def get_all_users(admin: dict = Depends(require_admin)):
    users = await db.users.find().to_list(1000)
    return [{"id": u["id"], "email": u["email"], "name": u["name"], "subscription_tier": u["subscription_tier"], "subscription_expires": u.get("subscription_expires"), "is_trial": u.get("is_trial", False), "created_at": u.get("created_at")} for u in users]

@router.put("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, role_update: UserRoleUpdate, admin: dict = Depends(require_admin)):
    valid_roles = ["trial", "bronze", "silver", "gold", "subadmin"]
    if role_update.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("email", "").lower() == ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Cannot modify main admin account")
    expires = None
    is_trial = False
    if role_update.role == "subadmin": expires = datetime.utcnow() + timedelta(days=36500)
    elif role_update.role == "trial": is_trial = True
    elif role_update.role in ["bronze", "silver", "gold"]: expires = datetime.utcnow() + timedelta(days=30)
    await db.users.update_one({"id": user_id}, {"$set": {"subscription_tier": role_update.role, "subscription_expires": expires, "is_trial": is_trial}})
    return {"success": True, "message": f"User role updated to {role_update.role}"}

@router.get("/admin/check")
async def check_admin_status(user: dict = Depends(require_user)):
    is_main_admin = user.get("email", "").lower() == ADMIN_EMAIL.lower()
    is_subadmin = user.get("subscription_tier") == "subadmin"
    return {"is_admin": is_main_admin, "is_subadmin": is_subadmin, "can_edit_settings": is_main_admin, "has_full_access": is_main_admin or is_subadmin}

@router.post("/admin/users/create")
async def admin_create_user(user_data: AdminCreateUser, admin: dict = Depends(require_admin)):
    email = user_data.email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    valid_tiers = ["trial", "bronze", "silver", "gold", "subadmin"]
    if user_data.subscription_tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {valid_tiers}")
    password_hashed = hash_password(user_data.password)
    expires = None
    is_trial = False
    trial_started = None
    if user_data.subscription_tier == "trial":
        is_trial = True
        trial_started = datetime.utcnow()
        trial_days = user_data.trial_days if user_data.trial_days else 7
        expires = datetime.utcnow() + timedelta(days=trial_days)
    elif user_data.subscription_tier == "subadmin":
        expires = datetime.utcnow() + timedelta(days=36500)
    elif user_data.subscription_tier in ["bronze", "silver", "gold"]:
        expires = datetime.utcnow() + timedelta(days=30)
    new_user = {"id": str(uuid.uuid4()), "email": email, "name": user_data.name.strip(), "password": password_hashed, "subscription_tier": user_data.subscription_tier, "subscription_expires": expires, "is_trial": is_trial, "trial_started": trial_started, "created_at": datetime.utcnow(), "created_by_admin": admin["email"]}
    await db.users.insert_one(new_user)
    return {"success": True, "message": f"User {email} created successfully", "user": {"id": new_user["id"], "email": new_user["email"], "name": new_user["name"], "subscription_tier": new_user["subscription_tier"]}}

@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("email", "").lower() == ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Cannot delete main admin account")
    await db.saved_designs.delete_many({"user_id": user_id})
    await db.users.delete_one({"id": user_id})
    return {"success": True, "message": f"User {user['email']} deleted successfully"}


# ── Pending Upgrades ──

@router.get("/admin/pending-upgrades")
async def get_pending_upgrades(admin: dict = Depends(require_admin)):
    pending = await db.pending_upgrades.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"upgrades": pending}


@router.post("/admin/pending-upgrades/{request_id}/approve")
async def approve_upgrade(request_id: str, admin: dict = Depends(require_admin)):
    req = await db.pending_upgrades.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Upgrade request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {req['status']}")
    tier_key = req["tier"]
    tier_info = SUBSCRIPTION_TIERS.get(tier_key, {})
    duration_days = tier_info.get("duration_days", 30)
    expires = datetime.utcnow() + timedelta(days=duration_days)
    # Upgrade the user
    await db.users.update_one(
        {"id": req["user_id"]},
        {"$set": {"subscription_tier": tier_key, "subscription_expires": expires, "is_trial": False}},
    )
    # Mark request as approved
    await db.pending_upgrades.update_one(
        {"id": request_id},
        {"$set": {"status": "approved", "approved_by": admin["email"], "approved_at": datetime.utcnow().isoformat()}},
    )
    return {"success": True, "message": f"Approved {req['user_email']} for {req['tier_name']}"}


@router.post("/admin/pending-upgrades/{request_id}/reject")
async def reject_upgrade(request_id: str, admin: dict = Depends(require_admin)):
    req = await db.pending_upgrades.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Upgrade request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {req['status']}")
    await db.pending_upgrades.update_one(
        {"id": request_id},
        {"$set": {"status": "rejected", "rejected_by": admin["email"], "rejected_at": datetime.utcnow().isoformat()}},
    )
    return {"success": True, "message": f"Rejected upgrade request from {req['user_email']}"}


# ── Subscription Management ──

@router.post("/admin/subscription/manage")
async def admin_manage_subscription(data: dict, admin: dict = Depends(require_admin)):
    user_id = data.get("user_id")
    action = data.get("action")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if action == "extend":
        days = data.get("days", 30)
        current_expires = user.get("subscription_expires")
        if current_expires:
            if isinstance(current_expires, str):
                current_expires = datetime.fromisoformat(current_expires.replace('Z', '+00:00'))
            base = max(current_expires.replace(tzinfo=None), datetime.utcnow())
        else: base = datetime.utcnow()
        new_expires = base + timedelta(days=days)
        await db.users.update_one({"id": user_id}, {"$set": {"subscription_expires": new_expires, "is_trial": False}})
        return {"success": True, "message": f"Extended {days} days. Expires: {new_expires.isoformat()}"}
    elif action == "change_tier":
        new_tier = data.get("tier")
        if new_tier not in SUBSCRIPTION_TIERS:
            raise HTTPException(status_code=400, detail="Invalid tier")
        duration_days = SUBSCRIPTION_TIERS[new_tier].get("duration_days", 30)
        expires = datetime.utcnow() + timedelta(days=duration_days)
        await db.users.update_one({"id": user_id}, {"$set": {"subscription_tier": new_tier, "subscription_expires": expires, "is_trial": False}})
        return {"success": True, "message": f"Changed to {new_tier}. Expires: {expires.isoformat()}"}
    elif action == "cancel":
        await db.users.update_one({"id": user_id}, {"$set": {"subscription_tier": "trial", "subscription_expires": None, "is_trial": False, "cancelled_at": datetime.utcnow()}})
        return {"success": True, "message": "User subscription cancelled"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use: extend, change_tier, cancel")


# ── Designs Management ──

@router.get("/admin/designs")
async def admin_get_all_designs(admin: dict = Depends(require_admin)):
    designs = await db.saved_designs.find().to_list(length=500)
    result = []
    for design in designs:
        user = await db.users.find_one({"id": design.get("user_id")})
        result.append({"id": design.get("id"), "name": design.get("name"), "user_id": design.get("user_id"), "user_email": user.get("email") if user else "Unknown", "user_name": user.get("name") if user else "Unknown", "created_at": design.get("created_at"), "updated_at": design.get("updated_at"), "element_count": design.get("design_data", {}).get("num_elements", 0)})
    return {"designs": result, "total": len(result)}

@router.delete("/admin/designs/{design_id}")
async def admin_delete_design(design_id: str, admin: dict = Depends(require_admin)):
    design = await db.saved_designs.find_one({"id": design_id})
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    await db.saved_designs.delete_one({"id": design_id})
    return {"success": True, "message": f"Design '{design.get('name', 'Unnamed')}' deleted successfully"}

@router.delete("/admin/designs/bulk/all")
async def admin_delete_all_designs(admin: dict = Depends(require_admin)):
    result = await db.saved_designs.delete_many({})
    return {"success": True, "message": f"Deleted {result.deleted_count} designs"}

@router.delete("/admin/designs/bulk/user/{user_id}")
async def admin_delete_user_designs(user_id: str, admin: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.saved_designs.delete_many({"user_id": user_id})
    return {"success": True, "message": f"Deleted {result.deleted_count} designs from {user.get('email', 'Unknown')}"}


# ── Tutorial & Designer Info ──

@router.put("/admin/tutorial")
async def update_tutorial(request: UpdateTutorialRequest, admin: dict = Depends(require_admin)):
    await db.app_settings.update_one({"key": "tutorial_content"}, {"$set": {"key": "tutorial_content", "content": request.content, "updated_at": datetime.utcnow().isoformat(), "updated_by": admin["email"]}}, upsert=True)
    return {"success": True, "message": "Tutorial content updated"}

@router.get("/admin/tutorial")
async def admin_get_tutorial(admin: dict = Depends(require_admin)):
    tutorial = await db.app_settings.find_one({"key": "tutorial_content"}, {"_id": 0})
    if tutorial:
        return {"content": tutorial.get("content", DEFAULT_TUTORIAL_CONTENT), "updated_at": tutorial.get("updated_at"), "updated_by": tutorial.get("updated_by")}
    return {"content": DEFAULT_TUTORIAL_CONTENT, "updated_at": None, "updated_by": None}

@router.put("/admin/designer-info")
async def update_designer_info(request: UpdateTutorialRequest, admin: dict = Depends(require_admin)):
    await db.app_settings.update_one({"key": "designer_info"}, {"$set": {"key": "designer_info", "content": request.content, "updated_at": datetime.utcnow().isoformat(), "updated_by": admin["email"]}}, upsert=True)
    return {"success": True, "message": "Designer info updated"}

@router.get("/admin/designer-info")
async def admin_get_designer_info(admin: dict = Depends(require_admin)):
    info = await db.app_settings.find_one({"key": "designer_info"}, {"_id": 0})
    if info:
        return {"content": info.get("content", DEFAULT_DESIGNER_INFO), "updated_at": info.get("updated_at"), "updated_by": info.get("updated_by")}
    return {"content": DEFAULT_DESIGNER_INFO, "updated_at": None, "updated_by": None}


# ── Discounts ──

@router.get("/admin/discounts")
async def get_discounts(admin: dict = Depends(require_admin)):
    discounts = await db.discounts.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"discounts": discounts}

@router.post("/admin/discounts")
async def create_discount(data: DiscountCreate, admin: dict = Depends(require_admin)):
    existing = await db.discounts.find_one({"code": data.code.upper()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Discount code already exists")
    discount = {"id": str(uuid.uuid4()), "code": data.code.upper(), "discount_type": data.discount_type, "value": data.value, "applies_to": data.applies_to, "tiers": data.tiers if data.tiers else ["bronze", "silver", "gold"], "max_uses": data.max_uses, "times_used": 0, "expires_at": data.expires_at, "user_emails": [e.lower() for e in data.user_emails], "active": True, "created_at": datetime.utcnow().isoformat(), "created_by": admin["email"]}
    await db.discounts.insert_one(discount)
    discount.pop("_id", None)
    return {"discount": discount}

@router.put("/admin/discounts/{discount_id}")
async def update_discount(discount_id: str, data: DiscountCreate, admin: dict = Depends(require_admin)):
    existing = await db.discounts.find_one({"id": discount_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Discount not found")
    update_fields = {"code": data.code.upper(), "discount_type": data.discount_type, "value": data.value, "applies_to": data.applies_to, "tiers": data.tiers if data.tiers else ["bronze", "silver", "gold"], "max_uses": data.max_uses, "expires_at": data.expires_at, "user_emails": [e.lower() for e in data.user_emails]}
    await db.discounts.update_one({"id": discount_id}, {"$set": update_fields})
    updated = await db.discounts.find_one({"id": discount_id}, {"_id": 0})
    return {"discount": updated}

@router.delete("/admin/discounts/{discount_id}")
async def delete_discount(discount_id: str, admin: dict = Depends(require_admin)):
    result = await db.discounts.delete_one({"id": discount_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Discount not found")
    return {"message": "Discount deleted"}

@router.post("/admin/discounts/{discount_id}/toggle")
async def toggle_discount(discount_id: str, admin: dict = Depends(require_admin)):
    discount = await db.discounts.find_one({"id": discount_id}, {"_id": 0})
    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found")
    new_active = not discount.get("active", True)
    await db.discounts.update_one({"id": discount_id}, {"$set": {"active": new_active}})
    return {"active": new_active}


# ── App Update Notifications ──

@router.get("/admin/app-update-settings")
async def get_app_update_settings(admin: dict = Depends(require_admin)):
    settings = await db.app_settings.find_one({"key": "app_update"}, {"_id": 0})
    return {"expo_url": settings.get("expo_url", "") if settings else "", "download_link": settings.get("download_link", "") if settings else ""}

@router.put("/admin/app-update-settings")
async def update_app_update_settings(data: dict, admin: dict = Depends(require_admin)):
    await db.app_settings.update_one({"key": "app_update"}, {"$set": {"key": "app_update", "expo_url": data.get("expo_url", ""), "download_link": data.get("download_link", "")}}, upsert=True)
    return {"message": "Settings saved"}

@router.get("/admin/qr-code")
async def get_qr_code(admin: dict = Depends(require_admin)):
    settings = await db.app_settings.find_one({"key": "app_update"}, {"_id": 0})
    url = (settings or {}).get("expo_url", "")
    if not url:
        raise HTTPException(status_code=400, detail="No Expo URL configured")
    return {"qr_base64": generate_qr_base64(url), "url": url}

@router.post("/admin/send-update-email")
async def send_update_email(data: SendUpdateEmail, admin: dict = Depends(require_admin)):
    if not RESEND_API_KEY:
        raise HTTPException(status_code=500, detail="Email service not configured")
    if data.send_to == "all":
        users = await db.users.find({}, {"_id": 0, "email": 1}).to_list(10000)
        recipients = [u["email"] for u in users if u.get("email")]
    else:
        recipients = [e.strip() for e in data.send_to.split(",") if e.strip()]
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients found")
    saved_settings = await db.app_settings.find_one({"key": "app_update"}, {"_id": 0}) or {}
    expo_url = data.expo_url or saved_settings.get("expo_url", "")
    download_link = data.download_link or data.expo_url or saved_settings.get("download_link", "") or expo_url
    qr_html = ""
    if expo_url:
        qr_b64 = generate_qr_base64(expo_url)
        qr_html = f'<div style="text-align:center;margin:20px 0;"><img src="data:image/png;base64,{qr_b64}" alt="QR Code" width="200" height="200" style="border:2px solid #333;border-radius:8px;" /></div>'
    link_html = ""
    if download_link:
        link_html = f'<div style="text-align:center;margin:20px 0;"><a href="{download_link}" style="display:inline-block;background:#4CAF50;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-size:16px;font-weight:bold;">Download Latest Version</a></div>'
    html_content = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#1a1a1a;color:#e0e0e0;padding:30px;border-radius:12px;">
        <div style="text-align:center;margin-bottom:20px;"><h1 style="color:#4CAF50;margin:0;">SMA Antenna Calc</h1><p style="color:#888;font-size:14px;">App Update Notification</p></div>
        <h2 style="color:#fff;font-size:18px;">{data.subject}</h2>
        <div style="line-height:1.6;font-size:15px;color:#ccc;">{data.message.replace(chr(10), '<br/>')}</div>
        {qr_html}{link_html}
        <div style="border-top:1px solid #333;margin-top:30px;padding-top:15px;text-align:center;font-size:12px;color:#666;"><p>Scan the QR code with your phone camera to install the latest version via Expo.</p></div>
    </div>"""
    import resend as resend_mod
    resend_mod.api_key = RESEND_API_KEY
    sent = 0
    errors = []
    for i in range(0, len(recipients), 50):
        batch = recipients[i:i+50]
        try:
            await asyncio.to_thread(resend_mod.Emails.send, {"from": SENDER_EMAIL, "to": batch, "subject": data.subject, "html": html_content})
            sent += len(batch)
        except Exception as e:
            errors.append(f"Batch {i//50+1}: {str(e)}")
    return {"sent": sent, "total": len(recipients), "errors": errors if errors else None, "message": f"Update email sent to {sent}/{len(recipients)} users"}

@router.get("/admin/user-emails")
async def get_user_emails(admin: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "email": 1, "id": 1, "subscription_tier": 1}).to_list(10000)
    return {"users": users}


# ── Changelog ──

@router.delete("/admin/changelog/{change_id}")
async def delete_changelog_entry(change_id: str, admin: dict = Depends(require_admin)):
    result = await db.changelog.delete_one({"id": change_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Deleted"}
