from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import hashlib
import jwt

from config import db, JWT_SECRET, JWT_ALGORITHM, ADMIN_EMAIL, SUBSCRIPTION_TIERS

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user = await db.users.find_one({"id": payload["user_id"]})
        return user
    except:
        return None

async def require_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("email", "").lower() != ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def check_subscription_active(user: dict) -> tuple:
    """Check if user has active subscription. Returns (is_active, tier_info, message)."""
    if not user:
        return False, None, "Not authenticated"

    if user.get("email", "").lower() == ADMIN_EMAIL.lower():
        return True, SUBSCRIPTION_TIERS["admin"], "Admin access"

    tier = user.get("subscription_tier", "trial")

    if tier == "trial":
        trial_started = user.get("trial_started")
        if trial_started:
            if isinstance(trial_started, str):
                trial_started = datetime.fromisoformat(trial_started.replace('Z', '+00:00'))
            elapsed = datetime.utcnow() - trial_started.replace(tzinfo=None)
            if elapsed > timedelta(hours=1):
                return False, SUBSCRIPTION_TIERS["trial"], "Trial expired"
        return True, SUBSCRIPTION_TIERS["trial"], "Trial active"

    expires = user.get("subscription_expires")
    if expires:
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
        if datetime.utcnow() > expires.replace(tzinfo=None):
            return False, SUBSCRIPTION_TIERS.get(tier), "Subscription expired - please renew"

    return True, SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["trial"]), "Active"
