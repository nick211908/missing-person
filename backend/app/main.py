from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.api import routes_missing, routes_stream, routes_detection
from app.auth.routes_auth import router as auth_router
from app.database.db import init_db
import app.models.user  # noqa: F401 — ensures users table is created by init_db

app = FastAPI(
    title="Missing Person Detection MVP",
    description="AI-powered CCTV face detection system for finding missing persons.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

# Mount static files for serving images
os.makedirs("data/missing_persons", exist_ok=True)
app.mount("/images", StaticFiles(directory="data/missing_persons"), name="images")

# Public routes
app.include_router(auth_router)

# Protected routes (require JWT token)
app.include_router(routes_missing.router, tags=["Missing Persons"])
app.include_router(routes_stream.router, tags=["Stream Processing"])
app.include_router(routes_detection.router, tags=["Detections"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
