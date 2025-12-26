from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType

import re

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

BTN_SHARE_PHONE = "Поделиться номером"
BTN_ENTER_PHONE = "Ввести номер вручную"


def phone_choice_kb() -> ReplyKeyboardMarkup:
    """
    Для курсантов телефон обязателен: либо контакт, либо ввод вручную.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SHARE_PHONE, request_contact=True)],
            [KeyboardButton(text=BTN_ENTER_PHONE)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        selective=True,
    )


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
    return (user_id in admin_ids) and (user_id not in officer_ids)


def compute_menu_flags(*, user_id: int, config) -> tuple[bool, bool, bool]:
    officer = is_officer(user_id, config.officer_ids)
    admin_cadet = is_admin_cadet(user_id, config.admin_ids, config.officer_ids)
    show_not_reported = admin_cadet and (current_slot(now_msk()) is not None)
    return officer, admin_cadet, show_not_reported


def build_role_menu(*, officer: bool, admin_cadet: bool, show_not_reported: bool):
    return role_menu_kb(
        is_officer=officer,
        is_admin_cadet=admin_cadet,
        show_not_reported=show_not_reported,
    )


def normalize_ru_phone(raw: str) -> str | None:
    """
    Нормализация номера РФ к виду +7XXXXXXXXXX.
    Допускаем ввод:
      +7XXXXXXXXXX
      7XXXXXXXXXX
      8XXXXXXXXXX
    а также любые разделители (пробелы, скобки, дефисы).
    Возвращает нормализованный номер или None.
    """
    s = (raw or "").strip()
    if not s:
        return None

    # оставляем только цифры и ведущий '+'
    # проще: вытащим все цифры
    digits = "".join(ch for ch in s if ch.isdigit())

    # РФ номер должен быть 11 цифр и начинаться с 7 или 8
    if len(digits) != 11:
        return None
    if digits[0] not in ("7", "8"):
        return None

    # нормализуем к +7
    return "+7" + digits[1:]


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db, config):
    user_id = message.from_user.id
    officer, admin_cadet, show_not_reported = compute_menu_flags(user_id=user_id, config=config)
    menu = build_role_menu(officer=officer, admin_cadet=admin_cadet, show_not_reported=show_not_reported)

    cadet = await db.get_cadet(user_id)

    # Уже зарегистрирован
    if cadet:
        await db.update_username(user_id, message.from_user.username)

        grp_label = group_label_from_code(cadet["group_code"])
        text = (
            "Вы уже зарегистрированы.\n\n"
            f"Группа: {grp_label}\n"
            f"ФИО: {cadet['full_name']}\n"
        )
        await message.answer(text, reply_markup=menu)
        await message.answer("Действия:", reply_markup=registered_kb_inline())
        return

    # Не зарегистрирован: запускаем регистрацию (без показа меню)
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
    officer = is_officer(user_id, config.officer_ids)

    await cb.answer()
    await state.set_state(Registration.choose_group)

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

    # Серверная защита от подмены callback
    if not officer and group_code == OFFICERS_GROUP_CODE:
        await cb.answer("Регистрация как офицер запрещена для вашего аккаунта.", show_alert=True)
        await cb.message.edit_text("Выберите учебную группу:", reply_markup=cadet_groups_kb())
        return

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

    if not group_code:
        await state.set_state(Registration.choose_group)
        if officer:
            await message.answer("Подтвердите регистрацию как офицер:", reply_markup=officer_only_kb())
        else:
            await message.answer("Выберите учебную группу:", reply_markup=cadet_groups_kb())
        return

    # Дублирующая серверная защита
    if not officer and group_code == OFFICERS_GROUP_CODE:
        await state.set_state(Registration.choose_group)
        await message.answer("Регистрация как офицер запрещена. Выберите учебную группу:", reply_markup=cadet_groups_kb())
        return

    if officer and group_code != OFFICERS_GROUP_CODE:
        await state.set_state(Registration.choose_group)
        await message.answer("Офицер может зарегистрироваться только как офицер.", reply_markup=officer_only_kb())
        return

    username = message.from_user.username
    await db.upsert_cadet(tg_user_id=user_id, group_code=group_code, full_name=full_name, username=username)

    if officer:
        # Офицеру телефон не нужен: завершаем регистрацию и показываем меню
        await state.clear()

        officer_f, admin_cadet, show_not_reported = compute_menu_flags(user_id=user_id, config=config)
        menu = build_role_menu(officer=officer_f, admin_cadet=admin_cadet, show_not_reported=show_not_reported)

        await message.answer("Регистрация завершена.", reply_markup=menu)
        return

    # Курсант: телефон обязателен (2 опции)
    await state.set_state(Registration.enter_contact)
    await message.answer(
        "Номер телефона для связи (обязательно):\n"
        "— нажмите «Поделиться номером», или\n"
        "— выберите «Ввести номер вручную», если аккаунт тг зарегистирован на другой номер.",
        reply_markup=phone_choice_kb(),
    )


@router.message(Registration.enter_contact, F.content_type == ContentType.CONTACT)
async def reg_contact_share(message: Message, state: FSMContext, db, config):
    user_id = message.from_user.id

    if not message.contact or message.contact.user_id != user_id:
        await message.answer("Нужно отправить контакт своего аккаунта или выбрать «Ввести номер вручную».")
        return

    phone_raw = (message.contact.phone_number or "").strip()
    phone = normalize_ru_phone(phone_raw)
    if not phone:
        await message.answer(
            "Номер из контакта не распознан как корректный.\n"
            "Попробуйте «Ввести номер вручную» в формате +79991234567."
        )
        return

    await db.update_phone(user_id, phone)
    await state.clear()

    officer, admin_cadet, show_not_reported = compute_menu_flags(user_id=user_id, config=config)
    menu = build_role_menu(officer=officer, admin_cadet=admin_cadet, show_not_reported=show_not_reported)

    await message.answer("Регистрация завершена.", reply_markup=menu)


@router.message(Registration.enter_contact, F.text == BTN_ENTER_PHONE)
async def reg_contact_enter_manual_prompt(message: Message):
    await message.answer(
        "Введите номер телефона.\n"
        "Допустимые форматы: +79991234567, 89991234567, 79991234567.\n"
    )


@router.message(Registration.enter_contact)
async def reg_contact_manual(message: Message, state: FSMContext, db, config):
    """
    Любой текст (кроме кнопки BTN_ENTER_PHONE) трактуем как попытку ввода телефона вручную.
    """
    user_id = message.from_user.id
    phone = normalize_ru_phone(message.text or "")
    if not phone:
        await message.answer(
            "Номер некорректен.\n"
            "Введите в формате +79991234567 (или 89991234567 / 79991234567)."
        )
        return

    await db.update_phone(user_id, phone)
    await state.clear()

    officer, admin_cadet, show_not_reported = compute_menu_flags(user_id=user_id, config=config)
    menu = build_role_menu(officer=officer, admin_cadet=admin_cadet, show_not_reported=show_not_reported)

    await message.answer("Регистрация завершена.", reply_markup=menu)
