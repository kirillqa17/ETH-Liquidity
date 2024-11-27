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
            if web3.eth.get_block('latest') != None:
                return web3
            else:
                raise ConnectionError("Подключение не удалось.")
        except Exception as e:
            attempts += 1
            current_rpc_index = (current_rpc_index + 1) % len(rpc_urls)
            print(f"Ошибка подключения: {e}. Переключение на следующий RPC ({rpc_urls[current_rpc_index]}).")
    raise ConnectionError("Не удалось подключиться ни к одному из RPC узлов.")

web3 = get_web3()

def get_contract(contract_address, abi_path):
    """
    Загружает контракт по адресу и ABI.

    :param contract_address: Адрес смарт-контракта.
    :param abi_path: Путь к файлу с ABI.
    :return: Экземпляр контракта.
    """
    with open(abi_path, 'r') as abi_file:
        abi = json.load(abi_file)
    contract = web3.eth.contract(address=web3.to_checksum_address(contract_address), abi=abi)
    return contract

def get_user_position(position_manager_address, abi_path, user_address):
    """
    Получает ID позиции пользователя на Uniswap V3.

    :param position_manager_address: Адрес контракта NonFungiblePositionManager.
    :param abi_path: Путь к файлу с ABI контракта.
    :param user_address: Адрес пользователя.
    :return: ID позиции (tokenId) или None, если позиций нет.
    """
    position_manager = get_contract(position_manager_address, abi_path)

    try:
        # Проверяем, есть ли хотя бы одна позиция
        balance = position_manager.functions.balanceOf(user_address).call()
        if balance > 0:
            return position_manager.functions.tokenOfOwnerByIndex(user_address, balance - 1).call()
        else:
            print(f"У пользователя {user_address} нет позиций.")
            return None
    except Exception as e:
        print(f"Ошибка при получении позиции пользователя: {e}")
        return None

def get_position_liquidity(position_manager_address, abi_path, position_id):
    """
    Получает объём ликвидности для позиции.

    :param position_manager_address: Адрес контракта NonFungiblePositionManager.
    :param abi_path: Путь к файлу с ABI контракта.
    :param position_id: ID позиции (tokenId).
    :return: Объём ликвидности для позиции.
    """
    position_manager = get_contract(position_manager_address, abi_path)

    try:
        position_data = position_manager.functions.positions(position_id).call()
        liquidity = position_data[7]  # Ликвидность находится на 7-м месте в структуре
        return liquidity
    except Exception as e:
        print(f"Ошибка при получении данных позиции: {e}")
        return 0
