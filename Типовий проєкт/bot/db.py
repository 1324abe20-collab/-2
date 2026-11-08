"""Робота з базою даних (SQLite) для CRM-бота.

Замовлення, коментарі менеджерів та історія статусів.
"""

from datetime import datetime, timedelta

import aiosqlite

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    name          TEXT NOT NULL,
    patronymic    TEXT NOT NULL DEFAULT '',
    phone         TEXT NOT NULL,
    city          TEXT NOT NULL DEFAULT '',
    delivery      TEXT NOT NULL DEFAULT '',
    payment       TEXT NOT NULL DEFAULT '',
    comment       TEXT NOT NULL DEFAULT '',
    pack          TEXT NOT NULL DEFAULT '',
    price         INTEGER NOT NULL DEFAULT 0,
    qty           INTEGER NOT NULL DEFAULT 1,
    source        TEXT NOT NULL DEFAULT 'landing',
    status        TEXT NOT NULL DEFAULT 'new',
    ttn           TEXT,
    cancel_reason TEXT
);

CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    author     TEXT NOT NULL DEFAULT '',
    text       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS status_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    status     TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    author     TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_notes_order    ON notes(order_id);
"""


def now_str():
    return datetime.now(config.TZ).strftime("%Y-%m-%d %H:%M:%S")


def _connect():
    return aiosqlite.connect(str(config.DB_PATH))


async def init():
    """Створює файл бази та таблиці, якщо їх ще немає."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with _connect() as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.executescript(SCHEMA)
        try:
            await conn.execute("ALTER TABLE orders ADD COLUMN patronymic TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        await conn.commit()


def _order_dict(row):
    order = dict(row)
    order["number"] = order["id"] + config.ORDER_NUMBER_OFFSET
    return order


async def get_order(order_id):
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        order = _order_dict(row)
        async with conn.execute(
            "SELECT * FROM notes WHERE order_id = ? ORDER BY id ASC", (order_id,)
        ) as cur:
            order["notes"] = [dict(r) for r in await cur.fetchall()]
        return order


async def create_order(data):
    created = now_str()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            INSERT INTO orders
                (created_at, updated_at, name, patronymic, phone, city, delivery, payment,
                 comment, pack, price, qty, source, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """,
            (
                created,
                created,
                data.get("name", ""),
                data.get("patronymic", ""),
                data.get("phone", ""),
                data.get("city", ""),
                data.get("delivery", ""),
                data.get("payment", ""),
                data.get("comment", ""),
                data.get("pack", ""),
                int(data.get("price") or 0),
                int(data.get("qty") or 1),
                data.get("source", "landing"),
            ),
        )
        await conn.commit()
        order_id = cur.lastrowid
    return await get_order(order_id)


async def set_status(order_id, status, author="", cancel_reason=None):
    changed = now_str()
    async with _connect() as conn:
        await conn.execute(
            """
            UPDATE orders
               SET status = ?, updated_at = ?, cancel_reason = ?
             WHERE id = ?
            """,
            (status, changed, cancel_reason if status == "canceled" else None, order_id),
        )
        await conn.execute(
            "INSERT INTO status_history (order_id, status, changed_at, author) VALUES (?, ?, ?, ?)",
            (order_id, status, changed, author),
        )
        await conn.commit()
    return await get_order(order_id)


async def set_ttn(order_id, ttn):
    async with _connect() as conn:
        await conn.execute(
            "UPDATE orders SET ttn = ?, updated_at = ? WHERE id = ?",
            (ttn, now_str(), order_id),
        )
        await conn.commit()
    return await get_order(order_id)


async def add_note(order_id, text, author=""):
    async with _connect() as conn:
        await conn.execute(
            "INSERT INTO notes (order_id, created_at, author, text) VALUES (?, ?, ?, ?)",
            (order_id, now_str(), author, text),
        )
        await conn.execute(
            "UPDATE orders SET updated_at = ? WHERE id = ?", (now_str(), order_id)
        )
        await conn.commit()
    return await get_order(order_id)


async def list_orders(status=None, limit=10, offset=0):
    where = ""
    params = []
    if status and status != "all":
        where = "WHERE status = ?"
        params.append(status)
    params.extend([limit, offset])
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM orders {} ORDER BY id DESC LIMIT ? OFFSET ?".format(where),
            params,
        ) as cur:
            rows = await cur.fetchall()
    return [_order_dict(r) for r in rows]


async def count_orders(status=None):
    where = ""
    params = []
    if status and status != "all":
        where = "WHERE status = ?"
        params.append(status)
    async with _connect() as conn:
        async with conn.execute("SELECT COUNT(*) FROM orders {}".format(where), params) as cur:
            row = await cur.fetchone()
    return int(row[0]) if row else 0


async def search_orders(query, limit=20):
    query = (query or "").strip()
    if not query:
        return []
    like = "%{}%".format(query)
    conditions = [
        "name LIKE ?",
        "phone LIKE ?",
        "city LIKE ?",
        "delivery LIKE ?",
        "COALESCE(ttn, '') LIKE ?",
    ]
    params = [like, like, like, like, like]

    digits = query.lstrip("#")
    if digits.isdigit():
        conditions.append("id = ?")
        params.append(int(digits) - config.ORDER_NUMBER_OFFSET)

    digits_only = "".join(ch for ch in query if ch.isdigit())
    if len(digits_only) >= 7:
        tail = digits_only[-9:]
        conditions.append(
            "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(phone, ' ', ''), '-', ''), '(', ''), ')', ''), '+', '') LIKE ?"
        )
        params.append("%{}%".format(tail))

    params.append(limit)
    sql = "SELECT * FROM orders WHERE ({}) ORDER BY id DESC LIMIT ?".format(
        " OR ".join(conditions)
    )
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(sql, params) as cur:
            rows = await cur.fetchall()
    return [_order_dict(r) for r in rows]


async def stats():
    today = datetime.now(config.TZ)
    today_start = today.strftime("%Y-%m-%d 00:00:00")
    week_start = (today - timedelta(days=6)).strftime("%Y-%m-%d 00:00:00")
    month_start = (today - timedelta(days=29)).strftime("%Y-%m-%d 00:00:00")

    result = {"by_status": {}, "cancel_reasons": []}

    async with _connect() as conn:
        async with conn.execute("SELECT COUNT(*) FROM orders") as cur:
            result["total"] = int((await cur.fetchone())[0])

        async with conn.execute(
            "SELECT status, COUNT(*) FROM orders GROUP BY status"
        ) as cur:
            for status, count in await cur.fetchall():
                result["by_status"][status] = int(count)

        async with conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at >= ?", (today_start,)
        ) as cur:
            result["today"] = int((await cur.fetchone())[0])

        async with conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at >= ?", (week_start,)
        ) as cur:
            result["week"] = int((await cur.fetchone())[0])

        async with conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at >= ?", (month_start,)
        ) as cur:
            result["month"] = int((await cur.fetchone())[0])

        async with conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(price), 0), COALESCE(AVG(price), 0) "
            "FROM orders WHERE status = 'done'"
        ) as cur:
            done_count, revenue, avg_check = await cur.fetchone()
            result["done"] = int(done_count)
            result["revenue"] = int(revenue)
            result["avg_check"] = int(avg_check)

        async with conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'done' AND created_at >= ?",
            (today_start,),
        ) as cur:
            result["done_today"] = int((await cur.fetchone())[0])

        async with conn.execute(
            "SELECT cancel_reason, COUNT(*) FROM orders "
            "WHERE status = 'canceled' AND COALESCE(cancel_reason, '') <> '' "
            "GROUP BY cancel_reason ORDER BY COUNT(*) DESC LIMIT 5"
        ) as cur:
            result["cancel_reasons"] = [
                (reason, int(count)) for reason, count in await cur.fetchall()
            ]

    total = result["total"]
    result["conversion"] = (result["done"] / total * 100) if total else 0.0
    result["cancel_rate"] = (
        result["by_status"].get("canceled", 0) / total * 100 if total else 0.0
    )
    return result


async def export_rows():
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT o.*,
                   (SELECT GROUP_CONCAT(created_at || ' ' || text, ' | ')
                      FROM notes WHERE order_id = o.id) AS notes_text
              FROM orders o
             ORDER BY o.id DESC
            """
        ) as cur:
            rows = await cur.fetchall()
    return [_order_dict(r) for r in rows]
