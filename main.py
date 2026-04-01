from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

VERSION = "0.1.0"

app = FastAPI(title="Weefin API", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3001").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers.terminal import router as terminal_router
app.include_router(terminal_router)

from routers.watchlist import router as watchlist_router
app.include_router(watchlist_router)

@app.get("/health")
async def health():
    return {"status": "ok", "version": VERSION}
