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

BTN_CHECKIN = "✅ Отметиться"


def cadet_groups_kb() -> InlineKeyboardMarkup:
    """
    Inline-клавиатура выбора учебной группы (только для курсантов).
    """
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
    """
    Inline-клавиатура для регистрации офицера: единственная опция «Офицер».
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=OFFICERS_GROUP_LABEL, callback_data=f"group:{OFFICERS_GROUP_CODE}")]
        ]
    )


def registered_kb_inline() -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для зарегистрированного пользователя.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перерегистрироваться", callback_data="reg:restart")]
        ]
    )


from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def role_menu_kb(*, is_officer: bool, is_admin_cadet: bool) -> ReplyKeyboardMarkup | None:
    if is_officer:
        rows = [
            [KeyboardButton(text=BTN_PICK_GROUP)],
            [KeyboardButton(text=BTN_COURSE)],
        ]
    elif is_admin_cadet:
        rows = [
            [KeyboardButton(text=BTN_CHECKIN)],
            [KeyboardButton(text=BTN_MY_GROUP)],
        ]
    elif not is_officer and not is_admin_cadet:
        rows = [
            [KeyboardButton(text=BTN_CHECKIN)],
        ]
    else:
        return None

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        selective=True,
    )



def officer_groups_kb() -> InlineKeyboardMarkup:
    """
    Inline-клавиатура выбора учебной группы для офицеров (погруппно).
    Офицерскую группу не показываем.
    """
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
