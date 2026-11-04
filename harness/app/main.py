from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import produktfinder


app = FastAPI(title="Waschmaschinen-Harness")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(produktfinder.router)


@app.get("/health")
def health():
    return {"status": "ok"}