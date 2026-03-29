"""
Handlers: запуск и завершение процессов.

Новый flow:
1. Пользователь нажимает кнопку процесса (Разгрузка и т.д.)
2. Бот показывает список сотрудников (inline keyboard)
3. Пользователь выбирает сотрудника → процесс стартует

Для завершения:
1. Нажимает «Завершить процесс»
2. Бот показывает список сотрудников с активными процессами
3. Пользователь выбирает → процесс завершается
"""

from telegram import Update
from telegram.ext import (
    ContextTypes, MessageHandler, CallbackQueryHandler, CommandHandler, filters
)

from app.bot.keyboards.main_keyboard import (
    BTN_UNLOADING, BTN_RECEIVING, BTN_SORTING, BTN_PUTAWAY, BTN_FINISH,
    BUTTON_TO_PROCESS, get_main_keyboard,
)
from app.bot.keyboards.inline_keyboards import (
    CB_EMPLOYEE, CB_FINISH_EMPLOYEE,
    get_employee_keyboard, get_active_employees_keyboard,
)
from app.utils.messages import (
    MSG_PROCESS_STARTED, MSG_PROCESS_FINISHED,
    MSG_ALREADY_ACTIVE, MSG_NO_ACTIVE, MSG_ERROR,
    process_display_name,
)
from app.utils.roles import get_employee_by_id
from app.config.settings import logger


# Ссылка на сервис
_sheets_service = None


def init_service(service) -> None:
    """Инициализация ссылки на GoogleSheetsService."""
    global _sheets_service
    _sheets_service = service


# ------------------------------------------------------------------
# Шаг 1: Пользователь нажимает кнопку процесса → показываем список сотрудников
# ------------------------------------------------------------------
async def start_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатия кнопки запуска процесса."""
    text = update.message.text
    process_key = BUTTON_TO_PROCESS.get(text)
    if not process_key:
        return

    logger.info("Выбран процесс '%s', показываем список сотрудников", process_key)

    await update.message.reply_text(
        f"📦 Процесс: {process_display_name(process_key)}\n\n"
        f"👇 Выберите сотрудника:",
        reply_markup=get_employee_keyboard(process_key),
    )


# ------------------------------------------------------------------
# Шаг 2: Пользователь выбирает сотрудника → стартуем процесс
# ------------------------------------------------------------------
async def employee_selected_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Callback: выбран сотрудник для запуска процесса."""
    query = update.callback_query
    await query.answer()

    # Парсим: emp_{process_key}_{employee_id}
    data = query.data[len(CB_EMPLOYEE):]  # process_key_employee_id
    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        return

    process_key, emp_id_str = parts
    try:
        emp_id = int(emp_id_str)
    except ValueError:
        return

    employee = get_employee_by_id(emp_id)
    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден")
        return

    user = update.effective_user
    logger.info(
        "Запуск процесса '%s' для сотрудника '%s' (оператор: %s)",
        process_key, employee["name"], user.full_name,
    )

    try:
        row = _sheets_service.add_time_log(
            user_name=employee["name"],
            telegram_id=employee["id"],
            process=process_display_name(process_key),
            started_by=user.full_name,
        )
        await query.edit_message_text(
            MSG_PROCESS_STARTED.format(
                process=process_display_name(process_key),
                time=row["Начало"],
            )
            + f"\n👤 Сотрудник: {employee['name']}"
        )
    except ValueError:
        await query.edit_message_text(
            f"⚠️ У сотрудника {employee['name']} уже есть активный процесс.\n"
            "Сначала завершите текущий."
        )
    except Exception as e:
        logger.exception("Ошибка при запуске процесса: %s", e)
        await query.edit_message_text(MSG_ERROR)


# ------------------------------------------------------------------
# Завершение: показываем список активных сотрудников
# ------------------------------------------------------------------
async def finish_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки «Завершить процесс»."""
    logger.info("Запрос на завершение процесса")

    try:
        active = _sheets_service.get_all_active_processes()
        if not active:
            await update.message.reply_text(
                MSG_NO_ACTIVE,
                reply_markup=get_main_keyboard(),
            )
            return

        await update.message.reply_text(
            "👇 Выберите сотрудника для завершения:",
            reply_markup=get_active_employees_keyboard(active),
        )
    except Exception as e:
        logger.exception("Ошибка при получении активных процессов: %s", e)
        await update.message.reply_text(MSG_ERROR)


# ------------------------------------------------------------------
# Callback: завершение процесса для выбранного сотрудника
# ------------------------------------------------------------------
async def finish_employee_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Callback: завершить процесс выбранного сотрудника."""
    query = update.callback_query
    await query.answer()

    emp_id_str = query.data[len(CB_FINISH_EMPLOYEE):]
    try:
        emp_id = int(emp_id_str)
    except ValueError:
        return

    user = update.effective_user
    logger.info("Завершение процесса для сотрудника id=%s (оператор: %s)", emp_id, user.full_name)

    try:
        result = _sheets_service.finish_time_log(
            telegram_id=emp_id,
            finished_by=user.full_name,
        )

        if result is None:
            await query.edit_message_text("❌ Нет активного процесса для этого сотрудника.")
            return

        await query.edit_message_text(
            MSG_PROCESS_FINISHED.format(
                process=result["process"],
                start=result["start_time"],
                end=result["end_time"],
                minutes=result["duration_minutes"],
            )
        )
    except Exception as e:
        logger.exception("Ошибка при завершении процесса: %s", e)
        await query.edit_message_text(MSG_ERROR)


# ------------------------------------------------------------------
# Callback: отмена
# ------------------------------------------------------------------
async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback: отмена."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Действие отменено.")

    # Очистка группового состояния (если было)
    context.user_data.pop("group_selected", None)
    context.user_data.pop("group_selected_finish", None)
    context.user_data.pop("group_mode", None)


def get_handlers() -> list:
    """Возвращает список handlers для регистрации."""
    process_buttons = [BTN_UNLOADING, BTN_RECEIVING, BTN_SORTING, BTN_PUTAWAY]
    process_filter = filters.Text(process_buttons)

    return [
        MessageHandler(process_filter, start_process),
        MessageHandler(filters.Text([BTN_FINISH]), finish_process),
        CommandHandler("finish", finish_process),
        CallbackQueryHandler(employee_selected_callback, pattern=f"^{CB_EMPLOYEE}"),
        CallbackQueryHandler(finish_employee_callback, pattern=f"^{CB_FINISH_EMPLOYEE}"),
        CallbackQueryHandler(cancel_callback, pattern="^cancel$"),
    ]
