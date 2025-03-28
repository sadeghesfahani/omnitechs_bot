from aiogram.fsm.state import StatesGroup, State


class UserState(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    year_of_birth = State()


class NavigationState(StatesGroup):
    home_page = State()
    translate_page = State()


class TranslationState(StatesGroup):
    waiting_for_first_language = State()


class LanguageState(StatesGroup):
    languages = State()


class Form(StatesGroup):
    namespace = State()
