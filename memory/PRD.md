# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator (React/Expo frontend + FastAPI backend) for CB radio Yagi antennas. Calculates impedance, SWR, and gamma match tuning for 2-20 element Yagi antennas at 27.185 MHz.

## Core Architecture
- **Frontend**: React/Expo Web on port 3000
- **Backend**: FastAPI on port 8001
- **No database** (stateless calculations)

## Current Hardware Defaults (Feb 2026)

### Per-Element Tube Sizing:
| Elements | Tube | Teflon | Max Ins | Rod OD | Rod Length |
|----------|------|--------|---------|--------|------------|
| 2        | 4.0" | 5.0"   | 3.5"    | 0.625" | 22"        |
| 3        | 3.5" | 4.5"   | 3.0"    | 0.625" | 22"        |
| 4-6      | 3.0" | 4.0"   | 2.5"    | 0.625" | 22"        |
| 7+       | 3.0" | 4.0"   | 2.5"    | 0.625" | 30"        |

Common: Tube OD=0.750", Rod spacing=3.5", Wall=0.049"

### Physical Constraints:
- **Bar position**: bar_min = teflon_length (bar clamps where teflon ends on exposed rod)
- **Rod insertion**: max_insertion = tube_length - 0.5" (rod stops 0.5" before far end of tube)
- **Teflon**: tube + 1" — extends 1" past tube open end for RF arc prevention

### SWR Results (per-element tube sizing):
| Elements | SWR   | Null | Bar    | Insertion |
|----------|-------|------|--------|-----------|
| 2        | 1.106 | No   | 5.42"  | 3.5" (max)|
| 3        | 1.024 | No   | 7.12"  | 3.0" (max)|
| 4        | 1.008 | No   | 8.72"  | 2.5" (max)|
| 5        | 1.003 | Yes  | 10.53" | 2.08"     |
| 6        | 1.005 | Yes  | 12.32" | 1.77"     |
| 8        | 1.002 | Yes  | 16.68" | 1.30"     |
| 20       | 1.003 | Yes  | 29.68" | 0.70"     |

## What's Been Implemented

### Session Feb 2026 — Per-Element Tube Sizing:
- Implemented auto-sizing: 2-el→4.0", 3-el→3.5", 4+→3.0"
- FIXED optimizer: now sweeps full bar range (bar_min to rod_length) to find global best SWR
- Previous optimizer only searched when null wasn't reachable, missing better solutions
- Results: 2-el improved from 1.233→1.106, 3-el from 1.092→1.024
- VERIFIED: 13/13 backend tests passed (iteration_32)

### Session Feb 2026 — Physical Constraint Fix:
- max_insertion = tube_length - 0.5 (was incorrectly teflon - 0.5)
- Per the user: rod slides into tube, must stop 0.5" before far end

### Session Feb 2026 — P1 Refactoring:
- Extracted shared helpers: get_gamma_hardware_defaults(), compute_feedpoint_impedance(), compute_element_resonant_freq()
- Single source of truth for both /api/calculate and /api/gamma-designer

### Prior Session Work:
- Physics Unification between calculator and designer
- Driven Element Correction (auto-recommend corrected driven element length)
- Frontend: 0.01" step controls for fine-tuning

## Prioritized Backlog
- P2: Air gap dielectric model (teflon-to-tube wall air gap)
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
