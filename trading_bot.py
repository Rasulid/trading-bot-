import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TELEGRAM_TOKEN, TARGET_PROFIT, SYMBOL
from bybit_service import BybitService
from telegram_service import TelegramService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

bybit_service = BybitService()
telegram_service = TelegramService()


class TradingBot:
    def __init__(self, bybit_service: BybitService, telegram_service: TelegramService, sender_id: str | int):
        self.bybit_service = bybit_service
        self.telegram_service = telegram_service
        self.sender_id = sender_id
        self.entry_price = None
        self.order_id = None

    async def start_monitoring(self, order_id):
        self.order_id = order_id

        # Get the position information
        current_position = await bybit_service.get_position_info(SYMBOL)
        qty = current_position['size']
        logging.info(f"Начало мониторинга позиции с ID: {self.order_id}")

        # Get the initial price by passing SYMBOL as argument
        latest_price_data = await self.bybit_service.get_latest_price(SYMBOL)  # Pass SYMBOL here
        if latest_price_data:
            self.entry_price = latest_price_data["latest_price"]
            logging.info(f"Начальная цена установлена: {self.entry_price} USD")
        else:
            await self.telegram_service.send_message("❌ Не удалось получить начальную цену для мониторинга.",
                                                     chat_id=self.sender_id)
            logging.error("Не удалось получить начальную цену для мониторинга.")
            return

        # Start monitoring the price
        while True:
            await asyncio.sleep(10)  # Pause between price checks

            # Get the latest price data again, passing SYMBOL
            latest_price_data = await self.bybit_service.get_latest_price(SYMBOL)  # Pass SYMBOL here
            if not latest_price_data:
                await self.telegram_service.send_message("⚠️ Не удалось получить текущую цену. Пропуск проверки.",
                                                         chat_id=self.sender_id)
                logging.warning("Не удалось получить текущую цену. Пропуск проверки.")
                continue

            current_price = latest_price_data["latest_price"]
            profit_percentage = ((current_price - self.entry_price) / self.entry_price) * 100

            # Log current price and profit percentage
            logging.info(f"Текущая цена: {current_price} USD, текущая прибыль: {profit_percentage:.2f}%")

            # Check if the target profit has been reached
            if profit_percentage >= TARGET_PROFIT:
                close_result = await bybit_service.close_position_market(SYMBOL, qty)
                logging.info(
                    f"Попытка закрытия позиции с ID: {order_id}, текущая цена: {current_price}, прибыль: {profit_percentage:.2f}%")
                if close_result:
                    logging.info("Отправка уведомления через Telegram о закрытии позиции...")
                    await self.telegram_service.send_message(
                        f"✅ Позиция закрыта с прибылью {profit_percentage:.2f}%. ID ордера: {self.order_id}"
                        , chat_id=self.sender_id
                    )
                    logging.info(f"Позиция с ID {self.order_id} закрыта с прибылью {profit_percentage:.2f}%.")
                else:
                    await self.telegram_service.send_message("❌ Не удалось закрыть позицию.", chat_id=self.sender_id)
                    logging.error(f"Не удалось закрыть позицию с ID {self.order_id}.")
                break
