"""
Конфигурация приложения.

Загружает переменные окружения из .env файла и предоставляет
константы для всего приложения.
"""

import os
import sys
import logging

from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)

logger = logging.getLogger("time_bot")

# ---------------------------------------------------------------------------
# Обязательные переменные окружения
# ---------------------------------------------------------------------------
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_CREDENTIALS_JSON_PATH: str = os.getenv(
    "GOOGLE_CREDENTIALS_JSON_PATH", "credentials.json"
)

# Валидация при импорте
_REQUIRED = {
    "BOT_TOKEN": BOT_TOKEN,
    "GOOGLE_SHEETS_ID": GOOGLE_SHEETS_ID,
}

for _name, _value in _REQUIRED.items():
    if not _value:
        logger.critical("Переменная окружения %s не задана!", _name)
        sys.exit(1)

if not os.path.isfile(GOOGLE_CREDENTIALS_JSON_PATH):
    logger.critical(
        "Файл credentials не найден: %s", GOOGLE_CREDENTIALS_JSON_PATH
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Константы процессов
# ---------------------------------------------------------------------------
PROCESSES: dict[str, str] = {
    "unloading": "Разгрузка",
    "receiving": "Приемка",
    "sorting": "Сортировка",
    "putaway": "Размещение",
}

# ---------------------------------------------------------------------------
# Роли
# ---------------------------------------------------------------------------
ROLE_WORKER = "worker"
ROLE_SUPERVISOR = "supervisor"
ROLE_ADMIN = "admin"

# ---------------------------------------------------------------------------
# Колонки Google Sheets (порядок важен!)
# ---------------------------------------------------------------------------
SHEET_NAME = "time_logs"

COLUMNS: list[str] = [
    "ID",
    "Сотрудник",
    "ID сотрудника",
    "Процесс",
    "Начало",
    "Конец",
    "Длительность (мин)",
    "Статус",
    "Запустил",
    "Завершил",
    "Дата",
]

# Статусы
STATUS_ACTIVE = "В работе"
STATUS_FINISHED = "Завершён"

# Формат даты / времени
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
