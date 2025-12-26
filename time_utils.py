from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Moscow")

SLOT_MORNING = "morning"
SLOT_EVENING = "evening"

@dataclass(frozen=True)
class SlotConfig:
    slot: str
    start: time
    deadline: time
    close: time

MORNING = SlotConfig(
    slot=SLOT_MORNING,
    start=time(7, 00),
    deadline=time(7, 30),
    close=time(7, 30),
)

EVENING = SlotConfig(
    slot=SLOT_EVENING,
    start=time(21, 30),
    deadline=time(22, 00),
    close=time(22, 00),
)

def now_msk() -> datetime:
    return datetime.now(tz=TZ)

def date_str_msk(dt: datetime) -> str:
    return dt.date().isoformat()  # YYYY-MM-DD

def current_slot(dt: datetime) -> str | None:
    t = dt.timetz().replace(tzinfo=None)
    if MORNING.start <= t <= MORNING.close:
        return SLOT_MORNING
    if EVENING.start <= t <= EVENING.close:
        return SLOT_EVENING
    return None

def slot_config(slot: str) -> SlotConfig:
    if slot == SLOT_MORNING:
        return MORNING
    if slot == SLOT_EVENING:
        return EVENING
    raise ValueError(f"Unknown slot: {slot}")
