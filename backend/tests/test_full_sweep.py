"""Comprehensive Fine-Tune Gamma test: 5 to 20 elements with full data output."""
import requests
import json
import time

API_URL = "https://swr-optimizer.preview.emergentagent.com"

def build_yagi(num_elements):
    """Build a standard Yagi antenna with given element count."""
    elements = []
    elements.append({"element_type": "reflector", "length": 216.0, "diameter": 0.5, "position": 0})
    elements.append({"element_type": "driven", "length": 203.0, "diameter": 0.5, "position": 48})
    dir_lengths = [195, 192, 190, 188, 187, 186, 185, 184, 183, 183, 182, 182, 181, 181, 180, 180, 179, 179]
    for i in range(num_elements - 2):
        pos = 48 + (i + 1) * 48
        length = dir_lengths[i] if i < len(dir_lengths) else 179
        elements.append({"element_type": "director", "length": length, "diameter": 0.5, "position": pos})
    return elements


def fine_tune(num_elements, elements):
    payload = {
        "num_elements": num_elements, "elements": elements,
        "band": "11m_cb", "frequency_mhz": 27.185,
        "height_from_ground": 54, "height_unit": "ft",
        "boom_diameter": 1.5, "boom_unit": "inches",
        "boom_grounded": False, "boom_mount": "insulated",
        "element_diameter": 0.5,
    }
    start = time.time()
    resp = requests.post(f"{API_URL}/api/gamma-fine-tune", json=payload, timeout=30)
    elapsed = time.time() - start
    resp.raise_for_status()
    data = resp.json()
    data["_elapsed"] = round(elapsed, 3)
    return data


def calculate(num_elements, elements):
    payload = {
        "num_elements": num_elements,
        "elements": [{"element_type": e["element_type"], "length": e["length"], "diameter": e.get("diameter", 0.5), "position": e["position"]} for e in elements],
        "height_from_ground": 54, "height_unit": "ft",
        "boom_diameter": 1.5, "boom_unit": "inches",
        "band": "11m_cb", "frequency_mhz": 27.185,
        "antenna_orientation": "horizontal", "feed_type": "gamma",
        "coax_type": "RG-213", "coax_length_ft": 100, "transmit_power_watts": 500,
        "boom_grounded": False, "boom_mount": "insulated",
    }
    resp = requests.post(f"{API_URL}/api/calculate", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def gamma_designer(num_elements, elements, calc_data):
    mi = calc_data.get("matching_info", {})
    gd = mi.get("gamma_design", {})
    fz = gd.get("feedpoint_impedance_ohms", 25)
    res_freq = mi.get("element_resonant_freq_mhz", 27.185)
    driven = next(e for e in elements if e["element_type"] == "driven")
    refl = next(e for e in elements if e["element_type"] == "reflector")
    dirs = sorted([e for e in elements if e["element_type"] == "director"], key=lambda x: x["position"])
    refl_sp = abs(driven["position"] - refl["position"])
    dir_sp = [abs(d["position"] - driven["position"]) for d in dirs]
    payload = {
        "num_elements": num_elements, "driven_element_length_in": driven["length"],
        "frequency_mhz": 27.185, "feedpoint_impedance": fz,
        "element_resonant_freq_mhz": res_freq, "reflector_spacing_in": refl_sp,
        "director_spacings_in": dir_sp, "driven_element_dia": 0.5,
    }
    resp = requests.post(f"{API_URL}/api/gamma-designer", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


print("=" * 130)
print(f"{'FINE-TUNE GAMMA — COMPREHENSIVE DATA SWEEP (5 to 20 ELEMENTS)':^130}")
print("=" * 130)

all_results = []

for n in range(5, 21):
    original_elems = build_yagi(n)
    ft = fine_tune(n, original_elems)
    optimized_elems = ft["optimized_elements"]
    calc = calculate(n, optimized_elems)
    gd = gamma_designer(n, optimized_elems, calc)
    recipe = gd.get("recipe", {})
    mi = calc.get("matching_info", {})

    # Smith chart data at center freq
    smith = calc.get("smith_chart_data", [])
    center_smith = {}
    if smith:
        mid = len(smith) // 2
        center_smith = smith[mid]

    result = {
        "n": n,
        "time_s": ft["_elapsed"],
        # SWR data
        "ft_orig_swr": ft["original_swr"],
        "ft_opt_swr": ft["optimized_swr"],
        "gamma_swr_null": recipe.get("swr_at_null", "N/A"),
        "null_reachable": recipe.get("null_reachable", False),
        # Return loss & efficiency
        "return_loss_null": recipe.get("return_loss_at_null", "N/A"),
        "return_loss_calc": calc.get("return_loss_db", "N/A"),
        "efficiency": calc.get("antenna_efficiency", "N/A"),
        "refl_coeff": calc.get("reflection_coefficient", "N/A"),
        # Gain & Pattern
        "gain": calc.get("gain_dbi", "N/A"),
        "fb": calc.get("fb_ratio", "N/A"),
        "beamwidth_h": calc.get("beamwidth_h", "N/A"),
        "beamwidth_v": calc.get("beamwidth_v", "N/A"),
        "bw_1_5": calc.get("usable_bandwidth_1_5", "N/A"),
        "bw_2_0": calc.get("usable_bandwidth_2_0", "N/A"),
        # Impedance
        "feedpoint_z": ft["feedpoint_impedance"],
        "z_matched_r": recipe.get("z_matched_r", "N/A"),
        "z_matched_x": recipe.get("z_matched_x", "N/A"),
        # Gamma hardware & settings
        "rod_od": recipe.get("rod_od", "N/A"),
        "tube_od": recipe.get("tube_od", "N/A"),
        "tube_id": recipe.get("tube_id", "N/A"),
        "rod_spacing": recipe.get("rod_spacing", "N/A"),
        "bar_pos": recipe.get("ideal_bar_position", "N/A"),
        "insertion": recipe.get("optimal_insertion", "N/A"),
        "cap_pf": recipe.get("capacitance_at_null", "N/A"),
        "cap_per_inch": recipe.get("cap_per_inch", "N/A"),
        "k_step": recipe.get("k_step_up", "N/A"),
        "k_sq": recipe.get("k_squared", "N/A"),
        "coupling_mult": recipe.get("coupling_multiplier", "N/A"),
        "driven_len_rec": recipe.get("recommended_driven_length_in", "N/A"),
        "driven_corrected": recipe.get("driven_length_corrected", False),
        "tube_length": recipe.get("tube_length", "N/A"),
        "teflon_length": recipe.get("teflon_length", "N/A"),
        "rod_length": recipe.get("gamma_rod_length", "N/A"),
        # Smith chart at center freq
        "smith_z_real": center_smith.get("z_real", "N/A"),
        "smith_z_imag": center_smith.get("z_imag", "N/A"),
        "smith_gamma_real": center_smith.get("gamma_real", "N/A"),
        "smith_gamma_imag": center_smith.get("gamma_imag", "N/A"),
        # Optimization steps
        "steps": ft["optimization_steps"],
    }
    all_results.append(result)
    print(f"  {n:>2} elem: SWR {ft['original_swr']} -> {ft['optimized_swr']} | Gamma null: {recipe.get('swr_at_null', 'N/A')} | {ft['_elapsed']}s")


def fmt(v, f=".2f"):
    if isinstance(v, (int, float)):
        return format(v, f)
    return str(v)

# ── Table 1: SWR / Return Loss / Efficiency ──
print("\n" + "=" * 130)
print(f"{'TABLE 1: SWR, RETURN LOSS, EFFICIENCY':^130}")
print("=" * 130)
print(f"{'Elem':>4} | {'Fine-Tune':>9} | {'Gamma Null':>10} | {'RL@Null':>7} | {'RL Calc':>7} | {'Ref Coeff':>9} | {'Eff(%)':>6} | {'Gain':>6} | {'F/B':>5} | {'BW-H':>5} | {'BW-V':>5} | {'BW1.5':>5} | {'BW2.0':>5} | {'Time':>5}")
print("-" * 130)
for r in all_results:
    print(f"{r['n']:>4} | {fmt(r['ft_opt_swr'],'.3f'):>9} | {fmt(r['gamma_swr_null'],'.3f'):>10} | {fmt(r['return_loss_null'],'.1f'):>7} | {fmt(r['return_loss_calc'],'.1f'):>7} | {fmt(r['refl_coeff'],'.4f'):>9} | {fmt(r['efficiency'],'.1f'):>6} | {fmt(r['gain'],'.1f'):>6} | {fmt(r['fb'],'.1f'):>5} | {fmt(r['beamwidth_h'],'.1f'):>5} | {fmt(r['beamwidth_v'],'.1f'):>5} | {fmt(r['bw_1_5'],'.2f'):>5} | {fmt(r['bw_2_0'],'.2f'):>5} | {fmt(r['time_s'],'.2f'):>5}")

# ── Table 2: Gamma Match Hardware & Settings ──
print("\n" + "=" * 130)
print(f"{'TABLE 2: GAMMA MATCH SETTINGS':^130}")
print("=" * 130)
print(f"{'Elem':>4} | {'Rod OD':>6} | {'Tube OD':>7} | {'Tube ID':>7} | {'Spc':>4} | {'Bar Pos':>7} | {'Insert':>6} | {'Cap pF':>6} | {'C/in':>5} | {'K':>5} | {'K^2':>5} | {'Couple':>6} | {'Tube L':>6} | {'Rod L':>5} | {'Null':>4}")
print("-" * 130)
for r in all_results:
    null_ok = "Y" if r["null_reachable"] else "N"
    print(f"{r['n']:>4} | {fmt(r['rod_od'],'.3f'):>6} | {fmt(r['tube_od'],'.3f'):>7} | {fmt(r['tube_id'],'.3f'):>7} | {fmt(r['rod_spacing'],'.1f'):>4} | {fmt(r['bar_pos'],'.2f'):>7} | {fmt(r['insertion'],'.2f'):>6} | {fmt(r['cap_pf'],'.1f'):>6} | {fmt(r['cap_per_inch'],'.1f'):>5} | {fmt(r['k_step'],'.2f'):>5} | {fmt(r['k_sq'],'.2f'):>5} | {fmt(r['coupling_mult'],'.2f'):>6} | {fmt(r['tube_length'],'.1f'):>6} | {fmt(r['rod_length'],'.1f'):>5} | {null_ok:>4}")

# ── Table 3: Impedance & Driven Element ──
print("\n" + "=" * 130)
print(f"{'TABLE 3: IMPEDANCE & DRIVEN ELEMENT':^130}")
print("=" * 130)
print(f"{'Elem':>4} | {'Z Feed':>6} | {'Z Match R':>9} | {'Z Match X':>9} | {'Driven Rec':>10} | {'Corrected':>9} | {'Teflon L':>8}")
print("-" * 80)
for r in all_results:
    corr = "YES" if r["driven_corrected"] else "no"
    print(f"{r['n']:>4} | {fmt(r['feedpoint_z'],'.1f'):>6} | {fmt(r['z_matched_r'],'.2f'):>9} | {fmt(r['z_matched_x'],'.2f'):>9} | {fmt(r['driven_len_rec'],'.2f'):>10} | {corr:>9} | {fmt(r['teflon_length'],'.1f'):>8}")

# ── Table 4: Smith Chart at Center Frequency ──
print("\n" + "=" * 130)
print(f"{'TABLE 4: SMITH CHART DATA AT CENTER FREQ (27.185 MHz)':^130}")
print("=" * 130)
print(f"{'Elem':>4} | {'Z Real':>8} | {'Z Imag':>8} | {'Gamma Real':>10} | {'Gamma Imag':>10} | {'|Gamma|':>8} | {'SWR from Smith':>14}")
print("-" * 80)
for r in all_results:
    gr = r["smith_gamma_real"]
    gi = r["smith_gamma_imag"]
    if isinstance(gr, (int, float)) and isinstance(gi, (int, float)):
        gm = (gr**2 + gi**2)**0.5
        swr_smith = (1 + gm) / (1 - gm) if gm < 1 else 99
    else:
        gm = "N/A"
        swr_smith = "N/A"
    print(f"{r['n']:>4} | {fmt(r['smith_z_real'],'.2f'):>8} | {fmt(r['smith_z_imag'],'.2f'):>8} | {fmt(gr,'.5f'):>10} | {fmt(gi,'.5f'):>10} | {fmt(gm,'.5f'):>8} | {fmt(swr_smith,'.3f'):>14}")

# ── Optimization Steps ──
print("\n" + "=" * 130)
print(f"{'OPTIMIZATION STEPS DETAIL':^130}")
print("=" * 130)
for r in all_results:
    print(f"\n  {r['n']} Elements:")
    for s in r["steps"]:
        print(f"    {s}")

with open("/app/test_reports/fine_tune_full_data.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\n\nJSON saved to /app/test_reports/fine_tune_full_data.json")
