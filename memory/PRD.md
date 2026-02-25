# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.8, versionCode: 27

## Completed This Session (Feb 25, 2026)

### Reset All Button — Complete Fix
- handleRefresh now resets ALL state to exact factory defaults
- Fixed: elements array was reset to [] instead of default 2-element Yagi (reflector 216" + driven 204")
- Fixed: missing boom_mount/boom_grounded in reset
- Fixed: gamma/hairpin values incorrectly reset to null instead of their defaults (gammaRodSpacing='3.5', gammaBarPos=18, etc.)
- Fixed: gainMode was set to invalid 'dBd' instead of 'realworld'
- Fixed: coaxType/coaxLengthFt didn't match initial defaults (ldf5-50a/100)
- Added: rlResult, rlTuning, fineTuning, showDebugPanel reset

### Scale Design — Full Parameter Scaling Fix
- Scale now resizes ALL parameters proportionally: element lengths, positions (spacings), taper, stacking, height
- Added: spacing override scaling (closeDriven, farDriven, closeDir1, farDir1, closeDir2, farDir2)
- Added: boom lock length scaling when enabled
- Added: hairpinBoomGap scaling
- Added: director presets/nudge counts reset on scale
- Gamma cap cleared for recalculation at new frequency

### Previous Session Completed Work
- Save/Load Bug Fixed: Gamma match and fine-tune settings persisted
- Frequency Scale Feature Implemented
- Power Advisory Implemented
- Admin Access Restored (fallstommy@gmail.com / admin123)
- New Features Gated (scale_design, fine_tune_gamma, power_advisory)
- SWR Graph Physics Fixed: Dynamic Q-factor and realistic curves
- SWR Span Control Implemented (Band, 1, 2, 5, 10, 20 MHz)
- SWR Graph Resolution Increased to 201 points
- Gamma Auto-Tune Fixed: parameter mismatch + frequency scaling

## Architecture
```
backend/
  services/physics.py   - Q-factor, gamma cap fix, bar_min scaling, SWR span
  routes/user.py        - Save/load, RL tune, auth, subscriptions
  routes/antenna.py     - Calculate, gamma designer, fine-tune
  models.py             - AntennaInput with swr_span_mhz
frontend/
  app/index.tsx         - Full reset, scale modal, power advisory, span buttons
  app/admin.tsx         - Feature locks with new features
  components/SwrMeter   - Auto-scaling Y-axis, adaptive freq labels
```

## Backlog
- P1: Auto-Tune for Direct Feed antennas (optimize element lengths/spacing for 50-ohm feedpoint)
- P2: SWR Mismatch Between Models (unify design_gamma_match vs create_smith_chart_data)
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx into smaller components
- P3: iOS version (pending user confirmation)
