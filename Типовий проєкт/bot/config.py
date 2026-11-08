"""Конфігурація CRM-бота ТеплоПак.

Усі значення читаються зі змінних оточення або з файлу .env
(див. .env.example).
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _csv_ints(value):
    """Розбирає '123,456;789' у список цілих."""
    result = []
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            result.append(int(part))
    return result


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Користувачі, яким дозволено користуватися ботом (менеджери/власник).
ADMIN_IDS = _csv_ints(os.getenv("ADMIN_IDS", ""))

# Чат, куди прилітають нові замовлення. Може бути особистий чат або група (id з мінусом).
_raw_chat = os.getenv("ADMIN_CHAT_ID", "").strip()
ADMIN_CHAT_ID = int(_raw_chat) if _raw_chat.lstrip("-").isdigit() else 0
if not ADMIN_CHAT_ID and ADMIN_IDS:
    ADMIN_CHAT_ID = ADMIN_IDS[0]

# Ключ, з яким сайт звертається до /api/order (заголовок X-API-Key).
SITE_API_KEY = os.getenv("SITE_API_KEY", "").strip()

# Ключ API Нової Пошти (для автозаповнення міст і відділень на сайті).
NP_API_KEY = os.getenv("NP_API_KEY", "").strip()

DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "orders.db"))).expanduser()

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))

TIMEZONE = os.getenv("TIMEZONE", "Europe/Kyiv")
TZ = ZoneInfo(TIMEZONE)

CURRENCY = "грн"

# Номер замовлення = id у базі + цей зсув (перше замовлення отримає №1001).
ORDER_NUMBER_OFFSET = 1000

# Статуси замовлення.
STATUSES = {
    "new": ("🆕", "Нове"),
    "processing": ("⚙️", "Опрацювання"),
    "shipping": ("🚚", "Доставка"),
    "done": ("✅", "Успішно"),
    "canceled": ("❌", "Відміна"),
}
STATUS_ORDER = ["new", "processing", "shipping", "done", "canceled"]

# Комплекти для швидкого створення замовлення з бота: (к-сть, назва, ціна).
PACKS = [
    ("1", "1 шт — Комплект «Спробувати»", 189),
    ("2", "2 шт — Комплект «Для двох рук»", 329),
    ("4", "4 шт — Комплект «Сімейний/Тактичний»", 549),
]

# Варіанти оплати для кнопок у боті.
PAYMENTS = {
    "cod": "Накладений платіж (при отриманні)",
    "prepay": "Передоплата на картку",
}

