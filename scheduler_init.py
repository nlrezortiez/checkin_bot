from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from time_utils import TZ, SLOT_MORNING, SLOT_EVENING
from scheduler_jobs import notify_admin_cadets_start, send_reports

def setup_scheduler(s: AsyncIOScheduler, *, bot, db, config) -> None:
    # Начало утреннего доклада
    s.add_job(
        notify_admin_cadets_start,
        CronTrigger(hour=17, minute=00, timezone=TZ),
        args=[bot, db, config, SLOT_MORNING],
        id="notify_admins_morning_start",
        replace_existing=True,
    )

    # Отчет по утреннему докладу
    s.add_job(
        send_reports,
        CronTrigger(hour=17, minute=12, timezone=TZ),
        args=[bot, db, config, SLOT_MORNING],
        id="reports_morning",
        replace_existing=True,
    )

    # Начало вечернего доклада
    s.add_job(
        notify_admin_cadets_start,
        CronTrigger(hour=17, minute=15, timezone=TZ),
        args=[bot, db, config, SLOT_EVENING],
        id="notify_admins_evening_start",
        replace_existing=True,
    )

    # Отчет по вечернему докладу
    s.add_job(
        send_reports,
        CronTrigger(hour=17, minute=22, timezone=TZ),
        args=[bot, db, config, SLOT_EVENING],
        id="reports_evening",
        replace_existing=True,
    )
