# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator (React/Expo frontend + FastAPI backend) for CB radio Yagi antennas. Calculates impedance, SWR, and gamma match tuning for 2-20 element Yagi antennas at 27.185 MHz.

## Core Architecture
- **Frontend**: React/Expo Web on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB (via MONGO_URL for main app, STORE_MONGO_URL for store)
- **Payments**: Stripe (automated), PayPal & CashApp (manual with admin approval)

## Current Hardware Defaults (Feb 2026)

### Per-Element Hardware Sizing:
| Elements | Rod OD | Tube OD | Tube Len | Teflon | Max Ins | Rod Length | SWR |
|----------|--------|---------|----------|--------|---------|------------|------|
| 2        | 0.875" (7/8") | 1.0" | 4.0" | 5.0" | 3.5" | 22" | 1.032 |
| 3        | 0.750" (3/4") | 0.875" (7/8") | 3.5" | 4.5" | 3.0" | 22" | 1.001 |
| 4-6      | 0.625" (5/8") | 0.750" (3/4") | 3.0" | 4.0" | 2.5" | 22" | 1.008 |
| 7+       | 0.625" (5/8") | 0.750" (3/4") | 3.0" | 4.0" | 2.5" | 30" | ≤1.005 |

Common: Wall=0.049", Rod spacing=3.5"

## What's Been Implemented

### Session Feb 20 2026 — System Status Monitor + Railway Remote Redeploy:
- Added `/api/health` endpoint that checks API server, MongoDB, and production Railway app status with latency
- Created System Status page (`/system-status`) showing all services with green/orange/red indicators
- Added status dot in the main page header — green when all systems operational, orange for degraded, red when down
- Auto-refreshes every 5 minutes
- Added **Railway Remote Redeploy** button in Admin Panel → Updates tab
  - `POST /api/admin/railway/redeploy` — triggers fresh deployment via Railway GraphQL API
  - `GET /api/admin/railway/status` — shows latest deployment status
  - Confirmation dialog before triggering, with success/error feedback
- Added **System Notification** feature for "back online" in-app banners
  - Admin Panel → Updates tab → "Send to All Users" button with custom message
  - Users see a green dismissible banner at the top of the main page when they open the app
  - `POST /api/admin/system-notification` — create notification
  - `DELETE /api/admin/system-notification` — clear notification
  - `GET /api/system-notification` — public endpoint for users to check

### Session Feb 20 2026 — Payment System Fix + Stripe Integration:
- **CRITICAL FIX**: PayPal/CashApp upgrades now create PENDING requests requiring admin approval (was instantly upgrading without payment verification)
- Added Stripe Checkout for subscription payments via `emergentintegrations` library — instant upgrade on successful payment
- New backend endpoints:
  - `POST /api/subscription/upgrade` — Creates pending request (PayPal/CashApp)
  - `GET /api/subscription/pending` — User checks their pending request
  - `POST /api/subscription/stripe-checkout` — Creates Stripe Checkout session
  - `GET /api/subscription/stripe-status/{session_id}` — Polls Stripe payment status + auto-upgrades
  - `GET /api/admin/pending-upgrades` — Admin lists all pending upgrade requests
  - `POST /api/admin/pending-upgrades/{id}/approve` — Admin approves (upgrades user)
  - `POST /api/admin/pending-upgrades/{id}/reject` — Admin rejects
- Frontend subscription page now shows 3 payment methods: Stripe (Credit/Debit), PayPal, CashApp
- Admin panel has new "Payments" tab for reviewing/approving/rejecting upgrade requests
- Stripe webhook handler updated to handle subscription payments
- All 11 backend tests passed (100% success rate)

### Session Feb 20 2026 — Hairpin Physics Finalization:
- Switched Z0 formula to natural log form: `Z_hp = 120 * ln(2s/d)` per user's physics reference
- Added tuning_instructions block to both /api/calculate and /api/hairpin-designer responses

### Session Feb 20 2026 — Hairpin Match Designer + Reflection Coefficient Physics:
- Built full Hairpin Match Designer modal
- Upgraded SWR to use complex impedance + reflection coefficient
- New endpoint: POST /api/hairpin-designer

### Session Feb 20 2026 — Spacing Preset Bug Fix:
- Fixed element spacing preset buttons resetting ALL element positions

### Session Feb 20 2026 — Rod/Tube Mismatch Bug Fix:
- Fixed frontend GammaDesigner sending stale custom_rod_od

### Prior Session Work:
- Physics Unification, Driven Element Correction, Frontend 0.01" step controls
- E-commerce store with Stripe Checkout for amplifier products
- User auth, subscription tiers, admin panel
- Email system via Resend
- App update system

## Pending/Known Issues
- Frontend initial gammaBarPos=18: Consider auto-running designer on element count change

## Prioritized Backlog
- P2: Complete Hairpin Match UI/Physics Refinements (tuning instructions display, Z0 natural log)
- P2: Air gap dielectric model
- P2: Improve .easignore
- P3: iOS Version

## Key Files
- `frontend/app/system-status.tsx` — System Status page
- `frontend/components/StatusIndicator.tsx` — Status dot component + health hook
- `backend/routes/user.py` — Auth, subscription (upgrade, Stripe checkout, pending)
- `backend/routes/admin.py` — Admin panel (pricing, users, pending upgrades, designs)
- `backend/routes/store.py` — E-commerce store (products, orders, Stripe store checkout)
- `backend/server.py` — FastAPI app, Stripe webhook handler
- `backend/services/physics.py` — All physics (shared helpers + main functions)
- `frontend/app/index.tsx` — Main UI
- `frontend/app/subscription.tsx` — Subscription page (3 payment methods)
- `frontend/app/admin.tsx` — Admin panel (with Payments tab)
- `frontend/components/GammaDesigner.tsx` — Gamma match designer
- `frontend/components/HairpinDesigner.tsx` — Hairpin match designer

## Key API Endpoints
- `POST /api/calculate` — Main antenna calculation
- `POST /api/gamma-designer` — Auto-tune gamma designer
- `POST /api/hairpin-designer` — Hairpin match designer
- `POST /api/subscription/upgrade` — Submit upgrade request (pending for PayPal/CashApp)
- `POST /api/subscription/stripe-checkout` — Start Stripe Checkout session
- `GET /api/subscription/stripe-status/{session_id}` — Check Stripe payment
- `GET /api/admin/pending-upgrades` — List pending upgrade requests
- `POST /api/admin/pending-upgrades/{id}/approve` — Approve upgrade
- `POST /api/admin/pending-upgrades/{id}/reject` — Reject upgrade

## Credentials
- Store Admin: fallstommy@gmail.com / admin123
- Stripe: sk_test_emergent (test key from environment)
- PayPal: tfcp2011@gmail.com
- CashApp: $tfcp2011
