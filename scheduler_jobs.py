import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from keyboards import OFFICERS_GROUP_CODE
from time_utils import now_msk, date_str_msk, slot_config
from reporting import build_missing_report_all, build_missing_report_one_group

async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except (TelegramForbiddenError, TelegramBadRequest):
        return

def _is_officer(user_id: int, officer_ids: set[int]) -> bool:
    return user_id in officer_ids

def _is_admin_cadet(user_id: int, admin_ids: set[int], officer_ids: set[int]) -> bool:
    return (user_id in admin_ids) and (user_id not in officer_ids)

async def notify_admin_cadets_start(bot: Bot, db, config, slot: str) -> None:
    dt = now_msk()
    date_str = date_str_msk(dt)
    cfg = slot_config(slot)

    for admin_id in config.admin_ids:
        if not _is_admin_cadet(admin_id, config.admin_ids, config.officer_ids):
            continue

        cadet = await db.get_cadet(admin_id)
        if not cadet:
            continue
        if cadet["group_code"] == OFFICERS_GROUP_CODE:
            continue

        group_code = cadet["group_code"]
        total = await db.count_group_total(group_code)
        checked = await db.count_group_checked(group_code, date_str, slot)

        text = (
            "Началось время доклада.\n"
            f"Доклад до {cfg.deadline.strftime('%H:%M')} (МСК). "
            f"Окно закрывается в {cfg.close.strftime('%H:%M')}.\n"
            f"Отметились {checked}/{total}"
        )
        await _safe_send(bot, admin_id, text)
        await asyncio.sleep(0.05)

async def send_reports(bot: Bot, db, config, slot: str) -> None:
    dt = now_msk()
    date_str = date_str_msk(dt)

    # 1) Офицерам: общий отчёт по курсу (без OFFICERS)
    if config.officer_ids:
        rows = await db.missing_all_groups(date_str, slot, OFFICERS_GROUP_CODE)
        report = build_missing_report_all(rows)
        header = f"Отчёт ({date_str})"
        text = f"{header}\n\n{report}"
        for оф_id in config.officer_ids:
            await _safe_send(bot, оф_id, text)
            await asyncio.sleep(0.05)

    # 2) Админам-курсантам: отчёт только по своей группе
    for admin_id in config.admin_ids:
        if not _is_admin_cadet(admin_id, config.admin_ids, config.officer_ids):
            continue

        cadet = await db.get_cadet(admin_id)
        if not cadet:
            continue
        if cadet["group_code"] == OFFICERS_GROUP_CODE:
            continue

        group_code = cadet["group_code"]
        missing_names = await db.missing_by_group(group_code, date_str, slot)
        report = build_missing_report_one_group(group_code, missing_names)

        header = f"Отчёт по вашей группе ({date_str})"
        await _safe_send(bot, admin_id, f"{header}\n\n{report}")
        await asyncio.sleep(0.05)
