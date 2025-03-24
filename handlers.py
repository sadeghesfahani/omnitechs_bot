import os

from aiogram.enums import ParseMode, ChatAction
from babel import Locale
import requests
from aiogram import Router, Bot, types, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import subprocess
from openai_helper import ask_openai, transcribe, create_voice_out_of_text, ask_intention_function
from states import UserState, NavigationState, TranslationState, Form
from utils.files import load_costs
from utils.general import get_language_name
from utils.keyboard import generate_keyboard, get_namespace_keyboard
from utils.open_ai import update_user_cost

router = Router()
DJANGO_API_URL = "http://127.0.0.1:8000"
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
    ]
}


@router.message(Command("intention"))
async def ask_intention(message: Message):
    prompt = message.text.replace("/intention", "").strip()
    if not prompt:
        await message.answer("Please provide a prompt after /intention")
        return
    response, cost = await ask_intention_function(prompt)
    await message.answer(response)
    await update_user_cost(
        user_id=message.from_user.id,
        user_name=message.from_user.full_name or message.from_user.username or "Unknown",
        cost=cost
    )



@router.message(Command("cost"))
async def get_user_cost(message: Message):
    """Command to check the cost for each user in a formatted table."""
    user_costs = load_costs()  # Load costs from file

    user_id_str = str(message.from_user.id)
    user_cost = user_costs.get(user_id_str, {"cost": 0})["cost"]

    # Calculate total cost across all users
    total_cost = sum(user["cost"] for user in user_costs.values())

    # Format the table header
    table_header = "👥 *User*            | 💰 *Cost (USD)*\n" + "-" * 30 + "\n"

    # Format each user's cost with their name
    table_rows = [
        f"{user['name'][:15]:<15} | ${user['cost']:.4f}"
        for user in user_costs.values()
    ]

    # Combine everything
    response_text = (
        f"💰 *Your total OpenAI API usage cost:* `${user_cost:.4f}`\n"
        f"🌍 *Total usage by all users:* `${total_cost:.4f}`\n\n"
        f"📊 *Cost Breakdown:*\n"
        f"```{table_header}\n" + "\n".join(table_rows) + "```"
    )

    await message.answer(response_text, parse_mode="MarkdownV2")


@router.message(Command("help"))
async def send_help(message: Message):
    help_text = (
        "🤖 *Translation Bot - Quick Guide*\n"
    "📝 Supports *text & voice translation*.\n\n"
    "📌 *Commands:*\n"
    "🔄 /language first_language second_language – Set translation languages\n"
    "💬 /ask your question – Ask ChatGPT\n"
    "🔄 /start – Restart the bot\n"
    "ℹ️ Use /help anytime for guidance."
    )

    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("language"))
async def set_languages(message: Message, state: FSMContext):
    args = message.text.split()[1:]  # Extracts the arguments after "/language"

    if not args:
        await message.answer("❌ Please specify one or two languages. Example: `/language english polish`")
        return

    # Retrieve current state
    data = await state.get_data()
    language_list = data.get("languages", [])

    # Handle input logic
    if len(args) == 1:
        # If only one language is provided, keep the last one and add the new one
        if language_list:
            language_list = [language_list[-1], args[0].lower()]
        else:
            language_list = [args[0].lower()]
    elif len(args) >= 2:
        # If two languages are provided, overwrite the list
        language_list = [args[0].lower(), args[1].lower()]

    # Ensure max size is 2
    language_list = language_list[-2:]

    # Save updated state
    await state.update_data(languages=language_list)

    # Send confirmation
    await message.answer(f"✅ Active languages: {language_list[0]} ↔ {language_list[1]}" if len(language_list) == 2 else f"✅ Active language: {language_list[0]}")

@router.message(Command("menu"))
async def send_inline_keyboard(message: Message,state: FSMContext,bot: Bot):
    await message.delete()

    keyboard = await get_namespace_keyboard()
    msg = await message.answer("Choose a namespace:", reply_markup=keyboard)
    await state.set_state(Form.namespace)
    await state.update_data(tracked_bot_messages=[msg.message_id])

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
    response, _ = await ask_openai(user_input)

    await message.answer(response)



@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """Sends user data to Django when they start the bot"""
    language = get_language_name(message.from_user.language_code)
    user_data = {
        "telegram_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "default_language": language,
    }
    print(message.from_user)
    # Send data to Django
    response = requests.post(DJANGO_API_URL + "/user/save_telegram_user/", json=user_data)

    # Handle response
    if response.status_code == 200:
        await message.answer("Welcome! Your data has been saved.")
    else:
        await message.answer("Error saving your data.")

    await message.delete()

    keyboard = await get_namespace_keyboard()
    msg = await message.answer("Choose a namespace:", reply_markup=keyboard)
    await state.set_state(Form.namespace)
    await state.update_data(tracked_bot_messages=[msg.message_id])

@router.message(Command("user"))
async def start_command(message: Message, state: FSMContext):
    """Sends user data to Django when they start the bot"""
    response = requests.get(DJANGO_API_URL + f"/user/{message.from_user.id}/")
    print(response.json())



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


@router.message(TranslationState.waiting_for_first_language)
async def process_first_language(message: Message, state: FSMContext, bot:Bot):

    user_text = ""
    message_type =""
    final_cost = 0
    if message.voice:  # If the user sends a voice message
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.RECORD_VOICE)
        # await message.answer("Fetching audio 🤖")
        message_type = "voice"
        file_info = await message.bot.get_file(message.voice.file_id)  # Fetch file info
        file_path = f"downloads/{message.voice.file_id}.ogg"
        await message.bot.download_file(file_info.file_path, file_path)  # Download the file

        # await message.answer("Converting audio to text 🤖")
        # Convert OGG to WAV for Whisper
        wav_path = file_path.replace(".ogg", ".wav")
        subprocess.run(["/opt/homebrew/bin/ffmpeg", "-i", file_path, wav_path, "-y"])

        user_text, cost = transcribe(wav_path)
        final_cost += cost

    else:  # If the user sends a text message
        user_text = message.text

    # Retrieve active languages from state
    data = await state.get_data()
    language_list = data.get("languages", [])

    if len(language_list) == 1:
        language_list.append("english")

    if len(language_list) == 0:
        language_list = ["english", "polish"]


    source_lang, target_lang = language_list  # Extract the language pair
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    final_message = (
        f"Please translate the following text.\n"
        f"If it's in {source_lang}, translate it to {target_lang}.\n"
        f"If it's in {target_lang}, translate it to {source_lang}.\n"
        f"User message: '{user_text}'"
    )
    response, cost = await ask_openai(final_message)
    final_cost += cost

    if message_type == "voice":
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.RECORD_VOICE)
        output_path, cost = create_voice_out_of_text(message.message_id,response)
        final_cost += cost
        audio_file = FSInputFile(output_path)
        # Send the file to the user
        await message.answer_audio(audio=audio_file)
        # message.answer_audio(audio_file=output_path)

    else:
        await message.answer(response)

    await update_user_cost(
        user_id=message.from_user.id,
        user_name=message.from_user.full_name or message.from_user.username or "Unknown",
        cost=final_cost,
    )

@router.message()
async def handle_text(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    namespace = data.get("namespace")

    if namespace == "Translate":
        await process_first_language(message, state, bot)

    elif namespace == "Chat":
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        response, _ = await ask_openai(message.text)

        await message.answer(response)

    else:
        await message.answer(f"❌ No handler defined for namespace: `{namespace}`")
    if message.text == "Translate":
        await state.set_state(TranslationState.waiting_for_first_language)



@router.callback_query(F.data.startswith("namespace:"), Form.namespace)
async def handle_namespace_callback(callback: types.CallbackQuery, state: FSMContext,bot: Bot):
    namespace_value = callback.data.split("namespace:")[1]
    await state.update_data(namespace=namespace_value)

    await callback.answer()

    # Get and delete all previous tracked bot messages
    data = await state.get_data()
    tracked_msg_ids = data.get("tracked_bot_messages", [])

    for msg_id in tracked_msg_ids:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
        except:
            pass  # Might already be deleted or invalid

    # Send new inline keyboard
    keyboard = await get_namespace_keyboard(namespace_value)
    # Base message
    new_text = f"✅ Current namespace: *{namespace_value}*\n\n"

    if namespace_value.lower() == "translate":
        languages = data.get("languages", ["english", "polish"])  # fallback defaults
        if len(languages) < 2:
            languages.append("english")
        lang1, lang2 = languages[:2]
        new_text += (
            f"\n\n🌍 Current languages: *{lang1}* ↔ *{lang2}*"
            f"\n\n🛠️ To change, use: `/language {lang1} {lang2}`"
        )
    new_msg = await callback.message.answer(new_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Track only this new message
    await state.update_data(tracked_bot_messages=[new_msg.message_id])