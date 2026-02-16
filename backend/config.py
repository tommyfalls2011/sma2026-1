from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ── Database ──
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

_store_client = AsyncIOMotorClient(os.environ.get("STORE_MONGO_URL"))
store_db = _store_client["sma_store"]

# ── JWT ──
JWT_SECRET = os.environ.get('JWT_SECRET', 'antenna-calc-secret-key-2024')
JWT_ALGORITHM = "HS256"

# ── Admin / Email ──
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'fallstommy@gmail.com')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

# ── Stripe / Store ──
NC_TAX_RATE = 0.075
SHIPPING_RATES = {"standard": 15.00, "priority": 25.00, "express": 45.00}
GITHUB_REPO = "tommyfalls2011/sma2026-1"

# ── Uploads ──
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# ── Subscription Tiers ──
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

# ── Band Definitions ──
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

# ── Free-Space Gain Model (dBi) ──
FREE_SPACE_GAIN_DBI = {
    2: 6.2, 3: 8.2, 4: 10.0, 5: 10.8, 6: 12.0, 7: 12.5, 8: 13.0,
    9: 13.5, 10: 14.0, 11: 14.3, 12: 15.0, 13: 15.3, 14: 15.6,
    15: 16.0, 16: 16.3, 17: 16.5, 18: 16.8, 19: 17.0, 20: 17.2,
}

# Standard boom lengths (inches) at 11m (27.185 MHz)
STANDARD_BOOM_11M_IN = {
    2: 47, 3: 138, 4: 217, 5: 295, 6: 394, 7: 472, 8: 551,
    9: 640, 10: 728, 11: 827, 12: 925, 13: 1024, 14: 1122,
    15: 1221, 16: 1323, 17: 1425, 18: 1528, 19: 1630, 20: 1732,
}
REF_WAVELENGTH_11M_IN = 434.2

# ── Default Content ──
DEFAULT_TUTORIAL_CONTENT = """# Welcome to SMA Antenna Calculator!

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

## 5. Auto-Tune
Hit the Auto-Tune button to automatically calculate optimal element lengths and spacing for your selected band. Great starting point!

## 6. Optimize Height
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

Happy DX'ing! 73"""

DEFAULT_DESIGNER_INFO = """# SMA Antenna Calculator
## Designed & Developed by Tommy Falls

### About the Designer
With over 25 years of experience in CB and amateur radio, I've dedicated my career to understanding antenna design and RF engineering. This app was born from the need for a reliable, easy-to-use tool that gives real-world results - not just theoretical numbers.

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
(c) 2026 Tommy Falls. All rights reserved.

73 & Good DX!"""
