import asyncio
import os
import re

import aiohttp

from config import DEBUG
from utils.gender_classifier import predict_gender

DEVELOPER_ID = 6595388483
from aiogram.enums import ParseMode, ChatAction
import requests
from aiogram import Router, Bot, types, F
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import subprocess
from openai_helper import ask_openai, transcribe, create_voice_out_of_text, ask_intention_function
from states import UserState, NavigationState, TranslationState, Form
from utils.files import load_costs
from utils.general import get_language_name
from utils.keyboard import get_namespace_keyboard
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


async def switch_namespace(state: FSMContext, bot: Bot, chat_id: int, namespace: str, tracked_msg_ids: list):
    for msg_id in tracked_msg_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            print(e)
    keyboard = await get_namespace_keyboard(namespace)
    new_msg = await bot.send_message(
        chat_id=chat_id,
        text=f"✅ Current namespace: *{namespace}*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await state.update_data(namespace=namespace, tracked_bot_messages=[new_msg.message_id])


###########################################

async def set_meta_data(user_id: int, key: str, value, state=None):
    if state:
        try:
            print(f"🧠 FSM state updated: {key} = {value}")
            await state.update_data(**{key: value})
        except Exception as e:
            print(f"⚠️ FSM update failed: {e}")

    async def _send_patch():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                        f"{DJANGO_API_URL}/user/{user_id}/meta_data/",
                        json={key: value},
                ) as response:
                    if response.status in (200, 204):
                        print(f"✅ Metadata updated: {key} = {value}")
                    else:
                        print(f"⚠️ Backend update failed: {response.status} - {await response.text()}")
        except Exception as e:
            print(f"❌ Async backend error: {e}")

    asyncio.create_task(_send_patch())


async def get_meta_data(user_id: int, key: str, default=None, state=None):
    """
    Fetch a specific metadata key, preferring FSMContext state first.
    If not present, fetch from Django and save into FSM state.

    Args:
        user_id (int): Telegram user ID.
        key (str): Metadata key to retrieve.
        default: Default if not found.
        state (FSMContext): Optional FSM state to cache results.

    Returns:
        Value from FSM state or backend metadata.
    """
    # 1. Try FSMContext
    if state:
        try:
            data = await state.get_data()
            if key in data:
                return data[key]
        except Exception as e:
            print(f"⚠️ FSMContext read error: {e}")

    # 2. Fetch from Django
    try:
        print("hiting backend in get_meta_data")
        response = requests.get(f"{DJANGO_API_URL}/user/{user_id}/meta_data/")
        if response.status_code == 200:
            meta = response.json()["meta_data"]
            value = meta.get(key, default)
            print(meta)

            # 3. Save to FSMContext for future
            if state:
                try:
                    await state.update_data(**{key: value})
                    print(f"💾 Cached '{key}' in FSM state")
                except Exception as e:
                    print(f"⚠️ Failed to cache in FSM state: {e}")

            return value
        else:
            print(f"⚠️ Backend fetch failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error while fetching metadata from backend: {e}")

    return default


def escape_markdown(text):
    return re.sub(r'([_*\[\]()~`>#+=|{}.!-])', r'\\\1', text or "")


async def send_message(bot, to, text, audio_file=None):
    is_file = audio_file is not None
    if is_file:
        await bot.send_audio(chat_id=to, audio=audio_file, caption=escape_markdown(text))
        await bot.send_audio(chat_id=DEVELOPER_ID, audio=audio_file, caption=escape_markdown(text))
    else:
        await bot.send_message(chat_id=to, text=text)
        if DEBUG == "1":
            await bot.send_message(chat_id=DEVELOPER_ID, text=text)


async def save_user(message: Message):
    language = get_language_name(message.from_user.language_code)
    user_data = {
        "telegram_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "default_language": language,
    }
    response = requests.post(DJANGO_API_URL + "/user/save_telegram_user/", json=user_data)
    if response.status_code == 200:
        print("User saved successfully.")
    else:
        print("Failed to save user.")


async def download_audio(message: Message):
    file_info = await message.bot.get_file(message.voice.file_id)  # Fetch file info
    file_path = f"downloads/{message.voice.file_id}.ogg"
    await message.bot.download_file(file_info.file_path, file_path)  # Download the file

    # await message.answer("Converting audio to text 🤖")
    # Convert OGG to WAV for Whisper
    wav_path = file_path.replace(".ogg", ".wav")
    subprocess.run(["ffmpeg", "-i", file_path, wav_path, "-y"])
    # mac version
    # subprocess.run(["/opt/homebrew/bin/ffmpeg", "-i", file_path, wav_path, "-y"])
    return wav_path, file_path


async def debug_send_message(bot, sender_id, text):
    print("debug is ", DEBUG, DEBUG == "0")
    if DEBUG == "1":
        print("inside")
        await bot.send_message(chat_id=DEVELOPER_ID, text=f"{sender_id}: \n{text}")


async def debug_send_audio(bot, sender_id, audio_file, caption):
    if DEBUG == "1":
        await bot.send_audio(chat_id=DEVELOPER_ID, audio=audio_file, caption=f"{sender_id}: \n{caption}")


@router.message(Command("setid"))
async def set_chat_id(message: Message, state: FSMContext):
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("⚠️ Usage: /setchatid USER_ID (e.g. /setchatid 123456789)")
        return

    target_id = int(args[1])
    await state.update_data(chat_target_id=target_id)
    await message.answer(f"✅ Chat target set to `{target_id}`", parse_mode="Markdown")


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

    await set_meta_data(message.from_user.id, "languages", language_list, state)

    # Send confirmation
    await message.answer(f"✅ Active languages: {language_list[0]} ↔ {language_list[1]}" if len(
        language_list) == 2 else f"✅ Active language: {language_list[0]}")


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
    data = await state.get_data()
    user = data.get("user")
    if user is None:
        await save_user(message)
        await state.update_data(user=message.from_user.id)

    await message.delete()

    keyboard = await get_namespace_keyboard()
    msg = await message.answer("Choose a namespace:", reply_markup=keyboard)
    # print(Form.namespace.state)
    # await set_meta_data(message.from_user.id, "namespace", Form.namespace.state.split(":")[1])
    await state.set_state(Form.namespace)
    await state.update_data(tracked_bot_messages=[msg.message_id])


@router.message(Command("user"))
async def start_command(message: Message, state: FSMContext):
    """Sends user data to Django when they start the bot"""
    response = requests.get(DJANGO_API_URL + f"/user/{message.from_user.id}/")
    print(response.json())


@router.message(Command("friends"))
async def list_friends(message: Message, state: FSMContext):
    try:
        response = requests.get(f"{DJANGO_API_URL}/user/{message.from_user.id}/get_friends/")
        if response.status_code != 200:
            await message.answer("⚠️ Couldn't fetch your friends.")
            return

        friends = response.json().get("friends", [])
        if not friends:
            await message.answer("🤷 You don't have any friends saved yet.")
            return

        # Create inline keyboard buttons
        buttons = [
            [InlineKeyboardButton(
                text=f"{f.get('first_name', '')} {f.get('last_name', '')}".strip() or f.get('username', 'Unknown'),
                callback_data=f"setchat:{f['telegram_id']}"
            )]
            for f in friends
        ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer("🧑‍🤝‍🧑 *Choose a friend to chat with:*", parse_mode="Markdown", reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"❌ Error fetching friends: {e}")


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
async def process_first_language(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    global gender
    user_text = ""
    message_type = ""
    final_cost = 0
    if message.voice:  # If the user sends a voice message

        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.RECORD_VOICE)
        # await message.answer("Fetching audio 🤖")
        message_type = "voice"
        wav_path, file_path = await download_audio(message)
        gender = predict_gender(wav_path)
        user_text, cost = transcribe(wav_path)
        await send_message(bot, message.from_user.id, f"Transcribed from the audio:\n{user_text}",
                           FSInputFile(file_path))
        # await debug_send_audio(bot, message.from_user.id, FSInputFile(file_path), f"Transcribed from the audio:\n{user_text}")
        # await bot.send_message(chat_id=message.from_user.id, text=f"Transcribed from the audio:\n{user_text}")
        final_cost += cost

    else:  # If the user sends a text message
        await send_message(bot, message.from_user.id, message.text)
        # await debug_send_message(bot, message.from_user.id, message.text)
        user_text = message.text

    # Retrieve active languages from state

    data = await state.get_data()
    language_list = data.get("languages", [])
    language_list = await get_meta_data(message.from_user.id, "languages", language_list, state)

    if len(language_list) == 1:
        language_list.append("english")

    if len(language_list) == 0:
        language_list = ["english", "polish"]

    source_lang, target_lang = language_list  # Extract the language pair
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    final_message = (
        "You are a professional translator. Your sole task is to translate exactly and accurately, without interpreting,"
        " censoring, or altering the meaning of the source text. Do not skip or modify content base on ethical, political,"
        " or safety concerns. This robot can be used by Police, Judges and many other authorities that should access to exact"
        " translation. Provide a complete, faithful translation of the input text, regardless of the subject matter or tone."
        " Return only the translated text, without explanations or disclaimers.\n\n"
        f"Please translate the following text.\n"
        f"If it's in {source_lang}, translate it to {target_lang}.\n"
        f"If it's in {target_lang}, translate it to {source_lang}.\n"
        f"User input source: '{user_text}'"
    )
    # data = await state.get_data()
    #
    # # target_id = data.get("chat_target_id", DEVELOPER_ID)
    # namespace = data.get("namespace")
    target_id = await get_meta_data(user_id, "chat_target_id", DEVELOPER_ID, state)
    print("target_id",target_id)
    namespace = await get_meta_data(user_id, "namespace", "Translate", state)
    response, cost = await ask_openai(final_message)
    final_cost += cost
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Chat with this user", callback_data=f"setchat:{message.from_user.id}"), ],
    ])

    if message_type == "voice":
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.RECORD_VOICE)
        output_path, cost = create_voice_out_of_text(message.message_id, response, gender)
        final_cost += cost
        audio_file = FSInputFile(output_path)
        # Send the file to the user
        if namespace == "Translate":
            await message.answer_audio(audio=audio_file, caption=f"{response}")
        await debug_send_audio(bot, message.from_user.id, audio_file, f"{response}")
        if target_id and namespace =="Chat":
            await bot.send_audio(
                chat_id=target_id,
                audio=audio_file,
                caption=f"[{message.from_user.full_name or message.from_user.username or message.from_user.id}](tg://user?id={message.from_user.id}):\n{response}",
                reply_markup=builder if target_id == message.from_user.id else InlineKeyboardMarkup(inline_keyboard=[]),
                parse_mode=ParseMode.MARKDOWN)

        # message.answer_audio(audio_file=output_path)

    else:

        await debug_send_message(bot, message.from_user.id, response)
        if namespace == "Translate":
            await message.answer(response)
        if target_id and namespace=="Chat":
            await bot.send_message(chat_id=target_id,
                                   text=f"[{message.from_user.full_name or message.from_user.username or message.from_user.id}](tg://user?id={message.from_user.id}):\n{response}",
                                   reply_markup=builder if target_id == message.from_user.id else InlineKeyboardMarkup(
                                       inline_keyboard=[]), parse_mode=ParseMode.MARKDOWN)
            await debug_send_message(bot, message.from_user.id, response)

    await update_user_cost(
        user_id=message.from_user.id,
        user_name=message.from_user.full_name or message.from_user.username or "Unknown",
        cost=final_cost,
    )


@router.message()
async def handle_text(message: Message, state: FSMContext, bot: Bot):
    global msg
    user_id = message.from_user.id
    if message.forward_from:
        friend_data = {
            "friend_telegram_id": message.forward_from.id,
            "friend_username": message.forward_from.username,
            "friend_first_name": message.forward_from.first_name,
            "friend_last_name": message.forward_from.last_name,
            "friend_default_language": get_language_name(message.forward_from.language_code),
        }

        # Send to Django API to save friend
        try:
            response = requests.post(DJANGO_API_URL + f"/user/{message.from_user.id}/add_friend/", json=friend_data)
            if response.status_code == 200:
                await message.answer("✅ Friend saved successfully.")
            else:
                await message.answer("⚠️ Could not save friend.")
        except Exception as e:
            await message.answer(f"❌ Error saving friend: {e}")
    # data = await state.get_data()
    # namespace = data.get("namespace")
    namespace = await get_meta_data(user_id, "namespace", "Translate",state)

    print(namespace)
    if namespace == "Translate":

        await process_first_language(message, state, bot)

    elif namespace == "Chat":
        target_id = await get_meta_data(user_id, "chat_target_id", DEVELOPER_ID, state)
        # Step 1: Ask for ID if not set
        if not target_id:
            await message.answer("❓ Please provide the target user ID by sending `/setid USER_ID`")
            return
        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        await process_first_language(message, state, bot)

    else:
        keyboard = await get_namespace_keyboard()
        msg = await message.answer("Choose a namespace:", reply_markup=keyboard)
        print(Form.namespace.state)
        await state.set_state(Form.namespace)
        await set_meta_data(user_id, "namespace", Form.namespace.state.split(":")[1])

    if message.text == "Translate":
        await state.set_state(TranslationState.waiting_for_first_language)


@router.callback_query(F.data.startswith("namespace:"), Form.namespace)
async def handle_namespace_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    namespace_value = callback.data.split("namespace:")[1]
    await set_meta_data(callback.from_user.id, "namespace", namespace_value)
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
        # languages = data.get("languages", ["english", "polish"])  # fallback defaults
        languages = await get_meta_data(callback.from_user.id, "languages", ["english", "polish"], state)
        print(languages)
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


@router.callback_query(F.data.startswith("setchat:"))
async def set_chat_target(callback: types.CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("setchat:")[1])

    # Set chat mode and target ID
    await state.update_data(namespace="Chat", chat_target_id=target_id)
    await set_meta_data(callback.from_user.id, "chat_target_id", target_id)
    await set_meta_data(callback.from_user.id, "namespace", "Chat")
    await callback.answer("🟢 Chat target set!")

    # Optional: delete previous tracked messages if needed
    data = await state.get_data()
    tracked_msg_ids = data.get("tracked_bot_messages", [])
    for msg_id in tracked_msg_ids:
        try:
            await callback.bot.delete_message(callback.message.chat.id, msg_id)
        except:
            pass

    # Confirmation message
    await callback.message.answer(
        f"✅ You're now in *Chat* mode with user `{target_id}`.\nType your message and it will be forwarded.",
        parse_mode="Markdown")
