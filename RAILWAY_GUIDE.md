# 🚂 Railway Deployment Guide for SMA Antenna Analyzer

## Step-by-Step Instructions

---

## Step 1: Create Railway Account

1. Go to **https://railway.app**
2. Click **"Start a New Project"** or **"Login"**
3. Sign up with **GitHub** (recommended) or email

---

## Step 2: Push Code to GitHub

### From Emergent:
1. Click your **profile icon** (top right)
2. Click **"Connect GitHub"** if not connected
3. Click **"Push to GitHub"**
4. Create a new repository named `sma-antenna-analyzer`

---

## Step 3: Create MongoDB Database on Railway

1. In Railway dashboard, click **"New Project"**
2. Click **"Add a Service"**
3. Select **"Database"** → **"MongoDB"**
4. Wait for it to provision (1-2 minutes)
5. Click on the MongoDB service
6. Go to **"Variables"** tab
7. Copy the **`MONGO_URL`** value (looks like `mongodb://...`)

---

## Step 4: Deploy Backend to Railway

1. In the same project, click **"Add a Service"**
2. Select **"GitHub Repo"**
3. Choose your `sma-antenna-analyzer` repository
4. Railway will detect it's a Python app

### Configure Environment Variables:
1. Click on your backend service
2. Go to **"Variables"** tab
3. Add these variables:

| Variable | Value |
|----------|-------|
| `MONGO_URL` | (paste the MongoDB URL from Step 3) |
| `JWT_SECRET` | `your-super-secret-key-change-this` |
| `ADMIN_EMAIL` | `fallstommy@gmail.com` |

4. Click **"Deploy"**

---

## Step 5: Configure Root Directory (Important!)

Since your backend is in `/backend` folder:

1. Click on your service
2. Go to **"Settings"** tab
3. Find **"Root Directory"**
4. Set it to: `backend`
5. Redeploy

---

## Step 6: Get Your Public URL

1. Click on your backend service
2. Go to **"Settings"** tab
3. Scroll to **"Networking"**
4. Click **"Generate Domain"**
5. You'll get a URL like: `sma-antenna-analyzer-production.up.railway.app`

---

## Step 7: Test Your Backend

Open this in your browser (replace with your URL):
```
https://YOUR-URL.up.railway.app/api/subscription/tiers
```

If you see JSON data, it's working! ✅

---

## Step 8: Update Your App

### Update the `.env` file in frontend:
```
EXPO_PUBLIC_BACKEND_URL=https://YOUR-URL.up.railway.app
```

### Rebuild your APK:
```cmd
cd C:\your-project\frontend
eas build --platform android --profile preview --clear-cache
```

---

## Troubleshooting

### Error: "No start command"
Make sure `railway.json` exists in your root folder with:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT"
  }
}
```

### Error: "Module not found"
Check that `requirements.txt` is in the `backend` folder.

### Error: "MongoDB connection failed"
- Verify MONGO_URL is set correctly in Variables
- Make sure there are no extra spaces

### App not starting?
1. Go to your service → **"Deployments"** tab
2. Click on the failed deployment
3. Check the **"Build Logs"** and **"Deploy Logs"**
4. Share the error message

---

## Cost

Railway's free tier includes:
- **$5 free credit/month**
- Usually enough for small apps
- Pay as you go after that (~$5-20/month)

---

## Quick Reference

| What | Where |
|------|-------|
| Railway Dashboard | https://railway.app/dashboard |
| Your MongoDB URL | Railway → MongoDB service → Variables |
| Your Backend URL | Railway → Backend service → Settings → Domains |
| Deploy Logs | Railway → Service → Deployments |

---

## Need Help?

Share the error message from Railway's deployment logs and I'll help you fix it!
