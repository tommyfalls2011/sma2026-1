# Gamma Match Physics - Detailed Technical Handoff

## Overview
The gamma match model in `backend/services/physics.py` was completely rewritten in Fork 4 to be physics-based instead of heuristic. SWR, Return Loss, and Smith Chart all derive from a single impedance model.

## Core Physics Model (apply_matching_network, ~line 205)

### Impedance Transformation
```
Z_matched = R_feedpoint × K² + j(X_stub + X_cap)
where:
  K² = 50 / feedpoint_R           (step-up ratio, geometric constant)
  X_stub = Z0_gamma × tan(β × L)  (shorted transmission line stub)
  X_cap = -1/(2πfC)               (series coaxial capacitor)
  Z0_gamma = 276 × log10(2 × spacing / rod_dia)
  β = 2π / wavelength
  L = bar_position in meters
```

### SWR from Impedance
```
Γ = (Z_matched - 50) / (Z_matched + 50)
SWR = (1 + |Γ|) / (1 - |Γ|)
Return Loss = -20 × log10(|Γ|)
```

### Coaxial Capacitor
```
C_per_inch = 1.413 × ε_r / ln(tube_ID / rod_OD)
where ε_r = 2.1 (teflon)
Total C = C_per_inch × insertion_inches
```
**IMPORTANT**: `insertion_cap_pf_exact` (full precision float) is used for physics calculations. `insertion_cap_pf` (rounded to 0.1 pF) is display only. This was a bug fix — rounding before calculation killed precision at the null point.

## Hardware Scaling (auto-selected by num_elements)

The function takes `num_elements` parameter and auto-selects hardware:
```
Elements  Rod OD    Tube OD   Tube ID   Spacing  Cap/inch  Z0_gamma
2-3       3/8"      5/8"      0.527"    3.5"     8.72      350.8
4-6       1/2"      3/4"      0.652"    4.0"     11.18     332.3
7-10      1/2"      7/8"      0.777"    4.5"     6.73      346.5
11-14     5/8"      1"        0.902"    5.0"     8.09      332.3
15-17     5/8"      1-1/8"    1.027"    5.5"     5.97      343.5
18-20     3/4"      1-1/4"    1.152"    6.0"     6.91      332.3
```

### Critical Design Rule
Tube/Rod diameter ratio MUST be 1.3-1.6×. Higher ratios = lower pF/inch = null falls outside tube.
- 1.4× ratio → ~8-11 pF/inch (ideal, null at 8-10")
- 1.55× ratio → ~6-7 pF/inch (null at 13-15", tight fit)
- 1.8× ratio → ~5 pF/inch (null may not fit in 15" tube!)
- 4-6× ratio → 1-2 pF/inch (completely unusable)

User can override defaults with `gamma_rod_dia`, `gamma_tube_od`, `gamma_rod_spacing` API parameters.

## Constants
- Tube wall: 0.049" (standard aluminum)
- Tube length: 15" (hardcoded)
- Teflon sleeve: 16" (hardcoded)
- Rod length: ~32" (calculated as wavelength × 0.074)
- Bar position default: 13"
- Rod insertion default: 8"

## Null Point Behavior
The "null" is where X_stub + X_cap = 0 (stub inductance perfectly cancels cap reactance).
- At null: Z_matched ≈ 50 + j0, SWR = 1.000, RL = 80 dB (model ceiling)
- For 3-element (3/8" rod, 5/8" tube): null at 10.0512", 87.663 pF
- Bar=13" gives X_stub ≈ 66.8 ohms for the 2-3 element tier
- Different hardware tiers have different X_stub values (different Z0_gamma)

## Smith Chart (line ~1165)
Uses identical physics as apply_matching_network but sweeps across frequency:
- At each freq: calculates X_ant from antenna Q model, X_stub(f), X_cap(f)
- R transformation uses constant K² (NOT frequency-dependent k_eff — that was removed)
- sc_r = feedpoint_R × K²
- sc_x = (X_ant × step_up) + X_stub + X_cap

## Return Loss Section (line ~960)
For gamma match: uses `matching_info["z_matched_r"]` and `matching_info["z_matched_x"]` directly.
For hairpin/direct: uses separate reactance model.
All feed types then compute Γ, return_loss_db, mismatch_loss_db from the same formula.

## matching_info Dict (returned from apply_matching_network for gamma)
Key fields used downstream:
- `z_matched_r`, `z_matched_x` — final impedance (used by return loss section)
- `x_stub`, `x_cap`, `net_reactance` — reactance components (displayed in UI)
- `z0_gamma` — characteristic impedance of gamma section
- `insertion_cap_pf` — display value (rounded)
- `step_up_ratio` — K value (used by Smith Chart)
- `bar_position_inches` — bar pos (used by Smith Chart)
- `resonant_freq_mhz` — system resonant freq (used by SWR curve)
- `q_factor`, `gamma_bandwidth_mhz`, `bandwidth_mult` — bandwidth params
- `hardware` dict — rod_od, tube_od, tube_id, tube_wall, rod_spacing, cap_per_inch, etc.
- `reflection_coefficient` — |Γ| at center freq

## Known Issues for Next Agent

### 1. K not tied to bar position (P1)
Currently K = sqrt(50/feedpoint_R) regardless of bar position. In reality, bar position determines K geometrically. This means all element counts show identical SWR at same bar/insertion settings, which isn't physical. A 5-element Yagi (12.8Ω feedpoint, needs K=1.98) should require a longer bar than a 3-element (19.3Ω, needs K=1.61).

### 2. Air gap in dielectric (P1)
Model assumes pure teflon fill between rod and tube. Real hardware has a teflon sleeve with specific OD — gap between sleeve and tube wall is air (ε_r=1.0). This creates two capacitors in series, reducing effective pF/inch. User reported expecting 76.1 pF at null vs model's 87.2 pF. Fix: model as series caps with teflon + air layers. Need teflon sleeve OD from user.

### 3. SWR curve approximation
SWR curve uses parabolic model (calculate_swr_at_frequency) centered on resonant_freq. Could derive from Smith Chart impedance at each frequency for full consistency. Lower priority since center-freq SWR is already unified.

## Testing Done
- 13/13 automated backend tests (testing_agent_v3_fork, iteration_21.json)
- Insertion sweeps: 0-15" at 1/8" and 1/32" resolution
- Bar position sweeps: 3-28"
- Binary search null finding (sub-nanoinch precision)
- Hardware scaling: all tiers 2-20 elements verified, null within 15" tube
- Custom hardware: tested 2.5" tube with 3/8", 1/2", 1-3/4" rods; 1" tube with 1/2" rod
- Tube length variations: 8"-16"
- Teflon length variations: 12", 16" (no effect when teflon >= tube)

## Test Commands
```bash
# Basic 3-element gamma test
curl -s -X POST "http://localhost:8001/api/calculate" \
  -H "Content-Type: application/json" \
  -d '{"band":"11m_cb","frequency_mhz":27.185,"num_elements":3,
  "antenna_orientation":"horizontal","height_from_ground":50,"height_unit":"ft",
  "boom_diameter":2,"boom_unit":"inches","boom_grounded":true,"boom_mount":"bonded",
  "feed_type":"gamma","gamma_rod_dia":0.375,"gamma_rod_spacing":3.5,
  "gamma_bar_pos":13,"gamma_element_gap":10,
  "elements":[
    {"element_type":"reflector","length":214,"diameter":0.5,"position":0},
    {"element_type":"driven","length":203,"diameter":0.5,"position":44},
    {"element_type":"director","length":195,"diameter":0.5,"position":100}
  ]}'

# Custom tube OD test (20-element with 2.5" tube, 1-3/4" rod)
curl -s -X POST "http://localhost:8001/api/calculate" \
  -H "Content-Type: application/json" \
  -d '{"band":"11m_cb","frequency_mhz":27.185,"num_elements":20,
  "antenna_orientation":"horizontal","height_from_ground":50,"height_unit":"ft",
  "boom_diameter":2,"boom_unit":"inches","boom_grounded":true,"boom_mount":"bonded",
  "feed_type":"gamma","gamma_rod_dia":1.75,"gamma_tube_od":2.5,"gamma_rod_spacing":6.0,
  "gamma_bar_pos":13,"gamma_element_gap":14.25,
  "elements":[...]}'
```
