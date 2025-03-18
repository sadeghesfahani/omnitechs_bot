from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import UserState

router = Router()

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    await message.answer("Hello! What is your name?")
    await state.set_state(UserState.waiting_for_name)

@router.message(UserState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Nice! How old are you?")
    await state.set_state(UserState.waiting_for_age)

@router.message(UserState.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    user_data = await state.get_data()
    name = user_data.get("name")
    age = message.text

    await message.answer(f"Great! Your name is {name} and you are {age} years old.")
    await state.clear()  # Reset state after completion