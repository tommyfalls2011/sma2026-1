# Swing Master Amps (SMA) - Product Requirements Document

## Original Problem Statement
Build a full e-commerce website to sell custom-built CB amplifiers under the brand "Swing Master Amps" (SMA).

### Core Requirements
- Product listings with detail pages
- Free member signup and login
- Admin dashboard to manage products and view members
- Shopping cart functionality
- Payments: UI placeholders for Stripe, PayPal, CashApp
- Multi-image product gallery

### Secondary Application (On Hold)
An antenna modeling calculator app (React Native) was previously built and is on hold due to Google Play Store's 12-tester policy blocking submission.

## Architecture
- **Frontend**: React + Vite + TailwindCSS at `/app/frontend/src/`
- **Backend**: FastAPI at `/app/backend/server.py`
- **Database**: MongoDB Atlas (store) + local MongoDB (antenna app)
- **Production Deployment**: Frontend on Namecheap (static), Backend on Railway

## What's Been Implemented

### E-commerce Store (Feb 2026)
- Homepage with hero section and product grid
- Product listing page with cards
- Product detail page with gallery modal (NEW - Feb 12)
- User registration and login (JWT auth)
- Shopping cart (client-side)
- Admin dashboard: manage products, view members
- Privacy policy page
- Multi-image gallery: admin can manage gallery URLs, product detail shows thumbnails + fullscreen modal with navigation

### Multi-Image Gallery Feature (Feb 12, 2026 - COMPLETE)
- **Backend**: `gallery: List[str]` field on product schema, supported in POST/PUT/GET
- **Admin**: Gallery URL input, add/remove buttons, thumbnail preview, edit loads existing gallery
- **Product Detail**: Combines main image + gallery, shows "+N MORE" button, fullscreen modal with thumbnails and arrow navigation
- **Backward compatible**: Products without gallery display correctly
- **Tested**: 9/9 backend tests passed, all frontend flows verified

### Image Upload Feature (Feb 12, 2026 - COMPLETE)
- **Backend**: POST /api/store/admin/upload accepts JPG/PNG/WEBP/GIF up to 10MB, stores with UUID filenames, serves via /api/uploads/
- **Admin**: Upload buttons for main image and gallery images, shows preview after upload, "Uploading..." state indicator
- **Auth fix**: Improved require_store_admin with proper null check and JWT exception handling
- **Tested**: 12/12 backend tests passed, all frontend upload flows verified

### Antenna Calculator App (On Hold)
- Feature-rich calculator with gain, SWR, F/B ratio, impedance, bandwidth
- Multiple orientations, feed matching, stacking patterns
- 3-way boom mount selector with DL6WU/G3SEK correction
- App update system via Railway backend
- Local build workflow on Ubuntu VM established

### APK Download Button on Homepage (Feb 13, 2026 - COMPLETE)
- **Backend**: `GET /api/store/latest-apk` checks GitHub Releases API, compares with cached version in DB, auto-updates if newer
- **Frontend**: Download section on homepage shows version, file size, and "Download APK" button linking to GitHub release
- **Auto-updating**: When you push a new release on GitHub, the website automatically picks it up
- **Tested**: 12/12 backend tests passed, all frontend elements verified

### Stripe Payment Checkout (Feb 13, 2026 - COMPLETE)
- **Backend**: `POST /api/store/checkout` creates Stripe Checkout Session with server-side price validation (6.75% NC tax + $15 shipping)
- **Backend**: `GET /api/store/checkout/status/{session_id}` polls Stripe for payment status, updates DB
- **Backend**: `POST /api/webhook/stripe` handles Stripe webhooks
- **Backend**: `GET /api/store/orders` returns user's order history
- **Frontend Cart**: "Proceed to Checkout" button creates session and redirects to Stripe's hosted checkout
- **Frontend**: `/checkout/success` page polls for status with spinner states (checking → processing → success/error)
- **Security**: Prices are always calculated server-side from DB, never from frontend
- **Payment transactions**: Stored in `payment_transactions` collection with full order details
- **Tested**: 14/14 backend, 100% frontend (iteration 12)

## Key Technical Info
- **Store Admin**: fallstommy@gmail.com / admin123
- **Store API**: `/api/store/products`, `/api/store/register`, `/api/store/login`
- **Store Admin API**: `/api/store/admin/products`, `/api/store/admin/members`
- **Product Schema**: `{id, name, price, short_desc, description, image_url, gallery: [], in_stock, specs: [], created_at}`

## Prioritized Backlog

### P0 (Completed)
- ~~Multi-image product gallery~~ DONE
- ~~Image upload from computer~~ DONE
- ~~Download APK button on homepage~~ DONE
- ~~Stripe payment checkout~~ DONE

### P1
- Implement shipping calculation (more options beyond flat rate)
- Add order management in admin dashboard

### P2
- Refactor codebase: separate React Native app and Vite website into distinct directories
- Replace placeholder product images with real photos
- Modularize backend server.py (split antenna + store routes)

### P3
- Build iOS version of antenna app (requires Apple dev account)
- Google Play Store submission (blocked by 12-tester policy)

## Known Issues
- External preview URL not working (infrastructure issue with forked environment)
- Payment/shipping on e-commerce site are UI-only (MOCKED)
- Product images are Unsplash placeholders
- Google Play Store submission blocked (12-tester/14-day policy)
