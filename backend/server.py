"""SMA Antenna Calculator API - Slim entry point.

All logic is in modular files:
  config.py          - DB, env, constants
  models.py          - Pydantic models
  auth.py            - Auth helpers
  services/physics.py - Antenna physics engine
  services/email_service.py - Email helpers
  routes/antenna.py  - Calculate, auto-tune, optimize
  routes/user.py     - Auth, subscription, designs
  routes/admin.py    - Admin endpoints
  routes/public.py   - Public endpoints
"""
import logging
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from config import client, load_settings_from_db
from routes.antenna import router as antenna_router
from routes.user import router as user_router
from routes.admin import router as admin_router
from routes.public import router as public_router

app = FastAPI(title="SMA Antenna Calculator API")

api_router = APIRouter(prefix="/api")
api_router.include_router(public_router)
api_router.include_router(antenna_router)
api_router.include_router(user_router)
api_router.include_router(admin_router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@app.on_event("startup")
async def startup_load_settings():
    await load_settings_from_db()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
