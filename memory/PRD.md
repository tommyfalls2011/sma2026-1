# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.4, versionCode: 23

## Completed This Session (Feb 22, 2026)

### Element Diameter Q-Factor Model (NEW)
- Added `compute_diameter_q_factor()` using antenna thickness parameter Omega = 2*ln(2L/a)
- `calculate_swr_from_elements()` now scales SWR sensitivity by Q ratio
- Bandwidth calculation uses Q-based `bandwidth_mult` instead of crude binary thresholds
- `antenna_q` computed as `12.0 * q_ratio` instead of hardcoded 12.0
- SWR curve exponent varies with diameter: fat=1.38 (U-shape), standard=1.60, thin=1.77 (V-shape)
- `calculate_taper_effects()` uses actual start/end diameters for equivalent Q computation
- New `element_q_info` field in AntennaOutput with q_ratio, bandwidth_mult, description
- Verified: 1.25"→BW 0.946MHz, SWR 1.94 | 0.5"→BW 0.816MHz, SWR 2.37 | 0.25"→BW 0.739MHz, SWR 2.71

### Fine-Tune Gamma FIXED
- Multi-objective `_perf_score()` scoring (impedance + SWR + boom length)
- Elements now MOVE on all configurations. Fixed cumulative parameter bug.

### Reflector Spacing Controls Added
- 5 presets (V.Close→V.Far) + Closer/Farther nudge buttons in Element Spacing UI

### Return Loss Tune Fixed
- Reflector position sweep, gamma designer on winner, returns gamma recipe
- SWR improved from ~2:1 to ~1.0:1

## Architecture
```
backend/
  services/physics.py   - compute_diameter_q_factor(), antenna_q = 12*q_ratio,
                          Q-aware calculate_swr_from_elements(), taper_effects with real diameters,
                          _perf_score multi-objective optimizer
  routes/antenna.py     - RL tune with reflector sweep + gamma designer
  models.py             - AntennaOutput.element_q_info, GammaFineTuneOutput with gains
frontend/
  app/index.tsx         - Reflector spacing presets/nudge, Fine-Tune, RL tune with gamma recipe
```

## Key API Endpoints
- POST /api/calculate - Full calculation with Q-factor model, element_q_info in response
- POST /api/gamma-fine-tune - Multi-objective optimizer
- POST /api/optimize-return-loss - Reflector sweep + gamma designer
- POST /api/gamma-designer - Full gamma match designer
- POST /api/auto-tune - Auto-tune by build style

## Backlog
- P1: Add power-aware hardware selector
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx
- P3: Build iOS version
