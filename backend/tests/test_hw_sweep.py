"""Post-fix sweep: high-power combos 5-20 elements with corrected tube length."""
import requests

API_URL = "https://element-tuner.preview.emergentagent.com"

def build_yagi(n):
    elements = [{"element_type": "reflector", "length": 216.0, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 203.0, "diameter": 0.5, "position": 48}]
    dir_lengths = [195, 192, 190, 188, 187, 186, 185, 184, 183, 183, 182, 182, 181, 181, 180, 180, 179, 179]
    for i in range(n - 2):
        elements.append({"element_type": "director", "length": dir_lengths[i] if i < len(dir_lengths) else 179,
                         "diameter": 0.5, "position": 48 + (i+1)*48})
    return elements

def calc(n, elems):
    return requests.post(f"{API_URL}/api/calculate", json={
        "num_elements": n, "elements": elems, "height_from_ground": 54, "height_unit": "ft",
        "boom_diameter": 1.5, "boom_unit": "inches", "band": "11m_cb", "frequency_mhz": 27.185,
        "antenna_orientation": "horizontal", "feed_type": "gamma", "coax_type": "RG-213",
        "coax_length_ft": 100, "transmit_power_watts": 5000, "boom_grounded": False, "boom_mount": "insulated",
    }, timeout=30).json()

def gamma(n, elems, calc_data, tube_od, rod_od, tube_length):
    mi = calc_data.get("matching_info", {})
    gd = mi.get("gamma_design", {})
    fz = gd.get("feedpoint_impedance_ohms", 25)
    res_freq = mi.get("element_resonant_freq_mhz", 27.185)
    driven = next(e for e in elems if e["element_type"] == "driven")
    refl = next(e for e in elems if e["element_type"] == "reflector")
    dirs = sorted([e for e in elems if e["element_type"] == "director"], key=lambda x: x["position"])
    refl_sp = abs(driven["position"] - refl["position"])
    dir_sp = [abs(d["position"] - driven["position"]) for d in dirs]
    return requests.post(f"{API_URL}/api/gamma-designer", json={
        "num_elements": n, "driven_element_length_in": driven["length"],
        "frequency_mhz": 27.185, "feedpoint_impedance": fz,
        "element_resonant_freq_mhz": res_freq, "reflector_spacing_in": refl_sp,
        "director_spacings_in": dir_sp, "driven_element_dia": 0.5,
        "custom_tube_od": tube_od, "custom_rod_od": rod_od,
        "custom_tube_length": tube_length,
    }, timeout=30).json()

def fmt(v, f=".2f"):
    return format(v, f) if isinstance(v, (int, float)) else str(v)

combos = [
    ("DEFAULT: 3/4in Tube + 5/8in Rod (3in tube)", 0.75, 0.625, None),
    ("COMBO A: 1in Tube + 5/8in Rod (15in tube)", 1.0, 0.625, 15.0),
    ("COMBO B: 1-1/4in Tube + 3/4in Rod (18in tube)", 1.25, 0.75, 18.0),
]

for name, tube_od, rod_od, tube_len in combos:
    wall = 0.049
    tube_id = tube_od - 2 * wall
    gap = (tube_id - rod_od) / 2
    v_peak = (2 * 5000 * 50 * 4.17) ** 0.5
    teflon_bv = gap * 1000 * 500
    tl_str = f"{tube_len}in" if tube_len else "default"
    print()
    print("=" * 130)
    print(f"  {name}  |  Gap: {gap:.3f}in ({gap*1000:.0f} mils)")
    print(f"  5kW Safety: PTFE breakdown {teflon_bv:.0f}V vs peak {v_peak:.0f}V = {teflon_bv/v_peak:.1f}x margin")
    print("=" * 130)
    print(f"  {'Elem':>4} | {'SWR':>7} | {'RL dB':>6} | {'Null':>4} | {'Bar':>6} | {'Ins':>5} | {'Cap':>5} | {'K':>5} | {'K^2':>5} | {'ZmR':>6} | {'ZmX':>7} | {'Z Feed':>6} | {'Drv Rec':>7}")
    print("  " + "-" * 120)

    for n in range(5, 21):
        elems = build_yagi(n)
        c = calc(n, elems)
        if tube_len:
            g = gamma(n, elems, c, tube_od, rod_od, tube_len)
        else:
            g = gamma(n, elems, c, tube_od, rod_od, 3.0)
        r = g.get("recipe", {})
        swr = r.get("swr_at_null", 99)
        null_ok = "Y" if r.get("null_reachable") else "N"
        mi = c.get("matching_info", {}).get("gamma_design", {})
        fz = mi.get("feedpoint_impedance_ohms", 0)
        mark = " <<<" if swr < 1.05 else (" <--" if swr < 1.2 else (" *" if swr < 1.5 else ""))
        print(f"  {n:>4} | {fmt(swr,'.3f'):>7} | {fmt(r.get('return_loss_at_null','N/A'),'.1f'):>6} | {null_ok:>4} | {fmt(r.get('ideal_bar_position','N/A'),'.1f'):>6} | {fmt(r.get('optimal_insertion','N/A'),'.1f'):>5} | {fmt(r.get('capacitance_at_null','N/A'),'.0f'):>5} | {fmt(r.get('k_step_up','N/A'),'.2f'):>5} | {fmt(r.get('k_squared','N/A'),'.2f'):>5} | {fmt(r.get('z_matched_r','N/A'),'.1f'):>6} | {fmt(r.get('z_matched_x','N/A'),'.1f'):>7} | {fz:>6} | {fmt(r.get('recommended_driven_length_in','N/A'),'.1f'):>7}{mark}")

print("\nDone.")
