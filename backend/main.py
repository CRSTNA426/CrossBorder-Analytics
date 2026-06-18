"""FastAPI application entry point."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import platforms, metrics, dashboards, data, upload, insights

# Path to frontend directory
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

app = FastAPI(
    title="CrossBorder Analytics",
    description="Multi-platform cross-border e-commerce operations dashboard",
    version="1.0.0",
)

# CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(platforms.router)
app.include_router(metrics.router)
app.include_router(dashboards.router)
app.include_router(data.router)
app.include_router(upload.router)
app.include_router(insights.router)

# Serve frontend static files
if os.path.isdir(FRONTEND_DIR):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    def root():
        return {
            "app": "CrossBorder Analytics API",
            "version": "1.0.0",
            "docs": "/docs",
        }
