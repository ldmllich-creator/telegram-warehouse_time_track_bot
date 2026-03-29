"""
Handlers: групповой режим (/group_start, /group_finish).
Только для supervisor / admin.
Multi-select сотрудников через inline keyboard.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.bot.keyboards.inline_keyboards import (
    get_worker_select_keyboard, get_process_select_keyboard,
    CB_SELECT_WORKER, CB_DONE_SELECT, CB_SELECT_PROCESS,
    CB_CONFIRM_YES, CB_CONFIRM_NO, CB_FINISH_WORKER, CB_FINISH_DONE,
)
from app.utils.messages import (
    MSG_GROUP_SELECT_WORKERS, MSG_GROUP_SELECT_PROCESS,
    MSG_GROUP_STARTED, MSG_GROUP_FINISHED, MSG_GROUP_CONFLICT,
    MSG_ACCESS_DENIED, MSG_GROUP_NOBODY_SELECTED,
    MSG_GROUP_NO_ACTIVE_TO_FINISH, MSG_ERROR, process_display_name,
)
from app.utils.roles import is_supervisor_or_admin, get_worker_by_id
from app.config.settings import logger

_sheets_service = None

def init_service(service) -> None:
    global _sheets_service
    _sheets_service = service

async def group_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_supervisor_or_admin(user.id):
        await update.message.reply_text(MSG_ACCESS_DENIED)
        return
    context.user_data["group_selected"] = set()
    context.user_data["group_mode"] = "start"
    await update.message.reply_text(MSG_GROUP_SELECT_WORKERS, reply_markup=get_worker_select_keyboard())

async def group_finish_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_supervisor_or_admin(user.id):
        await update.message.reply_text(MSG_ACCESS_DENIED)
        return
    context.user_data["group_selected_finish"] = set()
    context.user_data["group_mode"] = "finish"
    await update.message.reply_text(MSG_GROUP_SELECT_WORKERS, reply_markup=get_worker_select_keyboard(finish_mode=True))

async def toggle_worker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    worker_id = int(query.data.replace(CB_SELECT_WORKER, ""))
    selected: set = context.user_data.setdefault("group_selected", set())
    if worker_id in selected:
        selected.discard(worker_id)
    else:
        selected.add(worker_id)
    await query.edit_message_reply_markup(reply_markup=get_worker_select_keyboard(selected_ids=selected))

async def done_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    selected: set = context.user_data.get("group_selected", set())
    if not selected:
        await query.edit_message_text(MSG_GROUP_NOBODY_SELECTED)
        return
    await query.edit_message_text(MSG_GROUP_SELECT_PROCESS, reply_markup=get_process_select_keyboard())

async def select_process_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    process_key = query.data.replace(CB_SELECT_PROCESS, "")
    selected: set = context.user_data.get("group_selected", set())
    supervisor = update.effective_user
    logger.info("Групповой старт: supervisor=%s process=%s workers=%s", supervisor.full_name, process_key, selected)
    results, conflicts = [], []
    for worker_id in selected:
        worker = get_worker_by_id(worker_id)
        if worker is None:
            continue
        try:
            _sheets_service.add_time_log(user_name=worker["name"], telegram_id=worker["id"], process=process_display_name(process_key), started_by=f"supervisor: {supervisor.full_name}")
            results.append(f"✅ {worker['name']}")
        except ValueError:
            conflicts.append(worker["name"])
        except Exception as e:
            logger.exception("Ошибка группового старта для %s: %s", worker["name"], e)
            results.append(f"❌ {worker['name']} — ошибка")
    text_parts = []
    if results:
        text_parts.append(MSG_GROUP_STARTED.format(results="\n".join(results)))
    if conflicts:
        text_parts.append(MSG_GROUP_CONFLICT.format(conflicts="\n".join(f"⚠️ {c}" for c in conflicts)))
    await query.edit_message_text("\n\n".join(text_parts) or MSG_ERROR)
    context.user_data.pop("group_selected", None)
    context.user_data.pop("group_mode", None)

async def toggle_finish_worker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    worker_id = int(query.data.replace(CB_FINISH_WORKER, ""))
    selected: set = context.user_data.setdefault("group_selected_finish", set())
    if worker_id in selected:
        selected.discard(worker_id)
    else:
        selected.add(worker_id)
    await query.edit_message_reply_markup(reply_markup=get_worker_select_keyboard(selected_ids=selected, finish_mode=True))

async def done_finish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    selected: set = context.user_data.get("group_selected_finish", set())
    if not selected:
        await query.edit_message_text(MSG_GROUP_NOBODY_SELECTED)
        return
    supervisor = update.effective_user
    logger.info("Групповое завершение: supervisor=%s workers=%s", supervisor.full_name, selected)
    results, no_active = [], []
    for worker_id in selected:
        worker = get_worker_by_id(worker_id)
        if worker is None:
            continue
        try:
            result = _sheets_service.finish_time_log(telegram_id=worker["id"], finished_by=f"supervisor: {supervisor.full_name}")
            if result is None:
                no_active.append(worker["name"])
            else:
                results.append(f"✅ {worker['name']} — {result['process']} ({result['duration_minutes']} мин)")
        except Exception as e:
            logger.exception("Ошибка группового завершения для %s: %s", worker["name"], e)
            results.append(f"❌ {worker['name']} — ошибка")
    text_parts = []
    if results:
        text_parts.append(MSG_GROUP_FINISHED.format(results="\n".join(results)))
    if no_active:
        text_parts.append(MSG_GROUP_NO_ACTIVE_TO_FINISH + "\n" + "\n".join(f"ℹ️ {n}" for n in no_active))
    await query.edit_message_text("\n\n".join(text_parts) or MSG_ERROR)
    context.user_data.pop("group_selected_finish", None)
    context.user_data.pop("group_mode", None)

async def confirm_no_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Действие отменено.")
    context.user_data.pop("group_selected", None)
    context.user_data.pop("group_selected_finish", None)
    context.user_data.pop("group_mode", None)

def get_handlers() -> list:
    return [
        CommandHandler("group_start", group_start_command),
        CommandHandler("group_finish", group_finish_command),
        CallbackQueryHandler(toggle_worker_callback, pattern=f"^{CB_SELECT_WORKER}\\d+$"),
        CallbackQueryHandler(done_select_callback, pattern=f"^{CB_DONE_SELECT}$"),
        CallbackQueryHandler(select_process_callback, pattern=f"^{CB_SELECT_PROCESS}"),
        CallbackQueryHandler(toggle_finish_worker_callback, pattern=f"^{CB_FINISH_WORKER}\\d+$"),
        CallbackQueryHandler(done_finish_callback, pattern=f"^{CB_FINISH_DONE}$"),
        CallbackQueryHandler(confirm_no_callback, pattern=f"^{CB_CONFIRM_NO}$"),
    ]
