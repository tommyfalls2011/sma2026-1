# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator (React/Expo frontend + FastAPI backend) for CB radio Yagi antennas. The app calculates impedance, SWR, and gamma match tuning for 2-20 element Yagi antennas at 27.185 MHz.

## Core Architecture
- **Frontend**: React/Expo Web on port 3000
- **Backend**: FastAPI on port 8001
- **No database** (stateless calculations)

## Current Hardware Defaults (Feb 20, 2026)

### 2-Element Only:
- Rod: 48", Tube: 30", Teflon: 31"
- Rod OD: 0.5625" (9/16"), Tube OD: 0.750"
- Driven element: 208", Spacing: 3.5"

### 3-20 Elements:
- Rod: 36", Tube: 22", Teflon: 23"
- Rod OD: 0.500" (1/2"), Tube OD: 0.750"
- Driven element: 204", Spacing: 3.5"

### Shared Defaults:
- Bar position: 18" (average across configs)
- Rod insertion: 8" (average across configs)

## What's Been Implemented

### Session Feb 19, 2026 (Fork 7):
- Major physics engine overhaul & unification
- Physics Trace debug panel
- SWR curve centered on element resonant frequency
- Removed incorrect ground radial SWR bonus
- Gamma Designer overhaul to match main calculator

### Session Feb 19, 2026 (Fork 8):
- Verified P0 (PERFECT MATCH label) and P1 (3-element tune) fixes

### Session Feb 20, 2026 (Fork 9) — CURRENT:
- Updated gamma hardware to user specs (rod 48"/36", tube 30"/22", teflon 31"/23")
- Unified hardware across 3-20 elements (same rod/tube/spacing)
- 2-element gets special hardware (0.5625" rod, 48" rod, 30" tube)
- Dynamic feedpoint R based on reflector LENGTH (Q-based coupling model)
- Feedpoint R no longer hardcoded — varies with element length, spacing, and count
- Designer now passes driven_element_dia for consistent Z0 calculation
- Designer now computes dynamic feedpoint R (same formula as main calculator)
- Fixed director gap formula in designer (was starting at 48" instead of 64")
- Fixed floating point display on bar position (.toFixed(2))
- Added teflon end marker and bar range display on slider
- Rod length now reads from backend (not hardcoded 36")
- Compared theory vs model for 2, 4, 10 elements — 2 and 10 match perfectly

## Known Issues
- 4-element SWR 1.19 (X_net = -8.44Ω) — antenna reactance from 204" driven not fully cancelled
- This could be improved by optimizing 4-element driven length (like 208" for 2-element)

## Prioritized Backlog
- P1: Optimize driven element length per element count for better default match
- P2: Air gap dielectric model for series capacitor
- P2: PayPal/CashApp Payments
- P2: Improve .easignore
- P3: Build iOS Version

## Key Files
- `backend/services/physics.py` — All physics calculations
- `backend/routes/antenna.py` — API endpoints
- `backend/models.py` — Pydantic models
- `frontend/app/index.tsx` — Main UI
- `frontend/components/GammaDesigner.tsx` — Designer modal
- `frontend/components/PhysicsDebugPanel.tsx` — Debug panel

## Key API Endpoints
- `POST /api/calculate` — Main calculation
- `POST /api/gamma-designer` — Auto-tune designer
