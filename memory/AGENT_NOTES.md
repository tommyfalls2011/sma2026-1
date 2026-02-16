# CRITICAL SETUP NOTES FOR FUTURE AGENTS

## User's Local Development Setup
- User develops on a **VM on their PC**
- Local repo path: **~/sma2026-1**
- GitHub repo: https://github.com/tommyfalls2011/sma2026-1
- User builds APKs via EAS on their VM

## Service Configuration
This app has TWO frontend projects in `/app/frontend/`:
1. **Expo/React Native antenna calculator app** (in `app/` directory) — THIS IS THE MAIN APP
2. **Vite/React e-commerce website** (in `src/` directory) — secondary

### How to run the Antenna App (PRIMARY)
The supervisor service `expo` must be running (NOT `frontend`).
```bash
sudo supervisorctl stop frontend    # Stop Vite if running
sudo supervisorctl start expo       # Start Expo (serves on port 3000)
```

### How to run the E-commerce Website (SECONDARY) 
```bash
sudo supervisorctl stop expo        # Stop Expo if running
sudo supervisorctl start frontend   # Start Vite (serves on port 3000)
```

**IMPORTANT**: Only ONE can run at a time on port 3000.

## Hot Reload Does NOT Work in Expo CI Mode
The Expo server runs in CI mode (EXPO_NO_DOTENV_EXTRA=true). 
**After ANY code change to files in `/app/frontend/app/`**, you MUST restart expo:
```bash
sudo supervisorctl restart expo
```
Wait 10-15 seconds for Metro to rebundle before testing.

## Backend Architecture (Refactored Feb 16, 2026)
The monolithic `server.py` (4517 lines) was refactored into modular files:
- `server.py` (~100 lines) — slim entry point, mounts all routers under `/api`
- `config.py` — DB connections, constants, band definitions
- `models.py` — all Pydantic request/response models
- `auth.py` — JWT auth, password hashing, settings
- `routes/antenna.py` — `/api/calculate`, `/api/auto-tune`, `/api/optimize-*`
- `routes/user.py` — `/api/auth/*`, `/api/subscription/*`, `/api/designs/*`
- `routes/admin.py` — `/api/admin/*`
- `routes/public.py` — `/api/bands`, `/api/app-update`, `/api/download/*`
- `routes/store.py` — `/api/store/*` (e-commerce)
- `services/physics.py` — full antenna physics engine (1066 lines)
- `services/email_service.py` — Resend email + QR code

A backup of the original monolithic file exists at `server_monolithic_backup.py`.

## Key UI Features in index.tsx

### Spacing Override Buttons (Added Feb 16, 2026)
Located in `/app/frontend/app/index.tsx` under the "Element Spacing" section:

**State variables** (around line 355):
```tsx
const [closeDriven, setCloseDriven] = useState(false);
const [farDriven, setFarDriven] = useState(false);
const [closeDir1, setCloseDir1] = useState(false);
const [farDir1, setFarDir1] = useState(false);
```

**Passed to auto-tune API** (in the handleAutoTune function):
```tsx
close_driven: closeDriven,
far_driven: farDriven,
close_dir1: closeDir1,
far_dir1: farDir1,
```

**UI buttons** appear below the Tight/Normal/Long row:
- "Driven Element Spacing": Close (0.12λ) / Normal (0.18λ) / Far (0.22λ)  
- "1st Director Spacing": Close / Normal / Far

The backend handles these in `services/physics.py` (lines ~895, ~1043).

## Version Management
- App version is in `/app/frontend/app.json` (`version` and `versionCode` fields)
- Backend app-update API (`/api/app-update`) tells the mobile app about available updates
- Both must be updated when releasing a new version

## Credentials
- **Admin**: fallstommy@gmail.com / admin123
- **Backend URL**: https://physics-backend.preview.emergentagent.com

## Latest Session Updates (Feb 16, 2026)
1. **Backend refactored** from monolithic 4517-line `server.py` → modular architecture (backup at `server_monolithic_backup.py`). All 24/24 API tests passed.
2. **Spacing override buttons added** to `index.tsx`: Driven Element (Close 0.12λ / Normal 0.18λ / Far 0.22λ) + 1st Director (Close / Normal / Far). State vars: `closeDriven`, `farDriven`, `closeDir1`, `farDir1`.
3. **Physics engine fixed** in `services/physics.py`: Both `/api/auto-tune` and `/api/calculate` now properly adjust gain, F/B, SWR based on driven AND director spacing (director spacing was completely missing, driven gain adjustment was missing from calculate).
4. **App version updated** to v4.1.2 (versionCode 7) in `app.json` and `/api/app-update` endpoint.
5. **Preview set to Expo antenna app** (not the Vite website). User is done with the website for now.

## Common Gotchas
1. **Don't switch expo to frontend (Vite)** unless user specifically asks for the website
2. **Always restart expo after code changes** — no hot reload in CI mode
3. **The `package.json` has both Expo and Vite deps** — don't remove either set
4. **REACT_APP_BACKEND_URL** must be set in `/app/frontend/.env`
5. **The Expo CORS error** in logs is normal and can be ignored
