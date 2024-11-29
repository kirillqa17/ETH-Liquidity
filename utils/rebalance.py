from utils.logger import setup_logger
from utils.blockchain import get_contract, get_position_liquidity
from utils.pricing import get_eth_price
from utils.unimath import eth_to_usdc, price_to_tick, tick_to_price
import os,time
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Загрузка ABI и адреса контракта из .env
POSITION_MANAGER_ABI_PATH = os.getenv('POSITION_MANAGER_ABI_PATH', 'utils/position_manager_abi.json')
POSITION_MANAGER_ADDRESS = os.getenv('POSITION_MANAGER_ADDRESS', '0xC36442b4a4522E871399CD717aBDD847Ab11FE88')  # Адрес контракта Uniswap V3 Non-Fungible Position Manager
TOKEN0 = os.getenv('TOKEN0', '0xC02aaa39b223FE8D0A0e5C4F27eAD9083C756Cc2')
TOKEN1 = os.getenv('TOKEN1', '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')

AMOUNT0 = float(os.getenv('AMOUNT0'))
AMOUNT1 = float(os.getenv('AMOUNT1'))

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
    new_lower = int(center - range_width / 2)
    new_upper = int(center + range_width / 2)
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
    try:

        # Получаем контракт
        position_manager = get_contract(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH)
        logger.info(f"Удаление ликвидности для позиции с ID {token_id} начато.")

        # Подготовка транзакции для вызова функции collect
        collect_txn = position_manager.functions.collect({
            "tokenId": token_id,
            "recipient": wallet_address,
            "amount0Max": 2 ** 128 - 1,
            "amount1Max": 2 ** 128 - 1
        }).build_transaction({
            "from": wallet_address,
            "gasPrice": int(web3.eth.gas_price),
            "nonce": web3.eth.get_transaction_count(wallet_address)
        })

        # Оценка газа для collect
        estimated_gas = web3.eth.estimate_gas(collect_txn)
        collect_txn['gas'] = int(estimated_gas * 1.2)  # Добавляем запас 20%

        # Подписание транзакции collect
        signed_collect_txn = web3.eth.account.sign_transaction(collect_txn, private_key)
        # Отправка транзакции collect
        collect_txn_hash = web3.eth.send_raw_transaction(signed_collect_txn.raw_transaction)
        logger.info(f"Комиссии успешно собраны. Хеш транзакции: {collect_txn_hash.hex()}")

        # Подготовка транзакции для decreaseLiquidity
        liquidity = get_position_liquidity(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH, token_id)
        decrease_liquidity_txn = position_manager.functions.decreaseLiquidity({
            "tokenId": token_id,
            "liquidity": liquidity,
            "amount0Min": 0,
            "amount1Min": 0,
            "deadline": web3.eth.get_block('latest')['timestamp'] + 60
        }).build_transaction({
            "from": wallet_address,
            "gasPrice": int(web3.eth.gas_price),
            "nonce": web3.eth.get_transaction_count(wallet_address) + 1
        })

        # Оценка газа для decreaseLiquidity
        estimated_gas = web3.eth.estimate_gas(decrease_liquidity_txn)
        decrease_liquidity_txn['gas'] = int(estimated_gas * 1.2)  # Добавляем запас 20%

        # Подписание транзакции decreaseLiquidity
        signed_decrease_liquidity_txn = web3.eth.account.sign_transaction(decrease_liquidity_txn, private_key)
        # Отправка транзакции decreaseLiquidity
        decrease_liquidity_txn_hash = web3.eth.send_raw_transaction(signed_decrease_liquidity_txn.raw_transaction)
        logger.info(f"Ликвидность успешно удалена для кошелька {wallet_address}. Хеш транзакции: {decrease_liquidity_txn_hash.hex()}")

        return 1
    except Exception as e:
        logger.error(f"Ошибка при удалении ликвидности для кошелька {wallet_address}: {e}")



def add_liquidity(web3, wallet_address, private_key, new_range_lower, new_range_upper, token_id, amount0=None,
                  amount1=None):
    """
    Добавляет ликвидность в новый диапазон.
    :param web3: Экземпляр Web3 для взаимодействия с блокчейном.
    :param wallet_address: Адрес кошелька.
    :param private_key: Приватный ключ кошелька.
    :param new_range_lower: Новая нижняя граница диапазона.
    :param new_range_upper: Новая верхняя граница диапазона.
    :param amount0: Количество первого токена для добавления.
    :param amount1: Количество второго токена для добавления.
    :param token_id: ID позиции NFT на Uniswap.
    """
    token0 = TOKEN0  # WETH
    token1 = TOKEN1  # USDC

    logger = setup_logger(wallet_address)
    logger.info(f"Добавление ликвидности в диапазон {new_range_lower} - {new_range_upper} начато.")

    tick_lower, tick_upper = price_to_tick(new_range_lower), price_to_tick(new_range_upper)
    price_ticked_lower, price_ticked_upper = tick_to_price(tick_lower), tick_to_price(tick_upper)

    try:
        # Если amount0 не передано, вычисляем их динамически
        if amount0 is None:
            amount0, amount1 = AMOUNT0, AMOUNT1
            logger.info(f"Вычислены значения для кошелька {wallet_address}: amount0 = {amount0}, amount1 = {amount1}")
        else:
            amount1 = eth_to_usdc(price_ticked_lower, price_ticked_upper, get_eth_price(), amount0)
            logger.info(f"Используются переданные значения для кошелька {wallet_address}: amount0 = {amount0}, amount1 = {amount1}")


        # Получаем контракт
        position_manager = get_contract(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH)

        params = (
            Web3.to_checksum_address(token0),
            Web3.to_checksum_address(token1),
            3000,
            -194710,
            -194160,
            Web3.to_wei(amount0, 'ether'),
            int(amount1 * (10**6)),
            0,
            0,
            Web3.to_checksum_address(wallet_address),
            int(time.time()) + 60
        )
        print(Web3.to_checksum_address(token0),
            Web3.to_checksum_address(token1),
            3000,
            tick_lower,
            tick_upper,
            Web3.to_wei(amount0, 'ether'),
            int(amount1 * (10**6)),
            0,
            0,
            Web3.to_checksum_address(wallet_address),
            int(time.time()) + 60)
        add_liquidity_txn = position_manager.functions.mint(params).build_transaction({
            "from": wallet_address,
            "value": 0,
            "gasPrice": int(web3.eth.gas_price * GAS_PRICE_MULTIPLIER),
            "nonce": web3.eth.get_transaction_count(wallet_address),
        })

        # Оценка газа для mint
        estimated_gas = web3.eth.estimate_gas(add_liquidity_txn)
        add_liquidity_txn['gas'] = int(estimated_gas * 1.2)  # Добавляем запас 20%


        signed_tx = web3.eth.account.sign_transaction(add_liquidity_txn, private_key=private_key)

        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        logger.info(f"Ликвидность успешно добавлена для кошелька {wallet_address}. Хэш транзакции: {tx_hash}")
    except Exception as e:
        logger.error(f"Ошибка при добавлении ликвидности для кошелька {wallet_address}: {e}")
