# SMA Antenna Calculator - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator app with payment processing (Stripe/PayPal), admin panel, and RF physics engine for amateur radio operators designing Yagi antennas with gamma/hairpin matching.

## Current Version
app.json: 4.3.8, versionCode: 27

## Completed This Session (Feb 25, 2026)

### SWR Curve Physics Fix (Major)
- Fixed antenna_q to vary with element count (2-el: Q*0.7, 3-el: Q*1.0, 5-el: Q*1.4+)
- Fixed antenna_q to vary with reflector-driven spacing (tight: Q*1.5, wide: Q*0.8)
- Fixed antenna_q to include matching network Q (gamma bar position, cap value effects)
- Fixed Smith chart sweep to use matching_info.cap_pf_used (actual cap) instead of insertion_cap_pf (geometric)
- Fixed Smith chart sweep to use matching_info.antenna_q_used for consistency with apply_matching_network
- Moved dia_q_info computation before apply_matching_network call
- Result: Sharp V curve for high-Q (many elements, thin), wide U curve for low-Q (few elements, fat)

### Save/Load Bug Fix
- Added missing gamma settings to save: gammaTubeOd, gammaTubeLength, originalDrivenLength
- Added missing reflector settings: reflectorNudgeCount, reflectorPreset
- Load function now restores all gamma tube and reflector settings

### Frequency Scale Feature (NEW)
- Scale button in action toolbar (always visible)
- Modal with target frequency input, live preview (ratio, scaled driven length, band match)
- Quick-select buttons for common bands (CB 27, 10m, 6m, 2m)
- Scales: element lengths, positions, height, gamma match settings, hairpin settings
- Feature-gated as 'scale_design' in admin panel

### Power-Aware Advisory Panel (NEW - P1)
- Advisory panel in gamma match design section
- Calculates: capacitor voltage, rod current, feedpoint voltage based on power and SWR
- Color-coded severity with hardware recommendations
- Feature-gated as 'power_advisory' in admin panel

### Admin Panel Updates
- Added 3 new features to feature locks: scale_design, fine_tune_gamma, power_advisory
- Added FEATURE_LABELS for all new features
- Admin account restored (fallstommy@gmail.com / admin123, tier: admin)

## Architecture
```
backend/
  services/physics.py   - Q-factor with element count/spacing/matching Q, SWR curve fix
  routes/user.py        - Save/load designs, RL tune, auth, subscriptions
  routes/antenna.py     - Calculate, gamma designer, fine-tune
  models.py             - SavedDesign with spacing_state
frontend/
  app/index.tsx         - Scale modal, power advisory, save/load with full gamma state
  app/admin.tsx         - Feature locks with 3 new features
```

## Backlog
- P2: More accurate series-capacitor dielectric model
- P2: Refactor subscription.tsx and admin.tsx into smaller components
