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
- Outer tube: 5/8" OD, 0.049" standard wall → 0.527" ID
- Gamma rod: 3/8" (0.375") diameter
- Teflon sleeve: 12" long over rod (εr = 2.1)
- Tube length: 11"
- Rod-to-element spacing: 3.5" center-to-center
- Coaxial cap constant: 1.413 pF/inch factor → 8.72 pF/inch for these dims
- Cap range: ~9-96 pF for 1"-11" insertion (target 20-100 pF)

## Gamma Match Physics Model
- Z0_gamma = 276 × log10(2 × 3.5 / 0.375) ≈ 351 ohms
- X_stub = Z0 × tan(β × bar_pos) — shorted transmission line stub
- X_cap = -1/(2πfC) — series capacitor from rod insertion
- Tuning: bar position adjusts R (impedance transform) + stub inductance
- Rod insertion adjusts capacitance to cancel stub inductance
- At bar=13", ~10" insertion (87 pF): stub and cap nearly cancel

## IN PROGRESS: SWR/Smith Chart Unification
Replace heuristic additive SWR model in apply_matching_network() with:
- Z_matched = R_feedpoint × K² + j(X_antenna × K + X_stub + X_cap)
- Γ = (Z_matched - 50)/(Z_matched + 50)
- SWR = (1 + |Γ|)/(1 - |Γ|)
The Smith chart section already uses this model. Need SWR to match.

### Session: Feb 19, 2026 (Fork 3)
- **(P1) Feature Enforcement with FeatureGate Component**: Created FeatureGate component, replaced 7 hide patterns with visual lock overlays
- **(P0) Critical Bug Fix: Tier Key Mapping**: Fixed isFeatureAvailable() bronze → bronze_monthly
- **(P0) Coaxial Capacitance Formula**: Fixed constant 0.614→1.413, real dimensions, geometry-based cap
- **(P0) Shorting bar default**: 32"→13" (rod×0.4)
- **(P0) Rod diameter**: 0.5"→0.375" (3/8")
- **(P1) Smith Chart**: Transmission line stub model replaces forced 50+0j
- **(P1) Frontend fixes**: Elevation height scaling, spec sheet padding, real reactance display
- **(P2) release.sh**: Automated build release workflow
- **IN PROGRESS**: SWR/Smith chart unification (code written, not yet applied)

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
- (P3) Improve release.sh (auto-detect APK path, version bump)

## Build Notes
- Local build: `cd frontend && eas build --profile preview --platform android --local`
- Cloud fallback: `eas build --profile preview --platform android`
- Release: `./release.sh ./frontend/build-*.apk`
- GitHub token saved at ~/.sma_release_token on user's VM
