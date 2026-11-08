"""Обробники команд та кнопок CRM-бота."""

import csv
import io
import logging
import re
from datetime import datetime
from math import ceil

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

import cards
import config
import db
import keyboards
import stats as stats_module

log = logging.getLogger(__name__)

PAGE_SIZE = 8

router = Router(name="crm")


class IsAdmin(BaseFilter):
    """Пропускає лише користувачів зі списку ADMIN_IDS."""

    async def __call__(self, event):
        user = getattr(event, "from_user", None)
        return bool(user and user.id in config.ADMIN_IDS)


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class Flow(StatesGroup):
    ttn = State()
    comment = State()
    cancel = State()
    search = State()
    new_name = State()
    new_patronymic = State()
    new_phone = State()
    new_city = State()
    new_delivery = State()
    new_payment = State()
    new_pack = State()
    new_price = State()
    new_comment = State()
    new_preview = State()



def _author(user):
    if not user:
        return ""
    name = getattr(user, "full_name", None) or getattr(user, "username", None)
    return name or str(user.id)


async def _safe_edit(message, text, markup):
    """Редагує повідомлення; повертає False, якщо це неможливо."""
    if not message or not hasattr(message, "edit_text"):
        return False
    try:
        await message.edit_text(text, reply_markup=markup)
        return True
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return True
        return False
    except Exception:
        log.exception("Не вдалося відредагувати повідомлення")
        return False


async def _edit_card(bot, data, order):
    """Оновлює картку замовлення, до якої була прив'язана дія."""
    chat_id = data.get("card_chat")
    message_id = data.get("card_msg")
    text = cards.build_order_text(order)
    markup = keyboards.order_keyboard(order)

    if chat_id and message_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup,
            )
            return
        except Exception:
            pass

    if chat_id:
        try:
            await bot.send_message(chat_id, text, reply_markup=markup)
        except Exception:
            log.exception("Не вдалося оновити картку замовлення")


async def _finish_flow(message, state, data, order, confirmation):
    await state.clear()
    await _edit_card(message.bot, data, order)

    prompt_chat = data.get("prompt_chat")
    prompt_msg = data.get("prompt_msg")
    if prompt_chat and prompt_msg:
        try:
            await message.bot.edit_message_text(
                chat_id=prompt_chat, message_id=prompt_msg, text=confirmation
            )
        except Exception:
            pass

    try:
        await message.delete()
    except Exception:
        pass


async def _render_list(bot, chat_id, status, page, edit_message=None):
    status = status or "all"
    total = await db.count_orders(status)
    pages = max(1, ceil(total / PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    orders = await db.list_orders(status, PAGE_SIZE, page * PAGE_SIZE)

    text = cards.build_list_text(status, orders, total, page, pages)
    markup = keyboards.list_keyboard(status, page, pages, orders)

    if edit_message is not None:
        if await _safe_edit(edit_message, text, markup):
            return
    await bot.send_message(chat_id, text, reply_markup=markup)


async def _send_stats(bot, chat_id, edit_message=None):
    data = await db.stats()
    text = stats_module.build_stats_text(data)
    markup = keyboards.menu_keyboard()
    if edit_message is not None and await _safe_edit(edit_message, text, markup):
        return
    await bot.send_message(chat_id, text, reply_markup=markup)


async def _send_export(bot, chat_id):
    rows = await db.export_rows()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "Номер",
            "Дата створення",
            "Статус",
            "Клієнт",
            "По батькові",
            "Телефон",
            "Місто",
            "Доставка",
            "Оплата",
            "Комплект",
            "К-сть",
            "Сума, грн",
            "ТТН",
            "Причина відміни",
            "Коментар клієнта",
            "Коментарі менеджера",
        ]
    )
    for order in rows:
        writer.writerow(
            [
                order.get("number"),
                order.get("created_at"),
                cards.status_label(order.get("status")),
                order.get("name"),
                order.get("patronymic") or "",
                order.get("phone"),
                order.get("city"),
                order.get("delivery"),
                order.get("payment"),
                order.get("pack"),
                order.get("qty"),
                order.get("price"),
                order.get("ttn") or "",
                order.get("cancel_reason") or "",
                order.get("comment") or "",
                order.get("notes_text") or "",
            ]
        )

    payload = output.getvalue().encode("utf-8-sig")
    filename = "orders_{}.csv".format(datetime.now(config.TZ).strftime("%Y-%m-%d_%H-%M"))
    document = BufferedInputFile(payload, filename=filename)
    await bot.send_document(
        chat_id,
        document,
        caption="📤 Експорт замовлень: {}".format(len(rows)),
    )


# ---------------------------------------------------------------------------
# Нове замовлення (FSM)
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "menu:new")
async def cb_new_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Flow.new_name)
    prompt = await callback.message.answer(
        "👤 <b>Нове замовлення</b>\n\nНапишіть ПІБ клієнта:",
        reply_markup=keyboards.abort_keyboard(),
    )
    await state.update_data(prompt_chat=prompt.chat.id, prompt_msg=prompt.message_id)
    await callback.answer()


@router.message(Flow.new_name)
async def flow_new_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.reply("Вкажіть імʼя клієнта (мінімум 2 символи).")
        return
    await state.update_data(name=name)
    await state.set_state(Flow.new_patronymic)
    await message.answer(
        "👤 Імʼя: <b>{}</b>\n\nПо батькові (необов'язково). Якщо немає — пропустіть:".format(cards.e(name)),
        reply_markup=keyboards.skip_keyboard("np:skip_patronymic"),
    )


@router.message(Flow.new_patronymic)
async def flow_new_patronymic(message: Message, state: FSMContext):
    patronymic = (message.text or "").strip()[:60]
    await state.update_data(patronymic=patronymic)
    await state.set_state(Flow.new_phone)
    await message.answer(
        "📞 Напишіть телефон клієнта (напр. 0671234567):",
        reply_markup=keyboards.abort_keyboard(),
    )


@router.callback_query(Flow.new_patronymic, F.data == "np:skip_patronymic")
async def flow_new_patronymic_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(patronymic="")
    await state.set_state(Flow.new_phone)
    await callback.message.answer(
        "📞 Напишіть телефон клієнта (напр. 0671234567):",
        reply_markup=keyboards.abort_keyboard(),
    )
    await callback.answer()


@router.message(Flow.new_phone)
async def flow_new_phone(message: Message, state: FSMContext):
    phone = (message.text or "").strip()
    normalized = cards.normalize_phone(phone)
    if not normalized:
        await message.reply("Некоректний номер. Спробуйте ще раз (напр. 0671234567):")
        return
    await state.update_data(phone=normalized)
    await state.set_state(Flow.new_city)
    await message.answer(
        "✅ Телефон: {}\n\n📍 Місто клієнта:".format(cards.format_phone(normalized)),
        reply_markup=keyboards.abort_keyboard(),
    )


@router.message(Flow.new_city)
async def flow_new_city(message: Message, state: FSMContext):
    city = (message.text or "").strip()
    await state.update_data(city=city)
    await state.set_state(Flow.new_delivery)
    await message.answer("🚚 Відділення / спосіб доставки:", reply_markup=keyboards.abort_keyboard())


@router.message(Flow.new_delivery)
async def flow_new_delivery(message: Message, state: FSMContext):
    delivery = (message.text or "").strip()
    await state.update_data(delivery=delivery)
    await state.set_state(Flow.new_payment)
    await message.answer("💳 Оберіть спосіб оплати:", reply_markup=keyboards.payment_keyboard())


@router.callback_query(Flow.new_payment, F.data.startswith("np:pay:"))
async def flow_new_payment(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[2]
    if val == "other":
        await state.set_state(Flow.new_payment)  # чекаємо текст
        await callback.message.edit_text("✍️ Напишіть спосіб оплати:", reply_markup=keyboards.abort_keyboard())
    else:
        payment = config.PAYMENTS.get(val, "—")
        await state.update_data(payment=payment)
        await state.set_state(Flow.new_pack)
        await callback.message.edit_text("📦 Оберіть комплект:", reply_markup=keyboards.pack_keyboard())
    await callback.answer()


@router.message(Flow.new_payment)
async def flow_new_payment_text(message: Message, state: FSMContext):
    payment = (message.text or "").strip()
    await state.update_data(payment=payment)
    await state.set_state(Flow.new_pack)
    await message.answer("📦 Оберіть комплект:", reply_markup=keyboards.pack_keyboard())


@router.callback_query(Flow.new_pack, F.data.startswith("np:pack:"))
async def flow_new_pack(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[2]
    if val == "other":
        await state.set_state(Flow.new_pack) # просто мітка, чекаємо текст
        await callback.message.edit_text("✍️ Напишіть комплект і ціну:", reply_markup=keyboards.abort_keyboard())
    else:
        pack_data = next((p for p in config.PACKS if p[0] == val), None)
        if pack_data:
            await state.update_data(pack=pack_data[1], price=pack_data[2], qty=int(pack_data[0]))
            await state.set_state(Flow.new_comment)
            await callback.message.edit_text(
                "📦 Комплект: <b>{}</b>\n💰 Сума: <b>{} грн</b>".format(
                    cards.e(pack_data[1]), pack_data[2]
                )
            )
            await callback.message.answer(
                "Крок 6/6. Додайте коментар до замовлення або пропустіть:",
                reply_markup=keyboards.comment_skip_keyboard(),
            )
        else:
            await callback.answer("Помилка", show_alert=True)
    await callback.answer()


@router.message(Flow.new_pack)
async def flow_new_pack_text(message: Message, state: FSMContext):
    pack = (message.text or "").strip()
    if len(pack) < 2:
        await message.reply("Введіть назву комплекту (мінімум 2 символи).")
        return
    await state.update_data(pack=pack)
    await state.set_state(Flow.new_price)
    await message.answer(
        "💰 Введіть суму замовлення в гривнях (тільки число):",
        reply_markup=keyboards.abort_keyboard(),
    )


@router.message(Flow.new_price)
async def flow_new_price(message: Message, state: FSMContext):
    raw = (message.text or "").strip().replace(" ", "").replace("грн", "").replace(",", ".")
    try:
        price = int(float(raw))
    except ValueError:
        await message.reply("Введіть число, напр. 450")
        return
    if price <= 0 or price > 1_000_000:
        await message.reply("Сума має бути від 1 до 1 000 000 грн.")
        return
    data = await state.get_data()
    qty_match = re.search(r"(\\d+)\\s*шт", data.get("pack", ""))
    qty = int(qty_match.group(1)) if qty_match else 1
    await state.update_data(price=price, qty=qty)
    await state.set_state(Flow.new_comment)
    await message.answer(
        "Крок 6/6. Додайте коментар до замовлення або пропустіть:",
        reply_markup=keyboards.comment_skip_keyboard(),
    )


@router.message(Flow.new_comment)
async def flow_new_comment(message: Message, state: FSMContext):
    comment = (message.text or "").strip()[:500]
    await state.update_data(comment=comment)
    await _preview_new(message, state)


@router.callback_query(Flow.new_comment, F.data == "np:skip_comment")
async def flow_new_comment_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(comment="")
    await _preview_new(callback.message, state)
    await callback.answer()


async def _preview_new(message: Message, state: FSMContext):
    data = await state.get_data()
    name_line = data["name"]
    if data.get("patronymic"):
        name_line += " " + data["patronymic"]
    text = (
        "👀 <b>Перевірка замовлення</b>\n\n"
        "👤 {}\n📞 {}\n".format(name_line, cards.format_phone(data["phone"])) +
        "📍 {}\n🚚 {}\n".format(data["city"], data["delivery"]) +
        "💳 {}\n📦 {} ({} грн)".format(data["payment"], data["pack"], data["price"])
    )
    await state.set_state(Flow.new_preview)
    await message.answer(text, reply_markup=keyboards.new_preview_keyboard())


@router.callback_query(Flow.new_preview, F.data == "np:save")
async def flow_new_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order = await db.create_order(
        {
            "name": data["name"],
            "patronymic": data.get("patronymic", ""),
            "phone": data["phone"],
            "city": data["city"],
            "delivery": data["delivery"],
            "payment": data.get("payment", ""),
            "pack": data.get("pack", ""),
            "price": int(data.get("price") or 0),
            "qty": int(data.get("qty") or 1),
            "source": "bot",
        }
    )
    await state.clear()
    text = cards.build_order_text(order)
    markup = keyboards.order_keyboard(order)
    if not await _safe_edit(callback.message, text, markup):
        await callback.message.answer(text, reply_markup=markup)
    if config.ADMIN_CHAT_ID and config.ADMIN_CHAT_ID != callback.message.chat.id:
        try:
            await callback.bot.send_message(
                config.ADMIN_CHAT_ID, text, reply_markup=markup
            )
        except Exception:
            log.exception("Не вдалося надіслати створене замовлення в ADMIN_CHAT_ID")
    await callback.answer("✅ Створено №{}".format(order["number"]))


@router.callback_query(Flow.new_preview, F.data == "np:restart")
async def flow_new_restart(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Flow.new_name)
    await callback.message.answer(
        "👤 <b>Нове замовлення</b>\n\nНапишіть ПІБ клієнта:",
        reply_markup=keyboards.abort_keyboard(),
    )
    await callback.answer()


@router.callback_query(Flow.new_preview, F.data == "abort")
async def flow_new_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Створення замовлення скасовано.")
    await callback.answer()


@router.message(Command("start"))
async def cmd_start(message: Message):
    data = await db.stats()
    await message.answer(cards.build_menu_text(data), reply_markup=keyboards.menu_keyboard())


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext):
    await state.set_state(Flow.new_name)
    await message.answer(
        "👤 <b>Нове замовлення</b>\n\nНапишіть ПІБ клієнта:",
        reply_markup=keyboards.abort_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "🤖 <b>CRM ТеплоПак — довідка</b>\n\n"
        "/new — створити замовлення вручну\n"
        "/orders — список замовлень\n"
        "/stats — статистика\n"
        "/find <i>запит</i> — пошук за номером, телефоном, ім'ям або ТТН\n"
        "/export — експорт усіх замовлень у CSV\n"
        "/cancel — скасувати поточну дію\n\n"
        "У картці замовлення можна змінювати статус, додавати ТТН і коментарі.\n"
        "Телефон у картці — клікабельний, натисніть щоб подзвонити."
    )
    await message.answer(text)


@router.message(Command("orders"))
async def cmd_orders(message: Message):
    await _render_list(message.bot, message.chat.id, "all", 0)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    await _send_stats(message.bot, message.chat.id)


@router.message(Command("export"))
async def cmd_export(message: Message):
    await _send_export(message.bot, message.chat.id)


@router.message(Command("find"))
async def cmd_find(message: Message, state: FSMContext):
    query = (message.text or "").partition(" ")[2].strip()
    if query:
        orders = await db.search_orders(query)
        await message.answer(
            cards.build_search_text(query, orders),
            reply_markup=keyboards.search_keyboard(orders),
        )
        return

    await state.set_state(Flow.search)
    prompt = await message.answer(
        "🔍 Надішліть номер замовлення, телефон, ім'я або ТТН:",
        reply_markup=keyboards.abort_keyboard(),
    )
    await state.update_data(prompt_chat=prompt.chat.id, prompt_msg=prompt.message_id)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("↩️ Дію скасовано.")


# ---------------------------------------------------------------------------
# Меню
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "menu:main")
async def cb_menu(callback: CallbackQuery):
    data = await db.stats()
    await _safe_edit(
        callback.message, cards.build_menu_text(data), keyboards.menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "menu:orders")
async def cb_menu_orders(callback: CallbackQuery):
    await _render_list(
        callback.bot, callback.message.chat.id, "all", 0, callback.message
    )
    await callback.answer()


@router.callback_query(F.data == "menu:stats")
async def cb_menu_stats(callback: CallbackQuery):
    await _send_stats(callback.bot, callback.message.chat.id, callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu:find")
async def cb_menu_find(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Flow.search)
    prompt = await callback.message.answer(
        "🔍 Надішліть номер замовлення, телефон, ім'я або ТТН:",
        reply_markup=keyboards.abort_keyboard(),
    )
    await state.update_data(prompt_chat=prompt.chat.id, prompt_msg=prompt.message_id)
    await callback.answer()


@router.callback_query(F.data == "menu:export")
async def cb_menu_export(callback: CallbackQuery):
    await callback.answer("📤 Формую файл…")
    await _send_export(callback.bot, callback.message.chat.id)


# ---------------------------------------------------------------------------
# Список замовлень
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("list:"))
async def cb_list(callback: CallbackQuery):
    parts = callback.data.split(":")
    status = parts[1] if len(parts) > 1 else "all"
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    await _render_list(
        callback.bot, callback.message.chat.id, status, page, callback.message
    )
    await callback.answer()


@router.callback_query(F.data.startswith("open:"))
async def cb_open(callback: CallbackQuery):
    try:
        order_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некоректне замовлення", show_alert=True)
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Замовлення не знайдено", show_alert=True)
        return

    await callback.message.answer(
        cards.build_order_text(order), reply_markup=keyboards.order_keyboard(order)
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Картка замовлення
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("refresh:"))
async def cb_refresh(callback: CallbackQuery):
    try:
        order_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некоректне замовлення", show_alert=True)
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Замовлення не знайдено", show_alert=True)
        return

    await _safe_edit(
        callback.message, cards.build_order_text(order), keyboards.order_keyboard(order)
    )
    await callback.answer("Оновлено")


@router.callback_query(F.data.startswith("st:"))
async def cb_status(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) != 3 or parts[2] not in config.STATUSES:
        await callback.answer("Некоректний статус", show_alert=True)
        return

    try:
        order_id = int(parts[1])
    except ValueError:
        await callback.answer("Некоректне замовлення", show_alert=True)
        return

    status = parts[2]
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Замовлення не знайдено", show_alert=True)
        return

    if status == "canceled":
        await state.set_state(Flow.cancel)
        await state.update_data(
            order_id=order_id,
            card_chat=callback.message.chat.id,
            card_msg=callback.message.message_id,
        )
        prompt = await callback.message.answer(
            "❌ <b>Відміна замовлення №{}</b>\n\n"
            "Вкажіть причину відміни одним повідомленням:".format(order["number"]),
            reply_markup=keyboards.abort_keyboard(),
        )
        await state.update_data(prompt_chat=prompt.chat.id, prompt_msg=prompt.message_id)
        await callback.answer()
        return

    order = await db.set_status(order_id, status, _author(callback.from_user))
    await _safe_edit(
        callback.message, cards.build_order_text(order), keyboards.order_keyboard(order)
    )
    await callback.answer("Статус: {}".format(cards.status_label(status)))


@router.callback_query(F.data.startswith("ttn:"))
async def cb_ask_ttn(callback: CallbackQuery, state: FSMContext):
    try:
        order_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некоректне замовлення", show_alert=True)
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Замовлення не знайдено", show_alert=True)
        return

    await state.set_state(Flow.ttn)
    await state.update_data(
        order_id=order_id,
        card_chat=callback.message.chat.id,
        card_msg=callback.message.message_id,
    )
    prompt = await callback.message.answer(
        "✏️ <b>ТТН для замовлення №{}</b>\n\n"
        "Надішліть номер ТТН одним повідомленням:".format(order["number"]),
        reply_markup=keyboards.abort_keyboard(),
    )
    await state.update_data(prompt_chat=prompt.chat.id, prompt_msg=prompt.message_id)
    await callback.answer()


@router.callback_query(F.data.startswith("cmt:"))
async def cb_ask_comment(callback: CallbackQuery, state: FSMContext):
    try:
        order_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некоректне замовлення", show_alert=True)
        return

    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Замовлення не знайдено", show_alert=True)
        return

    await state.set_state(Flow.comment)
    await state.update_data(
        order_id=order_id,
        card_chat=callback.message.chat.id,
        card_msg=callback.message.message_id,
    )
    prompt = await callback.message.answer(
        "💬 <b>Коментар до замовлення №{}</b>\n\n"
        "Надішліть текст коментаря одним повідомленням:".format(order["number"]),
        reply_markup=keyboards.abort_keyboard(),
    )
    await state.update_data(prompt_chat=prompt.chat.id, prompt_msg=prompt.message_id)
    await callback.answer()


# ---------------------------------------------------------------------------
# Введення даних (FSM)
# ---------------------------------------------------------------------------


@router.message(Flow.ttn)
async def flow_ttn(message: Message, state: FSMContext):
    ttn = (message.text or "").strip()
    if not 4 <= len(ttn) <= 40:
        await message.reply(
            "Введіть номер ТТН (4–40 символів) або натисніть «Скасувати»."
        )
        return

    data = await state.get_data()
    order = await db.set_ttn(data["order_id"], ttn)
    await _finish_flow(message, state, data, order, "✅ ТТН збережено")


@router.message(Flow.comment)
async def flow_comment(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.reply("Коментар не може бути порожнім.")
        return
    if len(text) > 500:
        text = text[:500]

    data = await state.get_data()
    order = await db.add_note(data["order_id"], text, _author(message.from_user))
    await _finish_flow(message, state, data, order, "✅ Коментар додано")


@router.message(Flow.cancel)
async def flow_cancel(message: Message, state: FSMContext):
    reason = (message.text or "").strip()
    if len(reason) < 2:
        await message.reply("Вкажіть причину відміни (мінімум 2 символи).")
        return

    data = await state.get_data()
    order = await db.set_status(
        data["order_id"], "canceled", _author(message.from_user), cancel_reason=reason[:300]
    )
    await _finish_flow(message, state, data, order, "❌ Замовлення відмінено")


@router.message(Flow.search)
async def flow_search(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    await state.clear()

    orders = await db.search_orders(query)
    await message.answer(
        cards.build_search_text(query, orders),
        reply_markup=keyboards.search_keyboard(orders),
    )


@router.callback_query(F.data == "abort")
async def cb_abort(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _safe_edit(callback.message, "↩️ Дію скасовано.", None)
    await callback.answer("Скасовано")


@router.message(F.text, ~F.text.startswith("/"))
async def fallback(message: Message):
    await message.answer("Скористайтеся меню 👇", reply_markup=keyboards.menu_keyboard())
