import asyncio
import logging
import json
import database


from aiogram import Bot, Dispatcher
from handlers import router as handlers_router
from inline_keyboards import router as keyboards_router, check_schedule_and_notify


with open('config.json', 'r', encoding="utf-8") as config_file:
    config = json.load(config_file)


BOT_TOKEN = config["BOT_TOKEN"]


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


database.init_db()
logging.basicConfig(level=logging.INFO)
dp.include_router(handlers_router)
dp.include_router(keyboards_router)


async def on_startup(dp):
    await bot.delete_webhook(drop_pending_updates=True)  #Удаление вебхуков


async def main():
    await on_startup(dp)                                 # Вызов функций при старте
    await dp.start_polling(bot)                          # Запуск бота с передачей экземпляра бота
    asyncio.create_task(check_schedule_and_notify(bot))


if __name__ == "__main__":
    asyncio.run(main())