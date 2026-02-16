# CRITICAL SETUP NOTES FOR FUTURE AGENTS

## User's Local Environment
- **User runs a VM on their PC**
- **Local project path**: `~/sma2026-1`
- User builds APK via EAS on their local machine, not in the preview environment
- User tests on their **actual Android phone**, not the web preview

## Preview Environment Setup
- The preview MUST run the **Expo antenna app** (not the Vite website)
- Supervisor services: `expo` (antenna app on port 3000) and `frontend` (Vite website on port 3000) — only ONE can run at a time
- **Stop `frontend` before starting `expo`**: `sudo supervisorctl stop frontend && sudo supervisorctl start expo`
- Expo runs in CI mode with `--tunnel` flag
- **Expo does NOT hot-reload in this environment** — you must restart: `sudo supervisorctl restart expo`
- Clear Metro cache on restart: `rm -rf /app/frontend/.metro-cache`

## Architecture
```
/app/
├── backend/
│   ├── server.py          # Slim entry point
│   ├── config.py          # DB, constants, band definitions
│   ├── models.py          # Pydantic models
│   ├── auth.py            # JWT auth
│   ├── routes/
│   │   ├── antenna.py     # Calculate, auto-tune, optimize
│   │   ├── user.py        # Auth, subscription, designs
│   │   ├── admin.py       # Admin management
│   │   └── public.py      # Public endpoints
│   └── services/
│       ├── physics.py     # Antenna physics engine (HEAVILY MODIFIED)
│       └── email_service.py
└── frontend/              # MIXED: Expo + Vite (needs separation)
    ├── app/
    │   └── index.tsx      # Main calculator UI (3400+ lines)
    ├── src/               # Vite e-commerce website
    ├── app.json           # Expo config, version 4.1.2
    └── package.json
```

## Key Files Modified This Session
- `backend/services/physics.py` — Feed type physics (gamma/hairpin/direct), director spacing sensitivity fix, ground radials gain removal, auto-tune feed type shortening, hairpin_design & gamma_design data in calculate response
- `frontend/app/index.tsx` — Nudge arrows (element spacing, driven, 1st director), gamma/hairpin design panels with editable inputs & sliders, auto-shortening on feed type switch, switchFeedType function

## Frontend State Variables Added
- `drivenNudgeCount`, `dir1NudgeCount`, `spacingNudgeCount` — nudge arrow counters (±5 steps = ±12.5%)
- `hairpinRodDia`, `hairpinRodSpacing` — hairpin panel editable inputs
- `hairpinBarPos` (0.2-0.9 ratio), `hairpinBoomGap` (0.25-3.0 inches) — hairpin sliders
- `gammaRodDia`, `gammaRodSpacing` — gamma panel editable inputs
- `originalDrivenLength` — tracks pre-shortening length for feed type restore

## Key Functions Added
- `nudgeElement('driven'|'dir1', direction)` — nudges single element position by 2.5%
- `nudgeSpacing(direction)` — nudges ALL element positions by 2.5%
- `switchFeedType(newType)` — switches feed type, auto-shortens/restores driven element

## Backend API Changes
- `POST /api/calculate` — now returns `matching_info.hairpin_design` (when hairpin) and `matching_info.gamma_design` (when gamma) with full design calculations
- `POST /api/auto-tune` — now shortens driven element 3% (gamma) or 4% (hairpin) based on feed_type

## Common Issues
1. **Port conflict**: `frontend` and `expo` both use port 3000. Stop one before starting the other.
2. **Expo CORS error** in logs is normal and can be ignored
3. **`@react-native-community/slider`** was installed but doesn't work on React Native Web — custom View-based sliders with +/- buttons are used instead
4. **1st Director nudge** requires 3+ elements (at least one director) — shows "Add 3+ elements" message otherwise

## Credentials
- **Admin**: fallstommy@gmail.com / admin123
