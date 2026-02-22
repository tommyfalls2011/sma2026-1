# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.4, versionCode: 23

## Completed This Session (Feb 22, 2026)

### Fine-Tune Gamma FIXED
- Root cause: optimizer used gamma-matched SWR as sole metric, but gamma match always achieves ~1.0
- Fix: multi-objective `_perf_score()` scoring that optimizes impedance (target Z=22 ohms), SWR, and boom length
- Elements now MOVE on all antenna configurations (3-20 elements)
- Fixed `cumulative` parameter bug in `_fast_gamma_swr`
- Added director length optimization (Pass 5)
- Added `original_gain` and `optimized_gain` to response

### Reflector Spacing Controls Added
- New "Reflector Spacing" section in Element Spacing UI
- 5 presets: V.Close (0.10λ), Close (0.14λ), Normal (0.18λ), Far (0.22λ), V.Far (0.28λ)
- Closer/Farther nudge buttons with percentage display
- Resets on auto-tune, fine-tune, and RL tune

### Return Loss Tune Fixed
- Added reflector position sweep (±0.02λ in 5 steps)
- Added fine-tune pass around winner (±0.005λ)
- Gamma designer now runs on winning configuration for accurate matched SWR
- SWR improved from ~2:1 (broken) to ~1.0:1 (perfect)
- Returns gamma_recipe with bar position, insertion, rod/tube specs
- Frontend applies gamma recipe from RL tune result

## Previous Session Completions
- Fine-Tune Gamma backend - fast analytical estimator
- Custom tube length bug fix
- Gamma Designer to Main Page SWR sync
- Fine-tune returns gamma recipe
- Auto-recalc dependency fix
- Live recurring subscriptions (Stripe/PayPal)
- Admin panel
- Build styles with auto-tune

## Architecture
```
backend/
  routes/server.py      - Stripe/PayPal recurring logic, webhooks (LIVE)
  routes/user.py        - Auth, subscription, designs
  routes/antenna.py     - Calculator, auto-tune, fine-tune, RL tune (with reflector sweep + gamma designer), gamma/hairpin designers
  services/physics.py   - Core physics: _perf_score, _fast_gamma_swr (fixed cumulative), gamma_fine_tune (multi-objective), apply_matching_network
  models.py             - GammaFineTuneOutput with original_gain/optimized_gain
frontend/
  app/index.tsx         - Reflector spacing presets/nudge, Fine-Tune button, RL tune with gamma recipe apply
  components/GammaDesigner.tsx - onApply passes tubeOd + tubeLength
```

## Key API Endpoints
- POST /api/gamma-fine-tune - Multi-objective optimizer, always moves elements
- POST /api/optimize-return-loss - Sweeps reflector+driven+dir1, runs gamma designer, returns recipe
- POST /api/gamma-designer - Full gamma match designer with auto-hardware escalation
- POST /api/calculate - Full antenna calculation (accepts gamma_tube_length)
- POST /api/auto-tune - Auto-tune antenna geometry by build style

## Backlog
- P1: Add power-aware hardware selector (auto-size tube/rod gap based on transmit power)
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx into smaller components
- P3: Build iOS version
