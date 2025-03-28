import asyncio
from aiogram import Bot, Dispatcher

from commands import set_bot_commands
from config import BOT_TOKEN
from handlers import router
from database import init_db

async def main():
    await init_db()  # Initialize database
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    print("Bot commands are loading")
    # Set bot command menu
    await set_bot_commands(bot)
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())