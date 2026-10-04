"""
TikTok Web Selectors & Fallback patterns.
TikTok frequently updates internal class hashes, so multiple fallback strategies
(data-e2e, ARIA roles, tag combinations, text matching) are used for maximum resilience.
"""

# Login indicators
LOGIN_QR_CODE = [
    "canvas",
    "img[src*='qrcode']",
    "div[class*='qr-code']",
    "div[data-e2e='qrcode-container']"
]

QR_LOGIN_SWITCH_BUTTONS = [
    "div:has-text('Gunakan kode QR')",
    "div:has-text('Use QR code')",
    "div:has-text('Use QR / TikTok app')",
    "a:has-text('Gunakan kode QR')",
    "a:has-text('Use QR code')",
    "p:has-text('Gunakan kode QR')",
    "p:has-text('Use QR code')"
]

LOGIN_BUTTONS = [
    "button[data-e2e='top-login-button']",
    "button:has-text('Log in')",
    "a:has-text('Log in')"
]

LOGGED_IN_INDICATORS = [
    "a[data-e2e='profile-icon']",
    "div[data-e2e='profile-icon']",
    "img[data-e2e='avatar-img']",
    "div[class*='DivHeaderInbox']",
    "div[data-e2e='chat-list']",
    "div[class*='ChatList']"
]

# Messages Inbox
MESSAGES_URL = "https://www.tiktok.com/messages"

CHAT_ITEM_CONTAINERS = [
    "div[data-e2e='chat-item']",
    "div[class*='DivChatItem']",
    "div[role='listitem']",
    "div[class*='chat-item']"
]

UNREAD_BADGE = [
    "span[data-e2e='unread-badge']",
    "div[class*='UnreadBadge']",
    "span[class*='Badge']",
    "div[class*='Badge']",
    "span[class*='dot']"
]

CHAT_INPUT_BOX = [
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true']",
    "div[data-e2e='message-input']",
    "textarea",
    "div[placeholder*='Send a message']"
]

SEND_BUTTON = [
    "button[data-e2e='message-send-btn']",
    "button[aria-label='Send message']",
    "button:has-text('Send')",
    "svg[class*='SendButton']"
]

MESSAGE_BUBBLES = [
    "div[data-e2e='chat-message']",
    "div[class*='DivMessageItem']",
    "div[class*='ChatMessage']",
    "div[role='row']"
]
