# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.8, versionCode: 27

## Completed This Session (Feb 25, 2026)

### Reset All Button — Complete Fix
- handleRefresh now resets ALL state to exact factory defaults
- Fixed: elements array, gamma/hairpin defaults, gainMode, coaxType, boom_mount, UI state

### Scale Design — Full Parameter Scaling + Proportional Method
- Scale now resizes ALL parameters: spacings, overrides, boom lock, hairpin, director presets
- NEW: Added "% Proportional" scaling method (default) alongside "Freq Ratio"
  - Proportional: computes ideal driven length at target freq using diameter-adjusted shortening factor (0.935 - 0.5 * dia/wavelength), then scales all elements by their % ratio to driven
  - Matches reference designs within 0.01 dBi for any source frequency
  - Ratio: traditional frequency ratio multiplication (preserved for exact electrical geometry preservation)
- Method toggle UI in Scale modal with live preview for both methods
- Quick-pick frequency buttons (CB 27, 10m, 6m, 2m)

### Previous Session Completed Work
- Save/Load Bug Fixed, Frequency Scale Feature, Power Advisory
- Admin Access Restored, New Features Gated
- SWR Graph Physics Fixed (dynamic Q-factor), SWR Span Control, 201 points
- Gamma Auto-Tune Fixed

## Architecture
```
backend/
  services/physics.py   - Q-factor, gamma cap fix, SWR span
  routes/user.py        - Save/load, auth, subscriptions
  routes/antenna.py     - Calculate, gamma designer, fine-tune
  models.py             - AntennaInput with swr_span_mhz
frontend/
  app/index.tsx         - Reset, dual-method scale modal, power advisory
  app/admin.tsx         - Feature locks
  components/SwrMeter   - Auto-scaling Y-axis
```

## Backlog
- P1: Auto-Tune for Direct Feed antennas
- P2: SWR Mismatch Between Models
- P2: Series-capacitor dielectric model
- P2: Refactor large components
- P3: iOS version
