import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import TELEGRAM_TOKEN, SYMBOL
from bybit_service import BybitService
from telegram_service import TelegramService
from trading_bot import TradingBot

# Initialize bot, dispatcher, and services
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
telegram_service = TelegramService()
bybit_service = BybitService()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Main menu keyboard
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Показать текущий баланс")],
        [KeyboardButton(text="Выбрать валютную пару и показать цену")],
        [KeyboardButton(text="История ордеров")],
        [KeyboardButton(text="Разместить ордер")]
    ],
    resize_keyboard=True
)

# Currency pairs keyboard
currency_pairs_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="BTC/USDT")],
        [KeyboardButton(text="ETH/USDT")],
        [KeyboardButton(text="XRP/USDT")],
        [KeyboardButton(text="Назад в меню")]
    ],
    resize_keyboard=True
)


@dp.message(Command("start"))
async def start_command(message: types.Message):
    sender_id = message.from_user.id
    await telegram_service.send_message("Привет! Добро пожаловать в бота!", chat_id=sender_id)
    await message.answer("Привет! Вот что я могу:", reply_markup=main_menu)


@dp.message()
async def handle_menu_selection(message: types.Message):
    if message.text == "Показать текущий баланс":
        await get_balance_command(message)
    elif message.text == "Выбрать валютную пару и показать цену":  # Ensure this matches the button text
        await message.answer("Выберите валютную пару:", reply_markup=currency_pairs_menu)
    elif message.text == "История ордеров":
        await get_orders_history_command(message)
    elif message.text == "Разместить ордер":
        # Ask user to select a currency pair for the order
        await message.answer("Выберите валютную пару для размещения ордера:", reply_markup=currency_pairs_menu)
    elif message.text == "Назад в меню":
        await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu)
    elif message.text in ["BTC/USDT", "ETH/USDT", "XRP/USDT"]:  # Check for exact matches to predefined pairs
        await place_order_command(message, message.text)
    else:
        await message.answer("Пожалуйста, выберите доступный вариант из меню.", reply_markup=main_menu)


# Modify place_order_command to accept the selected symbol
async def place_order_command(message: types.Message, symbol: str):
    sender_id = message.from_user.id
    symbol = symbol.replace("/", "")  # Convert BTC/USDT to BTCUSDT

    # Now place the order using the selected currency pair symbol
    order_id = await bybit_service.open_position(symbol=symbol)  # Pass the selected symbol dynamically

    if order_id:
        await message.answer(f"Ордер успешно размещен для {symbol}. ID ордера: {order_id}")
        logging.info(f"Ордер размещен успешно для {symbol}. ID ордера: {order_id}")
        trading_bot = TradingBot(bybit_service, telegram_service, sender_id=sender_id)
        asyncio.create_task(trading_bot.start_monitoring(order_id))
    else:
        await message.answer("Не удалось разместить ордер. Убедитесь, что у вас есть средства на счете.")
        logging.error("Не удалось разместить ордер. Проверьте средства на счете.")


async def get_balance_command(message: types.Message):
    balance = await bybit_service.get_balance()
    if balance is None:
        await message.answer("API key is invalid")
    else:
        await message.answer(f"Ваш текущий баланс: {balance:.2f} USDT")


async def get_orders_history_command(message: types.Message):
    history = await bybit_service.get_all_orders(SYMBOL)
    if history:
        for order in history:
            order_text = (
                f"📝 **Order Details**:\n"
                f"🔹 **Order ID**: {order['orderId']}\n"
                f"🔹 **Symbol**: {order['symbol']}\n"
                f"🔹 **Order Type**: {order['orderType']}\n"
                f"🔹 **Side**: {order['side']}\n"
                f"🔹 **Quantity**: {order['qty']}\n"
                f"🔹 **Average Price**: {order['avgPrice']} USD\n"
                f"🔹 **Price**: {order['price']} USD\n"
                f"🔹 **Order Status**: {order['orderStatus']}\n"
                f"🔹 **Time in Force**: {order['timeInForce']}\n"
                f"🔹 **Cumulative Executed Quantity**: {order['cumExecQty']}\n"
                f"🔹 **Cumulative Executed Value**: {order['cumExecValue']} USD\n"
                f"🔹 **Cumulative Execution Fee**: {order['cumExecFee']} USD\n"
                f"🔹 **Creation Time**: {order['createdTime']}\n"
                f"🔹 **Last Price on Creation**: {order['lastPriceOnCreated']} USD\n"
                f"🔹 **Updated Time**: {order['updatedTime']}\n"
            )
            await message.answer(order_text, parse_mode='Markdown')
    else:
        await message.answer("❌ No orders found.")


async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await bybit_service.close()


if __name__ == "__main__":
    asyncio.run(main())
