from fastapi import APIRouter
from app.database import get_recent_logs, clear_logs, get_dashboard_stats

router = APIRouter()

@router.get("/")
async def list_logs(limit: int = 50):
    """Mengambil riwayat log aktivitas balasan DM."""
    logs = await get_recent_logs(limit=limit)
    return {"status": "success", "logs": logs}

@router.delete("/")
async def reset_logs():
    """Membersihkan riwayat log aktivitas."""
    await clear_logs()
    return {"status": "success", "message": "Log aktivitas berhasil dibersihkan"}

@router.get("/stats")
async def dashboard_stats():
    """Mengambil ringkasan statistik bot."""
    stats = await get_dashboard_stats()
    return {"status": "success", "stats": stats}
