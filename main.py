import os
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import settings, BASE_DIR
from app.database import init_db
from app.api import api_router
from app.bot.engine import bot_engine

import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite database
    await init_db()
    print("=" * 60)
    print(f"[*] {settings.app_name} v{settings.version} Started!")
    print(f"[*] Dashboard URL: http://localhost:{settings.port}")
    if settings.auto_start:
        print("[*] Auto-Start: Memulai bot otomatis di latar belakang...")
        await bot_engine.start()
    print("=" * 60)
    yield
    # Shutdown: Stop bot background worker and clean up browser
    await bot_engine.stop()
    print("[*] Bot and server shutdown completed.")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="TikTok Auto DM Pro - 24/7 Keyword Triggered Auto Responder",
    lifespan=lifespan
)

# Mount Static Assets & Templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

# Mount API Endpoints
app.include_router(api_router)

# Main Dashboard View
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": settings.app_name}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )
