from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def generate_keyboard(json_data):
    keyboard_type = json_data.get("type")
    buttons_data = json_data.get("buttons", [])

    if keyboard_type == "inline":
        keyboard = InlineKeyboardBuilder()
        for row in buttons_data:
            button_row = [
                InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])
                for btn in row
            ]
            keyboard.row(*button_row)
        return keyboard.as_markup()

    elif keyboard_type == "reply":
        keyboard = ReplyKeyboardBuilder()
        resize = json_data.get("resize", True)
        one_time = json_data.get("one_time", False)

        for row in buttons_data:
            button_row = [
                KeyboardButton(
                    text=btn["text"],
                    request_contact=btn.get("request_contact", False),
                    request_location=btn.get("request_location", False)
                )
                for btn in row
            ]
            keyboard.row(*button_row)

        return keyboard.as_markup(resize_keyboard=resize, one_time_keyboard=one_time)

    else:
        return None  # Invalid keyboard type


# Generate the keyboard, showing the selected namespace with a checkmark
async def get_namespace_keyboard(current: str = None):
    builder = InlineKeyboardBuilder()
    options = ["Translate", "Invoices", "Expenses","Chat","Chat bot"]

    for option in options:
        label = f"✅ {option}" if option == current else option
        builder.button(text=label, callback_data=f"namespace:{option}")

    builder.adjust(1)
    return builder.as_markup()