import os

from aiogram import Router, Bot
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import subprocess
from openai_helper import ask_openai, transcribe, create_voice_out_of_text
from states import UserState, NavigationState, translationState
from utils.keyboard import generate_keyboard

router = Router()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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
    user_text = ""
    message_type =""
    if message.voice:  # If the user sends a voice message
        await message.answer("Fetching audio 🤖")
        message_type = "voice"
        file_info = await message.bot.get_file(message.voice.file_id)  # Fetch file info
        file_path = f"downloads/{message.voice.file_id}.ogg"
        await message.bot.download_file(file_info.file_path, file_path)  # Download the file

        await message.answer("Converting audio to text 🤖")
        # Convert OGG to WAV for Whisper
        wav_path = file_path.replace(".ogg", ".wav")
        subprocess.run(["/opt/homebrew/bin/ffmpeg", "-i", file_path, wav_path, "-y"])

        user_text = transcribe(wav_path)

    else:  # If the user sends a text message
        user_text = message.text

    final_message = (
        "Please translate to either English or Polish based on the user's input. "
        "If it's in English, translate it to Polish. If it's in Polish, translate it to English. "
        f"The user message is as follows: '{user_text}'"
    )
    response = await ask_openai(final_message)
    if message_type == "voice":
        await message.answer("Converting text to audio 🤖")
        output_path = create_voice_out_of_text(message.message_id,response)
        print(output_path)
        audio_file = FSInputFile(output_path)
        # Send the file to the user
        await message.answer_audio(audio=audio_file)
        # message.answer_audio(audio_file=output_path)

    else:
        await message.answer(response)
@router.message()
async def handle_text(message: Message, state: FSMContext):
    if message.text == "Translate":
        await state.set_state(translationState.waiting_for_first_language)