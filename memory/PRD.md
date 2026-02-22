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
- Payment system (PayPal automated, Stripe checkout, CashApp manual)
- Admin panel (users, designs, payments, redeploy, notifications, design copy/send)
- System health monitoring
- Design save/load with full state persistence

## Architecture
- Frontend: React Native/Expo (app.json v4.2.9, versionCode 18)
- Backend: FastAPI on port 8001
- Database: MongoDB
- Deployment: Railway

## What's Been Implemented

### Session Feb 21 2026 (Latest):
- Director labeling fix (#1, #2, #3 instead of array index)
- Fixed stray `)}` rendering bug in spacing section
- Full design save/load (gamma, hairpin, coax, locks, presets, build style)
- Gold tier access fix (short tier name mapping in check_subscription_active)
- Tap-and-hold auto-repeat for gamma/hairpin +/- buttons
- Build Style Selector (Tight/Normal/Far DL6WU/Broadband) for Auto-Tune
- Position-aware impedance model (compute_feedpoint_impedance uses actual spacings, cumulative param)
- Matching Recommendation Engine (Z < 35Ω → Hairpin, 35-55Ω → Direct, >55Ω → Gamma)
- Updated Far build profile: D1 tight at 0.10λ, outer dirs graduate to 0.30-0.35λ
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
- Tight: refl=0.12λ, D1=0.08λ, incr=0.01λ — max gain, narrower bandwidth
- Normal: refl=0.18λ, D1=0.10λ, incr=0.02λ — balanced
- Far (DL6WU): refl=0.20λ, D1=0.10λ, incr=0.035λ — clean pattern, long boom
- Broadband: refl=0.18λ, D1=0.12λ, incr=0.025λ — stable, rain/snow tolerant

## Key API Endpoints
- POST /api/calculate - Main antenna calculation (includes matching_recommendation)
- POST /api/auto-tune - Auto-tune with build_style support
- POST /api/gamma-designer - Gamma match design (position-aware Z)
- POST /api/hairpin-designer - Hairpin match design (position-aware Z)
- POST /api/admin/designs/copy - Copy design between users
- GET /api/health - System health check

## DB Schema
- users: { id, email, subscription_tier, subscription_expires, is_admin }
- saved_designs: { id, user_id, name, design_data, spacing_state }
- settings: { key, value }
- pending_upgrades: { userId, tier, method, status }
- system_notifications: { message, active }

## Key Files
- backend/services/physics.py - Core physics engine, auto-tune, gamma/hairpin designers
- backend/models.py - Pydantic models (AntennaOutput has matching_recommendation)
- backend/auth.py - Auth with tier mapping fix (check_subscription_active)
- backend/routes/admin.py - Admin endpoints including designs/copy
- frontend/app/index.tsx - Main calculator UI with build style selector
- frontend/components/ElementInput.tsx - Element card with directorNum prop

## Credentials
- Admin: fallstommy@gmail.com / admin123

## P0 - Next Priority
- Auto-recurring monthly billing (Stripe + PayPal subscriptions with opt-in checkbox)

## P1 - Upcoming
- Activate Stripe with live keys once account verified

## P2 - Future
- Refactor subscription.tsx and admin.tsx into smaller components
- Series-capacitor dielectric model (air gap)
- iOS version
