from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'antenna-calc-secret-key-2024')
JWT_ALGORITHM = "HS256"

# Admin email
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'fallstommy@gmail.com')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

# Band definitions
BAND_DEFINITIONS = {
    "17m": {"name": "17m", "center": 18.118, "start": 18.068, "end": 18.168, "channel_spacing_khz": 5},
    "15m": {"name": "15m", "center": 21.225, "start": 21.0, "end": 21.45, "channel_spacing_khz": 5},
    "12m": {"name": "12m", "center": 24.94, "start": 24.89, "end": 24.99, "channel_spacing_khz": 5},
    "11m_cb": {"name": "11m CB", "center": 27.185, "start": 26.965, "end": 27.405, "channel_spacing_khz": 10},
    "10m": {"name": "10m", "center": 28.5, "start": 28.0, "end": 29.7, "channel_spacing_khz": 10},
    "6m": {"name": "6m", "center": 51.0, "start": 50.0, "end": 54.0, "channel_spacing_khz": 20},
    "2m": {"name": "2m", "center": 146.0, "start": 144.0, "end": 148.0, "channel_spacing_khz": 20},
    "1.25m": {"name": "1.25m", "center": 223.5, "start": 222.0, "end": 225.0, "channel_spacing_khz": 25},
    "70cm": {"name": "70cm", "center": 435.0, "start": 420.0, "end": 450.0, "channel_spacing_khz": 25},
}

# Free-space gain model (dBi) - calibrated to real-world Yagi data at 27 MHz
FREE_SPACE_GAIN_DBI = {
    2: 6.2, 3: 8.2, 4: 10.0, 5: 10.8, 6: 12.0, 7: 12.5, 8: 13.0,
    9: 13.5, 10: 14.0, 11: 14.3, 12: 15.0, 13: 15.3, 14: 15.6,
    15: 16.0, 16: 16.3, 17: 16.5, 18: 16.8, 19: 17.0, 20: 17.2,
}

# Standard boom lengths (inches) at 11m (27.185 MHz)
STANDARD_BOOM_11M_IN = {
    2: 47, 3: 138, 4: 217, 5: 295, 6: 394, 7: 472, 8: 551, 9: 640,
    10: 728, 11: 827, 12: 925, 13: 1024, 14: 1122, 15: 1221,
    16: 1323, 17: 1425, 18: 1528, 19: 1630, 20: 1732,
}
REF_WAVELENGTH_11M_IN = 434.2  # 11m at 27.185 MHz in inches

# Default Subscription Tiers
DEFAULT_SUBSCRIPTION_TIERS = {
    "trial": {
        "name": "Free Trial", "price": 0, "max_elements": 3,
        "duration_hours": 1, "features": ["basic_calc", "swr_meter"],
        "description": "1 hour free trial with basic features"
    },
    "bronze_monthly": {
        "name": "Bronze Monthly", "price": 39.99, "max_elements": 5,
        "duration_days": 30, "features": ["basic_calc", "swr_meter", "band_selection"],
        "description": "$39.99/month - Basic antenna calculations"
    },
    "bronze_yearly": {
        "name": "Bronze Yearly", "price": 400.00, "max_elements": 5,
        "duration_days": 365, "features": ["basic_calc", "swr_meter", "band_selection"],
        "description": "$400/year - Basic antenna calculations (Save $80!)"
    },
    "silver_monthly": {
        "name": "Silver Monthly", "price": 59.99, "max_elements": 10,
        "duration_days": 30, "features": ["basic_calc", "swr_meter", "band_selection", "auto_tune", "save_designs"],
        "description": "$59.99/month - Auto-tune & save designs"
    },
    "silver_yearly": {
        "name": "Silver Yearly", "price": 675.00, "max_elements": 10,
        "duration_days": 365, "features": ["basic_calc", "swr_meter", "band_selection", "auto_tune", "save_designs"],
        "description": "$675/year - Auto-tune & save designs (Save $45!)"
    },
    "gold_monthly": {
        "name": "Gold Monthly", "price": 99.99, "max_elements": 20,
        "duration_days": 30, "features": ["all"],
        "description": "$99.99/month - All features"
    },
    "gold_yearly": {
        "name": "Gold Yearly", "price": 1050.00, "max_elements": 20,
        "duration_days": 365, "features": ["all"],
        "description": "$1050/year - All features (Save $150!)"
    },
    "subadmin": {
        "name": "Sub-Admin", "price": 0, "max_elements": 20,
        "duration_days": 36500, "features": ["all"],
        "description": "Sub-Admin full access"
    },
    "admin": {
        "name": "Admin", "price": 0, "max_elements": 20,
        "duration_days": 36500, "features": ["all"],
        "description": "Admin full access"
    }
}

SUBSCRIPTION_TIERS = DEFAULT_SUBSCRIPTION_TIERS.copy()

DEFAULT_PAYMENT_CONFIG = {
    "paypal": {"email": "tfcp2011@gmail.com", "enabled": True},
    "cashapp": {"tag": "$tfcp2011", "enabled": True}
}
PAYMENT_CONFIG = DEFAULT_PAYMENT_CONFIG.copy()


async def load_settings_from_db():
    """Load pricing and payment settings from database."""
    global SUBSCRIPTION_TIERS, PAYMENT_CONFIG

    settings = await db.settings.find_one({"type": "pricing"})
    if settings:
        if "bronze_monthly" in SUBSCRIPTION_TIERS:
            for base in ("bronze", "silver", "gold"):
                for period in ("monthly", "yearly"):
                    key = f"{base}_{period}"
                    SUBSCRIPTION_TIERS[key]["price"] = settings.get(f"{base}_{period}_price", SUBSCRIPTION_TIERS[key]["price"])
                    SUBSCRIPTION_TIERS[key]["max_elements"] = settings.get(f"{base}_max_elements", SUBSCRIPTION_TIERS[key]["max_elements"])
                    SUBSCRIPTION_TIERS[key]["features"] = settings.get(f"{base}_features", SUBSCRIPTION_TIERS[key]["features"])

    payment_settings = await db.settings.find_one({"type": "payment"})
    if payment_settings:
        PAYMENT_CONFIG["paypal"]["email"] = payment_settings.get("paypal_email", "tfcp2011@gmail.com")
        PAYMENT_CONFIG["cashapp"]["tag"] = payment_settings.get("cashapp_tag", "$tfcp2011")
