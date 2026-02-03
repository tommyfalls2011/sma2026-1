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
        "name": "Trial",
        "price": 0,
        "max_elements": 3,
        "duration_hours": 1,
        "features": ["basic_calc", "swr_meter"],
        "description": "1 hour free trial with basic features"
    },
    "bronze": {
        "name": "Bronze",
        "price": 29.99,
        "max_elements": 3,
        "duration_days": 30,
        "features": ["basic_calc", "swr_meter", "band_selection"],
        "description": "$29.99/month - 3 elements max"
    },
    "silver": {
        "name": "Silver",
        "price": 49.99,
        "max_elements": 7,
        "duration_days": 30,
        "features": ["basic_calc", "swr_meter", "band_selection", "stacking", "taper"],
        "description": "$49.99/month - 7 elements max"
    },
    "gold": {
        "name": "Gold",
        "price": 69.99,
        "max_elements": 20,
        "duration_days": 30,
        "features": ["all"],
        "description": "$69.99/month - Full access"
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
    bronze_price: float
    bronze_max_elements: int
    silver_price: float
    silver_max_elements: int
    gold_price: float
    gold_max_elements: int

class PaymentConfigUpdate(BaseModel):
    paypal_email: str
    cashapp_tag: str

class UserRoleUpdate(BaseModel):
    role: str  # 'trial', 'bronze', 'silver', 'gold', 'subadmin'


# ==================== HELPER FUNCTIONS ====================
async def load_settings_from_db():
    """Load pricing and payment settings from database"""
    global SUBSCRIPTION_TIERS, PAYMENT_CONFIG
    
    settings = await db.settings.find_one({"type": "pricing"})
    if settings:
        SUBSCRIPTION_TIERS["bronze"]["price"] = settings.get("bronze_price", 29.99)
        SUBSCRIPTION_TIERS["bronze"]["max_elements"] = settings.get("bronze_max_elements", 3)
        SUBSCRIPTION_TIERS["silver"]["price"] = settings.get("silver_price", 49.99)
        SUBSCRIPTION_TIERS["silver"]["max_elements"] = settings.get("silver_max_elements", 7)
        SUBSCRIPTION_TIERS["gold"]["price"] = settings.get("gold_price", 69.99)
        SUBSCRIPTION_TIERS["gold"]["max_elements"] = settings.get("gold_max_elements", 20)
        # Update descriptions
        SUBSCRIPTION_TIERS["bronze"]["description"] = f"${SUBSCRIPTION_TIERS['bronze']['price']}/month - {SUBSCRIPTION_TIERS['bronze']['max_elements']} elements max"
        SUBSCRIPTION_TIERS["silver"]["description"] = f"${SUBSCRIPTION_TIERS['silver']['price']}/month - {SUBSCRIPTION_TIERS['silver']['max_elements']} elements max"
        SUBSCRIPTION_TIERS["gold"]["description"] = f"${SUBSCRIPTION_TIERS['gold']['price']}/month - Full access"
    
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
            return False, SUBSCRIPTION_TIERS.get(tier), "Subscription expired"
    
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
    
    base_gain_bonus = 0.3 * num_tapers
    bandwidth_mult = 1.0 + (0.15 * num_tapers)
    swr_mult = 1.0 - (0.04 * num_tapers)
    fb_bonus = 1.5 * num_tapers
    fs_bonus = 1.0 * num_tapers
    
    if sections:
        total_taper_ratio = 0
        for section in sections:
            if section.start_diameter > 0:
                ratio = section.end_diameter / section.start_diameter
                total_taper_ratio += (1 - ratio)
        avg_taper = total_taper_ratio / len(sections) if sections else 0
        if 0.3 <= avg_taper <= 0.6:
            base_gain_bonus += 0.5
            bandwidth_mult += 0.1
    
    return {
        "gain_bonus": round(base_gain_bonus, 2),
        "bandwidth_mult": round(bandwidth_mult, 2),
        "swr_mult": round(max(0.7, swr_mult), 2),
        "fb_bonus": round(fb_bonus, 1),
        "fs_bonus": round(fs_bonus, 1),
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
    if n == 2: gain_dbi = 5.5
    elif n == 3: gain_dbi = 8.5
    elif n == 4: gain_dbi = 10.5
    elif n == 5: gain_dbi = 12.0
    elif n == 6: gain_dbi = 13.5
    elif n == 7: gain_dbi = 14.5
    else: gain_dbi = 8.5 + 3.0 * math.log10(n - 2) + 1.5 * (n - 3) * 0.55
    
    # Without reflector, gain is reduced by ~1.5-2 dB
    if not has_reflector:
        gain_dbi -= 1.5
    
    gain_dbi += taper_effects["gain_bonus"]
    gain_dbi += corona_effects.get("gain_effect", 0)
    
    if 0.5 <= height_wavelengths <= 1.0: gain_dbi += 2.5
    elif 0.25 <= height_wavelengths < 0.5: gain_dbi += 1.5
    elif 1.0 < height_wavelengths <= 1.5: gain_dbi += 2.0
    elif height_wavelengths > 1.5: gain_dbi += 1.5
    
    if boom_dia_m > 0.05: gain_dbi += 0.3
    elif boom_dia_m > 0.03: gain_dbi += 0.2
    
    gain_dbi = round(min(gain_dbi, 45.0), 2)
    
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
        
        # 8 radial directions
        radial_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        
        # Ground effect on antenna performance
        ground_improvement = {
            "wet": {"swr_improvement": 0.05, "gain_bonus": 1.5, "efficiency_bonus": 8},
            "average": {"swr_improvement": 0.03, "gain_bonus": 0.8, "efficiency_bonus": 5},
            "dry": {"swr_improvement": 0.01, "gain_bonus": 0.3, "efficiency_bonus": 2}
        }
        g_bonus = ground_improvement.get(ground_type, ground_improvement["average"])
        
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
            "radial_directions": radial_directions[:ground_radials.num_radials],
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
    
    if use_reflector:
        # Optimal reflector: ~5% longer than driven, 0.2 wavelength behind
        reflector_length = round(driven_length * 1.05, 1)
        reflector_spacing = round(wavelength_in * 0.2, 1)
        
        # Add reflector
        elements.append({
            "element_type": "reflector",
            "length": reflector_length,
            "diameter": 0.5,
            "position": 0
        })
        notes.append(f"Reflector: {reflector_length}\" (5% longer than driven)")
        
        # Add driven element
        elements.append({
            "element_type": "driven",
            "length": driven_length,
            "diameter": 0.5,
            "position": reflector_spacing
        })
        notes.append(f"Driven: {driven_length}\" at {reflector_spacing}\" from reflector")
        
        # Add directors
        num_directors = n - 2
        current_position = reflector_spacing
    else:
        # No reflector mode - driven element at position 0
        elements.append({
            "element_type": "driven",
            "length": driven_length,
            "diameter": 0.5,
            "position": 0
        })
        notes.append(f"Driven: {driven_length}\" at position 0 (no reflector)")
        
        # All remaining elements are directors
        num_directors = n - 1
        current_position = 0
    
    # Add directors (each ~3% shorter, spaced 0.2-0.25 wavelength)
    for i in range(num_directors):
        director_spacing = round(wavelength_in * (0.2 + i * 0.02), 1)  # Gradually increase spacing
        current_position += director_spacing
        director_length = round(driven_length * (0.95 - i * 0.02), 1)  # Each ~2% shorter
        
        elements.append({
            "element_type": "director",
            "length": director_length,
            "diameter": 0.5,
            "position": current_position
        })
        notes.append(f"Director {i+1}: {director_length}\" at {current_position}\"")
    
    # Predict performance (slightly worse without reflector)
    base_predicted_swr = 1.05 if request.taper and request.taper.enabled else 1.1
    predicted_swr = base_predicted_swr if use_reflector else base_predicted_swr + 0.1
    
    # Use safe calculation that handles n=2 case
    if n <= 7:
        base_gain = {2: 5.5, 3: 8.5, 4: 10.5, 5: 12.0, 6: 13.5, 7: 14.5}.get(n, 8.5)
    else:
        base_gain = 8.5 + 3.0 * math.log10(max(n - 2, 1))
    
    if not use_reflector:
        base_gain -= 1.5  # Less gain without reflector
    if request.taper and request.taper.enabled:
        base_gain += 0.3 * request.taper.num_tapers
    predicted_gain = round(base_gain + 2.0, 1)  # Add height gain estimate
    
    # Safe F/B calculation
    if n <= 5:
        predicted_fb = {2: 14, 3: 20, 4: 24, 5: 26}.get(n, 14)
    else:
        predicted_fb = 20 + 3 * math.log2(max(n - 2, 1))
    
    if not use_reflector:
        predicted_fb -= 8  # Worse F/B without reflector
    if request.taper and request.taper.enabled:
        predicted_fb += 1.5 * request.taper.num_tapers
    
    notes.append(f"")
    notes.append(f"Wavelength at {center_freq} MHz: {round(wavelength_in, 1)}\"")
    notes.append(f"Total boom length: ~{round(current_position, 1)}\"")
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

class HeightOptimizeOutput(BaseModel):
    optimal_height: int
    optimal_swr: float
    optimal_gain: float
    optimal_fb_ratio: float
    heights_tested: List[dict]

@api_router.post("/optimize-height", response_model=HeightOptimizeOutput)
async def optimize_height(request: HeightOptimizeRequest):
    """Test heights from min to max and find best overall performance (SWR, Gain, F/B)."""
    best_height = request.min_height
    best_score = -999.0  # We'll maximize a combined score
    best_swr = 999.0
    best_gain = 0.0
    best_fb = 0.0
    heights_tested = []
    
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
            corona_balls=None
        )
        
        # Calculate for this height
        result = await calculate_antenna(calc_input)
        swr = result.swr
        gain = result.gain_dbi
        fb = result.fb_ratio
        
        # Calculate a combined performance score
        # Lower SWR is better (penalty for high SWR)
        # Higher gain is better
        # Higher F/B is better
        swr_score = max(0, 3 - swr) * 10  # SWR 1.0 = 20 pts, SWR 2.0 = 10 pts, SWR 3.0+ = 0 pts
        gain_score = gain * 2  # Gain directly contributes
        fb_score = fb * 0.5  # F/B contributes
        
        total_score = swr_score + gain_score + fb_score
        
        heights_tested.append({
            "height": height, 
            "swr": round(swr, 2),
            "gain": round(gain, 2),
            "fb_ratio": round(fb, 1),
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
            "price": SUBSCRIPTION_TIERS["bronze"]["price"],
            "max_elements": SUBSCRIPTION_TIERS["bronze"]["max_elements"]
        },
        "silver": {
            "price": SUBSCRIPTION_TIERS["silver"]["price"],
            "max_elements": SUBSCRIPTION_TIERS["silver"]["max_elements"]
        },
        "gold": {
            "price": SUBSCRIPTION_TIERS["gold"]["price"],
            "max_elements": SUBSCRIPTION_TIERS["gold"]["max_elements"]
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
    
    # Update in-memory
    SUBSCRIPTION_TIERS["bronze"]["price"] = pricing.bronze_price
    SUBSCRIPTION_TIERS["bronze"]["max_elements"] = pricing.bronze_max_elements
    SUBSCRIPTION_TIERS["bronze"]["description"] = f"${pricing.bronze_price}/month - {pricing.bronze_max_elements} elements max"
    
    SUBSCRIPTION_TIERS["silver"]["price"] = pricing.silver_price
    SUBSCRIPTION_TIERS["silver"]["max_elements"] = pricing.silver_max_elements
    SUBSCRIPTION_TIERS["silver"]["description"] = f"${pricing.silver_price}/month - {pricing.silver_max_elements} elements max"
    
    SUBSCRIPTION_TIERS["gold"]["price"] = pricing.gold_price
    SUBSCRIPTION_TIERS["gold"]["max_elements"] = pricing.gold_max_elements
    SUBSCRIPTION_TIERS["gold"]["description"] = f"${pricing.gold_price}/month - Full access"
    
    # Save to database
    await db.settings.update_one(
        {"type": "pricing"},
        {"$set": {
            "type": "pricing",
            "bronze_price": pricing.bronze_price,
            "bronze_max_elements": pricing.bronze_max_elements,
            "silver_price": pricing.silver_price,
            "silver_max_elements": pricing.silver_max_elements,
            "gold_price": pricing.gold_price,
            "gold_max_elements": pricing.gold_max_elements,
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

@api_router.post("/admin/users/create")
async def admin_create_user(user_data: AdminCreateUser, admin: dict = Depends(require_admin)):
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
    await db.designs.delete_many({"user_id": user_id})
    
    # Delete the user
    await db.users.delete_one({"id": user_id})
    
    return {"success": True, "message": f"User {user['email']} deleted successfully"}


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
