# Antenna Modeling Application - PRD

## Original Problem Statement
A full-stack antenna modeling/calculator application (React Native Expo frontend + FastAPI backend + MongoDB) for designing and analyzing Yagi-Uda antennas.

## What's Been Implemented
- **Wavelength-based autotune** (0.18λ default reflector-driven spacing)
- **Close/Normal/Far spacing overrides** with boom-proportional placement
- **Boom length gain/F/B adjustment** (2.5 dB gain + 1.5 dB F/B per boom doubling)
- **Boom-fraction spacing corrections** for gain/F/B in both auto-tune and calculate
- **Physics-based beamwidth**: `BW_H × BW_V = 32400/G_linear`, split by antenna aspect ratio (boom/element length)
- **Band filtering** (17m to 70cm)
- **TOP VIEW SVG** rendering fix
- **App version** v4.0.5

## Key Architecture
- `backend/server.py`: ~4000+ lines monolithic FastAPI
- `frontend/app/index.tsx`: ~3300+ lines monolithic React Native
- Production backend: Railway (`helpful-adaptation-production.up.railway.app`)

## Prioritized Backlog
### P0 — User syncs updated `server.py` to Railway
### P1 — `.easignore` optimization
### P2 — Refactor server.py and index.tsx into modules

## Bug Fixes This Session (Feb 2026)
1. Spacing overrides not affecting gain (flat element-count lookup)
2. Boom lock clamping all modes to same position (wavelength-based min_director_room)
3. Same gain/F/B across different boom lengths (missing boom_adj)
4. Beamwidth not physics-based (element-count lookup → gain/aperture formula)
