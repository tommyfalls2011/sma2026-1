# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator mobile app with React Native (Expo) frontend and FastAPI backend. Features include realistic RF physics modeling, gamma/hairpin/direct feed types, coax simulation, radiation patterns, and Smith Chart.

## Architecture
- **Frontend**: React Native + Expo (app/frontend/)
- **Backend**: FastAPI + Python (app/backend/)
- **Database**: MongoDB
- **Physics Engine**: backend/services/physics.py

## Completed Features (Feb 17 2026 Session)
- **Smith Chart Backend**: 61-point impedance sweep (R, X, Γ, L, C) for all feed types — 14/14 tests passed
- **SmithChart Frontend Component**: SVG polar plot with constant-R circles, constant-X arcs, impedance trace, Lo/f0/Hi markers, readout panel (R, X, L, C)
- **Return Loss Tune Fix Verified**: Uses user's selected feed type
- **Elevation Pattern Fix Verified**: Forward lobe correctly points right
- **SVG Min-Width Guards**: All SVG components use Math.max(200, ...) to prevent negative dimensions

## Completed Features (Previous Sessions)
- Realistic Gamma Match physics (two-phase blend, <16dB poor to ~74dB excellent)
- Coax & Power Simulation (7 cable types, loss modeling)
- Editable Gamma Match inputs (null sentinel pattern)
- .easignore optimization
- Nudge arrows for element spacing
- Auto element shortening for Gamma (3%) and Hairpin (4%)
- Interactive Gamma/Hairpin panels with real-time SWR
- Multi-lobe elevation pattern
- Return Loss Tune optimizer

## Known Issues
- **P0: Expo Web SSR Hydration**: `Cannot read properties of undefined (reading 'default')` prevents useEffect from running in web preview. App works on Expo Go mobile. Root cause: Expo Router treats files in `app/context/` and `app/components/` as routes. Moving outside `app/` fixes the route warning but a deeper client-side error persists.

## Backlog
### P1
- Frontend Vite cleanup (remove index.html, vite.config.js, src/main.tsx, etc.)

### P2
- PayPal/CashApp Payments
- Improve .easignore to reduce APK build size
- Replace deprecated shadow* style props with boxShadow

### P3
- Build iOS version

## Key API Endpoints
- `POST /api/calculate` — Main calculation. Returns smith_chart_data, elevation_pattern, swr_curve, etc.
- `POST /api/auto-tune` — Auto-tune element dimensions
- `POST /api/optimize-return-loss` — Sweep spacings for best return loss

## Key Files
- `backend/services/physics.py` — Core physics engine
- `backend/models.py` — Pydantic models (AntennaOutput has smith_chart_data)
- `backend/server.py` — API routes
- `frontend/app/index.tsx` — Main UI + SmithChart component
- `frontend/app/context/AuthContext.tsx` — Auth provider
- `frontend/app/_layout.tsx` — Root layout

## Test Credentials
- Store Admin: `fallstommy@gmail.com` / `admin123`
