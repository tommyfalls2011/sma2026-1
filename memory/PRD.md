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

### Advanced Physics
- Gain model using lookup tables and physics-based calculations
- Polarization models: Horizontal, Vertical, 45-degree Slant (gain, noise, takeoff angle)
- Ground effects: oscillating gain with height, ground quality impact (wet/average/dry)
- Antenna efficiency based on radiation resistance and losses
- Radials up to 128 for vertical antennas (efficiency + SWR improvement)

### Admin Panel Extensions
- Discounts tab for promo code management
- Notify tab for user email notifications (Resend API)
- QR code generation for app download link

### UI/UX
- Real World / Free Space gain mode toggle
- Scrollable admin tabs for mobile
- SWR limited to 3 decimal places
- Gain breakdown display (base, height, taper, corona, boom contributions)
- Tutorial/Intro popup (admin-editable)

### Recent Changes (Dec 2025)
- Renamed "Boom Lock" to "Boom Restraint" (frontend label + backend notes)
- Removed dead "+0dB gain" from radial bonus display (was always zero, never affected by any setting)
- Radial section now shows only efficiency bonus percentage

## Key Endpoints
- POST /api/calculate - Main antenna calculation
- POST /api/auto-tune - Auto-tune element dimensions
- POST /api/optimize-height - Height optimizer
- GET/POST/DELETE /api/admin/discounts - Discount code management
- POST /api/admin/notify-users - Send update emails
- GET /api/admin/qr-code - QR code generation
- GET /api/auth/me - Current user profile
- GET /api/tutorial - Public tutorial content
- PUT /api/admin/tutorial - Admin update tutorial

## Admin Credentials
- Email: fallstommy@gmail.com / Password: admin123

## Known Limitations
- Bulk email notifications MOCKED: sends user list to admin for manual sending (Resend free tier limitation)
- Frontend changes require new APK build to be visible to end users

## Backlog
- Refactor server.py (1600+ lines) into modules (routes, models, services)
