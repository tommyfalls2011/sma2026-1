# SMA Antenna Calculator - Product Requirements

## Overview
Full-stack mobile application for antenna analysis. React Native (Expo) frontend + FastAPI backend + MongoDB.

## Features Implemented

### Core
- Antenna calculation (SWR, gain, F/B, beamwidth, bandwidth, far-field pattern)
- Auto-tune for optimal element dimensions
- Optimize height for best mounting height
- Multi-band support (11m CB, 10m, 12m, 15m, 17m, 20m, 40m, 6m, 2m, 70cm)
- Save/Load designs, CSV export
- Authentication (JWT), subscription tiers (Trial/Bronze/Silver/Gold)
- Admin panel (pricing, users, designs, feature toggles, tutorial editor)

### New Features (This Session)
1. **Gain Breakdown** - Base gain per element count, final gain with individual bonus contributions (height, boom, taper, corona, radials, reflector)
2. **Enhanced Height Optimizer** - Factors boom length, element count, ground radials, ground type for varied optimal heights
3. **Tutorial/Intro Popup** - Scrollable popup on first login, toggle to show/hide, admin-editable content

### Completed in Previous Sessions
- Advanced physics model (lookup tables, polarization: H/V/Slant, ground effects, radials up to 128)
- Admin panel: Discounts tab, Notify tab (Resend email integration)
- Real World / Free Space gain mode toggle
- Bug fixes: settings persistence, JWT logout, boom lock logic, deployment
- UI: scrollable admin tabs, SWR 3-decimal rounding
- Renamed "Boom Lock" → "Boom Restraint" (frontend label + backend notes, Dec 2025)

## Key Endpoints
- POST /api/calculate - Main antenna calculation (now includes base_gain_dbi, gain_breakdown)
- POST /api/optimize-height - Height optimizer (now accepts ground_radials, factors boom/elements)
- GET /api/tutorial - Public tutorial content
- PUT /api/admin/tutorial - Admin update tutorial content
- GET /api/admin/tutorial - Admin get tutorial with metadata

## Admin Credentials
- Email: fallstommy@gmail.com / Password: admin123
