"""Test two high-power gamma hardware combos across 5-20 elements."""
import requests, json, time

API_URL = "https://swr-optimizer.preview.emergentagent.com"

def build_yagi(n):
    elements = [{"element_type": "reflector", "length": 216.0, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 203.0, "diameter": 0.5, "position": 48}]
    dir_lengths = [195, 192, 190, 188, 187, 186, 185, 184, 183, 183, 182, 182, 181, 181, 180, 180, 179, 179]
    for i in range(n - 2):
        elements.append({"element_type": "director", "length": dir_lengths[i] if i < len(dir_lengths) else 179, "diameter": 0.5, "position": 48 + (i+1)*48})
    return elements

def calc(n, elems):
    resp = requests.post(f"{API_URL}/api/calculate", json={
        "num_elements": n, "elements": elems, "height_from_ground": 54, "height_unit": "ft",
        "boom_diameter": 1.5, "boom_unit": "inches", "band": "11m_cb", "frequency_mhz": 27.185,
        "antenna_orientation": "horizontal", "feed_type": "gamma", "coax_type": "RG-213",
        "coax_length_ft": 100, "transmit_power_watts": 5000, "boom_grounded": False, "boom_mount": "insulated",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()

def gamma(n, elems, calc_data, tube_od, rod_od):
    mi = calc_data.get("matching_info", {})
    gd = mi.get("gamma_design", {})
    fz = gd.get("feedpoint_impedance_ohms", 25)
    res_freq = mi.get("element_resonant_freq_mhz", 27.185)
    driven = next(e for e in elems if e["element_type"] == "driven")
    refl = next(e for e in elems if e["element_type"] == "reflector")
    dirs = sorted([e for e in elems if e["element_type"] == "director"], key=lambda x: x["position"])
    refl_sp = abs(driven["position"] - refl["position"])
    dir_sp = [abs(d["position"] - driven["position"]) for d in dirs]
    resp = requests.post(f"{API_URL}/api/gamma-designer", json={
        "num_elements": n, "driven_element_length_in": driven["length"],
        "frequency_mhz": 27.185, "feedpoint_impedance": fz,
        "element_resonant_freq_mhz": res_freq, "reflector_spacing_in": refl_sp,
        "director_spacings_in": dir_sp, "driven_element_dia": 0.5,
        "custom_tube_od": tube_od, "custom_rod_od": rod_od,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()

def fmt(v, f=".2f"):
    return format(v, f) if isinstance(v, (int, float)) else str(v)

combos = [
    {"name": "COMBO A: 1\" Tube + 5/8\" Rod", "tube": 1.0, "rod": 0.625},
    {"name": "COMBO B: 1-1/4\" Tube + 3/4\" Rod", "tube": 1.25, "rod": 0.75},
]

for combo in combos:
    print("\n" + "=" * 140)
    print(f"  {combo['name']}  |  Tube OD: {combo['tube']}\"  |  Rod OD: {combo['rod']}\"  |  Wall: 0.049\"  |  Tube ID: {combo['tube'] - 0.098:.3f}\"  |  Gap/side: {(combo['tube'] - 0.098 - combo['rod'])/2:.3f}\"")
    print("=" * 140)
    print(f"{'Elem':>4} | {'SWR@Null':>8} | {'RL(dB)':>6} | {'Null':>4} | {'Bar Pos':>7} | {'Insert':>6} | {'Cap pF':>6} | {'C/in':>5} | {'K':>5} | {'K^2':>5} | {'Z Feed':>6} | {'Z Match R':>9} | {'Z Match X':>9} | {'Driven':>7} | {'Rod L':>5} | {'Tube L':>6}")
    print("-" * 140)

    for n in range(5, 21):
        elems = build_yagi(n)
        c = calc(n, elems)
        g = gamma(n, elems, c, combo["tube"], combo["rod"])
        r = g.get("recipe", {})

        print(f"{n:>4} | {fmt(r.get('swr_at_null','N/A'),'.3f'):>8} | {fmt(r.get('return_loss_at_null','N/A'),'.1f'):>6} | {'Y' if r.get('null_reachable') else 'N':>4} | {fmt(r.get('ideal_bar_position','N/A'),'.2f'):>7} | {fmt(r.get('optimal_insertion','N/A'),'.2f'):>6} | {fmt(r.get('capacitance_at_null','N/A'),'.1f'):>6} | {fmt(r.get('cap_per_inch','N/A'),'.1f'):>5} | {fmt(r.get('k_step_up','N/A'),'.2f'):>5} | {fmt(r.get('k_squared','N/A'),'.2f'):>5} | {fmt(r.get('z_matched_r','N/A') if r.get('z_matched_r') else c.get('matching_info',{}).get('gamma_design',{}).get('feedpoint_impedance_ohms','N/A'),'.1f'):>6} | {fmt(r.get('z_matched_r','N/A'),'.2f'):>9} | {fmt(r.get('z_matched_x','N/A'),'.2f'):>9} | {fmt(r.get('recommended_driven_length_in','N/A'),'.2f'):>7} | {fmt(r.get('gamma_rod_length','N/A'),'.1f'):>5} | {fmt(r.get('tube_length','N/A'),'.1f'):>6}")

    # Power safety summary
    tube_id = combo["tube"] - 0.098
    gap = (tube_id - combo["rod"]) / 2
    # At worst case 20-elem (Z=12, K^2 ~4.17): V_peak = sqrt(2 * 5000 * 50 * 4.17) ~= 1443V
    v_peak = (2 * 5000 * 50 * 4.17) ** 0.5
    air_breakdown = gap * 1000 * 75  # 75V/mil for air
    teflon_breakdown = gap * 1000 * 500  # 500V/mil for PTFE
    print(f"\n  5kW SAFETY: V_peak(worst)={v_peak:.0f}V | Gap={gap:.3f}\" ({gap*1000:.1f} mils)")
    print(f"  Air only: breakdown @ {air_breakdown:.0f}V {'OK' if air_breakdown > v_peak * 1.5 else 'MARGINAL' if air_breakdown > v_peak else 'WILL ARC'}")
    print(f"  With PTFE: breakdown @ {teflon_breakdown:.0f}V {'OK (huge margin)' if teflon_breakdown > v_peak * 3 else 'OK' if teflon_breakdown > v_peak * 1.5 else 'MARGINAL'}")

print("\n\nDone.")
