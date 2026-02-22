# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine. The app serves amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Core Features (Implemented)
- **Payment System**: Live auto-recurring monthly/yearly subscriptions via Stripe and PayPal. Manual CashApp option.
- **Admin Panel**: User management, tier assignment (gold_monthly/gold_yearly with 30/365 day expiry)
- **Antenna Calculator**: Position-aware impedance, Auto-Tune with Build Styles, Gamma Designer with auto-hardware escalation
- **Fine-Tune Gamma** (NEW - Feb 2026): Automatic optimization of element lengths/positions for best SWR. Uses fast analytical estimator (~100x faster than full gamma designer sweep). Completes in <0.2s for up to 20 elements.

## Architecture
```
backend/
  routes/server.py    - Stripe/PayPal recurring logic, webhooks
  routes/user.py      - Auth, subscription, designs, gamma designer
  routes/antenna.py   - Calculator, auto-tune, fine-tune, gamma/hairpin designers
  services/physics.py - Core physics engine, _fast_gamma_swr, gamma_fine_tune
  models.py           - Pydantic models
frontend/
  app/index.tsx       - Main calculator UI with Fine-Tune Gamma button
  app/admin.tsx       - Admin panel
  app/subscription.tsx - Subscription management
  components/GammaDesigner.tsx - Gamma designer modal
```

## Key API Endpoints
- POST /api/gamma-fine-tune - Fine-tune element lengths/positions for best gamma SWR
- POST /api/gamma-designer - Full gamma match designer with auto-hardware escalation
- POST /api/auto-tune - Auto-tune antenna geometry by build style
- POST /api/calculate - Full antenna calculation
- POST /api/stripe/create-checkout-session - Stripe recurring subscription
- POST /api/paypal/create-subscription - PayPal recurring subscription

## Current Version
app.json: 4.3.2, versionCode: 21

## Completed (This Session - Feb 2026)
- Fixed Fine-Tune Gamma backend performance: replaced brute-force algorithm with fast analytical estimator
- Added Fine-Tune Gamma button to frontend UI
- All 12 backend tests passing (SWR improvement verified, <0.2s for all element counts)

## Backlog
- P2: Refactor subscription.tsx and admin.tsx into smaller components
- P2: Implement more accurate series-capacitor dielectric model
- P3: Build iOS version of the Antenna App
