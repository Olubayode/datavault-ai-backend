from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.files import router as files_router
from app.routers.product_analytics import router as product_analytics_router
from app.routers.projects import router as projects_router
from app.services.store import init_db


init_db()

app = FastAPI(title="Datavault AI Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "Datavault AI Analytics API",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "analytics": "/analytics/ask",
        "workspace": "/workspace-analytics/ask",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(files_router)
app.include_router(product_analytics_router)
app.include_router(analytics_router)
