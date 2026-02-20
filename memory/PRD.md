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
- Teflon: 4" (tube + 1")
- Rod spacing: 3.5"
- Rod length: 22" (2-6 elements), 30" (7+ elements)
- Bar min = teflon end (4")
- Max insertion = teflon - 0.5" = 3.5" (rod stops 0.5" before teflon end to avoid shorting)

### Physical Constraints (CRITICAL):
- **Bar position**: Bar clamps on exposed rod right where teflon ends. bar_min = teflon_length
- **Rod insertion**: Rod slides into tube, must stop 0.5" before teflon end to avoid shorting. max_insertion = teflon - 0.5"
- **Teflon**: Always tube + 1". Insulator sleeve inside tube, keeps rod centered, creates capacitor
- **Rod length**: Tube length + enough for bar adjustment range

### SWR Results with Current Hardware (5/8" rod, tube=3"):
- 2-element: 1.107 (null not reachable, best achievable)
- 3-element: 1.00
- 4-20 element: 1.00

## What's Been Implemented

### Session Feb 2026 — P0 Fix (max_insertion constraint):
- FIXED: `apply_matching_network()` insertion cap changed from `tube_length` to `max_insertion = teflon - 0.5"`
- FIXED: Designer auto_rod unified to 0.625" (was 0.5625/0.500)
- FIXED: Designer insertion sweep uses `max_insertion` (was `tube_length`)
- FIXED: Debug trace formula updated to show `max_insertion`
- FIXED: Notes reference `max_insertion` instead of `tube_length`
- VERIFIED: 15/15 backend tests passed

### Session Feb 2026 — P1 Refactoring (shared physics helpers):
- EXTRACTED: `get_gamma_hardware_defaults(num_elements)` — single source of truth for hardware constants
- EXTRACTED: `compute_feedpoint_impedance()` — mutual coupling model shared between calculate and designer
- EXTRACTED: `compute_element_resonant_freq()` — resonance with coupling correction shared between calculate and designer
- Updated `apply_matching_network()` to use `get_gamma_hardware_defaults()`
- Updated `calculate_antenna_parameters()` to use shared impedance and resonant freq helpers
- Updated `design_gamma_match()` to use all three shared helpers
- VERIFIED: All results identical before and after refactoring

### Prior Session Work:
- Physics Unification: Synchronized SWR/impedance between /api/calculate and /api/gamma-designer
- Driven Element Correction: Designer auto-calculates correct driven element length for resonance
- Hardware Optimization: 5/8" rod, 3" tube, 4" teflon for all element counts
- Physical Constraint Refinement: bar_min = teflon end, max_insertion = teflon - 0.5"
- Frontend Polish: 0.01" step controls for fine-tuning

## Prioritized Backlog
- P2: Air gap dielectric model for series capacitor (accounts for air gap between teflon and tube wall)
- P2: PayPal/CashApp Payments
- P2: Improve .easignore to reduce build size
- P3: Build iOS Version

## Key Files
- `backend/services/physics.py` — All physics calculations (three shared helpers + main functions)
- `backend/routes/antenna.py` — API endpoints
- `backend/models.py` — Pydantic models
- `frontend/app/index.tsx` — Main UI
- `frontend/components/GammaDesigner.tsx` — Designer modal

## Key API Endpoints
- `POST /api/calculate` — Main calculation
- `POST /api/gamma-designer` — Auto-tune designer

## Debugging Checklist
- If SWR differs between designer and calculator: check if element_resonant_freq_mhz and feedpoint_impedance are being passed from frontend
- If bar position seems wrong: check bar_min = teflon_sleeve
- If insertion bottoms out: check max_insertion = teflon_sleeve - 0.5
- If hardware defaults wrong: check get_gamma_hardware_defaults() in physics.py
