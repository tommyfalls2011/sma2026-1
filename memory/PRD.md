# SMA Antenna Calculator — PRD

## Original Problem Statement
Build a sophisticated antenna design and analysis tool with a React Native/Expo frontend and FastAPI/Python backend. The app models antenna physics including dual-polarity, feed matching networks, complex array stacking, mechanical wind load analysis, and provides detailed performance calculations.

## Architecture
- **Frontend**: React Native (Expo SDK 54) — `frontend/app/index.tsx`
- **Backend**: Python FastAPI — `backend/server.py`
- **Database**: MongoDB Atlas
- **Deployment**: APK built via `eas build --local` on Ubuntu VM

## Current Version: v4.0.5 (Feb 15, 2026)

## What's Been Implemented
- Dual polarity (H+V) with simultaneous activation (+3dB)
- Feed matching: Direct, Gamma Match, Hairpin Match
- Stacking: Line, 2x2 Quad layouts with power splitter info
- Wind load calculator
- View Specs modal, auto-scaling performance bars
- CSV export (redesigned for mobile/spreadsheet readability)
- Admin panel with discount CRUD
- TOP VIEW element layout SVG viewer
- Boom correction (G3SEK formula, bonded/insulated/nonconductive)
- Channel presets (Ch6, Ch11, Ch19, Ch28)
- Tapered elements, corona balls, ground radials
- Height optimizer
- App update system (version check against backend)
- **v4.0.5: Fixed autotune spacing (wavelength-based 0.18λ), added Close/Normal/Far spacing overrides, trimmed to 9 bands (17m-70cm)**

## Bands Supported (17m through 70cm)
17m, 15m, 12m, 11m CB, 10m, 6m, 2m, 1.25m, 70cm

## Key API Endpoints
- `POST /api/calculate` — Main antenna calculation
- `POST /api/auto-tune` — Auto-tune element arrangement
- `GET /api/export-results` — CSV export
- `GET /api/bands` — Available bands
- `PUT /api/admin/discounts/{id}` — Edit discount codes
- `GET /api/app-update` — Version check

## Credentials
- Admin Email: fallstommy@gmail.com
- Resend API Key: re_aG6DFDvh_EdZZSrGC8121N6Dh4cXbgWH2
- JWT Secret: antenna-calc-secure-jwt-secret-key-2024-production

## Backlog
- P1: .easignore optimization for smaller builds
- P2: Refactor server.py into modules (routes, services, models)
- P2: Refactor index.tsx into smaller components
- P3: Compare mode for spacing visualizations
