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

### Backend Refactoring (Feb 16, 2026) - COMPLETED
- **Refactored monolithic `server.py`** (4517 lines) into modular architecture:
  - `server.py` (~100 lines) - Slim entry point, router mounting, CORS, lifecycle
  - `config.py` (~215 lines) - DB connections, constants, band definitions, gain model
  - `models.py` (~340 lines) - All Pydantic models
  - `auth.py` (~118 lines) - JWT auth, password hashing, subscription checks
  - `routes/antenna.py` (~208 lines) - Calculate, auto-tune, optimize endpoints
  - `routes/user.py` (~227 lines) - Auth, subscription, designs, history
  - `routes/admin.py` (~356 lines) - Admin pricing, users, discounts, notifications
  - `routes/public.py` (~130 lines) - Bands, app-update, downloads, changelog
  - `routes/store.py` (~277 lines) - E-commerce: products, checkout, orders, uploads
  - `services/physics.py` (~1066 lines) - Full antenna physics engine
  - `services/email_service.py` (~52 lines) - Resend email + QR code generation
- **Full regression test**: 24/24 backend tests passed, all frontend features verified

### Frontend Fix (Feb 16, 2026) - COMPLETED
- Fixed FATAL frontend service by adding Vite dependencies and `dev` script
- Set `REACT_APP_BACKEND_URL` to preview URL
- Stopped conflicting Expo service to free port 3000 for Vite

### Previous Work
- **Critical Autotune Bug Fix**: Corrected spacing logic from boom-length-% to wavelength-based (0.18λ default)
- **Spacing Override Feature**: Close (0.12λ), Normal (0.18λ), Far (0.22λ) for driven element; similar for first director
- **Position-Based Gain/F/B Corrections**: Both `/api/auto-tune` and `/api/calculate` adjust gain/F/B based on actual element positions
- **Band Filtering**: 17m to 70cm bands
- **E-commerce Website**: Product listings, admin dashboard, Stripe checkout

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
│       ├── physics.py     # Antenna physics engine
│       └── email_service.py
└── frontend/
    ├── src/               # Vite/React e-commerce website
    ├── app/               # Expo/React Native antenna app
    ├── vite.config.js
    └── package.json
```

## Key API Endpoints
- `POST /api/calculate` - Full antenna parameter calculation
- `POST /api/auto-tune` - Auto-optimize element dimensions
- `POST /api/optimize-height` - Height optimization
- `POST /api/optimize-stacking` - Stacking optimization
- `GET /api/bands` - Available frequency bands
- `POST /api/auth/register`, `/api/auth/login` - User authentication
- `GET /api/subscription/tiers` - Subscription plans
- `GET /api/store/products` - E-commerce products
- `POST /api/store/checkout` - Stripe checkout

## Prioritized Backlog

### P0 (Critical)
- ✅ Backend refactoring completed and tested
- ✅ Frontend service fixed

### P1 (Important)
- Fix original "auto-tune" feature bug (elements not moving on user's device)
- Frontend refactoring: Separate Vite (website) and Expo (mobile) into clean directories
- PayPal/CashApp payment options for e-commerce

### P2 (Technical Debt)
- Improve `.easignore` file for APK build size optimization
- Replace deprecated `shadow*` style props with `boxShadow` in mobile app
- Build iOS version of Antenna App

## URLs
- **Live Website**: https://sma-antenna.org
- **Railway Backend**: https://helpful-adaptation-production.up.railway.app
- **GitHub Repo**: https://github.com/tommyfalls2011/sma2026-1

## Credentials
- **Admin/Store Admin**: fallstommy@gmail.com / admin123
