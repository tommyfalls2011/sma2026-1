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
- Payment system (PayPal automated one-time, Stripe recurring subscription, CashApp manual)
- Admin panel (users, designs, payments, redeploy, notifications, design copy/send)
- System health monitoring
- Design save/load with full state persistence

## Architecture
- Frontend: React Native/Expo (app.json v4.2.9, versionCode 18)
- Backend: FastAPI on port 8001
- Database: MongoDB
- Deployment: Railway

## What's Been Implemented

### Session Feb 22 2026 (Latest):
- **Stripe Recurring Billing**: Full subscription mode implementation
  - Stripe checkout now uses `mode='subscription'` with recurring Prices
  - Stripe Products/Prices created on server startup and cached in DB (stripe_prices collection)
  - Stripe Customers created per user (stripe_customer_id stored on user)
  - Webhook handler for `checkout.session.completed`, `invoice.paid` (auto-renewal), `customer.subscription.deleted`
  - Cancel auto-renewal (keeps sub active until period end) via `cancel_at_period_end`
  - Resume auto-renewal endpoint
  - Full cancellation clears subscription tier and Stripe subscription
  - User record tracks: auto_renew, billing_method, stripe_customer_id, stripe_subscription_id
  - Login, /auth/me, /subscription/status all return auto_renew and billing_method
- **Frontend Billing Management**:
  - Status card shows auto-renewal date or expiration date
  - Billing management section shows next billing date, billing status
  - Cancel/Resume Auto-Renewal button (only for Stripe billing users)
  - Stripe payment method label updated to "auto-recurring billing"
- **Testing**: 16/16 backend tests passed for recurring billing

### Session Feb 21 2026:
- Director labeling fix (#1, #2, #3 instead of array index)
- Fixed stray `)}` rendering bug in spacing section
- Full design save/load (gamma, hairpin, coax, locks, presets, build style)
- Gold tier access fix (short tier name mapping in check_subscription_active)
- Tap-and-hold auto-repeat for gamma/hairpin +/- buttons
- Build Style Selector (Tight/Normal/Far DL6WU/Broadband) for Auto-Tune
- Position-aware impedance model (compute_feedpoint_impedance uses actual spacings)
- Matching Recommendation Engine (Z < 35 -> Hairpin, 35-55 -> Direct, >55 -> Gamma)
- Updated Far build profile: D1 tight at 0.10L, outer dirs graduate to 0.30-0.35L
- Admin Design Copy/Send feature ($15 tune service)
- Auto-tune now sends feed_type, build_style, dir_presets to backend
- AutoTuneRequest model updated with build_style, dir_presets, dir_nudge_counts, elements, boom_mount

### Previous Sessions:
- Payment system overhaul (PayPal, Stripe, CashApp)
- Admin panel (payments, redeploy, notifications)
- System health monitor
- DB-driven config (settings collection)
- Antenna director controls (18 elements, 30% spacing presets)

## Build Style Profiles
- Tight: refl=0.12L, D1=0.08L, incr=0.01L - max gain, narrower bandwidth
- Normal: refl=0.18L, D1=0.10L, incr=0.02L - balanced
- Far (DL6WU): refl=0.20L, D1=0.10L, incr=0.035L - clean pattern, long boom
- Broadband: refl=0.18L, D1=0.12L, incr=0.025L - stable, rain/snow tolerant

## Key API Endpoints
- POST /api/calculate - Main antenna calculation (includes matching_recommendation)
- POST /api/auto-tune - Auto-tune with build_style support
- POST /api/gamma-designer - Gamma match design (position-aware Z)
- POST /api/hairpin-designer - Hairpin match design (position-aware Z)
- POST /api/subscription/stripe-checkout - Creates Stripe subscription checkout session
- GET /api/subscription/stripe-status/{session_id} - Check Stripe payment status (returns auto_renew)
- POST /api/subscription/cancel-auto-renew - Cancel auto-renewal at period end
- POST /api/subscription/resume-auto-renew - Resume auto-renewal
- POST /api/subscription/cancel - Full cancellation
- GET /api/subscription/status - Returns auto_renew, billing_method, next_billing_date
- POST /api/admin/designs/copy - Copy design between users
- GET /api/health - System health check

## DB Schema
- users: { id, email, subscription_tier, subscription_expires, auto_renew, billing_method, stripe_customer_id, stripe_subscription_id, is_admin }
- saved_designs: { id, user_id, name, design_data, spacing_state }
- settings: { key, value }
- pending_upgrades: { userId, tier, method, status }
- system_notifications: { message, active }
- stripe_prices: { type: "recurring_prices", prices: { tier_key: price_id } }
- payment_transactions: { id, session_id, user_id, tier, amount, payment_method, payment_status, billing_mode, stripe_subscription_id }

## Key Files
- backend/services/physics.py - Core physics engine, auto-tune, gamma/hairpin designers
- backend/models.py - Pydantic models (AntennaOutput has matching_recommendation)
- backend/auth.py - Auth with tier mapping fix (check_subscription_active)
- backend/routes/user.py - Subscription, Stripe recurring billing, auth endpoints
- backend/routes/admin.py - Admin endpoints including designs/copy
- backend/server.py - Stripe webhook handler (checkout.session.completed, invoice.paid, customer.subscription.deleted)
- frontend/app/index.tsx - Main calculator UI with build style selector
- frontend/app/subscription.tsx - Subscription page with billing management
- frontend/context/AuthContext.tsx - User interface with auto_renew, billing_method
- frontend/components/ElementInput.tsx - Element card with directorNum prop

## Credentials
- Admin: fallstommy@gmail.com / admin123
- Test Gold User: bronze@test.com / password123 (gold_monthly, auto_renew, stripe billing)

## P0 - Completed
- Auto-recurring monthly billing (Stripe subscriptions) - DONE
- Auto-recurring monthly billing (PayPal subscriptions) - DONE
- Fixed tier double-suffix bug (gold_monthly → gold_monthly_monthly → 3 elements) - DONE
- Added max_elements to login response - DONE
- Admin panel: monthly/yearly tier selection for users - DONE
- Stripe live key activated - DONE
- Stripe webhook configured - DONE

## P1 - Next Priority
- Set up PayPal webhook for auto-renewal notifications (IPN/webhook for PAYMENT.SALE.COMPLETED)
- Refactor subscription.tsx and admin.tsx into smaller components

## P2 - Future
- Series-capacitor dielectric model (air gap)
- iOS version
