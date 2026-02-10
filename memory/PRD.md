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

### App Update System (Feb 2026 - WORKING)
- App reads version from app.json via direct import + Constants fallback
- Checks Railway backend first (`/api/app-update`), Gist fallback
- Railway POST endpoint to push updates (no code deploy needed)
- Admin Panel "Updates" tab for GUI-based update pushing
- Debug log panel for troubleshooting
- tsconfig.json: resolveJsonModule: true (required for JSON imports)

### Stacking Pattern Fix (Feb 2026)
- Fixed array factor formula for vertical stacking (was not applying properly)
- Now uses proper phased array math: AF = sin(N*psi/2) / (N*sin(psi/2))

### Visual Element Viewer
- TOP VIEW label: white, 12px, bold (was gray 9px)
- Element labels bumped to 10px, spacing labels to 9px

### Package Versions Fixed
- All 22 packages synced with SDK 54 via `npx expo install --fix`
- react-native-worklets must match react-native-reanimated version
- Reanimated 4.1.1 requires Worklets 0.5.x

## Key Deployment Info
- **app.json version**: 4.0.2, versionCode: 4
- **Railway update endpoint**: POST to `/api/app-update` with JSON body
- **Gist URL**: `https://gist.githubusercontent.com/tommyfalls2011/3bb5c9e586bfa929d26da16776b0b9c6/raw/`
- **PowerShell update command**: `Invoke-RestMethod -Uri "https://helpful-adaptation-production.up.railway.app/api/app-update" -Method POST -ContentType "application/json" -Body '{"version":"X.X.X",...}'`

## Build Workflow
1. Change version in `app.json` (done by Emergent)
2. Save to GitHub from Emergent
3. On PC: `git fetch origin main && git reset --hard origin/main`
4. `Remove-Item -Recurse -Force node_modules, package-lock.json`
5. `npm install --legacy-peer-deps`
6. `eas build --profile preview --platform android`
7. Update Railway + Gist with new APK URL

## VM Local Build Setup (IN PROGRESS)
- Ubuntu 24.04 LTS installed in VirtualBox
- Node 20, default-jdk installed
- BLOCKED: Copy/paste not working (need Guest Additions)
- TODO: Android SDK, EAS CLI, first local build

## Known Issues
- Package version conflicts: Worklets version must match Reanimated expectations

## Recently Fixed (Feb 10, 2026)
- PUT /api/app-update 500 error: ObjectId serialization fix (insert_one mutates dict)
- POST /api/app-update: Same ObjectId fix applied preventively
- Spec sheet modal: Added paddingTop using Constants.statusBarHeight

## Prioritized Backlog
### P0
- Deploy latest backend to Railway (user action - sync production with these fixes)
- Complete VM local build setup (Guest Additions → Android SDK → EAS CLI)

### P1
- Refactor `index.tsx` (~3200+ lines) into smaller components
- User verification of Popular Channels, dual-polarity, Gamma/Hairpin notes

### P2
- Custom domain for Resend emails
