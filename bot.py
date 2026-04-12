from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
import asyncio

bot = Bot("8629214575:AAE8l0FcxWWxEjRjeZvO-lgmaU2I-izlwW0")
dp = Dispatcher()

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Играть", web_app=WebAppInfo(
            url="https://adamhubyt.github.io/bot/?v=1"
        ))]
    ],
    resize_keyboard=True
)

@dp.message()
async def start(msg: types.Message):
    await msg.answer("Жми играть", reply_markup=kb)

async def main():
    await dp.start_polling(bot)

asyncio.run(main())