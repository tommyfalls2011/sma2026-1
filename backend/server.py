from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import math


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str


# Ham/CB Band definitions (frequency in MHz)
BAND_DEFINITIONS = {
    "11m_cb": {"name": "11m CB Band", "center": 27.185, "start": 26.965, "end": 27.405},
    "10m": {"name": "10m Ham Band", "center": 28.5, "start": 28.0, "end": 29.7},
    "12m": {"name": "12m Ham Band", "center": 24.94, "start": 24.89, "end": 24.99},
    "15m": {"name": "15m Ham Band", "center": 21.225, "start": 21.0, "end": 21.45},
    "17m": {"name": "17m Ham Band", "center": 18.118, "start": 18.068, "end": 18.168},
    "20m": {"name": "20m Ham Band", "center": 14.175, "start": 14.0, "end": 14.35},
    "40m": {"name": "40m Ham Band", "center": 7.15, "start": 7.0, "end": 7.3},
    "6m": {"name": "6m Ham Band", "center": 51.0, "start": 50.0, "end": 54.0},
    "2m": {"name": "2m Ham Band", "center": 146.0, "start": 144.0, "end": 148.0},
    "70cm": {"name": "70cm Ham Band", "center": 435.0, "start": 420.0, "end": 450.0},
}


# Element Input Model
class ElementDimension(BaseModel):
    element_type: str  # "reflector", "driven", "director"
    length: float = Field(..., gt=0, description="Element length")
    diameter: float = Field(..., gt=0, description="Element diameter")
    position: float = Field(default=0, ge=0, description="Position from reflector")


# Antenna Input Model
class AntennaInput(BaseModel):
    num_elements: int = Field(..., ge=2, le=20, description="Number of antenna elements")
    elements: List[ElementDimension] = Field(..., description="Element dimensions")
    height_from_ground: float = Field(..., gt=0, description="Height from ground")
    height_unit: str = Field(default="ft", description="Height unit: ft or inches")
    boom_diameter: float = Field(..., gt=0, description="Boom diameter")
    boom_unit: str = Field(default="inches", description="Boom unit: mm or inches")
    band: str = Field(default="11m_cb", description="Operating band")
    frequency_mhz: Optional[float] = Field(default=None, description="Custom frequency in MHz")


class SwrPoint(BaseModel):
    frequency: float
    swr: float


class AntennaOutput(BaseModel):
    swr: float
    swr_description: str
    fb_ratio: float
    fb_ratio_description: str
    beamwidth: float
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
    swr_curve: List[SwrPoint]
    usable_bandwidth_1_5: float
    usable_bandwidth_2_0: float
    center_frequency: float
    band_info: dict
    input_summary: dict


class CalculationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    inputs: dict
    outputs: dict


def convert_height_to_meters(value: float, unit: str) -> float:
    """Convert height to meters."""
    if unit == "ft":
        return value * 0.3048
    elif unit == "inches":
        return value * 0.0254
    return value


def convert_boom_to_meters(value: float, unit: str) -> float:
    """Convert boom diameter to meters."""
    if unit == "mm":
        return value * 0.001
    elif unit == "inches":
        return value * 0.0254
    return value


def convert_element_to_meters(value: float, unit: str) -> float:
    """Convert element dimensions to meters."""
    if unit == "inches":
        return value * 0.0254
    return value


def calculate_swr_at_frequency(freq: float, center_freq: float, bandwidth: float, min_swr: float = 1.1) -> float:
    """Calculate SWR at a given frequency based on distance from center."""
    freq_offset = abs(freq - center_freq)
    half_bandwidth = bandwidth / 2
    
    if freq_offset == 0:
        return min_swr
    
    # SWR increases as we move away from center frequency
    # Using a quadratic model for realistic SWR curve
    normalized_offset = freq_offset / half_bandwidth if half_bandwidth > 0 else 0
    
    # SWR formula: starts at min_swr at center, increases quadratically
    swr = min_swr + (normalized_offset ** 1.5) * (3.0 - min_swr)
    
    return min(swr, 10.0)  # Cap at 10:1


def calculate_antenna_parameters(input_data: AntennaInput) -> AntennaOutput:
    """Calculate antenna parameters based on input specifications."""
    
    # Get band info
    band_info = BAND_DEFINITIONS.get(input_data.band, BAND_DEFINITIONS["11m_cb"])
    center_freq = input_data.frequency_mhz if input_data.frequency_mhz else band_info["center"]
    
    # Convert all measurements to meters for calculations
    height_m = convert_height_to_meters(input_data.height_from_ground, input_data.height_unit)
    boom_dia_m = convert_boom_to_meters(input_data.boom_diameter, input_data.boom_unit)
    
    # Calculate wavelength in meters
    c = 299792458  # Speed of light in m/s
    wavelength = c / (center_freq * 1e6)
    
    n = input_data.num_elements
    
    # Height in wavelengths
    height_wavelengths = height_m / wavelength
    
    # Analyze elements
    reflector = None
    driven = None
    directors = []
    
    for elem in input_data.elements:
        if elem.element_type == "reflector":
            reflector = elem
        elif elem.element_type == "driven":
            driven = elem
        elif elem.element_type == "director":
            directors.append(elem)
    
    # Calculate average element size (in inches, convert to meters)
    avg_element_dia = sum(convert_element_to_meters(e.diameter, "inches") for e in input_data.elements) / len(input_data.elements)
    
    # Check if elements are tapered (different diameters)
    element_dias = [e.diameter for e in input_data.elements]
    tapered = len(set(element_dias)) > 1
    
    # === GAIN CALCULATION (dBi) ===
    if n == 2:
        gain_dbi = 4.5  # Dipole with reflector
    elif n == 3:
        gain_dbi = 7.0  # 3 element yagi
    else:
        # Approximate gain using empirical formula for Yagi antennas
        gain_dbi = 7.0 + 2.5 * math.log10(n - 2) + 1.2 * (n - 3) * 0.5
    
    # Tapering effect on gain
    if tapered:
        gain_dbi += 0.3
    
    # Height effect on gain (ground reflection)
    if 0.5 <= height_wavelengths <= 1.0:
        gain_dbi += 2.0
    elif 0.25 <= height_wavelengths < 0.5:
        gain_dbi += 1.0
    elif height_wavelengths > 1.0:
        gain_dbi += 1.5
    
    gain_dbi = round(min(gain_dbi, 18.0), 2)  # Cap at realistic maximum
    
    # === SWR CALCULATION ===
    # Base SWR depends on element ratios and matching
    if driven:
        driven_length_m = convert_element_to_meters(driven.length, "inches")
        # Check if driven element is close to half wavelength
        ideal_length = wavelength / 2 * 0.95  # 95% of half wavelength
        length_ratio = driven_length_m / ideal_length if ideal_length > 0 else 1
        
        if 0.95 <= length_ratio <= 1.05:
            base_swr = 1.2  # Well tuned
        elif 0.9 <= length_ratio < 0.95 or 1.05 < length_ratio <= 1.1:
            base_swr = 1.5
        else:
            base_swr = 2.0
    else:
        base_swr = 1.5
    
    # Boom diameter affects matching
    if boom_dia_m > 0.03:  # > 30mm boom
        base_swr *= 0.95
    
    if tapered:
        base_swr *= 0.9
    
    swr = round(max(1.0, min(base_swr, 3.0)), 2)
    
    # === FRONT-TO-BACK RATIO ===
    if n == 2:
        fb_ratio = 12
    elif n == 3:
        fb_ratio = 18
    else:
        fb_ratio = 18 + 2.5 * math.log2(n - 2)
    
    if tapered:
        fb_ratio += 2
    
    fb_ratio = round(min(fb_ratio, 35), 1)
    
    # === BEAMWIDTH CALCULATION ===
    if n == 2:
        beamwidth = 65
    elif n == 3:
        beamwidth = 55
    else:
        beamwidth = 55 / (1 + 0.08 * (n - 3))
    
    beamwidth = round(max(beamwidth, 25), 1)
    
    # === BANDWIDTH CALCULATION ===
    # Bandwidth as percentage of center frequency
    if n <= 3:
        bandwidth_percent = 5
    else:
        bandwidth_percent = 5 / (1 + 0.05 * (n - 3))
    
    if tapered:
        bandwidth_percent *= 1.3  # Tapered elements improve bandwidth
    
    # Larger element diameter improves bandwidth
    if avg_element_dia > 0.005:  # > 5mm
        bandwidth_percent *= 1.15
    
    bandwidth_mhz = round(center_freq * bandwidth_percent / 100, 3)
    
    # === MULTIPLICATION FACTOR ===
    multiplication_factor = round(10 ** (gain_dbi / 10), 2)
    
    # === ANTENNA EFFICIENCY ===
    base_efficiency = 0.95
    swr_loss = (swr - 1) / (swr + 1)
    efficiency_from_swr = 1 - swr_loss ** 2
    
    if boom_dia_m > 0.025:
        conductor_efficiency = 0.98
    else:
        conductor_efficiency = 0.95
    
    antenna_efficiency = round(base_efficiency * efficiency_from_swr * conductor_efficiency * 100, 1)
    
    # === SWR CURVE ===
    swr_curve = []
    freq_range = bandwidth_mhz * 2.5  # Show wider range than usable bandwidth
    freq_step = freq_range / 50
    
    for i in range(51):
        freq = center_freq - freq_range/2 + (i * freq_step)
        swr_at_freq = calculate_swr_at_frequency(freq, center_freq, bandwidth_mhz, swr)
        swr_curve.append(SwrPoint(frequency=round(freq, 4), swr=round(swr_at_freq, 2)))
    
    # Calculate usable bandwidth at different SWR thresholds
    usable_1_5 = 0
    usable_2_0 = 0
    
    for point in swr_curve:
        if point.swr <= 1.5:
            usable_1_5 += freq_step
        if point.swr <= 2.0:
            usable_2_0 += freq_step
    
    usable_1_5 = round(usable_1_5, 3)
    usable_2_0 = round(usable_2_0, 3)
    
    # === FAR FIELD PATTERN ===
    far_field_pattern = []
    for angle in range(0, 361, 10):
        theta = math.radians(angle)
        
        if n == 2:
            main_lobe = (math.cos(theta) + 0.3) / 1.3
            if main_lobe < 0:
                main_lobe = 0
            magnitude = main_lobe ** 2 * 100
        else:
            main_lobe = math.cos(theta) ** 2
            if main_lobe < 0:
                main_lobe = 0
            
            back_attenuation = 10 ** (-fb_ratio / 20)
            if 90 < angle < 270:
                magnitude = main_lobe * back_attenuation * 100
            else:
                magnitude = main_lobe * 100
            
            if 60 < angle < 120 or 240 < angle < 300:
                magnitude *= 0.25
        
        far_field_pattern.append({
            "angle": angle,
            "magnitude": round(max(magnitude, 1), 1)
        })
    
    # Generate descriptions
    swr_desc = "Excellent" if swr < 1.3 else ("Very Good" if swr < 1.5 else ("Good" if swr < 2.0 else "Fair"))
    fb_desc = f"{fb_ratio} dB front-to-back isolation"
    beamwidth_desc = f"{beamwidth}° half-power beamwidth"
    bandwidth_desc = f"±{bandwidth_mhz/2:.3f} MHz from center ({usable_2_0:.3f} MHz at 2:1 SWR)"
    gain_desc = f"{multiplication_factor}x power gain over isotropic"
    mult_desc = f"Effective radiated power multiplier"
    eff_desc = "Excellent" if antenna_efficiency > 90 else ("Good" if antenna_efficiency > 80 else "Fair")
    
    return AntennaOutput(
        swr=swr,
        swr_description=f"{swr_desc} match - {swr}:1 at center",
        fb_ratio=fb_ratio,
        fb_ratio_description=fb_desc,
        beamwidth=beamwidth,
        beamwidth_description=beamwidth_desc,
        bandwidth=bandwidth_mhz,
        bandwidth_description=bandwidth_desc,
        gain_dbi=gain_dbi,
        gain_description=gain_desc,
        multiplication_factor=multiplication_factor,
        multiplication_description=mult_desc,
        antenna_efficiency=antenna_efficiency,
        efficiency_description=f"{eff_desc} - {antenna_efficiency}% efficient",
        far_field_pattern=far_field_pattern,
        swr_curve=[p.dict() for p in swr_curve],
        usable_bandwidth_1_5=usable_1_5,
        usable_bandwidth_2_0=usable_2_0,
        center_frequency=center_freq,
        band_info=band_info,
        input_summary={
            "num_elements": input_data.num_elements,
            "height_from_ground": input_data.height_from_ground,
            "height_unit": input_data.height_unit,
            "boom_diameter": input_data.boom_diameter,
            "boom_unit": input_data.boom_unit,
            "band": input_data.band,
            "center_frequency_mhz": center_freq,
            "wavelength_m": round(wavelength, 3),
            "wavelength_ft": round(wavelength * 3.28084, 2)
        }
    )


@api_router.get("/")
async def root():
    return {"message": "Antenna Calculator API"}


@api_router.get("/bands")
async def get_bands():
    """Get available band definitions."""
    return BAND_DEFINITIONS


@api_router.post("/calculate", response_model=AntennaOutput)
async def calculate_antenna(input_data: AntennaInput):
    """Calculate antenna parameters from input specifications."""
    result = calculate_antenna_parameters(input_data)
    
    # Save calculation to database
    record = CalculationRecord(
        inputs=input_data.dict(),
        outputs=result.dict()
    )
    await db.calculations.insert_one(record.dict())
    
    return result


@api_router.get("/history", response_model=List[CalculationRecord])
async def get_calculation_history():
    """Get history of calculations."""
    records = await db.calculations.find().sort("timestamp", -1).limit(20).to_list(20)
    return [CalculationRecord(**record) for record in records]


@api_router.delete("/history")
async def clear_history():
    """Clear calculation history."""
    result = await db.calculations.delete_many({})
    return {"deleted_count": result.deleted_count}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
