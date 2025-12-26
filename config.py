from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    officer_ids: set[int]
    db_path: str = "bot.sqlite3"


def _parse_ids(raw: str) -> set[int]:
    raw = (raw or "").strip()
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    admin_ids = _parse_ids(os.getenv("ADMIN_IDS", ""))
    officer_ids = _parse_ids(os.getenv("OFFICER_IDS", ""))

    db_path = os.getenv("DB_PATH", "bot.sqlite3").strip() or "bot.sqlite3"

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        officer_ids=officer_ids,
        db_path=db_path,
    )
