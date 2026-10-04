import os
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from app.bot.engine import bot_engine
from app.config import SCREENSHOTS_DIR, settings

router = APIRouter()

class BotSettingsSchema(BaseModel):
    check_interval: Optional[int] = None
    headless: Optional[bool] = None
    human_delay_min: Optional[float] = None
    human_delay_max: Optional[float] = None
    max_dm_per_hour: Optional[int] = None

@router.get("/status")
async def get_status():
    """Mengambil status real-time dari bot TikTok."""
    state = await bot_engine.get_state()
    return {"status": "success", "data": state}

@router.post("/start")
async def start_bot():
    """Menjalankan bot auto DM TikTok."""
    if bot_engine.is_running:
        return {"status": "info", "message": "Bot sudah berjalan"}
    await bot_engine.start()
    return {"status": "success", "message": "Bot sedang dimulai"}

@router.post("/stop")
async def stop_bot():
    """Menghentikan bot auto DM TikTok."""
    if not bot_engine.is_running:
        return {"status": "info", "message": "Bot sudah dalam keadaan berhenti"}
    await bot_engine.stop()
    return {"status": "success", "message": "Bot berhasil dihentikan"}

@router.post("/restart")
async def restart_bot():
    """Memulai ulang bot TikTok."""
    await bot_engine.stop()
    await bot_engine.start()
    return {"status": "success", "message": "Bot berhasil direstart"}

@router.get("/screenshot")
async def get_screenshot():
    """Mengambil tampilan layar browser terkini (untuk scan QR login & monitoring)."""
    screenshot_file = SCREENSHOTS_DIR / "live.png"
    if not screenshot_file.exists():
        # Return a simple 1x1 transparent png or 404
        raise HTTPException(status_code=404, detail="Screenshot belum tersedia. Nyalakan bot terlebih dahulu.")
    return FileResponse(
        path=str(screenshot_file),
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@router.post("/screenshot/capture")
async def capture_screenshot():
    """Memicu tangkapan layar langsung secara instan."""
    path = await bot_engine.capture_screenshot()
    if not path:
        raise HTTPException(status_code=400, detail="Tidak dapat menangkap screenshot (bot tidak aktif atau browser belum terbuka).")
    return {"status": "success", "message": "Screenshot berhasil diperbarui"}

@router.post("/settings")
async def update_settings(cfg: BotSettingsSchema):
    """Mengubah pengaturan operasional bot."""
    if cfg.check_interval is not None:
        settings.check_interval = max(5, cfg.check_interval)
    if cfg.headless is not None:
        settings.headless = cfg.headless
    if cfg.human_delay_min is not None:
        settings.human_delay_min = cfg.human_delay_min
    if cfg.human_delay_max is not None:
        settings.human_delay_max = cfg.human_delay_max
    if cfg.max_dm_per_hour is not None:
        settings.max_dm_per_hour = cfg.max_dm_per_hour

    return {
        "status": "success",
        "message": "Pengaturan berhasil diperbarui",
        "settings": {
            "check_interval": settings.check_interval,
            "headless": settings.headless,
            "human_delay_min": settings.human_delay_min,
            "human_delay_max": settings.human_delay_max,
            "max_dm_per_hour": settings.max_dm_per_hour
        }
    }
