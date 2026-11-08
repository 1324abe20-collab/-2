"""Точка входу CRM-бота ТеплоПак.

Запускає Telegram-бота (long polling) та HTTP API для сайту.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiohttp import web

import api
import config
import db
from handlers import router

log = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="Головне меню"),
    BotCommand(command="new", description="Створити замовлення"),
    BotCommand(command="orders", description="Список замовлень"),
    BotCommand(command="stats", description="Статистика"),
    BotCommand(command="find", description="Пошук замовлення"),
    BotCommand(command="export", description="Експорт у CSV"),
    BotCommand(command="cancel", description="Скасувати дію"),
]


def _validate_config():
    problems = []
    if not config.BOT_TOKEN:
        problems.append("BOT_TOKEN не вказано")
    if not config.ADMIN_IDS:
        problems.append("ADMIN_IDS не вказано (кому дозволено користуватися ботом)")
    if not config.ADMIN_CHAT_ID:
        problems.append("ADMIN_CHAT_ID не вказано (куди надсилати замовлення)")
    if not config.SITE_API_KEY:
        log.warning(
            "SITE_API_KEY не вказано — HTTP API для сайту буде недоступне "
            "(замовлення з сайту не створюватимуться)."
        )
    if problems:
        raise SystemExit("Помилка конфігурації: " + "; ".join(problems))


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    _validate_config()
    await db.init()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    try:
        await bot.set_my_commands(COMMANDS)
    except Exception:
        log.warning("Не вдалося оновити список команд бота", exc_info=True)

    app = api.create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.API_HOST, config.API_PORT)
    await site.start()
    log.info("HTTP API слухає http://%s:%s", config.API_HOST, config.API_PORT)
    log.info("База даних: %s", config.DB_PATH)

    try:
        await dispatcher.start_polling(
            bot, allowed_updates=dispatcher.resolve_used_update_types()
        )
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as exc:
        if isinstance(exc, SystemExit) and exc.code:
            print(exc)
