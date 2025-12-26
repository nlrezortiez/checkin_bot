from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards import (
    BTN_MY_GROUP,
    BTN_PICK_GROUP,
    BTN_COURSE,
    officer_groups_kb,
    OFFICERS_GROUP_CODE,
)

router = Router()


def is_officer(user_id: int, officer_ids: set[int]) -> bool:
    return user_id in officer_ids


def is_admin_cadet(user_id: int, admin_ids: set[int], officer_ids: set[int]) -> bool:
    return (user_id in admin_ids) and (user_id not in officer_ids)


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
    n = await db.count_registered_in_group(group_code)
    await message.answer(
        "Статистика: моя группа\n\n"
        f"{group_code}: {n}"
    )


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
