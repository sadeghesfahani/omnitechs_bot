from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from openai_helper import ask_openai
from states import UserState, NavigationState, translationState
from utils.keyboard import generate_keyboard

router = Router()


INLINE_KEYBOARD_JSON = {
    "type": "inline",
    "buttons": [
        [{"text": "Option 1", "callback_data": "option_1"}],
        [{"text": "Option 2", "callback_data": "option_2"}, {"text": "Option 3", "callback_data": "option_3"}]
    ]
}

REPLY_KEYBOARD_JSON = {
    "type": "reply",
    "resize": True,
    "one_time": True,
    "buttons": [
        [{"text": "Translate"}],
        [{"text": "Send Contact (test)", "request_contact": True}],
        [{"text": "Share Location (test)", "request_location": True}]
    ]
}
@router.message(Command("menu"))
async def send_inline_keyboard(message: Message):
    keyboard = generate_keyboard(INLINE_KEYBOARD_JSON)
    await message.answer("Choose an option:", reply_markup=keyboard)

@router.message(Command("menu1"))
async def send_inline_keyboard(message: Message):
    keyboard = generate_keyboard(REPLY_KEYBOARD_JSON)
    await message.answer("Choose an option:", reply_markup=keyboard)

@router.message(Command("ask"))
async def chat_with_openai(message: Message):
    user_input = message.text.replace("/ask", "").strip()

    if not user_input:
        await message.answer("Please provide a question after /ask")
        return

    await message.answer("Thinking... 🤖")
    response = await ask_openai(user_input)

    await message.answer(response)

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    keyboard = generate_keyboard(REPLY_KEYBOARD_JSON)
    await message.answer("Welcome to the Omni Techs AI chatbot, please choose an area",reply_markup=keyboard)



@router.message(NavigationState.translate_page)
async def translate_command(message: Message, state: FSMContext):
    await message.answer("You can translate")


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


@router.message(translationState.waiting_for_first_language)
async def process_first_language(message: Message, state: FSMContext):
    await message.answer("Thinking... 🤖")
    final_message = "Please translate to either english or polish based on what the user input is, if it's in english translate to polish, if it's polish, translate to English. the user message is as the following: '" + message.text + "'"
    response = await ask_openai(final_message)

    await message.answer(response)
@router.message()
async def handle_text(message: Message, state: FSMContext):
    if message.text == "Translate":
        await state.set_state(translationState.waiting_for_first_language)