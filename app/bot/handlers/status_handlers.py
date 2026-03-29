"""
Handlers: статус и дневной отчёт.

/status — текущий активный процесс
/myday — все записи за сегодня
"""

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, filters

from app.bot.keyboards.main_keyboard import (
    BTN_STATUS, BTN_MYDAY, get_main_keyboard,
)
from app.utils.messages import (
    MSG_STATUS, MSG_MYDAY_HEADER, MSG_MYDAY_EMPTY,
    MSG_MYDAY_FOOTER, MSG_NO_ACTIVE, MSG_ERROR,
)
from app.config.settings import logger, STATUS_ACTIVE


_sheets_service = None


def init_service(service) -> None:
    global _sheets_service
    _sheets_service = service


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/status от %s", update.effective_user.full_name)
    try:
        active = _sheets_service.get_all_active_processes()
        if not active:
            await update.message.reply_text("📊 Нет активных процессов", reply_markup=get_main_keyboard())
            return
        lines = ["📊 Активные процессы:\n"]
        for item in active:
            lines.append(f"👤 {item['user_name']} — {item['process']} (с {item['start_time']})")
        await update.message.reply_text("\n".join(lines), reply_markup=get_main_keyboard())
    except Exception as e:
        logger.exception("Ошибка при получении статуса: %s", e)
        await update.message.reply_text(MSG_ERROR)


async def myday_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("/myday от %s", update.effective_user.full_name)
    try:
        logs = _sheets_service.get_today_all_logs()
        if not logs:
            await update.message.reply_text(MSG_MYDAY_EMPTY, reply_markup=get_main_keyboard())
            return
        lines = [MSG_MYDAY_HEADER]
        total_minutes = 0
        for log in logs:
            status_icon = "🟢" if log["status"] == STATUS_ACTIVE else "✅"
            duration = log["duration_minutes"]
            duration_str = f"{duration} мин" if duration else "в работе..."
            if duration:
                try:
                    total_minutes += float(duration)
                except (ValueError, TypeError):
                    pass
            lines.append(f"{status_icon} {log['user_name']} — {log['process']} | {duration_str}")
        if total_minutes > 0:
            hours = int(total_minutes // 60)
            mins = int(total_minutes % 60)
            total_str = f"{hours}ч {mins}мин" if hours else f"{mins} мин"
            lines.append(MSG_MYDAY_FOOTER.format(total_time=total_str))
        await update.message.reply_text("\n".join(lines), reply_markup=get_main_keyboard())
    except Exception as e:
        logger.exception("Ошибка при получении отчёта: %s", e)
        await update.message.reply_text(MSG_ERROR)


def get_handlers() -> list:
    return [
        MessageHandler(filters.Text([BTN_STATUS]), status_command),
        CommandHandler("status", status_command),
        MessageHandler(filters.Text([BTN_MYDAY]), myday_command),
        CommandHandler("myday", myday_command),
    ]
