# Antenna Modeling Application - PRD

## Original Problem Statement
A full-stack antenna modeling/calculator application (React Native Expo frontend + FastAPI backend + MongoDB) for designing and analyzing Yagi-Uda antennas. The app provides physics-based calculations for gain, SWR, F/B ratio, beamwidth, and other parameters based on element dimensions and spacing.

Additionally, an e-commerce website ("Swing Master Amps") sells hand-built CB amplifiers with Stripe checkout, admin dashboard, and product management.

## Core Requirements
- Accurate antenna physics modeling (wavelength-based element placement)
- Auto-tune feature for optimal element placement
- Close/Normal/Far spacing overrides for driven element and first director
- Band filtering (17m to 70cm)
- APK builds via EAS on user's VPS
- E-commerce website with Stripe payments, admin dashboard, product management

## What's Been Implemented

### Spacing Override Buttons + Physics Fix (Feb 16, 2026) - COMPLETED
- Added UI buttons for Driven Element Spacing: Close (0.12λ) / Normal (0.18λ) / Far (0.22λ)
- Added UI buttons for 1st Director Spacing: Close / Normal / Far
- State variables: `closeDriven`, `farDriven`, `closeDir1`, `farDir1` in index.tsx (~line 355)
- Fixed backend `services/physics.py` to handle `close_dir1`/`far_dir1` in auto-tune
- Fixed `/api/calculate` to include spacing-based gain adjustments (was only adjusting F/B, not gain)
- Fixed `/api/calculate` to include director spacing adjustments (was completely missing)

### Backend Refactoring (Feb 16, 2026) - COMPLETED
- Refactored monolithic `server.py` (4517 lines) into modular architecture
- Backup at `server_monolithic_backup.py`
- Full regression test: 24/24 backend tests passed

### Frontend Fix (Feb 16, 2026) - COMPLETED
- Fixed FATAL frontend service by adding Vite dependencies and `dev` script
- Set `REACT_APP_BACKEND_URL` to preview URL

### Version Update (Feb 16, 2026) - COMPLETED
- Updated app.json to v4.1.2 (versionCode 7)
- Updated /api/app-update to v4.1.2 with correct GitHub release APK URL

## Key Technical Architecture
```
/app/
├── backend/
│   ├── server.py          # Slim entry point (~100 lines)
│   ├── config.py          # DB, constants, band definitions
│   ├── models.py          # Pydantic models
│   ├── auth.py            # JWT auth, subscription checks
│   ├── routes/
│   │   ├── antenna.py     # Calculate, auto-tune, optimize
│   │   ├── user.py        # Auth, subscription, designs
│   │   ├── admin.py       # Admin management
│   │   ├── public.py      # Public endpoints (bands, downloads)
│   │   └── store.py       # E-commerce (products, checkout)
│   └── services/
│       ├── physics.py     # Antenna physics engine (1066 lines)
│       └── email_service.py
└── frontend/
    ├── src/               # Vite/React e-commerce website
    ├── app/               # Expo/React Native antenna app (MAIN)
    │   └── index.tsx      # Main calculator UI
    ├── vite.config.js
    └── package.json
```

## Prioritized Backlog

### P0 (Critical)
- ✅ Backend refactoring completed and tested
- ✅ Frontend service fixed
- ✅ Spacing override buttons + physics calculations fixed

### P1 (Important)
- Fix original "auto-tune" feature bug (elements not moving on user's device)
- Frontend refactoring: Separate Vite (website) and Expo (mobile) into clean directories

### P2 (Nice to Have)
- Implement PayPal/CashApp payment integrations for e-commerce
- Improve `.easignore` file for APK build size optimization
- Replace deprecated `shadow*` style props with `boxShadow` in mobile app
- Build iOS version of Antenna App

## Service Configuration
- **Preview runs Expo antenna app** (supervisor service: `expo`)
- **E-commerce website** uses Vite (supervisor service: `frontend`)
- Only ONE can run on port 3000 at a time
- See `/app/memory/AGENT_NOTES.md` for detailed setup instructions

## Credentials
- **Admin/Store Admin**: fallstommy@gmail.com / admin123
