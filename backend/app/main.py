from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.analytics import router as analytics_router


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
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(analytics_router)
