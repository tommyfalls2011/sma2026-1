# 📱 Play Store & Mobile Distribution Guide

## SMA Antenna Analyzer App - Publishing Instructions

---

## Option 1: PWA (Progressive Web App) - FREE & INSTANT ✅

Your app already supports PWA installation! Users can install it directly from the web.

### For Android Users:
1. Open your deployed app URL in **Chrome**
2. Tap the **menu (⋮)** button
3. Select **"Add to Home Screen"** or **"Install App"**
4. The app will appear as an icon on their home screen

### For iPhone Users:
1. Open your deployed app URL in **Safari**
2. Tap the **Share** button (square with arrow)
3. Scroll down and tap **"Add to Home Screen"**
4. The app will appear as an icon on their home screen

### Benefits:
- ✅ No app store approval needed
- ✅ Instant updates (no store review delays)
- ✅ Works offline once installed
- ✅ Full screen experience (no browser bars)
- ✅ FREE - no developer fees

---

## Option 2: Google Play Store - NATIVE APP

### Step 1: Create Google Play Developer Account
1. Go to: https://play.google.com/console/
2. Sign in with your Google account
3. Pay the **$25 one-time registration fee**
4. Complete account setup (verify identity)

### Step 2: Prepare App Assets

You'll need these files ready:

#### Required Images (Already Created! ✅):
| Asset | Size | Status |
|-------|------|--------|
| App Icon | 512x512 px | ✅ Created |
| Adaptive Icon | 432x432 px | ✅ Created |
| Favicon | 32x32 px | ✅ Created |
| Feature Graphic | 1024x500 px | Need to create |
| Screenshots (min 2) | varies | Take from app |

#### App Information:
- **App Name**: SMA Antenna Analyzer
- **Short Description** (80 chars max): 
  ```
  Professional antenna design & SWR calculator for ham radio operators
  ```
- **Full Description** (4000 chars max): 
  ```
  SMA Antenna Analyzer is the ultimate tool for ham radio operators and antenna enthusiasts.
  
  🎯 FEATURES:
  • Calculate SWR, gain, and front-to-back ratio
  • Visualize radiation patterns with polar plots
  • Optimize antenna height for best performance
  • Design Yagi-Uda antennas with up to 20 elements
  • Auto-tune element dimensions
  • Support for multiple bands (CB, 10m, 12m, 15m, 17m, 20m)
  • Ground radial system simulation
  • Take-off angle analysis for DX optimization
  • Side-view elevation pattern visualization
  • Save and load antenna designs
  • Export results to CSV
  • Boom lock and spacing lock for precise tuning
  
  📡 PERFECT FOR:
  • Amateur radio operators (hams)
  • CB radio enthusiasts  
  • Antenna builders and experimenters
  • RF engineers
  • Anyone interested in radio communications
  
  🔧 ADVANCED FEATURES:
  • Element tapering support
  • Corona ball configuration
  • Stacking calculations
  • Height optimization from 10-100 feet
  • Real-time calculations
  
  💎 SUBSCRIPTION TIERS:
  • Trial: 3 elements (free)
  • Bronze: 7 elements
  • Silver: 11 elements
  • Gold: 20 elements
  
  Built with precision and accuracy for professional antenna analysis.
  ```

### Step 3: Build the Production APK/AAB

Run these commands on your local machine:

```bash
# 1. Install EAS CLI globally
npm install -g eas-cli

# 2. Login to Expo account
eas login

# 3. Navigate to frontend folder
cd frontend

# 4. Configure EAS (first time only)
eas build:configure

# 5. Build for Play Store (AAB format)
eas build --platform android --profile production

# 6. Or build APK for testing
eas build --platform android --profile preview
```

### Step 4: Upload to Play Store

1. Go to **Google Play Console**: https://play.google.com/console/
2. Click **"Create app"**
3. Fill in app details:
   - App name: **SMA Antenna Analyzer**
   - Default language: English (United States)
   - App or game: **App**
   - Free or paid: **Free** (with in-app purchases for subscriptions)
   - Category: **Tools**
   - Tags: Radio, Amateur Radio, Antenna, Calculator, Ham Radio

4. **Store Listing**:
   - Upload app icon (512x512)
   - Upload feature graphic (1024x500)
   - Add 2-8 screenshots
   - Write short and full descriptions

5. **Content Rating**:
   - Complete questionnaire
   - Answer: No violence, no data collection beyond basic

6. **Data Safety**:
   - Data collected: Email (for account)
   - Data shared: None
   - Security: Data encrypted in transit

7. **Pricing & Distribution**:
   - Free app
   - Available in all countries

8. **Release**:
   - Upload your AAB file
   - Create release
   - Submit for review

### Step 5: Wait for Approval
- Initial review: **3-7 days**
- Updates review: **1-3 days**

---

## Option 3: Direct APK Distribution

For private distribution without the Play Store:

1. Build an APK:
   ```bash
   eas build --platform android --profile preview
   ```

2. Download the APK file from Expo dashboard

3. Share via:
   - Email attachment
   - Website download link
   - QR code to download URL
   - Google Drive/Dropbox link

4. Users install by:
   - Enabling "Install from unknown sources" in Android settings
   - Opening the APK file

---

## Current App Configuration

Your `app.json` is configured with:

```json
{
  "name": "SMA Antenna Analyzer",
  "android": {
    "package": "com.smaantennaanalyzer.app",
    "versionCode": 1,
    "permissions": [
      "android.permission.INTERNET",
      "android.permission.ACCESS_NETWORK_STATE"
    ]
  }
}
```

---

## Checklist Before Publishing

### Already Done ✅
- [x] App icon (512x512) created
- [x] Adaptive icon created
- [x] Favicon created
- [x] Splash icon created
- [x] App.json configured
- [x] EAS.json build config created
- [x] Package name set (com.smaantennaanalyzer.app)

### You Need To Do 📋
- [ ] Create Google Play Developer account ($25)
- [ ] Create feature graphic (1024x500)
- [ ] Take 2-8 app screenshots
- [ ] Run `eas build` command
- [ ] Upload to Play Console
- [ ] Complete content rating
- [ ] Complete data safety form
- [ ] Submit for review

---

## Creating Feature Graphic & Screenshots

### Feature Graphic (1024x500):
- Use Canva, Figma, or Photoshop
- Include: App name, antenna graphic, tagline
- Colors: Dark background (#121212), green accents (#4CAF50)
- Text: "SMA Antenna Analyzer" + "Professional Ham Radio Tool"

### Screenshots:
Take screenshots of these screens:
1. Main calculator with results
2. Radiation pattern polar plot
3. Height optimizer results
4. Saved designs list
5. Admin panel (optional)
6. Subscription page

Use a phone or emulator at 1080x1920 resolution.

---

## Quick Reference URLs

- **Google Play Console**: https://play.google.com/console/
- **Expo EAS Build Docs**: https://docs.expo.dev/build/introduction/
- **Expo Account Signup**: https://expo.dev/signup
- **Play Store Asset Requirements**: https://support.google.com/googleplay/android-developer/answer/9866151

---

## Support

For questions about:
- **Building**: Check Expo documentation
- **Play Store policies**: Google Play Console Help Center
- **App features**: Contact developer

🚀 Good luck with your Play Store launch!
