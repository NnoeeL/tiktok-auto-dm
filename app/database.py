import aiosqlite
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.config import DB_PATH

@asynccontextmanager
async def get_db():
    """Async context manager for SQLite database connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    async with get_db() as db:
        # Rules table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                match_type TEXT DEFAULT 'contains',
                reply_message TEXT NOT NULL,
                cooldown_seconds INTEGER DEFAULT 3600,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Conversations history & cooldown tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_user_id TEXT UNIQUE,
                chat_username TEXT,
                last_message_text TEXT,
                last_replied_rule_id INTEGER,
                last_replied_at TIMESTAMP,
                total_replies INTEGER DEFAULT 0
            )
        """)

        # Message activity logs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_username TEXT,
                incoming_message TEXT,
                matched_keyword TEXT,
                replied_message TEXT,
                status TEXT,
                error_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Runtime settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Insert helpful default rules if table is empty
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM rules")
        row = await cursor.fetchone()
        if row and row["cnt"] == 0:
            default_rules = [
                ("harga", "contains", "Halo {username}! Terima kasih sudah bertanya. Untuk daftar harga dan paket promo lengkap, silakan cek link bio kami ya!", 1800, 1),
                ("order", "contains", "Halo {username}, untuk pemesanan langsung bisa hubungi WhatsApp admin di 0812-xxxx-xxxx atau klik link di bio! Kami siap melayani.", 1800, 1),
                ("promo", "contains", "Hai {username}! Lagi ada diskon spesial 20% khusus minggu ini dengan kode TIKTOK20. Yuk checkout sekarang di bio kami!", 3600, 1),
                ("info", "contains", "Halo {username}! Mau info seputar produk atau layanan apa nih? Kami siap bantu jawab pertanyaanmu!", 3600, 1)
            ]
            for r in default_rules:
                await db.execute(
                    "INSERT INTO rules (keyword, match_type, reply_message, cooldown_seconds, is_active) VALUES (?, ?, ?, ?, ?)",
                    r
                )
        await db.commit()

# --- Rules CRUD Operations ---
async def get_all_rules() -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM rules ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_active_rules() -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM rules WHERE is_active = 1 ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_rule_by_id(rule_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_rule(keyword: str, match_type: str, reply_message: str, cooldown_seconds: int = 3600, is_active: int = 1) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO rules (keyword, match_type, reply_message, cooldown_seconds, is_active) VALUES (?, ?, ?, ?, ?)",
            (keyword.strip().lower(), match_type, reply_message.strip(), cooldown_seconds, is_active)
        )
        await db.commit()
        return cursor.lastrowid

async def update_rule(rule_id: int, keyword: str, match_type: str, reply_message: str, cooldown_seconds: int, is_active: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            """UPDATE rules 
               SET keyword = ?, match_type = ?, reply_message = ?, cooldown_seconds = ?, is_active = ?
               WHERE id = ?""",
            (keyword.strip().lower(), match_type, reply_message.strip(), cooldown_seconds, is_active, rule_id)
        )
        await db.commit()
        return cursor.rowcount > 0

async def delete_rule(rule_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        await db.commit()
        return cursor.rowcount > 0

async def toggle_rule_status(rule_id: int) -> Optional[int]:
    async with get_db() as db:
        cursor = await db.execute("SELECT is_active FROM rules WHERE id = ?", (rule_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        new_status = 0 if row["is_active"] == 1 else 1
        await db.execute("UPDATE rules SET is_active = ? WHERE id = ?", (new_status, rule_id))
        await db.commit()
        return new_status

# --- Conversation & Cooldown Operations ---
async def can_reply_to_user(chat_user_id: str, rule_id: int, cooldown_seconds: int) -> bool:
    """Returns True if the cooldown has elapsed or user has never been replied to with this rule."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT last_replied_at, last_replied_rule_id FROM conversations WHERE chat_user_id = ?",
            (chat_user_id,)
        )
        row = await cursor.fetchone()
        if not row or not row["last_replied_at"]:
            return True
        
        try:
            last_time = datetime.fromisoformat(row["last_replied_at"])
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < cooldown_seconds:
                return False
        except Exception:
            return True
        return True

async def record_reply(chat_user_id: str, chat_username: str, last_message_text: str, rule_id: int):
    async with get_db() as db:
        now_str = datetime.now().isoformat()
        await db.execute(
            """INSERT INTO conversations (chat_user_id, chat_username, last_message_text, last_replied_rule_id, last_replied_at, total_replies)
               VALUES (?, ?, ?, ?, ?, 1)
               ON CONFLICT(chat_user_id) DO UPDATE SET
                   chat_username = excluded.chat_username,
                   last_message_text = excluded.last_message_text,
                   last_replied_rule_id = excluded.last_replied_rule_id,
                   last_replied_at = excluded.last_replied_at,
                   total_replies = total_replies + 1
            """,
            (chat_user_id, chat_username, last_message_text, rule_id, now_str)
        )
        await db.commit()

# --- Logging Operations ---
async def log_activity(chat_username: str, incoming_message: str, matched_keyword: Optional[str], replied_message: Optional[str], status: str, error_message: Optional[str] = None):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO message_logs (chat_username, incoming_message, matched_keyword, replied_message, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (chat_username, incoming_message, matched_keyword, replied_message, status, error_message)
        )
        await db.commit()

async def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM message_logs ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def clear_logs():
    async with get_db() as db:
        await db.execute("DELETE FROM message_logs")
        await db.commit()

async def get_dashboard_stats() -> Dict[str, Any]:
    async with get_db() as db:
        # Total sent today
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM message_logs WHERE status = 'sent' AND date(timestamp) = date('now')")
        sent_today = (await cursor.fetchone())["cnt"]

        # Total sent all time
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM message_logs WHERE status = 'sent'")
        total_sent = (await cursor.fetchone())["cnt"]

        # Total active rules
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM rules WHERE is_active = 1")
        active_rules = (await cursor.fetchone())["cnt"]

        # Unique users engaged
        cursor = await db.execute("SELECT COUNT(DISTINCT chat_user_id) as cnt FROM conversations")
        unique_users = (await cursor.fetchone())["cnt"]

        return {
            "sent_today": sent_today,
            "total_sent": total_sent,
            "active_rules": active_rules,
            "unique_users": unique_users
        }
