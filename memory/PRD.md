# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator (React/Expo frontend + FastAPI backend) for CB radio Yagi antennas. Calculates impedance, SWR, and gamma match tuning for 2-20 element Yagi antennas at 27.185 MHz.

## Core Architecture
- **Frontend**: React/Expo Web on port 3000
- **Backend**: FastAPI on port 8001
- **No database** (stateless calculations)

## Current Hardware Defaults (Feb 2026)

### ALL Elements (unified):
- Rod OD: 0.625" (5/8")
- Tube OD: 0.750", Tube length: 3"
- Teflon: 4" (tube + 1") — extends 1" past tube open end for RF arc prevention
- Rod spacing: 3.5"
- Rod length: 22" (2-6 elements), 30" (7+ elements)
- Bar min = teflon end (4") — bar clamps where teflon ends on the exposed rod
- **Max insertion = tube_length - 0.5" = 2.5"** — rod stops 0.5" before far end of tube

### Physical Constraints (CRITICAL):
- **Bar position**: Bar clamps on exposed rod right where teflon ends. bar_min = teflon_length
- **Rod insertion**: Rod slides into tube, must stop 0.5" before **far end of tube** to avoid shorting. max_insertion = tube_length - 0.5"
- **Teflon**: Always tube + 1". Extends 1" past tube on the **open end** (rod-entry side) to prevent RF arcing. Does NOT affect max insertion.
- **Rod length**: Tube length + enough for bar adjustment range

### SWR Results with Current Hardware (5/8" rod, tube=3"):
- 2-element: 1.233 (null NOT reachable — needs 5.4" insertion, max is 2.5")
- 3-element: 1.091 (null NOT reachable — needs 3.2" insertion, max is 2.5")
- 4-element: 1.012 (barely reaches null — insertion ~2.49")
- 6-element: 1.00
- 8-element: 1.00
- 20-element: 1.00

## What's Been Implemented

### Session Feb 2026 — Physical Constraint Fix:
- FIXED: max_insertion = tube_length - 0.5 (was incorrectly teflon - 0.5 = 3.5")
- FIXED: Designer and calculator both use tube_length - 0.5 = 2.5" as insertion cap
- FIXED: Designer auto_rod unified to 0.625" for all element counts
- VERIFIED: 17/17 backend tests passed (iteration_31)

### Session Feb 2026 — P1 Refactoring (shared physics helpers):
- EXTRACTED: `get_gamma_hardware_defaults(num_elements)` — single source of truth for hardware constants
- EXTRACTED: `compute_feedpoint_impedance()` — mutual coupling model shared between calculate and designer
- EXTRACTED: `compute_element_resonant_freq()` — resonance with coupling correction
- Both `/api/calculate` and `/api/gamma-designer` now use shared helpers

### Prior Session Work:
- Physics Unification: Synchronized SWR/impedance between /api/calculate and /api/gamma-designer
- Driven Element Correction: Designer auto-calculates correct driven element length for resonance
- Hardware Optimization: 5/8" rod, 3" tube, 4" teflon for all element counts
- Frontend Polish: 0.01" step controls for fine-tuning

## Prioritized Backlog
- P1: Explore longer tube for 2-el and 3-el to improve SWR (3-el needs ~3.7" tube, 2-el needs ~6")
- P2: Air gap dielectric model for series capacitor
- P2: PayPal/CashApp Payments
- P2: Improve .easignore to reduce build size
- P3: Build iOS Version

## Key Files
- `backend/services/physics.py` — All physics (shared helpers + main functions)
- `frontend/app/index.tsx` — Main UI
- `frontend/components/GammaDesigner.tsx` — Designer modal

## Key API Endpoints
- `POST /api/calculate` — Main calculation
- `POST /api/gamma-designer` — Auto-tune designer

## Debugging Checklist
- If insertion exceeds tube_length: check max_insertion = tube_length - 0.5 in get_gamma_hardware_defaults()
- If SWR differs between designer and calculator: check if element_resonant_freq_mhz is passed
- If bar position wrong: check bar_min = teflon_sleeve
- If hardware defaults wrong: check get_gamma_hardware_defaults() in physics.py
