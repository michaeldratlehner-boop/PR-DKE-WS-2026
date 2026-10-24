from fastapi import FastAPI

from app.routers import produktfinder


app = FastAPI(title="Waschmaschinen-Harness")


app.include_router(produktfinder.router)


@app.get("/health")
def health():
    return {"status": "ok"}