from web3 import Web3
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Подключение к Ethereum
RPC_URL_1 = os.getenv("RPC_URL_1")
RPC_URL_2 = os.getenv("RPC_URL_2")
RPC_URL_3 = os.getenv("RPC_URL_3")
RPC_RETRY_LIMIT = int(os.getenv("RPC_RETRY_LIMIT", 3))

rpc_urls = [RPC_URL_1, RPC_URL_2, RPC_URL_3]
current_rpc_index = 0

# Функция для переключения RPC
def get_web3():
    """Возвращает объект Web3 для взаимодействия с блокчейном."""
    global current_rpc_index
    attempts = 0
    while attempts < RPC_RETRY_LIMIT:
        try:
            web3 = Web3(Web3.HTTPProvider(rpc_urls[current_rpc_index]))
            if web3.isConnected():
                return web3
            else:
                raise ConnectionError("Подключение не удалось.")
        except Exception as e:
            attempts += 1
            current_rpc_index = (current_rpc_index + 1) % len(rpc_urls)
            print(f"Ошибка подключения: {e}. Переключение на следующий RPC ({rpc_urls[current_rpc_index]}).")
    raise ConnectionError("Не удалось подключиться ни к одному из RPC узлов.")

# Глобальный объект Web3
web3 = get_web3()

def get_wallet_info_from_file(file_path=None):
    """Загружает кошельки и их приватные ключи из файла, путь к которому передается в file_path."""
    wallets = []
    if file_path is None:
        file_path = os.getenv("WALLETS_FILE", "wallets.txt")  # Используем путь из переменной окружения или дефолтный
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    address, private_key = line.split(',')
                    wallets.append((address, private_key))
    except Exception as e:
        print(f"Ошибка при загрузке кошельков из файла: {e}")
    return wallets

def get_contract(contract_address, abi_path):
    """
    Загружает контракт по адресу и ABI.

    :param contract_address: Адрес смарт-контракта.
    :param abi_path: Путь к файлу с ABI.
    :return: Экземпляр контракта.
    """
    with open(abi_path, 'r') as abi_file:
        abi = json.load(abi_file)
    contract = web3.eth.contract(address=web3.toChecksumAddress(contract_address), abi=abi)
    return contract

def send_transaction(function, wallet_address, private_key, gas_limit, gas_price_multiplier=1.1):
    """
    Отправляет транзакцию в блокчейн.

    :param function: Вызов функции контракта.
    :param wallet_address: Адрес кошелька.
    :param private_key: Приватный ключ кошелька.
    :param gas_limit: Лимит газа.
    :param gas_price_multiplier: Множитель цены газа.
    :return: Хеш транзакции.
    """
    # Создание транзакции
    transaction = function.buildTransaction({
        'chainId': web3.eth.chain_id,
        'gas': gas_limit,
        'gasPrice': int(web3.eth.gas_price * gas_price_multiplier),
        'nonce': web3.eth.getTransactionCount(wallet_address),
    })

    # Подписание транзакции
    signed_tx = web3.eth.account.sign_transaction(transaction, private_key=private_key)

    # Отправка транзакции
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    return web3.toHex(tx_hash)
