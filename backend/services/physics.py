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



# ── Shared Physics Helpers (used by both calculate and design_gamma_match) ──

def get_gamma_hardware_defaults(num_elements: int) -> dict:
    """Unified gamma match hardware defaults with per-element tube/rod sizing."""
    if num_elements <= 2:
        rod_od = 0.875
        tube_od = 1.0
        tube_length = 4.0
    elif num_elements <= 3:
        rod_od = 0.750
        tube_od = 0.875
        tube_length = 3.5
    else:
        rod_od = 0.625
        tube_od = 0.750
        tube_length = 3.0
    wall = 0.049
    teflon_length = tube_length + 1.0  # extends 1" past tube open end (RF arc prevention)
    return {
        "wall": wall,
        "rod_od": rod_od,
        "tube_od": tube_od,
        "rod_spacing": 3.5,
        "tube_length": tube_length,
        "teflon_length": teflon_length,
        "max_insertion": tube_length - 0.5,  # rod stops 0.5" before far end of tube
        "rod_length": 22.0 if num_elements <= 6 else 30.0,
    }


def compute_feedpoint_impedance(num_elements: int, wavelength_m: float,
                                reflector_spacing_in: float = 48.0,
                                director_spacings_in: list = None,
                                reflector_length_in: float = 214.0) -> float:
    """Yagi feedpoint impedance from mutual coupling model.

    Args:
        director_spacings_in: cumulative distances from driven element to each director (inches).
    Returns:
        R_feed in ohms, clamped to [12, 73].
    """
    r_feed = 73.0
    if num_elements >= 2 and reflector_spacing_in > 0:
        refl_gap_wl = (reflector_spacing_in * 0.0254) / wavelength_m if wavelength_m > 0 else 0.18
        refl_len_m = reflector_length_in * 0.0254
        half_wave_m = wavelength_m / 2.0
        refl_detuning = (refl_len_m - half_wave_m) / half_wave_m if half_wave_m > 0 else 0
        refl_q = 12.0
        refl_coupling_strength = 1.0 / math.sqrt(1.0 + (refl_q * refl_detuning * 2) ** 2)
        refl_factor = max(0.35, 0.30 + refl_gap_wl * 1.8)
        refl_factor = 1.0 - (1.0 - refl_factor) * refl_coupling_strength
        r_feed *= refl_factor

    num_directors = max(0, num_elements - 2)
    if num_directors >= 1:
        d1_gap_in = director_spacings_in[0] if director_spacings_in and len(director_spacings_in) >= 1 else 48.0
        d1_gap_wl = (d1_gap_in * 0.0254) / wavelength_m if wavelength_m > 0 else 0.13
        d1_factor = max(0.70, 0.72 + d1_gap_wl * 1.2)
        r_feed *= d1_factor

    for i in range(1, num_directors):
        if director_spacings_in and i < len(director_spacings_in) and i - 1 < len(director_spacings_in):
            gap_in = director_spacings_in[i] - director_spacings_in[i - 1]
        else:
            gap_in = 48.0
        gap_wl = (gap_in * 0.0254) / wavelength_m if wavelength_m > 0 else 0.15
        factor = max(0.85, 0.85 + gap_wl * 0.5)
        r_feed *= factor

    return round(max(12.0, min(73.0, r_feed)), 1)


def compute_element_resonant_freq(driven_length_in: float, frequency_mhz: float,
                                  wavelength_m: float, num_elements: int,
                                  reflector_spacing_in: float = 48.0,
                                  director_spacings_in: list = None) -> float:
    """Element resonant frequency accounting for mutual coupling.

    Args:
        director_spacings_in: cumulative distances from driven element to each director (inches).
    """
    ideal_half_wave_m = wavelength_m / 2.0
    driven_len_m = driven_length_in * 0.0254
    if ideal_half_wave_m <= 0 or driven_len_m <= 0:
        return frequency_mhz
    length_ratio = driven_len_m / ideal_half_wave_m
    res_freq = frequency_mhz / length_ratio if length_ratio > 0 else frequency_mhz

    if num_elements >= 2 and reflector_spacing_in > 0:
        refl_gap_wl = (reflector_spacing_in * 0.0254) / wavelength_m if wavelength_m > 0 else 0.2
        refl_coupling = 0.067 * math.exp(-4.0 * max(refl_gap_wl, 0.02))
        res_freq *= (1.0 - refl_coupling)

    for d_idx in range(max(0, num_elements - 2)):
        if director_spacings_in and d_idx < len(director_spacings_in):
            d_gap_in = director_spacings_in[d_idx]
        else:
            d_gap_in = (d_idx + 1) * 48.0
        d_gap_wl = (d_gap_in * 0.0254) / wavelength_m if wavelength_m > 0 else 0.15
        dir_coupling = 0.015 * math.exp(-5.0 * max(d_gap_wl, 0.02)) * (0.7 ** d_idx)
        res_freq *= (1.0 - dir_coupling)

    return round(res_freq, 3)



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
                           gamma_cap_pf: float = None, gamma_tube_od: float = None,
                           hairpin_rod_dia: float = None, hairpin_rod_spacing: float = None,
                           hairpin_length_in: float = None, hairpin_boom_gap: float = None,
                           operating_freq_mhz: float = 27.185,
                           num_elements: int = 3,
                           driven_element_half_length_in: float = 101.5,
                           driven_element_dia_in: float = 0.5,
                           element_resonant_freq_mhz: float = 27.185) -> tuple:
    if feed_type == "gamma":
        hw = get_gamma_hardware_defaults(num_elements)
        wall = hw["wall"]
        rod_dia = gamma_rod_dia if gamma_rod_dia and gamma_rod_dia > 0 else hw["rod_od"]
        rod_spacing = gamma_rod_spacing if gamma_rod_spacing and gamma_rod_spacing > 0 else hw["rod_spacing"]
        bar_inches = gamma_bar_pos if gamma_bar_pos is not None else 18.0

        if gamma_tube_od and gamma_tube_od > 0:
            actual_tube_od = gamma_tube_od
            tube_id = actual_tube_od - 2 * wall
        else:
            actual_tube_od = hw["tube_od"]
            tube_id = actual_tube_od - 2 * wall

        wavelength_in = 11802.71 / operating_freq_mhz
        gamma_rod_length = hw["rod_length"]
        tube_length = hw["tube_length"]
        teflon_sleeve_in = hw["teflon_length"]
        max_insertion = hw["max_insertion"]

        if gamma_element_gap is not None:
            rod_insertion_in = max(0, min(gamma_element_gap, max_insertion))
        else:
            rod_insertion_in = 8.0
        insertion_ratio = rod_insertion_in / max(max_insertion, 0.1)

        # Coaxial capacitor: C = 2*pi*e0*er*L / ln(D/d)
        rod_od_actual = rod_dia
        if rod_insertion_in > 0 and tube_id > rod_od_actual:
            cap_per_inch = 1.413 * 2.1 / math.log(tube_id / rod_od_actual)
            insertion_cap_pf_exact = cap_per_inch * rod_insertion_in
            insertion_cap_pf = round(insertion_cap_pf_exact, 1)
        else:
            insertion_cap_pf_exact = 0
            insertion_cap_pf = 0
        user_cap = gamma_cap_pf if gamma_cap_pf and gamma_cap_pf > 0 else insertion_cap_pf_exact
        cap_ratio = round(user_cap / max(insertion_cap_pf, 1.0), 3) if insertion_cap_pf > 0 else 1.0

        # Z0 of gamma section (two-wire line with UNEQUAL conductors)
        # Driven element dia (d1) and gamma rod dia (d2) differ
        # Z0 = 276 * log10(2 * D / sqrt(d1 * d2))
        geo_mean_dia = math.sqrt(driven_element_dia_in * rod_dia)
        if rod_spacing > geo_mean_dia / 2:
            z0_gamma = 276.0 * math.log10(2.0 * rod_spacing / geo_mean_dia)
        else:
            z0_gamma = 300.0

        # Step-up ratio from bar position geometry with rod coupling:
        # K = 1 + (bar_pos / half_element_length) * coupling_multiplier
        # coupling_multiplier = Z0_gamma / 73  (normalized rod coupling)
        # This ties K to the physical bar position: different Yagis need different
        # bar positions for a 50Ω match (more elements → lower R → bar further out).
        half_len = max(driven_element_half_length_in, 1.0)
        coupling_multiplier = z0_gamma / 73.0  # 73Ω = free-space half-wave dipole impedance
        step_up = 1.0 + (bar_inches / half_len) * coupling_multiplier
        k_sq = step_up ** 2
        # Ideal bar position for perfect resistive match: R_feed * K² = 50
        # → K_ideal = sqrt(50 / R_feed) → bar_ideal = half_len * (K_ideal - 1) / coupling
        k_ideal = math.sqrt(50.0 / max(feedpoint_r, 5.0))
        bar_ideal_inches = round(half_len * (k_ideal - 1.0) / coupling_multiplier, 2)

        # Shorted transmission line stub: X_stub = Z0 * tan(beta * L)
        wavelength_m = 299792458.0 / (operating_freq_mhz * 1e6)
        bar_pos_m = bar_inches * 0.0254
        beta_l = 2.0 * math.pi * bar_pos_m / wavelength_m
        x_stub = z0_gamma * math.tan(beta_l)

        # Series capacitor: X_cap = -1/(2*pi*f*C)
        omega = 2.0 * math.pi * operating_freq_mhz * 1e6
        x_cap = -1.0 / (omega * (user_cap * 1e-12)) if user_cap > 0 else 0

        net_reactance = x_stub + x_cap

        # Stub inductance: L = X_stub / (2*pi*f)
        stub_inductance_nh = round(x_stub / omega * 1e9, 2) if omega > 0 else 0

        # Antenna reactance at operating frequency (driven element may not be resonant here)
        # X_ant = Q * R * (f/f_res - f_res/f)  — capacitive if element resonates above operating freq
        antenna_q = 12.0  # typical Yagi Q
        if element_resonant_freq_mhz > 0 and abs(element_resonant_freq_mhz - operating_freq_mhz) > 0.01:
            fr_ratio = operating_freq_mhz / element_resonant_freq_mhz
            x_antenna = antenna_q * feedpoint_r * (fr_ratio - 1.0 / fr_ratio)
        else:
            x_antenna = 0.0

        # Transformed impedance at operating frequency
        # R_matched = feedpoint_R * K^2
        # X_matched = X_antenna*K + X_stub + X_cap  (antenna reactance is K-transformed)
        z_r_matched = feedpoint_r * k_sq
        z_x_matched = (x_antenna * step_up) + x_stub + x_cap

        # Reflection coefficient: Gamma = (Z_matched - Z0) / (Z_matched + Z0)
        z0 = 50.0
        denom = (z_r_matched + z0) ** 2 + z_x_matched ** 2
        gamma_re = ((z_r_matched - z0) * (z_r_matched + z0) + z_x_matched ** 2) / denom if denom > 0 else 0
        gamma_im = (2 * z_x_matched * z0) / denom if denom > 0 else 0
        gamma_mag = min(math.sqrt(gamma_re ** 2 + gamma_im ** 2), 0.999)

        # SWR from reflection coefficient
        matched_swr = round((1 + gamma_mag) / (1 - gamma_mag), 3) if gamma_mag < 1.0 else 99.0
        matched_swr = max(1.0, matched_swr)

        tuning_quality = round(1.0 / max(matched_swr, 1.0), 3)

        # Q-factor and bandwidth
        q_factor = round(8.0 + insertion_ratio * 17.0, 1)
        gamma_bw_mhz = round(operating_freq_mhz / q_factor, 3)

        # Resonant frequency: use actual element resonant frequency
        # The gamma match transforms impedance but the system resonates 
        # where total X = 0 (antenna X*K + stub + cap = 0)
        resonant_freq = round(element_resonant_freq_mhz, 3)

        bw_label = f"{gamma_bw_mhz:.2f} MHz (Q={q_factor:.0f})"
        info = {"type": "Gamma Match",
                "description": "Rod with teflon sleeve slides into tube creating variable series capacitor",
                "original_swr": round(swr, 3), "matched_swr": matched_swr, "swr_at_resonance": matched_swr,
                "tuning_quality": tuning_quality,
                "rod_insertion": round(insertion_ratio, 3), "rod_insertion_inches": round(rod_insertion_in, 2),
                "tube_length_inches": round(tube_length, 2), "teflon_sleeve_inches": teflon_sleeve_in,
                "insertion_cap_pf": insertion_cap_pf,
                "bar_position_inches": bar_inches,
                "step_up_ratio": round(step_up, 3),
                "step_up_k_squared": round(k_sq, 3),
                "ideal_bar_position_inches": bar_ideal_inches,
                "ideal_step_up_ratio": round(k_ideal, 3),
                "coupling_multiplier": round(coupling_multiplier, 3),
                "cap_ratio": cap_ratio, "resonant_freq_mhz": resonant_freq,
                "q_factor": q_factor, "gamma_bandwidth_mhz": gamma_bw_mhz,
                "bandwidth_effect": bw_label, "bandwidth_mult": round(max(0.6, 1.0 - (q_factor - 12) * 0.02), 2),
                "z0_gamma": round(z0_gamma, 1),
                "x_stub": round(x_stub, 2), "x_cap": round(x_cap, 2),
                "x_antenna": round(x_antenna, 2),
                "stub_inductance_nh": stub_inductance_nh,
                "driven_element_dia_in": driven_element_dia_in,
                "element_resonant_freq_mhz": round(element_resonant_freq_mhz, 3),
                "net_reactance": round(net_reactance, 2),
                "z_matched_r": round(z_r_matched, 2), "z_matched_x": round(z_x_matched, 2),
                "reflection_coefficient": round(gamma_mag, 6),
                "technical_notes": {
                    "mechanism": "Teflon-sleeve coaxial capacitor in series with shorted bar",
                    "tube": f"{round(tube_length, 1)}\" tube at feedpoint, rod slides in with {round(teflon_sleeve_in, 0):.0f}\" teflon sleeve",
                    "shorting_bar": "4\" bar slides along rod + driven element to tune",
                    "asymmetry": "Minor beam skew", "pattern_impact": "Negligible for most operations",
                    "advantage": "Feeds balanced Yagi with unbalanced coax",
                    "tuning": "Bar position sets stub inductance, rod insertion sets capacitance",
                    "mitigation": "Proper tuning minimizes beam skew"}}
        info["hardware"] = {
            "rod_od": round(rod_dia, 3), "tube_od": round(tube_id + 2 * wall, 3),
            "tube_id": round(tube_id, 3),
            "tube_wall": wall, "rod_spacing": round(rod_spacing, 1),
            "rod_length": round(gamma_rod_length, 1), "tube_length": tube_length,
            "teflon_length": teflon_sleeve_in, "cap_per_inch": round(1.413 * 2.1 / math.log(tube_id / rod_od_actual), 3) if tube_id > rod_od_actual else 0,
        }
        # Debug trace: every computation step in code execution order
        info["debug_trace"] = [
            {"step": 1, "label": "HARDWARE SELECTION", "items": [
                {"var": "num_elements", "val": num_elements, "unit": ""},
                {"var": "rod_od", "val": round(rod_dia, 3), "unit": "in"},
                {"var": "tube_od", "val": round(actual_tube_od, 3), "unit": "in"},
                {"var": "tube_id", "val": round(tube_id, 3), "unit": "in", "formula": f"{actual_tube_od} - 2×{wall}"},
                {"var": "wall", "val": wall, "unit": "in"},
                {"var": "rod_spacing", "val": round(rod_spacing, 1), "unit": "in"},
            ]},
            {"step": 2, "label": "WAVELENGTH & ROD", "items": [
                {"var": "freq", "val": operating_freq_mhz, "unit": "MHz"},
                {"var": "wavelength", "val": round(wavelength_in, 2), "unit": "in", "formula": f"11802.71 / {operating_freq_mhz}"},
                {"var": "gamma_rod_length", "val": round(gamma_rod_length, 2), "unit": "in", "formula": "36.0 (fixed)"},
                {"var": "tube_length", "val": round(tube_length, 1), "unit": "in"},
                {"var": "teflon_sleeve", "val": round(teflon_sleeve_in, 1), "unit": "in"},
            ]},
            {"step": 3, "label": "ROD INSERTION & CAPACITANCE", "items": [
                {"var": "rod_insertion", "val": round(rod_insertion_in, 2), "unit": "in"},
                {"var": "insertion_ratio", "val": round(insertion_ratio, 3), "unit": "", "formula": f"{round(rod_insertion_in,1)} / {round(max_insertion,1)}"},
                {"var": "cap_per_inch", "val": round(1.413 * 2.1 / math.log(tube_id / rod_od_actual), 3) if tube_id > rod_od_actual else 0, "unit": "pF/in", "formula": f"1.413×2.1 / ln({round(tube_id,3)}/{round(rod_od_actual,3)})"},
                {"var": "insertion_cap", "val": insertion_cap_pf, "unit": "pF", "formula": f"{round(1.413 * 2.1 / math.log(tube_id / rod_od_actual), 2) if tube_id > rod_od_actual else 0} × {round(rod_insertion_in,1)}"},
                {"var": "user_cap", "val": round(user_cap, 1), "unit": "pF"},
            ]},
            {"step": 4, "label": "Z0 (TWO-WIRE LINE)", "items": [
                {"var": "driven_element_dia", "val": driven_element_dia_in, "unit": "in"},
                {"var": "geo_mean_dia", "val": round(geo_mean_dia, 4), "unit": "in", "formula": f"√({driven_element_dia_in} × {round(rod_dia,3)})"},
                {"var": "Z0_gamma", "val": round(z0_gamma, 1), "unit": "Ω", "formula": f"276 × log10(2×{round(rod_spacing,1)} / {round(geo_mean_dia,4)})"},
            ]},
            {"step": 5, "label": "STEP-UP RATIO K", "items": [
                {"var": "coupling_mult", "val": round(coupling_multiplier, 3), "unit": "", "formula": f"{round(z0_gamma,1)} / 73"},
                {"var": "bar_position", "val": bar_inches, "unit": "in"},
                {"var": "half_element_len", "val": round(half_len, 1), "unit": "in"},
                {"var": "K", "val": round(step_up, 4), "unit": "", "formula": f"1 + ({bar_inches}/{round(half_len,1)}) × {round(coupling_multiplier,3)}"},
                {"var": "K²", "val": round(k_sq, 4), "unit": ""},
                {"var": "K_ideal", "val": round(k_ideal, 4), "unit": "", "formula": f"√(50 / {round(feedpoint_r,1)})"},
                {"var": "bar_ideal", "val": bar_ideal_inches, "unit": "in"},
            ]},
            {"step": 6, "label": "STUB REACTANCE", "items": [
                {"var": "wavelength_m", "val": round(wavelength_m, 4), "unit": "m"},
                {"var": "bar_pos_m", "val": round(bar_pos_m, 4), "unit": "m"},
                {"var": "β×L", "val": round(beta_l, 4), "unit": "rad"},
                {"var": "tan(β×L)", "val": round(math.tan(beta_l), 4), "unit": ""},
                {"var": "X_stub", "val": round(x_stub, 2), "unit": "Ω", "formula": f"{round(z0_gamma,1)} × tan({round(beta_l,4)})"},
                {"var": "L_stub", "val": stub_inductance_nh, "unit": "nH", "formula": f"X_stub / (2πf)"},
            ]},
            {"step": 7, "label": "SERIES CAP REACTANCE", "items": [
                {"var": "ω", "val": round(omega, 0), "unit": "rad/s"},
                {"var": "C_series", "val": round(user_cap, 1), "unit": "pF"},
                {"var": "X_cap", "val": round(x_cap, 2), "unit": "Ω", "formula": f"-1 / (ω × C)"},
            ]},
            {"step": 8, "label": "ANTENNA REACTANCE", "items": [
                {"var": "element_res_freq", "val": round(element_resonant_freq_mhz, 3), "unit": "MHz"},
                {"var": "f_op/f_res", "val": round(operating_freq_mhz / max(element_resonant_freq_mhz, 1), 4), "unit": ""},
                {"var": "X_antenna", "val": round(x_antenna, 2), "unit": "Ω", "formula": f"Q×R×(fr-1/fr)"},
                {"var": "X_ant×K", "val": round(x_antenna * step_up, 2), "unit": "Ω"},
            ]},
            {"step": 9, "label": "NET REACTANCE", "items": [
                {"var": "X_ant×K", "val": round(x_antenna * step_up, 2), "unit": "Ω"},
                {"var": "X_stub", "val": round(x_stub, 2), "unit": "Ω"},
                {"var": "X_cap", "val": round(x_cap, 2), "unit": "Ω"},
                {"var": "X_total", "val": round(z_x_matched, 2), "unit": "Ω", "formula": f"{round(x_antenna*step_up,1)} + {round(x_stub,1)} + ({round(x_cap,1)})"},
            ]},
            {"step": 10, "label": "IMPEDANCE TRANSFORM", "items": [
                {"var": "R_feed", "val": round(feedpoint_r, 2), "unit": "Ω"},
                {"var": "R_matched", "val": round(z_r_matched, 2), "unit": "Ω", "formula": f"{round(feedpoint_r,1)} × {round(k_sq,3)}"},
                {"var": "X_matched", "val": round(z_x_matched, 2), "unit": "Ω"},
                {"var": "Z_matched", "val": f"{round(z_r_matched,1)} {'+' if z_x_matched >= 0 else ''}{round(z_x_matched,1)}j", "unit": "Ω"},
            ]},
            {"step": 11, "label": "REFLECTION & SWR", "items": [
                {"var": "Z0_line", "val": 50.0, "unit": "Ω"},
                {"var": "Γ_real", "val": round(gamma_re, 6), "unit": ""},
                {"var": "Γ_imag", "val": round(gamma_im, 6), "unit": ""},
                {"var": "|Γ|", "val": round(gamma_mag, 6), "unit": ""},
                {"var": "SWR", "val": matched_swr, "unit": ":1", "formula": f"(1+{round(gamma_mag,4)}) / (1-{round(gamma_mag,4)})"},
            ]},
        ]
        return matched_swr, info
    elif feed_type == "hairpin":
        # Physics-based hairpin (beta) match: L-network impedance transformation
        # Topology: shortened driven element (series X_C) + shorted stub (shunt X_L)
        h_rod_dia = hairpin_rod_dia if hairpin_rod_dia and hairpin_rod_dia > 0 else 0.25
        h_rod_spacing = hairpin_rod_spacing if hairpin_rod_spacing and hairpin_rod_spacing > 0 else 1.0
        boom_gap = hairpin_boom_gap if hairpin_boom_gap is not None else 1.0

        # Hairpin Z0 (balanced twin-lead, natural log form)
        if h_rod_spacing > h_rod_dia / 2:
            hairpin_z0 = 120.0 * math.log(2.0 * h_rod_spacing / h_rod_dia)
        else:
            hairpin_z0 = 200.0

        freq_hz = operating_freq_mhz * 1e6
        wl_m = 299792458.0 / freq_hz if freq_hz > 0 else 11.0
        wl_in = wl_m * 39.3701

        if feedpoint_r < 50.0 and feedpoint_r > 5.0:
            # L-network: step up R_feed to 50 ohms
            q_match = math.sqrt(50.0 / feedpoint_r - 1.0)
            xl_needed = 50.0 / q_match
            xc_needed = q_match * feedpoint_r

            # Ideal hairpin length for perfect match
            ideal_length_in = (math.atan(xl_needed / hairpin_z0) / (2.0 * math.pi)) * wl_in

            # Actual hairpin length (user-provided or ideal)
            actual_length = hairpin_length_in if hairpin_length_in and hairpin_length_in > 0 else ideal_length_in

            # Actual X_L from hairpin at this length
            beta_l = (2.0 * math.pi * actual_length) / wl_in
            if abs(beta_l) < math.pi / 2.0 - 0.01:
                xl_actual = hairpin_z0 * math.tan(beta_l)
            else:
                xl_actual = xl_needed

            # Complex impedance: Z_feed = R - jX_C, Z_hairpin = jX_L
            # Z_in = (Z_feed * Z_hp) / (Z_feed + Z_hp) — parallel combination
            z_feed = complex(feedpoint_r, -xc_needed)
            z_hp = complex(0, xl_actual)
            z_sum = z_feed + z_hp
            if abs(z_sum) > 0.001:
                z_in = (z_feed * z_hp) / z_sum
            else:
                z_in = complex(50, 0)

            # Reflection coefficient and SWR
            gamma_complex = (z_in - 50.0) / (z_in + 50.0)
            gamma_mag = abs(gamma_complex)
            matched_swr = (1.0 + gamma_mag) / (1.0 - gamma_mag) if gamma_mag < 0.99 else 99.0

            # Power calculations (reference 5W into 50 ohm)
            p_forward = 5.0
            v_forward = math.sqrt(p_forward * 50.0)  # 15.81V
            p_reflected = p_forward * gamma_mag ** 2
            p_net = p_forward - p_reflected

            if boom_gap < 0.5:
                matched_swr *= (1.0 + max(0, (0.5 - boom_gap) * 0.15))

            # Driven element shortening: X_C from element reactance slope
            driven_half_len = driven_element_half_length_in
            driven_dia = driven_element_dia_in
            z_char = 120.0 * (math.log(2.0 * driven_half_len / (driven_dia / 2.0)) - 1.0) if driven_dia > 0 else 600.0
            shorten_per_side = xc_needed * wl_in / (4.0 * math.pi * z_char) if z_char > 0 else 0
            new_total_length = (driven_half_len - shorten_per_side) * 2.0

            info = {
                "type": "Hairpin Match",
                "description": "L-network: shortened driven element (series C) + shorted stub (shunt L) transforms feedpoint to 50\u03a9",
                "original_swr": round(swr, 3),
                "matched_swr": round(max(1.0, matched_swr), 3),
                "q_match": round(q_match, 3),
                "xl_needed": round(xl_needed, 2),
                "xc_needed": round(xc_needed, 2),
                "xl_actual": round(xl_actual, 2),
                "ideal_hairpin_length_in": round(ideal_length_in, 2),
                "actual_hairpin_length_in": round(actual_length, 2),
                "hairpin_z0": round(hairpin_z0, 1),
                "shorten_per_side_in": round(shorten_per_side, 2),
                "shortened_total_length_in": round(new_total_length, 2),
                "target_element_reactance": round(-xc_needed, 2),
                "tuning_instructions": [
                    {"step": "Prune", "action": f"Shorten driven element by {round(shorten_per_side * 2, 2)}\" total ({round(shorten_per_side, 2)}\" each side)", "value": f"-j{round(xc_needed, 1)} ohms"},
                    {"step": "Set Bar", "action": f"Slide shorting bar to {round(actual_length, 2)}\" from feedpoint", "value": f"+j{round(xl_actual, 1)} ohms"},
                    {"step": "Result", "action": f"Predicted SWR center at {round(operating_freq_mhz, 3)} MHz", "value": f"{round(max(1.0, matched_swr), 3)}:1"},
                ],
                "z_in_r": round(z_in.real, 2),
                "z_in_x": round(z_in.imag, 2),
                "gamma_mag": round(gamma_mag, 4),
                "p_forward_w": round(p_forward, 2),
                "p_reflected_w": round(p_reflected, 3),
                "p_net_w": round(p_net, 2),
                "v_forward_v": round(v_forward, 2),
                "bandwidth_effect": "Broadband (minimal effect)",
                "bandwidth_mult": 1.0,
                "technical_notes": {
                    "mechanism": "Shorted transmission line stub (L-network)",
                    "asymmetry": "Symmetrical design \u2014 no beam skew",
                    "advantage": "Simple construction, broadband",
                    "tuning": "Adjust hairpin length to set inductive reactance",
                    "tradeoff": "Requires split driven element",
                    "balun_note": "Use current choke balun alongside",
                },
            }
        else:
            matched_swr = swr
            note = "Feedpoint R \u2265 50\u03a9. Standard hairpin (shunt L) cannot step down impedance. Use Gamma match or series capacitor." if feedpoint_r >= 50.0 else "Feedpoint R too low for reliable hairpin match."
            info = {
                "type": "Hairpin Match",
                "description": note,
                "original_swr": round(swr, 3),
                "matched_swr": round(swr, 3),
                "topology_note": note,
                "bandwidth_effect": "N/A",
                "bandwidth_mult": 1.0,
                "technical_notes": {"mechanism": "Hairpin not applicable", "suggestion": "Use Gamma match for this impedance"},
            }
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

    feed_type = input_data.feed_type

    # Feedpoint impedance via shared mutual coupling model
    num_directors = len([e for e in input_data.elements if e.element_type == "director"])
    has_reflector_for_z = any(e.element_type == "reflector" for e in input_data.elements)
    driven_el = next((e for e in input_data.elements if e.element_type == "driven"), None)
    refl_el = next((e for e in input_data.elements if e.element_type == "reflector"), None)
    dir_els = sorted([e for e in input_data.elements if e.element_type == "director"], key=lambda e: e.position)

    refl_spacing_in = abs(driven_el.position - refl_el.position) if driven_el and refl_el else 48.0
    dir_spacings_in = [abs(d.position - driven_el.position) for d in dir_els] if driven_el and dir_els else None
    refl_length_in = refl_el.length if refl_el else 214.0

    yagi_feedpoint_r = compute_feedpoint_impedance(
        num_elements=n, wavelength_m=wavelength,
        reflector_spacing_in=refl_spacing_in,
        director_spacings_in=dir_spacings_in,
        reflector_length_in=refl_length_in,
    )

    # Apply impedance mismatch to SWR
    impedance_swr = max(yagi_feedpoint_r / 50.0, 50.0 / yagi_feedpoint_r)
    swr = round(max(1.0, min(swr * 0.3 + impedance_swr * 0.7, 10.0)), 2)

    # Element resonant frequency via shared coupling model
    element_resonant_freq = center_freq
    if driven_el:
        element_resonant_freq = compute_element_resonant_freq(
            driven_length_in=driven_el.length, frequency_mhz=center_freq,
            wavelength_m=wavelength, num_elements=n,
            reflector_spacing_in=refl_spacing_in,
            director_spacings_in=dir_spacings_in,
        )

    # Get driven element half-length and diameter for geometric K calculation
    driven_half_length_in = driven_el.length / 2.0 if driven_el else 101.5
    driven_dia_in = driven_el.diameter if driven_el else 0.5

    matched_swr, matching_info = apply_matching_network(
        swr, feed_type, feedpoint_r=yagi_feedpoint_r,
        gamma_rod_dia=input_data.gamma_rod_dia,
        gamma_rod_spacing=input_data.gamma_rod_spacing,
        gamma_bar_pos=input_data.gamma_bar_pos,
        gamma_element_gap=input_data.gamma_element_gap,
        gamma_cap_pf=input_data.gamma_cap_pf,
        gamma_tube_od=input_data.gamma_tube_od,
        hairpin_rod_dia=input_data.hairpin_rod_dia,
        hairpin_rod_spacing=input_data.hairpin_rod_spacing,
        hairpin_length_in=input_data.hairpin_length_in,
        hairpin_boom_gap=input_data.hairpin_boom_gap,
        operating_freq_mhz=center_freq,
        num_elements=input_data.num_elements,
        driven_element_half_length_in=driven_half_length_in,
        driven_element_dia_in=driven_dia_in,
        element_resonant_freq_mhz=element_resonant_freq,
    )
    # Add element-based resonant freq to matching info
    if matching_info and feed_type != "direct":
        matching_info["element_resonant_freq_mhz"] = element_resonant_freq
    if feed_type != "direct":
        swr = round(matched_swr, 3)

    # Hairpin design: matching_info now contains all design data from apply_matching_network
    if feed_type == "hairpin":
        if "xl_needed" in matching_info:
            matching_info["hairpin_design"] = {
                "feedpoint_impedance_ohms": yagi_feedpoint_r,
                "target_impedance_ohms": 50.0,
                "q_match": matching_info.get("q_match", 0),
                "required_xl_ohms": matching_info.get("xl_needed", 0),
                "required_xc_ohms": matching_info.get("xc_needed", 0),
                "xl_actual_ohms": matching_info.get("xl_actual", 0),
                "z0_ohms": matching_info.get("hairpin_z0", 0),
                "ideal_hairpin_length_in": matching_info.get("ideal_hairpin_length_in", 0),
                "actual_hairpin_length_in": matching_info.get("actual_hairpin_length_in", 0),
                "shorten_per_side_in": matching_info.get("shorten_per_side_in", 0),
                "shortened_total_length_in": matching_info.get("shortened_total_length_in", 0),
                "wavelength_inches": round(wavelength * 39.3701, 2),
            }
        elif "topology_note" in matching_info:
            matching_info["hairpin_design"] = {
                "feedpoint_impedance_ohms": yagi_feedpoint_r,
                "target_impedance_ohms": 50.0,
                "topology_note": matching_info["topology_note"],
                "wavelength_inches": round(wavelength * 39.3701, 2),
            }

    # Gamma match design calculations
    if feed_type == "gamma" and yagi_feedpoint_r < 50.0:
        wavelength_in = wavelength * 39.3701
        step_up_ratio = round(math.sqrt(50.0 / yagi_feedpoint_r), 3)
        # Driven element diameter (get from actual element data)
        driven_elem_calc = next((e for e in input_data.elements if e.element_type == "driven"), None)
        element_dia = float(driven_elem_calc.diameter) if driven_elem_calc else 0.5
        # Use actual hardware from matching calculation
        hw = matching_info.get("hardware", {})
        gamma_rod_dia = hw.get("rod_od", 0.500)
        gamma_rod_spacing = hw.get("rod_spacing", 3.5)
        gamma_rod_length = 22.0 if input_data.num_elements <= 6 else 30.0
        design_tube_length = hw.get("tube_length", 3.0)
        design_tube_id = hw.get("tube_id", 0.652)
        design_rod_od = gamma_rod_dia
        # Series capacitance: from actual coaxial geometry (rod insertion into tube)
        rod_insertion_design = input_data.gamma_element_gap if input_data.gamma_element_gap is not None else 11.0
        rod_insertion_design = max(0, min(rod_insertion_design, design_tube_length))
        if rod_insertion_design > 0 and design_tube_id > design_rod_od:
            design_cap_per_inch = 1.413 * 2.1 / math.log(design_tube_id / design_rod_od)
            design_auto_cap_pf = round(design_cap_per_inch * rod_insertion_design, 1)
        else:
            design_auto_cap_pf = 0
        design_user_cap = input_data.gamma_cap_pf if input_data.gamma_cap_pf and input_data.gamma_cap_pf > 0 else design_auto_cap_pf
        # Shorting bar position from center (approximate)
        shorting_bar_pos = round(gamma_rod_length * 0.667, 2)
        matching_info["gamma_design"] = {
            "feedpoint_impedance_ohms": yagi_feedpoint_r,
            "target_impedance_ohms": 50.0,
            "step_up_ratio": step_up_ratio,
            "element_diameter_in": element_dia,
            "gamma_rod_diameter_in": gamma_rod_dia,
            "gamma_rod_spacing_in": gamma_rod_spacing,
            "gamma_rod_length_in": gamma_rod_length,
            "tube_length_in": round(design_tube_length, 1),
            "teflon_sleeve_in": 31.0 if input_data.num_elements <= 2 else 23.0,
            "capacitance_pf": design_user_cap,
            "auto_capacitance_pf": design_auto_cap_pf,
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

    # Return loss from complex impedance: Gamma = (Z - Z0) / (Z + Z0)
    # For gamma match: use physics-based Z from matching network model
    # For hairpin/direct: use feedpoint impedance with reactance model
    z_0 = 50.0  # feedline characteristic impedance
    antenna_q = 12.0  # typical Yagi Q

    if feed_type == "gamma" and matching_info and "z_matched_r" in matching_info:
        # Physics-based impedance from unified gamma match model
        z_r = matching_info["z_matched_r"]
        z_x = matching_info["z_matched_x"]
    elif feed_type == "hairpin":
        # Use complex impedance from matching_info
        if matching_info and "xl_actual" in matching_info and "xc_needed" in matching_info:
            z_r = matching_info.get("z_in_r", 50.0)
            z_x = matching_info.get("z_in_x", 0.0)
        else:
            z_r = 50.0
            z_x = 0.0
    else:
        # Direct feed: reactance from element resonance vs operating freq
        z_r = yagi_feedpoint_r
        if element_resonant_freq > 0:
            freq_ratio = center_freq / element_resonant_freq
            z_x = antenna_q * z_r * (freq_ratio - 1.0 / freq_ratio)
        else:
            z_x = 0.0

    # Complex reflection coefficient: Γ = (Z_ant - Z_0) / (Z_ant + Z_0)
    # Z_ant = z_r + j*z_x, Z_0 = 50 (real)
    gamma_real = ((z_r - z_0) * (z_r + z_0) + z_x * z_x) / ((z_r + z_0) ** 2 + z_x ** 2)
    gamma_imag = (2 * z_x * z_0) / ((z_r + z_0) ** 2 + z_x ** 2)  # note: sign doesn't matter for magnitude
    reflection_coefficient = round(math.sqrt(gamma_real ** 2 + gamma_imag ** 2), 8)
    reflection_coefficient = min(reflection_coefficient, 0.999)  # clamp

    if reflection_coefficient > 1e-6:
        return_loss_db = round(-20 * math.log10(reflection_coefficient), 2)
        return_loss_db = min(return_loss_db, 80.0)  # practical ceiling for real-world measurements
    else:
        return_loss_db = 80.0

    swr_from_gamma = (1 + reflection_coefficient) / (1 - reflection_coefficient) if reflection_coefficient < 1.0 else 99.0
    # SWR must be derived from reflection coefficient for consistency
    swr = round(max(1.0, swr_from_gamma), 2)
    mismatch_loss = 1 - (reflection_coefficient ** 2)
    mismatch_loss_db = round(-10 * math.log10(mismatch_loss), 3) if mismatch_loss > 0 else 0
    reflected_power_100w = round(100 * (reflection_coefficient ** 2), 2)
    reflected_power_1kw = round(1000 * (reflection_coefficient ** 2), 1)
    forward_power_100w = round(100 - reflected_power_100w, 2)
    forward_power_1kw = round(1000 - reflected_power_1kw, 1)
    impedance_high = round(50 * swr, 1)
    impedance_low = round(50 / swr, 1)

    # Coax feedline loss calculation
    coax_loss_table = {
        "ldf550a": {"name": "LDF5-50A 7/8\" Heliax", "loss_per_100ft": 0.22, "power_rating_watts": 14000, "velocity_factor": 0.89},
        "ldf450a": {"name": "LDF4-50A 1/2\" Heliax", "loss_per_100ft": 0.41, "power_rating_watts": 4800, "velocity_factor": 0.88},
        "rg213": {"name": "RG-213/U", "loss_per_100ft": 1.0, "power_rating_watts": 1000, "velocity_factor": 0.66},
        "rg213u": {"name": "RG-213/U", "loss_per_100ft": 1.0, "power_rating_watts": 1000, "velocity_factor": 0.66},
        "rg8": {"name": "RG-8/U", "loss_per_100ft": 1.0, "power_rating_watts": 1000, "velocity_factor": 0.66},
        "rg8u": {"name": "RG-8/U", "loss_per_100ft": 1.0, "power_rating_watts": 1000, "velocity_factor": 0.66},
        "rg8x": {"name": "RG-8X Mini-8", "loss_per_100ft": 1.6, "power_rating_watts": 300, "velocity_factor": 0.78},
        "rg8xmini8": {"name": "RG-8X Mini-8", "loss_per_100ft": 1.6, "power_rating_watts": 300, "velocity_factor": 0.78},
        "rg58": {"name": "RG-58/U", "loss_per_100ft": 2.4, "power_rating_watts": 200, "velocity_factor": 0.66},
        "rg58u": {"name": "RG-58/U", "loss_per_100ft": 2.4, "power_rating_watts": 200, "velocity_factor": 0.66},
    }
    coax_type = getattr(input_data, 'coax_type', 'ldf5-50a').lower().replace('-', '').replace('/', '').replace(' ', '')
    coax_length_ft = getattr(input_data, 'coax_length_ft', 100.0)
    transmit_power = getattr(input_data, 'transmit_power_watts', 500.0)
    coax_spec = coax_loss_table.get(coax_type, coax_loss_table["ldf550a"])
    coax_loss_db = round(coax_spec["loss_per_100ft"] * coax_length_ft / 100.0, 2)
    # Additional loss from SWR (standing waves increase cable heating)
    swr_loss_multiplier = 1.0 + (swr - 1.0) * 0.05 if swr > 1.0 else 1.0
    total_coax_loss_db = round(coax_loss_db * swr_loss_multiplier, 2)
    coax_loss_ratio = 10 ** (-total_coax_loss_db / 10)
    power_at_antenna = round(transmit_power * coax_loss_ratio, 1)
    reflected_power_watts = round(power_at_antenna * (reflection_coefficient ** 2), 2)
    forward_power_watts = round(power_at_antenna - reflected_power_watts, 2)
    coax_info = {
        "type": coax_spec["name"],
        "length_ft": coax_length_ft,
        "matched_loss_db": coax_loss_db,
        "total_loss_db": total_coax_loss_db,
        "swr_loss_multiplier": round(swr_loss_multiplier, 3),
        "power_rating_watts": coax_spec["power_rating_watts"],
        "velocity_factor": coax_spec["velocity_factor"],
        "transmit_power_watts": transmit_power,
    }

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
        swr = swr  # radials improve efficiency, NOT impedance match
        gain_breakdown["final_gain"] = gain_dbi
        antenna_efficiency = min(200.0, antenna_efficiency + g_bonus["efficiency_bonus"])

    # Antenna resonant frequency for impedance model — use element resonant freq
    # so the SWR curve reflects the actual driven element reactance at each frequency
    smith_res_freq = element_resonant_freq if element_resonant_freq > 0 else center_freq

    # ── Smith Chart Data: full-physics impedance sweep across frequency ──
    # Computed FIRST so we can derive the SWR curve from actual impedance
    smith_chart_data = []
    for i in range(-30, 31):
        freq = center_freq + (i * channel_spacing)
        sc_r = yagi_feedpoint_r
        if smith_res_freq > 0:
            fr = freq / smith_res_freq
            sc_x = antenna_q * yagi_feedpoint_r * (fr - 1.0 / fr)
        else:
            sc_x = 0.0
        if feed_type == "gamma" and matching_info and "tuning_quality" in matching_info:
            step_up = matching_info.get("step_up_ratio", math.sqrt(50.0 / max(yagi_feedpoint_r, 5.0)))
            if isinstance(step_up, str):
                try: step_up = float(str(step_up).replace(':1',''))
                except: step_up = math.sqrt(50.0 / max(yagi_feedpoint_r, 5.0))
            k_sq = step_up ** 2
            bar_pos_in = matching_info.get("bar_position_inches", 13.0)
            cap_pf = matching_info.get("insertion_cap_pf", 50.0)
            # Use pre-computed z0_gamma from apply_matching_network (actual hardware)
            z0_g = matching_info.get("z0_gamma", 300.0)
            freq_hz = freq * 1e6
            wavelength_m = 299792458.0 / freq_hz
            bar_pos_m = bar_pos_in * 0.0254
            beta_l = 2.0 * math.pi * bar_pos_m / wavelength_m
            x_stub = z0_g * math.tan(beta_l)
            omega_f = 2.0 * math.pi * freq_hz
            x_cap = -1.0 / (omega_f * (cap_pf * 1e-12)) if cap_pf > 0 else 0
            sc_r = sc_r * k_sq
            sc_x = (sc_x * step_up) + x_stub + x_cap
        elif feed_type == "hairpin" and matching_info and "tuning_quality" in matching_info:
            tq = matching_info["tuning_quality"]
            sc_x *= 0.10
            residual = (1.0 - tq) * 0.25
            sc_r = 50.0 * (1.0 + residual)
        denom_r = (sc_r + z_0) ** 2 + sc_x ** 2
        g_re = ((sc_r - z_0) * (sc_r + z_0) + sc_x ** 2) / denom_r if denom_r > 0 else 0
        g_im = (2 * sc_x * z_0) / denom_r if denom_r > 0 else 0
        omega = 2 * math.pi * freq * 1e6
        inductance_nh = round(sc_x / omega * 1e9, 2) if sc_x > 0 and omega > 0 else 0
        capacitance_pf_val = round(-1e12 / (omega * sc_x), 2) if sc_x < -0.5 and omega > 0 else 0
        if capacitance_pf_val > 1000:
            capacitance_pf_val = 0  # near-resonance artifact — not a real component value
        smith_chart_data.append({
            "freq": round(freq, 4),
            "z_real": round(sc_r, 2),
            "z_imag": round(sc_x, 2),
            "gamma_real": round(g_re, 5),
            "gamma_imag": round(g_im, 5),
            "inductance_nh": inductance_nh,
            "capacitance_pf": capacitance_pf_val,
        })

    # SWR curve — derived from Smith Chart full-physics impedance data
    swr_curve = []
    for idx, sc_pt in enumerate(smith_chart_data):
        g_mag = math.sqrt(sc_pt["gamma_real"] ** 2 + sc_pt["gamma_imag"] ** 2)
        g_mag = min(g_mag, 0.999)
        sc_swr = (1 + g_mag) / (1 - g_mag) if g_mag < 1.0 else 99.0
        sc_swr = round(max(1.0, min(sc_swr, 10.0)), 2)
        swr_curve.append({"frequency": sc_pt["freq"], "swr": sc_swr, "channel": idx - 30})
    usable_1_5 = round(sum(1 for p in swr_curve if p["swr"] <= 1.5) * channel_spacing, 3)
    usable_2_0 = round(sum(1 for p in swr_curve if p["swr"] <= 2.0) * channel_spacing, 3)

    # Derive gamma-tuned resonant frequency from actual SWR curve minimum
    if swr_curve:
        min_swr_pt = min(swr_curve, key=lambda p: p["swr"])
        curve_resonant_freq = min_swr_pt["frequency"]
    else:
        curve_resonant_freq = center_freq

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

    # Elevation pattern — full vertical plane showing all lobes, front AND back
    # Ground reflection creates multiple lobes: E(θ) = sin(2π·h·sin(θ)/λ)
    height_m = convert_height_to_meters(input_data.height_from_ground, input_data.height_unit)
    height_wl = height_m / wavelength if wavelength > 0 else 1.0
    elevation_pattern = []
    for angle in range(0, 361, 2):  # 0°=right(horizon), 90°=up, 180°=left(back horizon), 270°=down
        theta = math.radians(angle)
        if angle <= 180:
            # Front hemisphere: 0°=horizon, 90°=zenith, 180°=back horizon
            elev = angle  # elevation from front horizon
            if elev <= 90:
                # Front upper: main beam side
                elev_rad = math.radians(elev)
                # Ground reflection factor creates lobes
                ground_factor = abs(math.sin(2 * math.pi * height_wl * math.sin(elev_rad))) if height_wl > 0 else 1.0
                # Element pattern: Yagi forward gain tapers off at high elevations
                element_factor = max(0.05, math.cos(elev_rad * 0.7) ** 1.5)
                magnitude = ground_factor * element_factor * 100
            else:
                # Back upper: behind antenna, above horizon
                back_elev = 180 - elev  # angle above back horizon
                back_elev_rad = math.radians(back_elev)
                ground_factor = abs(math.sin(2 * math.pi * height_wl * math.sin(back_elev_rad))) if height_wl > 0 else 1.0
                # Back attenuation from F/B ratio
                back_atten = 10 ** (-fb_ratio / 20)
                element_factor = max(0.05, math.cos(back_elev_rad * 0.7) ** 1.5) * back_atten
                magnitude = ground_factor * element_factor * 100
        else:
            # Below ground plane (mirror/null) — show as minimal
            magnitude = 1.0
        elevation_pattern.append({"angle": angle, "magnitude": round(max(magnitude, 1), 1)})

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
        coax_loss_db=total_coax_loss_db, coax_info=coax_info,
        power_at_antenna_watts=power_at_antenna, reflected_power_watts=reflected_power_watts,
        forward_power_watts=forward_power_watts,
        takeoff_angle=takeoff_angle, takeoff_angle_description=takeoff_desc,
        height_performance=height_perf, ground_radials_info=ground_radials_info,
        noise_level="Moderate" if input_data.antenna_orientation in ("dual", "angle45") else ("High" if input_data.antenna_orientation == "vertical" else "Low"),
        noise_description="Dual polarity receives both H and V — moderate noise, excellent for fading/skip" if input_data.antenna_orientation == "dual" else ("Vertical polarization picks up more man-made noise (QRN)" if input_data.antenna_orientation == "vertical" else ("45\u00b0 slant receives both polarizations — moderate noise" if input_data.antenna_orientation == "angle45" else "Horizontal polarization has a quieter receive noise floor")),
        feed_type=feed_type, matching_info=matching_info, dual_polarity_info=dual_info,
        wind_load=wind_load_info,
        boom_correction_info=boom_correction if boom_correction.get("enabled") else boom_correction,
        resonant_freq_mhz=curve_resonant_freq,
        elevation_pattern=elevation_pattern,
        smith_chart_data=smith_chart_data,
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
        driven_override = getattr(request, 'close_driven', False) or getattr(request, 'far_driven', False)
        if driven_override == 'vclose': refl_driven_lambda = 0.08
        elif driven_override == 'close' or (driven_override is True and getattr(request, 'close_driven', False)): refl_driven_lambda = 0.12
        elif driven_override == 'far' or (driven_override is True and getattr(request, 'far_driven', False)): refl_driven_lambda = 0.22
        elif driven_override == 'vfar': refl_driven_lambda = 0.28
        elif getattr(request, 'close_driven', False) == 'vclose': refl_driven_lambda = 0.08
        elif getattr(request, 'close_driven', False) == 'close' or getattr(request, 'close_driven', False) is True: refl_driven_lambda = 0.12
        elif getattr(request, 'far_driven', False) == 'vfar': refl_driven_lambda = 0.28
        elif getattr(request, 'far_driven', False) == 'far' or getattr(request, 'far_driven', False) is True: refl_driven_lambda = 0.22
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
            close_d1 = getattr(request, 'close_dir1', False)
            far_d1 = getattr(request, 'far_dir1', False)
            if close_d1 == 'vclose':
                dir1_lambda = 0.06
            elif close_d1 == 'close' or close_d1 is True:
                dir1_lambda = 0.10
            elif far_d1 == 'vfar':
                dir1_lambda = 0.22
            elif far_d1 == 'far' or far_d1 is True:
                dir1_lambda = 0.18
            else:
                dir1_lambda = 0.13  # default

            # Determine second director spacing override
            close_d2 = getattr(request, 'close_dir2', False)
            far_d2 = getattr(request, 'far_dir2', False)
            if close_d2 == 'vclose':
                dir2_lambda = 0.08
            elif close_d2 == 'close' or close_d2 is True:
                dir2_lambda = 0.12
            elif far_d2 == 'vfar':
                dir2_lambda = 0.28
            elif far_d2 == 'far' or far_d2 is True:
                dir2_lambda = 0.22
            else:
                dir2_lambda = 0.16  # default (slightly wider than dir1)

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
                    if i == 1:
                        # Second director uses the dir2 override spacing
                        director_spacing = round(dir2_lambda * wavelength_in, 1)
                        if getattr(request, 'boom_lock_enabled', False) and getattr(request, 'max_boom_length', None):
                            max_dir2 = (request.max_boom_length - current_position) * 0.5
                            if director_spacing > max_dir2:
                                director_spacing = round(max_dir2, 1)
                        current_position += director_spacing
                        director_length = round(driven_length * (0.95 - i * 0.02), 1)
                        elements.append({"element_type": "director", "length": director_length, "diameter": 0.5, "position": round(current_position, 1)})
                        dir2_label = f"({dir2_lambda}\u03bb)" if (getattr(request, 'close_dir2', False) or getattr(request, 'far_dir2', False)) else ""
                        notes.append(f"Director 2: {director_length}\" at {round(current_position, 1)}\" {dir2_label}")
                    else:
                        remaining_after = target_boom - current_position
                        remaining_dirs = num_directors - i
                        weight = 0.8 + (0.4 * (i - 2) / max(remaining_dirs - 1, 1)) if remaining_dirs > 1 else 1.0
                        total_weight = sum(0.8 + (0.4 * j / max(remaining_dirs - 1, 1)) if remaining_dirs > 1 else 1.0 for j in range(remaining_dirs))
                        director_spacing = round(remaining_after * weight / total_weight, 1)
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
            close_d = request.close_driven
            far_d = request.far_driven
            if close_d == 'vclose': requested_lambda = 0.08
            elif close_d == 'close' or close_d is True: requested_lambda = 0.12
            elif far_d == 'vfar': requested_lambda = 0.28
            elif far_d == 'far' or far_d is True: requested_lambda = 0.22
            else: requested_lambda = 0.18
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


# ════════════════════════════════════════════════════════════════
# Gamma Match Designer — one-click recipe for any Yagi
# ════════════════════════════════════════════════════════════════

# Typical feedpoint impedance by element count (standard Yagi spacings)
_FEEDPOINT_R_TABLE = {
    2: 36.4, 3: 31.1, 4: 28.1, 5: 25.6, 6: 23.5, 7: 21.5,
    8: 20.0, 9: 18.5, 10: 17.2, 11: 16.0, 12: 15.0, 13: 14.0,
    14: 13.2, 15: 12.5, 16: 12.0, 17: 11.5, 18: 11.0, 19: 10.5, 20: 10.0,
}


def design_gamma_match(num_elements: int, driven_element_length_in: float,
                       frequency_mhz: float = 27.185,
                       feedpoint_impedance: float = None,
                       element_resonant_freq_mhz: float = None,
                       reflector_spacing_in: float = None,
                       director_spacings_in: list = None,
                       custom_tube_od: float = None, custom_rod_od: float = None,
                       custom_rod_spacing: float = None,
                       custom_teflon_length: float = None,
                       custom_tube_length: float = None,
                       driven_element_dia: float = 1.0) -> dict:
    """Design a gamma match recipe using the SAME physics as apply_matching_network()."""
    hw = get_gamma_hardware_defaults(num_elements)
    wall = hw["wall"]
    half_len = driven_element_length_in / 2.0
    wavelength_in = 11802.71 / frequency_mhz
    tube_length = custom_tube_length if custom_tube_length and custom_tube_length > 0 else hw["tube_length"]
    wavelength_m = 299792458.0 / (frequency_mhz * 1e6)
    refl_gap_in = reflector_spacing_in if reflector_spacing_in and reflector_spacing_in > 0 else 48.0

    # Element resonant frequency: use provided value or compute via shared helper
    if element_resonant_freq_mhz and element_resonant_freq_mhz > 0:
        element_res_freq = element_resonant_freq_mhz
    else:
        element_res_freq = compute_element_resonant_freq(
            driven_length_in=driven_element_length_in, frequency_mhz=frequency_mhz,
            wavelength_m=wavelength_m, num_elements=num_elements,
            reflector_spacing_in=refl_gap_in,
            director_spacings_in=director_spacings_in,
        )

    # Correct driven element length so resonance matches operating frequency
    original_driven_length = driven_element_length_in
    recommended_driven_length = driven_element_length_in
    length_was_corrected = False
    if element_res_freq > 0 and abs(element_res_freq - frequency_mhz) > 0.01:
        recommended_driven_length = round(driven_element_length_in * (element_res_freq / frequency_mhz), 2)
        driven_element_length_in = recommended_driven_length
        half_len = driven_element_length_in / 2.0
        element_res_freq = frequency_mhz
        length_was_corrected = True

    # Feedpoint impedance: user-provided or via shared mutual coupling model
    if feedpoint_impedance and feedpoint_impedance > 0:
        r_feed = feedpoint_impedance
    else:
        r_feed = compute_feedpoint_impedance(
            num_elements=num_elements, wavelength_m=wavelength_m,
            reflector_spacing_in=refl_gap_in,
            director_spacings_in=director_spacings_in,
        )
    swr_unmatched = max(50.0 / max(r_feed, 1), r_feed / 50.0)

    # Hardware selection: custom overrides or unified defaults
    is_custom = bool(custom_tube_od or custom_rod_od)
    auto_rod = hw["rod_od"]
    auto_tube = hw["tube_od"]
    auto_spacing = hw["rod_spacing"]
    rod_od = custom_rod_od if custom_rod_od and custom_rod_od > 0 else auto_rod
    tube_od = custom_tube_od if custom_tube_od and custom_tube_od > 0 else auto_tube
    rod_spacing = custom_rod_spacing if custom_rod_spacing and custom_rod_spacing > 0 else auto_spacing
    tube_id = tube_od - 2 * wall

    # Auto-fix: if custom rod is too big for the tube and tube wasn't custom, bump tube
    if tube_id <= rod_od and not (custom_tube_od and custom_tube_od > 0):
        tube_od = rod_od + 2 * wall + 0.025  # ensure clearance
        tube_id = tube_od - 2 * wall

    if tube_id <= rod_od:
        return {"error": f"Tube ID ({tube_id:.3f}\") must be larger than rod OD ({rod_od:.3f}\"). Increase tube OD or decrease rod OD."}

    cap_per_inch = 1.413 * 2.1 / math.log(tube_id / rod_od)
    id_rod_ratio = tube_id / rod_od
    gamma_rod_length = hw["rod_length"]
    teflon_sleeve = custom_teflon_length if custom_teflon_length and custom_teflon_length > 0 else tube_length + 1.0
    bar_min = teflon_sleeve

    # Helper: call apply_matching_network() for a given bar + insertion
    def _eval(bar: float, insertion: float) -> tuple:
        matched_swr, info = apply_matching_network(
            swr=swr_unmatched, feed_type='gamma', feedpoint_r=r_feed,
            gamma_rod_dia=rod_od, gamma_rod_spacing=rod_spacing,
            gamma_bar_pos=bar, gamma_element_gap=insertion,
            gamma_cap_pf=None, gamma_tube_od=tube_od,
            operating_freq_mhz=frequency_mhz,
            num_elements=num_elements,
            driven_element_half_length_in=half_len,
            driven_element_dia_in=driven_element_dia,
            element_resonant_freq_mhz=element_res_freq,
        )
        return matched_swr, info

    # Get ideal bar position from the same coupling formula as apply_matching_network
    _, probe_info = _eval(13.0, 8.0)
    coupling_multiplier = probe_info.get("coupling_multiplier", 4.5)
    x_antenna_at_center = probe_info.get("x_antenna", 0)  # antenna reactance at operating freq

    k_ideal = math.sqrt(50.0 / max(r_feed, 5.0))
    bar_ideal = half_len * (k_ideal - 1.0) / coupling_multiplier
    bar_ideal_clamped = max(bar_min, min(bar_ideal, gamma_rod_length))

    # Find null ANALYTICALLY: X_antenna*K + X_stub + X_cap = 0
    _, stub_info = _eval(bar_ideal_clamped, 0.001)
    x_stub_val = stub_info.get("x_stub", 0)
    x_ant_k = x_antenna_at_center * k_ideal  # antenna X transformed by K

    # Max rod insertion: rod stops 0.5" before teflon end to avoid shorting on tube
    # Max rod insertion: rod stops 0.5" before far end of tube
    max_insertion = tube_length - 0.5

    # Null: cap must cancel both antenna reactance and stub inductance
    omega = 2.0 * math.pi * frequency_mhz * 1e6
    null_reachable = True
    positive_x_total = x_ant_k + x_stub_val  # total reactance to cancel with cap
    if positive_x_total > 0:
        c_needed_pf = 1e12 / (omega * positive_x_total)
        optimal_insertion = c_needed_pf / cap_per_inch
        if optimal_insertion > max_insertion or optimal_insertion < 0:
            null_reachable = False
            optimal_insertion = max_insertion
    else:
        optimal_insertion = 0.0
        c_needed_pf = 0.0
        null_reachable = False

    # If null not reachable at ideal bar, OPTIMIZE: sweep bar positions to find
    # the best achievable SWR within the insertion range. A longer bar increases
    # X_stub (needs less cap = less insertion) but overshoots R_matched > 50Ω.
    # ALWAYS sweep to find the global best — the R-ideal bar is not always SWR-optimal.
    best_swr_opt = 999.0
    best_bar_opt = bar_ideal_clamped
    best_ins_opt = optimal_insertion if null_reachable else max_insertion
    # Sweep from bar_min out to rod length in fine steps
    steps = 80
    for i in range(steps + 1):
        test_bar = bar_min + (gamma_rod_length - bar_min) * i / steps
        if test_bar <= 0:
            continue
        # Get stub + antenna reactance at this bar
        _, ti = _eval(test_bar, 0.001)
        xs = ti.get("x_stub", 0)
        xa = ti.get("x_antenna", 0)
        k_at_bar = ti.get("step_up_ratio", 1.0)
        total_pos_x = xa * k_at_bar + xs  # antenna X * K + stub
        if total_pos_x <= 0:
            continue
        # Analytical null insertion for this bar
        c_need = 1e12 / (omega * total_pos_x)
        ins_need = c_need / cap_per_inch
        if ins_need <= max_insertion:
            test_ins = ins_need
        else:
            test_ins = max_insertion
        s, _ = _eval(test_bar, test_ins)
        if s < best_swr_opt:
            best_swr_opt = s
            best_bar_opt = test_bar
            best_ins_opt = test_ins
    optimized_bar = best_bar_opt
    optimal_insertion = best_ins_opt
    bar_ideal_clamped = optimized_bar
    # Re-check null reachability at optimized bar
    _, stub_opt = _eval(optimized_bar, 0.001)
    xs_opt = stub_opt.get("x_stub", 0)
    xa_opt = stub_opt.get("x_antenna", 0)
    k_opt = stub_opt.get("step_up_ratio", 1.0)
    total_x_opt = xa_opt * k_opt + xs_opt
    if total_x_opt > 0:
        c_opt = 1e12 / (omega * total_x_opt)
        ins_opt = c_opt / cap_per_inch
        null_reachable = ins_opt <= max_insertion
        if null_reachable:
            optimal_insertion = ins_opt
            c_needed_pf = c_opt
    else:
        null_reachable = False

    # Get authoritative values at the design point
    matched_swr, null_info = _eval(bar_ideal_clamped, optimal_insertion)

    swr_val = matched_swr
    rl_val = round(-20 * math.log10(max(null_info.get("reflection_coefficient", 0.001), 1e-8)), 2)
    rl_val = min(rl_val, 80.0)
    z_r = null_info.get("z_matched_r", 50.0)
    z_x = null_info.get("z_matched_x", 0.0)
    actual_cap = null_info.get("insertion_cap_pf", 0)
    k_at_ideal = null_info.get("step_up_ratio", 1.0)

    # Bar sweep: from bar_min to rod length (bar can't go below teflon end)
    bar_sweep = []
    for b_pct in range(0, 105, 5):
        b = bar_min + (gamma_rod_length - bar_min) * b_pct / 100.0
        s, info_b = _eval(b, optimal_insertion)
        bar_sweep.append({
            "bar_inches": round(b, 2), "k": info_b.get("step_up_ratio", 1.0),
            "r_matched": info_b.get("z_matched_r", 0), "x_net": info_b.get("net_reactance", 0),
            "swr": max(1.0, s),
        })

    # Insertion sweep: use apply_matching_network for each point
    ins_sweep = []
    for i_pct in range(0, 105, 5):
        ins = max_insertion * i_pct / 100.0
        if ins <= 0:
            ins = 0.001  # avoid zero-cap singularity
        s, info_i = _eval(bar_ideal_clamped, ins)
        ins_sweep.append({
            "insertion_inches": round(ins, 2), "cap_pf": info_i.get("insertion_cap_pf", 0),
            "x_net": info_i.get("net_reactance", 0), "swr": max(1.0, s),
        })

    # Notes
    notes = []
    if length_was_corrected:
        direction = "longer" if recommended_driven_length > original_driven_length else "shorter"
        delta = abs(recommended_driven_length - original_driven_length)
        notes.append(f"DRIVEN ELEMENT: Make {direction} to {recommended_driven_length:.2f}\" (was {original_driven_length:.1f}\", change {delta:.2f}\") to match resonance to {frequency_mhz} MHz")
    if is_custom:
        notes.append(f"Custom hardware: {tube_od:.3f}\" tube / {rod_od:.3f}\" rod")
        if id_rod_ratio > 2.0:
            notes.append(f"WARNING: ID/rod ratio {id_rod_ratio:.2f}:1 exceeds optimal 1.3-1.6x. Low cap/inch may prevent null.")
        elif id_rod_ratio < 1.2:
            notes.append(f"WARNING: ID/rod ratio {id_rod_ratio:.2f}:1 is very tight. Assembly may be difficult.")
    else:
        notes.append(f"Auto-selected hardware for {num_elements}-element Yagi")
    if optimized_bar != bar_ideal and null_reachable:
        notes.append(f"Bar optimized: ideal for R was {round(bar_ideal, 2)}\" but moved to {round(optimized_bar, 2)}\" so null fits within {max_insertion}\" max insertion.")
    if not null_reachable and c_needed_pf > 0:
        notes.append(f"NULL NOT REACHABLE at ideal bar ({round(bar_ideal, 2)}\"): needs {c_needed_pf:.1f} pF ({c_needed_pf/cap_per_inch:.1f}\" insertion) but max is {max_insertion}\".")
    if feedpoint_impedance:
        notes.append(f"Using user-provided feedpoint impedance: {feedpoint_impedance:.1f} ohms")
    else:
        notes.append(f"Estimated feedpoint impedance for {num_elements}-element Yagi: {r_feed:.1f} ohms")

    return {
        "recipe": {
            "rod_od": round(rod_od, 3),
            "tube_od": round(tube_od, 3),
            "tube_id": round(tube_id, 3),
            "rod_spacing": round(rod_spacing, 1),
            "teflon_length": round(custom_teflon_length if custom_teflon_length and custom_teflon_length > 0 else tube_length + 1.0, 1),
            "tube_length": tube_length,
            "gamma_rod_length": round(gamma_rod_length, 1),
            "ideal_bar_position": round(bar_ideal_clamped, 2),
            "optimal_insertion": round(optimal_insertion, 2),
            "swr_at_null": swr_val,
            "return_loss_at_null": rl_val,
            "capacitance_at_null": actual_cap,
            "z_matched_r": round(z_r, 2),
            "z_matched_x": round(z_x, 2),
            "k_step_up": round(k_at_ideal, 3),
            "k_squared": round(k_at_ideal ** 2, 3),
            "coupling_multiplier": round(coupling_multiplier, 3),
            "cap_per_inch": round(cap_per_inch, 3),
            "id_rod_ratio": round(id_rod_ratio, 3),
            "null_reachable": null_reachable,
            "recommended_driven_length_in": round(recommended_driven_length, 2),
            "original_driven_length_in": round(original_driven_length, 2),
            "driven_length_corrected": length_was_corrected,
            "bar_min": round(bar_min, 1),
        },
        "feedpoint_impedance": round(r_feed, 1),
        "hardware_source": "custom" if is_custom else "auto",
        "auto_hardware": {"rod_od": auto_rod, "tube_od": auto_tube, "spacing": auto_spacing},
        "bar_sweep": bar_sweep,
        "insertion_sweep": ins_sweep,
        "notes": notes,
    }


def design_hairpin_match(num_elements: int, frequency_mhz: float,
                          driven_element_length_in: float,
                          reflector_spacing_in: float = None,
                          director_spacings_in: list = None,
                          feedpoint_impedance: float = None,
                          element_resonant_freq_mhz: float = None,
                          custom_rod_dia: float = None,
                          custom_rod_spacing: float = None,
                          element_diameter: float = 0.5) -> dict:
    """Design a hairpin (beta) match using complex impedance + reflection coefficient."""
    wavelength_m = 299792458.0 / (frequency_mhz * 1e6)
    wl_in = wavelength_m * 39.3701
    half_len = driven_element_length_in / 2.0
    refl_gap_in = reflector_spacing_in if reflector_spacing_in and reflector_spacing_in > 0 else 48.0

    # Element resonant frequency
    if element_resonant_freq_mhz and element_resonant_freq_mhz > 0:
        element_res_freq = element_resonant_freq_mhz
    else:
        element_res_freq = compute_element_resonant_freq(
            driven_length_in=driven_element_length_in, frequency_mhz=frequency_mhz,
            wavelength_m=wavelength_m, num_elements=num_elements,
            reflector_spacing_in=refl_gap_in, director_spacings_in=director_spacings_in,
        )

    # Driven element length correction for resonance
    original_driven_length = driven_element_length_in
    recommended_driven_length = driven_element_length_in
    length_was_corrected = False
    if element_res_freq > 0 and abs(element_res_freq - frequency_mhz) > 0.01:
        recommended_driven_length = round(driven_element_length_in * (element_res_freq / frequency_mhz), 2)
        driven_element_length_in = recommended_driven_length
        half_len = driven_element_length_in / 2.0
        element_res_freq = frequency_mhz
        length_was_corrected = True

    # Feedpoint impedance
    if feedpoint_impedance and feedpoint_impedance > 0:
        r_feed = feedpoint_impedance
    else:
        r_feed = compute_feedpoint_impedance(
            num_elements=num_elements, wavelength_m=wavelength_m,
            reflector_spacing_in=refl_gap_in, director_spacings_in=director_spacings_in,
        )

    if r_feed >= 50.0:
        return {
            "error": None,
            "topology_note": f"Feedpoint R = {round(r_feed, 1)} ohms (>= 50). Hairpin cannot step down. Use Gamma match.",
            "feedpoint_impedance": round(r_feed, 1),
        }

    # L-network design
    q_match = math.sqrt(50.0 / r_feed - 1.0)
    xl_needed = 50.0 / q_match
    xc_needed = q_match * r_feed

    # Driven element shortening
    z_char = 120.0 * (math.log(2.0 * half_len / (element_diameter / 2.0)) - 1.0) if element_diameter > 0 else 600.0
    shorten_per_side = xc_needed * wl_in / (4.0 * math.pi * z_char) if z_char > 0 else 0
    shortened_total = (half_len - shorten_per_side) * 2.0

    # Hardware candidates: try different rod dia + spacing combos
    rod_dias = [0.125, 0.1875, 0.25, 0.3125, 0.375]
    rod_spacings = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    candidates = []

    for rd in rod_dias:
        for rs in rod_spacings:
            if rs <= rd / 2:
                continue
            z0 = 276.0 * math.log10(2.0 * rs / rd)
            ideal_len = (math.atan(xl_needed / z0) / (2.0 * math.pi)) * wl_in
            # Score: prefer practical lengths (8-36"), reasonable Z0
            if ideal_len < 2 or ideal_len > wl_in / 4:
                continue
            # Practical score: closer to 12-24" is better
            center = 18.0
            length_score = abs(ideal_len - center) / center
            candidates.append({
                "rod_dia": rd, "rod_spacing": rs, "z0": round(z0, 1),
                "ideal_length_in": round(ideal_len, 2), "score": length_score,
            })

    if not candidates:
        # Fallback to defaults
        rd = custom_rod_dia if custom_rod_dia and custom_rod_dia > 0 else 0.25
        rs = custom_rod_spacing if custom_rod_spacing and custom_rod_spacing > 0 else 1.0
        z0 = 276.0 * math.log10(2.0 * rs / rd) if rs > rd / 2 else 200.0
        ideal_len = (math.atan(xl_needed / z0) / (2.0 * math.pi)) * wl_in
        candidates = [{"rod_dia": rd, "rod_spacing": rs, "z0": round(z0, 1),
                        "ideal_length_in": round(ideal_len, 2), "score": 0}]

    # If user specified custom hardware, use it; otherwise pick best candidate
    if custom_rod_dia and custom_rod_dia > 0 and custom_rod_spacing and custom_rod_spacing > 0:
        rd = custom_rod_dia
        rs = custom_rod_spacing
        z0 = 276.0 * math.log10(2.0 * rs / rd) if rs > rd / 2 else 200.0
        ideal_len = (math.atan(xl_needed / z0) / (2.0 * math.pi)) * wl_in
        best = {"rod_dia": rd, "rod_spacing": rs, "z0": round(z0, 1), "ideal_length_in": round(ideal_len, 2)}
        hw_source = "custom"
    else:
        candidates.sort(key=lambda c: c["score"])
        best = candidates[0]
        hw_source = "auto"

    z0_best = best["z0"]
    ideal_length = best["ideal_length_in"]

    # SWR sweep: vary hairpin length
    length_sweep = []
    sweep_min = max(2.0, ideal_length * 0.3)
    sweep_max = min(wl_in / 4.0 - 1.0, ideal_length * 2.5)
    sweep_steps = 60
    step_size = (sweep_max - sweep_min) / sweep_steps if sweep_steps > 0 else 1.0

    best_swr = 999.0
    best_length = ideal_length

    for i in range(sweep_steps + 1):
        length = sweep_min + i * step_size
        beta_l = (2.0 * math.pi * length) / wl_in
        if abs(beta_l) >= math.pi / 2.0 - 0.01:
            continue
        xl_act = z0_best * math.tan(beta_l)

        # Complex impedance calculation
        z_feed = complex(r_feed, -xc_needed)
        z_hp = complex(0, xl_act)
        z_sum = z_feed + z_hp
        if abs(z_sum) < 0.001:
            continue
        z_in = (z_feed * z_hp) / z_sum

        gamma_c = (z_in - 50.0) / (z_in + 50.0)
        gamma_m = abs(gamma_c)
        swr_val = (1.0 + gamma_m) / (1.0 - gamma_m) if gamma_m < 0.99 else 99.0

        # Power (5W reference)
        p_refl = 5.0 * gamma_m ** 2

        pt = {
            "length_in": round(length, 2),
            "swr": round(swr_val, 3),
            "xl_actual": round(xl_act, 2),
            "z_in_r": round(z_in.real, 2),
            "z_in_x": round(z_in.imag, 2),
            "gamma": round(gamma_m, 4),
            "p_reflected_w": round(p_refl, 3),
        }
        length_sweep.append(pt)

        if swr_val < best_swr:
            best_swr = swr_val
            best_length = length

    # Build recipe
    recipe = {
        "rod_dia": best["rod_dia"],
        "rod_spacing": best["rod_spacing"],
        "z0": z0_best,
        "ideal_hairpin_length_in": round(best_length, 2),
        "xl_needed": round(xl_needed, 2),
        "xc_needed": round(xc_needed, 2),
        "q_match": round(q_match, 3),
        "swr_at_best": round(max(1.0, best_swr), 3),
        "feedpoint_r": round(r_feed, 1),
        "shorten_per_side_in": round(shorten_per_side, 2),
        "shortened_total_length_in": round(shortened_total, 2),
        "target_element_reactance": round(-xc_needed, 2),
        "original_driven_length_in": round(original_driven_length, 2),
        "recommended_driven_length_in": round(recommended_driven_length, 2) if length_was_corrected else None,
        "driven_length_corrected": length_was_corrected,
    }

    notes = []
    if length_was_corrected:
        delta = round(recommended_driven_length - original_driven_length, 2)
        direction = "LONGER" if delta > 0 else "SHORTER"
        notes.append(f"Driven element should be {abs(delta)}\" {direction} for resonance at {frequency_mhz} MHz")
    notes.append(f"Shorten each half of driven by {round(shorten_per_side, 2)}\" for {round(xc_needed, 1)} ohms X_C")
    notes.append(f"New driven element total: {round(shortened_total, 2)}\"")

    tuning_instructions = [
        {"step": "1. Prune", "action": f"Shorten driven element by {round(shorten_per_side * 2, 2)}\" total ({round(shorten_per_side, 2)}\" each side)", "value": f"Target -j{round(xc_needed, 1)} ohms"},
        {"step": "2. Set Bar", "action": f"Slide shorting bar to {round(best_length, 2)}\" from feedpoint", "value": f"Provides +j{round(xl_needed, 1)} ohms"},
        {"step": "3. Result", "action": f"Predicted SWR center at {frequency_mhz} MHz", "value": f"{round(max(1.0, best_swr), 3)}:1 SWR"},
    ]

    return {
        "recipe": recipe,
        "feedpoint_impedance": round(r_feed, 1),
        "hardware_source": hw_source,
        "auto_hardware": {"rod_dia": best["rod_dia"], "rod_spacing": best["rod_spacing"], "z0": z0_best},
        "length_sweep": length_sweep,
        "tuning_instructions": tuning_instructions,
        "notes": notes,
        "error": None,
    }

