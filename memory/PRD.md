# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
SMA Antenna Calculator is a Yagi-Uda antenna design and analysis tool for CB and Ham radio bands. It provides real-time antenna modeling including gain, SWR, beamwidth, F/B ratio, takeoff angle, stacking optimization, height optimization, and more.

The app has a React Native/Expo frontend (serving web + mobile) and a FastAPI + MongoDB backend.

## Architecture (Post-Refactoring - Feb 2026)

### Backend (~3172 lines across 10 files)
```
backend/
  server.py              (51 lines) - Slim entry: app, CORS, routers, startup/shutdown
  config.py              (125 lines) - DB, env, JWT, subscription tiers, band defs, gain tables
  models.py              (326 lines) - All Pydantic models
  auth.py                (93 lines)  - Auth helpers, JWT, user deps
  services/
    physics.py           (1398 lines) - Core antenna physics engine
    email_service.py     (38 lines)  - Email helpers via Resend
  routes/
    antenna.py           (243 lines) - Calculate, auto-tune, optimize endpoints
    user.py              (273 lines) - Auth, subscription, saved designs
    public.py            (166 lines) - Bands, status, tutorial, designer-info, changelog
    admin.py             (459 lines) - Admin pricing, users, designs, discounts, notifications
```

### Frontend (~3288 lines across 11 files)
```
frontend/app/
  index.tsx              (2769 lines) - Main AntennaCalculator screen
  types.ts               (9 lines)   - TypeScript interfaces
  constants.ts           (59 lines)  - Bands, URLs, tier colors, defaults
  styles.ts              (202 lines) - Shared StyleSheet
  components/
    ResultCard.tsx        (12 lines)  - Result display card
    SwrMeter.tsx          (38 lines)  - SWR bandwidth chart
    PolarPattern.tsx      (24 lines)  - Radiation pattern polar chart
    ElevationPattern.tsx  (72 lines)  - Side-view elevation pattern
    Dropdown.tsx          (42 lines)  - Modal dropdown selector
    ElementInput.tsx      (39 lines)  - Element dimension input card
    SpecSheet.tsx         (22 lines)  - SpecSection + SpecRow helpers
```

## What's Been Implemented
- Full Yagi-Uda antenna physics engine (gain, SWR, F/B, beamwidth, takeoff angle)
- Auto-tune with boom lock, spacing lock, close/far overrides
- Height optimization with multi-factor scoring
- Stacking optimization (vertical, horizontal, quad)
- Taper element support, corona ball calculations
- Ground radial configuration
- Dual polarity antenna support
- Wind load calculation (EIA/TIA-222)
- Boom correction (G3SEK empirical formula)
- User auth (register/login/forgot password)
- Subscription tiers (trial, bronze, silver, gold)
- Save/load antenna designs
- Admin panel (pricing, users, designs, discounts, notifications)
- CSV export of height optimizer data
- App update checker + QR code

## Key API Endpoints
- `POST /api/calculate` - Full antenna calculation
- `POST /api/auto-tune` - Optimize element dimensions
- `POST /api/optimize-height` - Find best mounting height
- `POST /api/optimize-stacking` - Find best stacking spacing
- `POST /api/auth/register` + `POST /api/auth/login` - Auth
- `GET /api/bands` - Band definitions
- `GET /api/subscription/tiers` - Pricing tiers
- Admin endpoints under `/api/admin/*`

## Completed Tasks
- [x] Physics engine overhaul (gain, F/B, beamwidth based on actual positions)
- [x] Backend refactoring: server.py 4115 → 51 lines (modular)
- [x] Frontend refactoring: index.tsx 3301 → 2769 lines (components extracted)
- [x] All 16 API endpoints tested and passing

## Backlog
- [ ] P1: Improve .easignore to reduce APK build size
- [ ] P2: Move frontend component files outside app/ to prevent expo-router warnings
- [ ] P2: Replace deprecated shadow* style props with boxShadow
- [ ] P3: Further frontend refactoring (extract more sections from main component)
