# Antenna Modeling Application - PRD

## Original Problem Statement
A full-stack antenna modeling/calculator application (React Native Expo frontend + FastAPI backend + MongoDB) for designing and analyzing Yagi-Uda antennas. The app provides physics-based calculations for gain, SWR, F/B ratio, beamwidth, and other parameters based on element dimensions and spacing.

Additionally, an e-commerce website ("Swing Master Amps") sells hand-built CB amplifiers with Stripe checkout, admin dashboard, and product management.

## Core Requirements
- Accurate antenna physics modeling (wavelength-based element placement)
- Auto-tune feature for optimal element placement
- Close/Normal/Far spacing overrides for driven element and first director
- Fine-tune nudge arrows for driven element and 1st director (25% total range)
- Feed type physics (Direct/Gamma/Hairpin) with real performance differences
- Band filtering (17m to 70cm)
- APK builds via EAS on user's VPS
- E-commerce website with Stripe payments, admin dashboard, product management

## What's Been Implemented

### Nudge Arrows + Feed Type Physics (Feb 16, 2026) - COMPLETED
- Added left/right arrow buttons under Driven Element Spacing and 1st Director Spacing
- Each press nudges element position by 2.5%, capped at ±12.5% (25% total range)
- Nudge counter shows current adjustment percentage
- Resets on auto-tune or Close/Normal/Far button change
- State: `drivenNudgeCount`, `dir1NudgeCount` in index.tsx
- Function: `nudgeElement('driven'|'dir1', direction)` in index.tsx

### Feed Type Real Physics (Feb 16, 2026) - COMPLETED
- Gamma Match: -0.15dB gain (rod loss), -0.8dB F/B (beam skew), -0.4dB F/S, +0.5deg beamwidth broadening, 97% feed efficiency, -5% bandwidth
- Hairpin Match: -0.05dB gain (minimal loss), +0.5dB F/B (symmetry bonus), +5% bandwidth, 99.5% feed efficiency
- Direct Feed: baseline (no matching loss, no bandwidth change)
- All effects applied in `services/physics.py` calculate function after bandwidth section

### Spacing Override Buttons + Physics Fix (Feb 16, 2026) - COMPLETED
- Added UI buttons for Driven Element Spacing: Close (0.12) / Normal (0.18) / Far (0.22)
- Added UI buttons for 1st Director Spacing: Close / Normal / Far
- State variables: `closeDriven`, `farDriven`, `closeDir1`, `farDir1` in index.tsx
- Fixed backend `services/physics.py` to handle spacing overrides in auto-tune and calculate

### Backend Refactoring (Feb 16, 2026) - COMPLETED
- Refactored monolithic `server.py` (4517 lines) into modular architecture
- Full regression test: 24/24 backend tests passed

### Version Update (Feb 16, 2026) - COMPLETED
- Updated app.json to v4.1.2 (versionCode 7)
- Updated /api/app-update to v4.1.2

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
│       ├── physics.py     # Antenna physics engine (modified for feed type + spacing)
│       └── email_service.py
└── frontend/
    ├── src/               # Vite/React e-commerce website
    ├── app/               # Expo/React Native antenna app (MAIN)
    │   └── index.tsx      # Main calculator UI (nudge arrows + feed type)
    ├── vite.config.js
    └── package.json
```

## Prioritized Backlog

### P0 (Critical)
- All completed

### P1 (Important)
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
