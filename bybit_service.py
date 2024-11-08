import time
import hmac
import hashlib
import httpx
from config import BYBIT_API_KEY, BYBIT_API_SECRET, API_URL, ORDER_SIZE, ACCOUNTTYPE


def generate_signature(secret, params):
    param_str = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
    return hmac.new(secret.encode('utf-8'), param_str.encode('utf-8'), hashlib.sha256).hexdigest()


class BybitService:
    def __init__(self):
        # Initialize the asynchronous HTTP client
        self.client = httpx.AsyncClient()

    async def get_position_info(self, symbol):
        endpoint = '/v5/position/list'
        timestamp = int(time.time() * 1000)
        params = {
            'api_key': BYBIT_API_KEY,
            'timestamp': timestamp,
            'category': 'linear',
            'symbol': symbol
        }
        params['sign'] = generate_signature(BYBIT_API_SECRET, params)
        response = await self.client.get(API_URL + endpoint, params=params)

        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0 and 'list' in data['result']:
                return data['result']['list'][0]  # Assuming the first item is the relevant position info
            else:
                print(f"Failed to fetch position info: {data['retMsg']}")
        else:
            print(f"Failed to fetch position info: HTTP {response.status_code}")
        return None

    async def get_all_orders(self, symbol):
        endpoint = '/v5/order/history'
        timestamp = int(time.time() * 1000)
        params = {
            'api_key': BYBIT_API_KEY,
            'timestamp': timestamp,
            'category': 'linear',
            'symbol': symbol
        }
        params['sign'] = generate_signature(BYBIT_API_SECRET, params)
        response = await self.client.get(API_URL + endpoint, params=params)

        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0:
                return data['result']['list']  # Adjust based on the response structure
            else:
                print(f"Failed to fetch orders: {data['retMsg']}")
        else:
            print(f"Failed to fetch orders: HTTP {response.status_code}")
        return None

    async def get_balance(self):
        endpoint = '/v5/account/wallet-balance'
        params = {
            'api_key': BYBIT_API_KEY,
            'timestamp': int(time.time() * 1000),
            'accountType': ACCOUNTTYPE
        }
        params['sign'] = generate_signature(BYBIT_API_SECRET, params)
        response = await self.client.get(API_URL + endpoint, params=params)

        if response.status_code == 200:
            data = response.json()
            print("Response data:", data)
            if data['retCode'] == 0 and 'result' in data and 'list' in data['result']:
                account_data = data['result']['list'][0]
                total_available_balance = float(account_data.get('totalAvailableBalance', 0))
                print(total_available_balance)
                return total_available_balance
            else:
                print("No 'list' key or balance data found in the response.")
        else:
            print(response.text)
            print(f"Failed to fetch balance: HTTP {response.status_code}")
        return None

    async def get_latest_price(self, symbol):
        endpoint = '/v5/market/tickers'
        params = {'category': 'linear', 'symbol': symbol}
        response = await self.client.get(API_URL + endpoint, params=params)

        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0:
                price_data = data['result']['list'][0]
                return {
                    "latest_price": float(price_data['lastPrice']),
                    "high_price_24h": float(price_data['highPrice24h']),
                    "low_price_24h": float(price_data['lowPrice24h']),
                    "volume_24h": float(price_data['volume24h'])
                }
            else:
                print(f"Error fetching price: {data['retMsg']}")
        else:
            print(f"Failed to fetch price: HTTP {response.status_code}")
        return None

    async def calculate_min_order_size(self, price, preset_min_size=0.001, min_notional=100):
        return max(preset_min_size, min_notional / price)

    async def open_position(self, symbol):
        # Fetch the latest price for the given symbol
        data = await self.get_latest_price(symbol)
        if data is None:
            print("Could not retrieve the latest price.")
            return None

        latest_price = data["latest_price"]

        # Calculate the minimum order size
        min_order_size = await self.calculate_min_order_size(latest_price)

        # Set the order size to at least the minimum required size
        order_size = max(ORDER_SIZE, min_order_size)
        order_size = round(order_size, 3)  # Round for precision

        # Place the market order
        endpoint = '/v5/order/create'
        timestamp = int(time.time() * 1000)
        params = {
            'api_key': BYBIT_API_KEY,
            'timestamp': timestamp,
            'category': 'linear',
            'symbol': symbol,
            'side': 'Buy',
            'orderType': 'Market',
            'qty': str(order_size),
            'timeInForce': 'GTC',
        }
        params['sign'] = generate_signature(BYBIT_API_SECRET, params)
        response = await self.client.post(API_URL + endpoint, json=params)

        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0:
                print(f"Position opened successfully with Order ID: {data['result']['orderId']}")
                return data['result']['orderId']
            else:
                print(f"Failed to open position: {data['retMsg']}")
        else:
            print(f"Failed to open position: HTTP {response.status_code}")
        return None

    async def close_position_market(self, symbol, qty):
        endpoint = '/v5/order/create'
        timestamp = int(time.time() * 1000)
        params = {
            'api_key': BYBIT_API_KEY,
            'timestamp': timestamp,
            'category': 'linear',
            'symbol': symbol,
            'side': 'Sell',
            'orderType': 'Market',
            'qty': str(qty),
            'timeInForce': 'GTC',
        }
        params['sign'] = generate_signature(BYBIT_API_SECRET, params)
        response = await self.client.post(API_URL + endpoint, json=params)

        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0:
                print("Position closed successfully.")
                return True
            else:
                print(f"Failed to close position: {data['retMsg']}")
        else:
            print(f"Failed to close position: HTTP {response.status_code}")
        return False

    async def close(self):
        await self.client.aclose()
