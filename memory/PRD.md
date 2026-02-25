# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.8, versionCode: 27

## Completed This Session (Feb 25, 2026)

### Auto-Tune / Fine-Tune Gamma — Major Fix
- Fixed `gamma_element_gap` vs `gamma_cap_pf` parameter mismatch in `_fast_gamma_swr` and `design_gamma_match` — cap was passed as wrong param
- Scaled `bar_min` with wavelength for VHF/UHF (was 4" fixed, now 0.7" at 144MHz)
- Improved perf_score: SWR weight 25x, wider acceptable Z range (18-35Ω)
- Result: 144MHz 7-element tunes to SWR=1.006, CB 27MHz tunes to SWR=1.0

### SWR Curve Physics Fix
- antenna_q varies with element count, spacing, diameter, matching network
- Smith chart sweep uses matching_info.cap_pf_used and antenna_q_used for consistency
- Sharp V for high-Q, wide U for low-Q

### SWR Span Control
- SPAN buttons above SWR chart: Band, 1, 2, 5, 10, 20 MHz
- 201 points for smooth curves, auto-scaling Y-axis
- Direct calculateAntenna(opt.value) call to avoid closure issues

### Reset Button — Full Reset
- handleRefresh now resets ALL state: inputs, spacing, locks, gamma, hairpin, coax, power, build style, SWR span, element unit, gain mode, nudge counts, presets

### Save/Load Bug Fix
- Added missing gamma tube + reflector settings to save/load

### Frequency Scale Feature
- Scale button rescales design to any target frequency proportionally
- Feature-gated as 'scale_design'

### Power-Aware Advisory Panel
- Calculates cap voltage, rod current, feedpoint voltage at high power
- Feature-gated as 'power_advisory'

### Admin Panel Updates
- Added 3 new features to locks: scale_design, fine_tune_gamma, power_advisory
- Admin account restored (fallstommy@gmail.com / admin123)

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
- P1: Verify SWR span buttons working on user's device
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx into smaller components
