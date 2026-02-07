from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import math
import random
import hashlib
import secrets
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'antenna-calc-secret-key-2024')
JWT_ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

# Admin email for backdoor access (from environment variable)
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'fallstommy@gmail.com')

# Default Subscription Tiers Configuration (can be overridden from DB)
DEFAULT_SUBSCRIPTION_TIERS = {
    "trial": {
        "name": "Free Trial",
        "price": 0,
        "max_elements": 3,
        "duration_hours": 1,
        "features": ["basic_calc", "swr_meter"],
        "description": "1 hour free trial with basic features"
    },
    "bronze_monthly": {
        "name": "Bronze Monthly",
        "price": 39.99,
        "max_elements": 5,
        "duration_days": 30,
        "features": ["basic_calc", "swr_meter", "band_selection"],
        "description": "$39.99/month - Basic antenna calculations"
    },
    "bronze_yearly": {
        "name": "Bronze Yearly",
        "price": 400.00,
        "max_elements": 5,
        "duration_days": 365,
        "features": ["basic_calc", "swr_meter", "band_selection"],
        "description": "$400/year - Basic antenna calculations (Save $80!)"
    },
    "silver_monthly": {
        "name": "Silver Monthly",
        "price": 59.99,
        "max_elements": 10,
        "duration_days": 30,
        "features": ["basic_calc", "swr_meter", "band_selection", "auto_tune", "save_designs"],
        "description": "$59.99/month - Auto-tune & save designs"
    },
    "silver_yearly": {
        "name": "Silver Yearly",
        "price": 675.00,
        "max_elements": 10,
        "duration_days": 365,
        "features": ["basic_calc", "swr_meter", "band_selection", "auto_tune", "save_designs"],
        "description": "$675/year - Auto-tune & save designs (Save $45!)"
    },
    "gold_monthly": {
        "name": "Gold Monthly",
        "price": 99.99,
        "max_elements": 20,
        "duration_days": 30,
        "features": ["all"],
        "description": "$99.99/month - All features"
    },
    "gold_yearly": {
        "name": "Gold Yearly",
        "price": 1050.00,
        "max_elements": 20,
        "duration_days": 365,
        "features": ["all"],
        "description": "$1050/year - All features (Save $150!)"
    },
    "subadmin": {
        "name": "Sub-Admin",
        "price": 0,
        "max_elements": 20,
        "duration_days": 36500,
        "features": ["all"],
        "description": "Sub-Admin full access"
    },
    "admin": {
        "name": "Admin",
        "price": 0,
        "max_elements": 20,
        "duration_days": 36500,
        "features": ["all"],
        "description": "Admin full access"
    }
}

# In-memory cache for tiers (loaded from DB on startup)
SUBSCRIPTION_TIERS = DEFAULT_SUBSCRIPTION_TIERS.copy()

# Default Payment Configuration
DEFAULT_PAYMENT_CONFIG = {
    "paypal": {
        "email": "tfcp2011@gmail.com",
        "enabled": True
    },
    "cashapp": {
        "tag": "$tfcp2011",
        "enabled": True
    }
}

# In-memory cache for payment config (loaded from DB on startup)
PAYMENT_CONFIG = DEFAULT_PAYMENT_CONFIG.copy()


# ==================== ADMIN MODELS ====================
class PricingUpdate(BaseModel):
    bronze_monthly_price: float = 39.99
    bronze_yearly_price: float = 400.00
    bronze_max_elements: int = 5
    bronze_features: list = ["basic_calc", "swr_meter", "band_selection"]
    silver_monthly_price: float = 59.99
    silver_yearly_price: float = 675.00
    silver_max_elements: int = 10
    silver_features: list = ["basic_calc", "swr_meter", "band_selection", "auto_tune", "save_designs"]
    gold_monthly_price: float = 99.99
    gold_yearly_price: float = 1050.00
    gold_max_elements: int = 20
    gold_features: list = ["all"]

class PaymentConfigUpdate(BaseModel):
    paypal_email: str
    cashapp_tag: str

class UserRoleUpdate(BaseModel):
    role: str  # 'trial', 'bronze_monthly', 'bronze_yearly', 'silver_monthly', 'silver_yearly', 'gold_monthly', 'gold_yearly', 'subadmin'


# ==================== HELPER FUNCTIONS ====================
async def load_settings_from_db():
    """Load pricing and payment settings from database"""
    global SUBSCRIPTION_TIERS, PAYMENT_CONFIG
    
    settings = await db.settings.find_one({"type": "pricing"})
    if settings:
        # Load monthly tiers
        if "bronze_monthly" in SUBSCRIPTION_TIERS:
            SUBSCRIPTION_TIERS["bronze_monthly"]["price"] = settings.get("bronze_monthly_price", 39.99)
            SUBSCRIPTION_TIERS["bronze_monthly"]["max_elements"] = settings.get("bronze_max_elements", 5)
            SUBSCRIPTION_TIERS["bronze_monthly"]["features"] = settings.get("bronze_features", ["basic_calc", "swr_meter", "band_selection"])
            SUBSCRIPTION_TIERS["bronze_yearly"]["price"] = settings.get("bronze_yearly_price", 400.00)
            SUBSCRIPTION_TIERS["bronze_yearly"]["max_elements"] = settings.get("bronze_max_elements", 5)
            SUBSCRIPTION_TIERS["bronze_yearly"]["features"] = settings.get("bronze_features", ["basic_calc", "swr_meter", "band_selection"])
            
            SUBSCRIPTION_TIERS["silver_monthly"]["price"] = settings.get("silver_monthly_price", 59.99)
            SUBSCRIPTION_TIERS["silver_monthly"]["max_elements"] = settings.get("silver_max_elements", 10)
            SUBSCRIPTION_TIERS["silver_monthly"]["features"] = settings.get("silver_features", ["basic_calc", "swr_meter", "band_selection", "auto_tune", "save_designs"])
            SUBSCRIPTION_TIERS["silver_yearly"]["price"] = settings.get("silver_yearly_price", 675.00)
            SUBSCRIPTION_TIERS["silver_yearly"]["max_elements"] = settings.get("silver_max_elements", 10)
            SUBSCRIPTION_TIERS["silver_yearly"]["features"] = settings.get("silver_features", ["basic_calc", "swr_meter", "band_selection", "auto_tune", "save_designs"])
            
            SUBSCRIPTION_TIERS["gold_monthly"]["price"] = settings.get("gold_monthly_price", 99.99)
            SUBSCRIPTION_TIERS["gold_monthly"]["max_elements"] = settings.get("gold_max_elements", 20)
            SUBSCRIPTION_TIERS["gold_monthly"]["features"] = settings.get("gold_features", ["all"])
            SUBSCRIPTION_TIERS["gold_yearly"]["price"] = settings.get("gold_yearly_price", 1050.00)
            SUBSCRIPTION_TIERS["gold_yearly"]["max_elements"] = settings.get("gold_max_elements", 20)
            SUBSCRIPTION_TIERS["gold_yearly"]["features"] = settings.get("gold_features", ["all"])
        else:
            # Legacy format
            SUBSCRIPTION_TIERS["bronze"]["price"] = settings.get("bronze_price", 29.99)
            SUBSCRIPTION_TIERS["bronze"]["max_elements"] = settings.get("bronze_max_elements", 3)
            SUBSCRIPTION_TIERS["silver"]["price"] = settings.get("silver_price", 49.99)
            SUBSCRIPTION_TIERS["silver"]["max_elements"] = settings.get("silver_max_elements", 7)
            SUBSCRIPTION_TIERS["gold"]["price"] = settings.get("gold_price", 69.99)
            SUBSCRIPTION_TIERS["gold"]["max_elements"] = settings.get("gold_max_elements", 20)
    
    payment_settings = await db.settings.find_one({"type": "payment"})
    if payment_settings:
        PAYMENT_CONFIG["paypal"]["email"] = payment_settings.get("paypal_email", "tfcp2011@gmail.com")
        PAYMENT_CONFIG["cashapp"]["tag"] = payment_settings.get("cashapp_tag", "$tfcp2011")

async def is_admin(user: dict) -> bool:
    """Check if user is main admin"""
    return user and user.get("email", "").lower() == ADMIN_EMAIL.lower()

async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Require main admin access"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("email", "").lower() != ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ==================== USER MODELS ====================
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=2)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    subscription_tier: str
    subscription_expires: Optional[datetime]
    is_trial: bool
    trial_started: Optional[datetime]
    created_at: datetime

class SubscriptionUpdate(BaseModel):
    tier: str
    payment_method: str
    payment_reference: Optional[str] = None

class PaymentRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float
    tier: str
    payment_method: str
    payment_reference: Optional[str]
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== AUTH HELPERS ====================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=7)
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

def check_subscription_active(user: dict) -> tuple:
    """Check if user has active subscription. Returns (is_active, tier_info, message)"""
    if not user:
        return False, None, "Not authenticated"
    
    # Admin backdoor
    if user.get("email", "").lower() == ADMIN_EMAIL.lower():
        return True, SUBSCRIPTION_TIERS["admin"], "Admin access"
    
    tier = user.get("subscription_tier", "trial")
    
    # Check trial
    if tier == "trial":
        trial_started = user.get("trial_started")
        if trial_started:
            if isinstance(trial_started, str):
                trial_started = datetime.fromisoformat(trial_started.replace('Z', '+00:00'))
            elapsed = datetime.utcnow() - trial_started.replace(tzinfo=None)
            if elapsed > timedelta(hours=1):
                return False, SUBSCRIPTION_TIERS["trial"], "Trial expired"
        return True, SUBSCRIPTION_TIERS["trial"], "Trial active"
    
    # Check paid subscription
    expires = user.get("subscription_expires")
    if expires:
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
        if datetime.utcnow() > expires.replace(tzinfo=None):
            # Subscription expired - downgrade to free (not trial)
            return False, SUBSCRIPTION_TIERS.get(tier), "Subscription expired - please renew"
    
    return True, SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["trial"]), "Active"


class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str


BAND_DEFINITIONS = {
    "11m_cb": {"name": "11m CB Band", "center": 27.185, "start": 26.965, "end": 27.405, "channel_spacing_khz": 10},
    "10m": {"name": "10m Ham Band", "center": 28.5, "start": 28.0, "end": 29.7, "channel_spacing_khz": 10},
    "12m": {"name": "12m Ham Band", "center": 24.94, "start": 24.89, "end": 24.99, "channel_spacing_khz": 5},
    "15m": {"name": "15m Ham Band", "center": 21.225, "start": 21.0, "end": 21.45, "channel_spacing_khz": 5},
    "17m": {"name": "17m Ham Band", "center": 18.118, "start": 18.068, "end": 18.168, "channel_spacing_khz": 5},
    "20m": {"name": "20m Ham Band", "center": 14.175, "start": 14.0, "end": 14.35, "channel_spacing_khz": 5},
    "40m": {"name": "40m Ham Band", "center": 7.15, "start": 7.0, "end": 7.3, "channel_spacing_khz": 5},
    "6m": {"name": "6m Ham Band", "center": 51.0, "start": 50.0, "end": 54.0, "channel_spacing_khz": 20},
    "2m": {"name": "2m Ham Band", "center": 146.0, "start": 144.0, "end": 148.0, "channel_spacing_khz": 20},
    "70cm": {"name": "70cm Ham Band", "center": 435.0, "start": 420.0, "end": 450.0, "channel_spacing_khz": 25},
}

# === FREE-SPACE GAIN MODEL (dBi) ===
# Based on real-world Yagi engineering data at 27 MHz (11m band).
# Doubling boom length yields ~2.5-3 dB gain increase.
# These values assume standard boom lengths from STANDARD_BOOM_11M_IN.
FREE_SPACE_GAIN_DBI = {
    2: 6.2,      # 6.0-6.5 dBi
    3: 8.2,      # 8.0-8.5 dBi
    4: 10.0,     # 10.0-11.5 range (4-5 elements)
    5: 10.8,
    6: 12.0,     # 12.0-13.5 range (6-8 elements)
    7: 12.5,
    8: 13.0,
    9: 13.5,
    10: 14.0,    # 14.0-15.0 range (10-12 elements)
    11: 14.3,
    12: 15.0,
    13: 15.3,
    14: 15.6,
    15: 16.0,    # 16.0-17.5 range (15-20 elements)
    16: 16.3,
    17: 16.5,
    18: 16.8,
    19: 17.0,
    20: 17.2,
}

# Standard boom lengths (inches) at 11m (27.185 MHz) for gain calibration.
# Based on real-world optimized Yagi designs at 27 MHz.
# These are also used by auto-tune; moved here for shared access.
STANDARD_BOOM_11M_IN = {
    2: 47,      # ~1.2m
    3: 138,     # ~3.5m
    4: 217,     # ~5.5m
    5: 295,     # ~7.5m
    6: 394,     # ~10.0m
    7: 472,     # ~12.0m (interpolated)
    8: 551,     # ~14.0m
    9: 640,     # ~16.25m (interpolated)
    10: 728,    # ~18.5m
    11: 827,    # ~21.0m (interpolated)
    12: 925,    # ~23.5m
    13: 1024,   # ~26.0m (interpolated)
    14: 1122,   # ~28.5m (interpolated)
    15: 1221,   # ~31.0m
    16: 1323,   # ~33.6m (interpolated)
    17: 1425,   # ~36.2m (interpolated)
    18: 1528,   # ~38.8m (interpolated)
    19: 1630,   # ~41.4m (interpolated)
    20: 1732,   # ~44.0m
}
REF_WAVELENGTH_11M_IN = 434.2  # 11m at 27.185 MHz in inches


def get_free_space_gain(n: int) -> float:
    """Get free-space gain for n elements, interpolating/extrapolating if needed."""
    if n in FREE_SPACE_GAIN_DBI:
        return FREE_SPACE_GAIN_DBI[n]
    if n < 2:
        return 4.0
    if n > 20:
        # Extrapolate: ~0.3 dBi per additional element beyond 20 (diminishing returns)
        return 17.2 + 0.3 * (n - 20)
    # Interpolate between known values
    lower = max(k for k in FREE_SPACE_GAIN_DBI if k <= n)
    upper = min(k for k in FREE_SPACE_GAIN_DBI if k >= n)
    if lower == upper:
        return FREE_SPACE_GAIN_DBI[lower]
    frac = (n - lower) / (upper - lower)
    return round(FREE_SPACE_GAIN_DBI[lower] + frac * (FREE_SPACE_GAIN_DBI[upper] - FREE_SPACE_GAIN_DBI[lower]), 2)


def get_standard_boom_in(n: int, wavelength_in: float) -> float:
    """Get standard boom length in inches for n elements, scaled for frequency."""
    scale = wavelength_in / REF_WAVELENGTH_11M_IN
    base = STANDARD_BOOM_11M_IN.get(n, 150 + (n - 3) * 60)
    return base * scale


def calculate_ground_gain(height_wavelengths: float) -> float:
    """Calculate ground reflection gain (dBi) for horizontal Yagi over average soil.
    At 1λ height: ~5.8 dBi. Formula: G_real = G_free_space + G_ground."""
    h = height_wavelengths
    if h <= 0:
        return 0.0
    if h < 0.25:
        return round(h * 8.0, 2)           # 0 → 2.0 dBi
    if h < 0.5:
        return round(2.0 + (h - 0.25) * 8.0, 2)   # 2.0 → 4.0
    if h < 0.75:
        return round(4.0 + (h - 0.5) * 4.0, 2)    # 4.0 → 5.0
    if h < 1.0:
        return round(5.0 + (h - 0.75) * 3.2, 2)   # 5.0 → 5.8
    if h <= 1.5:
        return round(5.8 + (h - 1.0) * 0.4, 2)    # 5.8 → 6.0
    if h <= 2.0:
        return round(6.0 - (h - 1.5) * 1.0, 2)    # 6.0 → 5.5
    return round(max(4.0, 5.5 - (h - 2.0) * 0.5), 2)  # gradual decrease


class TaperSection(BaseModel):
    length: float = Field(..., gt=0)
    start_diameter: float = Field(..., gt=0)
    end_diameter: float = Field(..., gt=0)

class TaperConfig(BaseModel):
    enabled: bool = Field(default=False)
    num_tapers: int = Field(default=2, ge=1, le=5)
    sections: List[TaperSection] = Field(default=[])

class CoronaBallConfig(BaseModel):
    enabled: bool = Field(default=False)
    diameter: float = Field(default=1.0, gt=0)

class ElementDimension(BaseModel):
    element_type: str
    length: float = Field(..., gt=0)
    diameter: float = Field(..., gt=0)
    position: float = Field(default=0, ge=0)

class StackingConfig(BaseModel):
    enabled: bool = Field(default=False)
    orientation: str = Field(default="vertical")
    num_antennas: int = Field(default=2, ge=2, le=8)
    spacing: float = Field(default=20, gt=0)
    spacing_unit: str = Field(default="ft")

class GroundRadialConfig(BaseModel):
    enabled: bool = Field(default=False)
    ground_type: str = Field(default="average")  # wet, dry, average
    wire_diameter: float = Field(default=0.5)  # inches
    num_radials: int = Field(default=8)  # 8 directions: N, S, E, W, NE, NW, SE, SW

class AntennaInput(BaseModel):
    num_elements: int = Field(..., ge=2, le=20)
    elements: List[ElementDimension] = Field(...)
    height_from_ground: float = Field(..., gt=0)
    height_unit: str = Field(default="ft")
    boom_diameter: float = Field(..., gt=0)
    boom_unit: str = Field(default="inches")
    band: str = Field(default="11m_cb")
    frequency_mhz: Optional[float] = Field(default=None)
    stacking: Optional[StackingConfig] = Field(default=None)
    taper: Optional[TaperConfig] = Field(default=None)
    corona_balls: Optional[CoronaBallConfig] = Field(default=None)
    ground_radials: Optional[GroundRadialConfig] = Field(default=None)

class AutoTuneRequest(BaseModel):
    num_elements: int = Field(..., ge=2, le=20)
    height_from_ground: float = Field(..., gt=0)
    height_unit: str = Field(default="ft")
    boom_diameter: float = Field(..., gt=0)
    boom_unit: str = Field(default="inches")
    band: str = Field(default="11m_cb")
    frequency_mhz: Optional[float] = Field(default=None)
    taper: Optional[TaperConfig] = Field(default=None)
    corona_balls: Optional[CoronaBallConfig] = Field(default=None)
    use_reflector: bool = Field(default=True)  # Added to support no-reflector mode
    # Boom and Spacing Lock options
    boom_lock_enabled: bool = Field(default=False)
    max_boom_length: Optional[float] = Field(default=None)  # Max boom length in inches
    spacing_lock_enabled: bool = Field(default=False)
    locked_positions: Optional[List[float]] = Field(default=None)  # Positions to preserve when spacing lock is on
    # Element spacing mode
    spacing_mode: str = Field(default="normal")  # normal, tight, long
    spacing_level: float = Field(default=1.0)  # Spacing multiplier

class AntennaOutput(BaseModel):
    swr: float
    swr_description: str
    fb_ratio: float
    fb_ratio_description: str
    fs_ratio: float
    fs_ratio_description: str
    beamwidth_h: float
    beamwidth_v: float
    beamwidth_description: str
    bandwidth: float
    bandwidth_description: str
    gain_dbi: float
    gain_description: str
    base_gain_dbi: Optional[float] = None
    gain_breakdown: Optional[dict] = None
    multiplication_factor: float
    multiplication_description: str
    antenna_efficiency: float
    efficiency_description: str
    far_field_pattern: List[dict]
    swr_curve: List[dict]
    usable_bandwidth_1_5: float
    usable_bandwidth_2_0: float
    center_frequency: float
    band_info: dict
    input_summary: dict
    stacking_enabled: bool
    stacking_info: Optional[dict] = None
    stacked_gain_dbi: Optional[float] = None
    stacked_pattern: Optional[List[dict]] = None
    taper_info: Optional[dict] = None
    corona_info: Optional[dict] = None
    # Reflected power data
    reflection_coefficient: Optional[float] = None
    return_loss_db: Optional[float] = None
    mismatch_loss_db: Optional[float] = None
    reflected_power_100w: Optional[float] = None
    reflected_power_1kw: Optional[float] = None
    forward_power_100w: Optional[float] = None
    forward_power_1kw: Optional[float] = None
    impedance_high: Optional[float] = None
    impedance_low: Optional[float] = None
    # Take-off angle and ground radials
    takeoff_angle: Optional[float] = None
    takeoff_angle_description: Optional[str] = None
    ground_radials_info: Optional[dict] = None

class AutoTuneOutput(BaseModel):
    optimized_elements: List[dict]
    predicted_swr: float
    predicted_gain: float
    predicted_fb_ratio: float
    optimization_notes: List[str]

class CalculationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    inputs: dict
    outputs: dict


def convert_height_to_meters(value: float, unit: str) -> float:
    if unit == "ft": return value * 0.3048
    elif unit == "inches": return value * 0.0254
    return value

def convert_boom_to_meters(value: float, unit: str) -> float:
    if unit == "mm": return value * 0.001
    elif unit == "inches": return value * 0.0254
    return value

def convert_element_to_meters(value: float, unit: str) -> float:
    if unit == "inches": return value * 0.0254
    return value

def convert_spacing_to_meters(value: float, unit: str) -> float:
    if unit == "ft": return value * 0.3048
    elif unit == "inches": return value * 0.0254
    return value


def calculate_swr_from_elements(elements: List[ElementDimension], wavelength: float, taper_enabled: bool = False, height_wavelengths: float = 1.0) -> float:
    """Calculate SWR based on element dimensions relative to wavelength and height."""
    driven = None
    reflector = None
    directors = []
    
    for elem in elements:
        if elem.element_type == "driven":
            driven = elem
        elif elem.element_type == "reflector":
            reflector = elem
        elif elem.element_type == "director":
            directors.append(elem)
    
    if not driven:
        return 2.0
    
    # Convert driven element length to meters
    driven_length_m = convert_element_to_meters(driven.length, "inches")
    
    # Ideal driven element is ~0.47-0.48 wavelength (accounting for end effects)
    ideal_driven = wavelength * 0.473
    
    # Calculate deviation from ideal
    deviation = abs(driven_length_m - ideal_driven) / ideal_driven
    
    # Base SWR calculation - more realistic curve
    if deviation < 0.005:  # Within 0.5%
        base_swr = 1.0 + (deviation * 10)  # 1.0 to 1.05
    elif deviation < 0.01:  # Within 1%
        base_swr = 1.05 + (deviation - 0.005) * 20  # 1.05 to 1.15
    elif deviation < 0.02:  # Within 2%
        base_swr = 1.15 + (deviation - 0.01) * 25  # 1.15 to 1.4
    elif deviation < 0.04:  # Within 4%
        base_swr = 1.4 + (deviation - 0.02) * 30  # 1.4 to 2.0
    elif deviation < 0.08:  # Within 8%
        base_swr = 2.0 + (deviation - 0.04) * 25  # 2.0 to 3.0
    else:
        base_swr = 3.0 + (deviation - 0.08) * 20  # Above 3.0
    
    # Reflector length affects SWR (should be ~5% longer than driven)
    if reflector:
        reflector_length_m = convert_element_to_meters(reflector.length, "inches")
        ideal_reflector = driven_length_m * 1.05
        reflector_deviation = abs(reflector_length_m - ideal_reflector) / ideal_reflector
        base_swr *= (1 + reflector_deviation * 0.5)
    
    # Directors affect SWR (should be progressively shorter)
    if directors:
        for i, director in enumerate(directors):
            director_length_m = convert_element_to_meters(director.length, "inches")
            # Each director should be about 3-5% shorter than the previous
            ideal_director = driven_length_m * (0.95 - i * 0.02)
            director_deviation = abs(director_length_m - ideal_director) / ideal_director
            base_swr *= (1 + director_deviation * 0.2)
    
    # Element spacing affects SWR
    if reflector and driven:
        spacing = abs(driven.position - reflector.position)
        spacing_m = convert_element_to_meters(spacing, "inches")
        ideal_spacing = wavelength * 0.2  # ~0.2 wavelength for reflector-driven
        spacing_deviation = abs(spacing_m - ideal_spacing) / ideal_spacing
        base_swr *= (1 + spacing_deviation * 0.3)
    
    # HEIGHT EFFECT ON SWR - Ground reflection affects feedpoint impedance
    # Optimal heights are at 0.5, 1.0, 1.5 wavelengths (half-wave multiples)
    # Worst heights are at 0.25, 0.75, 1.25 wavelengths (quarter-wave multiples)
    height_factor = 1.0
    # Calculate how close we are to an optimal (half-wave) height
    fractional_height = height_wavelengths % 0.5
    distance_from_optimal = min(fractional_height, 0.5 - fractional_height)
    
    # At optimal heights (0.5, 1.0, 1.5λ), SWR improves
    # At worst heights (0.25, 0.75λ), SWR degrades
    if distance_from_optimal < 0.1:  # Near optimal height
        height_factor = 0.90 + (distance_from_optimal * 1.0)  # 0.90 to 1.0
    elif distance_from_optimal < 0.2:  # Moderately good
        height_factor = 1.0 + (distance_from_optimal - 0.1) * 1.5  # 1.0 to 1.15
    else:  # Near quarter-wave heights (worst)
        height_factor = 1.15 + (distance_from_optimal - 0.2) * 1.0  # 1.15 to 1.25
    
    # Very low heights (< 0.25λ) are always bad for SWR
    if height_wavelengths < 0.25:
        height_factor *= 1.3 + (0.25 - height_wavelengths) * 2
    
    base_swr *= height_factor
    
    # Taper helps SWR
    if taper_enabled:
        base_swr *= 0.92
    
    return round(max(1.0, min(base_swr, 5.0)), 2)


def calculate_swr_at_frequency(freq: float, center_freq: float, bandwidth: float, min_swr: float = 1.0) -> float:
    freq_offset = abs(freq - center_freq)
    half_bandwidth = bandwidth / 2
    if freq_offset == 0:
        return min_swr
    normalized_offset = freq_offset / half_bandwidth if half_bandwidth > 0 else 0
    swr = min_swr + (normalized_offset ** 1.6) * (4.0 - min_swr)
    return min(swr, 10.0)


def calculate_taper_effects(taper: TaperConfig, num_elements: int) -> dict:
    if not taper or not taper.enabled:
        return {"gain_bonus": 0, "bandwidth_mult": 1.0, "swr_mult": 1.0, "fb_bonus": 0, "fs_bonus": 0}
    
    num_tapers = taper.num_tapers
    sections = taper.sections
    
    # Base effects from number of taper steps
    # More taper steps = smoother impedance transition = better performance
    base_gain_bonus = 0.15 * num_tapers
    bandwidth_mult = 1.0 + (0.08 * num_tapers)
    swr_mult = 1.0 - (0.02 * num_tapers)
    fb_bonus = 0.8 * num_tapers
    fs_bonus = 0.5 * num_tapers
    
    if sections:
        total_taper_ratio = 0
        max_start_dia = 0
        min_end_dia = 999
        
        for section in sections:
            if section.start_diameter > 0:
                ratio = section.end_diameter / section.start_diameter
                total_taper_ratio += (1 - ratio)
                max_start_dia = max(max_start_dia, section.start_diameter)
                min_end_dia = min(min_end_dia, section.end_diameter)
        
        avg_taper = total_taper_ratio / len(sections) if sections else 0
        
        # Larger diameter center elements (1.25"+) give structural strength bonus
        if max_start_dia >= 1.0:
            base_gain_bonus += 0.2
            bandwidth_mult += 0.05
        
        # Good taper ratio (gradual reduction) improves impedance matching
        if 0.2 <= avg_taper <= 0.7:
            # Sweet spot - smooth taper transition
            taper_quality = 1.0 - abs(avg_taper - 0.45) / 0.45  # Peak at 0.45 ratio
            base_gain_bonus += 0.4 * taper_quality * num_tapers
            bandwidth_mult += 0.12 * taper_quality * num_tapers
            swr_mult -= 0.03 * taper_quality * num_tapers
            fb_bonus += 1.5 * taper_quality * num_tapers
        
        # Overall diameter reduction (from largest center to smallest tip)
        if max_start_dia > 0 and min_end_dia < max_start_dia:
            overall_ratio = min_end_dia / max_start_dia
            if 0.3 <= overall_ratio <= 0.6:
                # Ideal overall taper (e.g., 1.25" to 0.5" = 0.4 ratio)
                base_gain_bonus += 0.3
                bandwidth_mult += 0.08
    
    # Scale effects by number of elements (more elements = more impact from taper)
    element_scale = min(1.5, num_elements / 3.0)
    
    return {
        "gain_bonus": round(base_gain_bonus * element_scale, 2),
        "bandwidth_mult": round(bandwidth_mult, 2),
        "swr_mult": round(max(0.7, swr_mult), 2),
        "fb_bonus": round(fb_bonus * element_scale, 1),
        "fs_bonus": round(fs_bonus * element_scale, 1),
        "num_tapers": num_tapers,
        "sections": [s.dict() for s in sections] if sections else []
    }


def calculate_corona_effects(corona: CoronaBallConfig) -> dict:
    if not corona or not corona.enabled:
        return {"enabled": False, "gain_effect": 0, "bandwidth_effect": 1.0, "corona_reduction": 0}
    diameter = corona.diameter
    gain_effect = -0.1 if diameter > 1.5 else 0
    bandwidth_effect = 1.02
    corona_reduction = min(90, 50 + diameter * 20)
    return {
        "enabled": True,
        "diameter": diameter,
        "gain_effect": gain_effect,
        "bandwidth_effect": bandwidth_effect,
        "corona_reduction": round(corona_reduction, 0),
        "description": f"{corona_reduction:.0f}% corona discharge reduction"
    }


def calculate_stacking_gain(base_gain: float, num_antennas: int, spacing_wavelengths: float, orientation: str) -> tuple:
    theoretical_gain = 10 * math.log10(num_antennas)
    if 0.5 <= spacing_wavelengths <= 1.0:
        efficiency = 0.95 if 0.6 <= spacing_wavelengths <= 0.8 else 0.88
    elif spacing_wavelengths < 0.5:
        efficiency = 0.6 + (spacing_wavelengths / 0.5) * 0.28
    else:
        efficiency = 0.82
    actual_gain_increase = theoretical_gain * efficiency
    stacked_gain = base_gain + actual_gain_increase
    return round(stacked_gain, 2), round(actual_gain_increase, 2)


def calculate_stacked_beamwidth(base_beamwidth: float, num_antennas: int, spacing_wavelengths: float) -> float:
    narrowing_factor = math.sqrt(num_antennas)
    if spacing_wavelengths < 0.5:
        narrowing_factor *= 0.7
    elif spacing_wavelengths > 1.0:
        narrowing_factor *= 0.9
    return round(max(base_beamwidth / narrowing_factor, 15), 1)


def generate_stacked_pattern(base_pattern: List[dict], num_antennas: int, spacing_wavelengths: float, orientation: str) -> List[dict]:
    stacked_pattern = []
    for point in base_pattern:
        angle = point["angle"]
        base_mag = point["magnitude"]
        theta_rad = math.radians(angle)
        if orientation == "vertical":
            array_factor = 1.0
            if 60 < angle < 120 or 240 < angle < 300:
                array_factor = 0.7 + 0.3 * abs(math.sin(num_antennas * math.pi * spacing_wavelengths * math.sin(theta_rad)))
        else:
            psi = 2 * math.pi * spacing_wavelengths * math.cos(theta_rad)
            array_factor = 1.0 if abs(math.sin(psi / 2)) < 0.001 else abs(math.sin(num_antennas * psi / 2) / (num_antennas * math.sin(psi / 2)))
        stacked_pattern.append({"angle": angle, "magnitude": round(max(base_mag * array_factor, 1), 1)})
    max_mag = max(p["magnitude"] for p in stacked_pattern)
    if max_mag > 0:
        for p in stacked_pattern:
            p["magnitude"] = round(p["magnitude"] / max_mag * 100, 1)
    return stacked_pattern


def calculate_antenna_parameters(input_data: AntennaInput) -> AntennaOutput:
    band_info = BAND_DEFINITIONS.get(input_data.band, BAND_DEFINITIONS["11m_cb"])
    center_freq = input_data.frequency_mhz if input_data.frequency_mhz else band_info["center"]
    channel_spacing = band_info.get("channel_spacing_khz", 10) / 1000
    
    height_m = convert_height_to_meters(input_data.height_from_ground, input_data.height_unit)
    boom_dia_m = convert_boom_to_meters(input_data.boom_diameter, input_data.boom_unit)
    
    c = 299792458
    wavelength = c / (center_freq * 1e6)
    
    n = input_data.num_elements
    height_wavelengths = height_m / wavelength
    
    taper_effects = calculate_taper_effects(input_data.taper, n)
    corona_effects = calculate_corona_effects(input_data.corona_balls)
    taper_enabled = input_data.taper.enabled if input_data.taper else False
    
    avg_element_dia = sum(convert_element_to_meters(e.diameter, "inches") for e in input_data.elements) / len(input_data.elements)
    
    # Check if antenna has a reflector
    has_reflector = any(e.element_type == "reflector" for e in input_data.elements)
    
    # === GAIN CALCULATION ===
    # Lookup-based model calibrated to real-world Yagi engineering data.
    # Free-space gain is keyed by element count at standard boom lengths.
    # If actual boom differs from standard, adjust by ~2.5 dB per boom doubling.
    
    # Calculate boom length from element positions
    positions = sorted([e.position for e in input_data.elements])
    boom_length_in = max(positions) - min(positions) if len(positions) > 1 else 48
    boom_length_m = boom_length_in * 0.0254
    
    # Free-space gain for this element count
    wavelength_in = wavelength / 0.0254  # wavelength in inches
    standard_gain = get_free_space_gain(n)
    standard_boom_in = get_standard_boom_in(n, wavelength_in)
    
    # Adjust gain if actual boom differs from standard (2.5 dB per doubling)
    boom_adj = 0.0
    if boom_length_in > 0 and standard_boom_in > 0:
        boom_ratio = boom_length_in / standard_boom_in
        if boom_ratio > 0 and boom_ratio != 1.0:
            boom_adj = round(2.5 * math.log2(boom_ratio), 2)
    
    gain_dbi = round(standard_gain + boom_adj, 2)
    
    # Track gain breakdown
    gain_breakdown = {"standard_gain": round(standard_gain, 2), "boom_adj": boom_adj}
    
    # Without reflector, gain is reduced by ~1.5-2 dB
    reflector_adj = 0
    if not has_reflector:
        reflector_adj = -1.5
        gain_dbi += reflector_adj
    gain_breakdown["reflector_adj"] = round(reflector_adj, 2)
    
    # Base gain = boom + elements + reflector (before any options)
    base_gain_dbi = round(gain_dbi, 2)
    
    # Taper bonus
    taper_bonus = taper_effects["gain_bonus"]
    gain_dbi += taper_bonus
    gain_breakdown["taper_bonus"] = round(taper_bonus, 2)
    
    # Corona effect
    corona_adj = corona_effects.get("gain_effect", 0)
    gain_dbi += corona_adj
    gain_breakdown["corona_adj"] = round(corona_adj, 2)
    
    # Ground gain (height-dependent reinforcement from earth reflections)
    # G_real = G_free_space + G_ground. At 1λ: ~5.8 dBi over average soil.
    height_bonus = calculate_ground_gain(height_wavelengths)
    gain_dbi += height_bonus
    gain_breakdown["height_bonus"] = round(height_bonus, 2)
    
    # Boom diameter bonus (negligible — already captured in empirical gain data)
    boom_bonus = 0
    gain_dbi += boom_bonus
    gain_breakdown["boom_bonus"] = round(boom_bonus, 2)
    
    gain_dbi = round(min(gain_dbi, 45.0), 2)
    gain_breakdown["final_gain"] = gain_dbi
    
    # === SWR CALCULATION (Now based on actual element dimensions and height) ===
    swr = calculate_swr_from_elements(input_data.elements, wavelength, taper_enabled, height_wavelengths)
    
    # Apply taper effect
    if taper_enabled:
        swr = round(swr * taper_effects["swr_mult"], 2)
    
    # Boom diameter helps with matching
    if boom_dia_m > 0.04: swr = round(swr * 0.95, 2)
    elif boom_dia_m > 0.025: swr = round(swr * 0.97, 2)
    
    swr = round(max(1.0, min(swr, 5.0)), 2)
    
    # === F/B and F/S RATIOS ===
    if n == 2: fb_ratio, fs_ratio = 14, 8
    elif n == 3: fb_ratio, fs_ratio = 20, 12
    elif n == 4: fb_ratio, fs_ratio = 24, 16
    elif n == 5: fb_ratio, fs_ratio = 26, 18
    else:
        fb_ratio = 20 + 3.0 * math.log2(n - 2)
        fs_ratio = 12 + 2.5 * math.log2(n - 2)
    
    # Without reflector, F/B and F/S are significantly reduced
    if not has_reflector:
        fb_ratio = max(6, fb_ratio - 12)  # Much worse F/B without reflector
        fs_ratio = max(4, fs_ratio - 6)   # Side rejection also worse
    
    fb_ratio += taper_effects["fb_bonus"]
    fs_ratio += taper_effects["fs_bonus"]
    fb_ratio = round(min(fb_ratio, 65), 1)
    fs_ratio = round(min(fs_ratio, 30), 1)
    
    # === BEAMWIDTH ===
    if n == 2: beamwidth_h, beamwidth_v = 62, 68
    elif n == 3: beamwidth_h, beamwidth_v = 52, 58
    elif n == 4: beamwidth_h, beamwidth_v = 45, 50
    elif n == 5: beamwidth_h, beamwidth_v = 40, 45
    else:
        beamwidth_h = 52 / (1 + 0.10 * (n - 3))
        beamwidth_v = 58 / (1 + 0.08 * (n - 3))
    beamwidth_h = round(max(beamwidth_h, 20), 1)
    beamwidth_v = round(max(beamwidth_v, 25), 1)
    
    # === BANDWIDTH ===
    if n <= 3: bandwidth_percent = 6
    elif n <= 5: bandwidth_percent = 5
    else: bandwidth_percent = 5 / (1 + 0.04 * (n - 5))
    
    bandwidth_percent *= taper_effects["bandwidth_mult"]
    bandwidth_percent *= corona_effects.get("bandwidth_effect", 1.0)
    if avg_element_dia > 0.006: bandwidth_percent *= 1.2
    elif avg_element_dia > 0.004: bandwidth_percent *= 1.1
    
    bandwidth_mhz = round(center_freq * bandwidth_percent / 100, 3)
    
    multiplication_factor = round(10 ** (gain_dbi / 10), 2)
    
    # === EFFICIENCY CALCULATION (Comprehensive) ===
    # 1. Base efficiency depends on element count and design complexity
    if n <= 3:
        base_efficiency = 0.92
    elif n <= 5:
        base_efficiency = 0.94
    elif n <= 7:
        base_efficiency = 0.95
    else:
        base_efficiency = 0.96
    
    # 2. SWR mismatch loss - power reflected back to transmitter
    swr_reflection_coeff = (swr - 1) / (swr + 1)  # Gamma (reflection coefficient)
    swr_mismatch_loss = 1 - (swr_reflection_coeff ** 2)  # Power transmitted
    
    # 3. Conductor/material losses based on element diameter
    avg_element_dia_m = sum(convert_element_to_meters(e.diameter, "inches") for e in input_data.elements) / n
    if avg_element_dia_m > 0.02:  # > 20mm (thick elements)
        conductor_efficiency = 0.99
    elif avg_element_dia_m > 0.015:  # 15-20mm
        conductor_efficiency = 0.98
    elif avg_element_dia_m > 0.01:  # 10-15mm
        conductor_efficiency = 0.97
    elif avg_element_dia_m > 0.005:  # 5-10mm
        conductor_efficiency = 0.95
    else:  # < 5mm (thin wire)
        conductor_efficiency = 0.92
    
    # 4. Boom losses
    if boom_dia_m > 0.05:  # > 50mm boom
        boom_efficiency = 0.99
    elif boom_dia_m > 0.03:  # 30-50mm
        boom_efficiency = 0.98
    else:
        boom_efficiency = 0.97
    
    # 5. Height-related ground losses
    if height_wavelengths < 0.25:
        height_efficiency = 0.85  # Very low - significant ground absorption
    elif height_wavelengths < 0.5:
        height_efficiency = 0.92
    elif height_wavelengths < 1.0:
        height_efficiency = 0.97
    else:
        height_efficiency = 0.99  # High enough for minimal ground interaction
    
    # 6. Element spacing efficiency
    driven_elem = next((e for e in input_data.elements if e.element_type == "driven"), None)
    reflector_elem = next((e for e in input_data.elements if e.element_type == "reflector"), None)
    spacing_efficiency = 0.98
    if driven_elem and reflector_elem:
        spacing_m = abs(convert_element_to_meters(driven_elem.position - reflector_elem.position, "inches"))
        ideal_spacing = wavelength * 0.2
        spacing_deviation = abs(spacing_m - ideal_spacing) / ideal_spacing
        if spacing_deviation > 0.3:
            spacing_efficiency = 0.92
        elif spacing_deviation > 0.2:
            spacing_efficiency = 0.95
        elif spacing_deviation > 0.1:
            spacing_efficiency = 0.97
    
    # 7. Taper bonus (tapered elements have better efficiency)
    taper_efficiency = 1.02 if taper_enabled else 1.0
    
    # Calculate total efficiency
    antenna_efficiency = (base_efficiency * swr_mismatch_loss * conductor_efficiency * 
                         boom_efficiency * height_efficiency * spacing_efficiency * taper_efficiency)
    antenna_efficiency = round(min(antenna_efficiency * 100, 99.9), 1)
    
    # === REFLECTED POWER CALCULATIONS ===
    # Reflection coefficient (Gamma)
    reflection_coefficient = round(swr_reflection_coeff, 4)
    
    # Return Loss in dB (how much power is reflected back)
    if reflection_coefficient > 0:
        return_loss_db = round(-20 * math.log10(reflection_coefficient), 2)
    else:
        return_loss_db = 99.99  # Perfect match (infinite return loss)
    
    # Mismatch Loss in dB (power lost due to reflection)
    mismatch_loss_db = round(-10 * math.log10(swr_mismatch_loss), 3) if swr_mismatch_loss > 0 else 0
    
    # Calculate reflected power for common transmit powers
    reflected_power_100w = round(100 * (reflection_coefficient ** 2), 2)
    reflected_power_1kw = round(1000 * (reflection_coefficient ** 2), 1)
    forward_power_100w = round(100 - reflected_power_100w, 2)
    forward_power_1kw = round(1000 - reflected_power_1kw, 1)
    
    # VSWR to Impedance mismatch (assuming 50 ohm system)
    impedance_high = round(50 * swr, 1)  # If load is higher than 50 ohm
    impedance_low = round(50 / swr, 1)   # If load is lower than 50 ohm
    
    # === TAKE-OFF ANGLE CALCULATION ===
    # Take-off angle depends on height above ground (in wavelengths) and ground conditions
    # Lower heights = higher take-off angles (NVIS-like)
    # Higher heights = lower take-off angles (DX-favorable)
    
    # Ground conductivity affects take-off angle
    ground_radials = input_data.ground_radials
    ground_type = "average"
    if ground_radials and ground_radials.enabled:
        ground_type = ground_radials.ground_type
    
    # Ground conductivity factors (affects reflection and take-off angle)
    ground_factors = {
        "wet": {"conductivity": 0.03, "permittivity": 30, "reflection": 0.95, "angle_adj": -3},
        "average": {"conductivity": 0.005, "permittivity": 13, "reflection": 0.85, "angle_adj": 0},
        "dry": {"conductivity": 0.001, "permittivity": 5, "reflection": 0.70, "angle_adj": 5}
    }
    ground = ground_factors.get(ground_type, ground_factors["average"])
    
    # Base take-off angle calculation (simplified model)
    # For a horizontal antenna, take-off angle ≈ arcsin(1/(4*h/λ)) for main lobe
    if height_wavelengths >= 0.25:
        # Main lobe angle decreases with height
        base_takeoff = math.degrees(math.asin(min(1.0, 1 / (4 * height_wavelengths))))
    else:
        # Very low antennas have high take-off angles (nearly vertical)
        base_takeoff = 70 + (0.25 - height_wavelengths) * 80
    
    # Adjust for ground type
    takeoff_angle = round(max(5, min(90, base_takeoff + ground["angle_adj"])), 1)
    
    # Describe the take-off angle
    if takeoff_angle < 15:
        takeoff_desc = "Very Low (Excellent DX)"
    elif takeoff_angle < 25:
        takeoff_desc = "Low (Good DX)"
    elif takeoff_angle < 35:
        takeoff_desc = "Medium-Low (Good all-around)"
    elif takeoff_angle < 50:
        takeoff_desc = "Medium (Regional/DX mix)"
    elif takeoff_angle < 70:
        takeoff_desc = "High (Regional)"
    else:
        takeoff_desc = "Very High (NVIS/Local)"
    
    # === GROUND RADIAL CALCULATIONS ===
    ground_radials_info = None
    if ground_radials and ground_radials.enabled:
        # Calculate quarter wavelength radial length
        quarter_wave_m = wavelength / 4
        quarter_wave_ft = quarter_wave_m * 3.28084
        quarter_wave_in = quarter_wave_m * 39.3701
        
        # Radial directions based on count
        all_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "NNE", "ENE", "ESE", "SSE", "SSW", "WSW", "WNW", "NNW", "N2", "E2"]
        num_rads = ground_radials.num_radials
        radial_directions = all_directions[:num_rads]
        
        # Ground effect on antenna performance - scaled by number of radials
        # More radials = better ground plane = more improvement
        # Base improvements at 8 radials, scale from there
        radial_factor = num_rads / 8.0  # 1.0 at 8 radials
        
        ground_improvement = {
            "wet": {"swr_improvement": 0.05, "gain_bonus": 1.5, "efficiency_bonus": 8},
            "average": {"swr_improvement": 0.03, "gain_bonus": 0.8, "efficiency_bonus": 5},
            "dry": {"swr_improvement": 0.01, "gain_bonus": 0.3, "efficiency_bonus": 2}
        }
        base_bonus = ground_improvement.get(ground_type, ground_improvement["average"])
        
        # Scale improvements by radial count (diminishing returns after 8)
        if radial_factor <= 1.0:
            # Fewer radials = linear reduction
            scale = radial_factor
        else:
            # More radials = diminishing returns (logarithmic)
            scale = 1.0 + (math.log2(radial_factor) * 0.5)
        
        g_bonus = {
            "swr_improvement": round(base_bonus["swr_improvement"] * scale, 3),
            "gain_bonus": round(base_bonus["gain_bonus"] * scale, 2),
            "efficiency_bonus": round(base_bonus["efficiency_bonus"] * scale, 1)
        }
        
        ground_radials_info = {
            "enabled": True,
            "ground_type": ground_type,
            "ground_conductivity": ground["conductivity"],
            "ground_permittivity": ground["permittivity"],
            "ground_reflection_coeff": ground["reflection"],
            "radial_length_m": round(quarter_wave_m, 2),
            "radial_length_ft": round(quarter_wave_ft, 2),
            "radial_length_in": round(quarter_wave_in, 1),
            "wire_diameter_in": ground_radials.wire_diameter,
            "num_radials": ground_radials.num_radials,
            "radial_directions": radial_directions,
            "total_wire_length_ft": round(quarter_wave_ft * ground_radials.num_radials, 1),
            "estimated_improvements": {
                "swr_improvement": g_bonus["swr_improvement"],
                "gain_bonus_db": g_bonus["gain_bonus"],
                "efficiency_bonus_percent": g_bonus["efficiency_bonus"]
            }
        }
        
        # Apply ground radial benefits to calculations
        swr = max(1.0, swr - g_bonus["swr_improvement"])
        gain_dbi = round(gain_dbi + g_bonus["gain_bonus"], 2)
        gain_breakdown["ground_radials_bonus"] = round(g_bonus["gain_bonus"], 2)
        gain_breakdown["final_gain"] = gain_dbi
        antenna_efficiency = min(99.9, antenna_efficiency + g_bonus["efficiency_bonus"])
    
    # === SWR CURVE ===
    swr_curve = []
    for i in range(-30, 31):
        freq = center_freq + (i * channel_spacing)
        swr_at_freq = calculate_swr_at_frequency(freq, center_freq, bandwidth_mhz, swr)
        swr_curve.append({"frequency": round(freq, 4), "swr": round(swr_at_freq, 2), "channel": i})
    
    usable_1_5 = round(sum(1 for p in swr_curve if p["swr"] <= 1.5) * channel_spacing, 3)
    usable_2_0 = round(sum(1 for p in swr_curve if p["swr"] <= 2.0) * channel_spacing, 3)
    
    # === FAR FIELD PATTERN ===
    # Check if antenna has a reflector
    has_reflector = any(e.element_type == "reflector" for e in input_data.elements)
    
    far_field_pattern = []
    for angle in range(0, 361, 5):
        theta = math.radians(angle)
        cos_theta = math.cos(theta)
        
        if not has_reflector:
            # No reflector: More omnidirectional pattern with reduced F/B
            # Pattern is more like a dipole with directors providing some directionality
            if n == 2:
                # Just driven + 1 director: slight forward bias
                main_lobe = 0.6 + 0.4 * cos_theta
                magnitude = (max(0.2, main_lobe) ** 1.5) * 100
            else:
                # Driven + multiple directors: forward gain but weak back rejection
                # Use abs to avoid complex numbers from negative cosine raised to fractional power
                forward_gain = max(0, cos_theta) ** 1.5 if cos_theta >= 0 else 0
                # Without reflector, back lobe is only ~6-10dB down (vs 20+ with reflector)
                back_level = 0.3 + 0.1 * min(n - 2, 5)  # More directors = slightly better rejection, cap at 5
                
                if 90 < angle < 270:  # Back hemisphere
                    magnitude = max(forward_gain, back_level) * 100
                else:  # Front hemisphere
                    magnitude = max(forward_gain, 0.1) * 100
                
                # Side lobes are also larger without reflector
                if 60 < angle < 120 or 240 < angle < 300:
                    magnitude = max(magnitude, 25)  # Higher side lobes
        else:
            # With reflector: Standard Yagi pattern with good F/B
            if n == 2:
                main_lobe = (cos_theta + 0.3) / 1.3
                magnitude = (max(0, main_lobe) ** 2) * 100
            else:
                main_lobe = max(0, cos_theta ** 2)
                back_attenuation = 10 ** (-fb_ratio / 20)
                side_attenuation = 10 ** (-fs_ratio / 20)
                if 90 < angle < 270:
                    magnitude = main_lobe * back_attenuation * 100
                else:
                    magnitude = main_lobe * 100
                if 60 < angle < 120 or 240 < angle < 300:
                    magnitude *= side_attenuation
        
        far_field_pattern.append({"angle": angle, "magnitude": round(max(magnitude, 1), 1)})
    
    # === STACKING ===
    stacking_enabled = False
    stacking_info = None
    stacked_gain_dbi = None
    stacked_pattern = None
    
    if input_data.stacking and input_data.stacking.enabled:
        stacking_enabled = True
        stacking = input_data.stacking
        spacing_m = convert_spacing_to_meters(stacking.spacing, stacking.spacing_unit)
        spacing_wavelengths = spacing_m / wavelength
        stacked_gain_dbi, gain_increase = calculate_stacking_gain(gain_dbi, stacking.num_antennas, spacing_wavelengths, stacking.orientation)
        
        if stacking.orientation == "vertical":
            new_beamwidth_v = calculate_stacked_beamwidth(beamwidth_v, stacking.num_antennas, spacing_wavelengths)
            new_beamwidth_h = beamwidth_h
        else:
            new_beamwidth_h = calculate_stacked_beamwidth(beamwidth_h, stacking.num_antennas, spacing_wavelengths)
            new_beamwidth_v = beamwidth_v
        
        stacked_pattern = generate_stacked_pattern(far_field_pattern, stacking.num_antennas, spacing_wavelengths, stacking.orientation)
        optimal_spacing_ft = round((wavelength * 0.65) / 0.3048, 1)
        
        stacking_info = {
            "orientation": stacking.orientation,
            "num_antennas": stacking.num_antennas,
            "spacing": stacking.spacing,
            "spacing_unit": stacking.spacing_unit,
            "spacing_wavelengths": round(spacing_wavelengths, 3),
            "gain_increase_db": gain_increase,
            "new_beamwidth_h": new_beamwidth_h,
            "new_beamwidth_v": new_beamwidth_v,
            "stacked_multiplication_factor": round(10 ** (stacked_gain_dbi / 10), 2),
            "optimal_spacing_ft": optimal_spacing_ft,
        }
        beamwidth_h, beamwidth_v = new_beamwidth_h, new_beamwidth_v
    
    swr_desc = "Perfect" if swr <= 1.1 else ("Excellent" if swr <= 1.3 else ("Very Good" if swr <= 1.5 else ("Good" if swr <= 2.0 else "Fair")))
    
    taper_info = None
    if input_data.taper and input_data.taper.enabled:
        taper_info = {
            "enabled": True,
            "num_tapers": taper_effects["num_tapers"],
            "gain_bonus": taper_effects["gain_bonus"],
            "bandwidth_improvement": f"{(taper_effects['bandwidth_mult'] - 1) * 100:.0f}%",
            "sections": taper_effects["sections"]
        }
    
    return AntennaOutput(
        swr=swr,
        swr_description=f"{swr_desc} match - {swr}:1",
        fb_ratio=fb_ratio,
        fb_ratio_description=f"{fb_ratio} dB front-to-back",
        fs_ratio=fs_ratio,
        fs_ratio_description=f"{fs_ratio} dB front-to-side",
        beamwidth_h=beamwidth_h,
        beamwidth_v=beamwidth_v,
        beamwidth_description=f"H: {beamwidth_h}° / V: {beamwidth_v}°",
        bandwidth=bandwidth_mhz,
        bandwidth_description=f"{usable_2_0:.3f} MHz at 2:1 SWR",
        gain_dbi=gain_dbi,
        gain_description=f"{round(10 ** ((stacked_gain_dbi or gain_dbi) / 10), 2)}x over isotropic",
        base_gain_dbi=base_gain_dbi,
        gain_breakdown=gain_breakdown,
        multiplication_factor=multiplication_factor,
        multiplication_description="ERP multiplier",
        antenna_efficiency=antenna_efficiency,
        efficiency_description=f"{antenna_efficiency}% efficient",
        far_field_pattern=far_field_pattern,
        swr_curve=swr_curve,
        usable_bandwidth_1_5=usable_1_5,
        usable_bandwidth_2_0=usable_2_0,
        center_frequency=center_freq,
        band_info={**band_info, "channel_spacing_khz": band_info.get("channel_spacing_khz", 10)},
        input_summary={"num_elements": n, "center_frequency_mhz": center_freq, "wavelength_m": round(wavelength, 3)},
        stacking_enabled=stacking_enabled,
        stacking_info=stacking_info,
        stacked_gain_dbi=stacked_gain_dbi,
        stacked_pattern=stacked_pattern,
        taper_info=taper_info,
        corona_info=corona_effects if corona_effects.get("enabled") else None,
        # Reflected power data
        reflection_coefficient=reflection_coefficient,
        return_loss_db=return_loss_db,
        mismatch_loss_db=mismatch_loss_db,
        reflected_power_100w=reflected_power_100w,
        reflected_power_1kw=reflected_power_1kw,
        forward_power_100w=forward_power_100w,
        forward_power_1kw=forward_power_1kw,
        impedance_high=impedance_high,
        impedance_low=impedance_low,
        # Take-off angle and ground radials
        takeoff_angle=takeoff_angle,
        takeoff_angle_description=takeoff_desc,
        ground_radials_info=ground_radials_info
    )


def auto_tune_antenna(request: AutoTuneRequest) -> AutoTuneOutput:
    """Calculate optimal element dimensions for best performance."""
    band_info = BAND_DEFINITIONS.get(request.band, BAND_DEFINITIONS["11m_cb"])
    center_freq = request.frequency_mhz if request.frequency_mhz else band_info["center"]
    
    c = 299792458
    wavelength_m = c / (center_freq * 1e6)
    wavelength_in = wavelength_m * 39.3701  # Convert to inches
    
    n = request.num_elements
    elements = []
    notes = []
    
    # Optimal driven element: ~0.473 wavelength
    driven_length = round(wavelength_in * 0.473, 1)
    
    # Determine if we should include reflector
    use_reflector = getattr(request, 'use_reflector', True)
    
    # Use shared standard boom lengths, scaled for current band
    scale_factor = wavelength_in / REF_WAVELENGTH_11M_IN
    
    # Get target boom length, scaled for current band
    target_boom = STANDARD_BOOM_11M_IN.get(n, 150 + (n - 3) * 60) * scale_factor
    
    if use_reflector:
        # Reflector-to-driven: ~15% of total boom (closer than directors)
        refl_driven_gap = round(target_boom * 0.15, 1) if n > 2 else round(target_boom, 1)
        
        elements.append({
            "element_type": "reflector",
            "length": round(driven_length * 1.05, 1),
            "diameter": 0.5,
            "position": 0
        })
        notes.append(f"Reflector: {round(driven_length * 1.05, 1)}\" (5% longer than driven)")
        
        elements.append({
            "element_type": "driven",
            "length": driven_length,
            "diameter": 0.5,
            "position": refl_driven_gap
        })
        notes.append(f"Driven: {driven_length}\" at {refl_driven_gap}\" from reflector")
        
        num_directors = n - 2
        remaining_boom = target_boom - refl_driven_gap
        current_position = refl_driven_gap
    else:
        elements.append({
            "element_type": "driven",
            "length": driven_length,
            "diameter": 0.5,
            "position": 0
        })
        notes.append(f"Driven: {driven_length}\" at position 0 (no reflector)")
        
        num_directors = n - 1
        remaining_boom = target_boom
        current_position = 0
    
    # === SPACING LOCK MODE ===
    # When spacing lock is enabled, keep original positions and only tune lengths
    if request.spacing_lock_enabled and request.locked_positions:
        # Preserve the locked positions
        for i, elem in enumerate(elements):
            if i < len(request.locked_positions):
                elem["position"] = request.locked_positions[i]
        
        # Add directors at locked positions  
        for i in range(num_directors):
            position_idx = (2 if use_reflector else 1) + i
            if position_idx < len(request.locked_positions):
                locked_pos = request.locked_positions[position_idx]
            else:
                director_spacing = remaining_boom / num_directors if num_directors > 0 else remaining_boom
                current_position += director_spacing
                locked_pos = current_position
            
            director_length = round(driven_length * (0.95 - i * 0.02), 1)
            
            elements.append({
                "element_type": "director",
                "length": director_length,
                "diameter": 0.5,
                "position": locked_pos
            })
            notes.append(f"Director {i+1}: {director_length}\" at {locked_pos}\" (spacing locked)")
        notes.append("Spacing Lock: Positions preserved, only lengths optimized")
    else:
        # Normal mode: distribute directors evenly along remaining boom
        # First director slightly closer, then gradually increasing spacing
        if num_directors > 0:
            for i in range(num_directors):
                # Weight: first director at ~0.8x avg spacing, last at ~1.2x avg spacing
                # This mimics real Yagi designs where initial directors are closer
                weight = 0.8 + (0.4 * i / max(num_directors - 1, 1))
                total_weight = sum(0.8 + (0.4 * j / max(num_directors - 1, 1)) for j in range(num_directors))
                director_spacing = round(remaining_boom * weight / total_weight, 1)
                current_position += director_spacing
                
                # Each director ~2% shorter than previous
                director_length = round(driven_length * (0.95 - i * 0.02), 1)
                
                elements.append({
                    "element_type": "director",
                    "length": director_length,
                    "diameter": 0.5,
                    "position": round(current_position, 1)
                })
                notes.append(f"Director {i+1}: {director_length}\" at {round(current_position, 1)}\"")
    
    notes.append(f"")
    notes.append(f"Wavelength at {center_freq} MHz: {round(wavelength_in, 1)}\"")
    
    # === SPACING MODE ===
    # Apply tight/long spacing BEFORE boom lock (boom lock is the hard constraint)
    spacing_factor = request.spacing_level
    if request.spacing_mode != "normal" and abs(spacing_factor - 1.0) > 0.01:
        first_pos = elements[0]["position"] if elements else 0
        for elem in elements:
            if elem["position"] != first_pos:
                relative = elem["position"] - first_pos
                elem["position"] = round(first_pos + relative * spacing_factor, 1)
        
        mode_label = "Tight" if request.spacing_mode == "tight" else "Long"
        notes.append(f"")
        notes.append(f"Spacing: {mode_label} mode ({spacing_factor:.2f}x)")
        if spacing_factor < 1.0:
            notes.append(f"Note: Tight spacing may reduce gain by ~{round((1 - spacing_factor) * 2.5, 1)} dB but improves F/B")
        else:
            notes.append(f"Note: Long spacing may increase gain by ~{round((spacing_factor - 1) * 1.5, 1)} dB but widen beamwidth")
    
    # === BOOM LOCK MODE (FINAL CONSTRAINT) ===
    # When boom lock is active, evenly distribute elements across the locked boom length
    # Reflector at 0, driven at ~15% of boom, directors equally spaced in remaining space
    if request.boom_lock_enabled and request.max_boom_length:
        target_boom = request.max_boom_length
        
        # Find reflector, driven, and directors
        refl_idx = next((i for i, e in enumerate(elements) if e["element_type"] == "reflector"), None)
        driven_idx = next((i for i, e in enumerate(elements) if e["element_type"] == "driven"), None)
        dir_indices = [i for i, e in enumerate(elements) if e["element_type"] == "director"]
        
        if driven_idx is not None:
            if refl_idx is not None:
                # Has reflector: reflector at 0
                elements[refl_idx]["position"] = 0
                
                if len(dir_indices) > 0:
                    # With directors: driven at 15% of boom, directors equally spaced after
                    refl_driven_gap = round(target_boom * 0.15, 1)
                    elements[driven_idx]["position"] = refl_driven_gap
                    remaining = target_boom - refl_driven_gap
                    dir_spacing = round(remaining / len(dir_indices), 1)
                    for j, idx in enumerate(dir_indices):
                        elements[idx]["position"] = round(refl_driven_gap + dir_spacing * (j + 1), 1)
                else:
                    # No directors (2-element): driven uses full boom length
                    elements[driven_idx]["position"] = round(target_boom, 1)
            else:
                # No reflector: driven at 0, directors equally spaced
                elements[driven_idx]["position"] = 0
                if len(dir_indices) > 0:
                    dir_spacing = round(target_boom / len(dir_indices), 1)
                    for j, idx in enumerate(dir_indices):
                        elements[idx]["position"] = round(dir_spacing * (j + 1), 1)
        
        notes.append(f"")
        notes.append(f"Boom Lock: {target_boom}\" ({round(target_boom/12, 1)} ft) — elements equally spaced")
        compression_penalty = 0
    else:
        compression_penalty = 0
    
    # Final boom length note (after all spacing/boom adjustments)
    final_boom = max(e['position'] for e in elements) if elements else 0
    notes.append(f"")
    notes.append(f"Total boom length: ~{round(final_boom, 1)}\" ({round(final_boom/12, 1)} ft)")
    
    # Predict performance using shared free-space gain model
    base_predicted_swr = 1.05 if request.taper and request.taper.enabled else 1.1
    predicted_swr = base_predicted_swr if use_reflector else base_predicted_swr + 0.1
    
    # Use the calibrated free-space gain lookup (same model as /api/calculate)
    base_gain = get_free_space_gain(n)
    
    if not use_reflector:
        base_gain -= 1.5  # Less gain without reflector
    if request.taper and request.taper.enabled:
        base_gain += 0.3 * request.taper.num_tapers
    height_m = convert_height_to_meters(request.height_from_ground, request.height_unit)
    predicted_gain = round(base_gain + calculate_ground_gain(height_m / wavelength_m) - compression_penalty, 1)
    
    # Safe F/B calculation
    if n <= 5:
        predicted_fb = {2: 14, 3: 20, 4: 24, 5: 26}.get(n, 14)
    else:
        predicted_fb = 20 + 3 * math.log2(max(n - 2, 1))
    
    if not use_reflector:
        predicted_fb -= 8  # Worse F/B without reflector
    if request.taper and request.taper.enabled:
        predicted_fb += 1.5 * request.taper.num_tapers
    
    if not use_reflector:
        notes.append(f"Note: No reflector mode - reduced F/B ratio")
    
    return AutoTuneOutput(
        optimized_elements=elements,
        predicted_swr=predicted_swr,
        predicted_gain=predicted_gain,
        predicted_fb_ratio=round(max(predicted_fb, 6), 1),
        optimization_notes=notes
    )


@api_router.get("/")
async def root():
    return {"message": "Antenna Calculator API"}

@api_router.get("/bands")
async def get_bands():
    return BAND_DEFINITIONS

@api_router.post("/calculate", response_model=AntennaOutput)
async def calculate_antenna(input_data: AntennaInput):
    result = calculate_antenna_parameters(input_data)
    record = CalculationRecord(inputs=input_data.dict(), outputs=result.dict())
    await db.calculations.insert_one(record.dict())
    return result

@api_router.post("/auto-tune", response_model=AutoTuneOutput)
async def auto_tune(request: AutoTuneRequest):
    """Auto-tune antenna elements for optimal performance."""
    return auto_tune_antenna(request)


class HeightOptimizeRequest(BaseModel):
    num_elements: int
    elements: List[ElementDimension]
    boom_diameter: float
    boom_unit: str = "inches"
    band: str = "11m_cb"
    frequency_mhz: Optional[float] = None
    min_height: int = 10
    max_height: int = 100
    step: int = 1  # Changed to 1 foot increments
    ground_radials: Optional[GroundRadialConfig] = None

class HeightOptimizeOutput(BaseModel):
    optimal_height: int
    optimal_swr: float
    optimal_gain: float
    optimal_fb_ratio: float
    heights_tested: List[dict]

@api_router.post("/optimize-height", response_model=HeightOptimizeOutput)
async def optimize_height(request: HeightOptimizeRequest):
    """Test heights from min to max and find best overall performance (SWR, Gain, F/B, Take-off Angle).
    Factors in: number of elements, boom length, ground radials, ground type."""
    best_height = request.min_height
    best_score = -999.0
    best_swr = 999.0
    best_gain = 0.0
    best_fb = 0.0
    heights_tested = []
    
    # Get wavelength for takeoff angle calculation
    band_info = BAND_DEFINITIONS.get(request.band, BAND_DEFINITIONS["11m_cb"])
    center_freq = request.frequency_mhz if request.frequency_mhz else band_info["center"]
    c = 299792458
    wavelength = c / (center_freq * 1e6)
    
    # Calculate boom length from element positions (in meters)
    positions = [e.position for e in request.elements]
    boom_length_in = max(positions) - min(positions) if positions else 0
    boom_length_m = boom_length_in * 0.0254
    boom_wavelengths = boom_length_m / wavelength if wavelength > 0 else 0
    
    n = request.num_elements
    
    # Ground type from radials config
    ground_type = "average"
    has_radials = False
    if request.ground_radials and request.ground_radials.enabled:
        ground_type = request.ground_radials.ground_type
        has_radials = True
    
    ground_angle_adj = {"wet": -3, "average": 0, "dry": 5}.get(ground_type, 0)
    
    for height in range(request.min_height, request.max_height + 1, request.step):
        # Create a calculation request for this height
        calc_input = AntennaInput(
            num_elements=request.num_elements,
            elements=request.elements,
            height_from_ground=height,
            height_unit="ft",
            boom_diameter=request.boom_diameter,
            boom_unit=request.boom_unit,
            band=request.band,
            frequency_mhz=request.frequency_mhz,
            stacking=None,
            taper=None,
            corona_balls=None,
            ground_radials=request.ground_radials
        )
        
        # Calculate for this height
        result = await calculate_antenna(calc_input)
        swr = result.swr
        gain = result.gain_dbi
        fb = result.fb_ratio
        
        # Calculate take-off angle for this height
        height_m = height * 0.3048
        height_wavelengths = height_m / wavelength
        
        if height_wavelengths >= 0.25:
            takeoff_angle = math.degrees(math.asin(min(1.0, 1 / (4 * height_wavelengths))))
        else:
            takeoff_angle = 70 + (0.25 - height_wavelengths) * 80
        takeoff_angle = round(max(5, min(90, takeoff_angle + ground_angle_adj)), 1)
        
        # === IMPROVED SCORING (factors in boom, elements, ground) ===
        
        # SWR score
        if swr <= 1.5:
            swr_score = 10 - (swr - 1.0) * 4
        elif swr <= 2.0:
            swr_score = 8 - (swr - 1.5) * 8
        else:
            swr_score = max(0, 4 - (swr - 2.0) * 4)
        
        # Gain score
        gain_score = gain * 2.5
        
        # F/B ratio score
        fb_score = fb * 0.4
        
        # Take-off angle score
        if takeoff_angle <= 15:
            takeoff_score = 25
        elif takeoff_angle <= 25:
            takeoff_score = 25 - (takeoff_angle - 15) * 1.0
        elif takeoff_angle <= 40:
            takeoff_score = 15 - (takeoff_angle - 25) * 0.8
        else:
            takeoff_score = max(0, 3 - (takeoff_angle - 40) * 0.1)
        
        # === BOOM LENGTH FACTOR ===
        # Longer booms need higher mounting for proper pattern formation
        # Minimum effective height is roughly boom_length * 1.5
        boom_height_ratio = height_m / boom_length_m if boom_length_m > 0 else 2.0
        min_effective_ratio = 1.5 + (boom_wavelengths * 0.5)  # Scales with boom size
        
        if boom_height_ratio >= min_effective_ratio:
            boom_score = 8.0  # Height well above boom requirement
        elif boom_height_ratio >= 1.0:
            boom_score = 4.0 + (boom_height_ratio - 1.0) * (4.0 / (min_effective_ratio - 1.0))
        elif boom_height_ratio >= 0.5:
            boom_score = boom_height_ratio * 4.0  # Under-height penalty
        else:
            boom_score = boom_height_ratio * 2.0  # Very low relative to boom
        
        # Scale boom importance by boom wavelengths (longer booms matter more)
        boom_score *= (1.0 + boom_wavelengths * 0.8)
        
        # === ELEMENT COUNT FACTOR ===
        # More elements = more directivity = needs height in specific wavelength bands
        # Higher element counts are more height-sensitive and benefit from higher mounting
        ideal_low = 0.5 + (n - 2) * 0.05   # Shifts sweet spot up with more elements
        ideal_high = 1.0 + (n - 2) * 0.1    # Widens sweet spot for more elements
        
        if ideal_low <= height_wavelengths <= ideal_high:
            element_score = 6.0 + (n - 2) * 1.5  # Sweet spot scales with element count
        elif (ideal_low - 0.15) <= height_wavelengths < ideal_low:
            element_score = 3.0 + (n - 2) * 0.5
        elif ideal_high < height_wavelengths <= (ideal_high + 0.3):
            element_score = 4.0 + (n - 2) * 0.5
        else:
            element_score = 1.0
        
        # === GROUND RADIALS FACTOR ===
        # With ground radials, lower heights can be more effective
        # Radials improve ground reflection, favoring slightly lower heights
        radial_score = 0
        if has_radials:
            num_rads = request.ground_radials.num_radials
            if ground_type == "wet":
                # Wet ground + radials: lower heights work well
                if 0.3 <= height_wavelengths <= 0.8:
                    radial_score = 4.0
                else:
                    radial_score = 2.0
            elif ground_type == "dry":
                # Dry ground: need more height even with radials
                if 0.6 <= height_wavelengths <= 1.2:
                    radial_score = 3.0
                else:
                    radial_score = 1.0
            else:
                # Average ground
                if 0.4 <= height_wavelengths <= 1.0:
                    radial_score = 3.5
                else:
                    radial_score = 1.5
            # Scale by radial count (more = better ground plane)
            radial_score *= min(num_rads / 8.0, 1.5)
        
        total_score = swr_score + gain_score + fb_score + takeoff_score + boom_score + element_score + radial_score
        
        heights_tested.append({
            "height": height, 
            "swr": round(swr, 2),
            "gain": round(gain, 2),
            "fb_ratio": round(fb, 1),
            "takeoff_angle": takeoff_angle,
            "score": round(total_score, 1)
        })
        
        if total_score > best_score:
            best_score = total_score
            best_height = height
            best_swr = swr
            best_gain = gain
            best_fb = fb
    
    return HeightOptimizeOutput(
        optimal_height=best_height,
        optimal_swr=round(best_swr, 2),
        optimal_gain=round(best_gain, 2),
        optimal_fb_ratio=round(best_fb, 1),
        heights_tested=heights_tested
    )


# ==================== SAVED DESIGNS ENDPOINTS ====================
class SavedDesign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: Optional[str] = ""
    design_data: dict
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SaveDesignRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    design_data: dict

class SaveDesignResponse(BaseModel):
    id: str
    name: str
    message: str

@api_router.post("/designs/save", response_model=SaveDesignResponse)
async def save_design(request: SaveDesignRequest, user: dict = Depends(require_user)):
    """Save a design for the current user"""
    design = SavedDesign(
        user_id=user["id"],
        name=request.name,
        description=request.description,
        design_data=request.design_data
    )
    
    await db.saved_designs.insert_one(design.dict())
    
    return SaveDesignResponse(
        id=design.id,
        name=design.name,
        message="Design saved successfully"
    )

@api_router.get("/designs")
async def get_user_designs(user: dict = Depends(require_user)):
    """Get all saved designs for the current user"""
    designs = await db.saved_designs.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    return [{
        "id": d["id"],
        "name": d["name"],
        "description": d.get("description", ""),
        "created_at": d["created_at"],
        "updated_at": d.get("updated_at", d["created_at"])
    } for d in designs]

@api_router.get("/designs/{design_id}")
async def get_design(design_id: str, user: dict = Depends(require_user)):
    """Get a specific saved design"""
    design = await db.saved_designs.find_one({"id": design_id, "user_id": user["id"]})
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return {
        "id": design["id"],
        "name": design["name"],
        "description": design.get("description", ""),
        "design_data": design["design_data"],
        "created_at": design["created_at"]
    }

@api_router.delete("/designs/{design_id}")
async def delete_design(design_id: str, user: dict = Depends(require_user)):
    """Delete a saved design"""
    result = await db.saved_designs.delete_one({"id": design_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Design not found")
    return {"message": "Design deleted successfully"}


@api_router.get("/history", response_model=List[CalculationRecord])
async def get_calculation_history():
    records = await db.calculations.find().sort("timestamp", -1).limit(20).to_list(20)
    return [CalculationRecord(**record) for record in records]

@api_router.delete("/history")
async def clear_history():
    result = await db.calculations.delete_many({})
    return {"deleted_count": result.deleted_count}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.dict())
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**sc) for sc in status_checks]


# ==================== AUTH ENDPOINTS ====================
@api_router.post("/auth/register")
async def register_user(user_data: UserCreate):
    """Register a new user with 1-hour trial"""
    # Check if email exists
    existing = await db.users.find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Determine tier (admin gets full access)
    is_admin = user_data.email.lower() == ADMIN_EMAIL.lower()
    tier = "admin" if is_admin else "trial"
    
    user = {
        "id": str(uuid.uuid4()),
        "email": user_data.email.lower(),
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "subscription_tier": tier,
        "subscription_expires": datetime.utcnow() + timedelta(days=36500) if is_admin else None,
        "is_trial": not is_admin,
        "trial_started": datetime.utcnow() if not is_admin else None,
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(user)
    token = create_token(user["id"], user["email"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "subscription_tier": user["subscription_tier"],
            "subscription_expires": user["subscription_expires"],
            "is_trial": user["is_trial"],
            "trial_started": user["trial_started"]
        }
    }

@api_router.post("/auth/login")
async def login_user(credentials: UserLogin):
    """Login existing user"""
    user = await db.users.find_one({"email": credentials.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_token(user["id"], user["email"])
    
    # Check subscription status
    is_active, tier_info, status_msg = check_subscription_active(user)
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "subscription_tier": user["subscription_tier"],
            "subscription_expires": user.get("subscription_expires"),
            "is_trial": user.get("is_trial", False),
            "trial_started": user.get("trial_started"),
            "is_active": is_active,
            "status_message": status_msg
        }
    }

@api_router.get("/auth/me")
async def get_current_user_info(user: dict = Depends(require_user)):
    """Get current user info and subscription status"""
    is_active, tier_info, status_msg = check_subscription_active(user)
    
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "subscription_tier": user["subscription_tier"],
        "subscription_expires": user.get("subscription_expires"),
        "is_trial": user.get("is_trial", False),
        "trial_started": user.get("trial_started"),
        "is_active": is_active,
        "status_message": status_msg,
        "tier_info": tier_info,
        "max_elements": tier_info["max_elements"] if tier_info else 3
    }


# ==================== SUBSCRIPTION ENDPOINTS ====================
@api_router.get("/subscription/tiers")
async def get_subscription_tiers():
    """Get available subscription tiers"""
    tiers = {k: v for k, v in SUBSCRIPTION_TIERS.items() if k != "admin"}
    return {"tiers": tiers, "payment_methods": PAYMENT_CONFIG}

@api_router.post("/subscription/upgrade")
async def upgrade_subscription(upgrade: SubscriptionUpdate, user: dict = Depends(require_user)):
    """Upgrade user subscription (after payment verification)"""
    if upgrade.tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    tier_info = SUBSCRIPTION_TIERS[upgrade.tier]
    
    # Record payment
    payment = PaymentRecord(
        user_id=user["id"],
        amount=tier_info["price"],
        tier=upgrade.tier,
        payment_method=upgrade.payment_method,
        payment_reference=upgrade.payment_reference,
        status="pending"
    )
    await db.payments.insert_one(payment.dict())
    
    # Update user subscription (in production, verify payment first)
    duration_days = tier_info.get("duration_days", 30)
    expires = datetime.utcnow() + timedelta(days=duration_days)
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "subscription_tier": upgrade.tier,
            "subscription_expires": expires,
            "is_trial": False
        }}
    )
    
    # Mark payment complete
    await db.payments.update_one(
        {"id": payment.id},
        {"$set": {"status": "completed"}}
    )
    
    return {
        "success": True,
        "message": f"Upgraded to {tier_info['name']}",
        "subscription_tier": upgrade.tier,
        "subscription_expires": expires,
        "max_elements": tier_info["max_elements"]
    }

@api_router.post("/subscription/cancel")
async def cancel_subscription(user: dict = Depends(require_user)):
    """Cancel subscription - downgrade to free/expired"""
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "subscription_tier": "trial",
            "subscription_expires": None,
            "is_trial": False,
            "cancelled_at": datetime.utcnow()
        }}
    )
    return {"success": True, "message": "Subscription cancelled. You can renew anytime."}

@api_router.post("/admin/subscription/manage")
async def admin_manage_subscription(data: dict, admin: dict = Depends(require_admin)):
    """Admin: extend, change, or cancel a user's subscription"""
    user_id = data.get("user_id")
    action = data.get("action")  # extend, change_tier, cancel
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if action == "extend":
        days = data.get("days", 30)
        current_expires = user.get("subscription_expires")
        if current_expires:
            if isinstance(current_expires, str):
                current_expires = datetime.fromisoformat(current_expires.replace('Z', '+00:00'))
            # Extend from current expiry or now, whichever is later
            base = max(current_expires.replace(tzinfo=None), datetime.utcnow())
        else:
            base = datetime.utcnow()
        new_expires = base + timedelta(days=days)
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"subscription_expires": new_expires, "is_trial": False}}
        )
        return {"success": True, "message": f"Extended {days} days. Expires: {new_expires.isoformat()}"}
    
    elif action == "change_tier":
        new_tier = data.get("tier")
        if new_tier not in SUBSCRIPTION_TIERS:
            raise HTTPException(status_code=400, detail="Invalid tier")
        duration_days = SUBSCRIPTION_TIERS[new_tier].get("duration_days", 30)
        expires = datetime.utcnow() + timedelta(days=duration_days)
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "subscription_tier": new_tier,
                "subscription_expires": expires,
                "is_trial": False
            }}
        )
        return {"success": True, "message": f"Changed to {new_tier}. Expires: {expires.isoformat()}"}
    
    elif action == "cancel":
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "subscription_tier": "trial",
                "subscription_expires": None,
                "is_trial": False,
                "cancelled_at": datetime.utcnow()
            }}
        )
        return {"success": True, "message": "User subscription cancelled"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use: extend, change_tier, cancel")


@api_router.get("/subscription/status")
async def get_subscription_status(user: dict = Depends(require_user)):
    """Get current subscription status"""
    is_active, tier_info, status_msg = check_subscription_active(user)
    
    # Calculate trial time remaining if on trial
    trial_remaining = None
    if user.get("is_trial") and user.get("trial_started"):
        trial_started = user["trial_started"]
        if isinstance(trial_started, str):
            trial_started = datetime.fromisoformat(trial_started.replace('Z', '+00:00'))
        elapsed = datetime.utcnow() - trial_started.replace(tzinfo=None)
        remaining = timedelta(hours=1) - elapsed
        trial_remaining = max(0, remaining.total_seconds())
    
    return {
        "is_active": is_active,
        "status_message": status_msg,
        "tier": user["subscription_tier"],
        "tier_info": tier_info,
        "expires": user.get("subscription_expires"),
        "trial_remaining_seconds": trial_remaining,
        "max_elements": tier_info["max_elements"] if tier_info else 3
    }


# ==================== ADMIN ENDPOINTS ====================
@api_router.get("/admin/pricing")
async def get_admin_pricing(admin: dict = Depends(require_admin)):
    """Get current pricing settings (admin only)"""
    return {
        "bronze": {
            "monthly_price": SUBSCRIPTION_TIERS["bronze_monthly"]["price"],
            "yearly_price": SUBSCRIPTION_TIERS["bronze_yearly"]["price"],
            "max_elements": SUBSCRIPTION_TIERS["bronze_monthly"]["max_elements"],
            "features": SUBSCRIPTION_TIERS["bronze_monthly"].get("features", ["basic_calc", "swr_meter", "band_selection"])
        },
        "silver": {
            "monthly_price": SUBSCRIPTION_TIERS["silver_monthly"]["price"],
            "yearly_price": SUBSCRIPTION_TIERS["silver_yearly"]["price"],
            "max_elements": SUBSCRIPTION_TIERS["silver_monthly"]["max_elements"],
            "features": SUBSCRIPTION_TIERS["silver_monthly"].get("features", ["basic_calc", "swr_meter", "band_selection", "auto_tune", "save_designs"])
        },
        "gold": {
            "monthly_price": SUBSCRIPTION_TIERS["gold_monthly"]["price"],
            "yearly_price": SUBSCRIPTION_TIERS["gold_yearly"]["price"],
            "max_elements": SUBSCRIPTION_TIERS["gold_monthly"]["max_elements"],
            "features": SUBSCRIPTION_TIERS["gold_monthly"].get("features", ["all"])
        },
        "payment": {
            "paypal_email": PAYMENT_CONFIG["paypal"]["email"],
            "cashapp_tag": PAYMENT_CONFIG["cashapp"]["tag"]
        }
    }

@api_router.put("/admin/pricing")
async def update_pricing(pricing: PricingUpdate, admin: dict = Depends(require_admin)):
    """Update subscription pricing (admin only)"""
    global SUBSCRIPTION_TIERS
    
    # Update Bronze
    SUBSCRIPTION_TIERS["bronze_monthly"]["price"] = pricing.bronze_monthly_price
    SUBSCRIPTION_TIERS["bronze_monthly"]["max_elements"] = pricing.bronze_max_elements
    SUBSCRIPTION_TIERS["bronze_monthly"]["features"] = pricing.bronze_features
    SUBSCRIPTION_TIERS["bronze_monthly"]["description"] = f"${pricing.bronze_monthly_price}/month - {pricing.bronze_max_elements} elements max"
    
    SUBSCRIPTION_TIERS["bronze_yearly"]["price"] = pricing.bronze_yearly_price
    SUBSCRIPTION_TIERS["bronze_yearly"]["max_elements"] = pricing.bronze_max_elements
    SUBSCRIPTION_TIERS["bronze_yearly"]["features"] = pricing.bronze_features
    yearly_savings = round((pricing.bronze_monthly_price * 12) - pricing.bronze_yearly_price, 0)
    SUBSCRIPTION_TIERS["bronze_yearly"]["description"] = f"${pricing.bronze_yearly_price}/year - {pricing.bronze_max_elements} elements (Save ${yearly_savings}!)"
    
    # Update Silver
    SUBSCRIPTION_TIERS["silver_monthly"]["price"] = pricing.silver_monthly_price
    SUBSCRIPTION_TIERS["silver_monthly"]["max_elements"] = pricing.silver_max_elements
    SUBSCRIPTION_TIERS["silver_monthly"]["features"] = pricing.silver_features
    SUBSCRIPTION_TIERS["silver_monthly"]["description"] = f"${pricing.silver_monthly_price}/month - {pricing.silver_max_elements} elements max"
    
    SUBSCRIPTION_TIERS["silver_yearly"]["price"] = pricing.silver_yearly_price
    SUBSCRIPTION_TIERS["silver_yearly"]["max_elements"] = pricing.silver_max_elements
    SUBSCRIPTION_TIERS["silver_yearly"]["features"] = pricing.silver_features
    yearly_savings = round((pricing.silver_monthly_price * 12) - pricing.silver_yearly_price, 0)
    SUBSCRIPTION_TIERS["silver_yearly"]["description"] = f"${pricing.silver_yearly_price}/year - {pricing.silver_max_elements} elements (Save ${yearly_savings}!)"
    
    # Update Gold
    SUBSCRIPTION_TIERS["gold_monthly"]["price"] = pricing.gold_monthly_price
    SUBSCRIPTION_TIERS["gold_monthly"]["max_elements"] = pricing.gold_max_elements
    SUBSCRIPTION_TIERS["gold_monthly"]["features"] = pricing.gold_features
    SUBSCRIPTION_TIERS["gold_monthly"]["description"] = f"${pricing.gold_monthly_price}/month - All features"
    
    SUBSCRIPTION_TIERS["gold_yearly"]["price"] = pricing.gold_yearly_price
    SUBSCRIPTION_TIERS["gold_yearly"]["max_elements"] = pricing.gold_max_elements
    SUBSCRIPTION_TIERS["gold_yearly"]["features"] = pricing.gold_features
    yearly_savings = round((pricing.gold_monthly_price * 12) - pricing.gold_yearly_price, 0)
    SUBSCRIPTION_TIERS["gold_yearly"]["description"] = f"${pricing.gold_yearly_price}/year - All features (Save ${yearly_savings}!)"
    
    # Save to database
    await db.settings.update_one(
        {"type": "pricing"},
        {"$set": {
            "type": "pricing",
            "bronze_monthly_price": pricing.bronze_monthly_price,
            "bronze_yearly_price": pricing.bronze_yearly_price,
            "bronze_max_elements": pricing.bronze_max_elements,
            "bronze_features": pricing.bronze_features,
            "silver_monthly_price": pricing.silver_monthly_price,
            "silver_yearly_price": pricing.silver_yearly_price,
            "silver_max_elements": pricing.silver_max_elements,
            "silver_features": pricing.silver_features,
            "gold_monthly_price": pricing.gold_monthly_price,
            "gold_yearly_price": pricing.gold_yearly_price,
            "gold_max_elements": pricing.gold_max_elements,
            "gold_features": pricing.gold_features,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )
    
    return {"success": True, "message": "Pricing updated successfully"}

@api_router.put("/admin/payment")
async def update_payment_config(config: PaymentConfigUpdate, admin: dict = Depends(require_admin)):
    """Update payment configuration (admin only)"""
    global PAYMENT_CONFIG
    
    PAYMENT_CONFIG["paypal"]["email"] = config.paypal_email
    PAYMENT_CONFIG["cashapp"]["tag"] = config.cashapp_tag
    
    await db.settings.update_one(
        {"type": "payment"},
        {"$set": {
            "type": "payment",
            "paypal_email": config.paypal_email,
            "cashapp_tag": config.cashapp_tag,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )
    
    return {"success": True, "message": "Payment config updated successfully"}

@api_router.get("/admin/users")
async def get_all_users(admin: dict = Depends(require_admin)):
    """Get all users (admin only)"""
    users = await db.users.find().to_list(1000)
    return [{
        "id": u["id"],
        "email": u["email"],
        "name": u["name"],
        "subscription_tier": u["subscription_tier"],
        "subscription_expires": u.get("subscription_expires"),
        "is_trial": u.get("is_trial", False),
        "created_at": u.get("created_at")
    } for u in users]

@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, role_update: UserRoleUpdate, admin: dict = Depends(require_admin)):
    """Update user role/subscription (admin only)"""
    valid_roles = ["trial", "bronze", "silver", "gold", "subadmin"]
    if role_update.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't allow changing main admin
    if user.get("email", "").lower() == ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Cannot modify main admin account")
    
    # Set expiration for paid tiers
    expires = None
    is_trial = False
    if role_update.role == "subadmin":
        expires = datetime.utcnow() + timedelta(days=36500)  # 100 years
    elif role_update.role == "trial":
        is_trial = True
    elif role_update.role in ["bronze", "silver", "gold"]:
        expires = datetime.utcnow() + timedelta(days=30)
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "subscription_tier": role_update.role,
            "subscription_expires": expires,
            "is_trial": is_trial
        }}
    )
    
    return {"success": True, "message": f"User role updated to {role_update.role}"}

@api_router.get("/admin/check")
async def check_admin_status(user: dict = Depends(require_user)):
    """Check if current user is admin or subadmin"""
    is_main_admin = user.get("email", "").lower() == ADMIN_EMAIL.lower()
    is_subadmin = user.get("subscription_tier") == "subadmin"
    
    return {
        "is_admin": is_main_admin,
        "is_subadmin": is_subadmin,
        "can_edit_settings": is_main_admin,
        "has_full_access": is_main_admin or is_subadmin
    }

class AdminCreateUser(BaseModel):
    email: str
    name: str
    password: str
    subscription_tier: str = "trial"
    trial_days: Optional[int] = Field(default=7)  # Default 7 days trial

@api_router.post("/admin/users/create")
async def admin_create_user(user_data: AdminCreateUser, admin: dict = Depends(require_admin)):
    """Create a new user (admin only)"""
    """Create a new user (admin only)"""
    # Validate email
    email = user_data.email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    # Check if user already exists
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate tier
    valid_tiers = ["trial", "bronze", "silver", "gold", "subadmin"]
    if user_data.subscription_tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {valid_tiers}")
    
    # Hash password using the existing hash_password function
    password_hashed = hash_password(user_data.password)
    
    # Set expiration based on tier
    expires = None
    is_trial = False
    trial_started = None
    
    if user_data.subscription_tier == "trial":
        is_trial = True
        trial_started = datetime.utcnow()
        # Set trial expiration based on trial_days
        trial_days = user_data.trial_days if user_data.trial_days else 7
        expires = datetime.utcnow() + timedelta(days=trial_days)
    elif user_data.subscription_tier == "subadmin":
        expires = datetime.utcnow() + timedelta(days=36500)  # 100 years
    elif user_data.subscription_tier in ["bronze", "silver", "gold"]:
        expires = datetime.utcnow() + timedelta(days=30)
    
    # Create user
    new_user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": user_data.name.strip(),
        "password": password_hashed,
        "subscription_tier": user_data.subscription_tier,
        "subscription_expires": expires,
        "is_trial": is_trial,
        "trial_started": trial_started,
        "created_at": datetime.utcnow(),
        "created_by_admin": admin["email"]
    }
    
    await db.users.insert_one(new_user)
    
    return {
        "success": True,
        "message": f"User {email} created successfully",
        "user": {
            "id": new_user["id"],
            "email": new_user["email"],
            "name": new_user["name"],
            "subscription_tier": new_user["subscription_tier"]
        }
    }

@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Delete a user (admin only)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't allow deleting main admin
    if user.get("email", "").lower() == ADMIN_EMAIL.lower():
        raise HTTPException(status_code=403, detail="Cannot delete main admin account")
    
    # Delete user's designs too
    await db.saved_designs.delete_many({"user_id": user_id})
    
    # Delete the user
    await db.users.delete_one({"id": user_id})
    
    return {"success": True, "message": f"User {user['email']} deleted successfully"}


# ==================== ADMIN DESIGNS MANAGEMENT ====================
@api_router.get("/admin/designs")
async def admin_get_all_designs(admin: dict = Depends(require_admin)):
    """Get all saved designs from all users (admin only)"""
    designs = await db.saved_designs.find().to_list(length=500)
    
    # Get user info for each design
    result = []
    for design in designs:
        user = await db.users.find_one({"id": design.get("user_id")})
        result.append({
            "id": design.get("id"),
            "name": design.get("name"),
            "user_id": design.get("user_id"),
            "user_email": user.get("email") if user else "Unknown",
            "user_name": user.get("name") if user else "Unknown",
            "created_at": design.get("created_at"),
            "updated_at": design.get("updated_at"),
            "element_count": design.get("design_data", {}).get("num_elements", 0)
        })
    
    return {"designs": result, "total": len(result)}

@api_router.delete("/admin/designs/{design_id}")
async def admin_delete_design(design_id: str, admin: dict = Depends(require_admin)):
    """Delete a specific design (admin only)"""
    design = await db.saved_designs.find_one({"id": design_id})
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    
    await db.saved_designs.delete_one({"id": design_id})
    
    return {"success": True, "message": f"Design '{design.get('name', 'Unnamed')}' deleted successfully"}

@api_router.delete("/admin/designs/bulk/all")
async def admin_delete_all_designs(admin: dict = Depends(require_admin)):
    """Delete ALL designs from all users (admin only) - use with caution!"""
    result = await db.saved_designs.delete_many({})
    
    return {"success": True, "message": f"Deleted {result.deleted_count} designs"}

@api_router.delete("/admin/designs/bulk/user/{user_id}")
async def admin_delete_user_designs(user_id: str, admin: dict = Depends(require_admin)):
    """Delete all designs from a specific user (admin only)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.saved_designs.delete_many({"user_id": user_id})
    
    return {"success": True, "message": f"Deleted {result.deleted_count} designs from {user.get('email', 'Unknown')}"}


# ==================== TUTORIAL / INTRO CONTENT ====================
DEFAULT_TUTORIAL_CONTENT = """# Welcome to SMA Antenna Calculator! 📡

## Getting Started
This app helps you design and analyze Yagi-Uda antennas for CB and Ham radio bands. Here's a quick guide to get you started.

## 1. Choose Your Band
Select your operating band (11m CB, 10m, 20m, etc.) from the dropdown at the top. The frequency will auto-fill to the band center, but you can adjust it.

## 2. Set Up Elements
- **Reflector**: The longest element, sits behind the driven element. Makes the antenna directional.
- **Driven**: The element connected to your feedline. Its length determines resonance.
- **Directors**: Shorter elements in front that increase gain and narrow the beam.

Use the element count dropdown to add more directors (up to 20 with Gold tier).

## 3. Enter Dimensions
For each element, enter:
- **Length**: Total tip-to-tip length (inches)
- **Diameter**: Element tube diameter (inches)
- **Position**: Distance from the reflector along the boom (inches)

## 4. Height & Boom
- **Height from Ground**: How high the antenna is mounted. Higher = lower take-off angle = better DX.
- **Boom Diameter**: The tube diameter of your boom. Affects gain slightly.

## 5. Auto-Tune 🔧
Hit the Auto-Tune button to automatically calculate optimal element lengths and spacing for your selected band. Great starting point!

## 6. Optimize Height 📊
Use "Optimize Height" to find the best mounting height. The optimizer considers SWR, gain, F/B ratio, take-off angle, boom length, and ground conditions.

## 7. Optional Features
- **Tapered Elements**: If your elements use multiple tube diameters (stepped taper), enable this for accurate calculations.
- **Corona Balls**: Add tip balls for high-power operation.
- **Ground Radials**: Model ground radials under the antenna.
- **Stacking**: Calculate performance for stacked antenna arrays.
- **Element Spacing**: Adjust spacing tighter or longer from optimal.

## 8. Reading Results
- **Gain (dBi)**: Higher = stronger signal in the forward direction.
- **SWR**: Lower is better. Under 1.5:1 is excellent.
- **F/B Ratio**: Higher = less signal off the back of the antenna.
- **Take-off Angle**: Lower = better for long-distance (DX) contacts.

## 9. Saving & Exporting
- Save your designs to load them later.
- Export results and height data to CSV files.

## Tips for Beginners
- Start with Auto-Tune, then fine-tune from there.
- A 3-element Yagi at 54' is a great starting point for 11m CB.
- Use Optimize Height to find the best height for your specific setup.
- The SWR Bandwidth chart shows your usable frequency range.

Happy DX'ing! 73 🎙️"""

@api_router.get("/tutorial")
async def get_tutorial():
    """Get tutorial content (public endpoint)"""
    tutorial = await db.app_settings.find_one({"key": "tutorial_content"}, {"_id": 0})
    if tutorial:
        return {"content": tutorial.get("content", DEFAULT_TUTORIAL_CONTENT)}
    return {"content": DEFAULT_TUTORIAL_CONTENT}

class UpdateTutorialRequest(BaseModel):
    content: str

@api_router.put("/admin/tutorial")
async def update_tutorial(request: UpdateTutorialRequest, admin: dict = Depends(require_admin)):
    """Update tutorial content (admin only)"""
    await db.app_settings.update_one(
        {"key": "tutorial_content"},
        {"$set": {"key": "tutorial_content", "content": request.content, "updated_at": datetime.utcnow().isoformat(), "updated_by": admin["email"]}},
        upsert=True
    )
    return {"success": True, "message": "Tutorial content updated"}

@api_router.get("/admin/tutorial")
async def admin_get_tutorial(admin: dict = Depends(require_admin)):
    """Get tutorial content for editing (admin only)"""
    tutorial = await db.app_settings.find_one({"key": "tutorial_content"}, {"_id": 0})
    if tutorial:
        return {"content": tutorial.get("content", DEFAULT_TUTORIAL_CONTENT), "updated_at": tutorial.get("updated_at"), "updated_by": tutorial.get("updated_by")}
    return {"content": DEFAULT_TUTORIAL_CONTENT, "updated_at": None, "updated_by": None}


# ==================== DESIGNER INFO / ABOUT ME ====================
DEFAULT_DESIGNER_INFO = """# SMA Antenna Calculator
## Designed & Developed by Tommy Falls

### About the Designer
With over 25 years of experience in CB and amateur radio, I've dedicated my career to understanding antenna design and RF engineering. This app was born from the need for a reliable, easy-to-use tool that gives real-world results — not just theoretical numbers.

### My Background
- Licensed amateur radio operator
- Specializing in Yagi-Uda antenna design for 11-meter CB band
- Hands-on builder with dozens of custom antenna installations
- Passionate about helping fellow operators get the best signal possible

### About This App
The SMA Antenna Calculator is a professional-grade tool designed for both beginners and experienced antenna builders. Every calculation is based on real-world data and validated against actual antenna measurements.

**Key Features:**
- Real-time antenna parameter calculations (SWR, Gain, F/B, Beamwidth)
- Auto-Tune with realistic boom lengths based on actual Yagi designs
- Height optimization considering boom length, elements, ground conditions
- Element spacing control (Tight/Normal/Long)
- Taper element support for stepped-diameter designs
- Corona ball calculations for high-power setups
- Ground radial modeling
- Stacking analysis for multi-antenna arrays
- CSV export for documentation

### Contact & Support
Have questions, suggestions, or want to share your build? I'd love to hear from you!

- Email: fallstommy@gmail.com
- Built with pride for the amateur radio community

### Version
SMA Antenna Calculator v2.0
© 2026 Tommy Falls. All rights reserved.

73 & Good DX! 🎙️📡"""

@api_router.get("/designer-info")
async def get_designer_info():
    """Get designer info content (public endpoint)"""
    info = await db.app_settings.find_one({"key": "designer_info"}, {"_id": 0})
    if info:
        return {"content": info.get("content", DEFAULT_DESIGNER_INFO)}
    return {"content": DEFAULT_DESIGNER_INFO}

@api_router.put("/admin/designer-info")
async def update_designer_info(request: UpdateTutorialRequest, admin: dict = Depends(require_admin)):
    """Update designer info content (admin only)"""
    await db.app_settings.update_one(
        {"key": "designer_info"},
        {"$set": {"key": "designer_info", "content": request.content, "updated_at": datetime.utcnow().isoformat(), "updated_by": admin["email"]}},
        upsert=True
    )
    return {"success": True, "message": "Designer info updated"}

@api_router.get("/admin/designer-info")
async def admin_get_designer_info(admin: dict = Depends(require_admin)):
    """Get designer info for editing (admin only)"""
    info = await db.app_settings.find_one({"key": "designer_info"}, {"_id": 0})
    if info:
        return {"content": info.get("content", DEFAULT_DESIGNER_INFO), "updated_at": info.get("updated_at"), "updated_by": info.get("updated_by")}
    return {"content": DEFAULT_DESIGNER_INFO, "updated_at": None, "updated_by": None}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
