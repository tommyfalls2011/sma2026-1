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

## Gamma Match Physics Model (Unified - Completed Fork 4)
- Z0_gamma = 276 * log10(2 * spacing / rod_dia)
- X_stub = Z0 * tan(beta * bar_pos) — shorted transmission line stub
- X_cap = -1/(2*pi*f*C) — series capacitor from rod insertion
- K^2 = 50/feedpoint_R — step-up ratio (geometric, constant with frequency)
- Z_matched = R_feedpoint * K^2 + j(X_stub + X_cap)
- Gamma = (Z_matched - 50)/(Z_matched + 50)
- SWR = (1 + |Gamma|)/(1 - |Gamma|)
- Return Loss = -20 * log10(|Gamma|)
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
- **Tube/Rod ratio validation**: Model doesn't warn when ratio is too large (>2x) making match impossible
- **K derived from bar position**: Currently K = sqrt(50/R) auto-computed. Should tie K to bar position geometry so different antennas need different bar positions
- **Air gap in dielectric**: Real teflon sleeve doesn't fill entire tube gap. User reported expected 76.1 pF vs model's 87.2 pF. Need teflon sleeve OD to model two-layer dielectric (teflon + air gap as series capacitors)
- **SWR curve consistency**: SWR curve uses parabolic approximation. Could derive from Smith Chart impedance at each frequency for full consistency

## Backlog
- (P1) Tie K (step-up ratio) to bar position geometry
- (P1) Model air gap in dielectric (teflon sleeve OD parameter)
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
