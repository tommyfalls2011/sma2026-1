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


# Antenna Input Model
class AntennaInput(BaseModel):
    num_elements: int = Field(..., ge=1, le=50, description="Number of antenna elements")
    height_from_ground: float = Field(..., gt=0, description="Height from ground")
    boom_diameter: float = Field(..., gt=0, description="Boom diameter")
    element_size: float = Field(..., gt=0, description="Size of elements")
    tapered: bool = Field(default=False, description="Whether elements are tapered")
    frequency_mhz: float = Field(default=144.0, gt=0, description="Operating frequency in MHz")
    unit: str = Field(default="meters", description="Unit of measurement: meters or inches")


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
    input_summary: dict


class CalculationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    inputs: dict
    outputs: dict


def convert_to_meters(value: float, unit: str) -> float:
    """Convert input value to meters for calculations."""
    if unit == "inches":
        return value * 0.0254
    return value


def calculate_antenna_parameters(input_data: AntennaInput) -> AntennaOutput:
    """Calculate antenna parameters based on input specifications."""
    
    # Convert all measurements to meters for calculations
    height_m = convert_to_meters(input_data.height_from_ground, input_data.unit)
    boom_dia_m = convert_to_meters(input_data.boom_diameter, input_data.unit)
    element_size_m = convert_to_meters(input_data.element_size, input_data.unit)
    
    # Calculate wavelength in meters
    c = 299792458  # Speed of light in m/s
    wavelength = c / (input_data.frequency_mhz * 1e6)
    
    n = input_data.num_elements
    
    # Height in wavelengths
    height_wavelengths = height_m / wavelength
    
    # Boom length approximation (based on number of elements)
    boom_length_wavelengths = 0.25 * (n - 1)  # Approximate spacing of 0.25λ
    
    # === GAIN CALCULATION (dBi) ===
    # Yagi-Uda gain formula approximation
    # Base gain for dipole is 2.15 dBi
    # Each additional director adds approximately 1-1.5 dB
    if n == 1:
        gain_dbi = 2.15  # Simple dipole
    elif n == 2:
        gain_dbi = 4.5  # Dipole with reflector
    else:
        # Approximate gain using empirical formula for Yagi antennas
        gain_dbi = 2.15 + 2.5 * math.log10(n) + 1.5 * (n - 2) * 0.6
        
    # Tapering effect on gain
    if input_data.tapered:
        gain_dbi += 0.3  # Slight improvement with tapered elements
    
    # Height effect on gain (ground reflection)
    if 0.5 <= height_wavelengths <= 1.0:
        gain_dbi += 2.0  # Optimal height range
    elif 0.25 <= height_wavelengths < 0.5:
        gain_dbi += 1.0
    
    gain_dbi = round(min(gain_dbi, 20.0), 2)  # Cap at realistic maximum
    
    # === SWR CALCULATION ===
    # SWR depends on matching - we'll estimate based on boom diameter ratio
    element_to_boom_ratio = element_size_m / boom_dia_m if boom_dia_m > 0 else 10
    
    if 5 <= element_to_boom_ratio <= 20:
        base_swr = 1.2  # Well-matched
    elif 3 <= element_to_boom_ratio < 5 or 20 < element_to_boom_ratio <= 30:
        base_swr = 1.5
    else:
        base_swr = 2.0
    
    # Tapered elements improve SWR
    if input_data.tapered:
        base_swr *= 0.9
    
    swr = round(max(1.0, min(base_swr, 3.0)), 2)
    
    # === FRONT-TO-BACK RATIO ===
    # F/B ratio increases with more elements
    if n == 1:
        fb_ratio = 0  # Dipole has no F/B
    elif n == 2:
        fb_ratio = 10  # Basic 2-element has ~10dB
    else:
        fb_ratio = 10 + 3 * math.log2(n - 1)
        
    if input_data.tapered:
        fb_ratio += 2  # Tapering improves F/B
    
    fb_ratio = round(min(fb_ratio, 35), 1)  # Cap at realistic maximum
    
    # === BEAMWIDTH CALCULATION ===
    # E-plane beamwidth decreases with more elements
    if n == 1:
        beamwidth = 78  # Dipole
    elif n == 2:
        beamwidth = 65
    else:
        # Approximate beamwidth formula
        beamwidth = 78 / (1 + 0.15 * (n - 1))
    
    beamwidth = round(max(beamwidth, 20), 1)
    
    # === BANDWIDTH CALCULATION ===
    # Bandwidth as percentage of center frequency
    # More elements generally narrow bandwidth
    if n <= 2:
        bandwidth_percent = 8
    else:
        bandwidth_percent = 8 / (1 + 0.1 * (n - 2))
    
    if input_data.tapered:
        bandwidth_percent *= 1.2  # Tapered elements improve bandwidth
    
    # Larger element size to wavelength ratio improves bandwidth
    element_wavelength_ratio = element_size_m / wavelength
    if element_wavelength_ratio > 0.01:
        bandwidth_percent *= 1.1
    
    bandwidth_mhz = round(input_data.frequency_mhz * bandwidth_percent / 100, 2)
    
    # === MULTIPLICATION FACTOR ===
    # Power multiplication compared to isotropic
    multiplication_factor = round(10 ** (gain_dbi / 10), 2)
    
    # === ANTENNA EFFICIENCY ===
    # Based on element construction and matching
    base_efficiency = 0.95  # Assuming good construction
    
    # SWR affects efficiency
    swr_loss = (swr - 1) / (swr + 1)
    efficiency_from_swr = 1 - swr_loss ** 2
    
    # Boom diameter affects ohmic losses
    if boom_dia_m > 0.02:  # > 20mm boom
        conductor_efficiency = 0.98
    else:
        conductor_efficiency = 0.95
    
    antenna_efficiency = round(base_efficiency * efficiency_from_swr * conductor_efficiency * 100, 1)
    
    # === FAR FIELD PATTERN ===
    # Generate radiation pattern data (simplified)
    far_field_pattern = []
    for angle in range(0, 361, 10):
        theta = math.radians(angle)
        
        # Simplified pattern based on number of elements
        if n == 1:
            # Dipole pattern (figure-8)
            magnitude = abs(math.cos(theta)) * 100
        else:
            # Yagi pattern (directional)
            main_lobe = math.cos(theta) ** 2
            if main_lobe < 0:
                main_lobe = 0
            
            # Back lobe (reduced by F/B ratio)
            back_attenuation = 10 ** (-fb_ratio / 20)
            if 90 < angle < 270:
                magnitude = main_lobe * back_attenuation * 100
            else:
                magnitude = main_lobe * 100
            
            # Side lobes
            if 60 < angle < 120 or 240 < angle < 300:
                magnitude *= 0.3
        
        far_field_pattern.append({
            "angle": angle,
            "magnitude": round(max(magnitude, 1), 1)
        })
    
    # Generate descriptions
    swr_desc = "Excellent" if swr < 1.5 else ("Good" if swr < 2.0 else "Fair")
    fb_desc = f"{fb_ratio} dB front-to-back isolation"
    beamwidth_desc = f"{beamwidth}° half-power beamwidth"
    bandwidth_desc = f"±{bandwidth_mhz/2:.1f} MHz from center frequency"
    gain_desc = f"{multiplication_factor}x power gain over isotropic"
    mult_desc = f"Effective radiated power multiplier"
    eff_desc = "Excellent" if antenna_efficiency > 90 else ("Good" if antenna_efficiency > 80 else "Fair")
    
    return AntennaOutput(
        swr=swr,
        swr_description=f"{swr_desc} match - {swr}:1",
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
        input_summary={
            "num_elements": input_data.num_elements,
            "height_from_ground": input_data.height_from_ground,
            "boom_diameter": input_data.boom_diameter,
            "element_size": input_data.element_size,
            "tapered": input_data.tapered,
            "frequency_mhz": input_data.frequency_mhz,
            "unit": input_data.unit,
            "wavelength_m": round(wavelength, 3)
        }
    )


# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Antenna Calculator API"}


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
