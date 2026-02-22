# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine. The app serves amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Core Features (Implemented)
- **Payment System**: Live auto-recurring monthly/yearly subscriptions via Stripe and PayPal. Manual CashApp option.
- **Admin Panel**: User management, tier assignment (gold_monthly/gold_yearly with 30/365 day expiry)
- **Antenna Calculator**: Position-aware impedance, Auto-Tune with Build Styles, Gamma Designer with auto-hardware escalation
- **Fine-Tune Gamma** (Feb 2026): Auto-optimization of element lengths/positions for best SWR. Uses fast analytical estimator (<0.2s for up to 20 elements).
- **Custom High-Power Hardware Support** (Feb 2026): Fixed max_insertion clamping bug in apply_matching_network. Now properly supports custom tube lengths for high-power combos (1" tube + 5/8" rod, etc.)
- **Gamma Designer → Main Page SWR Sync** (Feb 2026): Fixed tube_od/tube_length not being passed back from GammaDesigner to the main calculator. Added gamma_tube_length to AntennaInput model and full data flow.

## Architecture
```
backend/
  routes/server.py    - Stripe/PayPal recurring logic, webhooks
  routes/user.py      - Auth, subscription, designs, gamma designer
  routes/antenna.py   - Calculator, auto-tune, fine-tune, gamma/hairpin designers
  services/physics.py - Core physics engine, _fast_gamma_swr, gamma_fine_tune,
                        apply_matching_network (now accepts gamma_tube_length)
  models.py           - Pydantic models (AntennaInput now has gamma_tube_length)
frontend/
  app/index.tsx       - Main UI with Fine-Tune button, gammaTubeOd/gammaTubeLength state
  app/admin.tsx       - Admin panel
  app/subscription.tsx - Subscription management
  components/GammaDesigner.tsx - Now passes tubeOd + tubeLength back via onApply
```

## Key Bugs Fixed This Session
1. **Fine-Tune Gamma timeout**: Replaced brute-force algorithm with fast analytical estimator (~100x speedup)
2. **Max insertion clamping**: apply_matching_network clamped insertion to 2.5" regardless of custom tube length. Fixed to use gamma_tube_length parameter.
3. **Gamma Designer SWR mismatch**: GammaDesigner didn't pass tube_od/tube_length back to main calc, causing stale hardware settings and wrong SWR display.

## Current Version
app.json: 4.3.2, versionCode: 21

## Backlog
- P2: Refactor subscription.tsx and admin.tsx into smaller components
- P2: Implement more accurate series-capacitor dielectric model
- P2: Add power-aware hardware selector (auto-size tube/rod gap based on transmit power)
- P3: Build iOS version of the Antenna App
