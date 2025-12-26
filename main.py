import asyncio
import sys
import logging

from dotenv import load_dotenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scheduler_init import setup_scheduler
from handlers_checkin import router as checkin_router

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from config import load_config
from db import Database

from handlers_start import router as start_router
from handlers_admin_menu import router as admin_menu_router


class DependenciesMiddleware(BaseMiddleware):
    def __init__(self, db: Database, config):
        self._db = db
        self._config = config

    async def __call__(self, handler, event, data):
        data["db"] = self._db
        data["config"] = self._config
        return await handler(event, data)


async def main():
    load_dotenv()
    config = load_config()
    db = Database(config.db_path)
    await db.init()

    bot = Bot(token=config.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DependenciesMiddleware(db=db, config=config))

    dp.include_router(start_router)
    dp.include_router(admin_menu_router)
    dp.include_router(checkin_router)

    scheduler = AsyncIOScheduler()
    setup_scheduler(scheduler, bot=bot, db=db, config=config)
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
