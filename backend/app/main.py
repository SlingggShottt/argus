"""FastAPI application entrypoint. Run with:
uvicorn app.main:app --reload (from backend/), per CLAUDE.md's Commands."""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Argus API", version="0.1.0")

# Dev-friendly default matching Vite's default port (Phase 8 frontend).
# Not a business tunable -- deployment topology, wired here directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
