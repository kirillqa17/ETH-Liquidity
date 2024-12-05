from utils.logger import setup_logger
from utils.blockchain import get_contract, get_position_liquidity
from utils.pricing import get_eth_price
from utils.unimath import eth_to_usdc, get_ticks_for_range, tick_to_price
from utils.retry_decorator import retry_on_exception

import os, time
from web3 import Web3
from dotenv import load_dotenv
from utils.select_chain import load_config
config = load_config()
load_dotenv()

# Загрузка ABI и адреса контракта из .env
POSITION_MANAGER_ABI_PATH = os.getenv('POSITION_MANAGER_ABI_PATH', 'utils/position_manager_abi.json')
POSITION_MANAGER_ADDRESS = config[
    'POSITION_MANAGER_ADDRESS']  # Адрес контракта Uniswap V3 Non-Fungible Position Manager
TOKEN0 = config['TOKEN0']
TOKEN1 = config['TOKEN1']

AMOUNT0 = float(os.getenv('AMOUNT0'))

GAS_PRICE_MULTIPLIER = float(os.getenv('GAS_PRICE_MULTIPLIER', 1.2))


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
    new_lower = int(center - range_width / 2)
    new_upper = int(center + range_width / 2)
    logger.info(f"Новый диапазон ликвидности: {new_lower} - {new_upper}")
    return new_lower, new_upper

@retry_on_exception()
def collect_fees(web3, wallet_address, private_key, token_id):
    """
        Собирает комиссии из текущей позиции.
        :param web3: Экземпляр Web3 для взаимодействия с блокчейном.
        :param wallet_address: Адрес кошелька.
        :param private_key: Приватный ключ кошелька.
        :param token_id: ID позиции NFT на Uniswap.
        """
    logger = setup_logger(wallet_address)
    try:
        # Получаем контракт
        position_manager = get_contract(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH)
        logger.info(f"Сбор комиссий для позиции с ID {token_id} начато.")
        # Подготовка транзакции для вызова функции collect
        params = {
            "tokenId": token_id,
            "recipient": wallet_address,
            "amount0Max": 2 ** 128 - 1,
            "amount1Max": 2 ** 128 - 1
        }
        gas_estimate = int(position_manager.functions.collect(params).estimate_gas({
            "from": wallet_address
        }) * GAS_PRICE_MULTIPLIER)
        collect_txn = position_manager.functions.collect(params).build_transaction({
            "from": wallet_address,
            "gasPrice": web3.eth.gas_price,
            "gas": gas_estimate,
            "nonce": web3.eth.get_transaction_count(wallet_address)
        })
        # Подписание транзакции collect
        signed_collect_txn = web3.eth.account.sign_transaction(collect_txn, private_key)
        # Отправка транзакции collect
        collect_txn_hash = web3.eth.send_raw_transaction(signed_collect_txn.raw_transaction).hex()
        logger.info(f"Комиссии успешно собраны для кошелька {wallet_address}. Хеш транзакции: {collect_txn_hash}")
        return 1
    except Exception as e:
        logger.error(f"Ошибка при сборе комиссий для кошелька {wallet_address}: {e}")
        raise

@retry_on_exception()
def remove_liquidity(web3, wallet_address, private_key, token_id):
    """
    Удаляет ликвидность из текущей позиции.
    :param web3: Экземпляр Web3 для взаимодействия с блокчейном.
    :param wallet_address: Адрес кошелька.
    :param private_key: Приватный ключ кошелька.
    :param token_id: ID позиции NFT на Uniswap.
    """
    logger = setup_logger(wallet_address)
    try:
        logger.info(f"Удаление ликвидности для позиции с ID {token_id} начато.")
        liquidity = get_position_liquidity(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH, token_id, wallet_address)
        position_manager = get_contract(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH)
        # Подготовка транзакции для decreaseLiquidity
        params = {
            "tokenId": token_id,
            "liquidity": liquidity,
            "amount0Min": 0,
            "amount1Min": 0,
            "deadline": web3.eth.get_block('latest')['timestamp'] + 60
        }
        gas_estimate = int(position_manager.functions.decreaseLiquidity(params).estimate_gas({
            "from": wallet_address
        }) * GAS_PRICE_MULTIPLIER)
        decrease_liquidity_txn = position_manager.functions.decreaseLiquidity(params).build_transaction({
            "from": wallet_address,
            "gasPrice": web3.eth.gas_price,
            "gas": gas_estimate,
            "nonce": web3.eth.get_transaction_count(wallet_address) + 1
        })

        # Подписание транзакции decreaseLiquidity
        signed_decrease_liquidity_txn = web3.eth.account.sign_transaction(decrease_liquidity_txn, private_key)
        # Отправка транзакции decreaseLiquidity
        decrease_liquidity_txn_hash = web3.eth.send_raw_transaction(signed_decrease_liquidity_txn.raw_transaction).hex()
        logger.info(
            f"Ликвидность успешно удалена для кошелька {wallet_address}. Хеш транзакции: {decrease_liquidity_txn_hash}")

        return 1
    except Exception as e:
        logger.error(f"Ошибка при удалении ликвидности для кошелька {wallet_address}: {e}")
        raise

@retry_on_exception()
def add_liquidity(web3, wallet_address, private_key, new_range_lower, new_range_upper, amount0=None):
    """
    Добавляет ликвидность в новый диапазон.
    :param web3: Экземпляр Web3 для взаимодействия с блокчейном.
    :param wallet_address: Адрес кошелька.
    :param private_key: Приватный ключ кошелька.
    :param new_range_lower: Новая нижняя граница диапазона.
    :param new_range_upper: Новая верхняя граница диапазона.
    :param amount0: Количество первого токена для добавления.
    """
    token0 = TOKEN0  # WETH
    token1 = TOKEN1  # USDC

    logger = setup_logger(wallet_address)
    logger.info(f"Добавление ликвидности в диапазон {new_range_lower} - {new_range_upper} начато.")

    tick_lower, tick_upper = get_ticks_for_range(new_range_lower, new_range_upper)
    price_ticked_lower, price_ticked_upper = tick_to_price(tick_lower), tick_to_price(tick_upper)

    try:
        # Если amount0 не передано, вычисляем их динамически
        if amount0 is None:
            amount0 = AMOUNT0
            amount1 = eth_to_usdc(price_ticked_lower, price_ticked_upper, get_eth_price(), amount0)
            logger.info(f"Вычислены значения для кошелька {wallet_address}: amount0 = {amount0}, amount1 = {amount1}")
        else:
            amount1 = eth_to_usdc(price_ticked_lower, price_ticked_upper, get_eth_price(), amount0)
            logger.info(
                f"Используются переданные значения для кошелька {wallet_address}: amount0 = {amount0}, amount1 = {amount1}")

        # Получаем контракт
        position_manager = get_contract(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH)

        params = (
            Web3.to_checksum_address(token0),
            Web3.to_checksum_address(token1),
            3000,
            tick_lower,
            tick_upper,
            Web3.to_wei(amount0, 'ether'),
            int(amount1 * (10 ** 6)),
            0,
            0,
            Web3.to_checksum_address(wallet_address),
            int(time.time()) + 60
        )

        add_liquidity_txn = position_manager.functions.mint(params).build_transaction({
            "from": wallet_address,
            "value": Web3.to_wei(amount0, 'ether'),
            "gasPrice": int(web3.eth.gas_price * GAS_PRICE_MULTIPLIER),
            "nonce": web3.eth.get_transaction_count(wallet_address),
            "gas": 1000000
        })

        signed_tx = web3.eth.account.sign_transaction(add_liquidity_txn, private_key=private_key)

        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()

        logger.info(f"Ликвидность успешно добавлена для кошелька {wallet_address}. Хэш транзакции: {tx_hash}")
    except Exception as e:
        logger.error(f"Ошибка при добавлении ликвидности для кошелька {wallet_address}: {e}")
        raise