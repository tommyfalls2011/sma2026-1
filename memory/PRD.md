# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.8, versionCode: 27

## Completed This Session (Feb 25, 2026)

### SWR Curve Physics Fix (Major)
- Fixed antenna_q to vary with element count, spacing, diameter, matching network
- Fixed Smith chart sweep cap_pf_used and antenna_q_used consistency
- Result: Sharp V for high-Q (many elements, thin), wide U for low-Q

### SWR Span Control (NEW)
- SPAN buttons below SWR chart: Band (default), 1, 2, 5, 10, 20 MHz
- Backend swr_span_mhz param generates 61 points across chosen span
- SwrMeter Y-axis auto-scales: yMax=3/5/10 based on data range
- Frequency labels adapt for wide spans (MHz markers instead of channels)

### Save/Load Bug Fix
- Added missing gamma tube + reflector settings to save/load

### Frequency Scale Feature (NEW)
- Scale button rescales design to any target frequency proportionally
- Feature-gated as 'scale_design'

### Power-Aware Advisory Panel (NEW)
- Calculates cap voltage, rod current, feedpoint voltage at high power
- Feature-gated as 'power_advisory'

### Admin Panel Updates
- Added 3 new features to locks: scale_design, fine_tune_gamma, power_advisory

## Architecture
```
backend/
  services/physics.py   - Q-factor physics, SWR span sweep, Smith chart
  routes/user.py        - Save/load, RL tune, auth, subscriptions
  routes/antenna.py     - Calculate, gamma designer, fine-tune
  models.py             - AntennaInput with swr_span_mhz, SavedDesign
frontend/
  app/index.tsx         - Scale modal, power advisory, span buttons, save/load
  app/admin.tsx         - Feature locks with new features
  components/SwrMeter   - Auto-scaling Y-axis, adaptive freq labels
```

## Backlog
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx into smaller components
