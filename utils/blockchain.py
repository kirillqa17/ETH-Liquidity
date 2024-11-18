from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

# Подключение к Ethereum
INFURA_URL = os.getenv("INFURA_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

web3 = Web3(Web3.HTTPProvider(INFURA_URL))

if not web3.isConnected():
    raise ConnectionError("Не удалось подключиться к Ethereum узлу.")

def get_web3():
    """Возвращает объект Web3 для взаимодействия с блокчейном."""
    return web3

def get_wallet_info():
    """Возвращает кошелек и приватный ключ."""
    return web3.toChecksumAddress(WALLET_ADDRESS), PRIVATE_KEY
