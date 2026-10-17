from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config import CORS_ORIGINS
from routers import benefits

app = FastAPI(title="Civis API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
# The income what-if response repeats program ids at every income point.
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(benefits.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
