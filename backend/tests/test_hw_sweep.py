"""Test increased rod spacing to bring K² down to ~2.6 for high-power combos."""
import requests, math

API_URL = "https://swr-optimizer.preview.emergentagent.com"

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

def gamma(n, elems, calc_data, tube_od, rod_od, tube_length, rod_spacing):
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
        "custom_tube_length": tube_length, "custom_rod_spacing": rod_spacing,
    }, timeout=30).json()

def fmt(v, f=".2f"):
    return format(v, f) if isinstance(v, (int, float)) else str(v)

# ── PART 1: Find the magic spacing for each combo ──
print("=" * 130)
print("  PART 1: SPACING SWEEP — Finding where K² ≈ 2.6 for 8-element Yagi (Z=19Ω)")
print("=" * 130)

combos = [
    ("1in Tube + 5/8in Rod", 1.0, 0.625, 15.0),
    ("1-1/4in Tube + 3/4in Rod", 1.25, 0.75, 18.0),
]

best_spacings = {}

for name, tube_od, rod_od, tube_len in combos:
    tube_id = tube_od - 0.098
    gap = (tube_id - rod_od) / 2
    print(f"\n  {name}  |  Gap: {gap:.3f}in  |  Tube length: {tube_len}in")
    print(f"  {'Spc':>5} | {'SWR':>7} | {'RL dB':>6} | {'Null':>4} | {'Bar':>6} | {'Ins':>5} | {'Cap':>5} | {'C/in':>5} | {'K':>5} | {'K^2':>5} | {'ZmR':>6} | {'ZmX':>7} | {'Z0g':>5}")
    print("  " + "-" * 110)

    n = 8
    elems = build_yagi(n)
    c = calc(n, elems)
    best_swr = 99
    best_sp = 3.5

    for sp_x10 in range(35, 201, 5):  # 3.5" to 20.0" in 0.5" steps
        spacing = sp_x10 / 10.0
        g = gamma(n, elems, c, tube_od, rod_od, tube_len, spacing)
        r = g.get("recipe", {})
        swr = r.get("swr_at_null", 99)
        k = r.get("k_step_up", 0)
        k2 = r.get("k_squared", 0)
        zmr = r.get("z_matched_r", 0)
        # Z0 of gamma section
        geo_mean = math.sqrt(0.5 * rod_od)
        z0g = 276 * math.log10(2 * spacing / geo_mean) if spacing > geo_mean / 2 else 0

        null_ok = "Y" if r.get("null_reachable") else "N"
        mark = " <<<" if swr < 1.2 else (" <--" if swr < 1.5 else (" *" if swr < 2.0 else ""))
        if swr < best_swr:
            best_swr = swr
            best_sp = spacing
        # Only print interesting rows
        if sp_x10 % 10 == 0 or sp_x10 == 35 or swr < 2.0:
            print(f"  {spacing:>5} | {fmt(swr,'.3f'):>7} | {fmt(r.get('return_loss_at_null','N/A'),'.1f'):>6} | {null_ok:>4} | {fmt(r.get('ideal_bar_position','N/A'),'.1f'):>6} | {fmt(r.get('optimal_insertion','N/A'),'.1f'):>5} | {fmt(r.get('capacitance_at_null','N/A'),'.0f'):>5} | {fmt(r.get('cap_per_inch','N/A'),'.1f'):>5} | {fmt(k,'.2f'):>5} | {fmt(k2,'.2f'):>5} | {fmt(zmr,'.1f'):>6} | {fmt(r.get('z_matched_x','N/A'),'.1f'):>7} | {fmt(z0g,'.0f'):>5}{mark}")

    best_spacings[name] = best_sp
    print(f"\n  >>> Best SWR: {best_swr:.3f} at spacing: {best_sp}in")


# ── PART 2: Run full 5-20 elements with the best spacing found ──
print("\n\n" + "=" * 130)
print("  PART 2: FULL ELEMENT SWEEP AT OPTIMAL SPACING")
print("=" * 130)

for name, tube_od, rod_od, tube_len in combos:
    tube_id = tube_od - 0.098
    gap = (tube_id - rod_od) / 2
    sp = best_spacings[name]
    print(f"\n  {name}  |  Spacing: {sp}in  |  Gap: {gap:.3f}in  |  Tube: {tube_len}in")
    print(f"  {'Elem':>4} | {'SWR':>7} | {'RL dB':>6} | {'Null':>4} | {'Bar':>6} | {'Ins':>5} | {'Cap':>5} | {'K':>5} | {'K^2':>5} | {'ZmR':>6} | {'ZmX':>7} | {'Z Feed':>6} | {'Drv Len':>7}")
    print("  " + "-" * 115)

    for n in range(5, 21):
        elems = build_yagi(n)
        c = calc(n, elems)
        g = gamma(n, elems, c, tube_od, rod_od, tube_len, sp)
        r = g.get("recipe", {})
        swr = r.get("swr_at_null", 99)
        null_ok = "Y" if r.get("null_reachable") else "N"
        mi = c.get("matching_info", {}).get("gamma_design", {})
        fz = mi.get("feedpoint_impedance_ohms", 0)
        mark = " <<<" if swr < 1.1 else (" <--" if swr < 1.5 else "")
        print(f"  {n:>4} | {fmt(swr,'.3f'):>7} | {fmt(r.get('return_loss_at_null','N/A'),'.1f'):>6} | {null_ok:>4} | {fmt(r.get('ideal_bar_position','N/A'),'.1f'):>6} | {fmt(r.get('optimal_insertion','N/A'),'.1f'):>5} | {fmt(r.get('capacitance_at_null','N/A'),'.0f'):>5} | {fmt(r.get('k_step_up','N/A'),'.2f'):>5} | {fmt(r.get('k_squared','N/A'),'.2f'):>5} | {fmt(r.get('z_matched_r','N/A'),'.1f'):>6} | {fmt(r.get('z_matched_x','N/A'),'.1f'):>7} | {fz:>6} | {fmt(r.get('recommended_driven_length_in','N/A'),'.1f'):>7}{mark}")

    # 5kW safety
    v_peak = (2 * 5000 * 50 * 4.17) ** 0.5
    teflon_bv = gap * 1000 * 500
    print(f"\n  5kW Safety: V_peak={v_peak:.0f}V | Gap={gap*1000:.0f} mils | PTFE breakdown={teflon_bv:.0f}V | Margin: {teflon_bv/v_peak:.1f}x")

print("\nDone.")
