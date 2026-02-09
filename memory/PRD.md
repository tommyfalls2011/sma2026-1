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

## Architecture
- **Backend**: Python/FastAPI at `/app/backend/server.py`
- **Frontend**: React Native/Expo at `/app/frontend/app/index.tsx`
- **Database**: MongoDB (users, changelog, password_resets, discounts)
- **Email**: Resend API

## Key API Endpoints
- `POST /api/calculate` - Main antenna calculation
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

## What's Been Implemented (32 items)
- [x] Renamed "Boom Lock" to "Boom Restraint"
- [x] Discount Editing in Admin Panel
- [x] Removed Hardcoded "+0dB Radial Gain"
- [x] Updated Antenna Height Performance Model & Optimizer
- [x] Added Dual Polarity & Feed Matching (Gamma/Hairpin)
- [x] Created "View Specs" UI Modal
- [x] Overhauled CSV Export
- [x] Fixed Return Loss Calculation & Efficiency Cap
- [x] Added Power Splitter Details for Stacking
- [x] Added "Dual Active" (H+V) Toggle & +3dB Gain Logic
- [x] Fixed Multiple UI Bugs & JSX Errors
- [x] Implemented Auto-Scaling UI Performance Bars
- [x] Added Wind Load Calculations
- [x] Improved Vertical Stacking Model
- [x] Removed "Capture Area (sr)" Metric
- [x] Added 2x, 3x, 4x Line Stacking
- [x] **2x2 Quad Stack Feature** (Dec 2025)
- [x] Wavelength Spacing Preset Buttons (½λ, ¾λ, 1λ)
- [x] Spacing Fine-Tune Arrows (±25% nudge)
- [x] Auto-Recalculate on Input Change (300ms debounce)
- [x] Collinear Stacking Guidance
- [x] Far-Field Pattern Analysis (V & H stacking)
- [x] Horizontal Stacking Notes
- [x] Stacking Spacing Optimizer Backend
- [x] Changelog in MongoDB + Admin Panel viewer
- [x] Impact flags (BIG/MODERATE/LIGHT)
- [x] Built-in changelog (hardcoded in APK)
- [x] Resend Email System
- [x] Password Reset Flow (Forgot Password)
- [x] Welcome Emails
- [x] Subscription Receipts
- [x] App Update System (GitHub update.json + build date comparison)

## Update System
- `APP_BUILD_DATE` in index.tsx line 15 - update before each build
- `update.json` on GitHub - update after each build with new date + APK link
- App checks GitHub on launch, shows green banner if newer build exists

## Prioritized Backlog
### P1
- Refactor `index.tsx` into smaller components (~2800+ lines)
### P2  
- Custom domain for Resend emails (currently uses onboarding@resend.dev)
