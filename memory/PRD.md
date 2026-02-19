# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator mobile app (React Native/Expo + FastAPI + MongoDB). Features include Yagi antenna design, gamma/hairpin/direct feed matching, SWR calculation, radiation patterns, Smith chart, admin panel with subscription tiers and feature gating.

## Current Version: 4.2.3 (versionCode 11)

## Test Credentials
- **Admin**: fallstommy@gmail.com / admin123
- **Bronze Test**: test_bronze@testuser.com / test123

## Key Files
- `backend/services/physics.py` — Core physics simulation (gamma match, SWR, Smith chart)
- `frontend/app/index.tsx` — Main calculator UI (3600+ lines)
- `frontend/components/FeatureGate.tsx` — Lock overlay for gated features
- `frontend/context/AuthContext.tsx` — Auth + isFeatureAvailable()
- `frontend/app/admin.tsx` — Admin panel (20 feature toggles)
- `frontend/components/ElevationPattern.tsx` — Side view chart
- `release.sh` — Automated release script

## Physical Dimensions (User's Real Hardware)
- Outer tube: 5/8" OD, 0.049" standard wall -> 0.527" ID
- Gamma rod: 3/8" (0.375") diameter
- Teflon sleeve: 12" long over rod (er = 2.1)
- Tube length: 11"
- Rod-to-element spacing: 3.5" center-to-center
- Coaxial cap constant: 1.413 pF/inch factor -> 8.72 pF/inch for these dims
- Cap range: ~9-96 pF for 1"-11" insertion (target 20-100 pF)

## Gamma Match Physics Model (Unified)
- Z0_gamma = 276 * log10(2 * 3.5 / 0.375) ~ 351 ohms
- X_stub = Z0 * tan(beta * bar_pos) -- shorted transmission line stub
- X_cap = -1/(2*pi*f*C) -- series capacitor from rod insertion
- K^2 = 50/feedpoint_R -- step-up ratio (geometric, constant)
- Z_matched = R_feedpoint * K^2 + j(X_stub + X_cap)
- Gamma = (Z_matched - 50)/(Z_matched + 50)
- SWR = (1 + |Gamma|)/(1 - |Gamma|)
- Return Loss = -20 * log10(|Gamma|)
- At bar=13", 10" insertion (87 pF): X_stub ~ 66.8, X_cap ~ -67.1, net ~ -0.3 -> SWR ~ 1.01

## COMPLETED: SWR/Smith Chart Unification (Feb 19, 2026 - Fork 4)
- Replaced heuristic additive SWR model in apply_matching_network() with physics-based impedance
- SWR now derived from reflection coefficient using Z_matched
- Smith Chart and SWR use identical physics model (transmission line stub + series cap)
- Removed frequency-dependent k_eff degradation from Smith Chart (K^2 is geometric constant)
- Return loss section uses matching_info z_matched_r/z_matched_x directly for gamma
- All 13 automated tests pass: SWR formula, return loss formula, Smith Chart consistency

## Session History

### Session: Feb 19, 2026 (Fork 4) -- Current
- **(P0) SWR/Smith Chart Unification**: COMPLETE. Rewrote apply_matching_network gamma section with physics-based impedance model. SWR now derives from Gamma = (Z-50)/(Z+50). Smith Chart uses same model. Tested with 13 automated tests.
- **(P1) release.sh Fix**: COMPLETE. Added asset cleanup logic for pre-existing releases (deletes old APK assets before re-upload).

### Session: Feb 19, 2026 (Fork 3)
- Feature Gating with FeatureGate component
- Auth tier key mapping fix (bronze -> bronze_monthly)
- Coaxial capacitance formula correction (0.614->1.413)
- Shorting bar default fix (32"->13")
- Rod diameter fix (0.5"->0.375")
- Smith Chart transmission line stub model
- Frontend fixes (elevation height, spec sheet padding, reactance display)
- release.sh creation

### Session: Feb 2026 (Fork 2)
- Gamma match physics rewrite
- Admin panel expanded to 20 features
- Feature gating framework
- Full QA + bug fixes
- Version bumped to 4.2.3

## Backlog
- (P2) PayPal/CashApp Payments
- (P2) Improve .easignore
- (P3) Build iOS Version

## Build Notes
- Local build: `cd frontend && eas build --profile preview --platform android --local`
- Cloud fallback: `eas build --profile preview --platform android`
- Release: `./release.sh ./frontend/build-*.apk`
- GitHub token saved at ~/.sma_release_token on user's VM
