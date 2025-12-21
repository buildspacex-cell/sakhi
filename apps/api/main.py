from fastapi import FastAPI

from routes import presence, tone

app = FastAPI(title="Sakhi API (apps/api root)")


@app.get("/health")
def health():
    return {"status": "ok"}


# Optional: lightweight stubs for existing endpoints
app.include_router(presence.router)
app.include_router(tone.router)
