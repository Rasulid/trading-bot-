import os

from dotenv import load_dotenv

load_dotenv()


TARGET_PROFIT = float(
    os.getenv("TARGET_PROFIT", 0.001))

SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
ORDER_SIZE = 0.0001
ACCOUNTTYPE = os.getenv('ACCOUNTTYPE')

BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

API_URL = os.getenv('API_URL')