cd C:\sma2026-1\frontend\frontend
Write-Host "Pulling latest from GitHub..." -ForegroundColor Green
git fetch origin main
git reset --hard origin/main
Write-Host "Installing dependencies..." -ForegroundColor Green
npm install --legacy-peer-deps
Write-Host "Starting build..." -ForegroundColor Green
npx eas build --platform android --profile preview --clear-cache