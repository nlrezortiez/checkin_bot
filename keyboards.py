from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

OFFICERS_GROUP_CODE = "OFFICERS"
OFFICERS_GROUP_LABEL = "Офицер"

CADET_GROUPS: list[str] = ["841/11", "841/12", "841/13", "842/11", "842/12", "843/11", "843/12"]

BTN_MY_GROUP = "Статистика: моя группа"
BTN_PICK_GROUP = "Зарегистрировано: выбрать группу"
BTN_COURSE = "Зарегистрировано: весь курс"
BTN_NOT_REPORTED = "Не доложили"
BTN_CHECKIN = "✅ Отметиться"
BTN_LAST_REPORT = "Статистика последнего доклада"


def cadet_groups_kb() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for i, g in enumerate(CADET_GROUPS, start=1):
        row.append(InlineKeyboardButton(text=g, callback_data=f"group:{g}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def officer_only_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=OFFICERS_GROUP_LABEL, callback_data=f"group:{OFFICERS_GROUP_CODE}")]
        ]
    )


def registered_kb_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перерегистрироваться", callback_data="reg:restart")]
        ]
    )


def role_menu_kb(*, is_officer: bool, is_admin_cadet: bool, show_not_reported: bool) -> ReplyKeyboardMarkup | None:
    if is_officer:
        rows = [
            [KeyboardButton(text=BTN_LAST_REPORT)],
            [KeyboardButton(text=BTN_PICK_GROUP)],
            [KeyboardButton(text=BTN_COURSE)],
        ]
    elif is_admin_cadet:
        rows = [
            [KeyboardButton(text=BTN_CHECKIN)],
            [KeyboardButton(text=BTN_LAST_REPORT)],
            [KeyboardButton(text=BTN_MY_GROUP)],
        ]
        if show_not_reported:
            rows.append([KeyboardButton(text=BTN_NOT_REPORTED)])
    else:
        rows = [
            [KeyboardButton(text=BTN_CHECKIN)],
        ]

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        selective=True,
    )


def officer_groups_kb() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for i, g in enumerate(CADET_GROUPS, start=1):
        row.append(InlineKeyboardButton(text=g, callback_data=f"officer:group:{g}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="Назад", callback_data="nav:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
