import asyncio
import os
import re
import json
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from app.config import (
    BROWSER_PROFILE_DIR,
    SCREENSHOTS_DIR,
    settings
)
from app.database import (
    get_active_rules,
    can_reply_to_user,
    record_reply,
    log_activity
)
from app.bot.selectors import (
    LOGIN_QR_CODE,
    LOGIN_BUTTONS,
    QR_LOGIN_SWITCH_BUTTONS,
    LOGGED_IN_INDICATORS,
    MESSAGES_URL,
    CHAT_ITEM_CONTAINERS,
    UNREAD_BADGE,
    CHAT_INPUT_BOX,
    SEND_BUTTON,
    MESSAGE_BUBBLES
)

logger = logging.getLogger("tiktok_bot")
logging.basicConfig(level=logging.INFO)

class TikTokBotEngine:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.status: str = "STOPPED"  # STOPPED, STARTING, NEEDS_LOGIN, RUNNING, ERROR
        self.status_message: str = "Bot is currently stopped."
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self.hourly_replies: List[datetime] = []
        self.live_screenshot_path = SCREENSHOTS_DIR / "live.png"
        self.started_at: Optional[datetime] = None

    async def get_state(self) -> Dict[str, Any]:
        has_screenshot = self.live_screenshot_path.exists()
        return {
            "status": self.status,
            "status_message": self.status_message,
            "is_running": self.is_running,
            "has_screenshot": has_screenshot,
            "screenshot_timestamp": os.path.getmtime(self.live_screenshot_path) if has_screenshot else None,
            "uptime_seconds": int((datetime.now() - self.started_at).total_seconds()) if (self.is_running and self.started_at) else 0,
            "headless": settings.headless,
            "check_interval": settings.check_interval
        }

    async def capture_screenshot(self) -> Optional[str]:
        """Captures the current browser view for dashboard preview (e.g. for scanning QR login)."""
        if self.page:
            try:
                await self.page.screenshot(path=str(self.live_screenshot_path), full_page=False)
                return str(self.live_screenshot_path)
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")
        return None

    async def capture_qr_screenshot(self) -> Optional[str]:
        """Captures a zoomed-in screenshot of the QR code area for easy scanning.
        Falls back to full screenshot if QR element cannot be found."""
        if not self.page:
            return None
        try:
            qr_elem = None
            for sel in LOGIN_QR_CODE:
                qr_elem = await self.page.query_selector(sel)
                if qr_elem:
                    break

            if qr_elem:
                # Get bounding box and add generous padding around QR
                box = await qr_elem.bounding_box()
                if box:
                    padding = 80
                    clip = {
                        "x": max(0, box["x"] - padding),
                        "y": max(0, box["y"] - padding),
                        "width": box["width"] + padding * 2,
                        "height": box["height"] + padding * 2,
                    }
                    await self.page.screenshot(
                        path=str(self.live_screenshot_path),
                        clip=clip,
                        full_page=False
                    )
                    logger.info("QR code screenshot captured (zoomed).")
                    return str(self.live_screenshot_path)

            # Fallback to full page screenshot
            return await self.capture_screenshot()
        except Exception as e:
            logger.warning(f"Failed to capture QR screenshot: {e}")
            return await self.capture_screenshot()

    async def _switch_to_qr_login(self):
        """Attempts to click the 'Use QR Code' button on TikTok login page."""
        if not self.page:
            return
        try:
            # First check: maybe QR is already showing (canvas element present)
            for sel in LOGIN_QR_CODE:
                if await self.page.query_selector(sel):
                    logger.info("QR code already visible, no need to switch.")
                    return

            # Try each selector
            for sel in QR_LOGIN_SWITCH_BUTTONS:
                try:
                    btn = await self.page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        logger.info(f"Clicked QR login button via selector: {sel}")
                        await asyncio.sleep(2)
                        return
                except Exception:
                    continue

            # JS fallback: search all elements for QR-related text and click
            clicked = await self.page.evaluate("""
                () => {
                    const keywords = ['Gunakan kode QR', 'Use QR code', 'QR code', 'QR login'];
                    const all = document.querySelectorAll('div, span, a, button, p');
                    for (const el of all) {
                        const text = (el.textContent || '').trim();
                        if (keywords.some(kw => text === kw || text.startsWith(kw))) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }
            """)
            if clicked:
                logger.info("Clicked QR login button via JS fallback.")
                await asyncio.sleep(2)
            else:
                logger.warning("Could not find QR login button on page.")
        except Exception as e:
            logger.debug(f"Could not switch to QR login: {e}")


    async def start(self):
        """Starts the bot background task."""
        if self.is_running:
            return
        self.is_running = True
        self.status = "STARTING"
        self.status_message = "Initializing browser session..."
        self.started_at = datetime.now()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stops the bot gracefully."""
        self.is_running = False
        self.status = "STOPPED"
        self.status_message = "Bot stopped by user."
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._cleanup()

    async def _cleanup(self):
        """Closes browser context and Playwright instance."""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
        finally:
            self.page = None
            self.context = None
            self.playwright = None

    async def _init_browser(self):
        """Launches persistent browser context with stealth arguments."""
        self.playwright = await async_playwright().start()

        # Stealth browser launch args
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1280,800",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ]

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR),
                headless=settings.headless,
                viewport={"width": 1280, "height": 800},
                user_agent=user_agent,
                args=args,
                locale="id-ID",
                timezone_id="Asia/Jakarta"
            )
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
                logger.info("Chromium binary tidak ditemukan. Mengunduh Playwright Chromium otomatis...")
                import subprocess
                import sys
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(BROWSER_PROFILE_DIR),
                    headless=settings.headless,
                    viewport={"width": 1280, "height": 800},
                    user_agent=user_agent,
                    args=args,
                    locale="id-ID",
                    timezone_id="Asia/Jakarta"
                )
            else:
                raise e

        # Remove navigator.webdriver detection flag
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()

    async def _check_login_status(self) -> bool:
        """Determines if TikTok is logged in or waiting for login."""
        if not self.page:
            return False

        try:
            # Check for avatar or profile indicator or inbox header
            for sel in LOGGED_IN_INDICATORS:
                if await self.page.query_selector(sel):
                    return True
        except Exception:
            pass

        # Check if URL already contains /messages and is not redirected to login
        current_url = self.page.url
        if "messages" in current_url and "login" not in current_url:
            return True

        return False

    async def _verification_required(self) -> bool:
        """Detects an account verification checkpoint without attempting to bypass it."""
        if not self.page:
            return False

        try:
            page_text = " ".join(
                (await self.page.locator("body").inner_text(timeout=3000)).casefold().split()
            )
            current_url = self.page.url.casefold()
            indicators = (
                "verifikasi bahwa ini memang anda",
                "verifikasikan bahwa ini memang anda",
                "verifikasi identitas anda",
                "verify that it's you",
                "verify your identity",
                "security check",
            )
            return any(indicator in page_text for indicator in indicators) or any(
                marker in current_url for marker in ("/verify", "/challenge")
            )
        except Exception:
            return False

    def _is_rate_limited(self) -> bool:
        """Prevents exceeding max DMs per hour to protect account."""
        now = datetime.now()
        # Clean timestamps older than 1 hour
        self.hourly_replies = [t for t in self.hourly_replies if (now - t).total_seconds() < 3600]
        return len(self.hourly_replies) >= settings.max_dm_per_hour

    def _match_rule(self, message_text: str, rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Matches message against configured rules in order."""
        msg = message_text.strip().lower()
        for rule in rules:
            if not rule.get("is_active"):
                continue
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
                    if re.search(kw, message_text, re.IGNORECASE):
                        matched = True
                except Exception:
                    pass

            if matched:
                return rule
        return None

    async def _human_type(self, element, text: str):
        """Simulates realistic human typing with random delay."""
        await element.click()
        await asyncio.sleep(random.uniform(0.3, 0.7))
        for char in text:
            await self.page.keyboard.type(char, delay=random.randint(30, 80))
        await asyncio.sleep(random.uniform(0.4, 0.9))

    async def _process_active_chat(self, chat_name: str, rules: List[Dict[str, Any]]):
        """Reads recent incoming messages in the currently selected chat and auto-replies if matched."""
        if not self.page:
            return

        last_text: Optional[str] = None
        kw: Optional[str] = None
        try:
            # Locate messages in current thread
            message_elements = await self.page.query_selector_all(", ".join(MESSAGE_BUBBLES))

            if not message_elements:
                # TikTok sometimes exposes messages through generic chat bubble classes.
                message_elements = await self.page.query_selector_all(
                    "[class*='message' i], [data-e2e*='message' i]"
                )

            visible_messages = []
            for element in message_elements:
                if not await element.is_visible():
                    continue
                text = (await element.inner_text()).strip()
                if not text:
                    continue
                is_composer = await element.evaluate(
                    "el => !!el.closest('[contenteditable=\"true\"], textarea, input')"
                )
                if not is_composer:
                    visible_messages.append(element)
            message_elements = visible_messages

            if not message_elements:
                self.status_message = (
                    f"Percakapan {chat_name} terbuka, tetapi bubble pesan belum terdeteksi. "
                    "Struktur DM TikTok berubah; periksa pembaruan selector bot."
                )
                logger.warning(self.status_message)
                return

            latest_incoming_text = ""
            rule = None
            for element in reversed(message_elements):
                text = (await element.inner_text()).strip()
                if not text:
                    continue

                # Outbound bubbles should never trigger an automatic reply.
                is_self = await element.evaluate("""
                    el => {
                        for (let node = el, depth = 0; node && depth < 5; node = node.parentElement, depth++) {
                            const className = typeof node.className === 'string' ? node.className : '';
                            const markers = `${className} ${node.getAttribute('data-e2e') || ''} ${node.getAttribute('data-testid') || ''}`;
                            if (/(^|[-_\\s])(self|outgoing|sent|right)([-_\\s]|$)/i.test(markers)) return true;
                            const style = getComputedStyle(node);
                            if (style.alignItems === 'flex-end' || style.justifyContent === 'flex-end') return true;
                        }
                        return false;
                    }
                """)
                if is_self:
                    continue

                if not latest_incoming_text:
                    latest_incoming_text = text

                candidate_rule = self._match_rule(text, rules)
                if candidate_rule:
                    last_text = text
                    rule = candidate_rule
                    break

            if not rule:
                last_text = latest_incoming_text
                logger.info(f"No active keyword matched message from {chat_name}: {last_text!r}")
                self.status_message = (
                    f"Pesan terbaca dari {chat_name}: “{last_text[:100] or 'tidak ada pesan masuk'}”. "
                    f"Keyword aktif: {', '.join(r['keyword'] for r in rules)}."
                )
                return

            logger.info(f"Incoming message from {chat_name}: '{last_text}'")

            rule_id = rule["id"]
            kw = rule["keyword"]
            reply_tpl = rule["reply_message"]
            cooldown = rule.get("cooldown_seconds", 3600)

            # Check cooldown for this chat user
            chat_user_id = chat_name.lower().strip()
            can_send = await can_reply_to_user(chat_user_id, rule_id, cooldown)
            if not can_send:
                logger.info(f"User {chat_name} is in cooldown for rule '{kw}'. Skipping.")
                await log_activity(
                    chat_username=chat_name,
                    incoming_message=last_text,
                    matched_keyword=kw,
                    replied_message=None,
                    status="cooldown",
                    error_message=f"Cooldown active ({cooldown}s)"
                )
                return

            if self._is_rate_limited():
                logger.warning("Hourly rate limit reached! Pausing replies.")
                await log_activity(
                    chat_username=chat_name,
                    incoming_message=last_text,
                    matched_keyword=kw,
                    replied_message=None,
                    status="rate_limited",
                    error_message=f"Max {settings.max_dm_per_hour} DMs per hour limit reached."
                )
                return

            # Prepare reply
            final_reply = reply_tpl.replace("{username}", chat_name)

            # Find input box
            input_box = None
            for sel in CHAT_INPUT_BOX:
                input_box = await self.page.query_selector(sel)
                if input_box:
                    break

            if not input_box:
                error_message = "Kotak input DM tidak ditemukan pada percakapan ini."
                logger.warning(error_message)
                self.status_message = error_message
                await log_activity(
                    chat_username=chat_name,
                    incoming_message=last_text,
                    matched_keyword=kw,
                    replied_message=None,
                    status="error",
                    error_message=error_message
                )
                return

            # Human typing delay
            await asyncio.sleep(random.uniform(settings.human_delay_min, settings.human_delay_max))
            await self._human_type(input_box, final_reply)

            # Send message via Enter key or Send button
            sent_success = False
            for btn_sel in SEND_BUTTON:
                send_btn = await self.page.query_selector(btn_sel)
                if send_btn and await send_btn.is_visible():
                    await send_btn.click()
                    sent_success = True
                    break

            if not sent_success:
                # Press Enter key
                await self.page.keyboard.press("Enter")
                sent_success = True

            # Register reply
            self.hourly_replies.append(datetime.now())
            await record_reply(chat_user_id, chat_name, last_text, rule_id)
            await log_activity(
                chat_username=chat_name,
                incoming_message=last_text,
                matched_keyword=kw,
                replied_message=final_reply,
                status="sent"
            )
            logger.info(f"Successfully auto-replied to {chat_name} for keyword '{kw}'")

            # Post-reply delay
            await asyncio.sleep(random.uniform(1.0, 2.5))
            await self.capture_screenshot()

        except Exception as e:
            logger.error(f"Error processing active chat {chat_name}: {e}")
            self.status_message = f"Gagal memproses DM dari {chat_name}: {str(e)[:120]}"
            await log_activity(
                chat_username=chat_name,
                incoming_message=last_text,
                matched_keyword=kw,
                replied_message=None,
                status="error",
                error_message=str(e)
            )

    async def _scan_inbox(self):
        """Scans TikTok conversation list for new or unread messages."""
        if not self.page:
            return

        try:
            active_rules = await get_active_rules()
            if not active_rules:
                self.status_message = (
                    "Bot aktif, tetapi belum ada keyword aktif. Tambahkan atau aktifkan aturan di dashboard."
                )
                return

            # Make sure we are on TikTok messages page
            if "messages" not in self.page.url:
                await self.page.goto(MESSAGES_URL, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

            # Find conversation items
            chat_items = []
            for sel in CHAT_ITEM_CONTAINERS:
                items = await self.page.query_selector_all(sel)
                if items:
                    chat_items = items
                    break

            if not chat_items:
                self.status_message = (
                    "Inbox TikTok terlihat, tetapi elemen percakapannya tidak cocok dengan selector. "
                    "Perbarui bot dan restart agar deteksi inbox terbaru digunakan."
                )
                logger.warning(self.status_message)
                await self.capture_screenshot()
                return

            logger.info(f"Found {len(chat_items)} conversation item(s) in inbox.")
            self.status_message = (
                f"Inbox terdeteksi ({len(chat_items)} percakapan); memprioritaskan chat yang belum dibaca."
            )

            unread_chats = []
            recent_chats = []
            unread_selector = ", ".join(UNREAD_BADGE)
            for item in chat_items:
                try:
                    badge = await item.query_selector(unread_selector)
                    is_unread = badge is not None and await badge.is_visible()
                    (unread_chats if is_unread else recent_chats).append(item)
                except Exception as ex:
                    logger.warning(f"Error checking unread status for chat: {ex}")

            chats_to_check = unread_chats if unread_chats else recent_chats[:5]
            logger.info(
                f"Prioritizing {len(unread_chats)} unread conversation(s); "
                f"checking {len(chats_to_check)} chat(s) this scan."
            )

            for item in chats_to_check:
                try:
                    # Extract username / contact name
                    name_elem = await item.query_selector(
                        "[data-e2e*='name' i], [class*='name' i], span, p, h4"
                    )
                    chat_name = (
                        (await name_elem.inner_text()).strip()
                        if name_elem
                        else ""
                    )
                    if not chat_name:
                        chat_text = (await item.inner_text()).strip().splitlines()
                        chat_name = chat_text[0].strip() if chat_text else "Pengguna TikTok"

                    # Open conversation
                    await item.click()
                    await asyncio.sleep(random.uniform(1.2, 2.0))

                    # Process messages in this chat
                    await self._process_active_chat(chat_name, active_rules)

                except Exception as ex:
                    logger.warning(f"Error inspecting chat item: {ex}")
                    continue

            # Update screenshot
            await self.capture_screenshot()

        except Exception as e:
            logger.error(f"Inbox scan error: {e}")
            self.status_message = f"Gagal memindai inbox TikTok: {str(e)[:120]}"

    async def _run_loop(self):
        """Main 24/7 background worker loop with auto-recovery and resilience."""
        while self.is_running:
            try:
                # Initialize browser if not already active
                if not self.context or not self.page:
                    await self._init_browser()
                    logger.info(f"Navigating to {MESSAGES_URL}...")
                    await self.page.goto(MESSAGES_URL, wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(3)
                    await self.capture_screenshot()

                # Inner monitoring loop
                while self.is_running:
                    if await self._verification_required():
                        self.status = "NEEDS_VERIFICATION"
                        self.status_message = (
                            "TikTok meminta verifikasi identitas. Selesaikan melalui sesi browser resmi; "
                            "bot dijeda dan tidak mencoba melewati verifikasi."
                        )
                        await self.capture_screenshot()
                        await asyncio.sleep(5)
                        continue

                    is_logged_in = await self._check_login_status()

                    if not is_logged_in:
                        self.status = "NEEDS_LOGIN"
                        self.status_message = "Silakan scan QR Code TikTok di Live Browser Preview untuk login."
                        # Try to switch to QR login mode first
                        await self._switch_to_qr_login()
                        # Capture zoomed QR screenshot for easy scanning
                        await self.capture_qr_screenshot()
                        await asyncio.sleep(4)
                        continue

                    # When logged in
                    self.status = "RUNNING"
                    self.status_message = "Bot aktif & memantau Direct Messages 24/7."

                    # Perform inbox scan and reply
                    await self._scan_inbox()

                    # Sleep check interval with minor random jitter
                    jitter = random.uniform(-1.5, 2.5)
                    wait_time = max(5.0, settings.check_interval + jitter)
                    await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                logger.info("Bot worker task cancelled gracefully.")
                break
            except Exception as e:
                if not self.is_running:
                    break
                logger.error(f"Bot worker encountered error: {e}. Auto-recovering in 15 seconds...", exc_info=True)
                self.status = "ERROR"
                self.status_message = f"Terjadi kendala koneksi: {str(e)[:100]}. Memulihkan otomatis dalam 15 detik..."
                await self.capture_screenshot()
                await self._cleanup()
                await asyncio.sleep(15)

bot_engine = TikTokBotEngine()
