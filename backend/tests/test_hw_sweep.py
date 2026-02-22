"""Sweep rod spacing + tube length for both high-power combos on 8-element Yagi."""
import requests

API_URL = "https://swr-optimizer.preview.emergentagent.com"

def build_yagi(n):
    elements = [{"element_type": "reflector", "length": 216.0, "diameter": 0.5, "position": 0},
                {"element_type": "driven", "length": 203.0, "diameter": 0.5, "position": 48}]
    dir_lengths = [195, 192, 190, 188, 187, 186, 185, 184, 183, 183]
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
        "custom_tube_length": tube_length,
        "custom_rod_spacing": rod_spacing,
    }, timeout=30).json()

def fmt(v, f=".2f"):
    return format(v, f) if isinstance(v, (int, float)) else str(v)

n = 8
elems = build_yagi(n)
c = calc(n, elems)

combos = [
    ("COMBO A: 1in Tube + 5/8in Rod", 1.0, 0.625),
    ("COMBO B: 1-1/4in Tube + 3/4in Rod", 1.25, 0.75),
]

for name, tube_od, rod_od in combos:
    tube_id = tube_od - 0.098
    gap = (tube_id - rod_od) / 2
    print()
    print("=" * 115)
    print(f"  {name}  |  Gap/side: {gap:.3f}in  |  8-element Yagi (Z_feed=19 ohm)")
    print("=" * 115)
    hdr = f"{'Spc':>5} | {'TubeL':>5} | {'SWR':>7} | {'RL dB':>5} | {'OK':>2} | {'Bar':>6} | {'Ins':>5} | {'CapPF':>5} | {'C/in':>4} | {'K':>5} | {'ZmR':>5} | {'ZmX':>7}"
    print(hdr)
    print("-" * 115)

    for spacing in [3.5, 5.0, 6.5, 8.0, 10.0, 12.0]:
        for tube_len in [6, 10, 15, 20, 25]:
            g = gamma(n, elems, c, tube_od, rod_od, tube_len, spacing)
            r = g.get("recipe", {})
            swr = r.get("swr_at_null", 99)
            null_ok = "Y" if r.get("null_reachable") else "N"
            mark = " <<<" if swr < 1.5 else (" <-" if swr < 2.5 else "")
            bar = fmt(r.get("ideal_bar_position", "N/A"), ".1f")
            ins = fmt(r.get("optimal_insertion", "N/A"), ".1f")
            cap = fmt(r.get("capacitance_at_null", "N/A"), ".0f")
            cin = fmt(r.get("cap_per_inch", "N/A"), ".1f")
            k = fmt(r.get("k_step_up", "N/A"), ".2f")
            zmr = fmt(r.get("z_matched_r", "N/A"), ".1f")
            zmx = fmt(r.get("z_matched_x", "N/A"), ".1f")
            rl = fmt(r.get("return_loss_at_null", "N/A"), ".1f")
            print(f"{spacing:>5} | {tube_len:>5} | {fmt(swr,'.3f'):>7} | {rl:>5} | {null_ok:>2} | {bar:>6} | {ins:>5} | {cap:>5} | {cin:>4} | {k:>5} | {zmr:>5} | {zmx:>7}{mark}")
        print()

print("Done.")
