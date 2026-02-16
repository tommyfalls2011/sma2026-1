# Antenna Modeling Application - PRD

## Original Problem Statement
A full-stack antenna modeling/calculator application (React Native Expo frontend + FastAPI backend + MongoDB) for designing and analyzing Yagi-Uda antennas with e-commerce store.

## What's Been Implemented

### Earlier Sessions
- Nudge arrows for Element Spacing, Driven Element, 1st Director spacing
- Feed type physics: Gamma, Hairpin, Direct with distinct effects on gain/F/B/SWR/bandwidth
- Auto-shortening of driven element: 3% (gamma), 4% (hairpin)
- Interactive Gamma & Hairpin design panels with editable rod dia/spacing
- Director spacing physics fix, Ground radials fix

### Current Session (Feb 2026)
- **Real-time matching network tuning**: All design panel adjustments affect SWR in real time
- **Gamma match redesigned** with real-world component model:
  - **Shorting Bar Position** slider: autotransformer tap along element, sets R to 50 ohm
  - **Rod Insertion (Capacitance)** slider: rod in/out of tube, variable series cap, cancels reactance
  - Components section: Rod (inner, coax center) + Tube (outer) + Teflon (PTFE, 60kV/mm)
  - Backend physics: bar optimal = sqrt(50/R_feed)*0.35, rod insertion optimal at 50%
- **Hairpin sliders**: Shorting Bar Position + Rods-to-Boom Gap (also updated to Pressable)
- **Pressable fix**: Replaced TouchableOpacity with Pressable for slider buttons — fixes web click handling in Expo Web
- **Hairpin Z0**: optimal range updated to 200-600 ohms per HF Yagi standards
- **Tuning Quality %** shown in matching info section and bonus card
- **Expo Web mode**: Preview now runs Expo web on port 3000 (not Vite)

## Key Architecture
- Backend: `/app/backend/services/physics.py`, `/app/backend/routes/antenna.py`, `/app/backend/models.py`
- Frontend: `/app/frontend/app/index.tsx`
- Frontend supervisor: `npx expo start --web --port 3000 --non-interactive`

## Prioritized Backlog
### P2
- PayPal/CashApp payments
- `.easignore` optimization for smaller APK builds
- Replace deprecated `shadow*` style props with `boxShadow`
### P3
- iOS build

## Notes
- User VM path: ~/sma2026-1
- User is removing the Vite website themselves
- Expo Web requires `Pressable` (not `TouchableOpacity`) for reliable click handling
- Metro CI mode: restart frontend after code changes
