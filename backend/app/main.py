from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import os
from app.api import routes_missing, routes_stream, routes_detection, routes_phone_camera
from app.auth.routes_auth import router as auth_router
from app.database.db import init_db
from app.services.phone_camera_service import phone_camera_service
import app.models.user  # noqa: F401 — ensures users table is created by init_db


async def cleanup_stale_sessions():
    """Background task to clean up stale phone camera sessions."""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            cleaned = phone_camera_service.cleanup_stale_sessions(max_idle_seconds=300)
            if cleaned > 0:
                print(f"Cleaned up {cleaned} stale phone camera sessions")
        except Exception as e:
            print(f"Error in cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting background tasks...")
    cleanup_task = asyncio.create_task(cleanup_stale_sessions())
    yield
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Missing Person Detection MVP",
    description="AI-powered CCTV face detection system for finding missing persons.",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(routes_phone_camera.router, tags=["Phone Camera"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
