# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator mobile app (React Native/Expo + FastAPI + MongoDB). Features include Yagi antenna design, gamma/hairpin/direct feed matching, SWR calculation, radiation patterns, Smith chart, admin panel with subscription tiers and feature gating.

## Current Version: 4.2.3 (versionCode 11)

## Test Credentials
- **Admin**: fallstommy@gmail.com / admin123
- **Bronze Test**: test_bronze@testuser.com / test123

## Key Files
- `backend/services/physics.py` — Core physics simulation (gamma match, SWR, Smith chart)
- `backend/models.py` — Pydantic models (AntennaInput includes gamma_tube_od)
- `frontend/app/index.tsx` — Main calculator UI
- `frontend/components/FeatureGate.tsx` — Lock overlay for gated features
- `frontend/context/AuthContext.tsx` — Auth + isFeatureAvailable()
- `release.sh` — Automated release script

## Physical Dimensions (User's Real Hardware - 3 Element)
- Outer tube: 5/8" OD, 0.049" standard wall -> 0.527" ID
- Gamma rod: 3/8" (0.375") diameter
- Teflon sleeve: 12-16" long over rod (er = 2.1)
- Tube length: 15"
- Rod-to-element spacing: 3.5" center-to-center
- Rod length: 32"

## Gamma Match Physics Model (Unified + Geometric K)
- Z0_gamma = 276 * log10(2 * spacing / rod_dia)
- **K = 1 + (bar_pos / half_element_length) × coupling_multiplier** (NEW - Fork 5)
- **coupling_multiplier = Z0_gamma / 73** (normalized rod coupling, ~4.8 for standard hardware)
- X_stub = Z0 * tan(beta * bar_pos) — shorted transmission line stub
- X_cap = -1/(2*pi*f*C) — series capacitor from rod insertion
- Z_matched = R_feedpoint * K² + j(X_stub + X_cap)
- Gamma = (Z_matched - 50)/(Z_matched + 50)
- SWR = (1 + |Gamma|)/(1 - |Gamma|)
- Return Loss = -20 * log10(|Gamma|)
- **Ideal bar position = half_len × (K_ideal - 1) / coupling** (NEW - Fork 5)
- Capacitance uses full precision internally (rounded only for display)

## Hardware Scaling Rule (2-20 Elements)
Implemented in apply_matching_network(), auto-selects hardware based on num_elements:
| Elements | Rod OD  | Tube OD | Cap/inch | Null Point |
|----------|---------|---------|----------|------------|
| 2-3      | 3/8"    | 5/8"    | 8.72     | ~10.1"     |
| 4-6      | 1/2"    | 3/4"    | 11.18    | ~8.3"      |
| 7-10     | 1/2"    | 7/8"    | 6.73     | ~13.2"     |
| 11-14    | 5/8"    | 1"      | 8.09     | ~11.4"     |
| 15-17    | 5/8"    | 1-1/8"  | 5.97     | ~15.0"     |
| 18-20    | 3/4"    | 1-1/4"  | 6.91     | ~13.4"     |

Key principle: tube/rod ratio must stay 1.3-1.6x for adequate pF/inch.
Custom tube OD supported via gamma_tube_od API parameter.

## API Parameters Added
- `gamma_tube_od` (Optional[float]) — Override default tube OD for custom hardware testing

## Session History

### Session: Feb 2026 (Fork 6)
- **(P0) SWR Curve & Smith Chart Discrepancy FIX**: COMPLETE. 9/9 tests pass.
  - **Root cause 1**: Smith Chart code read rod geometry from `gamma_design` dict (hardcoded defaults 3.5"/0.375") instead of actual hardware.
  - **Fix**: Now uses `matching_info["z0_gamma"]` which is pre-computed from actual rod dimensions in `apply_matching_network()`.
  - **Root cause 2**: SWR curve used `calculate_swr_at_frequency()` parabolic approximation instead of full physics.
  - **Fix**: Smith Chart computed FIRST with full gamma match physics at each frequency. SWR curve derived from reflection coefficients: SWR = (1+|Γ|)/(1-|Γ|).
  - SWR curve minimum now correctly at operating frequency (27.185 MHz), not shifted.
  - SWR at operating freq matches main displayed SWR value.
- **(Enhancement) SWR Bandwidth Overlay**: COMPLETE.
  - Gradient-filled green (≤1.5) and yellow (≤2.0) zone bands with dashed edge boundaries
  - Channel count badges ("X CH") inside zone bands
  - Min SWR indicator dot with value label on the curve
  - Legend shows bandwidth MHz and channel counts per zone

### Session: Feb 19, 2026 (Fork 5)
- **(P0) Custom Hardware Test**: 1" OD tube / 1/2" rod — cap/inch=5.03, ID/rod ratio 1.80:1 (above optimal 1.3-1.6x). Null at 20.4" exceeds 15" tube. Best SWR=1.29 at full insertion. Confirmed hardware mismatch.
- **(P1) Geometric K from Bar Position**: COMPLETE. K = 1 + (bar_pos / half_element_length) × (Z0_gamma / 73). Coupling multiplier derived from two-wire line impedance, normalized to free-space dipole Z. New output fields: step_up_k_squared, ideal_bar_position_inches, ideal_step_up_ratio, coupling_multiplier. 12 new tests + 13 regression pass.
  - 2-element: ideal bar 6.5", R_feed ~29Ω
  - 3-element: ideal bar 12.6", R_feed ~20Ω → SWR 1.0 at null
  - 5-element: ideal bar 22.3", R_feed ~13Ω → SWR 1.0 at null
- **(P1) Gamma Match Designer**: COMPLETE. One-click recipe tool for any Yagi.
  - Backend: POST /api/gamma-designer — auto or custom hardware, bar/insertion sweep data, notes
  - Frontend: Full-screen modal with recipe card, SWR charts, Apply to Calculator button
  - Handles: auto hardware scaling, custom hardware analysis, null reachability check
  - **Fixed: Designer now calls apply_matching_network() internally for guaranteed consistency with calculator**
  - **Fixed: Analytical null finding (avoids 1/wC singularity in binary search)**
  - **Fixed: Frontend passes calculator's actual feedpoint R and rod dia to designer**
  - 9/9 backend + 8/8 frontend tests pass

### Session: Feb 19, 2026 (Fork 4)
- **(P0) SWR/Smith Chart Unification**: COMPLETE. SWR derives from Gamma = (Z-50)/(Z+50). 13 automated tests pass.
- **(P1) release.sh Fix**: COMPLETE. Handles pre-existing releases by deleting old assets.
- **Capacitance Precision Fix**: Internal calculation uses full float precision, display rounds to 0.1 pF. Exact null achievable (SWR 1.000, RL 80 dB).
- **Smith Chart K_eff Fix**: Removed frequency-dependent step-up degradation (K^2 is geometric constant).
- **Hardware Scaling Rule**: 6-tier auto-scaling from 2 to 20 elements using standard aluminum tubing.
- **gamma_tube_od Parameter**: Added to model and API for custom tube diameter testing.
- **Extensive Testing**: Sweeps at 1/8" and 1/32" resolution, null binary search, multi-element scaling validation. Tested custom hardware combos (2.5" tube with 3/8", 1/2", 1-3/4" rods; 1" tube with 1/2" rod).

### Session: Feb 19, 2026 (Fork 3)
- Feature Gating, Auth tier fix, Coaxial cap formula, Smith Chart transmission line stub
- Frontend fixes, release.sh creation, shorting bar default fix

### Session: Feb 2026 (Fork 2)
- Gamma match physics rewrite, Admin panel, Feature gating framework, QA

## Known Issues / Next Steps
- **Air gap in dielectric**: Real teflon sleeve doesn't fill entire tube gap. Need teflon sleeve OD for series-capacitor model
- **Tube/Rod ratio validation**: Model doesn't warn in main calculator when ratio is too large

## Backlog
- (P2) Model air gap in dielectric (teflon sleeve OD parameter)
- (P2) PayPal/CashApp Payments
- (P2) Improve .easignore
- (P3) Build iOS Version

## Build Notes
- Local build: `cd frontend && eas build --profile preview --platform android --local`
- Release: `./release.sh ./frontend/build-*.apk`
- GitHub token saved at ~/.sma_release_token on user's VM

## 3rd Party Integrations
- Stripe (Payments), Railway (Deploy), Namecheap (Domain)
- MongoDB Atlas (DB), GitHub API (Releases), Expo/EAS (Build)
