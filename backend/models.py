from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Union
from datetime import datetime
import uuid


# ── Admin Models ──
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
    role: str


# ── User Models ──
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


# ── Status Models ──
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str


# ── Antenna Element Models ──
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
    layout: str = Field(default="line")
    num_antennas: int = Field(default=2, ge=2, le=8)
    spacing: float = Field(default=20, gt=0)
    spacing_unit: str = Field(default="ft")
    h_spacing: Optional[float] = Field(default=None)
    h_spacing_unit: str = Field(default="ft")

class GroundRadialConfig(BaseModel):
    enabled: bool = Field(default=False)
    ground_type: str = Field(default="average")
    wire_diameter: float = Field(default=0.5)
    num_radials: int = Field(default=8, ge=1, le=128)


# ── Antenna Input/Output ──
class AntennaInput(BaseModel):
    num_elements: int = Field(..., ge=2, le=20)
    elements: List[ElementDimension] = Field(...)
    height_from_ground: float = Field(..., gt=0)
    height_unit: str = Field(default="ft")
    boom_diameter: float = Field(..., gt=0)
    boom_unit: str = Field(default="inches")
    band: str = Field(default="11m_cb")
    frequency_mhz: Optional[float] = Field(default=None)
    antenna_orientation: str = Field(default="horizontal")
    dual_active: bool = Field(default=False)
    dual_selected_beam: str = Field(default="horizontal")
    feed_type: str = Field(default="direct")
    gamma_rod_dia: Optional[float] = Field(default=None)
    gamma_rod_spacing: Optional[float] = Field(default=None)
    gamma_bar_pos: Optional[float] = Field(default=None)
    gamma_element_gap: Optional[float] = Field(default=None)
    gamma_cap_pf: Optional[float] = Field(default=None)
    gamma_tube_od: Optional[float] = Field(default=None)
    hairpin_rod_dia: Optional[float] = Field(default=None)
    hairpin_rod_spacing: Optional[float] = Field(default=None)
    hairpin_bar_pos: Optional[float] = Field(default=None)
    hairpin_boom_gap: Optional[float] = Field(default=None)
    stacking: Optional[StackingConfig] = Field(default=None)
    taper: Optional[TaperConfig] = Field(default=None)
    corona_balls: Optional[CoronaBallConfig] = Field(default=None)
    ground_radials: Optional[GroundRadialConfig] = Field(default=None)
    boom_grounded: bool = Field(default=True)
    boom_mount: Optional[str] = Field(default=None)
    coax_type: str = Field(default="ldf5-50a")
    coax_length_ft: float = Field(default=100.0, ge=0)
    transmit_power_watts: float = Field(default=500.0, ge=0)

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
    use_reflector: bool = Field(default=True)
    boom_lock_enabled: bool = Field(default=False)
    max_boom_length: Optional[float] = Field(default=None)
    spacing_lock_enabled: bool = Field(default=False)
    locked_positions: Optional[List[float]] = Field(default=None)
    spacing_mode: str = Field(default="normal")
    spacing_level: float = Field(default=1.0)
    antenna_orientation: str = Field(default="horizontal")
    dual_active: bool = Field(default=False)
    feed_type: str = Field(default="direct")
    close_driven: Union[str, bool] = Field(default=False)
    far_driven: Union[str, bool] = Field(default=False)
    close_dir1: Union[str, bool] = Field(default=False)
    far_dir1: Union[str, bool] = Field(default=False)
    close_dir2: Union[str, bool] = Field(default=False)
    far_dir2: Union[str, bool] = Field(default=False)
    element_diameter: Optional[float] = Field(default=0.5)

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
    reflection_coefficient: Optional[float] = None
    return_loss_db: Optional[float] = None
    mismatch_loss_db: Optional[float] = None
    reflected_power_100w: Optional[float] = None
    reflected_power_1kw: Optional[float] = None
    forward_power_100w: Optional[float] = None
    forward_power_1kw: Optional[float] = None
    impedance_high: Optional[float] = None
    impedance_low: Optional[float] = None
    coax_loss_db: Optional[float] = None
    coax_info: Optional[dict] = None
    power_at_antenna_watts: Optional[float] = None
    reflected_power_watts: Optional[float] = None
    forward_power_watts: Optional[float] = None
    takeoff_angle: Optional[float] = None
    takeoff_angle_description: Optional[str] = None
    height_performance: Optional[str] = None
    ground_radials_info: Optional[dict] = None
    noise_level: Optional[str] = None
    noise_description: Optional[str] = None
    feed_type: Optional[str] = None
    matching_info: Optional[dict] = None
    dual_polarity_info: Optional[dict] = None
    wind_load: Optional[dict] = None
    boom_correction_info: Optional[dict] = None
    resonant_freq_mhz: Optional[float] = None
    elevation_pattern: Optional[list] = None
    smith_chart_data: Optional[list] = None

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


# ── Optimizer Models ──
class StackingOptimizeRequest(BaseModel):
    num_elements: int = Field(..., ge=2, le=20)
    elements: List[ElementDimension]
    height_from_ground: float = Field(..., gt=0)
    height_unit: str = Field(default="ft")
    boom_diameter: float = Field(..., gt=0)
    boom_unit: str = Field(default="inches")
    band: str = Field(default="11m_cb")
    frequency_mhz: Optional[float] = Field(default=None)
    antenna_orientation: str = Field(default="horizontal")
    dual_active: bool = Field(default=False)
    dual_selected_beam: str = Field(default="horizontal")
    feed_type: str = Field(default="gamma")
    stacking_orientation: str = Field(default="vertical")
    stacking_layout: str = Field(default="line")
    num_antennas: int = Field(default=2, ge=2, le=8)
    min_spacing_ft: int = Field(default=15)
    max_spacing_ft: int = Field(default=40)
    taper: Optional[TaperConfig] = Field(default=None)
    corona_balls: Optional[CoronaBallConfig] = Field(default=None)
    ground_radials: Optional[GroundRadialConfig] = Field(default=None)

class StackingOptimizeResult(BaseModel):
    best_spacing_ft: float
    best_gain_dbi: float
    best_gain_increase: float
    best_beamwidth_h: float
    best_beamwidth_v: float
    best_h_spacing_ft: Optional[float] = None
    all_results: List[dict]

class HeightOptimizeRequest(BaseModel):
    num_elements: int
    elements: List[ElementDimension]
    boom_diameter: float
    boom_unit: str = "inches"
    band: str = "11m_cb"
    frequency_mhz: Optional[float] = None
    min_height: int = 10
    max_height: int = 100
    step: int = 1
    ground_radials: Optional[GroundRadialConfig] = None

class HeightOptimizeOutput(BaseModel):
    optimal_height: int
    optimal_swr: float
    optimal_gain: float
    optimal_fb_ratio: float
    heights_tested: List[dict]


# ── Saved Designs ──
class SavedDesign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    description: Optional[str] = ""
    design_data: dict
    spacing_state: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SaveDesignRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    design_data: dict
    spacing_state: Optional[dict] = None

class SaveDesignResponse(BaseModel):
    id: str
    name: str
    message: str


# ── Auth Models ──
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class AdminCreateUser(BaseModel):
    email: str
    name: str
    password: str
    subscription_tier: str = "trial"
    trial_days: Optional[int] = Field(default=7)


# ── Discount Models ──
class DiscountCreate(BaseModel):
    code: str
    discount_type: str = "percentage"
    value: float
    applies_to: str = "all"
    tiers: List[str] = []
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None
    user_emails: List[str] = []


# ── Notification Models ──
class SendUpdateEmail(BaseModel):
    subject: str
    message: str
    expo_url: Optional[str] = None
    download_link: Optional[str] = None
    send_to: str = "all"

class UpdateTutorialRequest(BaseModel):
    content: str



# ── Gamma Match Designer ──
class GammaDesignerRequest(BaseModel):
    num_elements: int = Field(..., ge=2, le=20)
    driven_element_length_in: float = Field(..., gt=0)
    frequency_mhz: float = Field(default=27.185)
    feedpoint_impedance: Optional[float] = Field(default=None, description="Override feedpoint R if known")
    custom_tube_od: Optional[float] = Field(default=None, description="Custom tube OD in inches")
    custom_rod_od: Optional[float] = Field(default=None, description="Custom rod OD in inches")
    custom_rod_spacing: Optional[float] = Field(default=None, description="Custom rod-element spacing in inches")
    custom_teflon_length: Optional[float] = Field(default=None, description="Custom teflon sleeve length in inches")
    custom_tube_length: Optional[float] = Field(default=None, description="Custom tube length in inches")
