"""Public endpoints: bands, app-update, tutorial, designer-info, changelog, downloads, discounts."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime

from config import db, BAND_DEFINITIONS
from auth import security

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Antenna Calculator API"}


@router.get("/bands")
async def get_bands():
    return BAND_DEFINITIONS


# ── App Update ──

@router.get("/app-update")
async def get_app_update():
    update_col = db["app_update"]
    doc = await update_col.find_one({}, {"_id": 0})
    if doc:
        return doc
    return {"version": "4.1.5", "buildDate": "2026-02-22T00:00:00", "releaseNotes": "v4.1.5 - Realistic Gamma/Hairpin feed physics, interactive match sliders, real-time SWR tuning, resonant frequency display, auto-scaling performance bars", "apkUrl": "https://expo.dev/artifacts/eas/fMxBwpXxnCqFhEqxvFH87W.apk", "forceUpdate": False}


@router.put("/app-update")
async def update_app_update(data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    from auth import require_admin
    user = await require_admin(credentials)
    update_col = db["app_update"]
    update_data = {"version": data.get("version", ""), "buildDate": data.get("buildDate", ""), "releaseNotes": data.get("releaseNotes", ""), "apkUrl": data.get("apkUrl", ""), "forceUpdate": data.get("forceUpdate", False)}
    await update_col.delete_many({})
    await update_col.insert_one(update_data)
    return {"status": "ok", "data": {k: v for k, v in update_data.items() if k != "_id"}}


@router.post("/app-update")
async def set_app_update(data: dict):
    update_col = db["app_update"]
    await update_col.delete_many({})
    doc = {"version": data.get("version", ""), "buildDate": data.get("buildDate", ""), "releaseNotes": data.get("releaseNotes", ""), "apkUrl": data.get("apkUrl", ""), "forceUpdate": data.get("forceUpdate", False)}
    await update_col.insert_one(doc)
    return {"status": "ok"}


# ── Tutorial ──

@router.get("/tutorial")
async def get_tutorial():
    from config import DEFAULT_TUTORIAL_CONTENT
    tutorial = await db.app_settings.find_one({"key": "tutorial_content"}, {"_id": 0})
    if tutorial:
        return {"content": tutorial.get("content", DEFAULT_TUTORIAL_CONTENT)}
    return {"content": DEFAULT_TUTORIAL_CONTENT}


# ── Designer Info ──

@router.get("/designer-info")
async def get_designer_info():
    from config import DEFAULT_DESIGNER_INFO
    info = await db.app_settings.find_one({"key": "designer_info"}, {"_id": 0})
    if info:
        return {"content": info.get("content", DEFAULT_DESIGNER_INFO)}
    return {"content": DEFAULT_DESIGNER_INFO}


# ── Changelog ──

@router.get("/changelog")
async def get_changelog():
    changes = await db.changelog.find({}, {"_id": 0}).sort("order", 1).to_list(1000)
    return {"changes": changes}


# ── Downloads ──

@router.get("/download/store-site")
async def download_store_site():
    return FileResponse("/app/backend/sma-store-site.zip", filename="sma-store-site.zip", media_type="application/zip")

@router.get("/download/feature-graphic")
async def download_feature_graphic():
    return FileResponse("/app/backend/feature-graphic-1024x500.png", filename="feature-graphic-1024x500.png", media_type="image/png")

@router.get("/download/screenshot/{num}")
async def download_screenshot(num: int):
    return FileResponse(f"/app/backend/screenshot_{num}.png", filename=f"screenshot_{num}.png", media_type="image/png")

@router.get("/download/app-icon")
async def download_app_icon():
    return FileResponse("/app/backend/app-icon-512.png", filename="app-icon-512.png", media_type="image/png")

@router.get("/download/feature-graphic-jpg")
async def download_feature_graphic_jpg():
    return FileResponse("/app/backend/feature-graphic.jpg", filename="feature-graphic.jpg", media_type="image/jpeg")


# ── Discount Validation (public) ──

@router.post("/validate-discount")
async def validate_discount(data: dict):
    code = data.get("code", "").upper()
    tier = data.get("tier", "").lower()
    billing = data.get("billing", "monthly")
    user_email = data.get("email", "").lower()
    discount = await db.discounts.find_one({"code": code, "active": True}, {"_id": 0})
    if not discount:
        raise HTTPException(status_code=404, detail="Invalid discount code")
    if discount.get("expires_at"):
        if datetime.fromisoformat(discount["expires_at"]) < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Discount code has expired")
    if discount.get("max_uses") and discount["times_used"] >= discount["max_uses"]:
        raise HTTPException(status_code=400, detail="Discount code usage limit reached")
    if discount["user_emails"] and user_email not in discount["user_emails"]:
        raise HTTPException(status_code=403, detail="This discount is not available for your account")
    if tier and tier not in discount.get("tiers", []):
        raise HTTPException(status_code=400, detail=f"Discount not valid for {tier} tier")
    if discount["applies_to"] != "all" and discount["applies_to"] != billing:
        raise HTTPException(status_code=400, detail=f"Discount only valid for {discount['applies_to']} billing")
    await db.discounts.update_one({"code": code}, {"$inc": {"times_used": 1}})
    return {"valid": True, "discount_type": discount["discount_type"], "value": discount["value"], "code": discount["code"]}
