"""Gamma Match Parameter Sweep Simulation
Tests combinations of tube diameter, rod diameter, tube length, and rod length
for a 4-element Yagi at 27.185 MHz with ~25 ohm feedpoint impedance.
"""
import sys
sys.path.insert(0, '/app/backend')
import math
import json

# Constants
FREQ_MHZ = 27.185
FREQ_HZ = FREQ_MHZ * 1e6
WAVELENGTH_M = 299792458.0 / FREQ_HZ
WAVELENGTH_IN = WAVELENGTH_M / 0.0254
Z0_TARGET = 50.0
FEEDPOINT_R = 25.0  # 4-element Yagi feedpoint
DIELECTRIC_K = 2.1  # Teflon
WALL_THICKNESS = 0.049  # Standard thin-wall aluminum

# Parameter ranges
TUBE_ODS = [0.500, 0.625, 0.750, 0.875, 1.000, 1.125, 1.250, 1.375, 1.500, 1.625]
TUBE_ROD_RATIOS = [1.3, 1.4, 1.5, 1.6]
TUBE_LENGTHS = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24]  # inches
ROD_LENGTHS = [22, 25, 28, 31, 34, 37, 40, 43, 46, 48]  # inches

OMEGA = 2.0 * math.pi * FREQ_HZ
ELEMENT_DIA = 0.5  # driven element diameter
SPACING = 3.5  # rod-element spacing

results = []

for tube_od in TUBE_ODS:
    tube_id = tube_od - 2 * WALL_THICKNESS
    
    for ratio in TUBE_ROD_RATIOS:
        rod_od = round(tube_od / ratio, 4)
        
        # Skip if rod doesn't fit in tube
        if rod_od >= tube_id:
            continue
        
        # Capacitance per inch (coaxial capacitor with teflon)
        cap_per_inch = 24.16 * DIELECTRIC_K / (25.4 * math.log(tube_id / rod_od))
        
        # Z0 of gamma section (unequal conductor two-wire line)
        geo_mean = math.sqrt(ELEMENT_DIA * rod_od)
        z0_gamma = 276.0 * math.log10(2.0 * SPACING / geo_mean)
        
        for tube_len in TUBE_LENGTHS:
            max_cap_pf = cap_per_inch * tube_len
            
            for rod_len in ROD_LENGTHS:
                # Tube can't be longer than rod
                if tube_len > rod_len:
                    continue
                
                # Find optimal bar position for R match
                # K = sqrt(50 / feedpoint_r) for perfect R match
                k_ideal = math.sqrt(Z0_TARGET / FEEDPOINT_R)
                
                # Try bar positions from 4" to rod_len
                best_swr = 99.0
                best_bar = 0
                best_insertion = 0
                best_cap = 0
                best_x_stub = 0
                best_x_cap = 0
                best_net_x = 0
                best_z_r = 0
                
                for bar_tenth in range(40, int(rod_len * 10) + 1, 5):  # 0.5" steps
                    bar_pos = bar_tenth / 10.0
                    
                    # Geometric K factor from bar position
                    half_el = 101.5  # ~half of 203" driven element
                    k_geo = 1.0 + bar_pos / half_el
                    # Coupling multiplier from Z0
                    coupling = z0_gamma / 75.0
                    k = k_geo * coupling
                    k_sq = k ** 2
                    
                    # Transformed resistance
                    z_r = FEEDPOINT_R * k_sq
                    
                    # Stub reactance
                    bar_m = bar_pos * 0.0254
                    beta_l = 2.0 * math.pi * bar_m / WAVELENGTH_M
                    if beta_l > 1.5:  # avoid tan blow-up
                        continue
                    x_stub = z0_gamma * math.tan(beta_l)
                    
                    # Try insertion depths
                    for ins_tenth in range(10, int(tube_len * 10) + 1, 5):
                        insertion = ins_tenth / 10.0
                        cap_pf = cap_per_inch * insertion
                        if cap_pf <= 0:
                            continue
                        x_cap = -1.0 / (OMEGA * cap_pf * 1e-12)
                        net_x = x_stub + x_cap
                        
                        # SWR from Z = z_r + j*net_x vs 50 ohm
                        denom = (z_r + Z0_TARGET) ** 2 + net_x ** 2
                        gamma_re = ((z_r - Z0_TARGET) * (z_r + Z0_TARGET) + net_x ** 2) / denom
                        gamma_im = (2 * net_x * Z0_TARGET) / denom
                        gamma_mag = math.sqrt(gamma_re ** 2 + gamma_im ** 2)
                        gamma_mag = min(gamma_mag, 0.999)
                        swr = (1 + gamma_mag) / (1 - gamma_mag)
                        swr = max(1.0, swr)
                        
                        if swr < best_swr:
                            best_swr = swr
                            best_bar = bar_pos
                            best_insertion = insertion
                            best_cap = cap_pf
                            best_x_stub = x_stub
                            best_x_cap = x_cap
                            best_net_x = net_x
                            best_z_r = z_r
                
                if best_swr < 10:
                    stub_l_nh = best_x_stub / OMEGA * 1e9 if OMEGA > 0 else 0
                    results.append({
                        "tube_od": tube_od,
                        "tube_id": round(tube_id, 3),
                        "rod_od": rod_od,
                        "ratio": ratio,
                        "tube_len": tube_len,
                        "rod_len": rod_len,
                        "cap_per_inch": round(cap_per_inch, 2),
                        "max_cap_pf": round(max_cap_pf, 1),
                        "z0_gamma": round(z0_gamma, 1),
                        "best_swr": round(best_swr, 3),
                        "bar_pos": best_bar,
                        "insertion": best_insertion,
                        "cap_pf": round(best_cap, 1),
                        "x_stub": round(best_x_stub, 1),
                        "x_cap": round(best_x_cap, 1),
                        "net_x": round(best_net_x, 1),
                        "z_r": round(best_z_r, 1),
                        "stub_l_nh": round(stub_l_nh, 1),
                    })

# Sort by best SWR
results.sort(key=lambda r: r["best_swr"])

# Print top 50 combinations
print(f"{'='*140}")
print(f"GAMMA MATCH PARAMETER SWEEP — 4-Element Yagi, {FREQ_MHZ} MHz, Feedpoint R = {FEEDPOINT_R}Ω, Target = {Z0_TARGET}Ω")
print(f"Element Dia: {ELEMENT_DIA}\", Spacing: {SPACING}\", Dielectric: Teflon (ε={DIELECTRIC_K})")
print(f"{'='*140}")
print(f"{'Tube OD':>7} {'TubeID':>6} {'RodOD':>6} {'Ratio':>5} {'TubeL':>5} {'RodL':>5} | {'pF/in':>5} {'MaxpF':>5} {'Z0':>5} | {'SWR':>6} {'Bar':>5} {'Ins':>5} {'Cap':>6} | {'Xstub':>6} {'Xcap':>7} {'NetX':>6} {'Zr':>5} {'StubL':>6}")
print(f"{'-'*140}")

count = 0
for r in results:
    if r["best_swr"] <= 1.5:
        print(f"{r['tube_od']:7.3f} {r['tube_id']:6.3f} {r['rod_od']:6.4f} {r['ratio']:5.1f} {r['tube_len']:5d} {r['rod_len']:5d} | {r['cap_per_inch']:5.2f} {r['max_cap_pf']:5.1f} {r['z0_gamma']:5.1f} | {r['best_swr']:6.3f} {r['bar_pos']:5.1f} {r['insertion']:5.1f} {r['cap_pf']:6.1f} | {r['x_stub']:6.1f} {r['x_cap']:7.1f} {r['net_x']:6.1f} {r['z_r']:5.1f} {r['stub_l_nh']:6.1f}")
        count += 1
        if count >= 60:
            break

print(f"\n{'='*140}")
print(f"Total combinations tested: {len(results)}")
print(f"Combinations with SWR ≤ 1.5: {sum(1 for r in results if r['best_swr'] <= 1.5)}")
print(f"Combinations with SWR ≤ 1.2: {sum(1 for r in results if r['best_swr'] <= 1.2)}")
print(f"Combinations with SWR ≤ 1.1: {sum(1 for r in results if r['best_swr'] <= 1.1)}")
print(f"{'='*140}")

# Summary by tube OD
print(f"\n{'='*80}")
print("SUMMARY BY TUBE OD — Best achievable SWR for each tube size")
print(f"{'='*80}")
print(f"{'Tube OD':>7} {'Best Rod':>8} {'Ratio':>5} {'TubeL':>5} {'RodL':>5} {'Best SWR':>8} {'Bar':>5} {'Ins':>5} {'Cap pF':>6}")
print(f"{'-'*80}")
seen = set()
for r in results:
    if r['tube_od'] not in seen:
        seen.add(r['tube_od'])
        print(f"{r['tube_od']:7.3f} {r['rod_od']:8.4f} {r['ratio']:5.1f} {r['tube_len']:5d} {r['rod_len']:5d} {r['best_swr']:8.3f} {r['bar_pos']:5.1f} {r['insertion']:5.1f} {r['cap_pf']:6.1f}")
