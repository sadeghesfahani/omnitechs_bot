from aiogram.fsm.state import StatesGroup, State

class UserState(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()