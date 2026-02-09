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

## Architecture
- **Backend**: Python/FastAPI at `/app/backend/server.py`
- **Frontend**: React Native/Expo at `/app/frontend/app/index.tsx`
- **Database**: MongoDB (for admin/discounts)

## Key API Endpoints
- `POST /api/calculate` - Main antenna calculation
- `POST /api/auto-tune` - Auto-optimize antenna parameters
- `POST /api/optimize-height` - Find optimal antenna height
- `GET /api/admin/discounts` - Fetch discounts
- `PUT /api/admin/discounts/{id}` - Update discount
- `DELETE /api/admin/discounts/{id}` - Delete discount
- `POST /api/admin/discounts` - Create discount

## What's Been Implemented
- [x] Renamed "Boom Lock" to "Boom Restraint"
- [x] Discount Editing in Admin Panel
- [x] Removed Hardcoded "+0dB Radial Gain"
- [x] Updated Antenna Height Performance Model & Optimizer
- [x] Added Dual Polarity & Feed Matching (Gamma/Hairpin)
- [x] Created "View Specs" UI Modal
- [x] Overhauled CSV Export for Readability and Completeness
- [x] Fixed Return Loss Calculation & Efficiency Cap
- [x] Added Power Splitter Details for Stacking
- [x] Added "Dual Active" (H+V) Toggle & +3dB Gain Logic
- [x] Fixed Multiple UI Bugs & JSX Errors
- [x] Implemented Auto-Scaling UI Performance Bars
- [x] Added Comprehensive Wind Load Calculation & Display
- [x] Improved Vertical Stacking Model with Detailed Guidance
- [x] Removed Confusing "Capture Area (sr)" Metric
- [x] **2x2 Quad Stack Feature** (Dec 2025) - Complete implementation with:
  - Backend: quad layout calculation (~+5-6dB gain), narrowed H+V beamwidths, quad_notes, wind load x4
  - Frontend: Layout toggle (V/H/2x2), V Spacing + H Spacing inputs, spec sheet quad section, CSV export
  - Tested: 12/12 backend tests passed, all frontend UI flows verified

## Prioritized Backlog
### P0 (Critical)
- None currently

### P1 (High)
- Refactor `index.tsx` into smaller components (file is ~2700+ lines)

### P2 (Nice to have)
- No explicit user requests pending
