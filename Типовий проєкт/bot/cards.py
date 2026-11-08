"""Формування текстів повідомлень (картки замовлення, списки, меню)."""

import html
from datetime import datetime

import config


def e(value):
    """Екранує текст для HTML-розмітки Telegram."""
    return html.escape(str(value if value is not None else ""), quote=False)


def money(value):
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        number = 0
    return "{} {}".format("{:,}".format(number).replace(",", " "), config.CURRENCY)


def short_dt(value):
    """'2026-11-08 14:35:00' -> '08.11.2026 14:35'."""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return e(value)
    return dt.strftime("%d.%m.%Y %H:%M")


def short_time(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return ""
    return dt.strftime("%d.%m %H:%M")


def status_label(status):
    return config.STATUSES.get(status, ("•", "—"))[1]


def status_emoji(status):
    return config.STATUSES.get(status, ("•", "—"))[0]


def normalize_phone(value):
    """Приводить український номер до формату +380XXXXXXXXX.

    Приймає +380 (67) 123-45-67, 380671234567, 0671234567, 671234567.
    Повертає None, якщо номер некоректний.
    """
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 12 and digits.startswith("380"):
        pass
    elif len(digits) == 11 and digits.startswith("80"):
        digits = "3" + digits
    elif len(digits) == 10 and digits.startswith("0"):
        digits = "38" + digits
    elif len(digits) == 9:
        digits = "380" + digits
    else:
        return None

    if len(digits) != 12 or not digits.startswith("380"):
        return None
    return "+" + digits


def phone_tel(value):
    """Повертає номер для посилання tel: (лише цифри з +)."""
    normalized = normalize_phone(value)
    if normalized:
        return normalized
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return "+" + digits if digits else ""


def format_phone(value):
    """Красивий формат для показу: +380 (67) 123-45-67."""
    normalized = normalize_phone(value)
    if not normalized:
        return str(value or "—")
    rest = normalized[4:]
    return "+380 ({}) {}-{}-{}".format(
        rest[0:2], rest[2:5], rest[5:7], rest[7:9]
    )


def build_order_text(order):
    """Повна картка замовлення для Telegram."""
    status = order.get("status", "new")
    emoji = status_emoji(status)
    label = status_label(status)

    phone_raw = order.get("phone") or ""
    phone_link = phone_tel(phone_raw)
    if phone_link:
        phone_line = '📞 <a href="tel:{}">{}</a>'.format(
            phone_link, e(format_phone(phone_raw))
        )
    else:
        phone_line = "📞 —"

    name_line = "👤 {}".format(e(order.get("name") or "—"))
    patronymic = (order.get("patronymic") or "").strip()
    if patronymic:
        name_line += " {}".format(e(patronymic))

    lines = [
        "{} <b>Замовлення №{}</b>".format(emoji, order.get("number", order.get("id", ""))),
        "🕒 {}".format(short_dt(order.get("created_at"))),
        "━━━━━━━━━━━━━━",
        "📦 {}".format(e(order.get("pack") or "—")),
        "💰 <b>{}</b>".format(money(order.get("price"))),
        "━━━━━━━━━━━━━━",
        name_line,
        phone_line,
        "📍 {}".format(e(order.get("city") or "—")),
        "🚚 {}".format(e(order.get("delivery") or "—")),
        "💳 {}".format(e(order.get("payment") or "—")),
    ]

    client_comment = (order.get("comment") or "").strip()
    if client_comment:
        if len(client_comment) > 300:
            client_comment = client_comment[:300] + "…"
        lines.append("💬 <i>{}</i>".format(e(client_comment)))

    lines.append("━━━━━━━━━━━━━━")

    ttn = (order.get("ttn") or "").strip()
    lines.append(
        "📮 <b>ТТН:</b> <code>{}</code>".format(e(ttn)) if ttn else "📮 <b>ТТН:</b> —"
    )

    notes = order.get("notes") or []
    lines.append("📝 <b>Коментарі менеджера:</b>")
    if notes:
        for note in notes[-5:]:
            text = (note.get("text") or "").strip()
            if len(text) > 200:
                text = text[:200] + "…"
            author = (note.get("author") or "").strip()
            prefix = "• {} ".format(short_time(note.get("created_at")))
            if author:
                prefix += "({}) ".format(e(author))
            lines.append("{}{}".format(prefix, e(text)))
    else:
        lines.append("• —")

    lines.append("━━━━━━━━━━━━━━")
    lines.append("📌 <b>Статус:</b> {} {}".format(emoji, label))
    if status == "canceled" and order.get("cancel_reason"):
        lines.append("❌ <b>Причина:</b> {}".format(e(order.get("cancel_reason"))))

    return "\n".join(lines)


def build_menu_text(stats):
    by_status = stats.get("by_status", {})
    lines = [
        "👋 <b>CRM ТеплоПак</b>",
        "",
        "📦 Всього замовлень: <b>{}</b>".format(stats.get("total", 0)),
    ]
    for status in config.STATUS_ORDER:
        emoji, label = config.STATUSES[status]
        lines.append("{} {}: {}".format(emoji, label, by_status.get(status, 0)))
    lines.extend(
        [
            "",
            "Оберіть дію нижче 👇",
            "",
            "Команди: /new · /orders · /stats · /find · /export",
        ]
    )
    return "\n".join(lines)


def build_list_text(status, orders, total, page, pages):
    titles = {
        "all": "📋 Усі замовлення",
        "new": "🆕 Нові замовлення",
        "processing": "⚙️ В опрацюванні",
        "shipping": "🚚 У доставці",
        "done": "✅ Успішні",
        "canceled": "❌ Скасовані",
    }
    title = titles.get(status or "all", "📋 Замовлення")

    lines = ["{}".format(title), "Знайдено: <b>{}</b>".format(total)]
    if total:
        lines.append("Сторінка {}/{}".format(page + 1, pages))
    lines.append("")
    if not orders:
        lines.append("Тут поки що порожньо.")
    else:
        lines.append("Натисніть на замовлення, щоб відкрити картку 👇")
    return "\n".join(lines)


def build_search_text(query, orders):
    lines = [
        "🔍 <b>Пошук:</b> <code>{}</code>".format(e(query)),
        "Знайдено: <b>{}</b>".format(len(orders)),
        "",
    ]
    if not orders:
        lines.append("Нічого не знайдено. Спробуйте номер, телефон, ім'я або ТТН.")
    else:
        lines.append("Натисніть на замовлення, щоб відкрити картку 👇")
    return "\n".join(lines)
