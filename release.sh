#!/bin/bash
#
# release.sh — Automates the full SMA Antenna Analyzer release workflow
#
# Usage:
#   ./release.sh <path-to-apk>
#
# What it does:
#   1. Reads version from app.json
#   2. Uploads APK to GitHub Releases
#   3. Updates production backend /api/app-update
#   4. Updates GitHub Gist fallback
#
# Prerequisites:
#   - GITHUB_TOKEN env variable set (or saved in ~/.sma_release_token)
#   - jq installed (sudo apt install jq)
#   - curl installed
#

set -e

# ── Config ──
REPO="tommyfalls2011/sma2026-1"
GIST_ID="3bb5c9e586bfa929d26da16776b0b9c6"
BACKEND_URL="https://helpful-adaptation-production.up.railway.app"
APP_JSON="$(dirname "$0")/frontend/app.json"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() { echo -e "\n${CYAN}[$1/4]${NC} $2"; }
print_ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
print_fail() { echo -e "  ${RED}✗${NC} $1"; }
print_warn() { echo -e "  ${YELLOW}!${NC} $1"; }

# ── Validate inputs ──
if [ -z "$1" ]; then
    echo -e "${RED}Usage: ./release.sh <path-to-apk>${NC}"
    echo ""
    echo "Example:"
    echo "  ./release.sh ./build-1234567890.apk"
    echo "  ./release.sh ~/sma2026-1/frontend/build-*.apk"
    exit 1
fi

APK_PATH="$1"
if [ ! -f "$APK_PATH" ]; then
    echo -e "${RED}Error: APK file not found: ${APK_PATH}${NC}"
    exit 1
fi

APK_FILENAME=$(basename "$APK_PATH")
APK_SIZE=$(du -h "$APK_PATH" | cut -f1)

# ── Read version from app.json ──
if [ ! -f "$APP_JSON" ]; then
    echo -e "${RED}Error: app.json not found at ${APP_JSON}${NC}"
    echo "Run this script from the project root directory."
    exit 1
fi

VERSION=$(python3 -c "import json; print(json.load(open('$APP_JSON'))['expo']['version'])")
VERSION_CODE=$(python3 -c "import json; print(json.load(open('$APP_JSON'))['expo']['android']['versionCode'])")
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%S")

echo -e "\n${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SMA Antenna Analyzer — Release Tool    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Version:      ${GREEN}v${VERSION}${NC} (code ${VERSION_CODE})"
echo -e "  APK:          ${APK_FILENAME} (${APK_SIZE})"
echo -e "  Build Date:   ${BUILD_DATE}"
echo -e "  Repo:         ${REPO}"

# ── Load GitHub token ──
if [ -z "$GITHUB_TOKEN" ]; then
    TOKEN_FILE="$HOME/.sma_release_token"
    if [ -f "$TOKEN_FILE" ]; then
        GITHUB_TOKEN=$(cat "$TOKEN_FILE" | tr -d '[:space:]')
        print_ok "Loaded token from ~/.sma_release_token"
    else
        echo ""
        echo -e "${YELLOW}No GITHUB_TOKEN found.${NC}"
        echo -e "Either export it:  ${CYAN}export GITHUB_TOKEN=ghp_xxxxx${NC}"
        echo -e "Or save it once:   ${CYAN}echo 'ghp_xxxxx' > ~/.sma_release_token && chmod 600 ~/.sma_release_token${NC}"
        exit 1
    fi
fi

echo ""
read -p "Ready to release v${VERSION}? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# ── Step 1: Create GitHub Release ──
print_step 1 "Creating GitHub Release v${VERSION}..."

RELEASE_NOTES="v${VERSION} - SMA Antenna Analyzer update (build ${VERSION_CODE})"

RELEASE_RESPONSE=$(curl -s -X POST \
    "https://api.github.com/repos/${REPO}/releases" \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"tag_name\": \"v${VERSION}\",
        \"name\": \"v${VERSION}\",
        \"body\": \"${RELEASE_NOTES}\",
        \"draft\": false,
        \"prerelease\": false
    }")

RELEASE_ID=$(echo "$RELEASE_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)

if [ -z "$RELEASE_ID" ] || [ "$RELEASE_ID" = "" ]; then
    # Maybe the tag already exists — try to find it
    print_warn "Release may already exist, looking for existing tag..."
    RELEASE_RESPONSE=$(curl -s "https://api.github.com/repos/${REPO}/releases/tags/v${VERSION}" \
        -H "Authorization: token ${GITHUB_TOKEN}")
    RELEASE_ID=$(echo "$RELEASE_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)
    
    if [ -z "$RELEASE_ID" ] || [ "$RELEASE_ID" = "" ]; then
        print_fail "Failed to create/find GitHub release"
        echo "$RELEASE_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','Unknown error'))" 2>/dev/null
        exit 1
    fi
    print_ok "Found existing release (ID: ${RELEASE_ID})"
    # Delete existing assets with same filename to allow re-upload
    print_warn "Checking for existing assets to replace..."
    EXISTING_ASSETS=$(curl -s "https://api.github.com/repos/${REPO}/releases/${RELEASE_ID}/assets" \
        -H "Authorization: token ${GITHUB_TOKEN}")
    # Find and delete any asset matching our APK filename
    ASSET_IDS=$(echo "$EXISTING_ASSETS" | python3 -c "
import sys, json
try:
    assets = json.load(sys.stdin)
    for a in assets:
        if a.get('name') == '${APK_FILENAME}':
            print(a['id'])
except: pass
" 2>/dev/null)
    for AID in $ASSET_IDS; do
        curl -s -X DELETE "https://api.github.com/repos/${REPO}/releases/assets/${AID}" \
            -H "Authorization: token ${GITHUB_TOKEN}" > /dev/null
        print_ok "Deleted existing asset (ID: ${AID})"
    done
else
    print_ok "Created release (ID: ${RELEASE_ID})"
fi

# ── Step 2: Upload APK to Release ──
print_step 2 "Uploading APK (${APK_SIZE})..."

UPLOAD_RESPONSE=$(curl -s -X POST \
    "https://uploads.github.com/repos/${REPO}/releases/${RELEASE_ID}/assets?name=${APK_FILENAME}" \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Content-Type: application/vnd.android.package-archive" \
    --data-binary "@${APK_PATH}")

APK_URL=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('browser_download_url',''))" 2>/dev/null)

if [ -z "$APK_URL" ] || [ "$APK_URL" = "" ]; then
    print_fail "Failed to upload APK"
    echo "$UPLOAD_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('errors',[{'message':'Unknown error'}])[0].get('message',''))" 2>/dev/null
    # Try constructing the URL manually
    APK_URL="https://github.com/${REPO}/releases/download/v${VERSION}/${APK_FILENAME}"
    print_warn "Using constructed URL: ${APK_URL}"
else
    print_ok "Uploaded: ${APK_URL}"
fi

# ── Step 3: Update Production Backend ──
print_step 3 "Updating production backend..."

BACKEND_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/app-update" \
    -H "Content-Type: application/json" \
    -d "{
        \"version\": \"${VERSION}\",
        \"buildDate\": \"${BUILD_DATE}\",
        \"releaseNotes\": \"${RELEASE_NOTES}\",
        \"apkUrl\": \"${APK_URL}\",
        \"forceUpdate\": false
    }")

BACKEND_STATUS=$(echo "$BACKEND_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','fail'))" 2>/dev/null)

if [ "$BACKEND_STATUS" = "ok" ]; then
    print_ok "Backend updated"
else
    print_fail "Backend update failed: ${BACKEND_RESPONSE}"
fi

# ── Step 4: Update Gist Fallback ──
print_step 4 "Updating Gist fallback..."

GIST_CONTENT=$(python3 -c "
import json
d = {
    'version': '${VERSION}',
    'buildDate': '${BUILD_DATE}',
    'releaseNotes': '${RELEASE_NOTES}',
    'apkUrl': '${APK_URL}',
    'forceUpdate': False
}
# Escape for JSON embedding
print(json.dumps(json.dumps(d)))
")

GIST_RESPONSE=$(curl -s -X PATCH \
    "https://api.github.com/gists/${GIST_ID}" \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"files\":{\"update.json\":{\"content\":${GIST_CONTENT}}}}")

GIST_URL=$(echo "$GIST_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('html_url',''))" 2>/dev/null)

if [ -n "$GIST_URL" ] && [ "$GIST_URL" != "" ]; then
    print_ok "Gist updated: ${GIST_URL}"
else
    print_warn "Gist update may have failed (non-critical — backend is primary)"
fi

# ── Done ──
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Release v${VERSION} Complete!          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  APK:      ${APK_URL}"
echo -e "  Backend:  ${BACKEND_URL}/api/app-update"
echo -e "  Gist:     https://gist.github.com/${GIST_ID}"
echo ""
echo -e "  Users will see the update prompt on next app launch."
echo ""
