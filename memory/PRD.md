# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app (React Native/Expo + FastAPI + MongoDB) for CB/ham radio Yagi antenna design with subscription-based features.

## Core Features
- Antenna calculation engine (2-20 elements, multiple bands)
- Gamma Match Designer with position-aware impedance model
- Hairpin Match Designer
- Auto-Tune with Build Style presets (Tight/Normal/Far/Broadband)
- Matching Recommendation Engine (Hairpin/Direct/Gamma based on Z)
- Element spacing controls with per-director presets
- Subscription tiers (Trial/Bronze/Silver/Gold/Admin)
- Payment system (PayPal automated, Stripe checkout, CashApp manual)
- Admin panel (users, designs, payments, redeploy, notifications)
- System health monitoring
- Design save/load with full state persistence

## Architecture
- Frontend: React Native/Expo (app.json v4.2.9, versionCode 18)
- Backend: FastAPI on port 8001
- Database: MongoDB
- Deployment: Railway

## What's Been Implemented

### Session Feb 21 2026:
- Director labeling fix (#1, #2, #3 instead of array index)
- Fixed stray `)}` rendering bug in spacing section
- Full design save/load (gamma, hairpin, coax, locks, presets, build style)
- Gold tier access fix (short tier name mapping in check_subscription_active)
- Tap-and-hold auto-repeat for gamma/hairpin +/- buttons
- Build Style Selector (Tight/Normal/Far/Broadband) for Auto-Tune
- Position-aware impedance model (compute_feedpoint_impedance uses actual spacings)
- Matching Recommendation Engine (Z-based: Hairpin <35R, Direct 35-55R, Gamma >55R)
- Admin Design Copy/Send feature ($15 tune service)
- Version 4.2.9 / versionCode 18

### Previous Sessions:
- Payment system overhaul (PayPal, Stripe, CashApp)
- Admin panel (payments, redeploy, notifications)
- System health monitor
- DB-driven config (settings collection)
- Antenna director controls (18 elements, 30% spacing presets)

## Key API Endpoints
- POST /api/calculate - Main antenna calculation
- POST /api/auto-tune - Auto-tune with build style support
- POST /api/gamma-designer - Gamma match design
- POST /api/hairpin-designer - Hairpin match design
- POST /api/admin/designs/copy - Copy design between users
- GET /api/health - System health check
- POST /api/auth/login - User authentication
- GET /api/subscription/status - Subscription status

## DB Schema
- users: { id, email, subscription_tier, subscription_expires, is_admin }
- saved_designs: { id, user_id, name, design_data, spacing_state }
- settings: { key, value } - API credentials
- pending_upgrades: { userId, tier, method, status }
- system_notifications: { message, active }

## Credentials
- Admin: fallstommy@gmail.com / admin123

## P0 - Next Priority
- Auto-recurring monthly billing (Stripe + PayPal subscriptions)

## P1 - Upcoming
- Activate Stripe with live keys

## P2 - Future
- Refactor subscription.tsx and admin.tsx into smaller components
- Series-capacitor dielectric model (air gap)
- iOS version
