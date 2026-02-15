"""Public routes: root, bands, status, app-update, tutorial, designer-info, changelog, validate-discount."""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends

from config import db, BAND_DEFINITIONS
from models import StatusCheck, StatusCheckCreate, UpdateTutorialRequest
from auth import require_admin

router = APIRouter()

DEFAULT_TUTORIAL_CONTENT = """# Welcome to SMA Antenna Calculator!

## Getting Started
This app helps you design and analyze Yagi-Uda antennas for CB and Ham radio bands.

## 1. Choose Your Band
Select your operating band from the dropdown at the top.

## 2. Set Up Elements
- **Reflector**: Longest element, sits behind driven element.
- **Driven**: Connected to your feedline. Length determines resonance.
- **Directors**: Shorter elements in front that increase gain.

## 3. Auto-Tune
Hit Auto-Tune for optimal element lengths and spacing.

## 4. Optimize Height
Find the best mounting height for your setup.

## 5. Reading Results
- **Gain (dBi)**: Higher = stronger forward signal.
- **SWR**: Lower is better. Under 1.5:1 is excellent.
- **F/B Ratio**: Higher = less signal off the back.
- **Take-off Angle**: Lower = better for DX.

Happy DX'ing! 73"""

DEFAULT_DESIGNER_INFO = """# SMA Antenna Calculator
## Designed & Developed by Tommy Falls

With over 25 years of experience in CB and amateur radio.

### Contact & Support
- Email: fallstommy@gmail.com
- Built with pride for the amateur radio community

SMA Antenna Calculator v2.0 - 2026 Tommy Falls. All rights reserved.

73 & Good DX!"""


@router.get("/")
async def root():
    return {"message": "Antenna Calculator API"}


@router.get("/bands")
async def get_bands():
    return BAND_DEFINITIONS


@router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.dict())
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj


@router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**sc) for sc in status_checks]


# === APP UPDATE ===
@router.get("/app-update")
async def get_app_update():
    update_col = db["app_update"]
    doc = await update_col.find_one({}, {"_id": 0})
    if doc:
        return doc
    return {
        "version": "3.2.5",
        "buildDate": "2026-03-01T00:00:00",
        "releaseNotes": "Added 2x2 Quad Stacking, Wavelength Spacing Presets, Auto-Recalculate, Collinear Stacking Guidance, Far-Field Pattern Analysis, Wind Load Calculations, Changelog Viewer, Update System, 3-Way Boom Mount Selector, Corrected Cut List",
        "apkUrl": "https://expo.dev/artifacts/eas/fMxBwpXxnCqFhEqxvFH87W.apk",
        "forceUpdate": False
    }


@router.put("/app-update")
async def update_app_update(data: dict, admin=Depends(require_admin)):
    update_col = db["app_update"]
    update_data = {
        "version": data.get("version", ""), "buildDate": data.get("buildDate", ""),
        "releaseNotes": data.get("releaseNotes", ""), "apkUrl": data.get("apkUrl", ""),
        "forceUpdate": data.get("forceUpdate", False)
    }
    await update_col.delete_many({})
    await update_col.insert_one(update_data)
    return {"status": "ok", "data": {k: v for k, v in update_data.items() if k != "_id"}}


@router.post("/app-update")
async def set_app_update(data: dict):
    update_col = db["app_update"]
    await update_col.delete_many({})
    doc = {
        "version": data.get("version", ""), "buildDate": data.get("buildDate", ""),
        "releaseNotes": data.get("releaseNotes", ""), "apkUrl": data.get("apkUrl", ""),
        "forceUpdate": data.get("forceUpdate", False)
    }
    await update_col.insert_one(doc)
    return {"status": "ok"}


# === TUTORIAL ===
@router.get("/tutorial")
async def get_tutorial():
    tutorial = await db.app_settings.find_one({"key": "tutorial_content"}, {"_id": 0})
    if tutorial:
        return {"content": tutorial.get("content", DEFAULT_TUTORIAL_CONTENT)}
    return {"content": DEFAULT_TUTORIAL_CONTENT}


# === DESIGNER INFO ===
@router.get("/designer-info")
async def get_designer_info():
    info = await db.app_settings.find_one({"key": "designer_info"}, {"_id": 0})
    if info:
        return {"content": info.get("content", DEFAULT_DESIGNER_INFO)}
    return {"content": DEFAULT_DESIGNER_INFO}


# === CHANGELOG ===
@router.get("/changelog")
async def get_changelog():
    changes = await db.changelog.find({}, {"_id": 0}).sort("order", 1).to_list(1000)
    return {"changes": changes}


# === DISCOUNT VALIDATION (public) ===
@router.post("/validate-discount")
async def validate_discount(data: dict):
    from fastapi import HTTPException
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
