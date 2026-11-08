"""Інлайн-клавіатури бота."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config


def _status_button(order_id, status, current):
    emoji, label = config.STATUSES[status]
    prefix = "• " if status == current else ""
    return InlineKeyboardButton(
        text="{}{} {}".format(prefix, emoji, label),
        callback_data="st:{}:{}".format(order_id, status),
    )


def order_keyboard(order):
    order_id = order["id"]
    current = order.get("status", "new")

    ttn_text = "✏️ Змінити ТТН" if order.get("ttn") else "✏️ Додати ТТН"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _status_button(order_id, "new", current),
                _status_button(order_id, "processing", current),
            ],
            [
                _status_button(order_id, "shipping", current),
                _status_button(order_id, "done", current),
            ],
            [_status_button(order_id, "canceled", current)],
            [
                InlineKeyboardButton(
                    text=ttn_text, callback_data="ttn:{}".format(order_id)
                ),
                InlineKeyboardButton(
                    text="💬 Коментар", callback_data="cmt:{}".format(order_id)
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Оновити", callback_data="refresh:{}".format(order_id)
                )
            ],
        ]
    )


def menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Нове замовлення", callback_data="menu:new"
                )
            ],
            [
                InlineKeyboardButton(text="📋 Замовлення", callback_data="menu:orders"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="menu:stats"),
            ],
            [
                InlineKeyboardButton(text="🔍 Пошук", callback_data="menu:find"),
                InlineKeyboardButton(text="📤 Експорт CSV", callback_data="menu:export"),
            ],
        ]
    )


def payment_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💵 Накладений платіж", callback_data="np:pay:cod"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Передоплата на картку", callback_data="np:pay:prepay"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✍️ Інша оплата", callback_data="np:pay:other"
                )
            ],
            [InlineKeyboardButton(text="↩️ Скасувати", callback_data="abort")],
        ]
    )


def pack_keyboard():
    rows = []
    for key, title, price in config.PACKS:
        rows.append(
            [
                InlineKeyboardButton(
                    text="{} · {} грн".format(title, price),
                    callback_data="np:pack:{}".format(key),
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="✍️ Інший комплект", callback_data="np:pack:other")]
    )
    rows.append([InlineKeyboardButton(text="↩️ Скасувати", callback_data="abort")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def comment_skip_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Пропустити", callback_data="np:skip_comment")],
            [InlineKeyboardButton(text="↩️ Скасувати", callback_data="abort")],
        ]
    )


def new_preview_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Створити замовлення", callback_data="np:save"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Заповнити заново", callback_data="np:restart"
                )
            ],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="abort")],
        ]
    )


def _filter_button(status, current):
    emoji, label = config.STATUSES[status]
    prefix = "• " if status == current else ""
    return InlineKeyboardButton(
        text="{}{} {}".format(prefix, emoji, label),
        callback_data="list:{}:0".format(status),
    )


def list_keyboard(status, page, pages, orders):
    status = status or "all"
    rows = [
        [
            InlineKeyboardButton(
                text="{}📋 Всі".format("• " if status == "all" else ""),
                callback_data="list:all:0",
            ),
            _filter_button("new", status),
            _filter_button("processing", status),
        ],
        [
            _filter_button("shipping", status),
            _filter_button("done", status),
            _filter_button("canceled", status),
        ],
    ]

    for order in orders:
        name = (order.get("name") or "Без імені").strip()
        if len(name) > 18:
            name = name[:18] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text="№{} · {} · {}".format(
                        order.get("number", order["id"]), name, order.get("price", 0)
                    ),
                    callback_data="open:{}".format(order["id"]),
                )
            ]
        )

    if pages > 1:
        nav = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(
                    text="⬅️", callback_data="list:{}:{}".format(status, page - 1)
                )
            )
        nav.append(
            InlineKeyboardButton(
                text="{}/{}".format(page + 1, pages), callback_data="list:{}:{}".format(status, page)
            )
        )
        if page + 1 < pages:
            nav.append(
                InlineKeyboardButton(
                    text="➡️", callback_data="list:{}:{}".format(status, page + 1)
                )
            )
        rows.append(nav)

    rows.append(
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_keyboard(orders):
    rows = []
    for order in orders:
        name = (order.get("name") or "Без імені").strip()
        if len(name) > 18:
            name = name[:18] + "…"
        rows.append(
            [
                InlineKeyboardButton(
                    text="№{} · {} · {}".format(
                        order.get("number", order["id"]), name, order.get("price", 0)
                    ),
                    callback_data="open:{}".format(order["id"]),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def abort_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Скасувати", callback_data="abort")]
        ]
    )


def skip_keyboard(callback_data):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Пропустити", callback_data=callback_data)],
            [InlineKeyboardButton(text="↩️ Скасувати", callback_data="abort")],
        ]
    )


def back_to_list_keyboard(status, page):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ До списку",
                    callback_data="list:{}:{}".format(status or "all", page or 0),
                )
            ]
        ]
    )

