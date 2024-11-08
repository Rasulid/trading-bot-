from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import TELEGRAM_TOKEN


class TelegramService:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dp = Dispatcher()

    async def send_message(self, message: str, chat_id: str|int):
        await self.bot.send_message(chat_id=chat_id, text=message)