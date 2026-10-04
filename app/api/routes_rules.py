import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.database import (
    get_all_rules,
    get_active_rules,
    get_rule_by_id,
    create_rule,
    update_rule,
    delete_rule,
    toggle_rule_status
)

router = APIRouter()

class RuleSchema(BaseModel):
    keyword: str = Field(..., min_length=1, description="Kata kunci pemicu auto DM")
    match_type: str = Field("contains", description="'contains', 'exact', 'starts_with', or 'regex'")
    reply_message: str = Field(..., min_length=1, description="Template pesan balasan DM ({username} dapat digunakan)")
    cooldown_seconds: int = Field(3600, ge=0, description="Cooldown dalam detik sebelum membalas user yang sama lagi")
    is_active: int = Field(1, description="1 untuk aktif, 0 untuk non-aktif")

class RuleUpdateSchema(BaseModel):
    keyword: str
    match_type: str
    reply_message: str
    cooldown_seconds: int
    is_active: int

class TestMessageSchema(BaseModel):
    message: str
    username: Optional[str] = "calon_customer"

@router.get("/")
async def list_rules():
    """Mengambil semua daftar keyword dan pesan balasan."""
    rules = await get_all_rules()
    return {"status": "success", "rules": rules}

@router.post("/")
async def add_rule(rule: RuleSchema):
    """Menambahkan keyword dan pesan auto DM baru."""
    if rule.match_type not in ["contains", "exact", "starts_with", "regex"]:
        raise HTTPException(status_code=400, detail="Match type tidak valid (harus contains, exact, starts_with, atau regex)")
    
    rule_id = await create_rule(
        keyword=rule.keyword,
        match_type=rule.match_type,
        reply_message=rule.reply_message,
        cooldown_seconds=rule.cooldown_seconds,
        is_active=rule.is_active
    )
    return {"status": "success", "message": "Aturan berhasil disimpan", "rule_id": rule_id}

@router.put("/{rule_id}")
async def edit_rule(rule_id: int, rule: RuleUpdateSchema):
    """Mengubah keyword atau pesan auto DM yang sudah ada."""
    existing = await get_rule_by_id(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Aturan tidak ditemukan")
    
    success = await update_rule(
        rule_id=rule_id,
        keyword=rule.keyword,
        match_type=rule.match_type,
        reply_message=rule.reply_message,
        cooldown_seconds=rule.cooldown_seconds,
        is_active=rule.is_active
    )
    return {"status": "success", "updated": success}

@router.delete("/{rule_id}")
async def remove_rule(rule_id: int):
    """Menghapus keyword auto DM."""
    success = await delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Aturan tidak ditemukan")
    return {"status": "success", "message": "Aturan berhasil dihapus"}

@router.post("/{rule_id}/toggle")
async def toggle_rule(rule_id: int):
    """Mengaktifkan atau menonaktifkan keyword auto DM."""
    new_status = await toggle_rule_status(rule_id)
    if new_status is None:
        raise HTTPException(status_code=404, detail="Aturan tidak ditemukan")
    return {"status": "success", "is_active": new_status}

@router.post("/test")
async def test_rule_matching(payload: TestMessageSchema):
    """Sandbox simulator untuk menguji pesan masuk terhadap keyword tanpa perlu menjalankan bot."""
    active_rules = await get_active_rules()
    msg = payload.message.strip().lower()
    uname = payload.username or "Pengguna"

    for rule in active_rules:
        kw = rule["keyword"].strip().lower()
        mtype = rule.get("match_type", "contains").lower()
        matched = False

        if mtype == "contains" and kw in msg:
            matched = True
        elif mtype == "exact" and kw == msg:
            matched = True
        elif mtype == "starts_with" and msg.startswith(kw):
            matched = True
        elif mtype == "regex":
            try:
                if re.search(kw, payload.message, re.IGNORECASE):
                    matched = True
            except Exception as e:
                return {"status": "error", "message": f"Regex error: {e}"}

        if matched:
            formatted_reply = rule["reply_message"].replace("{username}", uname)
            return {
                "status": "matched",
                "matched_rule": rule,
                "input_message": payload.message,
                "simulated_reply": formatted_reply
            }

    return {
        "status": "no_match",
        "message": "Tidak ada keyword aktif yang cocok dengan pesan ini.",
        "input_message": payload.message
    }
