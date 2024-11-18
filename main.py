import time
import os
from dotenv import load_dotenv
from utils.blockchain import get_web3, get_wallet_info
from utils.pricing import get_eth_price
from utils.rebalance import should_rebalance, calculate_new_range, remove_liquidity, add_liquidity
from utils.logger import setup_logger

# Загрузка настроек из .env
load_dotenv()

# Получаем настройки из переменных окружения
RANGE_WIDTH = float(os.getenv("RANGE_WIDTH", 100))  # Ширина диапазона
THRESHOLD_PERCENT = float(os.getenv("THRESHOLD_PERCENT", 10)) / 100  # Порог для ребалансировки (в процентах)
PRICE_CHECK_INTERVAL = int(os.getenv("PRICE_CHECK_INTERVAL", 60))  # Интервал проверки в секундах
RANGE_LOWER = float(os.getenv("RANGE_LOWER", 2950))  # Нижняя граница диапазона
RANGE_HIGHER = float(os.getenv("RANGE_HIGHER", 3050))  # Верхняя граница диапазона
PAIR = os.getenv("PAIR", "ETH/USDC")  # Торговая пара
GAS_LIMIT = int(os.getenv("GAS_LIMIT", 300000))  # Лимит газа
GAS_PRICE_MULTIPLIER = float(os.getenv("GAS_PRICE_MULTIPLIER", 1.1))  # Коэффициент для газа
LOG_FOLDER = os.getenv("LOG_FOLDER", "logs")  # Папка для логов
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # Уровень логов

# Создаем логгер для работы с кошельками
def create_logger(wallet_address):
    return setup_logger(wallet_address, LOG_FOLDER, LOG_LEVEL)

def main():
    """
    Основной цикл работы ребалансировщика.
    """
    print("Запуск ребалансировщика...")
    web3 = get_web3()
    wallets = get_wallet_info()

    # Создаём логгеры для каждого кошелька
    loggers = {address: create_logger(address) for address, _ in wallets}

    while True:
        for wallet_address, private_key in wallets:
            try:
                # Получаем текущую цену ETH
                current_price = get_eth_price()
                if current_price is None:
                    loggers[wallet_address].warning("Не удалось получить текущую цену. Повтор через 60 секунд.")
                    time.sleep(PRICE_CHECK_INTERVAL)
                    continue

                loggers[wallet_address].info(f"Текущая цена ETH: ${current_price}")

                # Проверка необходимости ребалансировки
                if should_rebalance(current_price, RANGE_LOWER, RANGE_HIGHER, THRESHOLD_PERCENT):
                    loggers[wallet_address].info("Ребалансировка начата...")

                    # Удаление текущей ликвидности
                    remove_liquidity(wallet_address, private_key)

                    # Расчёт нового диапазона
                    new_range_lower, new_range_upper = calculate_new_range(current_price, RANGE_WIDTH)

                    # Добавление ликвидности с новым диапазоном
                    add_liquidity(wallet_address, private_key, new_range_lower, new_range_upper)

                    # Обновление глобальных переменных диапазона
                    RANGE_LOWER, RANGE_HIGHER = new_range_lower, new_range_upper

                    loggers[wallet_address].info(f"Ребалансировка завершена. Новый диапазон: ${new_range_lower} - ${new_range_upper}")
                else:
                    loggers[wallet_address].info("Ребалансировка не требуется. Ожидание следующей проверки.")

            except Exception as e:
                loggers[wallet_address].error(f"Ошибка для кошелька {wallet_address}: {e}")

        # Задержка между проверками
        time.sleep(PRICE_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
