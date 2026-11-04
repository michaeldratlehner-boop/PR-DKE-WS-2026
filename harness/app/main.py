from fastapi import FastAPI

from app.routers import produktfinder, chat

app = FastAPI(title="Waschmaschinen-Harness")


app.include_router(produktfinder.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}