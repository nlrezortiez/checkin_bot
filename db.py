import aiosqlite
from datetime import datetime, timezone


CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cadets (
  tg_user_id INTEGER PRIMARY KEY,
  group_code TEXT NOT NULL,
  full_name  TEXT NOT NULL,
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
                "SELECT tg_user_id, group_code, full_name, created_at, is_active "
                "FROM cadets WHERE tg_user_id = ?",
                (tg_user_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def upsert_cadet(self, tg_user_id: int, group_code: str, full_name: str) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO cadets(tg_user_id, group_code, full_name, created_at, is_active) "
                "VALUES (?, ?, ?, ?, 1) "
                "ON CONFLICT(tg_user_id) DO UPDATE SET "
                "group_code=excluded.group_code, "
                "full_name=excluded.full_name",
                (tg_user_id, group_code, full_name, created_at),
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


    async def count_group_total(self, group_code: str) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM cadets WHERE is_active = 1 AND group_code = ?",
                (group_code,),
            )
            (n,) = await cur.fetchone()
            return int(n)


    async def count_group_checked(self, group_code: str, date_str: str, slot: str) -> int:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(*) "
                "FROM cadets c "
                "JOIN checkins ch ON ch.tg_user_id = c.tg_user_id "
                "WHERE c.is_active = 1 AND c.group_code = ? AND ch.date = ? AND ch.slot = ?",
                (group_code, date_str, slot),
            )
            (n,) = await cur.fetchone()
            return int(n)


    async def missing_by_group(self, group_code: str, date_str: str, slot: str) -> list[str]:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT c.full_name "
                "FROM cadets c "
                "LEFT JOIN checkins ch "
                "  ON ch.tg_user_id = c.tg_user_id AND ch.date = ? AND ch.slot = ? "
                "WHERE c.is_active = 1 AND c.group_code = ? AND ch.tg_user_id IS NULL "
                "ORDER BY c.full_name",
                (date_str, slot, group_code),
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows]


    async def missing_all_groups(self, date_str: str, slot: str, officers_group_code: str) -> list[tuple[str, str]]:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "SELECT c.group_code, c.full_name "
                "FROM cadets c "
                "LEFT JOIN checkins ch "
                "  ON ch.tg_user_id = c.tg_user_id AND ch.date = ? AND ch.slot = ? "
                "WHERE c.is_active = 1 AND c.group_code <> ? AND ch.tg_user_id IS NULL "
                "ORDER BY c.group_code, c.full_name",
                (date_str, slot, officers_group_code),
            )
            rows = await cur.fetchall()
            return [(r[0], r[1]) for r in rows]
