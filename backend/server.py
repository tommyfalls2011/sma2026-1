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
# Channel spacing in kHz for each band
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


# Element Input Model
class ElementDimension(BaseModel):
    element_type: str  # "reflector", "driven", "director"
    length: float = Field(..., gt=0, description="Element length")
    diameter: float = Field(..., gt=0, description="Element diameter")
    position: float = Field(default=0, ge=0, description="Position from reflector")


# Stacking Configuration
class StackingConfig(BaseModel):
    enabled: bool = Field(default=False, description="Enable antenna stacking")
    orientation: str = Field(default="vertical", description="vertical or horizontal")
    num_antennas: int = Field(default=2, ge=2, le=8, description="Number of stacked antennas")
    spacing: float = Field(default=20, gt=0, description="Spacing between antennas")
    spacing_unit: str = Field(default="ft", description="ft or inches")


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
    stacking: Optional[StackingConfig] = Field(default=None, description="Stacking configuration")


class SwrPoint(BaseModel):
    frequency: float
    swr: float
    channel: Optional[int] = None


class AntennaOutput(BaseModel):
    swr: float
    swr_description: str
    fb_ratio: float
    fb_ratio_description: str
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
    # Stacking results
    stacking_enabled: bool
    stacking_info: Optional[dict] = None
    stacked_gain_dbi: Optional[float] = None
    stacked_pattern: Optional[List[dict]] = None


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


def convert_spacing_to_meters(value: float, unit: str) -> float:
    """Convert stacking spacing to meters."""
    if unit == "ft":
        return value * 0.3048
    elif unit == "inches":
        return value * 0.0254
    return value


def calculate_swr_at_frequency(freq: float, center_freq: float, bandwidth: float, min_swr: float = 1.1) -> float:
    """Calculate SWR at a given frequency based on distance from center."""
    freq_offset = abs(freq - center_freq)
    half_bandwidth = bandwidth / 2
    
    if freq_offset == 0:
        return min_swr
    
    normalized_offset = freq_offset / half_bandwidth if half_bandwidth > 0 else 0
    swr = min_swr + (normalized_offset ** 1.5) * (3.0 - min_swr)
    
    return min(swr, 10.0)


def calculate_stacking_gain(base_gain: float, num_antennas: int, spacing_wavelengths: float, orientation: str) -> tuple:
    """Calculate gain increase from stacking antennas."""
    # Theoretical gain increase for stacking
    # Perfect stacking of N antennas adds 10*log10(N) dB
    # But real-world is typically less due to coupling losses
    
    theoretical_gain = 10 * math.log10(num_antennas)
    
    # Efficiency factor based on spacing (optimal around 0.625 to 0.75 wavelength)
    if 0.5 <= spacing_wavelengths <= 1.0:
        if 0.6 <= spacing_wavelengths <= 0.8:
            efficiency = 0.95  # Near optimal spacing
        else:
            efficiency = 0.85
    elif spacing_wavelengths < 0.5:
        efficiency = 0.6 + (spacing_wavelengths / 0.5) * 0.25  # Reduced due to coupling
    else:
        efficiency = 0.8  # Wider spacing, some pattern degradation
    
    actual_gain_increase = theoretical_gain * efficiency
    stacked_gain = base_gain + actual_gain_increase
    
    return round(stacked_gain, 2), round(actual_gain_increase, 2)


def calculate_stacked_beamwidth(base_beamwidth: float, num_antennas: int, spacing_wavelengths: float) -> float:
    """Calculate reduced beamwidth from stacking."""
    # Stacking narrows the beam in the stacking plane
    # Approximate formula: new_beamwidth = base / sqrt(N) for optimal spacing
    
    narrowing_factor = math.sqrt(num_antennas)
    
    # Adjust for non-optimal spacing
    if spacing_wavelengths < 0.5:
        narrowing_factor *= 0.7  # Less narrowing due to coupling
    elif spacing_wavelengths > 1.0:
        narrowing_factor *= 0.9  # Grating lobes reduce effectiveness
    
    new_beamwidth = base_beamwidth / narrowing_factor
    return round(max(new_beamwidth, 15), 1)  # Minimum practical beamwidth


def generate_stacked_pattern(base_pattern: List[dict], num_antennas: int, spacing_wavelengths: float, orientation: str) -> List[dict]:
    """Generate radiation pattern for stacked array."""
    stacked_pattern = []
    
    for point in base_pattern:
        angle = point["angle"]
        base_mag = point["magnitude"]
        theta_rad = math.radians(angle)
        
        # Array factor calculation
        if orientation == "vertical":
            # Vertical stacking affects elevation pattern (we show azimuth, so less effect)
            # But side lobes appear
            array_factor = 1.0
            if 60 < angle < 120 or 240 < angle < 300:
                # Side lobe regions get some additional lobes
                array_factor = 0.7 + 0.3 * abs(math.sin(num_antennas * math.pi * spacing_wavelengths * math.sin(theta_rad)))
        else:
            # Horizontal stacking directly affects azimuth pattern
            psi = 2 * math.pi * spacing_wavelengths * math.cos(theta_rad)
            if abs(math.sin(psi / 2)) < 0.001:
                array_factor = 1.0
            else:
                array_factor = abs(math.sin(num_antennas * psi / 2) / (num_antennas * math.sin(psi / 2)))
        
        new_mag = base_mag * array_factor
        
        # Normalize to keep main lobe at 100
        stacked_pattern.append({
            "angle": angle,
            "magnitude": round(max(new_mag, 1), 1)
        })
    
    # Normalize pattern so max is 100
    max_mag = max(p["magnitude"] for p in stacked_pattern)
    if max_mag > 0:
        for p in stacked_pattern:
            p["magnitude"] = round(p["magnitude"] / max_mag * 100, 1)
    
    return stacked_pattern


def calculate_antenna_parameters(input_data: AntennaInput) -> AntennaOutput:
    """Calculate antenna parameters based on input specifications."""
    
    # Get band info
    band_info = BAND_DEFINITIONS.get(input_data.band, BAND_DEFINITIONS["11m_cb"])
    center_freq = input_data.frequency_mhz if input_data.frequency_mhz else band_info["center"]
    channel_spacing = band_info.get("channel_spacing_khz", 10) / 1000  # Convert to MHz
    
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
        gain_dbi = 4.5
    elif n == 3:
        gain_dbi = 7.0
    else:
        gain_dbi = 7.0 + 2.5 * math.log10(n - 2) + 1.2 * (n - 3) * 0.5
    
    if tapered:
        gain_dbi += 0.3
    
    if 0.5 <= height_wavelengths <= 1.0:
        gain_dbi += 2.0
    elif 0.25 <= height_wavelengths < 0.5:
        gain_dbi += 1.0
    elif height_wavelengths > 1.0:
        gain_dbi += 1.5
    
    gain_dbi = round(min(gain_dbi, 18.0), 2)
    
    # === SWR CALCULATION ===
    if driven:
        driven_length_m = convert_element_to_meters(driven.length, "inches")
        ideal_length = wavelength / 2 * 0.95
        length_ratio = driven_length_m / ideal_length if ideal_length > 0 else 1
        
        if 0.95 <= length_ratio <= 1.05:
            base_swr = 1.2
        elif 0.9 <= length_ratio < 0.95 or 1.05 < length_ratio <= 1.1:
            base_swr = 1.5
        else:
            base_swr = 2.0
    else:
        base_swr = 1.5
    
    if boom_dia_m > 0.03:
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
    
    # === BEAMWIDTH CALCULATION (horizontal and vertical) ===
    if n == 2:
        beamwidth_h = 65
        beamwidth_v = 70
    elif n == 3:
        beamwidth_h = 55
        beamwidth_v = 60
    else:
        beamwidth_h = 55 / (1 + 0.08 * (n - 3))
        beamwidth_v = 60 / (1 + 0.06 * (n - 3))
    
    beamwidth_h = round(max(beamwidth_h, 25), 1)
    beamwidth_v = round(max(beamwidth_v, 30), 1)
    
    # === BANDWIDTH CALCULATION ===
    if n <= 3:
        bandwidth_percent = 5
    else:
        bandwidth_percent = 5 / (1 + 0.05 * (n - 3))
    
    if tapered:
        bandwidth_percent *= 1.3
    
    if avg_element_dia > 0.005:
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
    
    # === SWR CURVE (30 channels below to 20 channels above) ===
    swr_curve = []
    channels_below = 30
    channels_above = 20
    total_channels = channels_below + channels_above + 1
    
    for i in range(-channels_below, channels_above + 1):
        freq = center_freq + (i * channel_spacing)
        swr_at_freq = calculate_swr_at_frequency(freq, center_freq, bandwidth_mhz, swr)
        swr_curve.append({
            "frequency": round(freq, 4),
            "swr": round(swr_at_freq, 2),
            "channel": i  # Relative channel (0 = center)
        })
    
    # Calculate usable bandwidth at different SWR thresholds
    usable_1_5 = sum(1 for p in swr_curve if p["swr"] <= 1.5) * channel_spacing
    usable_2_0 = sum(1 for p in swr_curve if p["swr"] <= 2.0) * channel_spacing
    
    usable_1_5 = round(usable_1_5, 3)
    usable_2_0 = round(usable_2_0, 3)
    
    # === FAR FIELD PATTERN ===
    far_field_pattern = []
    for angle in range(0, 361, 5):  # 5 degree resolution
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
    
    # === STACKING CALCULATIONS ===
    stacking_enabled = False
    stacking_info = None
    stacked_gain_dbi = None
    stacked_pattern = None
    
    if input_data.stacking and input_data.stacking.enabled:
        stacking_enabled = True
        stacking = input_data.stacking
        
        # Convert spacing to wavelengths
        spacing_m = convert_spacing_to_meters(stacking.spacing, stacking.spacing_unit)
        spacing_wavelengths = spacing_m / wavelength
        
        # Calculate stacked gain
        stacked_gain_dbi, gain_increase = calculate_stacking_gain(
            gain_dbi, stacking.num_antennas, spacing_wavelengths, stacking.orientation
        )
        
        # Calculate new beamwidth in stacking plane
        if stacking.orientation == "vertical":
            new_beamwidth_v = calculate_stacked_beamwidth(beamwidth_v, stacking.num_antennas, spacing_wavelengths)
            new_beamwidth_h = beamwidth_h  # Horizontal beamwidth unchanged
        else:
            new_beamwidth_h = calculate_stacked_beamwidth(beamwidth_h, stacking.num_antennas, spacing_wavelengths)
            new_beamwidth_v = beamwidth_v  # Vertical beamwidth unchanged
        
        # Generate stacked pattern
        stacked_pattern = generate_stacked_pattern(
            far_field_pattern, stacking.num_antennas, spacing_wavelengths, stacking.orientation
        )
        
        # Optimal spacing recommendation
        optimal_spacing_m = wavelength * 0.65  # 5/8 wavelength is often optimal
        optimal_spacing_ft = optimal_spacing_m / 0.3048
        
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
            "optimal_spacing_ft": round(optimal_spacing_ft, 1),
            "optimal_spacing_wavelengths": 0.65,
            "total_height_ft": round((stacking.num_antennas - 1) * stacking.spacing + input_data.height_from_ground, 1) if stacking.orientation == "vertical" and stacking.spacing_unit == "ft" else None,
            "total_width_ft": round((stacking.num_antennas - 1) * stacking.spacing, 1) if stacking.orientation == "horizontal" and stacking.spacing_unit == "ft" else None,
        }
        
        # Update beamwidths for stacked config
        beamwidth_h = new_beamwidth_h
        beamwidth_v = new_beamwidth_v
    
    # Generate descriptions
    swr_desc = "Excellent" if swr < 1.3 else ("Very Good" if swr < 1.5 else ("Good" if swr < 2.0 else "Fair"))
    fb_desc = f"{fb_ratio} dB front-to-back isolation"
    beamwidth_desc = f"H: {beamwidth_h}° / V: {beamwidth_v}° half-power beamwidth"
    bandwidth_desc = f"±{bandwidth_mhz/2:.3f} MHz from center ({usable_2_0:.3f} MHz at 2:1 SWR)"
    
    final_gain = stacked_gain_dbi if stacked_gain_dbi else gain_dbi
    final_mult = round(10 ** (final_gain / 10), 2)
    gain_desc = f"{final_mult}x power gain over isotropic"
    mult_desc = f"Effective radiated power multiplier"
    eff_desc = "Excellent" if antenna_efficiency > 90 else ("Good" if antenna_efficiency > 80 else "Fair")
    
    return AntennaOutput(
        swr=swr,
        swr_description=f"{swr_desc} match - {swr}:1 at center",
        fb_ratio=fb_ratio,
        fb_ratio_description=fb_desc,
        beamwidth_h=beamwidth_h,
        beamwidth_v=beamwidth_v,
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
        swr_curve=swr_curve,
        usable_bandwidth_1_5=usable_1_5,
        usable_bandwidth_2_0=usable_2_0,
        center_frequency=center_freq,
        band_info={**band_info, "channel_spacing_khz": band_info.get("channel_spacing_khz", 10)},
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
        },
        stacking_enabled=stacking_enabled,
        stacking_info=stacking_info,
        stacked_gain_dbi=stacked_gain_dbi,
        stacked_pattern=stacked_pattern
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
