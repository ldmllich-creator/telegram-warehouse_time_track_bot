"""
Inline-клавиатуры: выбор сотрудника из списка.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.config.settings import PROCESSES
from app.utils.roles import get_employees_list


# ---------------------------------------------------------------------------
# Callback data prefixes
# ---------------------------------------------------------------------------
CB_EMPLOYEE = "emp_"
CB_FINISH_EMPLOYEE = "femp_"

# Group mode callback prefixes
CB_SELECT_WORKER = "gw_"
CB_DONE_SELECT = "gw_done"
CB_SELECT_PROCESS = "gp_"
CB_CONFIRM_YES = "gc_yes"
CB_CONFIRM_NO = "gc_no"
CB_FINISH_WORKER = "gfw_"
CB_FINISH_DONE = "gfw_done"


def get_employee_keyboard(process_key: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора сотрудника для запуска процесса."""
    employees = get_employees_list()
    buttons = []
    for emp in employees:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {emp['name']}",
                callback_data=f"{CB_EMPLOYEE}{process_key}_{emp['id']}",
            )
        ])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def get_active_employees_keyboard(active_list: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора сотрудника для завершения процесса."""
    buttons = []
    for item in active_list:
        process_name = PROCESSES.get(item["process"], item["process"])
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {item['user_name']} — {process_name}",
                callback_data=f"{CB_FINISH_EMPLOYEE}{item['telegram_id']}",
            )
        ])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def get_worker_select_keyboard(
    selected_ids: set | None = None,
    finish_mode: bool = False,
) -> InlineKeyboardMarkup:
    """Клавиатура multi-select сотрудников (групповой режим)."""
    if selected_ids is None:
        selected_ids = set()
    employees = get_employees_list()
    buttons = []
    prefix = CB_FINISH_WORKER if finish_mode else CB_SELECT_WORKER
    for emp in employees:
        check = "✅" if emp["id"] in selected_ids else "⬜"
        buttons.append([
            InlineKeyboardButton(
                text=f"{check} {emp['name']}",
                callback_data=f"{prefix}{emp['id']}",
            )
        ])
    done_cb = CB_FINISH_DONE if finish_mode else CB_DONE_SELECT
    done_text = "✅ Готово — завершить" if finish_mode else "✅ Готово — запустить"
    buttons.append([
        InlineKeyboardButton(done_text, callback_data=done_cb),
        InlineKeyboardButton("❌ Отмена", callback_data=CB_CONFIRM_NO),
    ])
    return InlineKeyboardMarkup(buttons)


def get_process_select_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора процесса (групповой режим)."""
    buttons = []
    for key, name in PROCESSES.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"📦 {name}",
                callback_data=f"{CB_SELECT_PROCESS}{key}",
            )
        ])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data=CB_CONFIRM_NO)])
    return InlineKeyboardMarkup(buttons)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=CB_CONFIRM_YES),
            InlineKeyboardButton("❌ Отмена", callback_data=CB_CONFIRM_NO),
        ]
    ])
