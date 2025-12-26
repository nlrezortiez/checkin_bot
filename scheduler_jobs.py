import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from keyboards import OFFICERS_GROUP_CODE, role_menu_kb
from time_utils import now_msk, date_str_msk, slot_config, current_slot, SLOT_MORNING, SLOT_EVENING
from reporting import build_missing_report_all, build_missing_report_one_group


async def _safe_send(bot: Bot, chat_id: int, text: str, reply_markup=None) -> None:
    try:
        await bot.send_message(chat_id, text, reply_markup=reply_markup)
    except (TelegramForbiddenError, TelegramBadRequest):
        return


def _is_admin_cadet(user_id: int, admin_ids: set[int], officer_ids: set[int]) -> bool:
    return (user_id in admin_ids) and (user_id not in officer_ids)


async def notify_admin_cadets_start(bot: Bot, db, config, slot: str) -> None:
    dt = now_msk()
    cfg = slot_config(slot)

    show_btn = (current_slot(dt) == slot)

    for admin_id in config.admin_ids:
        if not _is_admin_cadet(admin_id, config.admin_ids, config.officer_ids):
            continue

        cadet = await db.get_cadet(admin_id)
        if not cadet or cadet["group_code"] == OFFICERS_GROUP_CODE:
            continue

        menu = role_menu_kb(
            is_officer=False,
            is_admin_cadet=True,
            show_not_reported=show_btn,
        )

        text = (
            "Началось время доклада.\n"
            f"Доклад до {cfg.deadline.strftime('%H:%M')} (МСК). "
        )
        await _safe_send(bot, admin_id, text, reply_markup=menu)
        await asyncio.sleep(0.05)


async def notify_admin_cadets_close(bot: Bot, db, config) -> None:
    for admin_id in config.admin_ids:
        if not _is_admin_cadet(admin_id, config.admin_ids, config.officer_ids):
            continue

        cadet = await db.get_cadet(admin_id)
        if not cadet or cadet["group_code"] == OFFICERS_GROUP_CODE:
            continue

        menu = role_menu_kb(
            is_officer=False,
            is_admin_cadet=True,
            show_not_reported=False,
        )
        await _safe_send(bot, admin_id, "Время доклада закончено.", reply_markup=menu)
        await asyncio.sleep(0.05)


async def send_reports(bot: Bot, db, config, slot: str) -> None:
    dt = now_msk()
    date_str = date_str_msk(dt)

    if slot == SLOT_MORNING:
        officer_header = f"Утренний отчёт ({date_str})"
    elif slot == SLOT_EVENING:
        officer_header = f"Вечерний отчёт ({date_str})"
    else:
        officer_header = f"Отчёт ({date_str})"

    # 1) Офицерам: общий отчёт по курсу (без OFFICERS)
    if config.officer_ids:
        rows = await db.missing_all_groups(date_str, slot, OFFICERS_GROUP_CODE)
        report = build_missing_report_all(rows)
        text = f"{officer_header}\n\n{report}"

        for officer_id in config.officer_ids:
            await _safe_send(bot, officer_id, text)
            await asyncio.sleep(0.05)

    # 2) Админам-курсантам: отчёт только по своей группе
    for admin_id in config.admin_ids:
        if not _is_admin_cadet(admin_id, config.admin_ids, config.officer_ids):
            continue

        cadet = await db.get_cadet(admin_id)
        if not cadet or cadet["group_code"] == OFFICERS_GROUP_CODE:
            continue

        group_code = cadet["group_code"]
        missing_rows = await db.missing_by_group(group_code, date_str, slot)
        report = build_missing_report_one_group(group_code, missing_rows)

        header = f"Отчёт по вашей группе ({date_str})"
        await _safe_send(bot, admin_id, f"{header}\n\n{report}")
        await asyncio.sleep(0.05)
