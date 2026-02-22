# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.3, versionCode: 22

## Completed This Session (Feb 2026)
1. **Fine-Tune Gamma backend** — Replaced brute-force algorithm with fast analytical estimator (`_fast_gamma_swr`). <0.2s for all element counts. Works for 3-5 element detuned antennas (e.g., 1.135→1.004, 1.096→1.003).
2. **Custom tube length bug** — `apply_matching_network()` was clamping insertion to 2.5" (default 3" tube) even with custom hardware. Fixed by adding `gamma_tube_length` parameter. High-power combos now work: 1" tube + 5/8" rod gets SWR 1.03 for 8+ elements.
3. **Gamma Designer → Main Page SWR sync** — Added `tube_od` and `tube_length` passthrough from GammaDesigner onApply → index.tsx state → calculate endpoint. Added `gamma_tube_length` to AntennaInput model.
4. **Fine-tune returns gamma recipe** — Backend now returns full gamma_recipe in GammaFineTuneOutput. Frontend applies bar_pos, insertion, rod_od, tube_od, tube_length, and driven correction after fine-tune.
5. **Auto-recalc dependency fix** — Added `gammaTubeOd` and `gammaTubeLength` to both useCallback and useEffect dependency arrays. Removed race-condition setTimeout.

## Known Issue: Fine-Tune Doesn't Move Elements for 6+ Element Antennas
- For 6+ elements, the gamma designer with auto-hardware escalation already achieves SWR ~1.0, so fine-tune says "already near-perfect" and doesn't adjust elements.
- Elements DO move for 3-5 element detuned antennas where gamma match struggles.
- The fine-tune still applies gamma recipe settings even when elements don't move, so the main page SWR updates correctly.
- **TODO**: Consider making fine-tune optimize for a broader goal (e.g., maximize gain while maintaining matchable impedance) so elements move even when gamma match is already perfect.

## Architecture
```
backend/
  routes/server.py      - Stripe/PayPal recurring logic, webhooks (LIVE - DO NOT TOUCH)
  routes/user.py        - Auth, subscription, designs, gamma designer
  routes/antenna.py     - Calculator, auto-tune, fine-tune, gamma/hairpin designers
  services/physics.py   - Core physics: _fast_gamma_swr, gamma_fine_tune,
                          apply_matching_network (now accepts gamma_tube_length)
  models.py             - GammaFineTuneOutput now includes gamma_recipe field
frontend/
  app/index.tsx         - Fine-Tune button, gammaTubeOd/gammaTubeLength state,
                          fineTuneGamma applies gamma recipe on response
  components/GammaDesigner.tsx - onApply now passes tubeOd + tubeLength
```

## Key API Endpoints
- POST /api/gamma-fine-tune — Optimize elements + return gamma recipe
- POST /api/gamma-designer — Full gamma match designer with auto-hardware escalation
- POST /api/calculate — Full antenna calculation (now accepts gamma_tube_length)
- POST /api/auto-tune — Auto-tune antenna geometry by build style

## Backlog
- P1: Make fine-tune more aggressive for 6+ elements (optimize beyond gamma-matched SWR)
- P2: Add power-aware hardware selector (auto-size tube/rod gap based on transmit power)
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx into smaller components
- P3: Build iOS version
