"""E-commerce store endpoints: products, orders, checkout, APK, uploads."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime, timezone
from pathlib import Path
import uuid
import os
import jwt as pyjwt
import stripe
import httpx

from config import (
    store_db, JWT_SECRET, JWT_ALGORITHM, NC_TAX_RATE, SHIPPING_RATES,
    GITHUB_REPO, UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE,
)
from auth import security, hash_password, verify_password, create_token

router = APIRouter()


# ── Store Auth ──

async def require_store_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    member = await store_db.store_members.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not member or not member.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    return member


@router.post("/store/register")
async def store_register(data: dict):
    email = data.get("email", "").strip().lower()
    name = data.get("name", "").strip()
    password = data.get("password", "")
    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="All fields required")
    if await store_db.store_members.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    member_id = str(uuid.uuid4())
    member = {"id": member_id, "name": name, "email": email, "password_hash": hash_password(password), "is_admin": email == "fallstommy@gmail.com", "created_at": datetime.now(timezone.utc).isoformat()}
    await store_db.store_members.insert_one(member)
    token = create_token(member_id, email)
    return {"token": token, "user": {"id": member_id, "name": name, "email": email, "is_admin": member.get("is_admin", False)}}


@router.post("/store/login")
async def store_login(data: dict):
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    member = await store_db.store_members.find_one({"email": email}, {"_id": 0})
    if not member or not verify_password(password, member["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(member["id"], email)
    return {"token": token, "user": {"id": member["id"], "name": member["name"], "email": email, "is_admin": member.get("is_admin", False)}}


@router.get("/store/me")
async def store_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    member = await store_db.store_members.find_one({"id": payload["user_id"]}, {"_id": 0, "password_hash": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Not found")
    return member


# ── Products ──

@router.get("/store/products")
async def store_products():
    products = await store_db.store_products.find({}, {"_id": 0}).to_list(100)
    return products

@router.get("/store/products/{product_id}")
async def store_product(product_id: str):
    product = await store_db.store_products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/store/admin/products")
async def store_create_product(data: dict, admin: dict = Depends(require_store_admin)):
    product = {"id": str(uuid.uuid4()), "name": data.get("name", ""), "price": data.get("price", 0), "short_desc": data.get("short_desc", ""), "description": data.get("description", ""), "image_url": data.get("image_url", ""), "gallery": data.get("gallery", []), "in_stock": data.get("in_stock", True), "specs": data.get("specs", []), "created_at": datetime.now(timezone.utc).isoformat()}
    await store_db.store_products.insert_one(product)
    return {k: v for k, v in product.items() if k != "_id"}

@router.put("/store/admin/products/{product_id}")
async def store_update_product(product_id: str, data: dict, admin: dict = Depends(require_store_admin)):
    update = {k: v for k, v in data.items() if k not in ["id", "_id"]}
    result = await store_db.store_products.update_one({"id": product_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"status": "ok"}

@router.delete("/store/admin/products/{product_id}")
async def store_delete_product(product_id: str, admin: dict = Depends(require_store_admin)):
    result = await store_db.store_products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"status": "ok"}

@router.get("/store/admin/members")
async def store_list_members(admin: dict = Depends(require_store_admin)):
    members = await store_db.store_members.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return members


# ── APK / GitHub ──

@router.get("/store/latest-apk")
async def get_latest_apk():
    stored = await store_db.store_settings.find_one({"key": "apk_version"}, {"_id": 0})
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
            if resp.status_code != 200:
                if stored: return stored.get("value", {})
                return {"error": "No release found"}
            gh = resp.json()
            tag = gh.get("tag_name", "")
            assets = gh.get("assets", [])
            apk_asset = next((a for a in assets if a["name"].endswith(".apk")), None)
            if not apk_asset:
                if stored: return stored.get("value", {})
                return {"error": "No APK in latest release"}
            github_info = {"version": tag, "download_url": apk_asset["browser_download_url"], "filename": apk_asset["name"], "size_mb": round(apk_asset["size"] / (1024 * 1024), 1), "published_at": gh.get("published_at", ""), "release_name": gh.get("name", tag)}
            stored_version = stored.get("value", {}).get("version") if stored else None
            if stored_version != tag:
                await store_db.store_settings.update_one({"key": "apk_version"}, {"$set": {"key": "apk_version", "value": github_info}}, upsert=True)
                github_info["updated"] = True
            return github_info
    except Exception:
        if stored: return stored.get("value", {})
        return {"error": "Could not check GitHub"}


# ── Stripe Checkout ──

@router.post("/store/checkout")
async def store_checkout(data: dict, request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload["user_id"]
    user_email = payload.get("email", "")
    cart_items = data.get("items", [])
    origin_url = data.get("origin_url", "")
    if not cart_items or not origin_url:
        raise HTTPException(status_code=400, detail="Cart items and origin_url required")
    subtotal = 0.0
    order_items = []
    for ci in cart_items:
        product = await store_db.store_products.find_one({"id": ci["id"]}, {"_id": 0})
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {ci['id']} not found")
        if not product.get("in_stock"):
            raise HTTPException(status_code=400, detail=f"{product['name']} is sold out")
        qty = max(1, int(ci.get("qty", 1)))
        item_total = float(product["price"]) * qty
        subtotal += item_total
        order_items.append({"id": product["id"], "name": product["name"], "price": float(product["price"]), "qty": qty})
    tax = round(subtotal * NC_TAX_RATE, 2)
    shipping_method = data.get("shipping", "standard")
    if shipping_method not in SHIPPING_RATES: shipping_method = "standard"
    shipping = SHIPPING_RATES[shipping_method]
    grand_total = round(subtotal + tax + shipping, 2)
    stripe_key = os.environ.get("STRIPE_API_KEY", "")
    stripe.api_key = stripe_key
    success_url = f"{origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/cart"
    order_id = str(uuid.uuid4())
    line_items = []
    for item in order_items:
        line_items.append({"price_data": {"currency": "usd", "product_data": {"name": item["name"]}, "unit_amount": int(item["price"] * 100)}, "quantity": item["qty"]})
    if tax > 0:
        line_items.append({"price_data": {"currency": "usd", "product_data": {"name": "NC Sales Tax (7.5%)"}, "unit_amount": int(tax * 100)}, "quantity": 1})
    line_items.append({"price_data": {"currency": "usd", "product_data": {"name": f"Shipping ({shipping_method.title()})"}, "unit_amount": int(shipping * 100)}, "quantity": 1})
    session = stripe.checkout.Session.create(payment_method_types=["card"], line_items=line_items, mode="payment", success_url=success_url, cancel_url=cancel_url, customer_email=user_email, metadata={"order_id": order_id, "user_id": user_id, "email": user_email})
    transaction = {"id": order_id, "session_id": session.id, "user_id": user_id, "email": user_email, "items": order_items, "subtotal": subtotal, "tax": tax, "shipping": shipping, "shipping_method": shipping_method, "total": grand_total, "payment_status": "pending", "status": "initiated", "created_at": datetime.now(timezone.utc).isoformat()}
    await store_db.payment_transactions.insert_one(transaction)
    return {"url": session.url, "session_id": session.id, "order_id": order_id}


@router.get("/store/checkout/status/{session_id}")
async def store_checkout_status(session_id: str, request: Request):
    stripe_key = os.environ.get("STRIPE_API_KEY", "")
    stripe.api_key = stripe_key
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")
    payment_status = session.payment_status
    status = "complete" if payment_status == "paid" else "pending"
    txn = await store_db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if txn and txn.get("payment_status") != payment_status:
        await store_db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"payment_status": payment_status, "status": status, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"status": status, "payment_status": payment_status, "amount_total": session.amount_total / 100 if session.amount_total else 0, "currency": session.currency, "order_id": txn["id"] if txn else None}


# ── Orders ──

@router.get("/store/orders")
async def store_user_orders(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    orders = await store_db.payment_transactions.find({"user_id": payload["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return orders

@router.get("/store/admin/orders")
async def store_admin_orders(admin: dict = Depends(require_store_admin)):
    orders = await store_db.payment_transactions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return orders

@router.put("/store/admin/orders/{order_id}/status")
async def store_admin_update_order_status(order_id: str, data: dict, admin: dict = Depends(require_store_admin)):
    new_status = data.get("status")
    if new_status not in ["initiated", "processing", "shipped", "delivered", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    result = await store_db.payment_transactions.update_one({"id": order_id}, {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "ok"}


# ── Upload ──

@router.post("/store/admin/upload")
async def store_upload_image(file: UploadFile = File(...), admin: dict = Depends(require_store_admin)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 10 MB.")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        f.write(contents)
    return {"url": f"/api/uploads/{filename}", "filename": filename}


# ── Download Build ──

@router.get("/download-build")
async def download_build():
    zip_path = UPLOAD_DIR / "sma-website-build.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Build not found")
    return FileResponse(path=str(zip_path), filename="sma-website-build.zip", media_type="application/zip")


# ── Seed default products ──

async def seed_store_products():
    count = await store_db.store_products.count_documents({})
    if count == 0:
        defaults = [
            {"id": str(uuid.uuid4()), "name": "2-Pill Amplifier", "price": 450, "short_desc": "Compact 2-transistor amp for everyday use", "description": "Our entry-level 2-pill amplifier delivers solid power in a compact package.", "image_url": "https://images.unsplash.com/photo-1673023239309-ae54f5ef3b04?w=600", "in_stock": True, "specs": ["2 transistor pills", "Hand-built in NC", "Compact design", "Tested before shipping"], "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "name": "4-Pill Amplifier", "price": 650, "short_desc": "Mid-range 4-transistor powerhouse", "description": "The 4-pill is our most popular model.", "image_url": "https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=600", "in_stock": True, "specs": ["4 transistor pills", "Increased power output", "Quality components", "Hand-tested", "Heavy-duty build"], "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(uuid.uuid4()), "name": "6-Pill Amplifier", "price": 1050, "short_desc": "Premium 6-transistor beast for maximum power", "description": "Our flagship 6-pill amplifier is the ultimate in CB amplification.", "image_url": "https://images.unsplash.com/photo-1727036195443-d2ba0ad73311?w=600", "in_stock": True, "specs": ["6 transistor pills", "Maximum power output", "Premium components", "Professional grade", "Hand-built and tested", "Heavy-duty enclosure"], "created_at": datetime.now(timezone.utc).isoformat()},
        ]
        await store_db.store_products.insert_many(defaults)
