from dotenv import load_dotenv
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

from core.limiter import limiter
from models import User
from database import SessionLocal
from sqlalchemy.orm import Session
from fastapi import Depends

from database import engine
import models

from routers import (
    auth,
    events,
    bookings,
    admin,
    analytics,
    engagement,
    profile,
    payment
)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- RATE LIMITING ----------------
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ---------------- GLOBAL ERROR HANDLER ----------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc.errors())
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error"
        }
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "Too many requests. Try again later."
        }
    )


# ---------------- DATABASE ----------------
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/debug/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "username": u.username,
            "password": u.password
        }
        for u in users
    ]

# ---------------- ROUTERS ----------------
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(bookings.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(engagement.router)
app.include_router(profile.router)
app.include_router(payment.router)