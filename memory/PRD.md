# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.8, versionCode: 27

## Completed This Session (Feb 25, 2026)

### Save/Load Bug Fix
- Added missing gamma settings to save: gammaTubeOd, gammaTubeLength, originalDrivenLength
- Added missing reflector settings: reflectorNudgeCount, reflectorPreset
- Load function now restores all gamma tube and reflector settings

### Frequency Scale Feature (NEW)
- Scale button in action toolbar (always visible, no login required)
- Modal with target frequency input, live preview (ratio, scaled driven length, band match)
- Quick-select buttons for common bands (CB 27, 10m, 6m, 2m)
- Scales: element lengths, positions, height, gamma match settings, hairpin settings, taper sections, stacking spacing
- Diameters preserved (user picks tubing for new band)
- Resets nudge counts and clears gamma cap (needs recalculation at new frequency)

### Power-Aware Advisory Panel (NEW - P1)
- Advisory panel in gamma match design section
- Calculates: capacitor voltage, rod current, feedpoint voltage based on power and SWR
- Thresholds: vCap>500V, rodCurrent>5A, vFeed>300V, power>=1500W
- Color-coded severity: HIGH (red) / MODERATE (orange) / ADVISORY (orange)
- Hardware recommendations (vacuum/doorknob caps, copper tube sizing, silver-plated contacts)

## Previous Session Work (Feb 22, 2026)
- Element Diameter Q-Factor Model
- Fine-Tune Gamma FIXED (multi-objective optimization)
- Reflector Spacing Controls Added
- Return Loss Tune Fixed

## Architecture
```
backend/
  services/physics.py   - Q-factor, SWR, optimization algorithms
  routes/user.py        - Save/load designs, RL tune, auth, subscriptions
  routes/antenna.py     - Calculate, gamma designer, fine-tune
  models.py             - SavedDesign with spacing_state (now includes gamma tube + reflector fields)
frontend/
  app/index.tsx         - Scale modal, power advisory, save/load with full gamma state
```

## Key API Endpoints
- POST /api/calculate - Full calculation with Q-factor model
- POST /api/gamma-fine-tune - Multi-objective optimizer
- POST /api/optimize-return-loss - Reflector sweep + gamma designer
- POST /api/gamma-designer - Full gamma match designer
- POST /api/designs/save - Save design (now with full gamma/reflector state)
- GET /api/designs/{id} - Load design (restores all settings)

## Backlog
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx into smaller components
- P2: Fix SWR mismatch between gamma designer and main calculate models
