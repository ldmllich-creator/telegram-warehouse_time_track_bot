"""
Управление ролями и списком сотрудников.

Список сотрудников хранится в коде — можно расширить.
"""

# ---------------------------------------------------------------------------
# Список сотрудников
# ---------------------------------------------------------------------------
# Добавляйте сотрудников в этот список!
# name — отображаемое имя
EMPLOYEES: list[dict] = [
    {"id": i, "name": f"Сотрудник #{i:03d}"}
    for i in range(1, 11)
]


def get_employees_list() -> list[dict]:
    """Возвращает список всех сотрудников."""
    return EMPLOYEES


def get_employee_by_id(employee_id: int) -> dict | None:
    """Возвращает сотрудника по ID."""
    for emp in EMPLOYEES:
        if emp["id"] == employee_id:
            return emp
    return None


def get_worker_by_id(worker_id: int) -> dict | None:
    """Возвращает сотрудника по ID (алиас для get_employee_by_id)."""
    for emp in EMPLOYEES:
        if emp["id"] == worker_id:
            return emp
    return None


def is_supervisor_or_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь супервайзером или админом.

    TODO: реализовать проверку ролей.
    Пока возвращает True для всех.
    """
    return True
