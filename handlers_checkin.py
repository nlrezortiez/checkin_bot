from aiogram import Router, F
from aiogram.types import Message

from keyboards import BTN_CHECKIN, OFFICERS_GROUP_CODE
from time_utils import now_msk, date_str_msk, current_slot, slot_config

router = Router()

@router.message(F.text == BTN_CHECKIN)
async def do_checkin(message: Message, db):
    user_id = message.from_user.id

    cadet = await db.get_cadet(user_id)
    if not cadet:
        await message.answer("Вы не зарегистрированы. Используйте /start.")
        return

    if cadet["group_code"] == OFFICERS_GROUP_CODE:
        await message.answer("Для офицеров отметка не требуется.")
        return

    dt = now_msk()
    slot = current_slot(dt)
    if slot is None:
        await message.answer("Не время доклада")
        return

    date_str = date_str_msk(dt)
    inserted = await db.add_checkin(user_id, date_str, slot)

    cfg = slot_config(slot)
    if inserted:
        await message.answer(
            f"Доклад принят. Окно: {cfg.start.strftime('%H:%M')}–{cfg.close.strftime('%H:%M')} (МСК)."
        )
    else:
        await message.answer("Доклад уже был принят.")
