from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

def connect_to_blockchain():
    infura_url = os.getenv("INFURA_URL")
    web3 = Web3(Web3.HTTPProvider(infura_url))
    if web3.isConnected():
        return web3
    else:
        raise Exception("Не удалось подключиться к Ethereum узлу")
