# SMA Antenna Calculator - Product Requirements

## Overview
Full-stack mobile application for antenna analysis. React Native (Expo) frontend + FastAPI backend + MongoDB.

## Features Implemented

### Core
- Antenna calculation (SWR, gain, F/B, beamwidth, bandwidth, far-field pattern)
- Auto-tune for optimal element dimensions
- Optimize height for best mounting height (efficiency vs takeoff angle balanced scoring)
- Multi-band support (11m CB, 10m, 12m, 15m, 17m, 20m, 40m, 6m, 2m, 70cm)
- Save/Load designs, CSV export
- Authentication (JWT), subscription tiers (Trial/Bronze/Silver/Gold)
- Admin panel (pricing, users, designs, feature toggles, tutorial editor, discounts, notifications)

### Advanced Physics
- Gain model using lookup tables and physics-based calculations
- Polarization models: Horizontal, Vertical, 45-degree Slant, **Dual (H+V split)**
- **Dual Polarity**: N elements split N/2 H + N/2 V on shared boom, cross-coupling gain bonus, enhanced F/B from cross-pol nulling
- **Feed Match Types**: Direct Feed / Gamma Match / Hairpin Match — affects SWR and bandwidth
- Ground effects: oscillating gain with height, ground quality impact (wet/average/dry)
- Antenna efficiency based on radiation resistance and losses
- Radials up to 128 for vertical antennas (efficiency + SWR improvement)
- Height performance categories based on wavelength (Inefficient → Elite → Complex)
- Takeoff angle descriptions aligned with DX propagation terminology

### Admin Panel Extensions
- Discounts tab with create/edit/delete/toggle functionality
- Notify tab for user email notifications (Resend API)
- QR code generation for app download link

### UI/UX
- Real World / Free Space gain mode toggle
- Orientation selector: Horizontal / Vertical / 45° / Dual
- Feed Match selector: Direct / Gamma / Hairpin
- Scrollable admin tabs for mobile
- SWR limited to 3 decimal places
- Gain breakdown display with bonus cards
- Tutorial/Intro popup (admin-editable)

### Validation Benchmark
- Maco Laser 400 (12-element dual, 31ft boom, gamma match):
  - Model: 18.56 dBi gain, 39.2 dB F/B, 1.042:1 SWR
  - Spec: 17 dB gain, 40-44 dB F/B, ≤1.1:1 SWR

## Key Endpoints
- POST /api/calculate - Main antenna calculation
- POST /api/auto-tune - Auto-tune element dimensions
- POST /api/optimize-height - Height optimizer
- GET/POST/PUT/DELETE /api/admin/discounts - Discount code management
- POST /api/admin/notify-users - Send update emails
- GET /api/admin/qr-code - QR code generation

## Admin Credentials
- Email: fallstommy@gmail.com / Password: admin123

## Known Limitations
- Bulk email notifications MOCKED: sends user list to admin for manual sending (Resend free tier)
- Frontend changes require new APK build

## Backlog
- Refactor server.py (1700+ lines) into modules (routes, models, services)
