# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator (React/Expo frontend + FastAPI backend) for CB radio Yagi antennas. Calculates impedance, SWR, and gamma match tuning for 2-20 element Yagi antennas at 27.185 MHz.

## Core Architecture
- **Frontend**: React/Expo Web on port 3000
- **Backend**: FastAPI on port 8001
- **Database**: MongoDB (via MONGO_URL for main app, STORE_MONGO_URL for store)
- **Payments**: Stripe (automated), PayPal (automated via Orders API), CashApp (manual admin approval)
- **Deployment**: Railway (production), GitHub Releases (APK distribution)

## What's Been Implemented

### Session Feb 20 2026 — PayPal "Detail Not Found" Fix:
- Root cause: PayPal redirect went to backend URL with no handler → 404
- Added `GET /api/subscription/paypal-return` — server-side handler that captures PayPal payment and shows styled HTML success page
- Works for both mobile (APK) and web — no client-side capture needed
- **VERIFIED WORKING ON PRODUCTION** (`helpful-adaptation-production.up.railway.app`)

### Session Feb 20 2026 — Director Controls Dir1-Dir18:
- Extended individual director spacing controls from Dir1-Dir2 to Dir1-Dir18
- Each director gets V.Close/Close/Normal/Far/V.Far presets + Closer/Farther nudge
- Dynamic rendering — only shows controls for directors that exist based on element count
- Each director has unique color for identification
- Changed global spacing nudge from ±10% (0.5%/step) to ±30% (1.5%/step)

### Session Feb 20 2026 — Payment Credentials in MongoDB:
- PayPal/Stripe credentials stored in MongoDB via `payment_credentials` collection
- Backend reads from DB first, falls back to env vars
- Admin endpoints: `GET/POST /api/admin/payment-credentials`
- PayPal LIVE credentials already saved to DB

### Session Feb 20 2026 — Real PayPal Checkout Integration:
- PayPal Orders API v2 with LIVE credentials (api-m.paypal.com)
- `POST /api/subscription/paypal-checkout` — creates PayPal order, returns approval URL
- `POST /api/subscription/paypal-capture/{order_id}` — captures payment + auto-upgrades
- `GET /api/subscription/paypal-return` — handles PayPal redirect, captures, shows success page
- Frontend redirects to PayPal.com for real payment

### Session Feb 20 2026 — Payment System Fix + Stripe Integration:
- PayPal/CashApp manual upgrades create PENDING requests requiring admin approval
- Stripe Checkout for subscription payments via `emergentintegrations` library
- Admin panel "Payments" tab for approving/rejecting pending requests
- Stripe webhook handler for subscription payments

### Session Feb 20 2026 — System Status Monitor + Railway Deploy:
- `/api/health` checks API, MongoDB, and production Railway status
- System Status page at `/system-status` with green/orange/red indicators
- Status dot in main page header, auto-refreshes every 5 minutes
- Railway Remote Redeploy button in Admin Panel → Updates tab
- System Notification feature for "back online" banners

### Session Feb 20 2026 — Hairpin & Prior Work:
- Hairpin Match Designer with complex impedance + reflection coefficient physics
- Gamma Match Designer with auto-design
- E-commerce store with Stripe Checkout
- User auth, subscription tiers, admin panel
- Email system via Resend, App update system

### Session Feb 21 2026 — Dynamic Director Adjustments:
- Director spacing controls now only appear when element count >= 5 (3+ directors)
- Hides unused director adjustments — e.g., 8 elements shows exactly 6 director controls
- Added safety check: if directors.length < 3, returns null even if num_elements >= 5

## IN PROGRESS / NEXT PRIORITY

### Auto-Recurring Monthly Billing (P0 — User Requested)
- **Description**: Add auto-renew checkbox so customers can choose recurring monthly billing
- **Requirements**:
  - Checkbox/toggle on subscription page: "Auto-renew monthly"
  - **Stripe**: Use `mode="subscription"` with Stripe Checkout (recurring Price objects)
  - **PayPal**: Use PayPal Subscriptions API v1 (create Product → Plan → Subscription)
  - **CashApp**: No auto-recurring available, stays manual
  - Customers can cancel auto-renew from subscription page
- **Status**: NOT STARTED — research done, Stripe 14.3.0 + PayPal REST API ready
- **Implementation approach**:
  - Stripe: Create Checkout Session with `mode="subscription"` and inline recurring price
  - PayPal: Create Billing Plan per tier, then create Subscription on checkout
  - Store subscription IDs in `payment_transactions` for cancellation
  - Webhook handlers for `invoice.paid` (Stripe) and `BILLING.SUBSCRIPTION.*` (PayPal)

## Pending/Known Issues
- Stripe is on TEST key (`sk_test_emergent`) — user's Stripe account is being verified for live key
- Frontend initial gammaBarPos=18: Consider auto-running designer on element count change

## Prioritized Backlog
- P0: Auto-recurring monthly billing (Stripe + PayPal)
- P2: Complete Hairpin Match UI/Physics refinements (tuning instructions, Z0 natural log)
- P2: Air gap dielectric model
- P2: Improve .easignore
- P3: iOS Version

## Key Files
- `backend/routes/user.py` — Auth, subscription (upgrade, PayPal checkout/capture/return, Stripe checkout)
- `backend/routes/admin.py` — Admin panel (pricing, users, pending upgrades, payment credentials, railway deploy, system notifications)
- `backend/routes/public.py` — Health check, system notification, bands, app-update
- `backend/routes/store.py` — E-commerce store
- `backend/server.py` — FastAPI app, Stripe webhook handler
- `backend/services/physics.py` — All physics calculations
- `frontend/app/index.tsx` — Main UI (Dir1-Dir18 controls, spacing 30%)
- `frontend/app/subscription.tsx` — Subscription page (3 payment methods)
- `frontend/app/admin.tsx` — Admin panel (Payments, Updates, Railway, Notifications)
- `frontend/app/system-status.tsx` — System Status page
- `frontend/components/StatusIndicator.tsx` — Status dot + health hook

## Key API Endpoints
- `POST /api/calculate` — Main antenna calculation
- `POST /api/gamma-designer` — Auto-tune gamma
- `POST /api/hairpin-designer` — Hairpin match designer
- `POST /api/subscription/paypal-checkout` — Create PayPal order
- `GET /api/subscription/paypal-return` — Handle PayPal redirect + capture
- `POST /api/subscription/paypal-capture/{order_id}` — Manual PayPal capture
- `POST /api/subscription/stripe-checkout` — Stripe Checkout session
- `GET /api/subscription/stripe-status/{session_id}` — Check Stripe payment
- `POST /api/subscription/upgrade` — Manual upgrade (CashApp, creates pending)
- `GET /api/admin/pending-upgrades` — List pending upgrades
- `POST /api/admin/pending-upgrades/{id}/approve` — Approve upgrade
- `GET/POST /api/admin/payment-credentials` — Manage payment credentials
- `POST /api/admin/railway/redeploy` — Trigger Railway deployment
- `POST/DELETE /api/admin/system-notification` — Manage system notifications
- `GET /api/health` — System health check

## Credentials
- Store Admin: fallstommy@gmail.com / admin123
- Stripe: sk_test_emergent (test key)
- PayPal LIVE: Client ID=AUVD5nPm9yfpeWXU0e9ACFKhLeFqhGotQS4rnSCzJ0Ti744CasbNBDKzNMw_qhDYZuIJHvqRJ6fo6DAw (stored in MongoDB)
- Railway API Token: 086c1c3a-ecf2-462c-900f-8af3eedcb61a
- Railway Service ID: 68ad02fd-b6a1-407a-bf15-a6e741240be5
- Railway Env ID: 9374bfaa-4fa4-485d-ba89-f142028a5f4b
- Production URL: https://helpful-adaptation-production.up.railway.app
