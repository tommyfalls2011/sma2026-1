# Antenna Modeling Application - PRD

## Original Problem Statement
A full-stack antenna modeling/calculator application (React Native Expo frontend + FastAPI backend + MongoDB) for designing and analyzing Yagi-Uda antennas. The app provides physics-based calculations for gain, SWR, F/B ratio, beamwidth, and other parameters based on element dimensions and spacing.

## Core Requirements
- Accurate antenna physics modeling (wavelength-based element placement)
- Auto-tune feature for optimal element placement
- Close/Normal/Far spacing overrides for driven element and first director
- Band filtering (17m to 70cm)
- APK builds via EAS on user's VPS

## What's Been Implemented
- **Critical Autotune Bug Fix**: Corrected spacing logic from boom-length-% to wavelength-based (0.18λ default)
- **Spacing Override Feature**: Close/Normal/Far for driven element and first director
- **Boom-Proportional Placement**: Boom lock now uses boom-fraction (12%/20%/28%) capped at wavelength ideals so Close/Normal/Far always produce different positions on any boom length
- **Boom Length Gain/F/B Adjustment**: Auto-tune predicted gain and F/B now include `2.5 * log2(boom_ratio)` and `1.5 * log2(boom_ratio)` adjustments vs standard boom — shorter boom = less gain and F/B
- **Boom-Fraction Spacing Corrections**: Both `/api/auto-tune` and `/api/calculate` adjust gain/F/B based on driven position as fraction of boom (not absolute wavelength), ensuring consistent differentiation across all boom lengths
- **Band Filtering**: Only 17m to 70cm bands available
- **TOP VIEW SVG**: Rendering bug fixed
- **App version**: v4.0.5 (versionCode 5)

## Key Technical Architecture
- `backend/server.py`: ~4000+ lines monolithic FastAPI app
- `frontend/app/index.tsx`: ~3300+ lines monolithic React Native screen
- MongoDB Atlas for persistence
- Resend for email notifications
- Production backend: Railway (`helpful-adaptation-production.up.railway.app`)

## Key API Endpoints
- `POST /api/calculate`: Full antenna parameter calculation
- `POST /api/auto-tune`: Auto-optimize element dimensions with spacing overrides
- `GET /api/bands`: Available frequency bands

## Prioritized Backlog

### P0
- User syncs updated `server.py` to Railway

### P1
- Improve `.easignore` file for APK build size optimization

### P2 (Technical Debt)
- Refactor `server.py` into modules (routes, physics engine, models)
- Refactor `index.tsx` into reusable components

## Bug Fixes This Session (Feb 2026)
1. **Spacing overrides not affecting gain**: Gain/F/B were flat element-count lookups ignoring positions
2. **Boom lock clamping all modes to same position**: `min_director_room = num_dirs × wavelength × 0.12` too aggressive on HF short booms
3. **Same gain across different boom lengths**: Auto-tune missing boom length adjustment (`boom_adj`)
4. **Same F/B across different boom lengths**: Auto-tune missing boom length F/B adjustment
