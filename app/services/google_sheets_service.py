"""
Сервис для работы с Google Sheets.

Предоставляет полный CRUD для таблицы time_logs:
- add_time_log      — создать запись (status=active)
- finish_time_log   — завершить активный процесс
- get_active_process — получить текущий активный процесс пользователя
- get_today_logs    — все записи пользователя за сегодня
- get_all_active_processes — все активные процессы
"""

import uuid
import threading
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from app.config.settings import (
    GOOGLE_SHEETS_ID,
    GOOGLE_CREDENTIALS_JSON_PATH,
    SHEET_NAME,
    COLUMNS,
    STATUS_ACTIVE,
    STATUS_FINISHED,
    DATETIME_FORMAT,
    DATE_FORMAT,
    logger,
)


class GoogleSheetsService:
    """Сервис подключения и работы с Google Sheets."""

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._connect()

    def _connect(self) -> None:
        """Создаёт авторизованное подключение к Google Sheets."""
        logger.info("Подключение к Google Sheets...")
        credentials = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_JSON_PATH,
            scopes=self.SCOPES,
        )
        self._client = gspread.authorize(credentials)
        self._spreadsheet = self._client.open_by_key(GOOGLE_SHEETS_ID)
        self._sheet = self._get_or_create_sheet()
        self._migrate_english_statuses()
        logger.info("Подключение к Google Sheets установлено ✅")

    def _migrate_english_statuses(self) -> None:
        """Миграция: заменяет английские статусы на русские."""
        try:
            all_rows = self._sheet.get_all_values()
            status_col = COLUMNS.index("Статус") + 1
            migrated = 0
            for i, row in enumerate(all_rows[1:], start=2):
                if len(row) < len(COLUMNS):
                    continue
                status = row[COLUMNS.index("Статус")]
                if status == "Active":
                    self._sheet.update_cell(i, status_col, STATUS_ACTIVE)
                    migrated += 1
                elif status == "Finished":
                    self._sheet.update_cell(i, status_col, STATUS_FINISHED)
                    migrated += 1
            if migrated:
                logger.info("Мигрировано статусов: %d ✅", migrated)
        except Exception as e:
            logger.warning("Ошибка миграции статусов: %s", e)

    def _get_or_create_sheet(self) -> gspread.Worksheet:
        """Возвращает лист time_logs, создаёт при первом запуске."""
        try:
            sheet = self._spreadsheet.worksheet(SHEET_NAME)
            logger.info("Лист '%s' найден.", SHEET_NAME)
            try:
                existing_headers = sheet.row_values(1)
                if existing_headers != COLUMNS:
                    logger.info("Обновляю заголовки...")
                    for idx, col_name in enumerate(COLUMNS, start=1):
                        sheet.update_cell(1, idx, col_name)
                    logger.info("Заголовки обновлены ✅")
            except Exception as e:
                logger.warning("Не удалось проверить заголовки: %s", e)
        except gspread.exceptions.WorksheetNotFound:
            logger.info("Лист '%s' не найден — создаю...", SHEET_NAME)
            sheet = self._spreadsheet.add_worksheet(
                title=SHEET_NAME, rows=1000, cols=len(COLUMNS)
            )
            sheet.append_row(COLUMNS)
            logger.info("Лист '%s' создан с заголовками.", SHEET_NAME)
        return sheet

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    @staticmethod
    def _generate_id() -> str:
        return uuid.uuid4().hex[:12]

    def _col_index(self, col_name: str) -> int:
        return COLUMNS.index(col_name) + 1

    def add_time_log(self, user_name: str, telegram_id: int, process: str, started_by: str) -> dict:
        """Создаёт новую запись о начале процесса."""
        with self._lock:
            active = self._find_active_row(telegram_id)
            if active is not None:
                raise ValueError("У пользователя уже есть активный процесс")
            now = self._now()
            row_id = self._generate_id()
            row = {
                "ID": row_id,
                "Сотрудник": user_name,
                "ID сотрудника": str(telegram_id),
                "Процесс": process,
                "Начало": now.strftime(DATETIME_FORMAT),
                "Конец": "",
                "Длительность (мин)": "",
                "Статус": STATUS_ACTIVE,
                "Запустил": started_by,
                "Завершил": "",
                "Дата": now.strftime(DATE_FORMAT),
            }
            values = [row[col] for col in COLUMNS]
            self._sheet.append_row(values, value_input_option="USER_ENTERED")
            logger.info("Запись создана: user=%s process=%s id=%s", user_name, process, row_id)
            return row

    def finish_time_log(self, telegram_id: int, finished_by: str) -> Optional[dict]:
        """Завершает активный процесс пользователя."""
        with self._lock:
            result = self._find_active_row(telegram_id)
            if result is None:
                return None
            row_number, row_data = result
            now = self._now()
            start_time = datetime.strptime(row_data[COLUMNS.index("Начало")], DATETIME_FORMAT)
            duration = now - start_time
            duration_minutes = round(duration.total_seconds() / 60, 1)
            updates = {
                "Конец": now.strftime(DATETIME_FORMAT),
                "Длительность (мин)": str(duration_minutes),
                "Статус": STATUS_FINISHED,
                "Завершил": finished_by,
            }
            for col_name, value in updates.items():
                col_idx = self._col_index(col_name)
                self._sheet.update_cell(row_number, col_idx, value)
            logger.info("Процесс завершён: user_id=%s duration=%s мин", telegram_id, duration_minutes)
            return {
                "process": row_data[COLUMNS.index("Процесс")],
                "start_time": row_data[COLUMNS.index("Начало")],
                "end_time": now.strftime(DATETIME_FORMAT),
                "duration_minutes": duration_minutes,
            }

    def get_active_process(self, telegram_id: int) -> Optional[dict]:
        """Возвращает данные об активном процессе пользователя."""
        result = self._find_active_row(telegram_id)
        if result is None:
            return None
        _, row_data = result
        start_time_str = row_data[COLUMNS.index("Начало")]
        start_time = datetime.strptime(start_time_str, DATETIME_FORMAT)
        elapsed = round((self._now() - start_time).total_seconds() / 60, 1)
        return {
            "process": row_data[COLUMNS.index("Процесс")],
            "start_time": start_time_str,
            "duration_minutes": elapsed,
        }

    def get_today_logs(self, telegram_id: int) -> list[dict]:
        """Возвращает все записи пользователя за сегодня."""
        today = self._now().strftime(DATE_FORMAT)
        all_rows = self._sheet.get_all_values()
        results: list[dict] = []
        for row in all_rows[1:]:
            if len(row) < len(COLUMNS):
                continue
            if row[COLUMNS.index("ID сотрудника")] == str(telegram_id) and row[COLUMNS.index("Дата")] == today:
                results.append({
                    "process": row[COLUMNS.index("Процесс")],
                    "start_time": row[COLUMNS.index("Начало")],
                    "end_time": row[COLUMNS.index("Конец")],
                    "duration_minutes": row[COLUMNS.index("Длительность (мин)")],
                    "status": row[COLUMNS.index("Статус")],
                })
        return results

    def get_all_active_processes(self) -> list[dict]:
        """Возвращает все активные процессы."""
        all_rows = self._sheet.get_all_values()
        results: list[dict] = []
        for row in all_rows[1:]:
            if len(row) < len(COLUMNS):
                continue
            if row[COLUMNS.index("Статус")] == STATUS_ACTIVE:
                results.append({
                    "telegram_id": row[COLUMNS.index("ID сотрудника")],
                    "user_name": row[COLUMNS.index("Сотрудник")],
                    "process": row[COLUMNS.index("Процесс")],
                    "start_time": row[COLUMNS.index("Начало")],
                })
        return results

    def get_today_all_logs(self) -> list[dict]:
        """Возвращает все записи за сегодня."""
        today = self._now().strftime(DATE_FORMAT)
        all_rows = self._sheet.get_all_values()
        results: list[dict] = []
        for row in all_rows[1:]:
            if len(row) < len(COLUMNS):
                continue
            if row[COLUMNS.index("Дата")] == today:
                results.append({
                    "user_name": row[COLUMNS.index("Сотрудник")],
                    "process": row[COLUMNS.index("Процесс")],
                    "start_time": row[COLUMNS.index("Начало")],
                    "end_time": row[COLUMNS.index("Конец")],
                    "duration_minutes": row[COLUMNS.index("Длительность (мин)")],
                    "status": row[COLUMNS.index("Статус")],
                })
        return results

    def _find_active_row(self, telegram_id: int) -> Optional[tuple[int, list[str]]]:
        """Ищет активную строку пользователя."""
        all_rows = self._sheet.get_all_values()
        for i in range(len(all_rows) - 1, 0, -1):
            row = all_rows[i]
            if len(row) < len(COLUMNS):
                continue
            if row[COLUMNS.index("ID сотрудника")] == str(telegram_id) and row[COLUMNS.index("Статус")] == STATUS_ACTIVE:
                return (i + 1, row)
        return None
