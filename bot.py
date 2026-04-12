from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import asyncio

BOT_TOKEN = "8629214575:AAE8l0FcxWWxEjRjeZvO-lgmaU2I-izlwW0"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

WEBAPP_URL = "https://adamhubyt.github.io/bot/?v=5"  # твой GitHub Pages

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Играть", web_app=WebAppInfo(url=WEBAPP_URL))]
    ],
    resize_keyboard=True
)

@dp.message()
async def start(msg: types.Message):
    await msg.answer("Нажми и играй 👇", reply_markup=kb)

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
