# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Mobile-first antenna calculator app for ham radio/CB operators. Provides Yagi antenna design calculations including gain, SWR, radiation patterns, and matching network design (gamma match, hairpin match).

## Architecture
- **Frontend**: React Native (Expo) web + mobile app
- **Backend**: FastAPI (Python) with physics simulation engine
- **Database**: MongoDB Atlas
- **Deployment**: Railway (backend), EAS (mobile builds)
- **3rd Party**: Stripe (payments), GitHub API (app updates)

## Core Features (Implemented)
- Multi-band Yagi antenna calculator (17m through 70cm)
- Gamma match design with adjustable shorting bar + rod insertion
- Hairpin match design with adjustable parameters
- SWR bandwidth chart with usable zones
- Smith Chart impedance visualization
- Polar radiation pattern display
- Elevation pattern with take-off angle
- Element spacing controls (V.Short/Short/Normal/Long/V.Long presets)
- 1st Director spacing override + nudge controls
- 2nd Director spacing override + nudge controls
- Tapered elements support
- Corona ball calculations
- Ground radials modeling
- Stacking analysis (V, H, 2x2 quad)
- Coax feedline loss calculations
- Performance metrics (gain, F/B, F/S, efficiency)
- Reflected power analysis
- Height optimization
- Return Loss Tune feature
- Design save/load/export (CSV, PDF)
- User authentication + subscription tiers (trial/bronze/silver/gold)
- App update checker via GitHub Gist

## Completed Tasks

### Session: Feb 17, 2026
- **P1: Frontend Component Refactoring** - Extracted 11 components from monolithic index.tsx (4321→3562 lines):
  - `SwrMeter.tsx` - SWR bandwidth chart
  - `SmithChart.tsx` - Impedance visualization
  - `PolarPattern.tsx` - Radiation pattern
  - `ElevationPattern.tsx` - Elevation pattern
  - `Dropdown.tsx` - Modal dropdown selector
  - `ElementInput.tsx` - Element dimension card
  - `ResultCard.tsx` - Result display card
  - `SpecSection.tsx` + `SpecRow.tsx` - Spec sheet helpers
  - `styles.ts` - Shared StyleSheet
  - `types.ts` - TypeScript interfaces
  - `constants.ts` - BANDS, TIER_COLORS, COAX_OPTIONS
  - `index.ts` - Barrel export
- **P2: Vite Cleanup** - Removed all Vite-related files:
  - Deleted `/frontend/src/` directory (old Vite web app)
  - Deleted `index.html`, `vite.config.js`
  - Deleted `postcss.config.js`, `tailwind.config.js`
  - Removed `vite`, `@vitejs/plugin-react` from package.json
  - Removed `dev`, `build`, `preview` scripts from package.json
  - Removed `package-lock.json` (using yarn)

### Previous Sessions
- Backend crash fix (NameError in physics.py)
- Series capacitor integration
- Double API call fix
- Shorting bar functionality fix
- SWR display mismatch fix
- Realistic gamma match physics
- 2nd Director spacing controls
- Enhanced boom length tuning (5 presets)

## Pending/Backlog Tasks
- **(P2) Implement PayPal/CashApp Payments** - Currently mocked
- **(P2) Improve .easignore** - Reduce APK build size
- **(P2) Replace deprecated shadow* style props** - Use boxShadow instead
- **(P3) Build iOS Version** - iOS App Store deployment

## Key API Endpoints
- `POST /api/calculate` - Main antenna calculation
- `POST /api/auto-tune` - Automatic element optimization
- `GET /api/subscription/tiers` - Subscription tier info
- `GET /api/app-update` - Version check
- `POST /api/auth/login` - Authentication
- `POST /api/designs/save` - Save antenna design
- `GET /api/designs/list` - List saved designs

## Key Files
- `frontend/app/index.tsx` - Main calculator component (3562 lines)
- `frontend/components/` - Extracted UI components (11 files)
- `backend/services/physics.py` - Core physics simulation engine
- `backend/models.py` - Pydantic data models
- `backend/server.py` - FastAPI server with routes

## Test Credentials
- **Admin**: fallstommy@gmail.com / admin123
