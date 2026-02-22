"""Comprehensive Fine-Tune Gamma test: 5 to 20 elements with full data output."""
import requests
import json
import time
import sys

API_URL = "https://swr-optimizer.preview.emergentagent.com"

def build_yagi(num_elements):
    """Build a standard Yagi antenna with given element count."""
    elements = []
    # Reflector
    elements.append({"element_type": "reflector", "length": 216.0, "diameter": 0.5, "position": 0})
    # Driven
    elements.append({"element_type": "driven", "length": 203.0, "diameter": 0.5, "position": 48})
    # Directors
    dir_lengths = [195, 192, 190, 188, 187, 186, 185, 184, 183, 183, 182, 182, 181, 181, 180, 180, 179, 179]
    dir_spacing = 48  # starting spacing from driven
    for i in range(num_elements - 2):
        pos = 48 + (i + 1) * dir_spacing
        length = dir_lengths[i] if i < len(dir_lengths) else 179
        elements.append({"element_type": "director", "length": length, "diameter": 0.5, "position": pos})
    return elements


def fine_tune(num_elements, elements):
    """Call the fine-tune gamma endpoint."""
    payload = {
        "num_elements": num_elements,
        "elements": elements,
        "band": "11m_cb",
        "frequency_mhz": 27.185,
        "height_from_ground": 54,
        "height_unit": "ft",
        "boom_diameter": 1.5,
        "boom_unit": "inches",
        "boom_grounded": False,
        "boom_mount": "insulated",
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
    """Call the calculate endpoint for full antenna data."""
    payload = {
        "num_elements": num_elements,
        "elements": [
            {"element_type": e["element_type"], "length": e["length"], "diameter": e.get("diameter", 0.5), "position": e["position"]}
            for e in elements
        ],
        "height_from_ground": 54,
        "height_unit": "ft",
        "boom_diameter": 1.5,
        "boom_unit": "inches",
        "band": "11m_cb",
        "frequency_mhz": 27.185,
        "antenna_orientation": "horizontal",
        "feed_type": "gamma",
        "coax_type": "RG-213",
        "coax_length_ft": 100,
        "transmit_power_watts": 500,
        "boom_grounded": False,
        "boom_mount": "insulated",
    }
    resp = requests.post(f"{API_URL}/api/calculate", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def gamma_designer(num_elements, elements, calc_data):
    """Call the gamma designer for detailed gamma match settings."""
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
        "num_elements": num_elements,
        "driven_element_length_in": driven["length"],
        "frequency_mhz": 27.185,
        "feedpoint_impedance": fz,
        "element_resonant_freq_mhz": res_freq,
        "reflector_spacing_in": refl_sp,
        "director_spacings_in": dir_sp,
        "driven_element_dia": 0.5,
    }
    resp = requests.post(f"{API_URL}/api/gamma-designer", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── Run all tests ──
print("=" * 120)
print(f"{'FINE-TUNE GAMMA COMPREHENSIVE TEST — 5 to 20 ELEMENTS':^120}")
print("=" * 120)
print()

all_results = []

for n in range(5, 21):
    print(f"--- {n} Elements ---")

    # Build standard Yagi
    original_elems = build_yagi(n)

    # Step 1: Fine-tune
    ft = fine_tune(n, original_elems)
    optimized_elems = ft["optimized_elements"]

    # Step 2: Calculate BEFORE (original)
    calc_before = calculate(n, original_elems)

    # Step 3: Calculate AFTER (optimized)
    calc_after = calculate(n, optimized_elems)

    # Step 4: Gamma designer on optimized
    gd = gamma_designer(n, optimized_elems, calc_after)
    recipe = gd.get("recipe", {})

    # Extract smith chart data points
    smith = calc_after.get("smith_chart_data", [])
    smith_summary = []
    if smith:
        for pt in smith[:5]:  # first 5 points
            smith_summary.append(f"({pt.get('real', 0):.3f}, {pt.get('imag', 0):.3f})")

    result = {
        "elements": n,
        "time_s": ft["_elapsed"],
        "original_swr": ft["original_swr"],
        "optimized_swr": ft["optimized_swr"],
        "calc_swr_before": calc_before.get("swr", "N/A"),
        "calc_swr_after": calc_after.get("swr", "N/A"),
        "return_loss_before": calc_before.get("return_loss_db", "N/A"),
        "return_loss_after": calc_after.get("return_loss_db", "N/A"),
        "efficiency_before": calc_before.get("antenna_efficiency", "N/A"),
        "efficiency_after": calc_after.get("antenna_efficiency", "N/A"),
        "gain_before": calc_before.get("gain_dbi", "N/A"),
        "gain_after": calc_after.get("gain_dbi", "N/A"),
        "fb_after": calc_after.get("fb_ratio", "N/A"),
        "feedpoint_z": ft["feedpoint_impedance"],
        "gamma_rod_od": recipe.get("rod_od", ft["hardware"].get("rod_od", "N/A")),
        "gamma_tube_od": recipe.get("tube_od", ft["hardware"].get("tube_od", "N/A")),
        "gamma_bar_pos": recipe.get("bar_position_in", "N/A"),
        "gamma_insertion": recipe.get("rod_insertion_in", "N/A"),
        "gamma_cap_pf": recipe.get("cap_pf", "N/A"),
        "gamma_swr_at_null": recipe.get("swr_at_null", "N/A"),
        "gamma_null_reachable": recipe.get("null_reachable", "N/A"),
        "gamma_driven_len": recipe.get("recommended_driven_length_in", "N/A"),
        "smith_points": smith_summary,
        "optimization_steps": ft["optimization_steps"],
        "reflection_coeff": calc_after.get("reflection_coefficient", "N/A"),
    }
    all_results.append(result)
    print(f"  Fine-tune: {ft['original_swr']} -> {ft['optimized_swr']} in {ft['_elapsed']}s")


# ── Print Summary Table ──
print()
print("=" * 120)
print(f"{'RESULTS SUMMARY TABLE':^120}")
print("=" * 120)

# Table 1: SWR & Performance
print()
print(f"{'Elem':>4} | {'Orig SWR':>8} | {'Opt SWR':>7} | {'Calc SWR':>8} | {'Time(s)':>7} | {'Gain(dBi)':>9} | {'F/B(dB)':>7} | {'Z(ohm)':>6} | {'Efficiency':>10} | {'RL(dB)':>6}")
print("-" * 110)
for r in all_results:
    print(f"{r['elements']:>4} | {r['original_swr']:>8} | {r['optimized_swr']:>7} | {r['calc_swr_after']:>8} | {r['time_s']:>7} | {r['gain_after']:>9} | {r['fb_after']:>7} | {r['feedpoint_z']:>6} | {r['efficiency_after']:>10} | {r['return_loss_after']:>6}")

# Table 2: Gamma Settings
print()
print(f"{'GAMMA MATCH SETTINGS':^120}")
print("-" * 120)
print(f"{'Elem':>4} | {'Rod OD':>6} | {'Tube OD':>7} | {'Bar Pos':>7} | {'Insert':>6} | {'Cap(pF)':>7} | {'SWR@Null':>8} | {'Null OK':>7} | {'Driven Len':>10} | {'Refl Coeff':>10}")
print("-" * 120)
for r in all_results:
    bar = f"{r['gamma_bar_pos']:.2f}" if isinstance(r['gamma_bar_pos'], (int, float)) else str(r['gamma_bar_pos'])
    ins = f"{r['gamma_insertion']:.2f}" if isinstance(r['gamma_insertion'], (int, float)) else str(r['gamma_insertion'])
    cap = f"{r['gamma_cap_pf']:.1f}" if isinstance(r['gamma_cap_pf'], (int, float)) else str(r['gamma_cap_pf'])
    swr_null = f"{r['gamma_swr_at_null']:.3f}" if isinstance(r['gamma_swr_at_null'], (int, float)) else str(r['gamma_swr_at_null'])
    drv = f"{r['gamma_driven_len']:.2f}" if isinstance(r['gamma_driven_len'], (int, float)) else str(r['gamma_driven_len'])
    rc = f"{r['reflection_coeff']:.4f}" if isinstance(r['reflection_coeff'], (int, float)) else str(r['reflection_coeff'])
    print(f"{r['elements']:>4} | {r['gamma_rod_od']:>6} | {r['gamma_tube_od']:>7} | {bar:>7} | {ins:>6} | {cap:>7} | {swr_null:>8} | {str(r['gamma_null_reachable']):>7} | {drv:>10} | {rc:>10}")

# Table 3: Smith Chart Data
print()
print(f"{'SMITH CHART DATA (first 5 points per antenna)':^120}")
print("-" * 120)
for r in all_results:
    pts = ", ".join(r["smith_points"]) if r["smith_points"] else "No data"
    print(f"  {r['elements']:>2} elem: {pts}")

# Table 4: Optimization Steps
print()
print(f"{'OPTIMIZATION DETAILS':^120}")
print("-" * 120)
for r in all_results:
    print(f"\n  {r['elements']} Elements:")
    for s in r["optimization_steps"]:
        print(f"    {s}")

# Save to JSON
with open("/app/test_reports/fine_tune_full_data.json", "w") as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\n\nFull data saved to /app/test_reports/fine_tune_full_data.json")
