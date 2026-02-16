# Antenna Modeling Application - PRD

## Original Problem Statement
A full-stack antenna modeling/calculator application (React Native Expo frontend + FastAPI backend + MongoDB) for designing and analyzing Yagi-Uda antennas with e-commerce store.

## What's Been Implemented

### Session Feb 16, 2026
- **Nudge arrows**: Tighter/Wider under Element Spacing, Closer/Farther under Driven Element and 1st Director spacing (2.5%/click, ±12.5% = 25% total)
- **Feed type physics**: Gamma (-0.15dB gain, -0.8 F/B, -5% BW, 97% eff), Hairpin (-0.05dB, +0.5 F/B, +5% BW, 99.5% eff), Direct (baseline)
- **Gamma Match Design panel**: Shows feedpoint R, step-up ratio, editable rod dia/spacing, calculated rod length/series cap/shorting bar
- **Hairpin Match Design panel**: Shows feedpoint R, X_L required, editable rod dia/spacing, Z0/length calc, sliders for shorting bar position & rods-to-boom gap
- **Auto-shortening**: Driven element auto-shortened 3% (gamma) or 4% (hairpin) on feed type switch + auto-tune
- **Director spacing physics fix**: 1st director position now meaningfully affects gain (was flat before)
- **Ground radials fix**: Radials no longer add antenna gain (still affect efficiency as intended)

## Key Architecture
- Backend: `/app/backend/services/physics.py` (antenna physics), `/app/backend/routes/antenna.py`
- Frontend: `/app/frontend/app/index.tsx` (main calculator UI)
- State: `drivenNudgeCount`, `dir1NudgeCount`, `spacingNudgeCount`, `hairpinBarPos`, `hairpinBoomGap`, `gammaRodDia`, `gammaRodSpacing`, `originalDrivenLength`

## Prioritized Backlog
### P1
- Frontend refactoring: Separate Vite/Expo into clean directories
### P2
- PayPal/CashApp payments, .easignore optimization, boxShadow migration, iOS build
