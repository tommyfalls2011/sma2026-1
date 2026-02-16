"""Core antenna physics engine — all calculation and tuning logic."""
import math
from typing import List

from config import (
    BAND_DEFINITIONS, FREE_SPACE_GAIN_DBI, STANDARD_BOOM_11M_IN,
    REF_WAVELENGTH_11M_IN,
)
from models import (
    AntennaInput, AntennaOutput, AutoTuneRequest, AutoTuneOutput,
    ElementDimension, TaperConfig, CoronaBallConfig, CalculationRecord,
)


# ── Conversion Helpers ──

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


# ── Gain Model ──

def get_free_space_gain(n: int) -> float:
    if n in FREE_SPACE_GAIN_DBI:
        return FREE_SPACE_GAIN_DBI[n]
    if n < 2:
        return 4.0
    if n > 20:
        return 17.2 + 0.3 * (n - 20)
    lower = max(k for k in FREE_SPACE_GAIN_DBI if k <= n)
    upper = min(k for k in FREE_SPACE_GAIN_DBI if k >= n)
    if lower == upper:
        return FREE_SPACE_GAIN_DBI[lower]
    frac = (n - lower) / (upper - lower)
    return round(FREE_SPACE_GAIN_DBI[lower] + frac * (FREE_SPACE_GAIN_DBI[upper] - FREE_SPACE_GAIN_DBI[lower]), 2)

def get_standard_boom_in(n: int, wavelength_in: float) -> float:
    scale = wavelength_in / REF_WAVELENGTH_11M_IN
    base = STANDARD_BOOM_11M_IN.get(n, 150 + (n - 3) * 60)
    return base * scale


# ── Ground Gain ──

def calculate_ground_gain(height_wavelengths: float, orientation: str = "horizontal") -> float:
    h = height_wavelengths
    if h <= 0:
        return 0.0
    if orientation == "vertical":
        v_points = [
            (0.00, 0.0), (0.10, 1.0), (0.25, 1.8), (0.50, 2.5),
            (1.00, 2.8), (1.50, 2.5), (2.00, 2.6), (2.75, 2.5),
        ]
        if h >= v_points[-1][0]:
            return round(v_points[-1][1], 2)
        for i in range(len(v_points) - 1):
            h0, g0 = v_points[i]
            h1, g1 = v_points[i + 1]
            if h0 <= h <= h1:
                frac = (h - h0) / (h1 - h0) if h1 != h0 else 0
                return round(g0 + frac * (g1 - g0), 2)
        return round(v_points[-1][1], 2)
    h_points = [
        (0.00, 0.0), (0.25, 2.8), (0.55, 5.2), (1.00, 6.0),
        (1.50, 5.5), (2.00, 5.9), (2.50, 5.7), (2.75, 5.8),
    ]
    if h >= h_points[-1][0]:
        base = h_points[-1][1]
    else:
        base = 0.0
        for i in range(len(h_points) - 1):
            h0, g0 = h_points[i]
            h1, g1 = h_points[i + 1]
            if h0 <= h <= h1:
                frac = (h - h0) / (h1 - h0) if h1 != h0 else 0
                base = g0 + frac * (g1 - g0)
                break
    if orientation == "angle45":
        return round(max(0, base - 3.0), 2)
    return round(base, 2)


# ── Boom Correction (G3SEK / DL6WU) ──

def calculate_boom_correction(boom_dia_m: float, avg_element_dia_m: float, wavelength: float, boom_grounded: bool, boom_mount: str = "bonded") -> dict:
    mount = boom_mount
    if mount not in ("bonded", "insulated", "nonconductive"):
        mount = "bonded" if boom_grounded else "nonconductive"
    mount_multipliers = {"bonded": 1.0, "insulated": 0.55, "nonconductive": 0.0}
    k = mount_multipliers.get(mount, 1.0)
    mount_labels = {"bonded": "Bonded to Metal Boom", "insulated": "Insulated on Metal Boom", "nonconductive": "Non-Conductive Boom"}
    if k == 0 or boom_dia_m <= 0 or avg_element_dia_m <= 0:
        if mount == "nonconductive":
            notes = ["Elements match theoretical free-space dimensions", "More stable SWR across the band", "Higher achievable F/B ratio", "Non-conductive boom (PVC/wood/fiberglass) — no element coupling", "Add separate ground path for static/lightning protection"]
            desc = "Non-conductive boom — elements at free-space length, no correction needed. Cleanest, most predictable pattern."
        else:
            notes = ["Elements match theoretical free-space dimensions", "More stable SWR across the band", "Higher achievable F/B ratio", "Insulating sleeves reduce boom influence at each mount point", "Metal boom still provides partial static discharge path"]
            desc = "Insulated mount on metal boom — elements near free-space length. Pattern is cleaner and more predictable."
        return {"enabled": False, "boom_mount": mount, "boom_grounded": mount == "bonded", "swr_factor": 1.0, "gain_adj_db": 0.0, "fb_adj_db": 0.0, "impedance_shift_ohm": 0.0, "bandwidth_mult": 1.0, "correction_per_side_in": 0.0, "correction_total_in": 0.0, "corrected_elements": [], "description": desc, "practical_notes": notes}
    bd = boom_dia_m / wavelength
    c_frac = 12.5975 * bd - 114.5 * bd * bd
    c_frac = max(0, min(c_frac, 0.5))
    c_frac *= k
    boom_dia_in = boom_dia_m * 39.3701
    correction_per_side_in = c_frac * boom_dia_in
    dia_ratio = min(boom_dia_m / avg_element_dia_m, 5.0)
    correction_magnitude = min(c_frac * dia_ratio, 1.0)
    swr_penalty = min(1.0 + 0.04 * correction_magnitude, 1.10)
    gain_adj = max(-0.15 * correction_magnitude, -0.3)
    fb_adj = max(-0.8 * correction_magnitude, -1.5)
    impedance_shift = max(-5.0 * correction_magnitude, -10.0)
    bandwidth_mult = max(1.0 - 0.03 * correction_magnitude, 0.92)
    label = mount_labels.get(mount, mount)
    total_corr = 2 * correction_per_side_in
    if correction_per_side_in < 0.05:
        desc = f"{label} — minimal correction at this frequency."
    elif correction_per_side_in < 0.2:
        desc = f"{label}: shorten each element by ~{total_corr:.2f}\" total ({correction_per_side_in:.2f}\"/side)."
    else:
        desc = f"{label}: shorten each element by ~{total_corr:.2f}\" total ({correction_per_side_in:.2f}\"/side). Precise correction critical."
    if mount == "bonded":
        notes = [f"Boom adds capacitance — elements appear {total_corr:.2f}\" electrically longer", f"Shorten each element by {total_corr:.2f}\" total to restore resonance", "Mechanically strongest — elements welded/bolted directly through boom", "Excellent static and lightning protection (DC ground path)", "SWR more sensitive to boom diameter — verify with analyzer after build"]
    else:
        notes = [f"Proximity coupling: elements appear {total_corr:.2f}\" electrically longer (reduced vs bonded)", f"Shorten each element by {total_corr:.2f}\" total to restore resonance", "Insulating sleeves reduce boom influence but don't eliminate it", "Metal boom still provides partial static discharge", "Easier to match theoretical designs than fully bonded mount"]
    return {"enabled": True, "boom_mount": mount, "boom_grounded": mount == "bonded", "swr_factor": round(swr_penalty, 4), "gain_adj_db": round(gain_adj, 2), "fb_adj_db": round(fb_adj, 2), "impedance_shift_ohm": round(impedance_shift, 1), "bandwidth_mult": round(bandwidth_mult, 4), "correction_per_side_in": round(correction_per_side_in, 3), "correction_total_in": round(2 * correction_per_side_in, 3), "boom_to_element_ratio": round(dia_ratio, 2), "correction_multiplier": k, "corrected_elements": [], "description": desc, "practical_notes": notes}


# ── SWR Calculation ──

def calculate_swr_from_elements(elements: List[ElementDimension], wavelength: float, taper_enabled: bool = False, height_wavelengths: float = 1.0) -> float:
    driven = None
    reflector = None
    directors = []
    for elem in elements:
        if elem.element_type == "driven": driven = elem
        elif elem.element_type == "reflector": reflector = elem
        elif elem.element_type == "director": directors.append(elem)
    if not driven:
        return 2.0
    driven_length_m = convert_element_to_meters(driven.length, "inches")
    ideal_driven = wavelength * 0.473
    deviation = abs(driven_length_m - ideal_driven) / ideal_driven
    if deviation < 0.005: base_swr = 1.0 + (deviation * 10)
    elif deviation < 0.01: base_swr = 1.05 + (deviation - 0.005) * 20
    elif deviation < 0.02: base_swr = 1.15 + (deviation - 0.01) * 25
    elif deviation < 0.04: base_swr = 1.4 + (deviation - 0.02) * 30
    elif deviation < 0.08: base_swr = 2.0 + (deviation - 0.04) * 25
    else: base_swr = 3.0 + (deviation - 0.08) * 20
    if reflector:
        reflector_length_m = convert_element_to_meters(reflector.length, "inches")
        ideal_reflector = driven_length_m * 1.05
        reflector_deviation = abs(reflector_length_m - ideal_reflector) / ideal_reflector
        base_swr *= (1 + reflector_deviation * 0.5)
    if directors:
        for i, director in enumerate(directors):
            director_length_m = convert_element_to_meters(director.length, "inches")
            ideal_director = driven_length_m * (0.95 - i * 0.02)
            director_deviation = abs(director_length_m - ideal_director) / ideal_director
            base_swr *= (1 + director_deviation * 0.2)
    if reflector and driven:
        spacing = abs(driven.position - reflector.position)
        spacing_m = convert_element_to_meters(spacing, "inches")
        ideal_spacing = wavelength * 0.2
        spacing_deviation = abs(spacing_m - ideal_spacing) / ideal_spacing
        base_swr *= (1 + spacing_deviation * 0.3)
    height_factor = 1.0
    fractional_height = height_wavelengths % 0.5
    distance_from_optimal = min(fractional_height, 0.5 - fractional_height)
    if distance_from_optimal < 0.1: height_factor = 0.90 + (distance_from_optimal * 1.0)
    elif distance_from_optimal < 0.2: height_factor = 1.0 + (distance_from_optimal - 0.1) * 1.5
    else: height_factor = 1.15 + (distance_from_optimal - 0.2) * 1.0
    if height_wavelengths < 0.25:
        height_factor *= 1.3 + (0.25 - height_wavelengths) * 2
    base_swr *= height_factor
    if taper_enabled:
        base_swr *= 0.92
    return round(max(1.0, min(base_swr, 5.0)), 2)


# ── Matching Network ──

def apply_matching_network(swr: float, feed_type: str, feedpoint_r: float = 25.0,
                           gamma_rod_dia: float = None, gamma_rod_spacing: float = None,
                           gamma_bar_pos: float = None, gamma_element_gap: float = None,
                           hairpin_rod_dia: float = None, hairpin_rod_spacing: float = None,
                           hairpin_bar_pos: float = None, hairpin_boom_gap: float = None,
                           operating_freq_mhz: float = 27.185) -> tuple:
    if feed_type == "gamma":
        if swr <= 1.2: matched_swr = 1.02 + (swr - 1.0) * 0.15
        elif swr <= 2.0: matched_swr = 1.05 + (swr - 1.2) * 0.06
        elif swr <= 3.0: matched_swr = 1.10 + (swr - 2.0) * 0.10
        else: matched_swr = 1.20 + (swr - 3.0) * 0.15
        # Gamma match: shorting bar sets R, rod insertion sets C (cancels reactance)
        rod_dia = gamma_rod_dia if gamma_rod_dia and gamma_rod_dia > 0 else None
        rod_spacing = gamma_rod_spacing if gamma_rod_spacing and gamma_rod_spacing > 0 else None
        bar_pos = gamma_bar_pos if gamma_bar_pos is not None else 0.5
        rod_insertion = gamma_element_gap if gamma_element_gap is not None else 0.5
        tuning_factor = 1.0
        # Shorting bar: acts as autotransformer tap on the driven element
        # Optimal position depends on feedpoint R: needs sqrt(50/R_feed) ratio
        optimal_bar = min(0.9, max(0.2, math.sqrt(50.0 / max(feedpoint_r, 12.0)) * 0.35))
        bar_deviation = abs(bar_pos - optimal_bar) / max(optimal_bar, 0.1)
        bar_penalty = min(0.20, bar_deviation * 0.25)
        # Rod insertion: slides rod into tube to form variable series capacitor
        # 0.5 = optimal cancellation of gamma section inductance
        # Too little (0.0) = residual inductance, too much (1.0) = excess capacitance
        insertion_deviation = abs(rod_insertion - 0.5) / 0.5
        insertion_penalty = min(0.15, insertion_deviation * 0.20)
        # Z0 of gamma section from rod dimensions
        z0_penalty = 0
        if rod_dia and rod_spacing and rod_spacing > rod_dia / 2:
            gamma_z0 = 276.0 * math.log10(2.0 * rod_spacing / rod_dia)
            optimal_z0 = 250.0
            z0_deviation = abs(gamma_z0 - optimal_z0) / optimal_z0
            z0_penalty = min(0.10, z0_deviation * 0.12)
        # Shorting bar shifts resonant frequency: bar out = lower freq, bar in = higher freq
        # At 0.5 (center), resonant = operating freq. Each 0.1 shift = ~0.15 MHz offset
        freq_shift_mhz = round((bar_pos - 0.5) * 1.5, 3)  # +/- up to ~0.75 MHz
        resonant_freq = round(operating_freq_mhz - freq_shift_mhz, 3)
        # Rod insertion affects Q-factor: more insertion = higher Q = narrower BW
        # Baseline Q for CB Yagi gamma match: ~12. Range: 8 (low insertion) to 25 (high)
        q_factor = round(8.0 + rod_insertion * 17.0, 1)  # 8 at 0, 16.5 at 0.5, 25 at 1.0
        # Bandwidth from Q: BW = f_center / Q
        gamma_bw_mhz = round(operating_freq_mhz / q_factor, 3)
        # SWR at resonance (best achievable): no off-resonance penalty
        tuning_factor = 1.0 + min(0.35, bar_penalty + insertion_penalty + z0_penalty)
        swr_at_resonance = round(max(1.0, matched_swr * tuning_factor), 3)
        # Off-resonance SWR penalty for the operating frequency SWR display
        freq_offset = abs(operating_freq_mhz - resonant_freq)
        half_bw = gamma_bw_mhz / 2
        if half_bw > 0:
            off_resonance = min(1.0, freq_offset / half_bw)
            off_resonance_penalty = off_resonance * 0.25
        else:
            off_resonance_penalty = 0
        matched_swr = round(max(1.0, matched_swr * (tuning_factor + off_resonance_penalty)), 3)
        bw_label = f"{gamma_bw_mhz:.2f} MHz (Q={q_factor:.0f})"
        info = {"type": "Gamma Match", "description": "Rod + capacitor alongside driven element transforms impedance to 50\u03a9", "original_swr": round(swr, 3), "matched_swr": matched_swr, "swr_at_resonance": swr_at_resonance, "tuning_quality": round(1.0 / tuning_factor, 3), "resonant_freq_mhz": resonant_freq, "q_factor": q_factor, "gamma_bandwidth_mhz": gamma_bw_mhz, "bandwidth_effect": bw_label, "bandwidth_mult": round(max(0.6, 1.0 - (q_factor - 12) * 0.02), 2), "technical_notes": {"mechanism": "Series LC network", "asymmetry": "Minor beam skew", "pattern_impact": "Negligible for most operations", "advantage": "Feeds balanced Yagi with unbalanced coax", "tuning": "Bar sets resonant freq, rod sets Q/bandwidth", "mitigation": "Proper tuning minimizes beam skew"}}
        return matched_swr, info
    elif feed_type == "hairpin":
        if swr <= 1.2: matched_swr = 1.03 + (swr - 1.0) * 0.20
        elif swr <= 2.0: matched_swr = 1.07 + (swr - 1.2) * 0.10
        elif swr <= 3.0: matched_swr = 1.15 + (swr - 2.0) * 0.12
        else: matched_swr = 1.27 + (swr - 3.0) * 0.18
        # Hairpin stub tuning: rod dimensions + bar position affect match
        h_rod_dia = hairpin_rod_dia if hairpin_rod_dia and hairpin_rod_dia > 0 else None
        h_rod_spacing = hairpin_rod_spacing if hairpin_rod_spacing and hairpin_rod_spacing > 0 else None
        bar_pos = hairpin_bar_pos if hairpin_bar_pos is not None else 0.5
        boom_gap = hairpin_boom_gap if hairpin_boom_gap is not None else 1.0
        tuning_factor = 1.0
        if h_rod_dia and h_rod_spacing and h_rod_spacing > h_rod_dia / 2:
            hairpin_z0 = 276.0 * math.log10(2.0 * h_rod_spacing / h_rod_dia)
            if feedpoint_r < 50.0:
                xl_required = math.sqrt(max(feedpoint_r, 12.0) * (50.0 - feedpoint_r))
            else:
                xl_required = 10.0
            # Bar position: 0.5 = ideal, deviation increases SWR
            bar_deviation = abs(bar_pos - 0.5) / 0.5  # 0 at center, 1 at extremes
            bar_penalty = bar_deviation * 0.20
            # Z0: optimal range is 200-600 ohms for HF Yagi hairpin stubs
            optimal_z0 = 400.0  # center of 200-600 range
            z0_deviation = abs(hairpin_z0 - optimal_z0) / optimal_z0
            # Gentle penalty within 200-600, steeper outside
            if 200.0 <= hairpin_z0 <= 600.0:
                z0_penalty = z0_deviation * 0.08
            else:
                z0_penalty = min(0.15, z0_deviation * 0.15)
            # Boom gap: closer than 0.5" adds parasitic coupling
            boom_gap_penalty = max(0, (0.5 - boom_gap) * 0.20) if boom_gap < 0.5 else 0
            tuning_factor = 1.0 + min(0.35, bar_penalty + z0_penalty + boom_gap_penalty)
        matched_swr *= tuning_factor
        info = {"type": "Hairpin Match", "description": "Shorted stub adds inductance to cancel capacitive reactance at feedpoint", "original_swr": round(swr, 3), "matched_swr": round(matched_swr, 3), "tuning_quality": round(1.0 / tuning_factor, 3), "bandwidth_effect": "Broadband (minimal effect)", "bandwidth_mult": 1.0, "technical_notes": {"mechanism": "Shorted transmission line stub", "asymmetry": "Symmetrical design \u2014 no beam skew", "advantage": "Simple construction, broadband", "tuning": "Adjust hairpin length and spacing", "tradeoff": "Requires split driven element", "balun_note": "Use current choke balun alongside"}}
        return round(max(1.0, matched_swr), 3), info
    else:
        return swr, {"type": "Direct Feed", "description": "Direct 50\u03a9 coax connection to driven element", "original_swr": round(swr, 3), "matched_swr": round(swr, 3), "bandwidth_effect": "No effect", "bandwidth_mult": 1.0}


# ── Dual Polarity ──

def calculate_dual_polarity_gain(n_per_pol: int, gain_h_single: float) -> dict:
    n_total = n_per_pol * 2
    gain_per_pol = get_free_space_gain(n_per_pol)
    coupling_bonus = min(1.0, 0.3 + n_per_pol * 0.08)
    fb_bonus = min(12.0, 2.0 + n_per_pol * 1.2)
    return {"elements_per_polarization": n_per_pol, "total_elements": n_total, "gain_per_polarization_dbi": round(gain_per_pol + coupling_bonus, 2), "coupling_bonus_db": round(coupling_bonus, 2), "fb_bonus_db": round(fb_bonus, 1), "description": f"{n_per_pol}H + {n_per_pol}V = {n_total} total elements on shared boom"}


def calculate_swr_at_frequency(freq: float, center_freq: float, bandwidth: float, min_swr: float = 1.0) -> float:
    freq_offset = abs(freq - center_freq)
    half_bandwidth = bandwidth / 2
    if freq_offset == 0: return min_swr
    normalized_offset = freq_offset / half_bandwidth if half_bandwidth > 0 else 0
    swr = min_swr + (normalized_offset ** 1.6) * (4.0 - min_swr)
    return min(swr, 10.0)


# ── Wind Load (EIA/TIA-222) ──

def calculate_wind_load(elements: list, boom_dia_in: float, boom_length_in: float, is_dual: bool = False, num_stacked: int = 1) -> dict:
    total_element_area_sqin = 0
    element_weight_lbs = 0
    for e in elements:
        length_in = float(e.get('length', 0) if isinstance(e, dict) else e.length)
        dia_in = float(e.get('diameter', 0.5) if isinstance(e, dict) else e.diameter)
        area = length_in * dia_in
        total_element_area_sqin += area
        volume = math.pi * (dia_in/2)**2 * length_in
        element_weight_lbs += volume * 0.098
    if is_dual:
        total_element_area_sqin *= 2
        element_weight_lbs *= 2
    boom_area_sqin = boom_length_in * boom_dia_in
    boom_volume = math.pi * (boom_dia_in/2)**2 * boom_length_in
    boom_weight_lbs = boom_volume * 0.098
    hardware_area_sqin = 36
    hardware_weight_lbs = 2.0
    num_elements = len(elements) * (2 if is_dual else 1)
    hardware_area_sqin += num_elements * 1.0
    hardware_weight_lbs += num_elements * 0.15
    boom_length_ft = boom_length_in / 12
    truss_area_sqin = 0
    truss_weight_lbs = 0
    if boom_length_ft > 12:
        truss_length_in = boom_length_in * 2
        truss_area_sqin = truss_length_in * 0.125
        truss_weight_lbs = truss_length_in * 0.005
    total_area_sqin = total_element_area_sqin + boom_area_sqin + hardware_area_sqin + truss_area_sqin
    total_area_sqft = total_area_sqin / 144
    total_weight_lbs = element_weight_lbs + boom_weight_lbs + hardware_weight_lbs + truss_weight_lbs
    if num_stacked > 1:
        total_area_sqft *= num_stacked
        total_weight_lbs *= num_stacked
    cd = 1.2
    wind_ratings = {}
    for mph in [50, 70, 80, 90, 100, 120]:
        pressure_psf = 0.00256 * mph**2
        force_lbs = pressure_psf * cd * total_area_sqft
        torque_ft_lbs = force_lbs * (boom_length_ft / 2)
        wind_ratings[str(mph)] = {"force_lbs": round(force_lbs, 1), "torque_ft_lbs": round(torque_ft_lbs, 1)}
    survival_mph = 120
    for mph in range(120, 30, -1):
        pressure_psf = 0.00256 * mph**2
        force = pressure_psf * cd * total_area_sqft
        torque = force * (boom_length_ft / 2)
        if force <= 200 and torque <= 400:
            survival_mph = mph
            break
    longest_element = 0
    for e in elements:
        length_in = float(e.get('length', 0) if isinstance(e, dict) else e.length)
        if length_in > longest_element: longest_element = length_in
    turn_radius_in = math.sqrt((longest_element/2)**2 + (boom_length_in/2)**2)
    turn_radius_ft = turn_radius_in / 12
    return {"total_area_sqft": round(total_area_sqft, 2), "total_weight_lbs": round(total_weight_lbs, 1), "element_weight_lbs": round(element_weight_lbs, 1), "boom_weight_lbs": round(boom_weight_lbs, 1), "hardware_weight_lbs": round(hardware_weight_lbs + truss_weight_lbs, 1), "has_truss": boom_length_ft > 12, "boom_length_ft": round(boom_length_ft, 1), "turn_radius_ft": round(turn_radius_ft, 1), "turn_radius_in": round(turn_radius_in, 1), "survival_mph": survival_mph, "wind_ratings": wind_ratings, "num_stacked": num_stacked, "drag_coefficient": cd}


# ── Taper & Corona Effects ──

def calculate_taper_effects(taper: TaperConfig, num_elements: int) -> dict:
    if not taper or not taper.enabled:
        return {"gain_bonus": 0, "bandwidth_mult": 1.0, "swr_mult": 1.0, "fb_bonus": 0, "fs_bonus": 0}
    num_tapers = taper.num_tapers
    sections = taper.sections
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
        if max_start_dia >= 1.0:
            base_gain_bonus += 0.2
            bandwidth_mult += 0.05
        if 0.2 <= avg_taper <= 0.7:
            taper_quality = 1.0 - abs(avg_taper - 0.45) / 0.45
            base_gain_bonus += 0.4 * taper_quality * num_tapers
            bandwidth_mult += 0.12 * taper_quality * num_tapers
            swr_mult -= 0.03 * taper_quality * num_tapers
            fb_bonus += 1.5 * taper_quality * num_tapers
        if max_start_dia > 0 and min_end_dia < max_start_dia:
            overall_ratio = min_end_dia / max_start_dia
            if 0.3 <= overall_ratio <= 0.6:
                base_gain_bonus += 0.3
                bandwidth_mult += 0.08
    element_scale = min(1.5, num_elements / 3.0)
    return {"gain_bonus": round(base_gain_bonus * element_scale, 2), "bandwidth_mult": round(bandwidth_mult, 2), "swr_mult": round(max(0.7, swr_mult), 2), "fb_bonus": round(fb_bonus * element_scale, 1), "fs_bonus": round(fs_bonus * element_scale, 1), "num_tapers": num_tapers, "sections": [s.dict() for s in sections] if sections else []}

def calculate_corona_effects(corona: CoronaBallConfig) -> dict:
    if not corona or not corona.enabled:
        return {"enabled": False, "gain_effect": 0, "bandwidth_effect": 1.0, "corona_reduction": 0}
    diameter = corona.diameter
    gain_effect = -0.1 if diameter > 1.5 else 0
    bandwidth_effect = 1.02
    corona_reduction = min(90, 50 + diameter * 20)
    return {"enabled": True, "diameter": diameter, "gain_effect": gain_effect, "bandwidth_effect": bandwidth_effect, "corona_reduction": round(corona_reduction, 0), "description": f"{corona_reduction:.0f}% corona discharge reduction"}


# ── Stacking Calculations ──

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
    if spacing_wavelengths < 0.5: narrowing_factor *= 0.7
    elif spacing_wavelengths > 1.0: narrowing_factor *= 0.9
    return round(max(base_beamwidth / narrowing_factor, 15), 1)

def generate_stacked_pattern(base_pattern: List[dict], num_antennas: int, spacing_wavelengths: float, orientation: str) -> List[dict]:
    stacked_pattern = []
    for point in base_pattern:
        angle = point["angle"]
        base_mag = point["magnitude"]
        theta_rad = math.radians(angle)
        if orientation == "vertical":
            psi = 2 * math.pi * spacing_wavelengths * math.sin(theta_rad)
        else:
            psi = 2 * math.pi * spacing_wavelengths * math.cos(theta_rad)
        half_psi = psi / 2
        if abs(math.sin(half_psi)) < 0.001:
            array_factor = 1.0
        else:
            array_factor = abs(math.sin(num_antennas * half_psi) / (num_antennas * math.sin(half_psi)))
        stacked_mag = max(base_mag * array_factor, 1.0)
        stacked_pattern.append({"angle": angle, "magnitude": round(stacked_mag, 1)})
    max_mag = max(p["magnitude"] for p in stacked_pattern)
    if max_mag > 0:
        for p in stacked_pattern:
            p["magnitude"] = round(p["magnitude"] / max_mag * 100, 1)
    return stacked_pattern


# ════════════════════════════════════════════════════════════════
# Main calculation function — calculate_antenna_parameters
# ════════════════════════════════════════════════════════════════

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

    # Boom correction
    boom_correction = calculate_boom_correction(boom_dia_m, avg_element_dia, wavelength, input_data.boom_grounded, input_data.boom_mount or ("bonded" if input_data.boom_grounded else "nonconductive"))
    if boom_correction.get("enabled") and boom_correction.get("correction_total_in", 0) > 0:
        correction_total = boom_correction["correction_total_in"]
        corrected_elements = []
        for el in input_data.elements:
            original_len = el.length
            corrected_len = round(original_len - correction_total, 3)
            corrected_elements.append({"type": el.element_type, "original_length": original_len, "corrected_length": corrected_len, "correction": round(correction_total, 3), "unit": "in"})
        boom_correction["corrected_elements"] = corrected_elements

    has_reflector = any(e.element_type == "reflector" for e in input_data.elements)
    is_dual = input_data.antenna_orientation == "dual"
    dual_active = is_dual and input_data.dual_active
    dual_info = None
    effective_n = n

    if is_dual:
        dual_info = calculate_dual_polarity_gain(n, 0)
        dual_info["selected_beam"] = input_data.dual_selected_beam
        if dual_active:
            dual_info["both_active"] = True
            dual_info["combined_gain_bonus_db"] = 3.0
            dual_info["description"] = f"{n}H + {n}V = {n*2} total (BOTH ACTIVE)"
        else:
            dual_info["both_active"] = False
            dual_info["combined_gain_bonus_db"] = 0
            dual_info["description"] = f"{n}H + {n}V = {n*2} total ({input_data.dual_selected_beam.upper()} selected)"

    positions = sorted([e.position for e in input_data.elements])
    boom_length_in = max(positions) - min(positions) if len(positions) > 1 else 48
    boom_length_m = boom_length_in * 0.0254
    wavelength_in = wavelength / 0.0254
    standard_gain = get_free_space_gain(effective_n)
    standard_boom_in = get_standard_boom_in(effective_n, wavelength_in)

    boom_adj = 0.0
    if boom_length_in > 0 and standard_boom_in > 0:
        boom_ratio = boom_length_in / standard_boom_in
        if boom_ratio > 0 and boom_ratio != 1.0:
            boom_adj = round(2.5 * math.log2(boom_ratio), 2)
    if is_dual and dual_info:
        boom_adj += dual_info["coupling_bonus_db"]

    gain_dbi = round(standard_gain + boom_adj, 2)
    gain_breakdown = {"standard_gain": round(standard_gain, 2), "boom_adj": boom_adj}

    reflector_adj = 0
    if not has_reflector:
        reflector_adj = -1.5
        gain_dbi += reflector_adj
    gain_breakdown["reflector_adj"] = round(reflector_adj, 2)
    base_gain_dbi = round(gain_dbi, 2)

    taper_bonus = taper_effects["gain_bonus"]
    gain_dbi += taper_bonus
    gain_breakdown["taper_bonus"] = round(taper_bonus, 2)

    corona_adj = corona_effects.get("gain_effect", 0)
    gain_dbi += corona_adj
    gain_breakdown["corona_adj"] = round(corona_adj, 2)

    ground_orient = "horizontal" if is_dual else input_data.antenna_orientation
    base_ground_gain = calculate_ground_gain(height_wavelengths, ground_orient)

    ground_radials = input_data.ground_radials
    ground_type = "average"
    ground_scale = 1.0
    if ground_radials and ground_radials.enabled:
        ground_type = ground_radials.ground_type
        ground_type_scales = {"wet": 1.15, "average": 1.0, "dry": 0.70}
        ground_scale = ground_type_scales.get(ground_type, 1.0)
        # Radials improve ground plane quality but do NOT add antenna gain

    height_bonus = round(base_ground_gain * ground_scale, 2)
    gain_dbi += height_bonus
    gain_breakdown["height_bonus"] = height_bonus
    gain_breakdown["ground_type"] = ground_type
    gain_breakdown["ground_scale"] = round(ground_scale, 2)

    boom_bonus = 0
    gain_dbi += boom_bonus
    gain_breakdown["boom_bonus"] = round(boom_bonus, 2)

    if boom_correction["enabled"]:
        boom_grounded_adj = boom_correction["gain_adj_db"]
        gain_dbi += boom_grounded_adj
        gain_breakdown["boom_grounded_adj"] = round(boom_grounded_adj, 2)

    gain_dbi = round(min(gain_dbi, 45.0), 2)

    if dual_active and dual_info:
        gain_dbi = round(gain_dbi + dual_info["combined_gain_bonus_db"], 2)
        gain_breakdown["dual_active_bonus"] = dual_info["combined_gain_bonus_db"]

    gain_breakdown["final_gain"] = gain_dbi

    # SWR
    swr = calculate_swr_from_elements(input_data.elements, wavelength, taper_enabled, height_wavelengths)
    if taper_enabled:
        swr = round(swr * taper_effects["swr_mult"], 2)
    if boom_dia_m > 0.04: swr = round(swr * 0.95, 2)
    elif boom_dia_m > 0.025: swr = round(swr * 0.97, 2)
    swr = round(max(1.0, min(swr, 5.0)), 2)

    feed_type = input_data.feed_type

    # Feedpoint impedance estimate for Yagi (mutual coupling reduces it)
    num_directors = len([e for e in input_data.elements if e.element_type == "director"])
    has_reflector_for_z = any(e.element_type == "reflector" for e in input_data.elements)
    yagi_feedpoint_r = 73.0  # half-wave dipole baseline
    if has_reflector_for_z:
        yagi_feedpoint_r *= 0.55  # reflector coupling reduces ~45%
    if num_directors >= 1:
        yagi_feedpoint_r *= 0.70  # 1st director reduces ~30%
    if num_directors >= 2:
        yagi_feedpoint_r *= 0.85
    if num_directors >= 3:
        yagi_feedpoint_r *= 0.90
    if num_directors >= 4:
        yagi_feedpoint_r *= 0.95
    yagi_feedpoint_r = round(max(12.0, min(73.0, yagi_feedpoint_r)), 1)

    # Element-based resonant frequency: driven element length determines natural resonance
    # f_resonant = c / (2 * L_driven). Mutual coupling (spacing-dependent) shifts it further.
    driven_for_freq = next((e for e in input_data.elements if e.element_type == "driven"), None)
    reflector_for_freq = next((e for e in input_data.elements if e.element_type == "reflector"), None)
    directors_for_freq = sorted([e for e in input_data.elements if e.element_type == "director"], key=lambda e: e.position)
    element_resonant_freq = center_freq  # default to operating freq
    if driven_for_freq:
        driven_len_m = convert_element_to_meters(driven_for_freq.length, "inches")
        ideal_half_wave = wavelength / 2
        if driven_len_m > 0 and ideal_half_wave > 0:
            # Longer driven = lower freq, shorter = higher freq
            length_ratio = driven_len_m / ideal_half_wave
            element_resonant_freq = round(center_freq / length_ratio, 3)
            # Reflector coupling: closer = stronger pull-down on resonant freq
            # Exponential decay: strong coupling at close spacing, weaker at far
            if has_reflector_for_z and reflector_for_freq:
                refl_spacing_m = abs(convert_element_to_meters(driven_for_freq.position - reflector_for_freq.position, "inches"))
                refl_spacing_wl = refl_spacing_m / wavelength if wavelength > 0 else 0.2
                # At 0.1λ: ~4.3%, 0.15λ: ~3.5%, 0.2λ: ~3%, 0.3λ: ~2%
                import math
                refl_coupling = 0.067 * math.exp(-4.0 * max(refl_spacing_wl, 0.02))
                element_resonant_freq *= (1.0 - refl_coupling)
            # Director coupling: each director pulls resonance up slightly
            for i, d in enumerate(directors_for_freq):
                dir_spacing_m = abs(convert_element_to_meters(d.position - driven_for_freq.position, "inches"))
                dir_spacing_wl = dir_spacing_m / wavelength if wavelength > 0 else 0.15
                # Weaker than reflector, decays with distance and element index
                dir_coupling = 0.015 * math.exp(-5.0 * max(dir_spacing_wl, 0.02)) * (0.7 ** i)
                element_resonant_freq *= (1.0 + dir_coupling)
            element_resonant_freq = round(element_resonant_freq, 3)

    matched_swr, matching_info = apply_matching_network(
        swr, feed_type, feedpoint_r=yagi_feedpoint_r,
        gamma_rod_dia=input_data.gamma_rod_dia,
        gamma_rod_spacing=input_data.gamma_rod_spacing,
        gamma_bar_pos=input_data.gamma_bar_pos,
        gamma_element_gap=input_data.gamma_element_gap,
        hairpin_rod_dia=input_data.hairpin_rod_dia,
        hairpin_rod_spacing=input_data.hairpin_rod_spacing,
        hairpin_bar_pos=input_data.hairpin_bar_pos,
        hairpin_boom_gap=input_data.hairpin_boom_gap,
        operating_freq_mhz=center_freq,
    )
    # Add element-based resonant freq to matching info
    if matching_info and feed_type != "direct":
        matching_info["element_resonant_freq_mhz"] = element_resonant_freq
    if feed_type != "direct":
        swr = round(matched_swr, 3)

    # Hairpin design calculations
    if feed_type == "hairpin" and yagi_feedpoint_r < 50.0:
        xl_required = round(math.sqrt(yagi_feedpoint_r * (50.0 - yagi_feedpoint_r)), 2)
        default_rod_dia = 0.25  # inches
        default_rod_spacing = 1.0  # inches
        z0_hairpin = round(276.0 * math.log10(2.0 * default_rod_spacing / default_rod_dia), 1)
        length_deg = round(math.degrees(math.atan(xl_required / z0_hairpin)), 1) if z0_hairpin > 0 else 0
        wavelength_in = wavelength * 39.3701
        length_in = round((length_deg / 360.0) * wavelength_in, 2)
        matching_info["hairpin_design"] = {
            "feedpoint_impedance_ohms": yagi_feedpoint_r,
            "target_impedance_ohms": 50.0,
            "required_reactance_ohms": xl_required,
            "default_rod_diameter_in": default_rod_dia,
            "default_rod_spacing_in": default_rod_spacing,
            "z0_ohms": z0_hairpin,
            "length_degrees": length_deg,
            "length_inches": length_in,
            "element_shortening_pct": 4.0,
            "wavelength_inches": round(wavelength_in, 2),
        }

    # Gamma match design calculations
    if feed_type == "gamma" and yagi_feedpoint_r < 50.0:
        wavelength_in = wavelength * 39.3701
        step_up_ratio = round(math.sqrt(50.0 / yagi_feedpoint_r), 3)
        # Driven element diameter (get from actual element data)
        driven_elem_calc = next((e for e in input_data.elements if e.element_type == "driven"), None)
        element_dia = float(driven_elem_calc.diameter) if driven_elem_calc else 0.5
        # Rules of thumb
        gamma_rod_dia = round(element_dia / 3.0, 3)  # 1/3 of element diameter
        gamma_rod_spacing = round(element_dia * 4.0, 3)  # ~4x element diameter center-to-center
        gamma_rod_length = round(wavelength_in * 0.045, 2)  # 0.04-0.05 lambda
        # Series capacitance: ~7pF per meter of wavelength
        capacitance_pf = round(7.0 * wavelength, 1)
        # Shorting bar position from center (approximate)
        shorting_bar_pos = round(gamma_rod_length * 0.6, 2)
        matching_info["gamma_design"] = {
            "feedpoint_impedance_ohms": yagi_feedpoint_r,
            "target_impedance_ohms": 50.0,
            "step_up_ratio": step_up_ratio,
            "element_diameter_in": element_dia,
            "gamma_rod_diameter_in": gamma_rod_dia,
            "gamma_rod_spacing_in": gamma_rod_spacing,
            "gamma_rod_length_in": gamma_rod_length,
            "capacitance_pf": capacitance_pf,
            "shorting_bar_position_in": shorting_bar_pos,
            "element_shortening_pct": 3.0,
            "wavelength_inches": round(wavelength_in, 2),
        }

    if boom_correction["enabled"]:
        swr = round(swr * boom_correction["swr_factor"], 3)
        swr = round(max(1.0, min(swr, 5.0)), 2)

    # F/B and F/S
    if n == 2: fb_ratio, fs_ratio = 14, 8
    elif n == 3: fb_ratio, fs_ratio = 20, 12
    elif n == 4: fb_ratio, fs_ratio = 24, 16
    elif n == 5: fb_ratio, fs_ratio = 26, 18
    else:
        fb_ratio = 20 + 3.0 * math.log2(n - 2)
        fs_ratio = 12 + 2.5 * math.log2(n - 2)

    driven_elem = next((e for e in input_data.elements if e.element_type == "driven"), None)
    reflector_elem = next((e for e in input_data.elements if e.element_type == "reflector"), None)
    dir_elems = sorted([e for e in input_data.elements if e.element_type == "director"], key=lambda e: e.position)

    spacing_gain_adj = 0.0
    if driven_elem and reflector_elem and has_reflector and n >= 3:
        refl_driven_spacing_m = abs(convert_element_to_meters(driven_elem.position - reflector_elem.position, "inches"))
        refl_driven_lambda = refl_driven_spacing_m / wavelength if wavelength > 0 else 0.18

        # Gain adjustment from driven-reflector spacing
        optimal_gain_lambda = 0.20
        if refl_driven_lambda < optimal_gain_lambda:
            spacing_gain_adj -= 2.5 * (optimal_gain_lambda - refl_driven_lambda) / 0.1
        else:
            spacing_gain_adj -= 1.5 * (refl_driven_lambda - optimal_gain_lambda) / 0.1

        # F/B adjustment from driven-reflector spacing
        optimal_fb_lambda = 0.15
        if refl_driven_lambda < optimal_fb_lambda:
            spacing_fb_adj = 2.0 - 5.0 * (optimal_fb_lambda - refl_driven_lambda) / 0.1
        elif refl_driven_lambda <= 0.20:
            spacing_fb_adj = 2.0 - 4.0 * (refl_driven_lambda - optimal_fb_lambda) / 0.05
        else:
            spacing_fb_adj = -3.0 * (refl_driven_lambda - 0.20) / 0.1
        spacing_fb_adj = round(max(-4.0, min(3.0, spacing_fb_adj)), 1)

        # Director 1 spacing adjustments
        if len(dir_elems) >= 1 and driven_elem:
            dir1_spacing_m = abs(convert_element_to_meters(dir_elems[0].position - driven_elem.position, "inches"))
            dir1_lambda = dir1_spacing_m / wavelength if wavelength > 0 else 0.13
            optimal_dir1 = 0.13
            dir1_dev = dir1_lambda - optimal_dir1
            # Director spacing has significant effect on gain and pattern
            # Closer than optimal: gain drops, F/B improves slightly
            # Farther than optimal: gain rises slightly then drops, F/B degrades
            if dir1_dev < -0.005:
                # Too close — mutual coupling degrades gain
                spacing_gain_adj += 1.8 * dir1_dev / 0.05  # negative dev → negative gain adj
                spacing_fb_adj += -1.5 * dir1_dev / 0.05   # closer = better F/B
            elif dir1_dev > 0.005:
                # Farther — some gain initially, then drops; F/B degrades
                if dir1_dev < 0.04:
                    spacing_gain_adj += 0.6 * dir1_dev / 0.04  # slight gain boost
                else:
                    spacing_gain_adj += 0.6 - 1.5 * (dir1_dev - 0.04) / 0.05
                spacing_fb_adj -= 1.2 * dir1_dev / 0.05

        spacing_gain_adj = round(max(-2.5, min(1.0, spacing_gain_adj)), 2)
        spacing_fb_adj = round(max(-4.0, min(3.0, spacing_fb_adj)), 1)
        fb_ratio += spacing_fb_adj
        fs_ratio += spacing_fb_adj * 0.5
        gain_dbi += spacing_gain_adj
        gain_dbi = round(gain_dbi, 2)

    if is_dual and dual_info:
        fb_ratio += dual_info["fb_bonus_db"]
    if not has_reflector:
        fb_ratio = max(6, fb_ratio - 12)
        fs_ratio = max(4, fs_ratio - 6)
    fb_ratio += taper_effects["fb_bonus"]
    fs_ratio += taper_effects["fs_bonus"]
    if boom_correction["enabled"]:
        fb_ratio += boom_correction["fb_adj_db"]
        fs_ratio += boom_correction["fb_adj_db"] * 0.5
    fb_ratio = round(min(fb_ratio, 65), 1)
    fs_ratio = round(min(fs_ratio, 30), 1)

    # Beamwidth
    boom_length_m = boom_length_in * 0.0254
    g_free_linear = 10 ** (base_gain_dbi / 10) if base_gain_dbi > 0 else 1
    avg_el_len_m = sum(e.length for e in input_data.elements) / n * 0.0254 if n > 0 else wavelength * 0.48
    aspect = boom_length_m / avg_el_len_m if avg_el_len_m > 0 else 1.5
    aspect = max(0.5, min(aspect, 5.0))
    if g_free_linear > 1:
        beamwidth_h = math.sqrt(32400.0 / (g_free_linear * aspect))
        beamwidth_v = math.sqrt(32400.0 * aspect / g_free_linear)
    else:
        beamwidth_h = 90.0
        beamwidth_v = 90.0
    beamwidth_h = round(max(min(beamwidth_h, 120), 15), 1)
    beamwidth_v = round(max(min(beamwidth_v, 120), 25), 1)

    # Bandwidth
    if n <= 3: bandwidth_percent = 6
    elif n <= 5: bandwidth_percent = 5
    else: bandwidth_percent = 5 / (1 + 0.04 * (n - 5))
    bandwidth_percent *= taper_effects["bandwidth_mult"]
    bandwidth_percent *= corona_effects.get("bandwidth_effect", 1.0)
    if avg_element_dia > 0.006: bandwidth_percent *= 1.2
    elif avg_element_dia > 0.004: bandwidth_percent *= 1.1
    bandwidth_mhz = round(center_freq * bandwidth_percent / 100, 3)
    if boom_correction["enabled"]:
        bandwidth_mhz = round(bandwidth_mhz * boom_correction["bandwidth_mult"], 3)
    if feed_type != "direct":
        bandwidth_mhz = round(bandwidth_mhz * matching_info["bandwidth_mult"], 3)

    # Feed type physics adjustments (gain, F/B, beamwidth)
    if feed_type == "gamma":
        # Gamma rod introduces resistive loss and minor asymmetry (beam skew)
        gain_dbi = round(gain_dbi - 0.15, 2)
        fb_ratio = round(fb_ratio - 0.8, 1)
        fs_ratio = round(fs_ratio - 0.4, 1)
        beamwidth_h = round(beamwidth_h + 0.5, 1)  # slight broadening from asymmetry
    elif feed_type == "hairpin":
        # Symmetrical balanced feed — minimal loss, better balance improves F/B slightly
        gain_dbi = round(gain_dbi - 0.05, 2)
        fb_ratio = round(fb_ratio + 0.5, 1)
        bandwidth_mhz = round(bandwidth_mhz * 1.05, 3)  # hairpin is broadband

    multiplication_factor = round(10 ** (gain_dbi / 10), 2)

    # Efficiency
    antenna_orient = input_data.antenna_orientation
    r_rad = 73.0 if antenna_orient == "horizontal" else (36.5 if antenna_orient == "vertical" else 55.0)
    avg_element_dia_m = sum(convert_element_to_meters(e.diameter, "inches") for e in input_data.elements) / n
    if avg_element_dia_m > 0.02: r_ohmic = 0.5
    elif avg_element_dia_m > 0.015: r_ohmic = 1.0
    elif avg_element_dia_m > 0.01: r_ohmic = 1.5
    elif avg_element_dia_m > 0.005: r_ohmic = 2.5
    else: r_ohmic = 4.0
    if antenna_orient == "vertical":
        if ground_radials and ground_radials.enabled:
            num_r = ground_radials.num_radials
            if num_r >= 64: r_ground = 2.0
            elif num_r >= 32: r_ground = 5.0
            elif num_r >= 16: r_ground = 10.0
            elif num_r >= 8: r_ground = 15.0
            else: r_ground = 25.0
        else: r_ground = 36.0
    else:
        if height_wavelengths < 0.25: r_ground = 8.0
        elif height_wavelengths < 0.5: r_ground = 3.0
        elif height_wavelengths < 1.0: r_ground = 1.5
        else: r_ground = 0.5
    r_loss = r_ohmic + r_ground
    radiation_efficiency = r_rad / (r_rad + r_loss)
    swr_reflection_coeff = (swr - 1) / (swr + 1)
    swr_mismatch_loss = 1 - (swr_reflection_coeff ** 2)
    if boom_dia_m > 0.05: boom_efficiency = 0.99
    elif boom_dia_m > 0.03: boom_efficiency = 0.98
    else: boom_efficiency = 0.97
    driven_elem = next((e for e in input_data.elements if e.element_type == "driven"), None)
    reflector_elem = next((e for e in input_data.elements if e.element_type == "reflector"), None)
    spacing_efficiency = 0.98
    if driven_elem and reflector_elem:
        spacing_m = abs(convert_element_to_meters(driven_elem.position - reflector_elem.position, "inches"))
        ideal_spacing = wavelength * 0.2
        spacing_deviation = abs(spacing_m - ideal_spacing) / ideal_spacing
        if spacing_deviation > 0.3: spacing_efficiency = 0.92
        elif spacing_deviation > 0.2: spacing_efficiency = 0.95
        elif spacing_deviation > 0.1: spacing_efficiency = 0.97
    taper_efficiency = 1.02 if taper_enabled else 1.0
    # Feed type efficiency: gamma rod has resistive loss, hairpin is very low loss
    feed_efficiency = 0.97 if feed_type == "gamma" else (0.995 if feed_type == "hairpin" else 1.0)
    antenna_efficiency = (radiation_efficiency * swr_mismatch_loss * boom_efficiency * spacing_efficiency * taper_efficiency * feed_efficiency)
    antenna_efficiency = round(min(antenna_efficiency * 100, 200.0), 1)

    # Reflected power
    reflection_coefficient = round(swr_reflection_coeff, 4)
    if swr_reflection_coeff > 0.0001:
        return_loss_db = round(-20 * math.log10(swr_reflection_coeff), 2)
    else: return_loss_db = 60.0
    mismatch_loss_db = round(-10 * math.log10(swr_mismatch_loss), 3) if swr_mismatch_loss > 0 else 0
    reflected_power_100w = round(100 * (reflection_coefficient ** 2), 2)
    reflected_power_1kw = round(1000 * (reflection_coefficient ** 2), 1)
    forward_power_100w = round(100 - reflected_power_100w, 2)
    forward_power_1kw = round(1000 - reflected_power_1kw, 1)
    impedance_high = round(50 * swr, 1)
    impedance_low = round(50 / swr, 1)

    # Take-off angle
    ground_radials = input_data.ground_radials
    ground_type = "average"
    if ground_radials and ground_radials.enabled:
        ground_type = ground_radials.ground_type
    ground_factors = {
        "wet": {"conductivity": 0.03, "permittivity": 30, "reflection": 0.95, "angle_adj": -3},
        "average": {"conductivity": 0.005, "permittivity": 13, "reflection": 0.85, "angle_adj": 0},
        "dry": {"conductivity": 0.001, "permittivity": 5, "reflection": 0.70, "angle_adj": 5}
    }
    ground = ground_factors.get(ground_type, ground_factors["average"])
    antenna_orient = input_data.antenna_orientation
    if antenna_orient == "vertical":
        base_takeoff = 15.0
        if ground_radials and ground_radials.enabled:
            radial_reduction = min(10, ground_radials.num_radials / 4.0)
            base_takeoff = max(5, 15.0 - radial_reduction)
        else: base_takeoff = 25.0
    elif antenna_orient == "angle45":
        if height_wavelengths >= 0.25:
            horiz_takeoff = math.degrees(math.asin(min(1.0, 1 / (4 * height_wavelengths))))
            base_takeoff = horiz_takeoff * 0.85
        else: base_takeoff = 55 + (0.25 - height_wavelengths) * 60
    elif antenna_orient == "dual":
        if height_wavelengths >= 0.25:
            h_takeoff = math.degrees(math.asin(min(1.0, 1 / (4 * height_wavelengths))))
            base_takeoff = h_takeoff * 0.90
        else: base_takeoff = 65 + (0.25 - height_wavelengths) * 70
    elif height_wavelengths >= 0.25:
        base_takeoff = math.degrees(math.asin(min(1.0, 1 / (4 * height_wavelengths))))
    else: base_takeoff = 70 + (0.25 - height_wavelengths) * 80
    takeoff_angle = round(max(5, min(90, base_takeoff + ground["angle_adj"])), 1)

    if takeoff_angle < 10: takeoff_desc = "Elite (Extremely low angle, massive DX)"
    elif takeoff_angle < 15: takeoff_desc = "Deep DX (Reaching other continents)"
    elif takeoff_angle < 18: takeoff_desc = "DX Sweet Spot (Maximum ground gain)"
    elif takeoff_angle < 22: takeoff_desc = "Strong Mid-Range (Continent-wide skip)"
    elif takeoff_angle < 28: takeoff_desc = "Regional (Good local/statewide skip)"
    elif takeoff_angle < 35: takeoff_desc = "Minimum (Moderate skip, safe from detuning)"
    elif takeoff_angle < 50: takeoff_desc = "Medium (Regional/DX mix)"
    elif takeoff_angle < 70: takeoff_desc = "High (Near vertical, short distance)"
    else: takeoff_desc = "Inefficient (High ground absorption)"

    if height_wavelengths < 0.25: height_perf = "Inefficient: Below minimum height. Ground absorption detunes elements."
    elif height_wavelengths < 0.40: height_perf = "Near Vertical: High-angle signal, very short distance only."
    elif height_wavelengths < 0.55: height_perf = "Minimum: Safe from ground detuning. Moderate skip capability."
    elif height_wavelengths < 0.70: height_perf = "Regional: Good for local and statewide skip propagation."
    elif height_wavelengths < 0.85: height_perf = "Strong Mid-Range: Effective for continent-wide skip."
    elif height_wavelengths < 1.05: height_perf = "DX Sweet Spot: Maximum ground gain. Ideal for long distance."
    elif height_wavelengths < 1.25: height_perf = "Deep DX: Reaching other continents reliably."
    elif height_wavelengths < 1.75: height_perf = "Elite: Extremely low angle, massive skip distance."
    elif height_wavelengths < 2.5: height_perf = "Peak Performance: Point of diminishing returns."
    else: height_perf = "Complex: Multiple radiation lobes may cause signal splitting."

    # Ground radials info
    ground_radials_info = None
    if ground_radials and ground_radials.enabled:
        quarter_wave_m = wavelength / 4
        quarter_wave_ft = quarter_wave_m * 3.28084
        quarter_wave_in = quarter_wave_m * 39.3701
        all_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "NNE", "ENE", "ESE", "SSE", "SSW", "WSW", "WNW", "NNW", "N2", "E2"]
        num_rads = ground_radials.num_radials
        radial_directions = all_directions[:num_rads]
        radial_factor = num_rads / 8.0
        ground_improvement = {"wet": {"swr_improvement": 0.05, "efficiency_bonus": 8}, "average": {"swr_improvement": 0.03, "efficiency_bonus": 5}, "dry": {"swr_improvement": 0.01, "efficiency_bonus": 2}}
        base_bonus = ground_improvement.get(ground_type, ground_improvement["average"])
        if radial_factor <= 1.0: scale = radial_factor
        else: scale = 1.0 + (math.log2(radial_factor) * 0.5)
        g_bonus = {"swr_improvement": round(base_bonus["swr_improvement"] * scale, 3), "efficiency_bonus": round(base_bonus["efficiency_bonus"] * scale, 1)}
        ground_radials_info = {"enabled": True, "ground_type": ground_type, "ground_conductivity": ground["conductivity"], "ground_permittivity": ground["permittivity"], "ground_reflection_coeff": ground["reflection"], "radial_length_m": round(quarter_wave_m, 2), "radial_length_ft": round(quarter_wave_ft, 2), "radial_length_in": round(quarter_wave_in, 1), "wire_diameter_in": ground_radials.wire_diameter, "num_radials": ground_radials.num_radials, "radial_directions": radial_directions, "total_wire_length_ft": round(quarter_wave_ft * ground_radials.num_radials, 1), "estimated_improvements": {"swr_improvement": g_bonus["swr_improvement"], "efficiency_bonus_percent": g_bonus["efficiency_bonus"]}}
        swr = max(1.0, swr - g_bonus["swr_improvement"])
        gain_breakdown["final_gain"] = gain_dbi
        antenna_efficiency = min(200.0, antenna_efficiency + g_bonus["efficiency_bonus"])

    # SWR curve — center the minimum on the resonant frequency (from match tuning)
    # but display range centered on the operating frequency
    curve_resonant_freq = center_freq
    curve_min_swr = swr
    if feed_type != "direct" and matching_info:
        if "resonant_freq_mhz" in matching_info:
            curve_resonant_freq = matching_info["resonant_freq_mhz"]
        if "swr_at_resonance" in matching_info:
            curve_min_swr = matching_info["swr_at_resonance"]
    swr_curve = []
    for i in range(-30, 31):
        freq = center_freq + (i * channel_spacing)
        swr_at_freq = calculate_swr_at_frequency(freq, curve_resonant_freq, bandwidth_mhz, curve_min_swr)
        swr_curve.append({"frequency": round(freq, 4), "swr": round(swr_at_freq, 2), "channel": i})
    usable_1_5 = round(sum(1 for p in swr_curve if p["swr"] <= 1.5) * channel_spacing, 3)
    usable_2_0 = round(sum(1 for p in swr_curve if p["swr"] <= 2.0) * channel_spacing, 3)

    # Far field pattern
    far_field_pattern = []
    for angle in range(0, 361, 5):
        theta = math.radians(angle)
        cos_theta = math.cos(theta)
        if not has_reflector:
            if n == 2:
                main_lobe = 0.6 + 0.4 * cos_theta
                magnitude = (max(0.2, main_lobe) ** 1.5) * 100
            else:
                forward_gain = max(0, cos_theta) ** 1.5 if cos_theta >= 0 else 0
                back_level = 0.3 + 0.1 * min(n - 2, 5)
                if 90 < angle < 270: magnitude = max(forward_gain, back_level) * 100
                else: magnitude = max(forward_gain, 0.1) * 100
                if 60 < angle < 120 or 240 < angle < 300: magnitude = max(magnitude, 25)
        else:
            if n == 2:
                main_lobe = (cos_theta + 0.3) / 1.3
                magnitude = (max(0, main_lobe) ** 2) * 100
            else:
                main_lobe = max(0, cos_theta ** 2)
                back_attenuation = 10 ** (-fb_ratio / 20)
                side_attenuation = 10 ** (-fs_ratio / 20)
                if 90 < angle < 270: magnitude = main_lobe * back_attenuation * 100
                else: magnitude = main_lobe * 100
                if 60 < angle < 120 or 240 < angle < 300: magnitude *= side_attenuation
        far_field_pattern.append({"angle": angle, "magnitude": round(max(magnitude, 1), 1)})

    # Stacking
    stacking_enabled = False
    stacking_info = None
    stacked_gain_dbi = None
    stacked_pattern = None
    if input_data.stacking and input_data.stacking.enabled:
        stacking_enabled = True
        stacking = input_data.stacking
        spacing_m = convert_spacing_to_meters(stacking.spacing, stacking.spacing_unit)
        spacing_wavelengths = spacing_m / wavelength
        if stacking.layout == "quad":
            num_v = 2
            num_h = 2
            h_spacing_val = stacking.h_spacing if stacking.h_spacing else stacking.spacing
            h_spacing_unit = stacking.h_spacing_unit if stacking.h_spacing else stacking.spacing_unit
            h_spacing_m = convert_spacing_to_meters(h_spacing_val, h_spacing_unit)
            h_spacing_wavelengths = h_spacing_m / wavelength
            v_gain, v_increase = calculate_stacking_gain(gain_dbi, num_v, spacing_wavelengths, "vertical")
            stacked_gain_dbi, h_increase = calculate_stacking_gain(v_gain, num_h, h_spacing_wavelengths, "horizontal")
            gain_increase = round(stacked_gain_dbi - gain_dbi, 1)
            new_beamwidth_v = calculate_stacked_beamwidth(beamwidth_v, num_v, spacing_wavelengths)
            new_beamwidth_h = calculate_stacked_beamwidth(beamwidth_h, num_h, h_spacing_wavelengths)
            stacked_pattern = generate_stacked_pattern(far_field_pattern, 4, spacing_wavelengths, "vertical")
        else:
            stacked_gain_dbi, gain_increase = calculate_stacking_gain(gain_dbi, stacking.num_antennas, spacing_wavelengths, stacking.orientation)
            if stacking.orientation == "vertical":
                new_beamwidth_v = calculate_stacked_beamwidth(beamwidth_v, stacking.num_antennas, spacing_wavelengths)
                new_beamwidth_h = beamwidth_h
            else:
                new_beamwidth_h = calculate_stacked_beamwidth(beamwidth_h, stacking.num_antennas, spacing_wavelengths)
                new_beamwidth_v = beamwidth_v
            stacked_pattern = generate_stacked_pattern(far_field_pattern, stacking.num_antennas, spacing_wavelengths, stacking.orientation)

        is_dual_stacking = is_dual
        is_quad = stacking.layout == "quad"
        actual_num = 4 if is_quad else stacking.num_antennas
        optimal_spacing_wl = 1.0 if stacking.orientation == "vertical" or is_quad else 0.65
        optimal_spacing_ft = round((wavelength * optimal_spacing_wl) / 0.3048, 1)
        min_spacing_wl = 0.5 if stacking.orientation == "vertical" or is_quad else 0.65

        if stacking.orientation == "vertical" or is_quad:
            if spacing_wavelengths >= 2.0: isolation_db = 30
            elif spacing_wavelengths >= 1.0: isolation_db = 20 + (spacing_wavelengths - 1.0) * 10
            elif spacing_wavelengths >= 0.5: isolation_db = 12 + (spacing_wavelengths - 0.5) * 16
            else: isolation_db = max(5, spacing_wavelengths * 24)
        else: isolation_db = 15

        spacing_status = "Too close — high mutual coupling" if spacing_wavelengths < 0.25 else ("Minimum — some coupling" if spacing_wavelengths < 0.5 else ("Good" if spacing_wavelengths < 1.0 else ("Optimal" if spacing_wavelengths < 2.0 else "Wide — diminishing returns")))

        stacking_info = {"orientation": stacking.orientation, "layout": stacking.layout, "num_antennas": actual_num, "spacing": stacking.spacing, "spacing_unit": stacking.spacing_unit, "spacing_wavelengths": round(spacing_wavelengths, 3), "gain_increase_db": gain_increase, "new_beamwidth_h": new_beamwidth_h, "new_beamwidth_v": new_beamwidth_v, "stacked_multiplication_factor": round(10 ** (stacked_gain_dbi / 10), 2), "optimal_spacing_ft": optimal_spacing_ft, "min_spacing_ft": round((wavelength * min_spacing_wl) / 0.3048, 1), "spacing_status": spacing_status, "isolation_db": round(isolation_db, 1), "phasing": {"requirement": "0 deg phase — all feed lines identical length", "cable_note": "Cable lengths must match to the millimeter for proper phasing", "combiner": f"{stacking.num_antennas}:1 Hybrid Splitter/Combiner or Power Divider"}, "power_splitter": {"type": f"{stacking.num_antennas}:1 Power Splitter/Combiner", "input_impedance": "50 ohm", "combined_load": f"{round(50 / stacking.num_antennas, 1)} ohm (parallel)", "matching_method": "Quarter-wave (lambda/4) transformer", "quarter_wave_ft": round((wavelength * 0.25) / 0.3048, 1), "quarter_wave_in": round((wavelength * 0.25) / 0.0254, 1), "power_per_antenna_100w": round(100 / stacking.num_antennas, 1), "power_per_antenna_1kw": round(1000 / stacking.num_antennas, 1), "phase_lines": "All feed lines must be identical length for 0 deg phase shift", "min_power_rating": f"{round(1000 / stacking.num_antennas * 1.5)} W per port recommended", "isolation_note": "Port isolation prevents mismatch on one antenna from degrading others"}}

        if is_dual_stacking:
            stacking_info["dual_stacking"] = {"note": "Stack identical dual-pol antennas only", "cross_pol": "Each antenna maintains H+V elements at their original angles", "mimo_capable": stacking.num_antennas >= 2, "mimo_note": "2x2 MIMO possible with cross-polarization for multipath diversity" if stacking.num_antennas >= 2 else "", "weatherproofing": "Use self-amalgamating tape on all exterior connectors", "wind_load": f"Stacked array of {stacking.num_antennas} antennas — verify mast rating"}

        if stacking.orientation == "vertical" and not is_quad:
            one_wl_ft = round(wavelength / 0.3048, 1)
            spacing_vs_wl = spacing_wavelengths
            alignment_status = "Optimal collinear" if 0.8 <= spacing_vs_wl <= 1.2 else ("Acceptable" if 0.5 <= spacing_vs_wl <= 2.0 else "Sub-optimal")
            stacking_info["vertical_notes"] = {"alignment": "COLLINEAR — antennas must be on the same vertical axis", "effect": "Narrows vertical beamwidth, focusing power toward the horizon", "one_wavelength_ft": f"{one_wl_ft} ft (1\u03bb at {center_freq} MHz)", "alignment_status": alignment_status, "isolation": f"~{round(isolation_db)}dB isolation at current spacing", "far_field": {"elevation": "Compresses toward horizon", "azimuth": "Remains omnidirectional (360\u00b0)", "summary": "Vertical collinear stack: Maximum distance in ALL directions"}, "stagger_warning": "DO NOT offset horizontally", "coupling_warning": "Below 0.25\u03bb spacing causes severe mutual coupling" if spacing_wavelengths < 0.25 else "", "feed_line_note": "Feed lines MUST be identical length and type", "best_practice": f"Ideal spacing: ~1\u03bb ({one_wl_ft} ft center-to-center)"}

        if stacking.orientation == "horizontal" and not is_quad:
            stacking_info["horizontal_notes"] = {"effect": "Narrows horizontal beamwidth", "far_field": {"elevation": "Stays wide", "azimuth": "Becomes directional with lobes and nulls", "summary": "Horizontal stack: Intentional coverage in specific directions only"}, "tradeoff": "Sacrifices omnidirectional coverage for directional gain", "feed_line_note": "Feed lines MUST be identical length and type", "isolation": f"~{round(isolation_db)}dB isolation at current spacing"}

        if is_quad:
            h_spacing_val = stacking.h_spacing if stacking.h_spacing else stacking.spacing
            h_spacing_unit = stacking.h_spacing_unit if stacking.h_spacing else stacking.spacing_unit
            stacking_info["quad_notes"] = {"layout": "2x2 H-Frame (2 vertical x 2 horizontal)", "effect": "Narrows BOTH vertical and horizontal beamwidth", "v_spacing": f"{stacking.spacing} {stacking.spacing_unit} (vertical)", "h_spacing": f"{h_spacing_val} {h_spacing_unit} (horizontal)", "h_frame_note": "Two antennas on horizontal cross-arm, two stacked vertically on mast", "isolation": f"~{round(isolation_db)}dB vertical isolation", "coupling_warning": "Below 0.25 lambda spacing causes severe mutual coupling" if spacing_wavelengths < 0.25 else "", "identical_note": "All 4 antennas MUST be identical models", "phasing_note": "Use 4-way equal-length phasing harness"}
        beamwidth_h, beamwidth_v = new_beamwidth_h, new_beamwidth_v

    swr_desc = "Perfect" if swr <= 1.1 else ("Excellent" if swr <= 1.3 else ("Very Good" if swr <= 1.5 else ("Good" if swr <= 2.0 else "Fair")))

    taper_info = None
    if input_data.taper and input_data.taper.enabled:
        taper_info = {"enabled": True, "num_tapers": taper_effects["num_tapers"], "gain_bonus": taper_effects["gain_bonus"], "bandwidth_improvement": f"{(taper_effects['bandwidth_mult'] - 1) * 100:.0f}%", "sections": taper_effects["sections"]}

    # Wind load
    boom_dia_in = boom_dia_m / 0.0254
    num_stacked = stacking.num_antennas if stacking_enabled and input_data.stacking else 1
    element_dicts = [{"length": e.length, "diameter": e.diameter, "position": e.position} for e in input_data.elements]
    wind_load_info = calculate_wind_load(elements=element_dicts, boom_dia_in=boom_dia_in, boom_length_in=boom_length_in, is_dual=is_dual, num_stacked=num_stacked)

    return AntennaOutput(
        swr=swr, swr_description=f"{swr_desc} match - {swr}:1",
        fb_ratio=fb_ratio, fb_ratio_description=f"{fb_ratio} dB front-to-back",
        fs_ratio=fs_ratio, fs_ratio_description=f"{fs_ratio} dB front-to-side",
        beamwidth_h=beamwidth_h, beamwidth_v=beamwidth_v, beamwidth_description=f"H: {beamwidth_h}\u00b0 / V: {beamwidth_v}\u00b0",
        bandwidth=bandwidth_mhz, bandwidth_description=f"{usable_2_0:.3f} MHz at 2:1 SWR",
        gain_dbi=gain_dbi, gain_description=f"{round(10 ** ((stacked_gain_dbi or gain_dbi) / 10), 2)}x over isotropic",
        base_gain_dbi=base_gain_dbi, gain_breakdown=gain_breakdown,
        multiplication_factor=multiplication_factor, multiplication_description="ERP multiplier",
        antenna_efficiency=antenna_efficiency, efficiency_description=f"{antenna_efficiency}% efficient",
        far_field_pattern=far_field_pattern, swr_curve=swr_curve,
        usable_bandwidth_1_5=usable_1_5, usable_bandwidth_2_0=usable_2_0,
        center_frequency=center_freq, band_info={**band_info, "channel_spacing_khz": band_info.get("channel_spacing_khz", 10)},
        input_summary={"num_elements": n, "center_frequency_mhz": center_freq, "wavelength_m": round(wavelength, 3)},
        stacking_enabled=stacking_enabled, stacking_info=stacking_info,
        stacked_gain_dbi=stacked_gain_dbi, stacked_pattern=stacked_pattern,
        taper_info=taper_info, corona_info=corona_effects if corona_effects.get("enabled") else None,
        reflection_coefficient=reflection_coefficient, return_loss_db=return_loss_db, mismatch_loss_db=mismatch_loss_db,
        reflected_power_100w=reflected_power_100w, reflected_power_1kw=reflected_power_1kw,
        forward_power_100w=forward_power_100w, forward_power_1kw=forward_power_1kw,
        impedance_high=impedance_high, impedance_low=impedance_low,
        takeoff_angle=takeoff_angle, takeoff_angle_description=takeoff_desc,
        height_performance=height_perf, ground_radials_info=ground_radials_info,
        noise_level="Moderate" if input_data.antenna_orientation in ("dual", "angle45") else ("High" if input_data.antenna_orientation == "vertical" else "Low"),
        noise_description="Dual polarity receives both H and V — moderate noise, excellent for fading/skip" if input_data.antenna_orientation == "dual" else ("Vertical polarization picks up more man-made noise (QRN)" if input_data.antenna_orientation == "vertical" else ("45\u00b0 slant receives both polarizations — moderate noise" if input_data.antenna_orientation == "angle45" else "Horizontal polarization has a quieter receive noise floor")),
        feed_type=feed_type, matching_info=matching_info, dual_polarity_info=dual_info,
        wind_load=wind_load_info,
        boom_correction_info=boom_correction if boom_correction.get("enabled") else boom_correction,
        resonant_freq_mhz=curve_resonant_freq,
    )


# ════════════════════════════════════════════════════════════════
# Auto-tune function
# ════════════════════════════════════════════════════════════════

def auto_tune_antenna(request: AutoTuneRequest) -> AutoTuneOutput:
    band_info = BAND_DEFINITIONS.get(request.band, BAND_DEFINITIONS["11m_cb"])
    center_freq = request.frequency_mhz if request.frequency_mhz else band_info["center"]
    c = 299792458
    wavelength_m = c / (center_freq * 1e6)
    wavelength_in = wavelength_m * 39.3701
    n = request.num_elements
    elements = []
    notes = []
    driven_length = round(wavelength_in * 0.473, 1)
    # Apply feed type shortening to driven element
    feed_type = getattr(request, 'feed_type', 'direct')
    if feed_type == 'gamma':
        driven_length = round(driven_length * 0.97, 1)  # 3% shorter for gamma
    elif feed_type == 'hairpin':
        driven_length = round(driven_length * 0.96, 1)  # 4% shorter for hairpin
    use_reflector = getattr(request, 'use_reflector', True)
    scale_factor = wavelength_in / REF_WAVELENGTH_11M_IN
    target_boom = STANDARD_BOOM_11M_IN.get(n, 150 + (n - 3) * 60) * scale_factor

    if use_reflector:
        if getattr(request, 'close_driven', False): refl_driven_lambda = 0.12
        elif getattr(request, 'far_driven', False): refl_driven_lambda = 0.22
        else: refl_driven_lambda = 0.18
        refl_driven_gap = round(refl_driven_lambda * wavelength_in, 1)
        if getattr(request, 'boom_lock_enabled', False) and getattr(request, 'max_boom_length', None):
            max_boom = request.max_boom_length
            max_driven_pos = max_boom * 0.4
            if refl_driven_gap > max_driven_pos:
                refl_driven_gap = round(max_driven_pos, 1)
        elements.append({"element_type": "reflector", "length": round(driven_length * 1.05, 1), "diameter": 0.5, "position": 0})
        notes.append(f"Reflector: {round(driven_length * 1.05, 1)}\" (5% longer than driven)")
        elements.append({"element_type": "driven", "length": driven_length, "diameter": 0.5, "position": refl_driven_gap})
        notes.append(f"Driven: {driven_length}\" at {refl_driven_gap}\" from reflector ({refl_driven_lambda}\u03bb)")
        num_directors = n - 2
        remaining_boom = target_boom - refl_driven_gap
        current_position = refl_driven_gap
    else:
        elements.append({"element_type": "driven", "length": driven_length, "diameter": 0.5, "position": 0})
        notes.append(f"Driven: {driven_length}\" at position 0 (no reflector)")
        num_directors = n - 1
        remaining_boom = target_boom
        current_position = 0

    if request.spacing_lock_enabled and request.locked_positions:
        for i, elem in enumerate(elements):
            if i < len(request.locked_positions):
                elem["position"] = request.locked_positions[i]
        for i in range(num_directors):
            position_idx = (2 if use_reflector else 1) + i
            if position_idx < len(request.locked_positions):
                locked_pos = request.locked_positions[position_idx]
            else:
                director_spacing = remaining_boom / num_directors if num_directors > 0 else remaining_boom
                current_position += director_spacing
                locked_pos = current_position
            director_length = round(driven_length * (0.95 - i * 0.02), 1)
            elements.append({"element_type": "director", "length": director_length, "diameter": 0.5, "position": locked_pos})
            notes.append(f"Director {i+1}: {director_length}\" at {locked_pos}\" (spacing locked)")
        notes.append("Spacing Lock: Positions preserved, only lengths optimized")
    else:
        if num_directors > 0:
            # Determine first director spacing override
            if getattr(request, 'close_dir1', False):
                dir1_lambda = 0.10
            elif getattr(request, 'far_dir1', False):
                dir1_lambda = 0.18
            else:
                dir1_lambda = 0.13  # default

            for i in range(num_directors):
                if i == 0:
                    # First director uses the override spacing
                    director_spacing = round(dir1_lambda * wavelength_in, 1)
                    if getattr(request, 'boom_lock_enabled', False) and getattr(request, 'max_boom_length', None):
                        max_dir1 = (request.max_boom_length - current_position) * 0.5
                        if director_spacing > max_dir1:
                            director_spacing = round(max_dir1, 1)
                    current_position += director_spacing
                    director_length = round(driven_length * (0.95 - i * 0.02), 1)
                    elements.append({"element_type": "director", "length": director_length, "diameter": 0.5, "position": round(current_position, 1)})
                    dir1_label = f"({dir1_lambda}\u03bb)" if (getattr(request, 'close_dir1', False) or getattr(request, 'far_dir1', False)) else ""
                    notes.append(f"Director 1: {director_length}\" at {round(current_position, 1)}\" {dir1_label}")
                else:
                    remaining_after_dir1 = target_boom - current_position
                    remaining_dirs = num_directors - 1
                    weight = 0.8 + (0.4 * (i - 1) / max(remaining_dirs - 1, 1)) if remaining_dirs > 1 else 1.0
                    total_weight = sum(0.8 + (0.4 * j / max(remaining_dirs - 1, 1)) if remaining_dirs > 1 else 1.0 for j in range(remaining_dirs))
                    director_spacing = round(remaining_after_dir1 * weight / total_weight, 1)
                    current_position += director_spacing
                    director_length = round(driven_length * (0.95 - i * 0.02), 1)
                    elements.append({"element_type": "director", "length": director_length, "diameter": 0.5, "position": round(current_position, 1)})
                    notes.append(f"Director {i+1}: {director_length}\" at {round(current_position, 1)}\"")

    notes.append(f"")
    notes.append(f"Wavelength at {center_freq} MHz: {round(wavelength_in, 1)}\"")

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

    if request.boom_lock_enabled and request.max_boom_length:
        target_boom = request.max_boom_length
        refl_idx = next((i for i, e in enumerate(elements) if e["element_type"] == "reflector"), None)
        driven_idx = next((i for i, e in enumerate(elements) if e["element_type"] == "driven"), None)
        dir_indices = [i for i, e in enumerate(elements) if e["element_type"] == "director"]
        if driven_idx is not None:
            if refl_idx is not None:
                elements[refl_idx]["position"] = 0
                if len(dir_indices) > 0:
                    refl_driven_gap = round(target_boom * 0.15, 1)
                    elements[driven_idx]["position"] = refl_driven_gap
                    remaining = target_boom - refl_driven_gap
                    dir_spacing = round(remaining / len(dir_indices), 1)
                    for j, idx in enumerate(dir_indices):
                        elements[idx]["position"] = round(refl_driven_gap + dir_spacing * (j + 1), 1)
                else:
                    elements[driven_idx]["position"] = round(target_boom, 1)
            else:
                elements[driven_idx]["position"] = 0
                if len(dir_indices) > 0:
                    dir_spacing = round(target_boom / len(dir_indices), 1)
                    for j, idx in enumerate(dir_indices):
                        elements[idx]["position"] = round(dir_spacing * (j + 1), 1)
        notes.append(f"")
        notes.append(f"Boom Restraint: {target_boom}\" ({round(target_boom/12, 1)} ft) — elements equally spaced")
        compression_penalty = 0
    else:
        compression_penalty = 0

    final_boom = max(e['position'] for e in elements) if elements else 0
    notes.append(f"")
    notes.append(f"Total boom length: ~{round(final_boom, 1)}\" ({round(final_boom/12, 1)} ft)")

    base_predicted_swr = 1.05 if request.taper and request.taper.enabled else 1.1
    predicted_swr = base_predicted_swr if use_reflector else base_predicted_swr + 0.1

    base_gain = get_free_space_gain(n)
    standard_boom_in = get_standard_boom_in(n, wavelength_in)
    if final_boom > 0 and standard_boom_in > 0:
        boom_ratio = final_boom / standard_boom_in
        if boom_ratio > 0 and boom_ratio != 1.0:
            boom_adj = round(2.5 * math.log2(boom_ratio), 2)
            base_gain += boom_adj
    if not use_reflector: base_gain -= 1.5
    if request.taper and request.taper.enabled:
        base_gain += 0.3 * request.taper.num_tapers

    # Position-based spacing corrections
    spacing_gain_adj = 0.0
    spacing_fb_adj = 0.0
    refl_elem = next((e for e in elements if e["element_type"] == "reflector"), None)
    driven_elem_final = next((e for e in elements if e["element_type"] == "driven"), None)
    dir_elems = sorted([e for e in elements if e["element_type"] == "director"], key=lambda e: e["position"])

    if refl_elem and driven_elem_final and n >= 3:
        refl_driven_in = abs(driven_elem_final["position"] - refl_elem["position"])
        refl_driven_lambda = (refl_driven_in * 0.0254) / wavelength_m if wavelength_m > 0 else 0.18
        optimal_gain_lambda = 0.20
        if refl_driven_lambda < optimal_gain_lambda:
            spacing_gain_adj -= 2.5 * (optimal_gain_lambda - refl_driven_lambda) / 0.1
        else:
            spacing_gain_adj -= 1.5 * (refl_driven_lambda - optimal_gain_lambda) / 0.1
        optimal_fb_lambda = 0.15
        if refl_driven_lambda <= optimal_fb_lambda:
            spacing_fb_adj = 2.0 - 5.0 * (optimal_fb_lambda - refl_driven_lambda) / 0.1
        elif refl_driven_lambda <= 0.20:
            spacing_fb_adj = 2.0 - 4.0 * (refl_driven_lambda - optimal_fb_lambda) / 0.05
        else:
            spacing_fb_adj = -3.0 * (refl_driven_lambda - 0.20) / 0.1
        if len(dir_elems) >= 1:
            dir1_in = abs(dir_elems[0]["position"] - driven_elem_final["position"])
            dir1_lambda = (dir1_in * 0.0254) / wavelength_m if wavelength_m > 0 else 0.13
            optimal_dir1 = 0.13
            dir1_dev = abs(dir1_lambda - optimal_dir1)
            if dir1_dev > 0.05:
                spacing_gain_adj -= 0.3 * (dir1_dev - 0.05) / 0.05
                spacing_fb_adj += 0.5 if dir1_lambda < optimal_dir1 else -0.5
        spacing_gain_adj = round(max(-1.5, min(0.5, spacing_gain_adj)), 2)
        spacing_fb_adj = round(max(-4.0, min(3.0, spacing_fb_adj)), 1)
        if request.boom_lock_enabled and request.max_boom_length:
            requested_lambda = 0.12 if request.close_driven else (0.22 if request.far_driven else 0.18)
            actual_vs_requested = abs(refl_driven_lambda - requested_lambda)
            if actual_vs_requested > 0.02 and (request.close_driven or request.far_driven):
                notes.append(f"Note: Boom restraint limits driven spacing to {round(refl_driven_lambda, 3)}\u03bb (requested {requested_lambda}\u03bb). Use a longer boom for full effect.")

    base_gain += spacing_gain_adj
    height_m = convert_height_to_meters(request.height_from_ground, request.height_unit)
    predicted_gain = round(base_gain + calculate_ground_gain(height_m / wavelength_m, "horizontal") - compression_penalty, 1)

    if n <= 5: predicted_fb = {2: 14, 3: 20, 4: 24, 5: 26}.get(n, 14)
    else: predicted_fb = 20 + 3 * math.log2(max(n - 2, 1))
    if final_boom > 0 and standard_boom_in > 0:
        boom_ratio = final_boom / standard_boom_in
        if boom_ratio > 0 and boom_ratio != 1.0:
            fb_boom_adj = round(1.5 * math.log2(boom_ratio), 1)
            predicted_fb += fb_boom_adj
    predicted_fb += spacing_fb_adj
    if not use_reflector: predicted_fb -= 8
    if request.taper and request.taper.enabled:
        predicted_fb += 1.5 * request.taper.num_tapers
    if not use_reflector:
        notes.append(f"Note: No reflector mode - reduced F/B ratio")

    return AutoTuneOutput(optimized_elements=elements, predicted_swr=predicted_swr, predicted_gain=predicted_gain, predicted_fb_ratio=round(max(predicted_fb, 6), 1), optimization_notes=notes)
