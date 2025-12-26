from datetime import timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards import (
    BTN_MY_GROUP,
    BTN_PICK_GROUP,
    BTN_COURSE,
    BTN_NOT_REPORTED,
    BTN_LAST_REPORT,
    officer_groups_kb,
    OFFICERS_GROUP_CODE,
)
from time_utils import now_msk, date_str_msk, current_slot, MORNING, EVENING, SLOT_MORNING, SLOT_EVENING
from reporting import build_missing_report_all, build_missing_report_one_group

router = Router()


def is_officer(user_id: int, officer_ids: set[int]) -> bool:
    return user_id in officer_ids


def is_admin_cadet(user_id: int, admin_ids: set[int], officer_ids: set[int]) -> bool:
    return (user_id in admin_ids) and (user_id not in officer_ids)


def format_contact(username: str | None, phone: str | None) -> str:
    if phone:
        return phone
    if username:
        return f"@{username}"
    return ""


def _split_long_text(text: str, max_len: int = 3500) -> list[str]:
    lines = text.splitlines()
    parts: list[str] = []
    buf: list[str] = []
    cur = 0
    for line in lines:
        add = len(line) + 1
        if buf and cur + add > max_len:
            parts.append("\n".join(buf))
            buf = []
            cur = 0
        buf.append(line)
        cur += add
    if buf:
        parts.append("\n".join(buf))
    return parts


def last_closed_slot_and_date(dt) -> tuple[str, str]:
    """
    Возвращает (date_str, slot) для последнего ЗАКРЫТОГО окна доклада.
    При окнах:
      утро: 07:00–07:30
      вечер: 21:30–22:00
    Логика:
      - до закрытия утреннего окна -> последний закрытый = вчерашний вечер
      - после закрытия утреннего и до закрытия вечернего -> последний закрытый = утро сегодня
      - после закрытия вечернего -> последний закрытый = вечер сегодня
    """
    t = dt.timetz().replace(tzinfo=None)

    if t <= MORNING.close:
        prev = dt - timedelta(days=1)
        return date_str_msk(prev), SLOT_EVENING

    if t <= EVENING.close:
        return date_str_msk(dt), SLOT_MORNING

    return date_str_msk(dt), SLOT_EVENING


def slot_label(slot: str) -> str:
    return "Утренний" if slot == SLOT_MORNING else "Вечерний"


@router.message(F.text == BTN_LAST_REPORT)
async def last_report_stats(message: Message, db, config):
    user_id = message.from_user.id

    officer = is_officer(user_id, config.officer_ids)
    admin_cadet = is_admin_cadet(user_id, config.admin_ids, config.officer_ids)

    if not (officer or admin_cadet):
        return

    dt = now_msk()
    rep_date, rep_slot = last_closed_slot_and_date(dt)
    rep_title = f"{slot_label(rep_slot)} отчёт ({rep_date})"

    if officer:
        total = await db.count_course_total(exclude_group_code=OFFICERS_GROUP_CODE)
        checked = await db.count_course_checked(exclude_group_code=OFFICERS_GROUP_CODE, date_str=rep_date, slot=rep_slot)

        rows = await db.missing_all_groups(rep_date, rep_slot, OFFICERS_GROUP_CODE)
        report = build_missing_report_all(rows)

        text = (
            f"{rep_title}\n"
            f"Отметились {checked}/{total} курсантов\n\n"
            f"{report}"
        )
        for part in _split_long_text(text):
            await message.answer(part)
        return

    # admin-cadet
    cadet = await db.get_cadet(user_id)
    if not cadet or cadet["group_code"] == OFFICERS_GROUP_CODE:
        await message.answer("Команда недоступна: вы не зарегистрированы как курсант.")
        return

    group_code = cadet["group_code"]
    total = await db.count_group_total(group_code)
    checked = await db.count_group_checked(group_code, rep_date, rep_slot)

    missing = await db.missing_by_group(group_code, rep_date, rep_slot)
    report = build_missing_report_one_group(group_code, missing)

    text = (
        f"{rep_title}\n"
        f"Отметились {checked}/{total} курсантов\n\n"
        f"{report}"
    )
    for part in _split_long_text(text):
        await message.answer(part)


@router.message(F.text == BTN_NOT_REPORTED)
async def not_reported(message: Message, db, config):
    user_id = message.from_user.id
    if not is_admin_cadet(user_id, config.admin_ids, config.officer_ids):
        return

    cadet = await db.get_cadet(user_id)
    if not cadet or cadet["group_code"] == OFFICERS_GROUP_CODE:
        await message.answer("Команда недоступна: вы не зарегистрированы как курсант.")
        return

    dt = now_msk()
    slot = current_slot(dt)
    if slot is None:
        await message.answer("Не время доклада")
        return

    date_str = date_str_msk(dt)
    group_code = cadet["group_code"]

    missing = await db.missing_by_group(group_code, date_str, slot)
    if not missing:
        await message.answer("Все доложили.")
        return

    lines = ["Не доложили", "", f"{group_code} учебная группа:"]
    for i, (name, username, phone) in enumerate(missing, start=1):
        c = format_contact(username, phone)
        lines.append(f"{i}. {name}" + (f" ({c})" if c else ""))
    await message.answer("\n".join(lines))


@router.message(F.text == BTN_MY_GROUP)
async def admin_my_group_stats(message: Message, db, config):
    user_id = message.from_user.id
    if not is_admin_cadet(user_id, config.admin_ids, config.officer_ids):
        return

    cadet = await db.get_cadet(user_id)
    if not cadet:
        await message.answer(
            "Статистика: моя группа\n\n"
            "Вы не зарегистрированы. Выполните /start и зарегистрируйтесь в своей учебной группе."
        )
        return

    if cadet["group_code"] == OFFICERS_GROUP_CODE:
        await message.answer(
            "Статистика: моя группа\n\n"
            "Недоступно: ваш аккаунт зарегистрирован как «Офицеры»."
        )
        return

    group_code = cadet["group_code"]
    members = await db.list_registered_in_group(group_code)

    lines = [
        "Статистика: моя группа",
        "",
        f"{group_code}: {len(members)}",
        "",
        "Список зарегистрированных:",
    ]
    for i, (name, username, phone) in enumerate(members, start=1):
        c = format_contact(username, phone)
        lines.append(f"{i}. {name}" + (f" ({c})" if c else ""))

    for part in _split_long_text("\n".join(lines)):
        await message.answer(part)


@router.message(F.text == BTN_PICK_GROUP)
async def officer_pick_group(message: Message, config):
    user_id = message.from_user.id
    if not is_officer(user_id, config.officer_ids):
        return

    await message.answer(
        "Выберите учебную группу:",
        reply_markup=officer_groups_kb(),
    )


@router.callback_query(F.data.startswith("officer:group:"))
async def officer_group_stats(cb: CallbackQuery, db, config):
    user_id = cb.from_user.id
    if not is_officer(user_id, config.officer_ids):
        await cb.answer("Недостаточно прав", show_alert=True)
        return

    await cb.answer()
    group_code = cb.data.split(":", 2)[2]
    n = await db.count_registered_in_group(group_code)

    await cb.message.edit_text(
        "Статистика: выбранная группа\n\n"
        f"{group_code}: {n}",
        reply_markup=officer_groups_kb(),
    )


@router.message(F.text == BTN_COURSE)
async def officer_course_stats(message: Message, db, config):
    user_id = message.from_user.id
    if not is_officer(user_id, config.officer_ids):
        return

    total = await db.count_registered_course(exclude_group_code=OFFICERS_GROUP_CODE)
    by_group = await db.count_registered_by_group_course(exclude_group_code=OFFICERS_GROUP_CODE)

    lines = [
        "Статистика: весь курс",
        "",
        f"Зарегистрировано всего (без офицеров): {total}",
        "",
    ]
    for g, n in by_group:
        lines.append(f"{g}: {n}")

    await message.answer("\n".join(lines))


@router.callback_query(F.data == "nav:back")
async def nav_back(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("Выберите действие в меню ниже.")
