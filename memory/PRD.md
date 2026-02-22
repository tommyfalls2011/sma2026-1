# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.3, versionCode: 22

## Completed This Session (Feb 2026)
1. **Fine-Tune Gamma FIXED** - Root cause: optimizer used gamma-matched SWR as sole metric, but gamma match always achieves ~1.0 regardless of elements. Fix: multi-objective `_perf_score()` scoring function that optimizes impedance (target Z=22 ohms), SWR, and boom length. Elements now MOVE on all antenna configurations (3-20 elements).
2. **Impedance bug fix** - `_fast_gamma_swr` was using `cumulative=False` for director spacings (should be True). Fixed to match full evaluator's impedance calculation.
3. **Director length optimization** - Added Pass 5 to sweep director lengths for better impedance.
4. **Gain tracking** - Added `original_gain` and `optimized_gain` fields to GammaFineTuneOutput. Frontend alert now shows gain changes.
5. **Removed early exit** - Removed `if original_swr <= 1.02: no tuning needed` guard that prevented ALL optimization on well-tuned antennas.

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
  routes/antenna.py     - Calculator, auto-tune, fine-tune, gamma/hairpin designers
  services/physics.py   - Core physics: _perf_score, _fast_gamma_swr (fixed cumulative),
                          gamma_fine_tune (multi-objective), apply_matching_network
  models.py             - GammaFineTuneOutput with original_gain/optimized_gain
frontend/
  app/index.tsx         - Fine-Tune button, updated alert with gain info
  components/GammaDesigner.tsx - onApply passes tubeOd + tubeLength
```

## Key API Endpoints
- POST /api/gamma-fine-tune - Multi-objective optimizer, always moves elements
- POST /api/gamma-designer - Full gamma match designer with auto-hardware escalation
- POST /api/calculate - Full antenna calculation (accepts gamma_tube_length)
- POST /api/auto-tune - Auto-tune antenna geometry by build style

## Backlog
- P1: Add power-aware hardware selector (auto-size tube/rod gap based on transmit power)
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx into smaller components
- P3: Build iOS version
