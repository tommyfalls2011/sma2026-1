# HANDOFF: Antenna App Spacing Override Fixes

## PROBLEM STATEMENT
The antenna calculator app's Close/Normal/Far spacing override buttons don't change element positions or gain/F/B values after auto-tune. All three modes return identical results.

## ROOT CAUSE IDENTIFIED
1. **`AutoTuneRequest` model was missing the spacing override fields** - `close_driven`, `far_driven`, `close_dir1`, `far_dir1` were not defined in the Pydantic model, so the API ignored these parameters
2. **Driven position was calculated using boom percentage** (`target_boom * 0.15`) instead of wavelength-based spacing
3. **Railway backend has OLD code** - despite saving to GitHub, Railway may not have auto-deployed or has caching issues

## FIXES APPLIED IN THIS SESSION (server.py)

### 1. Added spacing override fields to AutoTuneRequest model (line ~570)
```python
class AutoTuneRequest(BaseModel):
    # ... existing fields ...
    # Spacing override flags (Close/Normal/Far)
    close_driven: bool = Field(default=False)  # 0.12λ reflector-driven spacing
    far_driven: bool = Field(default=False)    # 0.22λ reflector-driven spacing
    close_dir1: bool = Field(default=False)    # Tight first director spacing
    far_dir1: bool = Field(default=False)      # Wide first director spacing
```

### 2. Wavelength-based driven position (line ~2177)
```python
if use_reflector:
    # Close: 0.12λ, Normal: 0.18λ, Far: 0.22λ
    if getattr(request, 'close_driven', False):
        refl_driven_lambda = 0.12
    elif getattr(request, 'far_driven', False):
        refl_driven_lambda = 0.22
    else:
        refl_driven_lambda = 0.18  # Normal default
    
    refl_driven_gap = round(refl_driven_lambda * wavelength_in, 1)
```

### 3. Position-based gain/F/B corrections (line ~2325)
Uses actual final element positions in wavelengths to compute gain and F/B corrections.

### 4. Boom length gain adjustment (line ~2320)
```python
if final_boom > 0 and standard_boom_in > 0:
    boom_ratio = final_boom / standard_boom_in
    if boom_ratio > 0 and boom_ratio != 1.0:
        boom_adj = round(2.5 * math.log2(boom_ratio), 2)
        base_gain += boom_adj
```

### 5. Boom length F/B adjustment (line ~2438)
```python
if final_boom > 0 and standard_boom_in > 0:
    boom_ratio = final_boom / standard_boom_in
    if boom_ratio > 0 and boom_ratio != 1.0:
        fb_boom_adj = round(1.5 * math.log2(boom_ratio), 1)
        predicted_fb += fb_boom_adj
```

### 6. F/B spacing correction in calculate_antenna_parameters (line ~1493)
Adjusts F/B based on actual reflector-driven spacing in wavelengths.

### 7. Physics-based beamwidth (line ~1535)
`BW_H × BW_V = 32400/G_linear`, split by antenna aspect ratio.

## VERIFICATION
**Local (Emergent) works:**
- Close: Position 52.1", Gain 15.0 dBi, F/B 26.5 dB
- Normal: Position 78.2", Gain 16.0 dBi, F/B 25.6 dB
- Far: Position 95.5", Gain 16.2 dBi, F/B 25.4 dB

**Railway backend NOT working:**
- All three modes return Position 44.2", same gain/F/B
- Railway may have old code or deployment failed

## NEXT STEPS FOR NEW AGENT
1. **Verify Railway has latest code** - Check Railway deployment logs, trigger manual redeploy
2. **Compare server.py on Railway vs GitHub** - Ensure the spacing override changes are present
3. **Check if Railway is reading from correct branch** - Should be `main`
4. **Test Railway endpoint directly** after confirming deployment:
```bash
curl -X POST https://helpful-adaptation-production.up.railway.app/api/auto-tune \
  -H "Content-Type: application/json" \
  -d '{"band":"11m_cb","num_elements":5,"height_from_ground":30,"height_unit":"ft","boom_diameter":2,"use_reflector":true,"close_driven":true}'
```

## KEY FILES
- `/app/backend/server.py` - Main API with all antenna calculations
- `/app/frontend/app/index.tsx` - React Native app UI
- `/app/memory/PRD.md` - Project documentation

## URLS
- **Railway backend**: https://helpful-adaptation-production.up.railway.app
- **Railway dashboard**: https://railway.com/project/c930f817-357a-419a-ba12-a7ac71d04752
- **GitHub repo**: https://github.com/tommyfalls2011/sma2026-1
- **E-commerce website**: https://sma-antenna.org

## USER'S VM BUILD PROCESS
```bash
cd ~/sma2026-1/frontend
git pull origin main
yarn install
eas build --platform android --profile preview --local
```
Then upload APK to GitHub releases.

## CREDENTIALS
- **Store Admin**: fallstommy@gmail.com / admin123
- **MongoDB**: In backend/.env (STORE_MONGO_URL)
- **Stripe**: In backend/.env (STRIPE_API_KEY)
