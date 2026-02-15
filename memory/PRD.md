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
- **Spacing Override Feature**: Close (0.12λ), Normal (0.18λ), Far (0.22λ) for driven element; similar for first director
- **Position-Based Gain/F/B Corrections**: Both `/api/auto-tune` and `/api/calculate` now adjust gain and F/B ratio based on ACTUAL final element positions (reflector-driven spacing in wavelengths, director spacing distribution)
- **Boom Lock Awareness**: When boom lock constrains positions identically, the gain correctly stays the same; a note is added explaining the boom is too short for the requested spacing
- **Band Filtering**: Only 17m to 70cm bands available
- **TOP VIEW SVG**: Rendering bug fixed
- **App version**: v4.1.2 (versionCode 7)

## E-commerce Website (sma-antenna.org)
- Product listings with multi-image gallery
- Admin dashboard (products, members, orders)
- Stripe payment integration with tax (7.5% NC) and shipping options
- Live at: https://sma-antenna.org

## Key Technical Architecture
- `backend/server.py`: ~4000+ lines FastAPI app (antenna + e-commerce)
- `frontend/app/index.tsx`: ~3300+ lines React Native antenna calculator
- MongoDB Atlas for persistence
- Production backend: Railway (`helpful-adaptation-production.up.railway.app`)

## Key API Endpoints
- `POST /api/calculate`: Full antenna parameter calculation (gain, SWR, F/B, beamwidth, etc.)
- `POST /api/auto-tune`: Auto-optimize element dimensions with spacing overrides
- `GET /api/bands`: Available frequency bands
- `POST /api/store/checkout`: Stripe payment for e-commerce

## Prioritized Backlog

### P0 (Critical)
- ✅ Sync updated `server.py` to Railway backend for spacing fixes

### P1 (Important)
- Improve `.easignore` file for APK build size optimization
- PayPal/CashApp payment options for e-commerce

### P2 (Technical Debt)
- Refactor `server.py` into modules (routes, physics engine, models)
- Refactor `index.tsx` into reusable components

## Bug Fixes This Session (Feb 15, 2026)
- **Spacing overrides not affecting gain** (both auto-tune and calculate):
  - Root cause: Used flat element-count lookup, ignored actual spacing
  - Fix: Position-based gain/F/B correction using actual final element positions in wavelengths
  - Added boom lock note when spacing overrides are constrained by short boom
- **Website CSS issue**: Fixed filename mismatch on Namecheap deployment
- **Mobile app source restore**: Recovered complete app source from git history
- **APK build**: Successfully built v4.1.2 from correct source folder

## URLs
- **Live Website**: https://sma-antenna.org  
- **Railway Backend**: https://helpful-adaptation-production.up.railway.app
- **GitHub Repo**: https://github.com/tommyfalls2011/sma2026-1
