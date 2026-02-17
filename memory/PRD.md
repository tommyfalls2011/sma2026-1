# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Professional antenna design and analysis tool for ham radio operators. Calculate SWR, gain, radiation patterns, and optimize antenna configurations. Mobile-first app built with React Native (Expo) + FastAPI backend.

## Current Version: 4.1.5 (versionCode 8)

## Architecture
- **Frontend**: React Native (Expo), Expo Web for preview
- **Backend**: FastAPI (Python), MongoDB
- **Physics Engine**: `backend/services/physics.py` — models SWR, gain, F/B ratio, resonant frequency, Q-factor, complex impedance, return loss
- **Deployment**: EAS Build for Android APK, Railway for backend

## Completed Features (This Session - Feb 17 2026)
- **Smith Chart**: Full impedance sweep visualization across 61 frequency points
  - Plots normalized impedance on standard Smith Chart grid (constant R circles, constant X arcs)
  - Tracks R (resistance), X (reactance), L (inductance), C (capacitance)
  - Shows reflection coefficient Γ for each frequency point
  - Band edge markers (Lo/Hi) and center frequency marker (f0)
  - Works with all feed types: Direct, Gamma, Hairpin
- **P0 Bug Fix Verified**: Return Loss Tune now correctly uses user's selected feed type (gamma/hairpin/direct)
- **P0 Bug Fix Verified**: Elevation pattern lobes now correctly oriented (forward = right)
- **SVG Width Fix**: All SVG components now use minimum widths to prevent negative dimension errors on Expo Web

## Completed Features (Previous Session)
- **v4.1.5 applied** across all config files and database
- **SWR curve shifts with resonant frequency** — SWR dip moves based on gamma/hairpin match tuning, centered on operating freq
- **Resonant frequency marker** on SWR chart (orange "RES" line when shifted)
- **Spacing-dependent resonant frequency** — element resonant freq changes with mutual coupling (closer=lower freq, wider=higher freq per HF physics)
- **Spacing-dependent feedpoint impedance** — closer elements = stronger coupling = lower impedance (exponential decay model)
- **5 spacing presets** for Driven Element (V.Close 0.08λ, Close 0.12λ, Normal 0.18λ, Far 0.22λ, V.Far 0.28λ)
- **5 spacing presets** for 1st Director (V.Close, Close, Normal, Far, V.Far)
- **Smooth nudge controls** — 0.5% per click, ±45% max range (90 clicks each direction)
- **Full elevation pattern** — polar plot showing ALL lobes (multiple ground-reflection lobes), front AND back with F/B attenuation
- **Return Loss Tune** button — sweeps driven & director spacings to find best natural impedance match
- **Complex impedance return loss** — Γ = (Z_ant - Z_0)/(Z_ant + Z_0) with R+jX, RL = -20log10(|Γ|)
- **Consistent SWR/RL/Γ** — all derived from single complex impedance calculation
- **Gamma match tuning-quality-dependent model** — two-phase impedance blend (linear + exponential refinement) with realistic penalty system; achieves 74 dB RL at perfect tuning, drops below 16 dB at extreme detuning
- **Coax feedline settings** — Default: LDF5-50A 7/8" Heliax, 100ft, 500W TX. User can select from 6 cable types with real loss data. Live coax loss + SWR loss calculation, power-at-antenna display.
- **Optimized .easignore** — Excludes Vite files, dev configs, IDE files, test artifacts, lock files, backend code from APK build for smaller binary size.
- **Larger frequency text** under SWR meter (fontSize 13, bold)

## Previously Completed Features
- Antenna calculator with element spacing, dimensions, frequency input
- Real-time SWR/Frequency tuning (Gamma & Hairpin match panels)
- Interactive Gamma Match sliders (Shorting Bar, Rod Insertion)
- Realistic Gamma Match physics model
- Auto-scaling performance bars
- Resonant Frequency UI card
- Updated gain curve (+2.8 dB first director jump)
- 2x2 Quad Stacking, Wavelength Spacing Presets
- Far-Field Pattern Analysis, Wind Load Calculations
- 3-Way Boom Mount Selector, Visual Element Viewer
- Store with Stripe payments, Admin panel
- Update system with version checking

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
- `backend/services/physics.py` — All antenna calculation logic (complex impedance, return loss, resonant freq)
- `backend/routes/antenna.py` — API routes including optimize-return-loss endpoint
- `backend/models.py` — Pydantic models (AntennaOutput, AutoTuneRequest with Union[str,bool] spacing fields)
- `frontend/app/index.tsx` — Main UI and state management
- `frontend/app.json` — Expo config (version 4.1.5, versionCode 8)

## Key API Endpoints
- `POST /api/calculate` — Main calculation (accepts gamma_bar_pos, gamma_rod_insertion)
- `POST /api/auto-tune` — Auto-tune element dimensions
- `POST /api/optimize-return-loss` — Sweep spacings for best return loss

## Test Credentials
- Store Admin: `fallstommy@gmail.com` / `admin123`
