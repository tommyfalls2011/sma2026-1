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
7. Detailed "View Specs" modal with boom correction and corrected cut list
8. CSV export feature (includes all correction data)
9. Admin panel for managing discounts/changelog
10. Email system (welcome, password reset, receipts, announcements via Resend)
11. App update checker via GitHub Gist
12. Visual antenna element viewer (top-down SVG)
13. 3-way boom mount selector with full physics:
    - **Bonded**: Elements welded/bolted to metal boom (100% DL6WU correction)
    - **Insulated**: Elements on metal boom with insulating sleeves (55% correction)
    - **Non-conductive**: PVC/wood/fiberglass boom (0% correction)
14. Corrected Cut List: Shows original vs corrected element lengths per mount type

## Architecture
- **Backend**: Python/FastAPI at `/app/backend/server.py`
- **Frontend**: React Native/Expo at `/app/frontend/app/index.tsx`
- **Database**: MongoDB (users, changelog, password_resets, discounts)
- **Email**: Resend API

## What's Been Implemented
- All 32 items from previous sessions
- **Visual Antenna Element Viewer** (Feb 2026) - Top-down SVG
- **3-Way Boom Mount Selector** (Feb 2026):
  - Bonded/Insulated/Non-Conductive with distinct physics
  - G3SEK/DL6WU correction formula with mount-type multiplier
  - Affects gain, SWR, F/B, impedance, bandwidth
  - Practical notes per mount type
  - Corrected Cut List showing original -> corrected lengths
  - Displayed in results cards, spec sheet, CSV export
  - Backward compatible with legacy boom_grounded parameter
  - 27/27 backend tests passed + 16/16 previous iteration

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
