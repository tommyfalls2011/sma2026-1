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
- **Position-Based Gain/F/B Corrections**: Both `/api/auto-tune` and `/api/calculate` now adjust gain and F/B ratio based on ACTUAL final element positions (reflector-driven spacing in wavelengths, director spacing distribution)
- **Boom Lock Awareness**: When boom lock constrains positions identically, the gain correctly stays the same; a note is added explaining the boom is too short for the requested spacing
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
- `POST /api/calculate`: Full antenna parameter calculation (gain, SWR, F/B, beamwidth, etc.)
- `POST /api/auto-tune`: Auto-optimize element dimensions with spacing overrides
- `GET /api/bands`: Available frequency bands

## Prioritized Backlog

### P0 (Critical)
- User must sync updated `server.py` to Railway backend for spacing fixes to take effect on APK

### P1 (Important)
- Improve `.easignore` file for APK build size optimization

### P2 (Technical Debt)
- Refactor `server.py` into modules (routes, physics engine, models)
- Refactor `index.tsx` into reusable components (TopView, SpacingControls, ElementInputs)

## Bug Fixes This Session (Feb 2026)
- **Spacing overrides not affecting gain** (both auto-tune and calculate):
  - Root cause: `auto_tune_antenna()` used flat element-count lookup; `calculate_antenna_parameters()` had spacing_efficiency but only in percentage, not dBi
  - Fix: Position-based gain/F/B correction using actual final element positions in wavelengths, applied in both endpoints
  - Added boom lock note when spacing overrides are constrained by short boom
