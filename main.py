"""
Точка входа — запуск Telegram-бота.

Инициализирует сервисы, регистрирует handlers и запускает polling.
"""

from telegram import BotCommand
from telegram.ext import ApplicationBuilder

from app.config.settings import BOT_TOKEN, logger
from app.services.google_sheets_service import GoogleSheetsService

# Handlers
from app.bot.handlers import start, process_handlers, status_handlers, group_handlers


def main() -> None:
    """Инициализация и запуск бота."""
    logger.info("=" * 50)
    logger.info("Запуск бота учёта рабочего времени...")
    logger.info("=" * 50)

    # 1. Инициализация Google Sheets
    sheets_service = GoogleSheetsService()

    # Инжектим сервис в handlers
    process_handlers.init_service(sheets_service)
    status_handlers.init_service(sheets_service)
    group_handlers.init_service(sheets_service)

    # 2. Создание Telegram Application
    async def post_init(application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start", "Начать работу"),
        ])
        logger.info("Команды бота установлены ✅")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # 3. Регистрация handlers
    for handler in start.get_handlers():
        app.add_handler(handler)
    for handler in process_handlers.get_handlers():
        app.add_handler(handler)
    for handler in status_handlers.get_handlers():
        app.add_handler(handler)
    for handler in group_handlers.get_handlers():
        app.add_handler(handler)

    logger.info("Все handlers зарегистрированы ✅")

    # 4. Запуск polling
    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
