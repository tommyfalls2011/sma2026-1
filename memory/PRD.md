# Antenna Modeling Application - PRD

## Original Problem Statement
A full-stack antenna modeling/calculator application (React Native Expo frontend + FastAPI backend + MongoDB) for designing and analyzing Yagi-Uda antennas with e-commerce store.

## What's Been Implemented

### Current Session (Feb 2026)
- **Real-time matching network tuning**: Gamma/Hairpin design panel adjustments affect SWR in real time
- **Gamma match with real-world physics**:
  - Shorting Bar Position slider → shifts resonant frequency (bar out = lower freq, bar in = higher)
  - Rod Insertion slider → changes Q-factor/bandwidth (more insertion = higher Q = narrower BW)
  - Off-resonance SWR penalty when freq shift exceeds bandwidth
  - Components section: Rod/Tube/Teflon/Shorting Bar descriptions
- **Element-based resonant frequency**: Driven element length + parasitic coupling now compute natural resonant freq
  - Longer driven = lower resonant freq, shorter = higher
  - Reflector pulls freq down ~0.5%, each director pushes up ~0.3%
  - Returned as `element_resonant_freq_mhz` in matching_info
- **Hairpin sliders**: Shorting Bar Position + Rods-to-Boom Gap with Pressable buttons
- **Hairpin Z0**: optimal range 200-600 ohms
- **Performance Metrics**: Gain=15dB, F/B=18dB, F/S=8dB, Eff=100% base scales, auto-grow 15%
- **Gain model updated**: 3-element bumped from 8.2 to 9.0 dBi (1st director ~3dB gain)
- **Expo Web mode**: Preview runs Expo web on port 3000
- **Pressable fix**: Replaced TouchableOpacity with Pressable for web click handling

## Key Architecture
- Backend: `/app/backend/services/physics.py`, `/app/backend/config.py`, `/app/backend/models.py`
- Frontend: `/app/frontend/app/index.tsx`
- Frontend supervisor: `npx expo start --web --port 3000 --non-interactive`

## API Response Fields (matching_info for gamma)
- `resonant_freq_mhz`: gamma bar-shifted resonant frequency
- `element_resonant_freq_mhz`: element-length-based natural resonant frequency
- `q_factor`: from rod insertion depth
- `gamma_bandwidth_mhz`: BW = operating_freq / Q

## Prioritized Backlog
### P2
- PayPal/CashApp payments
- `.easignore` optimization for smaller APK builds
- Replace deprecated `shadow*` style props with `boxShadow`
### P3
- iOS build

## Notes
- User VM path: ~/sma2026-1
- User is removing the Vite website themselves
- Expo Web requires Pressable (not TouchableOpacity) for reliable click handling
- Metro CI mode: restart frontend after code changes
