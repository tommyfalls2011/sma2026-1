# Antenna Modeling Application - PRD

## Original Problem Statement
A full-stack antenna modeling/calculator application (React Native Expo frontend + FastAPI backend + MongoDB) for designing and analyzing Yagi-Uda antennas with e-commerce store.

## What's Been Implemented

### Earlier Sessions
- Nudge arrows for Element Spacing, Driven Element, 1st Director spacing
- Feed type physics: Gamma, Hairpin, Direct with distinct effects on gain/F/B/SWR/bandwidth
- Auto-shortening of driven element: 3% (gamma), 4% (hairpin)
- Interactive Gamma & Hairpin design panels with editable rod dia/spacing
- Custom Hairpin sliders (Shorting Bar Position & Rods-to-Boom Gap)
- Director spacing physics fix, Ground radials fix

### Current Session (Feb 2026)
- **Real-time matching network tuning**: All design panel adjustments affect SWR in real time
- **Gamma match redesigned** to model real-world components:
  - **Shorting Bar Position** slider (0.2-0.9): acts as autotransformer tap, sets resistive impedance step-up to 50 ohms
  - **Rod Insertion** slider (10%-90%): rod slides into tube (Teflon-insulated), forms variable series capacitor to cancel inductive reactance
  - Backend physics: bar position optimal depends on feedpoint R (`sqrt(50/R_feed)`), rod insertion optimal at 50% (symmetric reactance cancellation)
- **Hairpin Z0 updated**: optimal range 200-600 ohms per HF Yagi engineering standards
- **Tuning Quality %** indicator shown in matching info section and bonus card
- All 8 design parameters sent to backend on every change (300ms debounce)

## Key Architecture
- Backend: `/app/backend/services/physics.py`, `/app/backend/routes/antenna.py`, `/app/backend/models.py`
- Frontend: `/app/frontend/app/index.tsx`
- Gamma state: `gammaBarPos`, `gammaRodInsertion`, `gammaRodDia`, `gammaRodSpacing`
- Hairpin state: `hairpinBarPos`, `hairpinBoomGap`, `hairpinRodDia`, `hairpinRodSpacing`

## Prioritized Backlog
### P2
- PayPal/CashApp payments
- `.easignore` optimization for smaller APK builds
- Replace deprecated `shadow*` style props with `boxShadow`
### P3
- iOS build

## Notes
- User VM path: ~/sma2026-1
- Vite website is being removed by user (not our concern)
- Expo does NOT hot-reload in preview environment
