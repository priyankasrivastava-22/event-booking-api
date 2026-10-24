import os
from dotenv import load_dotenv
from pathlib import Path
# Work whether PyCharm starts from the repository root or event-booking-api/.
API_DIR = Path(__file__).resolve().parent
PROJECT_DIR = API_DIR.parent
load_dotenv(API_DIR / ".env")
load_dotenv(PROJECT_DIR / ".env")
from fastapi.middleware.cors import CORSMiddleware
from utils.helpers import get_db
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from core.limiter import limiter
from models import User
from database import SessionLocal
from sqlalchemy.orm import Session
from fastapi import Depends
from sqlalchemy import text
from database import engine
import models

from routers import (auth,events,bookings,admin,analytics,engagement,profile,payment,seating,inventory)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500,http://localhost:63342,http://127.0.0.1:63342").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter                                                                                              # RATE LIMITING
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(StarletteHTTPException)                                                                           # GLOBAL ERROR HANDLER
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail,  # frontend booking/login screens read the standard FastAPI key
            "error": exc.detail,   # retained for older clients
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Please check the submitted fields.",
            "errors": [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "Internal server error",
            "error": "Internal server error"
        }
    )

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "detail": "Too many requests. Try again later.",
            "error": "Too many requests. Try again later."
        }
    )

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])                                                       # ROUTERS
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(engagement.router, prefix="/api/engagement", tags=["Engagement"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(payment.router, prefix="/api/payment", tags=["Payment"])
app.include_router(seating.router, prefix="/api/seating", tags=["Seating"])
app.include_router(inventory.router)                                                                     # PREFIX/TAGS ALREADY SET ON THE ROUTER ITSELF

@app.get("/login")
async def login_page():
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:63342/Event%20Booking/frontend")
    return RedirectResponse(f"{frontend_url}/pages/login.html")

@app.get("/")
async def root():
    return {
        "message": "Event Booking API is running!",
        "docs": "/docs",
        "status": "success"
    }

@app.get("/api/config/public", tags=["Configuration"])
def public_config():
    """Only return public feature flags; never leak provider keys or DATABASE_URL."""
    demo_enabled = os.getenv("ENABLE_MOCK_PAYMENTS", "false").lower() == "true"
    return {"checkout_mode": "demo" if demo_enabled else "disabled",
            "payment_methods": ["mock"] if demo_enabled else []}

@app.get("/warmup")
@app.head("/warmup")
def warmup(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "awake"}