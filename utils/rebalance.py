from logger import setup_logger
from web3 import Web3
from utils.blockchain import get_web3, get_contract, send_transaction
import os
from dotenv import load_dotenv

load_dotenv()

logger = setup_logger()

# Загрузка ABI и адреса контракта из .env
POSITION_MANAGER_ABI_PATH = os.path.join('POSITION_MANAGER_ABI_PATH', 'utils/position_manager_abi.json')
POSITION_MANAGER_ADDRESS = os.getenv('POSITION_MANAGER_ADDRESS', '0xC36442b4a4522E871399CD717aBDD847Ab11FE88')  # Адрес контракта Uniswap V3 Non-Fungible Position Manager

GAS_LIMIT = int(os.getenv('GAS_LIMIT', 300000))
GAS_PRICE_MULTIPLIER = float(os.getenv('GAS_PRICE_MULTIPLIER', 1.1))

def should_rebalance(current_price, range_lower, range_upper, threshold_percent):
    """
    Проверяет, нужно ли выполнять ребалансировку.
    :param current_price: Текущая цена ETH.
    :param range_lower: Нижняя граница текущего диапазона.
    :param range_upper: Верхняя граница текущего диапазона.
    :param threshold_percent: Порог в процентах для ребалансировки.
    :return: True, если нужно ребалансировать, иначе False.
    """
    threshold_distance = (range_upper - range_lower) * threshold_percent
    if current_price > range_upper - threshold_distance:
        logger.warning("Цена приближается к верхней границе диапазона.")
        return True
    elif current_price < range_lower + threshold_distance:
        logger.warning("Цена приближается к нижней границе диапазона.")
        return True
    return False

def calculate_new_range(current_price, range_width):
    """
    Рассчитывает новый диапазон ликвидности, центрированный вокруг текущей цены.
    :param current_price: Текущая цена ETH.
    :param range_width: Ширина нового диапазона.
    :return: Кортеж (новая нижняя граница, новая верхняя граница).
    """
    center = current_price
    new_lower = center - range_width / 2
    new_upper = center + range_width / 2
    logger.info(f"Новый диапазон ликвидности: {new_lower} - {new_upper}")
    return new_lower, new_upper


def remove_liquidity(web3, wallet_address, private_key, token_id):
    """
    Удаляет ликвидность из текущей позиции.
    :param web3: Экземпляр Web3 для взаимодействия с блокчейном.
    :param wallet_address: Адрес кошелька.
    :param private_key: Приватный ключ кошелька.
    :param token_id: ID позиции NFT на Uniswap.
    """
    logger.info(f"Удаление ликвидности для позиции с ID {token_id} начато.")
    try:
        # Получаем контракт
        position_manager = get_contract(web3, POSITION_MANAGER_ABI_PATH, POSITION_MANAGER_ADDRESS)

        # Подготовка транзакции для вызова функции collectAllFees (забрать комиссии перед удалением)
        collect_txn = position_manager.functions.collect({
            "tokenId": token_id,
            "recipient": wallet_address,
            "amount0Max": 2 ** 128 - 1,  # Максимальное значение для токенов
            "amount1Max": 2 ** 128 - 1
        }).buildTransaction({
            "from": wallet_address,
            "gas": GAS_LIMIT,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.getTransactionCount(wallet_address)
        })

        # Отправляем транзакцию
        send_transaction(web3, collect_txn, private_key)
        logger.info("Комиссии успешно собраны.")

        # Подготовка транзакции для удаления ликвидности
        decrease_liquidity_txn = position_manager.functions.decreaseLiquidity({
            "tokenId": token_id,
            "liquidity": 100000,  # Указать объем ликвидности для удаления
            "amount0Min": 0,  # Минимальное количество токенов A
            "amount1Min": 0,  # Минимальное количество токенов B
            "deadline": web3.eth.get_block('latest')['timestamp'] + 60  # Тайм-аут 1 минута
        }).buildTransaction({
            "from": wallet_address,
            "gas": GAS_LIMIT,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.getTransactionCount(wallet_address) + 1
        })

        # Отправляем транзакцию
        send_transaction(web3, decrease_liquidity_txn, private_key)
        logger.info("Ликвидность успешно удалена.")
    except Exception as e:
        logger.error(f"Ошибка при удалении ликвидности: {e}")


def add_liquidity(web3, wallet_address, private_key, new_range_lower, new_range_upper, token0, token1, amount0,
                  amount1):
    """
    Добавляет ликвидность в новый диапазон.
    :param web3: Экземпляр Web3 для взаимодействия с блокчейном.
    :param wallet_address: Адрес кошелька.
    :param private_key: Приватный ключ кошелька.
    :param new_range_lower: Новая нижняя граница диапазона.
    :param new_range_upper: Новая верхняя граница диапазона.
    :param token0: Адрес первого токена.
    :param token1: Адрес второго токена.
    :param amount0: Количество первого токена для добавления.
    :param amount1: Количество второго токена для добавления.
    """
    logger.info(f"Добавление ликвидности в диапазон {new_range_lower} - {new_range_upper} начато.")
    try:
        # Получаем контракт
        position_manager = get_contract(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH)

        # Подготовка транзакции для добавления ликвидности
        add_liquidity_txn = position_manager.functions.mint({
            "token0": token0,
            "token1": token1,
            "fee": 3000,  # Указать сборы (например, 0.3%)
            "tickLower": new_range_lower,
            "tickUpper": new_range_upper,
            "amount0Desired": amount0,
            "amount1Desired": amount1,
            "amount0Min": 0,  # Минимальное количество токенов A
            "amount1Min": 0,  # Минимальное количество токенов B
            "recipient": wallet_address,
            "deadline": web3.eth.get_block('latest')['timestamp'] + 60  # Тайм-аут 1 минута
        }).buildTransaction({
            "from": wallet_address,
            "gas": GAS_LIMIT,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.getTransactionCount(wallet_address)
        })

        # Отправляем транзакцию
        send_transaction(web3, add_liquidity_txn, private_key)
        logger.info("Ликвидность успешно добавлена.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении ликвидности: {e}")
