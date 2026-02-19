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
- Spacing preset buttons auto-trigger recalculation
- Tapered elements support
- Corona ball calculations
- Ground radials modeling
- Stacking analysis (V, H, 2x2 quad)
- Coax feedline loss calculations
- Performance metrics (gain, F/B, F/S, efficiency)
- Reflected power analysis
- Height optimization
- Return Loss Tune feature
- Design save/load/export (CSV, PDF) with spacing state persistence
- User authentication + subscription tiers (trial/bronze/silver/gold)
- App update checker via GitHub Gist + backend

## Completed Tasks

### Session: Feb 17, 2026
- **P1: Frontend Component Refactoring** — Extracted 11 components from monolithic index.tsx (4321→3562 lines):
  - SwrMeter, SmithChart, PolarPattern, ElevationPattern, Dropdown, ElementInput, ResultCard, SpecSection, styles, types, constants
- **P2: Vite Cleanup** — Removed all dead Vite files, src/ directory, configs, deps
- **P2: Shadow Warnings Fixed** — Replaced deprecated shadow* props with boxShadow
- **P2: ProGuard Enabled** — enableProguardInReleaseBuilds + enableShrinkResourcesInReleaseBuilds for smaller APK
- **Bug Fix: Spacing State Save/Load** — spacing_state field added to save/load flow
- **Bug Fix: Dir2/Dir1/Driven Preset Auto-Tune** — Preset buttons now trigger auto-tune via useEffect + ref pattern
- **Bug Fix: Update Banner Dismiss** — Banner dismisses when user taps Download APK
- **Build Fix: .easignore** — Removed yarn.lock from .easignore (was causing EAS build failures)
- **Build Fix: Java 17** — Documented that JDK 17 is required for local EAS builds (not JDK 21)
- **Build Fix: VM Gradle** — Disabled Gradle daemon + file system watching for VM stability

### Previous Sessions
- Backend crash fix, Series capacitor integration, Double API call fix
- Shorting bar fix, SWR display mismatch fix, Realistic gamma match physics
- 2nd Director spacing controls, Enhanced boom length tuning (5 presets)

## Pending/Backlog Tasks
- **(P2) Implement PayPal/CashApp Payments** — Currently MOCKED
- **(P3) Build iOS Version** — Requires Apple Developer Account ($99/yr)
- **(P3) Further component extraction** — GammaMatchPanel, HairpinMatchPanel, ElementSpacingControls
- **(P3) Create Release Script** — Automate post-build workflow on user's VM

## Completed Tasks (Latest)

### Session: Feb 2026 (Fork 2)
- **(P0) Gamma Rod Defaults Updated**: Spacing 3", rod length ~32" (wavelength*0.074), insertion 4" (0.125 ratio), bar position reference updated to 32"
- **(P1) Admin Panel Feature Limits Expanded**: Increased from 8 to 20 feature toggles per subscription tier. New features: Gamma Match, Hairpin Match, Smith Chart, Polar Pattern, Elevation Pattern, Dual Polarity, Coax Loss, Wind Load, PDF Export, Spacing Control, Return Loss Tune, Reflected Power
- **(P1) Feature Enforcement Wired Up**: All 20 admin-toggleable features now enforced in the main calculator UI. Buttons show "Upgrade Required" alert, sections are hidden for restricted tiers. Non-logged-in users see everything.
- **Testing**: 13/13 backend + 10/10 frontend UI tests passed

## Current Version: 4.2.2 (versionCode 10)
- Element spacing affects antenna resonant frequency (not just impedance)
- Shorting bar position: moves lowest SWR frequency up/down the band
- Gamma rod depth: changes depth of SWR dip (matching quality)
- Tuning sequence: 1) Set element spacing, 2) Adjust shorting bar for frequency, 3) Adjust rod depth for match, 4) Iterate

## Build Notes
- Local EAS builds require: JDK 17, Node 20+, yarn 1.22.x
- VM builds: use org.gradle.daemon=false and org.gradle.vfs.watch=false in ~/.gradle/gradle.properties
- After each release: update backend via curl POST /api/app-update AND update GitHub Gist

## Key API Endpoints
- POST /api/calculate — Main antenna calculation
- POST /api/auto-tune — Automatic element optimization
- POST /api/app-update — Update version info for in-app updates
- GET /api/app-update — Check latest version
- POST /api/designs/save — Save design with spacing_state
- GET /api/designs/{id} — Load design with spacing_state

## Test Credentials
- **Admin**: fallstommy@gmail.com / admin123

## Current Version: 4.2.2 (versionCode 10)
