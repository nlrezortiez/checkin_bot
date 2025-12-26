from aiogram.fsm.state import StatesGroup, State


class Registration(StatesGroup):
    choose_group = State()
    enter_name = State()
