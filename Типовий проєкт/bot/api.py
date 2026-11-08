"""HTTP API, через яке сайт створює замовлення.

POST /api/order  (заголовок X-API-Key: <SITE_API_KEY>)
GET  /health
"""

import logging
import time
from collections import defaultdict, deque

from aiohttp import web

import cards
import config
import db
import keyboards
import np

log = logging.getLogger(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
    "Access-Control-Max-Age": "86400",
}

RATE_LIMIT = 12  # запитів
RATE_WINDOW = 60  # секунд
_recent = defaultdict(deque)


def _client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote or "unknown"


def _rate_ok(ip):
    now = time.monotonic()
    bucket = _recent[ip]
    while bucket and now - bucket[0] > RATE_WINDOW:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        return False
    bucket.append(now)
    return True


def _clean(value, limit):
    return str(value or "").strip()[:limit]


def _json_error(status, message):
    return web.json_response(
        {"success": False, "message": message}, status=status, headers=CORS_HEADERS
    )


@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(status=204, headers=CORS_HEADERS)
    try:
        response = await handler(request)
    except web.HTTPException as exc:
        exc.headers.update(CORS_HEADERS)
        raise
    response.headers.update(CORS_HEADERS)
    return response


async def handle_order(request):
    if not config.SITE_API_KEY:
        return _json_error(503, "API не налаштоване: вкажіть SITE_API_KEY у .env")

    if request.headers.get("X-API-Key", "") != config.SITE_API_KEY:
        return _json_error(401, "Невірний API-ключ")

    if not _rate_ok(_client_ip(request)):
        return _json_error(429, "Забагато запитів. Спробуйте за хвилину.")

    try:
        payload = await request.json()
    except Exception:
        return _json_error(400, "Очікується JSON")

    if not isinstance(payload, dict):
        return _json_error(400, "Некоректний формат даних")

    name = _clean(payload.get("name"), 100)
    phone = _clean(payload.get("phone"), 30)
    city = _clean(payload.get("city"), 100)
    delivery = _clean(payload.get("delivery"), 200)

    missing = [
        title
        for title, value in (
            ("ім'я", name),
            ("телефон", phone),
            ("місто", city),
            ("доставка", delivery),
        )
        if not value
    ]
    if missing:
        return _json_error(400, "Заповніть поля: {}".format(", ".join(missing)))

    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10:
        return _json_error(400, "Некоректний номер телефону")

    try:
        price = int(payload.get("price") or 0)
    except (TypeError, ValueError):
        price = 0
    price = max(0, min(price, 1_000_000))

    try:
        qty = int(payload.get("qty") or 1)
    except (TypeError, ValueError):
        qty = 1
    qty = max(1, min(qty, 100))

    order = await db.create_order(
        {
            "name": name,
            "patronymic": _clean(payload.get("patronymic"), 100),
            "phone": phone,
            "city": city,
            "delivery": delivery,
            "payment": _clean(payload.get("payment"), 100),
            "comment": _clean(payload.get("comment"), 500),
            "pack": _clean(payload.get("pack"), 200),
            "price": price,
            "qty": qty,
            "source": _clean(payload.get("source"), 40) or "landing",
        }
    )

    bot = request.app["bot"]
    try:
        await bot.send_message(
            config.ADMIN_CHAT_ID,
            cards.build_order_text(order),
            reply_markup=keyboards.order_keyboard(order),
        )
    except Exception:
        log.exception("Замовлення №%s збережено, але не надіслано в Telegram", order["number"])

    log.info("Нове замовлення №%s від %s", order["number"], name)

    return web.json_response(
        {
            "success": True,
            "order_id": order["id"],
            "order_number": order["number"],
        }
    )


async def handle_health(request):
    try:
        total = await db.count_orders()
        db_ok = True
    except Exception:
        total = 0
        db_ok = False
    return web.json_response(
        {"ok": db_ok, "orders": total, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    )


async def handle_options(request):
    return web.Response(status=204, headers=CORS_HEADERS)


async def handle_np_cities(request):
    if not config.SITE_API_KEY:
        return _json_error(503, "API не налаштоване")
    if request.headers.get("X-API-Key", "") != config.SITE_API_KEY:
        return _json_error(401, "Невірний API-ключ")
    if not _rate_ok(_client_ip(request)):
        return _json_error(429, "Забагато запитів. Спробуйте за хвилину.")

    query = _clean(request.query.get("q", ""), 100)
    if len(query) < 2:
        return web.json_response({"success": True, "items": []}, headers=CORS_HEADERS)

    items = await np.search_cities(query)
    if items is None:
        return _json_error(503, "Нова Пошта не налаштована (NP_API_KEY)")
    return web.json_response({"success": True, "items": items}, headers=CORS_HEADERS)


async def handle_np_warehouses(request):
    if not config.SITE_API_KEY:
        return _json_error(503, "API не налаштоване")
    if request.headers.get("X-API-Key", "") != config.SITE_API_KEY:
        return _json_error(401, "Невірний API-ключ")
    if not _rate_ok(_client_ip(request)):
        return _json_error(429, "Забагато запитів. Спробуйте за хвилину.")

    city_ref = _clean(request.query.get("city_ref", ""), 64)
    kind = _clean(request.query.get("kind", ""), 20)
    company_uuid = _clean(request.query.get("company_uuid", ""), 64)
    if not city_ref:
        return _json_error(400, "Вкажіть city_ref")

    items = await np.get_warehouses(
        city_ref, kind if kind in ("branch", "postomat") else None, company_uuid or None
    )
    if items is None:
        return _json_error(503, "Delengine не налаштований (NP_API_KEY)")
    return web.json_response({"success": True, "items": items}, headers=CORS_HEADERS)


async def handle_np_companies(request):
    if not config.SITE_API_KEY:
        return _json_error(503, "API не налаштоване")
    if request.headers.get("X-API-Key", "") != config.SITE_API_KEY:
        return _json_error(401, "Невірний API-ключ")
    if not _rate_ok(_client_ip(request)):
        return _json_error(429, "Забагато запитів. Спробуйте за хвилину.")

    items = await np.get_companies()
    if items is None:
        return _json_error(503, "Delengine не налаштований (NP_API_KEY)")
    return web.json_response({"success": True, "items": items}, headers=CORS_HEADERS)


def create_app(bot):
    app = web.Application(middlewares=[cors_middleware])
    app["bot"] = bot
    app.router.add_post("/api/order", handle_order)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/api/np/cities", handle_np_cities)
    app.router.add_get("/api/np/warehouses", handle_np_warehouses)
    app.router.add_get("/api/np/companies", handle_np_companies)
    app.router.add_route("OPTIONS", "/{tail:.*}", handle_options)
    return app
