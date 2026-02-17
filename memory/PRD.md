# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Build a mobile antenna calculator app with advanced physics modeling, interactive controls, and real-time visualization for antenna design and analysis.

## Architecture
- **Frontend**: React Native (Expo) with Expo Router, deployed via EAS
- **Backend**: Python FastAPI, deployed on Railway
- **Database**: MongoDB Atlas
- **Web Preview**: Expo Web with static output mode

## Core Features (Implemented)
- Antenna element calculations with realistic physics
- Multiple feed types: Direct, Gamma, Hairpin
- SWR bandwidth chart
- Radiation pattern (polar plot)
- Multi-lobe elevation pattern
- Smith Chart (impedance tracking)
- Performance metrics (Gain, F/B, F/S, Efficiency)
- Reflected power analysis
- Resonant frequency modeling
- Auto-scaling performance bars
- Return Loss Tune (auto-tuner)
- Coax & power simulation
- Gamma/Hairpin match interactive panels
- Nudge arrows for element spacing
- Subscription tiers & login
- App update checker

## Critical Bug Fix (Feb 17, 2026)
**Root cause**: `pretty-format@30.2.0`'s ESM wrapper (`index.mjs`) had a broken default re-export chain that crashed Metro's HMR client in the web bundle with: `"Cannot read properties of undefined (reading 'default')"`. This prevented ALL client-side JavaScript from executing, blocking `useEffect` hooks, API calls, and result rendering.

**Fix applied**:
1. Patched `pretty-format/build/index.mjs` with correct ESM re-exports
2. Added persistent `postinstall` script (`scripts/patch-pretty-format.js`)
3. Moved `context/AuthContext.tsx` and `components/InstallPrompt.tsx` out of `app/` to avoid Expo Router route conflicts
4. Made native-only imports (`expo-file-system`, `expo-sharing`, `expo-constants`) lazy/conditional
5. Fixed undefined `setCalcError` reference
6. Guarded `Constants.statusBarHeight` with optional chaining

## File Structure
```
frontend/
├── app/
│   ├── _layout.tsx          # Root layout
│   ├── index.tsx            # Main calculator page
│   ├── login.tsx            # Login page
│   ├── admin.tsx            # Admin panel
│   └── subscription.tsx     # Subscription page
├── context/
│   └── AuthContext.tsx       # Auth state (moved from app/context/)
├── components/
│   ├── InstallPrompt.tsx    # PWA install prompt (moved from app/components/)
│   └── ElevationPattern.tsx # Elevation pattern chart
├── scripts/
│   └── patch-pretty-format.js  # Postinstall patch for Metro
├── metro.config.js
├── app.json
└── package.json

backend/
├── server.py               # FastAPI routes
├── models.py               # Pydantic models
└── services/
    └── physics.py           # Antenna physics engine
```

## Recent Fixes (Feb 2026)
- **Backend NameError crash**: Fixed `user_cap` and `auto_cap_pf` variables being referenced in `calculate_antenna_parameters` but only defined inside `apply_matching_network`. Computed them locally as `design_user_cap` and `design_auto_cap_pf`.
- **Series Cap (pF) integration**: The user-provided `gamma_cap_pf` value now correctly overrides the auto-calculated capacitance and impacts SWR, Smith Chart, and tuning quality. Tested with cap values of 50, 76.1 (auto), and 120 pF — all produce different SWR results as expected.

## Pending/Upcoming Tasks
### P1 - Frontend Cleanup
- Remove Vite-related files (index.html, vite.config.js, src/main.tsx)

### P2 - Improvements
- PayPal/CashApp payment integration
- Improve .easignore for APK build size
- Replace deprecated shadow* props with boxShadow
- Refactor monolithic `frontend/app/index.tsx` (1500+ lines) into smaller components

### P3 - Future
- Build iOS version

## Test Credentials
- Store Admin: `fallstommy@gmail.com` / `admin123`

## 3rd Party Integrations
- Stripe (Payments), Railway (Deploy), MongoDB Atlas (DB), GitHub API (Updates), EAS (Mobile builds)
