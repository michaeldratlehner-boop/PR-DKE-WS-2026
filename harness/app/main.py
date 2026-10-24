from fastapi import FastAPI

app = FastAPI(title="Waschmaschinen-Harness")


@app.get("/health")
def health():
    return {"status": "ok"}