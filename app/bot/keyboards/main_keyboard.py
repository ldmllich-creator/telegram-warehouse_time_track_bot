"""
Reply-клавиатура главного меню.
"""

from telegram import ReplyKeyboardMarkup, KeyboardButton

# ---------------------------------------------------------------------------
# Текст кнопок (используется в handlers для сравнения)
# ---------------------------------------------------------------------------
BTN_UNLOADING = "▶️ Разгрузка"
BTN_RECEIVING = "▶️ Приемка"
BTN_SORTING = "▶️ Сортировка"
BTN_PUTAWAY = "▶️ Размещение"
BTN_FINISH = "⏹ Завершить процесс"
BTN_STATUS = "📊 Мой статус"
BTN_MYDAY = "📋 Мой день"

# Маппинг кнопка → ключ процесса
BUTTON_TO_PROCESS: dict[str, str] = {
    BTN_UNLOADING: "unloading",
    BTN_RECEIVING: "receiving",
    BTN_SORTING: "sorting",
    BTN_PUTAWAY: "putaway",
}


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает главную reply-клавиатуру."""
    keyboard = [
        [KeyboardButton(BTN_UNLOADING), KeyboardButton(BTN_RECEIVING)],
        [KeyboardButton(BTN_SORTING), KeyboardButton(BTN_PUTAWAY)],
        [KeyboardButton(BTN_FINISH)],
        [KeyboardButton(BTN_STATUS), KeyboardButton(BTN_MYDAY)],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )
