from logger import setup_logger
from web3 import Web3
from utils.blockchain import get_web3, get_contract, send_transaction, get_position_liquidity
import os
from dotenv import load_dotenv

load_dotenv()

# Загрузка ABI и адреса контракта из .env
POSITION_MANAGER_ABI_PATH = os.path.join('POSITION_MANAGER_ABI_PATH', 'utils/position_manager_abi.json')
POSITION_MANAGER_ADDRESS = os.getenv('POSITION_MANAGER_ADDRESS', '0xC36442b4a4522E871399CD717aBDD847Ab11FE88')  # Адрес контракта Uniswap V3 Non-Fungible Position Manager

GAS_LIMIT = int(os.getenv('GAS_LIMIT', 300000))
GAS_PRICE_MULTIPLIER = float(os.getenv('GAS_PRICE_MULTIPLIER', 1.1))

def should_rebalance(current_price, range_lower, range_upper, threshold_percent, wallet_address):
    """
    Проверяет, нужно ли выполнять ребалансировку.
    :param current_price: Текущая цена ETH.
    :param range_lower: Нижняя граница текущего диапазона.
    :param range_upper: Верхняя граница текущего диапазона.
    :param threshold_percent: Порог в процентах для ребалансировки.
    :param wallet_address: Адрес текущего кошелька для логгера.
    :return: True, если нужно ребалансировать, иначе False.
    """
    logger = setup_logger(wallet_address)
    threshold_distance = (range_upper - range_lower) * threshold_percent
    if current_price > range_upper - threshold_distance:
        logger.warning("Цена приближается к верхней границе диапазона.")
        return True
    elif current_price < range_lower + threshold_distance:
        logger.warning("Цена приближается к нижней границе диапазона.")
        return True
    return False

def calculate_new_range(current_price, range_width, wallet_address):
    """
    Рассчитывает новый диапазон ликвидности, центрированный вокруг текущей цены.
    :param current_price: Текущая цена ETH.
    :param range_width: Ширина нового диапазона.
    :param wallet_address: Адрес текущего кошелька для логгера.
    :return: Кортеж (новая нижняя граница, новая верхняя граница).
    """
    logger = setup_logger(wallet_address)
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
    logger = setup_logger(wallet_address)
    logger.info(f"Удаление ликвидности для позиции с ID {token_id} начато.")
    try:
        # Получаем контракт
        position_manager = get_contract(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH)

        # Подготовка транзакции для вызова функции collect
        collect_txn = position_manager.functions.collect({
            "tokenId": token_id,
            "recipient": wallet_address,
            "amount0Max": 2 ** 128 - 1,
            "amount1Max": 2 ** 128 - 1
        }).buildTransaction({
            "from": wallet_address,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.getTransactionCount(wallet_address)
        })

        # Оценка газа для collect
        estimated_gas = web3.eth.estimate_gas(collect_txn)
        collect_txn['gas'] = int(estimated_gas * 1.2)  # Добавляем запас 20%

        # Отправляем транзакцию collect
        send_transaction(web3, collect_txn, private_key, GAS_PRICE_MULTIPLIER)
        logger.info("Комиссии успешно собраны.")

        # Подготовка транзакции для decreaseLiquidity
        liquidity = get_position_liquidity(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH, token_id)
        decrease_liquidity_txn = position_manager.functions.decreaseLiquidity({
            "tokenId": token_id,
            "liquidity": liquidity,
            "amount0Min": 0,
            "amount1Min": 0,
            "deadline": web3.eth.get_block('latest')['timestamp'] + 60
        }).buildTransaction({
            "from": wallet_address,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.getTransactionCount(wallet_address) + 1
        })

        # Оценка газа для decreaseLiquidity
        estimated_gas = web3.eth.estimate_gas(decrease_liquidity_txn)
        decrease_liquidity_txn['gas'] = int(estimated_gas * 1.2)  # Добавляем запас 20%

        # Отправляем транзакцию decreaseLiquidity
        send_transaction(web3, decrease_liquidity_txn, private_key, GAS_PRICE_MULTIPLIER)
        logger.info("Ликвидность успешно удалена.")
    except Exception as e:
        logger.error(f"Ошибка при удалении ликвидности: {e}")



def add_liquidity(web3, wallet_address, private_key, new_range_lower, new_range_upper, amount0, amount1):
    """
    Добавляет ликвидность в новый диапазон.
    :param web3: Экземпляр Web3 для взаимодействия с блокчейном.
    :param wallet_address: Адрес кошелька.
    :param private_key: Приватный ключ кошелька.
    :param new_range_lower: Новая нижняя граница диапазона.
    :param new_range_upper: Новая верхняя граница диапазона.
    :param amount0: Количество первого токена для добавления.
    :param amount1: Количество второго токена для добавления.
    """
    token0 = '0xC02aaa39b223FE8D0A0e5C4F27eAD9083C756Cc2'  # WETH
    token1 = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'  # USDC
    logger = setup_logger(wallet_address)
    logger.info(f"Добавление ликвидности в диапазон {new_range_lower} - {new_range_upper} начато.")
    try:
        # Получаем контракт
        position_manager = get_contract(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH)

        # Подготовка транзакции для mint
        add_liquidity_txn = position_manager.functions.mint({
            "token0": token0,
            "token1": token1,
            "fee": 3000,  # Сборы 0.3%
            "tickLower": new_range_lower,
            "tickUpper": new_range_upper,
            "amount0Desired": amount0,
            "amount1Desired": amount1,
            "amount0Min": 0,
            "amount1Min": 0,
            "recipient": wallet_address,
            "deadline": web3.eth.get_block('latest')['timestamp'] + 60
        }).buildTransaction({
            "from": wallet_address,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.getTransactionCount(wallet_address)
        })

        # Оценка газа для mint
        estimated_gas = web3.eth.estimate_gas(add_liquidity_txn)
        add_liquidity_txn['gas'] = int(estimated_gas * 1.2)  # Добавляем запас 20%

        # Отправляем транзакцию mint
        send_transaction(web3, add_liquidity_txn, private_key, GAS_PRICE_MULTIPLIER)
        logger.info("Ликвидность успешно добавлена.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении ликвидности: {e}")