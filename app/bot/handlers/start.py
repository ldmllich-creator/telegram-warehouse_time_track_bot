"""
Handlers: /start, /menu.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from app.bot.keyboards.main_keyboard import get_main_keyboard
from app.utils.messages import MSG_START
from app.config.settings import logger


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start and /menu commands."""
    user = update.effective_user
    logger.info("/start from %s (id=%s)", user.full_name, user.id)

    await update.message.reply_text(
        MSG_START,
        reply_markup=get_main_keyboard(),
    )


def get_handlers() -> list:
    """Return a list of handlers for registration."""
    return [
        CommandHandler("start", start_command),
        CommandHandler("menu", start_command),
    ]
