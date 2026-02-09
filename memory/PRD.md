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
7. Detailed "View Specs" modal with boom correction section
8. CSV export feature (includes boom correction data)
9. Admin panel for managing discounts/changelog
10. Email system (welcome, password reset, receipts, announcements via Resend)
11. App update checker via GitHub Gist
12. Visual antenna element viewer (top-down SVG)
13. Boom grounded/insulated correction (G3SEK/DL6WU formula) with full physics:
    - Grounded: boom capacitance makes elements electrically longer → shorten to compensate
    - Insulated: free-space behavior, no correction needed
    - Affects: gain, SWR, F/B, impedance, bandwidth
    - Includes practical notes for each mode (safety, mechanical, tuning)

## Architecture
- **Backend**: Python/FastAPI at `/app/backend/server.py`
- **Frontend**: React Native/Expo at `/app/frontend/app/index.tsx`
- **Database**: MongoDB (users, changelog, password_resets, discounts)
- **Email**: Resend API

## Key API Endpoints
- `POST /api/calculate` - Main antenna calculation (includes boom_grounded param)
- `POST /api/auto-tune` - Auto-optimize antenna parameters
- `POST /api/optimize-height` - Find optimal antenna height
- `POST /api/optimize-stacking` - Sweep spacing for best gain
- Auth endpoints: register, login, forgot-password, reset-password, send-receipt
- `GET /api/changelog` - Changelog entries
- Admin CRUD for discounts, users, pricing

## What's Been Implemented
- All 32 items from previous sessions
- **Visual Antenna Element Viewer** (Feb 2026) - Top-down SVG with boom, elements, spacing
- **Boom Grounded/Insulated Toggle** (Feb 2026) - Complete G3SEK/DL6WU implementation:
  - Backend: boom_grounded field, boom_correction_info output with practical_notes
  - Affects gain (-0.02 to -0.3 dB), SWR (+2-10%), F/B (-0.1 to -1.5 dB), impedance, bandwidth
  - Correction scales with frequency and boom/element diameter ratio
  - Description: "Shorten elements by X" (grounded) vs "Free-space, no correction" (insulated)
  - Displayed in: results bonus cards, spec sheet section, CSV export
  - 16/16 backend tests passed

## Prioritized Backlog
### P0
- User verification of Popular Channels quick-pick
- User verification of dual-polarity checkbox logic
- User verification of Gamma/Hairpin match technical notes

### P1
- Refactor `index.tsx` into smaller components (~3100+ lines)
- EAS Build stability (pre-build script)

### P2
- Custom domain for Resend emails
