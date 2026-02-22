# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app (React Native/Expo + FastAPI + MongoDB) for CB/ham radio Yagi antenna design with subscription-based features.

## Core Features
- Antenna calculation engine (2-20 elements, multiple bands)
- Gamma Match Designer with position-aware impedance model
- Hairpin Match Designer
- Auto-Tune with Build Style presets (Tight/Normal/Far DL6WU/Broadband)
- Matching Recommendation Engine (Hairpin/Direct/Gamma based on Z)
- Element spacing controls with per-director presets
- Subscription tiers (Trial/Bronze/Silver/Gold/Admin)
- Payment system (PayPal recurring subscription, Stripe recurring subscription, CashApp manual)
- Admin panel (users, designs, payments, redeploy, notifications, design copy/send)
- System health monitoring
- Design save/load with full state persistence

## Architecture
- Frontend: React Native/Expo (app.json v4.3.2, versionCode 21)
- Backend: FastAPI on port 8001
- Database: MongoDB
- Deployment: Railway

## What's Been Implemented

### Session Feb 22 2026:
- **Stripe Recurring Billing**: Full subscription mode (mode='subscription')
  - Stripe Products/Prices auto-created on startup, cached in DB
  - Stripe Customers created per user
  - Webhook: checkout.session.completed, invoice.paid (auto-renewal), customer.subscription.deleted
  - Cancel/Resume auto-renewal endpoints
  - User tracks: auto_renew, billing_method, stripe_customer_id, stripe_subscription_id
- **PayPal Recurring Billing**: Full subscription mode via /v1/billing/subscriptions API
  - PayPal Products and Billing Plans auto-created on startup, cached in DB
  - Subscription return handler activates user with auto_renew=true
  - Cancel/Resume auto-renewal via PayPal suspend/activate API
- **Stripe Live Key**: sk_live_... activated, webhook whsec_... configured
- **Critical Bug Fixed**: getMaxElements double-suffix (gold_monthly → gold_monthly_monthly → 3 elements)
- **Login Response**: Now includes max_elements
- **Admin Panel**: Monthly/Yearly tier selection (gold_monthly, gold_yearly, etc.)
- **Gamma Hardware Auto-Escalation**: When standard 5/8" rod can't reach null, auto-upgrades to 3/4" then 7/8" rod. ALL element counts 2-20 now reach null.
- **Auto-Recalculate After Auto-Tune**: calculateAntenna() fires after auto-tune so gamma designer gets fresh impedance
- **Tap-and-Hold Fix**: Added onTouchEnd, onTouchCancel, onMouseUp, onMouseLeave + clearRepeat on unmount
- **Gamma Fine-Tune Endpoint**: NEW `/api/gamma-fine-tune` - optimizes reflector length, driven position, dir1 position, driven length for best gamma SWR. Backend done, has one bug fix applied (fb_ratio attribute name). NEEDS TESTING on 8, 12, 16, 20 elements.

### Previous Sessions:
- Build Style Selector (Tight/Normal/Far DL6WU/Broadband)
- Position-aware impedance model
- Matching Recommendation Engine
- Admin Design Copy/Send feature
- Full design save/load
- Gold tier access fix
- Director labeling fix
- Payment system (PayPal, Stripe, CashApp)
- Admin panel, system health monitor

## Key API Endpoints
- POST /api/calculate - Main antenna calculation
- POST /api/auto-tune - Auto-tune with build_style
- POST /api/gamma-designer - Gamma match design (auto-escalation hardware)
- POST /api/gamma-fine-tune - NEW: Optimize elements for best gamma SWR
- POST /api/hairpin-designer - Hairpin match design
- POST /api/subscription/stripe-checkout - Stripe subscription checkout
- POST /api/subscription/paypal-checkout - PayPal subscription checkout
- POST /api/subscription/cancel-auto-renew - Cancel auto-renewal
- POST /api/subscription/resume-auto-renew - Resume auto-renewal
- GET /api/subscription/status - Returns auto_renew, billing_method, next_billing_date

## DB Collections
- users: { id, email, subscription_tier, subscription_expires, auto_renew, billing_method, stripe_customer_id, stripe_subscription_id, paypal_subscription_id }
- stripe_prices: { type: "recurring_prices", prices: { tier_key: price_id } }
- paypal_plans: { type: "recurring_plans", plans: { tier_key: plan_id }, product_id }
- payment_transactions: { id, session_id, user_id, tier, amount, payment_method, payment_status, billing_mode, stripe_subscription_id, paypal_subscription_id }

## Key Files
- backend/services/physics.py - Core physics, auto-tune, gamma/hairpin designers, gamma_fine_tune
- backend/routes/user.py - Subscription, Stripe/PayPal recurring billing
- backend/routes/antenna.py - Calculation endpoints including /gamma-fine-tune
- backend/routes/admin.py - Admin endpoints with monthly/yearly tier selection
- backend/server.py - Stripe webhook handler
- backend/models.py - Pydantic models including GammaFineTuneRequest/Output
- frontend/app/index.tsx - Main calculator UI (auto-recalculate after auto-tune, tap-and-hold fix)
- frontend/app/subscription.tsx - Subscription page with billing management
- frontend/context/AuthContext.tsx - Fixed getMaxElements/isFeatureAvailable

## Credentials
- Admin: fallstommy@gmail.com / admin123
- Test User: bronze@test.com / password123

## PRIORITY TASKS FOR NEXT FORK

### P0 - Immediate
- **TEST gamma-fine-tune on 8, 12, 16, 20 elements** (bug fix applied but not tested yet)
- **Add "Fine-Tune Gamma" button to frontend** (backend endpoint exists, needs UI)

### P1 - Next
- Refactor subscription.tsx and admin.tsx into smaller components
- Set up PayPal webhook (IPN) for auto-renewal notifications

### P2 - Future
- Series-capacitor dielectric model (air gap)
- iOS version
