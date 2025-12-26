from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from time_utils import TZ, SLOT_MORNING, SLOT_EVENING
from scheduler_jobs import notify_admin_cadets_start, notify_admin_cadets_close, send_reports

def setup_scheduler(s: AsyncIOScheduler, *, bot, db, config) -> None:
    # Начало утреннего доклада
    s.add_job(
        notify_admin_cadets_start,
        CronTrigger(hour=7, minute=0, timezone=TZ),
        args=[bot, db, config, SLOT_MORNING],
        id="notify_admins_morning_start",
        replace_existing=True,
    )
    # Сообщение о закрытии утреннего доклада
    s.add_job(
        notify_admin_cadets_close,
        CronTrigger(hour=7, minute=30, timezone=TZ),
        args=[bot, db, config],
        id="admins_menu_after_morning_close",
        replace_existing=True,
    )

    # Отчет по утреннему докладу
    s.add_job(
        send_reports,
        CronTrigger(hour=7, minute=31, timezone=TZ),
        args=[bot, db, config, SLOT_MORNING],
        id="reports_morning",
        replace_existing=True,
    )

    # Начало вечернего доклада
    s.add_job(
        notify_admin_cadets_start,
        CronTrigger(hour=21, minute=30, timezone=TZ),
        args=[bot, db, config, SLOT_EVENING],
        id="notify_admins_evening_start",
        replace_existing=True,
    )

    # Сообщение о закрытии вечернего доклада
    s.add_job(
        notify_admin_cadets_close,
        CronTrigger(hour=22, minute=00, timezone=TZ),
        args=[bot, db, config],
        id="admins_menu_after_evening_close",
        replace_existing=True,
    )

    # Отчет по вечернему докладу
    s.add_job(
        send_reports,
        CronTrigger(hour=22, minute=1, timezone=TZ),
        args=[bot, db, config, SLOT_EVENING],
        id="reports_evening",
        replace_existing=True,
    )
