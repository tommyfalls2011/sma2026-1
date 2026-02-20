# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator (React/Expo frontend + FastAPI backend) for CB radio Yagi antennas. Calculates impedance, SWR, and gamma match tuning for 2-20 element Yagi antennas at 27.185 MHz.

## Core Architecture
- **Frontend**: React/Expo Web on port 3000
- **Backend**: FastAPI on port 8001
- **No database** (stateless calculations)

## Current Hardware Defaults (Feb 2026)

### Per-Element Hardware Sizing:
| Elements | Rod OD | Tube OD | Tube Len | Teflon | Max Ins | Rod Length | SWR |
|----------|--------|---------|----------|--------|---------|------------|------|
| 2        | 0.875" (7/8") | 1.0" | 4.0" | 5.0" | 3.5" | 22" | 1.032 |
| 3        | 0.750" (3/4") | 0.875" (7/8") | 3.5" | 4.5" | 3.0" | 22" | 1.001 |
| 4-6      | 0.625" (5/8") | 0.750" (3/4") | 3.0" | 4.0" | 2.5" | 22" | 1.008 |
| 7+       | 0.625" (5/8") | 0.750" (3/4") | 3.0" | 4.0" | 2.5" | 30" | ≤1.005 |

Common: Wall=0.049", Rod spacing=3.5"

### Physical Constraints:
- **Bar position**: bar_min = teflon_length (bar clamps where teflon ends on exposed rod)
- **Rod insertion**: max_insertion = tube_length - 0.5" (rod stops 0.5" before far end of tube)
- **Teflon**: tube + 1" — extends 1" past tube open end for RF arc prevention
- **Bar sweep**: starts at bar_min (not 0)

### Default Taper Configuration:
- 1 taper, center_length=36", taper length=50", start=0.625", tip=0.5"

## What's Been Implemented

### Session Feb 2026 — Per-Element Hardware (rod/tube/tube_length):
- 2-el: 7/8" rod, 1" tube OD, 4" tube → SWR=1.032 (RL=36dB)
- 3-el: 3/4" rod, 7/8" tube OD, 3.5" tube → SWR=1.001 (RL=66dB)
- 4+: 5/8" rod, 3/4" tube OD, 3" tube → SWR≤1.008

### Session Feb 2026 — Optimizer Fix:
- Global optimizer sweeps full bar range (bar_min→rod_length) for best SWR
- Bar sweep in designer starts at bar_min (was 0)
- Frontend barMin = teflonEnd (removed +0.5 offset)
- Frontend insertion max = tube_length - 0.5

### Session Feb 20 2026 — Rod/Tube Mismatch Bug Fix:
- Fixed frontend GammaDesigner sending stale `custom_rod_od` from previous element count in auto mode
- Reset `gammaRodDia` to null when element count changes in index.tsx
- Added backend safety net: auto-bumps tube_od when custom rod is too large for default tube

### Session Feb 2026 — UI Fixes:
- Fixed "Shorting Bar" display showing rod_spacing instead of actual bar position → now shows "Bar Position" with correct value
- Designer "Apply" now passes rod_od to main calculator so per-element hardware carries through
- Updated chart titles for clarity: "BAR POSITION SWEEP — insertion held at X" and "ROD INSERTION SWEEP — bar held at X" ✅ Verified Feb 20 2026

### Session Feb 2026 — P1 Refactoring:
- Extracted shared helpers: get_gamma_hardware_defaults(), compute_feedpoint_impedance(), compute_element_resonant_freq()

### Prior Session Work:
- Physics Unification, Driven Element Correction, Frontend 0.01" step controls

## Pending/Known Issues
- **Frontend initial gammaBarPos=18**: When page loads, bar defaults to 18" which is far from optimal. User must use Designer to get correct values. Consider auto-running designer on element count change.

## Prioritized Backlog
- P2: Air gap dielectric model
- P2: PayPal/CashApp Payments
- P2: Improve .easignore
- P3: iOS Version

## Key Files
- `backend/services/physics.py` — All physics (shared helpers + main functions)
- `frontend/app/index.tsx` — Main UI
- `frontend/components/GammaDesigner.tsx` — Designer modal

## Key API Endpoints
- `POST /api/calculate` — Main calculation
- `POST /api/gamma-designer` — Auto-tune designer

## Credentials
- Store Admin: fallstommy@gmail.com / admin123
- Bronze Test: bronze@test.com / password123
