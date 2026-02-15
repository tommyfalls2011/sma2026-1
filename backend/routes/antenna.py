"""Antenna calculation, auto-tune, and optimization routes."""
import math
from fastapi import APIRouter, Body
from fastapi.responses import Response

from config import BAND_DEFINITIONS, db
from models import (
    AntennaInput, AntennaOutput, AutoTuneRequest, AutoTuneOutput,
    StackingOptimizeRequest, StackingOptimizeResult,
    HeightOptimizeRequest, HeightOptimizeOutput,
    CalculationRecord,
)
from services.physics import (
    calculate_antenna_parameters, auto_tune_antenna,
    calculate_stacking_gain, calculate_stacked_beamwidth,
    convert_height_to_meters,
)
from services.pdf_service import generate_spec_sheet_pdf

router = APIRouter()


@router.post("/calculate", response_model=AntennaOutput)
async def calculate_antenna(input_data: AntennaInput):
    result = calculate_antenna_parameters(input_data)
    record = CalculationRecord(inputs=input_data.dict(), outputs=result.dict())
    await db.calculations.insert_one(record.dict())
    return result


@router.post("/auto-tune", response_model=AutoTuneOutput)
async def auto_tune(request: AutoTuneRequest):
    return auto_tune_antenna(request)


@router.post("/optimize-stacking", response_model=StackingOptimizeResult)
async def optimize_stacking(request: StackingOptimizeRequest):
    """Sweep spacing and find best stacked gain."""
    band_info = BAND_DEFINITIONS.get(request.band, BAND_DEFINITIONS["11m_cb"])
    center_freq = request.frequency_mhz if request.frequency_mhz else band_info["center"]
    wavelength = 299792458 / (center_freq * 1e6)

    base_input = AntennaInput(
        num_elements=request.num_elements, elements=request.elements,
        height_from_ground=request.height_from_ground, height_unit=request.height_unit,
        boom_diameter=request.boom_diameter, boom_unit=request.boom_unit,
        band=request.band, frequency_mhz=request.frequency_mhz,
        antenna_orientation=request.antenna_orientation,
        dual_active=request.dual_active, dual_selected_beam=request.dual_selected_beam,
        feed_type=request.feed_type, stacking=None,
        taper=request.taper, corona_balls=request.corona_balls,
        ground_radials=request.ground_radials,
    )
    base_result = calculate_antenna_parameters(base_input)
    base_gain = base_result.gain_dbi
    base_bw_h = base_result.beamwidth_h
    base_bw_v = base_result.beamwidth_v

    best_score = -999
    best_spacing = request.min_spacing_ft
    best_gain = base_gain
    best_increase = 0
    best_bw_h = base_bw_h
    best_bw_v = base_bw_v
    best_h_spacing = None
    all_results = []
    is_quad = request.stacking_layout == "quad"

    for spacing_ft in range(request.min_spacing_ft, request.max_spacing_ft + 1):
        spacing_m = spacing_ft * 0.3048
        spacing_wl = spacing_m / wavelength

        if is_quad:
            v_gain, v_inc = calculate_stacking_gain(base_gain, 2, spacing_wl, "vertical")
            h_gain, h_inc = calculate_stacking_gain(v_gain, 2, spacing_wl, "horizontal")
            total_gain = h_gain
            total_increase = round(total_gain - base_gain, 2)
            new_bw_v = calculate_stacked_beamwidth(base_bw_v, 2, spacing_wl)
            new_bw_h = calculate_stacked_beamwidth(base_bw_h, 2, spacing_wl)
        else:
            total_gain, total_increase = calculate_stacking_gain(base_gain, request.num_antennas, spacing_wl, request.stacking_orientation)
            if request.stacking_orientation == "vertical":
                new_bw_v = calculate_stacked_beamwidth(base_bw_v, request.num_antennas, spacing_wl)
                new_bw_h = base_bw_h
            else:
                new_bw_h = calculate_stacked_beamwidth(base_bw_h, request.num_antennas, spacing_wl)
                new_bw_v = base_bw_v

        score = total_gain
        if spacing_wl < 0.5: score -= 3
        elif spacing_wl > 2.0: score -= 0.5
        if request.stacking_orientation == "vertical" or is_quad:
            wl_distance = abs(spacing_wl - 1.0)
            if wl_distance < 0.2: score += 0.5
            elif wl_distance < 0.4: score += 0.2

        spacing_status = "Too close" if spacing_wl < 0.25 else ("Mutual coupling risk" if spacing_wl < 0.5 else ("Good" if spacing_wl < 0.8 else ("Optimal (\u22481\u03bb)" if spacing_wl < 1.2 else ("Good" if spacing_wl < 2.0 else "Wide"))))

        all_results.append({
            "spacing_ft": spacing_ft, "spacing_wl": round(spacing_wl, 3),
            "stacked_gain_dbi": round(total_gain, 2), "gain_increase": round(total_increase, 2),
            "beamwidth_h": round(new_bw_h, 1), "beamwidth_v": round(new_bw_v, 1),
            "spacing_status": spacing_status, "score": round(score, 2),
        })

        if score > best_score:
            best_score = score
            best_spacing = spacing_ft
            best_gain = round(total_gain, 2)
            best_increase = round(total_increase, 2)
            best_bw_h = round(new_bw_h, 1)
            best_bw_v = round(new_bw_v, 1)
            if is_quad:
                best_h_spacing = spacing_ft

    return StackingOptimizeResult(
        best_spacing_ft=best_spacing, best_gain_dbi=best_gain,
        best_gain_increase=best_increase, best_beamwidth_h=best_bw_h,
        best_beamwidth_v=best_bw_v, best_h_spacing_ft=best_h_spacing,
        all_results=all_results,
    )


@router.post("/optimize-height", response_model=HeightOptimizeOutput)
async def optimize_height(request: HeightOptimizeRequest):
    """Find best mounting height considering SWR, Gain, F/B, Take-off Angle."""
    best_height = request.min_height
    best_score = -999.0
    best_swr = 999.0
    best_gain = 0.0
    best_fb = 0.0
    heights_tested = []

    band_info = BAND_DEFINITIONS.get(request.band, BAND_DEFINITIONS["11m_cb"])
    center_freq = request.frequency_mhz if request.frequency_mhz else band_info["center"]
    c = 299792458
    wavelength = c / (center_freq * 1e6)

    positions = [e.position for e in request.elements]
    boom_length_in = max(positions) - min(positions) if positions else 0
    boom_length_m = boom_length_in * 0.0254
    boom_wavelengths = boom_length_m / wavelength if wavelength > 0 else 0
    n = request.num_elements

    ground_type = "average"
    has_radials = False
    if request.ground_radials and request.ground_radials.enabled:
        ground_type = request.ground_radials.ground_type
        has_radials = True
    ground_angle_adj = {"wet": -3, "average": 0, "dry": 5}.get(ground_type, 0)

    for height in range(request.min_height, request.max_height + 1, request.step):
        calc_input = AntennaInput(
            num_elements=request.num_elements, elements=request.elements,
            height_from_ground=height, height_unit="ft",
            boom_diameter=request.boom_diameter, boom_unit=request.boom_unit,
            band=request.band, frequency_mhz=request.frequency_mhz,
            stacking=None, taper=None, corona_balls=None,
            ground_radials=request.ground_radials
        )
        result = calculate_antenna_parameters(calc_input)
        swr = result.swr
        gain = result.gain_dbi
        fb = result.fb_ratio
        efficiency = result.antenna_efficiency

        height_m = height * 0.3048
        height_wavelengths = height_m / wavelength
        if height_wavelengths >= 0.25:
            takeoff_angle = math.degrees(math.asin(min(1.0, 1 / (4 * height_wavelengths))))
        else:
            takeoff_angle = 70 + (0.25 - height_wavelengths) * 80
        takeoff_angle = round(max(5, min(90, takeoff_angle + ground_angle_adj)), 1)

        # Height-adaptive scoring
        if height_wavelengths < 0.25: eff_weight, toa_weight = 3.0, 0.3
        elif height_wavelengths < 0.5:
            eff_weight = 2.5 - (height_wavelengths - 0.25) * 4.0
            toa_weight = 0.5 + (height_wavelengths - 0.25) * 3.0
        elif height_wavelengths < 1.0: eff_weight, toa_weight = 1.0, 1.5
        else: eff_weight, toa_weight = 0.5, 2.0

        if swr <= 1.5: swr_score = 10 - (swr - 1.0) * 4
        elif swr <= 2.0: swr_score = 8 - (swr - 1.5) * 8
        else: swr_score = max(0, 4 - (swr - 2.0) * 4)

        eff_score = (efficiency / 100.0) * 10 * eff_weight
        gain_score = gain * 2.5
        fb_score = fb * 0.4

        if takeoff_angle <= 15: raw_toa_score = 25
        elif takeoff_angle <= 25: raw_toa_score = 25 - (takeoff_angle - 15) * 1.0
        elif takeoff_angle <= 40: raw_toa_score = 15 - (takeoff_angle - 25) * 0.8
        else: raw_toa_score = max(0, 3 - (takeoff_angle - 40) * 0.1)
        takeoff_score = raw_toa_score * toa_weight

        # Boom length factor
        boom_height_ratio = height_m / boom_length_m if boom_length_m > 0 else 2.0
        min_effective_ratio = 1.5 + (boom_wavelengths * 0.5)
        if boom_height_ratio >= min_effective_ratio: boom_score = 8.0
        elif boom_height_ratio >= 1.0: boom_score = 4.0 + (boom_height_ratio - 1.0) * (4.0 / (min_effective_ratio - 1.0))
        elif boom_height_ratio >= 0.5: boom_score = boom_height_ratio * 4.0
        else: boom_score = boom_height_ratio * 2.0
        boom_score *= (1.0 + boom_wavelengths * 0.8)

        # Element count factor
        ideal_low = 0.5 + (n - 2) * 0.05
        ideal_high = 1.0 + (n - 2) * 0.1
        if ideal_low <= height_wavelengths <= ideal_high: element_score = 6.0 + (n - 2) * 1.5
        elif (ideal_low - 0.15) <= height_wavelengths < ideal_low: element_score = 3.0 + (n - 2) * 0.5
        elif ideal_high < height_wavelengths <= (ideal_high + 0.3): element_score = 4.0 + (n - 2) * 0.5
        else: element_score = 1.0

        # Ground radials factor
        radial_score = 0
        if has_radials:
            num_rads = request.ground_radials.num_radials
            if ground_type == "wet":
                radial_score = 4.0 if 0.3 <= height_wavelengths <= 0.8 else 2.0
            elif ground_type == "dry":
                radial_score = 3.0 if 0.6 <= height_wavelengths <= 1.2 else 1.0
            else:
                radial_score = 3.5 if 0.4 <= height_wavelengths <= 1.0 else 1.5
            radial_score *= min(num_rads / 8.0, 1.5)

        total_score = swr_score + eff_score + gain_score + fb_score + takeoff_score + boom_score + element_score + radial_score

        heights_tested.append({
            "height": height, "swr": round(swr, 2), "gain": round(gain, 2),
            "fb_ratio": round(fb, 1), "takeoff_angle": takeoff_angle,
            "efficiency": round(efficiency, 1), "score": round(total_score, 1)
        })

        if total_score > best_score:
            best_score = total_score
            best_height = height
            best_swr = swr
            best_gain = gain
            best_fb = fb

    return HeightOptimizeOutput(
        optimal_height=best_height, optimal_swr=round(best_swr, 2),
        optimal_gain=round(best_gain, 2), optimal_fb_ratio=round(best_fb, 1),
        heights_tested=heights_tested
    )


@router.post("/spec-sheet/pdf")
async def generate_pdf(payload: dict = Body(...)):
    """Generate a PDF spec sheet from provided inputs and results."""
    inputs = payload.get("inputs", {})
    results = payload.get("results", {})
    user_email = payload.get("user_email", "guest")
    gain_mode = payload.get("gain_mode", "realworld")
    pdf_bytes = generate_spec_sheet_pdf(inputs, results, user_email, gain_mode)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=antenna_spec_sheet.pdf"},
    )
