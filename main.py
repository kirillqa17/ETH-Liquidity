import time
from web3 import Web3
import os
from getpass import getpass
from dotenv import load_dotenv
from utils.blockchain import get_web3, get_user_position, get_position_liquidity
from utils.pricing import get_eth_price
from utils.rebalance import should_rebalance, calculate_new_range, remove_liquidity, add_liquidity
from utils.logger import setup_logger
from utils.decryption import is_base64, decrypt_private_key

# Загрузка настроек из .env
load_dotenv()

# Получаем настройки из переменных окружения
RANGE_WIDTH = float(os.getenv("RANGE_WIDTH", 100))  # Ширина диапазона
THRESHOLD_PERCENT = float(os.getenv("THRESHOLD_PERCENT", 10)) / 100  # Порог для ребалансировки (в процентах)
PRICE_CHECK_INTERVAL = int(os.getenv("PRICE_CHECK_INTERVAL", 60))  # Интервал проверки в секундах
GAS_PRICE_MULTIPLIER = float(os.getenv("GAS_PRICE_MULTIPLIER", 1.1))  # Коэффициент для газа
LOG_FOLDER = os.getenv("LOG_FOLDER", "logs")  # Папка для логов
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # Уровень логов
RANGE_LOWER = float(os.getenv("RANGE_LOWER"))  # Нижняя граница диапазона
RANGE_HIGHER = float(os.getenv("RANGE_HIGHER"))  # Верхняя граница диапазона
POSITION_MANAGER_ABI_PATH = os.getenv('POSITION_MANAGER_ABI_PATH', 'utils/position_manager_abi.json')
POSITION_MANAGER_ADDRESS = os.getenv('POSITION_MANAGER_ADDRESS')


def get_wallet_info_from_file(file_path="wallets.txt", password=None):
    """
    Считывает информацию о кошельках из файла. Поддерживает как зашифрованные, так и незашифрованные ключи.

    :param file_path: Путь к файлу с ключами.
    :param password: Пароль для расшифровки (если требуется).
    :return: Список пар (адрес, приватный ключ).
    """
    wallets = []

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл '{file_path}' не найден.")
    if os.path.getsize(file_path) == 0:
        raise ValueError(f"Файл '{file_path}' пуст. Добавьте кошельки в файл.")

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            try:
                # Проверяем, является ли строка base64-зашифрованной
                if is_base64(line):
                    # Зашифрованный ключ
                    if not password:
                        password = getpass("Введите пароль для расшифровки: ").strip()
                    private_key = decrypt_private_key(line, password)
                else:
                    # Незашифрованный ключ
                    private_key = line

                # Получаем адрес кошелька из приватного ключа
                wallet_address = Web3().eth.account.from_key(private_key).address
                wallets.append((wallet_address, private_key))
            except Exception as e:
                print(f"Ошибка обработки строки '{line}': {e}")

    return wallets



# Создаем логгер для работы с кошельками
def create_logger(wallet_address):
    return setup_logger(wallet_address, LOG_FOLDER, LOG_LEVEL)


def main():
    """
    Основной цикл работы ребалансировщика.
    """
    global RANGE_LOWER, RANGE_HIGHER

    print("Запуск ребалансировщика...")
    web3 = get_web3()
    current_chain_id = web3.eth.chain_id
    if current_chain_id not in [8453, 1]:
        raise ValueError("Вы подключены не к поддерживаемой сети. Проверьте RPC!")


    # Считываем кошельки
    wallets = get_wallet_info_from_file()
    # Создаём логгеры для каждого кошелька
    loggers = {address: create_logger(address) for address, _ in wallets}

    while True:
        for wallet_address, private_key in wallets:
            try:
                # Получаем текущую цену ETH
                current_price = get_eth_price()
                if current_price is None:
                    loggers[wallet_address].warning(
                        f"Не удалось получить текущую цену. Повтор через {PRICE_CHECK_INTERVAL} секунд.")
                    time.sleep(PRICE_CHECK_INTERVAL)
                    continue
                amount0, amount1 = None, None
                loggers[wallet_address].info(f"Текущая цена ETH: ${current_price}")

                # Проверка необходимости ребалансировки
                if should_rebalance(current_price, RANGE_LOWER, RANGE_HIGHER, THRESHOLD_PERCENT, wallet_address):
                    loggers[wallet_address].info("Ребалансировка начата...")
                    token_id = get_user_position(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH, wallet_address)
                    # Удаление текущей ликвидности
                    if not (get_position_liquidity(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH, token_id)):
                        user_answer = input(
                            f"У вас нет текущей ликвидности на кошельке {wallet_address}, желаете, чтобы ее добавил бот? (да/нет): ").strip().lower()
                        if user_answer in ["да", "yes", "y", "1"]:
                            try:
                                user_amount0 = float(input(
                                    f"Введите amount0(WETH) для кошелька {wallet_address} : ").strip())

                                # Если пользователь не ввел значения, используем авторасчёт
                                amount0 = float(user_amount0) if user_amount0 else None
                            except ValueError as e:
                                loggers[wallet_address].error(f"Некорректный ввод amount0: {e}")
                                continue
                        else:
                            loggers[wallet_address].error(
                                f"Ошибка для кошелька {wallet_address}: Нет текущей ликвидности")
                            continue
                    else:
                        remove_liquidity(web3, wallet_address, private_key, token_id)
                    # Расчёт нового диапазона
                    new_range_lower, new_range_upper = calculate_new_range(current_price, RANGE_WIDTH, wallet_address)
                    if amount0 == None:
                        # Добавление ликвидности с новым диапазоном с автоматическим amount
                        add_liquidity(web3, wallet_address, private_key, new_range_lower, new_range_upper)
                    else:
                        # Добавление ликвидности с новым диапазоном с ручным вводом amount
                        add_liquidity(web3, wallet_address, private_key, new_range_lower, new_range_upper,
                                      amount0)
                    # Обновление глобальных переменных диапазона
                    RANGE_LOWER, RANGE_HIGHER = new_range_lower, new_range_upper

                    loggers[wallet_address].info(
                        f"Ребалансировка завершена. Новый диапазон: ${new_range_lower} - ${new_range_upper}")
                else:
                    loggers[wallet_address].info("Ребалансировка не требуется. Ожидание следующей проверки.")

            except Exception as e:
                loggers[wallet_address].error(f"Ошибка для кошелька {wallet_address}: {e}")

        # Задержка между проверками
        time.sleep(PRICE_CHECK_INTERVAL)


if __name__ == "__main__":
    main()
