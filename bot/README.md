# 🤖 CRM-бот ТеплоПак

Telegram-бот із базовою CRM для замовлень з лендінгу: номери, клієнти, доставка, ТТН, коментарі, статуси та статистика. Працює на long polling + невелике HTTP API для сайту.

---

## 1. Що вміє

- Створює замовлення вручну з бота через `/new` або кнопку «➕ Нове замовлення» (нумерація спільна з сайтом).
- Номер телефону в картці — клікабельний (підтримка форматів +380, 0XX, 380…).
- Приймає замовлення з сайту через `POST /api/order` і зберігає їх у SQLite.
- Присвоює номер: `№1001`, `№1002`…
- Надсилає картку замовлення в Telegram з кнопками.
- Зміна статусу: 🆕 Нове → ⚙️ Опрацювання → 🚚 Доставка → ✅ Успішно / ❌ Відміна (з причиною).
- Додавання ТТН.
- Коментарі менеджера з автором і часом (історія зберігається).
- Статистика: кількість замовлень, розподіл за статусами, сьогодні / 7 / 30 днів, виторг, середній чек, конверсія, частка й причини скасувань.
- Список замовлень із фільтрами та пагінацією.
- Пошук за номером, телефоном, ім'ям, містом, ТТН.
- Експорт у CSV (відкривається в Excel).
- Доступ лише для `ADMIN_IDS`.

---

## 2. Структура

```
bot/
├── bot.py            # запуск: polling + HTTP API
├── api.py            # POST /api/order, GET /health
├── handlers.py       # команди, кнопки, FSM-діалоги
├── db.py             # SQLite
├── cards.py          # тексти карток
├── keyboards.py      # інлайн-клавіатури
├── stats.py          # текст статистики
├── config.py         # .env
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── data/orders.db    # створюється автоматично
```

---

## 3. Налаштування

```bash
cp .env.example .env
```

| Змінна | Опис |
|---|---|
| `BOT_TOKEN` | Токен від @BotFather |
| `ADMIN_IDS` | ID менеджерів через кому (хто має доступ) |
| `ADMIN_CHAT_ID` | Куди надсилати замовлення: ваш ID або ID групи (`-100…`) |
| `SITE_API_KEY` | Ключ для сайту (має збігатися з `BOT_API_KEY` у `js/config.js`) |
| `DB_PATH` | Шлях до бази (за замовчуванням `data/orders.db`) |
| `API_HOST` / `API_PORT` | Адреса HTTP API (за замовчуванням `0.0.0.0:8080`) |
| `TIMEZONE` | Часовий пояс (за замовчуванням `Europe/Kyiv`) |

> **Група для замовлень:** створіть групу, додайте бота, зробіть його адміністратором (або дозвольте писати), дізнайтеся ID групи (наприклад, через @getmyid_bot) і вкажіть його в `ADMIN_CHAT_ID`. Усі менеджери з `ADMIN_IDS` зможуть натискати кнопки в цій групі.

---

## 4. Запуск

### Локально / на VPS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

### Docker
```bash
docker compose up -d --build
docker compose logs -f
```
База зберігається в `./data` (volume), тому переживає перезапуск контейнера.

### systemd (приклад)
```ini
[Unit]
Description=TeploPak CRM Bot
After=network.target

[Service]
WorkingDirectory=/opt/teplopak/bot
ExecStart=/opt/teplopak/bot/.venv/bin/python bot.py
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

---

## 5. HTTP API

### `POST /api/order`

Заголовки:
```
Content-Type: application/json
X-API-Key: <SITE_API_KEY>
```

Тіло:
```json
{
  "name": "Олександр Коваль",
  "phone": "+380 (97) 123-45-67",
  "city": "Київ",
  "delivery": "Нова Пошта №25",
  "payment": "Накладений платіж",
  "comment": "Передзвоніть після 18:00",
  "pack": "2 шт — Комплект «Для двох рук» (329 грн)",
  "price": 329,
  "qty": 2,
  "source": "landing"
}
```

Відповідь:
```json
{ "success": true, "order_id": 1, "order_number": 1001 }
```

Помилки: `400` — невалідні дані, `401` — невірний ключ, `429` — забагато запитів, `503` — не заданий `SITE_API_KEY`.

### `GET /health`
```json
{ "ok": true, "orders": 42, "time": "2026-11-08 14:35:00" }
```

> API не має власної авторизації користувачів — захищайте його ключем і HTTPS. Порт `8080` краще не відкривати напряму, а поставити перед ним Caddy/Nginx із TLS.

---

## 6. Статуси

| Код | Відображення | Коли використовувати |
|---|---|---|
| `new` | 🆕 Нове | Щойно надійшло |
| `processing` | ⚙️ Опрацювання | Підтверджуємо, збираємо |
| `shipping` | 🚚 Доставка | Передано в НП/Укрпошту |
| `done` | ✅ Успішно | Клієнт отримав і оплатив |
| `canceled` | ❌ Відміна | Відмова; бот вимагає причину |

При зміні статусу в базі також пишеться історія (`status_history`).

---

## 7. База даних

SQLite, файл `data/orders.db`.

- `orders` — замовлення (номер = `id + 1000`, дата, клієнт, доставка, сума, ТТН, статус, причина відміни).
- `notes` — коментарі менеджерів.
- `status_history` — історія змін статусів.

Переглянути вручну:
```bash
sqlite3 data/orders.db "SELECT id+1000 AS number, created_at, name, status FROM orders ORDER BY id DESC LIMIT 10;"
```

Бекап:
```bash
cp data/orders.db "backup_$(date +%F).db"
```

---

## 8. Перевірка без Telegram

```bash
curl -X POST http://127.0.0.1:8080/api/order \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-please" \
  -d '{"name":"Тест","phone":"+380671112233","city":"Київ","delivery":"НП №1","pack":"1 шт","price":189,"qty":1}'
```

Якщо у відповіді є `order_number`, а в Telegram прийшла картка — все працює.

---

## 9. Часті проблеми

| Проблема | Причина |
|---|---|
| Бот мовчить | Не натиснуто `/start`; ваш ID не в `ADMIN_IDS` |
| Замовлення не приходять у чат | Невірний `ADMIN_CHAT_ID`, бот не в групі, немає прав писати |
| `401` від API | `X-API-Key` не збігається з `SITE_API_KEY` |
| `503` від API | Порожній `SITE_API_KEY` у `.env` |
| Сайт не може достукатися | API недоступне, HTTP замість HTTPS, неправильний URL |
| `database is locked` | Запущено два екземпляри бота на одній базі |
