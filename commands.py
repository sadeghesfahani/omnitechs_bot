# bot_commands.py
from aiogram import Bot
from aiogram.types import BotCommand

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Start the bot",),
        BotCommand(command="help", description="Show help and usage guide"),
        BotCommand(command="language", description="Set translation languages"),
        BotCommand(command="ask", description="Ask ChatGPT something"),
        BotCommand(command="cost", description="Check your usage cost"),
        BotCommand(command="user", description="Show your profile info"),
        BotCommand(command="friends", description="List your saved friends"),
    ]
    await bot.set_my_commands(commands)
