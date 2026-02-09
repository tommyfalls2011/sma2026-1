# Antenna Modeling Tool - Product Requirements Document

## Original Problem Statement
Advanced antenna modeling tool for Yagi antennas. Built as a React Native/Expo frontend with FastAPI backend. Supports complex physics calculations including gain, SWR, impedance, F/B ratio, takeoff angle, ground effects, dual polarization, stacking configurations, feed matching, and wind load analysis.

## Core Requirements
1. Calculate gain, SWR, F/B ratio, takeoff angle, and other performance metrics
2. Model different antenna orientations (Horizontal, Vertical, 45-degree, Dual Polarity)
3. Feed matching systems (Gamma, Hairpin)
4. Antenna stacking (2x, 3x, 4x linear arrays + 2x2 Quad)
5. Height optimizer with dynamic scoring
6. Wind load calculation and mechanical analysis
7. Detailed "View Specs" modal
8. CSV export feature
9. Admin panel for managing discounts
10. Email system (welcome, password reset, receipts, announcements)
11. App update checker via GitHub
12. Visual antenna element viewer (top-down SVG)
13. Boom grounded/insulated correction (DL6WU/G3SEK formula)

## Architecture
- **Backend**: Python/FastAPI at `/app/backend/server.py`
- **Frontend**: React Native/Expo at `/app/frontend/app/index.tsx`
- **Database**: MongoDB (users, changelog, password_resets, discounts)
- **Email**: Resend API

## Key API Endpoints
- `POST /api/calculate` - Main antenna calculation (includes boom_grounded param)
- `POST /api/auto-tune` - Auto-optimize antenna parameters
- `POST /api/optimize-height` - Find optimal antenna height
- `POST /api/optimize-stacking` - Sweep spacing 15-40ft for best gain
- `POST /api/auth/register` - User registration + welcome email
- `POST /api/auth/login` - User login
- `POST /api/auth/forgot-password` - Send reset code email
- `POST /api/auth/reset-password` - Reset password with code
- `POST /api/auth/send-receipt` - Send subscription receipt email
- `GET /api/changelog` - Get all changelog entries
- `POST /api/admin/send-update-email` - Bulk announcement emails
- Admin CRUD for discounts, users, pricing

## What's Been Implemented
- [x] All 32 items from previous sessions (see changelog)
- [x] **Visual Antenna Element Viewer** (Feb 2026) - Top-down SVG showing boom, elements, spacing labels
- [x] **Boom Grounded/Insulated Toggle** (Feb 2026) - G3SEK/DL6WU correction formula implementation
  - Backend: `boom_grounded` field in AntennaInput, `boom_correction_info` in output
  - Affects gain, SWR, F/B ratio, impedance based on boom-to-element diameter ratio
  - Correction scales with frequency (larger at VHF) and boom diameter
  - Displayed in results bonus cards, spec sheet, and CSV export
  - 16/16 backend tests passed

## Update System
- `APP_BUILD_DATE` in index.tsx line 15 - update before each build
- `update.json` on GitHub - update after each build with new date + APK link
- App checks GitHub on launch, shows green banner if newer build exists

## Prioritized Backlog
### P0
- User verification of Popular Channels quick-pick feature
- User verification of dual-polarity checkbox logic
- User verification of Gamma/Hairpin match technical notes

### P1
- Refactor `index.tsx` into smaller components (~3100+ lines)
- EAS Build stability (create reliable pre-build script)

### P2  
- Custom domain for Resend emails (currently uses onboarding@resend.dev)
