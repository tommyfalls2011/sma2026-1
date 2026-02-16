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
- **Real-time matching network tuning**: All design panel adjustments now affect SWR in real time
  - Backend `AntennaInput` accepts: `gamma_rod_dia`, `gamma_rod_spacing`, `gamma_bar_pos`, `gamma_element_gap`, `hairpin_rod_dia`, `hairpin_rod_spacing`, `hairpin_bar_pos`, `hairpin_boom_gap`
  - `apply_matching_network()` computes tuning quality from design parameters
  - Frontend sends design parameters in every `/api/calculate` call, auto-recalculates on change (300ms debounce)
  - UI shows "Tuning Quality %" in matching info section and bonus card
- **Gamma match sliders** (matching Hairpin panel style):
  - **Shorting Strap Position**: +/- buttons, 0.2–0.9 range, affects impedance step-up ratio
  - **Rod-to-Element Gap**: +/- buttons, 0.25–3.0" range, affects parasitic coupling
  - Both sliders update SWR in real time via backend
- **Updated Z0 physics** per user-provided antenna engineering formulas:
  - Gamma Z0: `276 * log10(2S/d)`, optimal ~250 ohms, rod:spacing ratio optimal at 8:1
  - Hairpin Z0: `276 * log10(2S/d)`, optimal range 200–600 ohms (HF Yagi standard)
  - Shorting bar position affects impedance transformation for both match types

## Key Architecture
- Backend: `/app/backend/services/physics.py`, `/app/backend/routes/antenna.py`, `/app/backend/models.py`
- Frontend: `/app/frontend/app/index.tsx`
- Key state: `gammaBarPos`, `gammaElementGap`, `hairpinBarPos`, `hairpinBoomGap`, `gammaRodDia`, `gammaRodSpacing`, `hairpinRodDia`, `hairpinRodSpacing`

## Prioritized Backlog
### P2
- PayPal/CashApp payments
- `.easignore` optimization for smaller APK builds
- Replace deprecated `shadow*` style props with `boxShadow`
### P3
- iOS build
