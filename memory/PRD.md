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
- **Critical Autotune Bug Fix**: Corrected spacing logic from boom-length-% to wavelength-based (0.18l default)
- **Spacing Override Feature**: Close (0.12l), Normal (0.18l), Far (0.22l) for driven element; similar for first director
- **Spacing-Dependent Gain/F/B**: Both `/api/auto-tune` and `/api/calculate` now properly adjust gain and F/B ratio based on element spacing distribution
- **Band Filtering**: Only 17m to 70cm bands available
- **TOP VIEW SVG**: Rendering bug fixed
- **App version**: v4.0.5 (versionCode 5)

## Key Technical Architecture
- `backend/server.py`: ~4000+ lines monolithic FastAPI app
- `frontend/app/index.tsx`: ~3300+ lines monolithic React Native screen
- MongoDB Atlas for persistence
- Resend for email notifications

## Key API Endpoints
- `POST /api/calculate`: Full antenna parameter calculation (gain, SWR, F/B, beamwidth, etc.)
- `POST /api/auto-tune`: Auto-optimize element dimensions with spacing overrides
- `GET /api/bands`: Available frequency bands

## Prioritized Backlog

### P0 (Critical)
- User verification of spacing override feature and gain changes

### P1 (Important)
- Improve `.easignore` file for APK build size optimization

### P2 (Technical Debt)
- Refactor `server.py` into modules (routes, physics engine, models)
- Refactor `index.tsx` into reusable components (TopView, SpacingControls, ElementInputs)

## Bug Fixes This Session (Feb 2026)
- **Spacing overrides not affecting gain**: `auto_tune_antenna()` predicted gain was a flat lookup by element count, ignoring spacing. Fixed by adding spacing correction factors. Also improved `calculate_antenna_parameters()` to apply a direct gain adjustment based on reflector-driven and director spacing relative to optimal wavelength fractions.
