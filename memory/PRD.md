# Antenna Modeling Tool - Product Requirements Document

## Original Problem Statement
Advanced antenna modeling tool for Yagi antennas. React Native/Expo frontend + FastAPI backend + MongoDB.

## Architecture
- **Backend**: Python/FastAPI at `/app/backend/server.py`
- **Frontend**: React Native/Expo at `/app/frontend/app/index.tsx`
- **Admin**: `/app/frontend/app/admin.tsx`
- **Database**: MongoDB
- **Production**: Railway (`helpful-adaptation-production.up.railway.app`)

## What's Been Implemented

### Core Calculator
- Gain, SWR, F/B ratio, takeoff angle, impedance, bandwidth
- Multiple orientations (Horizontal, Vertical, 45-degree, Dual Polarity)
- Feed matching (Gamma, Hairpin, Direct)
- Stacking (2x, 3x, 4x linear + 2x2 Quad)
- Height optimizer, wind load, corona effects

### 3-Way Boom Mount Selector (Feb 2026)
- Bonded / Insulated / Non-conductive with G3SEK/DL6WU correction
- Corrected Cut List showing original -> corrected element lengths
- 27/27 backend tests passed

### App Update System (Feb 2026 - Fixed)
- **Root cause found**: Phone APK hits Railway which had no update endpoint
- **Fix**: Added `GET /api/app-update` (reads from MongoDB, hardcoded fallback)
- **Fix**: Added `PUT /api/app-update` (admin-only, saves to MongoDB)
- **Fix**: App now tries backend first, Gist fallback second
- **Fix**: Debug log panel shows exactly what happened during update check
- **Admin Panel**: New "Updates" tab to push updates without code changes
  - Version, Build Date (with NOW button), APK URL, Release Notes, Force Update toggle
  - One-click "Push Update to All Users"
  - How-it-works guide built in

### Other Features
- Visual antenna element viewer (top-down SVG)
- Wavelength presets, auto-recalculation
- Admin panel (pricing, users, designs, tutorial, designer, discounts, notify, changelog, updates)
- Email system via Resend (welcome, password reset, receipts)
- App update checker with Gist fallback

## Key API Endpoints
- `POST /api/calculate` - Main calculation
- `GET /api/app-update` - Get update info (public, no auth)
- `PUT /api/app-update` - Push update (admin auth required)
- Auth: register, login, forgot-password, reset-password
- Admin: discounts, users, pricing, changelog, send-update-email

## Deployment Checklist
After pushing to GitHub and deploying to Railway:
1. The `/api/app-update` endpoint will be live on Railway
2. Go to Admin Panel > Updates tab
3. Enter version, click NOW for build date, paste APK URL
4. Hit "Push Update to All Users"
5. All installed apps see the banner on next launch

## Prioritized Backlog
### P0
- Deploy to Railway (so phone update check works)
- User verification of Popular Channels, dual-polarity, Gamma/Hairpin notes

### P1
- Refactor `index.tsx` (~3100+ lines) into smaller components
- EAS Build stability (pre-build script)

### P2
- Custom domain for Resend emails
