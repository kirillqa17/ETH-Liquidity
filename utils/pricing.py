from web3 import Web3
from blockchain import get_web3

# Chainlink Price Feed ETH/USD
CHAINLINK_PRICE_FEED = "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"
CHAINLINK_ABI = [
    {
        "inputs": [],
        "name": "latestAnswer",
        "outputs": [{"internalType": "int256", "name": "", "type": "int256"}],
        "stateMutability": "view",
        "type": "function",
    }
]

web3 = get_web3()
price_feed = web3.eth.contract(address=CHAINLINK_PRICE_FEED, abi=CHAINLINK_ABI)

def get_eth_price():
    """Получает текущую цену ETH через Chainlink."""
    try:
        price = price_feed.functions.latestAnswer().call() / 1e8  # Цена с 8 знаками
        return price
    except Exception as e:
        raise RuntimeError(f"Ошибка при получении цены ETH: {e}")
