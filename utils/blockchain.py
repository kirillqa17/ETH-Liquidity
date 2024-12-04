from web3 import Web3
import os, time
from utils.logger import setup_logger
import json
from utils.select_chain import load_config
from dotenv import load_dotenv
from utils.retry_decorator import retry_on_exception

load_dotenv()
config = load_config()
# Подключение к Ethereum
RPC_URL_1 = config["RPC_URL_1"]
RPC_URL_2 = config["RPC_URL_2"]
RPC_URL_3 = config["RPC_URL_3"]
RPC_RETRY_LIMIT = int(os.getenv("RPC_RETRY_LIMIT", 3))

GAS_LIMIT = os.getenv("GAS_LIMIT")
GAS_PRICE_MULTIPLIER = os.getenv("GAS_PRICE_MULTIPLIER", 1.1)
POSITION_MANAGER_ABI_PATH = os.getenv('POSITION_MANAGER_ABI_PATH', 'utils/position_manager_abi.json')
POSITION_MANAGER_ADDRESS = config['POSITION_MANAGER_ADDRESS']

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
            print(f"Ошибка подключения: {e}. Переключение на следующий RPC ({rpc_urls[current_rpc_index]}) через 10 секунд.")
            time.sleep(10)
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

@retry_on_exception()
def get_user_position(position_manager_address, abi_path, user_address):
    """
    Получает ID позиции пользователя на Uniswap V3.

    :param position_manager_address: Адрес контракта NonFungiblePositionManager.
    :param abi_path: Путь к файлу с ABI контракта.
    :param user_address: Адрес пользователя.
    :return: ID позиции (tokenId) или None, если позиций нет.
    """
    position_manager = get_contract(position_manager_address, abi_path)
    logger = setup_logger(user_address)
    try:
        # Проверяем, есть ли хотя бы одна позиция
        balance = position_manager.functions.balanceOf(user_address).call()
        if balance > 0:
            return position_manager.functions.tokenOfOwnerByIndex(user_address, balance - 1).call()
        else:
            print(f"У пользователя {user_address} нет позиций.")
            return None
    except Exception as e:
        logger.error(f"Ошибка при получении ликвидности для кошелька {user_address}: {e}")
        raise

@retry_on_exception()
def get_position_liquidity(position_manager_address, abi_path, position_id, wallet_address):
    """
    Получает объём ликвидности для позиции.

    :param position_manager_address: Адрес контракта NonFungiblePositionManager.
    :param abi_path: Путь к файлу с ABI контракта.
    :param position_id: ID позиции (tokenId).
    :param wallet_address: Адрес кошелька.
    :return: Объём ликвидности для позиции.
    """
    position_manager = get_contract(position_manager_address, abi_path)
    logger = setup_logger(wallet_address)
    try:
        position_data = position_manager.functions.positions(position_id).call()
        liquidity = position_data[7]  # Ликвидность находится на 7-м месте в структуре
        return liquidity
    except Exception as e:
        logger.error(f"Ошибка при получении ликвидности для кошелька {wallet_address}: {e}")
        raise

@retry_on_exception()
def check_allowance(wallet_address, position_manager_address, token_address, erc20_abi_path):
    """
    Получает информацию об allowance от erc20.

    :param wallet_address: Адрес кошелька.
    :param position_manager_address: Адрес Position Manager Address Uni V3.
    :param token_address: Адрес токена, для которого нужно allowance.
    :param erc20_abi_path: Путь с ABI ERC20.
    :return: Объем одобренных токенов для кошелька.
    """
    logger = setup_logger(wallet_address)

    erc20_contract = get_contract(token_address, erc20_abi_path)
    try:
        allowance = erc20_contract.functions.allowance(wallet_address, position_manager_address).call()
        return allowance
    except Exception as e:
        logger.error(f"Ошибка при проверки разрешений для кошелька {wallet_address}: {e}")
        raise

@retry_on_exception()
def approve_token(wallet_address, private_key, position_manager_address, token_address, erc20_abi_path):
    """
    Отправляет транзакцию approve для кошелька.

    :param wallet_address: Адрес кошелька.
    :param position_manager_address: Адрес Position Manager Address Uni V3.
    :param token_address: Адрес токена для approve.
    :param erc20_abi_path: Путь с ABI ERC20.
    :param private_key: Приватный ключ кошелька.
    :return: Хэш транзакции approve.
    """
    logger = setup_logger(wallet_address)
    try:
        amount_to_approve = 2 ** 256 -1
        erc20_contract = get_contract(token_address, erc20_abi_path)
        transaction = erc20_contract.functions.approve(
            Web3.to_checksum_address(position_manager_address),
            amount_to_approve
        ).build_transaction({
            'from': Web3.to_checksum_address(wallet_address),
            'nonce': web3.eth.get_transaction_count(wallet_address),
            'gas': GAS_LIMIT,
            'gasPrice': int(web3.eth.gas_price * GAS_PRICE_MULTIPLIER)
        })

        signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction).hex()
        return txn_hash
    except Exception as e:
        logger.error(f"Ошибка при подтверждении токенов для кошелька {wallet_address}: {e}")
        raise