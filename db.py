import aiosqlite
from datetime import datetime, timezone


CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cadets (
  tg_user_id INTEGER PRIMARY KEY,
  group_code TEXT NOT NULL,
  full_name  TEXT NOT NULL,
  username   TEXT,             -- @username without '@', may be NULL
  phone      TEXT,             -- phone number, may be NULL
  created_at TEXT NOT NULL,
  is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_cadets_group ON cadets(group_code);

CREATE TABLE IF NOT EXISTS checkins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_user_id INTEGER NOT NULL,
  date TEXT NOT NULL,          -- YYYY-MM-DD (MSK date)
  slot TEXT NOT NULL,          -- 'morning' | 'evening'
  created_at TEXT NOT NULL,    -- ISO UTC
  UNIQUE(tg_user_id, date, slot)
);

CREATE INDEX IF NOT EXISTS idx_checkins_date_slot ON checkins(date, slot);
CREATE INDEX IF NOT EXISTS idx_checkins_user ON checkins(tg_user_id);
"""


class Database:
    def __init__(self, db_path: str):
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(CREATE_SCHEMA_SQL)
            await db.commit()

    async def get_cadet(self, tg_user_id: int) -> dict | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT tg_user_id, group_code, full_name, username, phone, created_at, is_active "
                "FROM cadets WHERE tg_user_id = ?",
                (tg_user_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def upsert_cadet(self, tg_user_id: int, group_code: str, full_name: str, username: str | None) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO cadets(tg_user_id, group_code, full_name, username, phone, created_at, is_active) "
                "VALUES (?, ?, ?, ?, NULL, ?, 1) "
                "ON CONFLICT(tg_user_id) DO UPDATE SET "
                "group_code=excluded.group_code, "
                "full_name=excluded.full_name, "
                "username=excluded.username",
                (tg_user_id, group_code, full_name, username, created_at),
            )
            await db.commit()

    async def update_username(self, tg_user_id: int, username: str | None) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE cadets SET username = ? WHERE tg_user_id = ?",
                (username, tg_user_id),
            )
            await db.commit()

    async def update_phone(self, tg_user_id: int, phone: str | None) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE cadets SET phone = ? WHERE tg_user_id = ?",
                (phone, tg_user_id),
            )
            await db.commit()

    async def count_registered_in_group(self, group_code: str) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM cadets WHERE group_code = ?",
                (group_code,),
            )
            (n,) = await cur.fetchone()
            return int(n)

    async def count_registered_course(self, *, exclude_group_code: str) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM cadets WHERE group_code <> ?",
                (exclude_group_code,),
            )
            (n,) = await cur.fetchone()
            return int(n)

    async def count_registered_by_group_course(self, *, exclude_group_code: str) -> list[tuple[str, int]]:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT group_code, COUNT(*) "
                "FROM cadets "
                "WHERE group_code <> ? "
                "GROUP BY group_code "
                "ORDER BY group_code",
                (exclude_group_code,),
            )
            rows = await cur.fetchall()
            return [(r[0], int(r[1])) for r in rows]

    async def add_checkin(self, tg_user_id: int, date_str: str, slot: str) -> bool:
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "INSERT OR IGNORE INTO checkins(tg_user_id, date, slot, created_at) "
                "VALUES (?, ?, ?, ?)",
                (tg_user_id, date_str, slot, created_at),
            )
            await db.commit()
            return cur.rowcount == 1

    async def missing_by_group(self, group_code: str, date_str: str, slot: str) -> list[tuple[str, str | None, str | None]]:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT c.full_name, c.username, c.phone "
                "FROM cadets c "
                "LEFT JOIN checkins ch "
                "  ON ch.tg_user_id = c.tg_user_id AND ch.date = ? AND ch.slot = ? "
                "WHERE c.is_active = 1 AND c.group_code = ? AND ch.tg_user_id IS NULL "
                "ORDER BY c.full_name",
                (date_str, slot, group_code),
            )
            rows = await cur.fetchall()
            return [(r[0], r[1], r[2]) for r in rows]

    async def missing_all_groups(
        self, date_str: str, slot: str, officers_group_code: str
    ) -> list[tuple[str, str, str | None, str | None]]:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT c.group_code, c.full_name, c.username, c.phone "
                "FROM cadets c "
                "LEFT JOIN checkins ch "
                "  ON ch.tg_user_id = c.tg_user_id AND ch.date = ? AND ch.slot = ? "
                "WHERE c.is_active = 1 AND c.group_code <> ? AND ch.tg_user_id IS NULL "
                "ORDER BY c.group_code, c.full_name",
                (date_str, slot, officers_group_code),
            )
            rows = await cur.fetchall()
            return [(r[0], r[1], r[2], r[3]) for r in rows]

    async def list_registered_in_group(self, group_code: str) -> list[tuple[str, str | None, str | None]]:
        """
        Список зарегистрированных курсантов в группе:
        (full_name, username, phone), сортировка по full_name.
        """
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT full_name, username, phone "
                "FROM cadets "
                "WHERE is_active = 1 AND group_code = ? "
                "ORDER BY full_name",
                (group_code,),
            )
            rows = await cur.fetchall()
            return [(r[0], r[1], r[2]) for r in rows]
