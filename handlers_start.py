from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from states import Registration
from keyboards import (
    cadet_groups_kb,
    officer_only_kb,
    registered_kb_inline,
    role_menu_kb,
    OFFICERS_GROUP_CODE,
    OFFICERS_GROUP_LABEL,
)
from time_utils import current_slot, now_msk

router = Router()


def normalize_full_name(s: str) -> str:
    return " ".join(s.strip().split())


def looks_like_full_name(s: str) -> bool:
    parts = s.split()
    if not (2 <= len(parts) <= 4):
        return False
    for p in parts:
        if len(p) < 2:
            return False
    return True


def group_label_from_code(code: str) -> str:
    return OFFICERS_GROUP_LABEL if code == OFFICERS_GROUP_CODE else code


def is_officer(user_id: int, officer_ids: set[int]) -> bool:
    return user_id in officer_ids


def is_admin_cadet(user_id: int, admin_ids: set[int], officer_ids: set[int]) -> bool:
    # Админ-курсант: админ, но не офицер (офицер имеет приоритет)
    return (user_id in admin_ids) and (user_id not in officer_ids)


def build_menu(*, user_id: int, config) -> tuple[bool, bool, bool]:
    """
    Возвращает (officer, admin_cadet, show_not_reported).
    show_not_reported True только для админа-курсанта и только в активное окно доклада.
    """
    officer = is_officer(user_id, config.officer_ids)
    admin_cadet = is_admin_cadet(user_id, config.admin_ids, config.officer_ids)

    slot = current_slot(now_msk())
    show_not_reported = (slot is not None) and admin_cadet
    return officer, admin_cadet, show_not_reported


async def send_role_menu(message: Message, *, officer: bool, admin_cadet: bool, show_not_reported: bool) -> None:
    menu = role_menu_kb(is_admin_cadet=admin_cadet, is_officer=officer, show_not_reported=show_not_reported)
    if menu:
        await message.answer("Меню доступно.", reply_markup=menu)


async def send_role_menu_cb(cb: CallbackQuery, *, officer: bool, admin_cadet: bool, show_not_reported: bool) -> None:
    menu = role_menu_kb(is_admin_cadet=admin_cadet, is_officer=officer, show_not_reported=show_not_reported)
    if menu:
        await cb.message.answer("Меню доступно.", reply_markup=menu)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db, config):
    user_id = message.from_user.id
    officer, admin_cadet, show_not_reported = build_menu(user_id=user_id, config=config)

    # Меню показываем всегда (для офицеров/админов/курсантов)
    await send_role_menu(message, officer=officer, admin_cadet=admin_cadet, show_not_reported=show_not_reported)

    cadet = await db.get_cadet(user_id)
    if cadet:
        grp_label = group_label_from_code(cadet["group_code"])
        text = (
            "Вы уже зарегистрированы.\n\n"
            f"Группа: {grp_label}\n"
            f"ФИО: {cadet['full_name']}\n"
        )
        await message.answer(text, reply_markup=registered_kb_inline())
        return

    await state.set_state(Registration.choose_group)

    if officer:
        await message.answer(
            "Подтвердите регистрацию как офицер:",
            reply_markup=officer_only_kb(),
        )
    else:
        await message.answer(
            "Выберите учебную группу:",
            reply_markup=cadet_groups_kb(),
        )


@router.callback_query(F.data == "reg:restart")
async def reg_restart(cb: CallbackQuery, state: FSMContext, config):
    user_id = cb.from_user.id
    officer, admin_cadet, show_not_reported = build_menu(user_id=user_id, config=config)

    await cb.answer()
    await state.set_state(Registration.choose_group)

    # Меню показываем всегда
    await send_role_menu_cb(cb, officer=officer, admin_cadet=admin_cadet, show_not_reported=show_not_reported)

    if officer:
        await cb.message.edit_text(
            "Подтвердите регистрацию как офицер:",
            reply_markup=officer_only_kb(),
        )
    else:
        await cb.message.edit_text(
            "Выберите учебную группу:",
            reply_markup=cadet_groups_kb(),
        )


@router.callback_query(Registration.choose_group, F.data.startswith("group:"))
async def choose_group(cb: CallbackQuery, state: FSMContext, config):
    group_code = cb.data.split(":", 1)[1]
    user_id = cb.from_user.id
    officer = is_officer(user_id, config.officer_ids)

    # Серверная защита от подмены callback:
    # 1) не офицер -> запрет OFFICERS
    if not officer and group_code == OFFICERS_GROUP_CODE:
        await cb.answer("Регистрация как офицер запрещена для вашего аккаунта.", show_alert=True)
        await cb.message.edit_text("Выберите учебную группу:", reply_markup=cadet_groups_kb())
        return

    # 2) офицер -> разрешаем только OFFICERS
    if officer and group_code != OFFICERS_GROUP_CODE:
        await cb.answer("Офицер может зарегистрироваться только как офицер.", show_alert=True)
        await cb.message.edit_text("Подтвердите регистрацию как офицер:", reply_markup=officer_only_kb())
        return

    await cb.answer()
    await state.update_data(group_code=group_code)
    await state.set_state(Registration.enter_name)

    grp_label = group_label_from_code(group_code)
    await cb.message.edit_text(
        f"Группа выбрана: {grp_label}\n\nВведите Фамилия И. О. (например: Иванов И. И.)"
    )


@router.message(Registration.enter_name)
async def enter_name(message: Message, state: FSMContext, db, config):
    full_name = normalize_full_name(message.text or "")
    if not looks_like_full_name(full_name):
        await message.answer("Некорректный формат. Введите Фамилия И. О. (например: Иванов И. И.)")
        return

    data = await state.get_data()
    group_code = data.get("group_code")
    user_id = message.from_user.id
    officer = is_officer(user_id, config.officer_ids)
    admin_cadet = is_admin_cadet(user_id, config.admin_ids, config.officer_ids)

    if not group_code:
        await state.set_state(Registration.choose_group)
        if officer:
            await message.answer("Подтвердите регистрацию как офицер:", reply_markup=officer_only_kb())
        else:
            await message.answer("Выберите учебную группу:", reply_markup=cadet_groups_kb())
        return

    # Дублирующая серверная защита:
    if not officer and group_code == OFFICERS_GROUP_CODE:
        await state.set_state(Registration.choose_group)
        await message.answer(
            "Регистрация как офицер запрещена. Выберите учебную группу:",
            reply_markup=cadet_groups_kb(),
        )
        return

    if officer and group_code != OFFICERS_GROUP_CODE:
        await state.set_state(Registration.choose_group)
        await message.answer(
            "Офицер может зарегистрироваться только как офицер.",
            reply_markup=officer_only_kb(),
        )
        return

    await db.upsert_cadet(tg_user_id=user_id, group_code=group_code, full_name=full_name)
    await state.clear()

    # После регистрации обновляем меню (и кнопку "Не доложили", если окно активно)
    slot = current_slot(now_msk())
    show_not_reported = (slot is not None) and admin_cadet
    await send_role_menu(message, officer=officer, admin_cadet=admin_cadet, show_not_reported=show_not_reported)

    grp_label = group_label_from_code(group_code)
    await message.answer(
        "Регистрация завершена.\n\n"
        f"Группа: {grp_label}\n"
        f"ФИО: {full_name}\n"
    )
