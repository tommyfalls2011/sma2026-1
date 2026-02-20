# SMA Antenna Analyzer - Product Requirements Document

## Original Problem Statement
Full-stack antenna calculator (React/Expo frontend + FastAPI backend) for CB radio Yagi antennas. Calculates impedance, SWR, and gamma match tuning for 2-20 element Yagi antennas at 27.185 MHz.

## Core Architecture
- **Frontend**: React/Expo Web on port 3000
- **Backend**: FastAPI on port 8001
- **No database** (stateless calculations)

## Current Hardware Defaults (Feb 20, 2026)

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
- 2-element: 1.13 (bar clamped at min, best achievable)
- 3-element: 1.00
- 4-20 element: 1.00

## What's Been Implemented

### Session Feb 20, 2026 (Fork 10 - CURRENT):

**P0 Fixes:**
- FIXED: Designer/Calculator Physics Consistency — Designer accepts `element_resonant_freq_mhz`, `reflector_spacing_in`, `director_spacings_in` from main calculator
- FIXED: Default director spacing corrected from 64" to 48"
- VERIFIED: 2-element hardware isolation (confirmed with 20 backend tests)

**New Feature: Driven Element Length Correction:**
- Designer calculates optimal driven element length for resonance = center freq
- Formula: L_new = L_current × (f_res / f_target)
- Apply button sets driven length + bar + insertion in one click
- With correction, X_antenna = 0 for perfect reactance cancellation

**Hardware Optimization (major rework):**
- Enforced physical bar constraint: bar must be past teflon end (can't clamp inside tube)
- Enforced max insertion = teflon - 0.5" (rod stops before teflon end)
- Swept rod diameters: 5/8" rod (0.625") gives ~70 pF/inch vs ~11 pF/inch for 1/2"
- Swept tube lengths: 3" tube with 5/8" rod = sweet spot for all elements
- Changed from per-element hardware (48"/30" rod, 30"/22" tube) to unified 5/8" rod, 3" tube
- Frontend bar/insertion step size changed from 0.25" to 0.01" for fine tuning
- Bar min = teflon end (not teflon + arbitrary gap)

**Code Changes:**
- `backend/services/physics.py`: design_gamma_match() rewritten with proper physical constraints
- `backend/models.py`: GammaDesignerRequest added element_resonant_freq_mhz, reflector_spacing_in, director_spacings_in
- `backend/routes/antenna.py`: Pass new fields to designer
- `frontend/components/GammaDesigner.tsx`: New props for resonant freq and spacings, driven length correction UI, updated Apply button
- `frontend/app/index.tsx`: Pass calculator data to designer, 0.01" step buttons, bar_min from teflon

## IN PROGRESS (was working on when forked):
- Just updated max_insertion = teflon - 0.5" in designer optimizer
- Need to also update main calculator's insertion cap logic to match
- Frontend bar_min display may need updating to match teflon (not teflon + 0.5)
- Need to re-run full element sweep to verify all counts still work with new insertion limit
- User was exploring tube=3.5" for 2-element (gives SWR 1.119 with null reachable)
- May want to set tube=3.5" just for 2-element if 3" bottoms out

## Known Issues
- Frontend step size change (0.25 → 0.01) may need metro cache clear to take effect
- User reported buttons still stepping at 0.25 even after refresh

## Prioritized Backlog
- P0: Verify max_insertion fix works across all element counts (NEXT)
- P0: Decide final tube length for 2-element (3" vs 3.5")
- P1: Refactor physics.py to extract shared logic into helper functions
- P2: Air gap dielectric model for series capacitor
- P2: PayPal/CashApp Payments
- P3: Build iOS Version

## Key Files
- `backend/services/physics.py` — All physics calculations (heavily modified this session)
- `backend/routes/antenna.py` — API endpoints
- `backend/models.py` — Pydantic models (GammaDesignerRequest updated)
- `frontend/app/index.tsx` — Main UI (bar/insertion controls, designer props)
- `frontend/components/GammaDesigner.tsx` — Designer modal (driven length correction)

## Key API Endpoints
- `POST /api/calculate` — Main calculation
- `POST /api/gamma-designer` — Auto-tune designer (with driven length correction + physical constraints)

## Debugging Checklist
- If SWR differs between designer and calculator: check if element_resonant_freq_mhz and feedpoint_impedance are being passed from frontend
- If bar position seems wrong: check bar_min = teflon_sleeve in designer
- If insertion bottoms out: check max_insertion = teflon_sleeve - 0.5
- If frontend buttons don't respond: clear metro cache (rm -rf /app/frontend/node_modules/.cache /tmp/metro-*)
