# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Professional antenna design and analysis tool for ham radio operators. Calculate SWR, gain, radiation patterns, and optimize antenna configurations. Mobile-first app built with React Native (Expo) + FastAPI backend.

## Current Version: 4.1.5 (versionCode 8)

## Architecture
- **Frontend**: React Native (Expo), Expo Web for preview
- **Backend**: FastAPI (Python), MongoDB
- **Physics Engine**: `backend/services/physics.py` — models SWR, gain, F/B ratio, resonant frequency, Q-factor
- **Deployment**: EAS Build for Android APK, Railway for backend

## Completed Features
- Antenna calculator with element spacing, dimensions, frequency input
- Real-time SWR/Frequency tuning (Gamma & Hairpin match panels)
- Interactive Gamma Match sliders (Shorting Bar, Rod Insertion)
- Realistic Gamma Match physics model
- Auto-scaling performance bars
- Resonant Frequency UI card (element resonance, match-tuned resonance, Q-Factor/Bandwidth)
- Updated gain curve (+2.8 dB first director jump)
- 2x2 Quad Stacking, Wavelength Spacing Presets
- Far-Field Pattern Analysis, Wind Load Calculations
- 3-Way Boom Mount Selector, Visual Element Viewer
- Store with Stripe payments, Admin panel
- Update system with version checking
- Expo Web preview environment configured
- v4.1.5 version applied across all config files and database

## Pending Tasks
### P1
- Frontend Vite cleanup (remove `index.html`, `vite.config.js`, `src/main.tsx`, etc.)

### P2
- PayPal/CashApp Payments
- Improve `.easignore` to reduce APK build size
- Replace deprecated `shadow*` style props with `boxShadow`

### P3
- Build iOS version

## Key Files
- `backend/services/physics.py` — All antenna calculation logic
- `frontend/app/index.tsx` — Main UI and state management
- `frontend/app.json` — Expo config (version 4.1.5, versionCode 8)
- `frontend/update.json` — Update system config
- `backend/routes/public.py` — Public API including app-update endpoint

## Test Credentials
- Store Admin: `fallstommy@gmail.com` / `admin123`
