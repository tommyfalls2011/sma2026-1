# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator (React/Expo frontend + FastAPI backend + MongoDB) for ham radio operators. Features Yagi antenna design, gamma match physics simulation, and a "Gamma Match Designer" that recommends optimal hardware and tuning settings.

## Architecture
```
/app/
├── backend/
│   ├── server.py              # FastAPI main server
│   ├── models.py              # Pydantic models for API requests/responses
│   ├── gamma_sweep.py         # Parameter sweep simulation script (standalone)
│   ├── routes/
│   │   └── antenna.py         # /api/calculate and /api/gamma-designer endpoints
│   └── services/
│       └── physics.py         # Core physics engine (~1900 lines)
├── frontend/
│   ├── app/
│   │   └── index.tsx          # Main page (~2800 lines)
│   └── components/
│       ├── SwrMeter.tsx       # SWR Bandwidth chart with zone overlays
│       ├── SmithChart.tsx     # Smith Chart display
│       ├── GammaDesigner.tsx  # Gamma Match Designer modal
│       ├── styles.ts          # Shared styles
│       └── types.ts           # TypeScript interfaces
└── memory/
    └── PRD.md                 # This file
```

## Key API Endpoints
- `POST /api/calculate` — Main antenna calculation (feedpoint R, SWR, gain, matching network, SWR curve, Smith Chart)
- `POST /api/gamma-designer` — Gamma Match Designer (recommends hardware + tuning for target SWR)

## What's Been Implemented

### Core Features (Pre-existing)
- Yagi antenna calculator with 2-8 elements
- Feedpoint impedance model with mutual coupling
- Gamma, hairpin, and direct feed matching
- SWR meter, Smith Chart, gain/F-B calculations
- User auth, subscription tiers, tutorial system

### Session: Feb 2026 (Fork 6) — COMPLETED
- **(P0) SWR Curve & Smith Chart Fix**: SWR curve now derived from full-physics Smith Chart impedance data (was parabolic approximation). Smith Chart uses `matching_info["z0_gamma"]` from actual hardware (was hardcoded 3.5"/0.375").
- **SWR Bandwidth Overlay**: Green (≤1.5) and yellow (≤2.0) gradient zone bands with channel count badges on SWR chart.
- **Gamma Tuned Frequency**: Now derived from actual SWR curve minimum (was old bar-position formula). Frontend displays `results.resonant_freq_mhz` (curve min) instead of `matching_info.resonant_freq_mhz` (formula).

### Session: Feb 2026 (Fork 7 — CURRENT) — IN PROGRESS

#### Completed This Session
1. **Rod OD Default Change**: Changed from 0.375" to current sim-optimized values
2. **Z0 Unequal Conductor Formula**: `Z0 = 276 × log10(2D / √(d1×d2))` where d1=element dia, d2=rod dia. Previously only used rod diameter.
3. **Stub Inductance Display**: Added `stub_inductance_nh` to matching_info. `L = X_stub / (2πf)` from shorted transmission line model.
4. **Inline Gamma SWR Meter**: New UI widget in gamma tuning area showing: SWR bar, Z0 (both conductor diameters), Stub L (nH), X_stub, X_cap, Net X, Z_match. Updates live with bar/insertion adjustments.
5. **Bar Position Fine Tuning**: Changed from 1" to 0.25" step increments.
6. **Rod Length Correction**: Changed from 7.4% to 4.5% of wavelength per user's physics reference (~19.5" instead of ~32" for 11m).
7. **Feedpoint Impedance Correction**: Director coupling factors were too aggressive (dropping 4-elem to 13Ω instead of 25Ω). Corrected to give realistic values: 2-elem ~33-36Ω, 3-elem ~23-27Ω, 4-elem ~20-25Ω.
8. **driven_element_dia_in Parameter**: Added to `apply_matching_network()` function signature and passed from caller. Used in Z0 geometric mean calculation.
9. **Gamma Parameter Sweep Simulation** (`/app/backend/gamma_sweep.py`): Tested 3960 combinations of tube OD (10 sizes), rod OD (4 tube/rod ratios: 1.3-1.6), tube length (10 lengths), and rod length (22-48"). Found ~130 pF is the magic capacitance for cancelling stub inductance at 27.185 MHz with 25Ω feedpoint.

### Session: Feb 19, 2026 (Fork 8 — CURRENT) — COMPLETED

#### Bug Fixes Completed & Tested (12/12 tests passed)
1. **(P0) Dynamic Tube Length**: Changed `tube_length = 15.0` to `tube_length = round(gamma_rod_length, 1)` in `apply_matching_network()`. Now ~19.5" for 11m CB, scales with wavelength for other bands. This unblocked 2-element Yagi tuning (needed 17"+ insertion).
2. **(P0) Gamma Design Consistency**: Fixed `gamma_design` dict to use actual hardware dimensions from matching calculation instead of stale hardcoded `design_tube_id=0.527`, `design_rod_od=0.500`. Series Cap now shows correct 89.4 pF (was 451.4 pF).
3. **Smith Chart Capacitance Clamping**: Clamped `capacitance_pf` to 0 when |sc_x| < 0.5 Ohm or C > 1000 pF. Eliminates near-resonance artifacts showing 25000+ pF.
4. **Dynamic Teflon Sleeve**: Teflon sleeve length now = tube_length + 1.0" (was hardcoded 16.0"). Updated backend technical_notes and frontend display.
5. **Frontend Fallback Updates**: Updated fallback values in frontend for tube length display and teflon sleeve text to match new dynamic values.

#### Current Defaults (just updated, need validation)
- **≤3 elements**: Rod 0.500", Tube 0.750" (ID 0.652", ratio 1.30, 11.2 pF/in)
- **4-6 elements**: Rod 0.500", Tube 0.750" (same)
- Previous attempt with 0.769/1.000 failed because tube wall thickness (0.049") left only 0.067" clearance per side — impractical for assembly

#### Active Issue
The user tested the Gamma Designer with the 0.769/1.000 combo and got:
- "WARNING: ID/rod ratio 1.17:1 is very tight"
- "NULL NOT REACHABLE" — needs 315 pF (17" insertion) but tube is only 15"
- Defaults just changed to 0.500/0.750 but not yet tested by user

### Key Physics Concepts the New Agent MUST Understand

1. **Gamma Match = Two Independent Adjustments**:
   - **Bar position** → Controls Resistance (R). Moving bar outward from center increases the step-up ratio K. R_matched = feedpoint_R × K².
   - **Rod insertion depth** → Controls Capacitance (C in pF). More overlap between rod and tube = more pF. Capacitance cancels the stub inductance.

2. **Step-Up Ratio K**: `K = 1 + (bar_pos / half_element_length) × coupling_multiplier` where `coupling_multiplier = Z0_gamma / 73.0`

3. **Z0 of Gamma Section** (unequal conductor two-wire line): `Z0 = 276 × log10(2 × spacing / √(element_dia × rod_dia))`

4. **Capacitance Per Inch**: `C_pf_per_inch = 1.413 × ε_r / ln(tube_ID / rod_OD)` where ε_r = 2.1 for Teflon

5. **SWR Curve**: Derived from Smith Chart impedance sweep. For each frequency: compute antenna reactance, apply gamma transform (K², stub, cap), calculate reflection coefficient Γ, derive SWR = (1+|Γ|)/(1-|Γ|).

6. **Rod Length**: 4-5% of wavelength (per user's physics reference). At 27.185 MHz: ~19.5".

7. **Target Capacitance**: ~130 pF for HF gamma match at 27 MHz (cancels ~260 nH stub inductance).

8. **Practical Hardware**: Tube ID / Rod OD ratio must be ≥ 1.2 (preferably 1.3-1.6) for assembly clearance. Wall thickness = 0.049" for standard thin-wall aluminum.

## Backlog
- (P2) Air gap dielectric model (teflon sleeve OD parameter)
- (P2) PayPal/CashApp Payments
- (P2) Improve .easignore
- (P3) Build iOS Version

## Known Issues
- Tube/Rod ratio validation: Designer warns but main calculator doesn't
- Platform Chat UI bug: Messages occasionally duplicate (Emergent platform issue)
- Frontend caching: Expo Metro bundler aggressively caches; user may need hard refresh or incognito window

## Credentials
- Store Admin: fallstommy@gmail.com / admin123
- Bronze Test: bronze@test.com / password123

## 3rd Party Integrations
- MongoDB Atlas, GitHub API, Expo/EAS, Stripe

## Files of Reference (Priority Order)
1. `backend/services/physics.py` — ALL physics logic, matching network, Smith Chart, SWR curve
2. `backend/routes/antenna.py` — API endpoints
3. `backend/models.py` — Pydantic request/response models
4. `backend/gamma_sweep.py` — Parameter sweep simulation
5. `frontend/app/index.tsx` — Main UI, state management, gamma controls
6. `frontend/components/SwrMeter.tsx` — SWR Bandwidth chart with zone overlays
7. `frontend/components/GammaDesigner.tsx` — Designer modal UI
