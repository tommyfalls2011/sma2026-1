# Swing Master Amps (SMA) - E-commerce Website

## Original Problem Statement
Build a full e-commerce website from scratch to sell custom-built CB amplifiers.

## Project URLs
- **Live Website:** https://sma-antenna.org
- **Backend API:** https://helpful-adaptation-production.up.railway.app
- **Database:** MongoDB Atlas

## Tech Stack
- **Frontend:** React, Vite, TailwindCSS
- **Backend:** FastAPI, Python
- **Database:** MongoDB Atlas
- **Payments:** Stripe (integrated), PayPal/CashApp (MOCKED)
- **Hosting:** Namecheap (frontend static), Railway (backend)

## Implemented Features ✅
- User registration, login, authentication (JWT)
- Admin dashboard (products, members, orders)
- Product listings with multi-image gallery
- Direct image upload from admin panel
- Stripe payment integration with:
  - Tax calculation (7.5% NC)
  - Shipping options (Standard $15, Priority $25, Express $45)
- Orders tab in admin dashboard
- Automatic APK download button (fetches from GitHub releases)

## Deployment Notes
**Frontend (Namecheap):**
- Files go in `public_html/`
- Structure:
  ```
  public_html/
  ├── index.html
  ├── .htaccess
  └── assets/
      ├── index-BJ9_GFt_.css
      └── index-DQXtGrjE.js
  ```
- **IMPORTANT:** Filename must match EXACTLY (including underscores)

**Backend (Railway):**
- Dockerfile uses JSON CMD format
- Removed `emergentintegrations` (not available on Railway)
- Using official `stripe` SDK instead

## Credentials
- **Admin:** fallstommy@gmail.com / admin123
- **MongoDB:** Stored in backend/.env (STORE_MONGO_URL)
- **Stripe:** Stored in backend/.env (STRIPE_API_KEY)

## Pending/Future Tasks
- [ ] PayPal payment integration
- [ ] CashApp payment integration
- [ ] Refactor codebase (separate mobile app and website)
- [ ] Break down monolithic server.py into modules
- [ ] iOS version of Antenna App
- [ ] Google Play Store submission (needs 12 testers for 14 days)

## Key Files
- `backend/server.py` - Main API server
- `frontend/src/pages/` - React pages
- `frontend/vite.config.js` - Build configuration

## Last Updated
February 15, 2026 - Fixed CSS filename mismatch issue on Namecheap deployment
