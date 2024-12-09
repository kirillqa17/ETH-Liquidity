import time
from web3 import Web3
import os
from dotenv import load_dotenv
from utils.select_chain import select_chain

# Загрузка данных сети
chain = select_chain()

from utils.blockchain import get_web3, get_user_position, get_position_liquidity, check_allowance, approve_token
from utils.pricing import get_eth_price
from utils.rebalance import should_rebalance, calculate_new_range, remove_liquidity, add_liquidity, collect_fees
from utils.logger import setup_logger
from utils.decryption import is_base64, decrypt_private_key, get_password
# Загрузка настроек из .env
load_dotenv()

# Получаем настройки из переменных окружения
RANGE_WIDTH = float(os.getenv("RANGE_WIDTH", 100))  # Ширина диапазона
THRESHOLD_PERCENT = float(os.getenv("THRESHOLD_PERCENT", 10)) / 100  # Порог для ребалансировки (в процентах)
PRICE_CHECK_INTERVAL = int(chain["PRICE_CHECK_INTERVAL"])  # Интервал проверки в секундах
GAS_PRICE_MULTIPLIER = float(os.getenv("GAS_PRICE_MULTIPLIER", 1.2))  # Коэффициент для газа
LOG_FOLDER = os.getenv("LOG_FOLDER", "logs")  # Папка для логов
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # Уровень логов
RANGE_LOWER = float(os.getenv("RANGE_LOWER"))  # Нижняя граница диапазона
RANGE_HIGHER = float(os.getenv("RANGE_HIGHER"))  # Верхняя граница диапазона
POSITION_MANAGER_ABI_PATH = os.getenv('POSITION_MANAGER_ABI_PATH', 'utils/position_manager_abi.json')
POSITION_MANAGER_ADDRESS = chain['POSITION_MANAGER_ADDRESS']
ERC20_ABI = os.getenv("ERC20_ABI_PATH", 'utils/erc20_abi.json')
TOKEN1 = chain["TOKEN1"]
AMOUNT0 = float(os.getenv('AMOUNT0'))


def get_wallet_info_from_file(file_path="wallets.txt"):
    """
    Считывает информацию о кошельках из файла. Поддерживает как зашифрованные, так и незашифрованные ключи.
    Проверяет, зашифрован ли файл, по первой строке. Если да, запрашивает пароль один раз для всех строк.

    :param file_path: Путь к файлу с ключами.
    :return: Список пар (адрес, приватный ключ).
    """
    wallets = []

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл '{file_path}' не найден.")
    if os.path.getsize(file_path) == 0:
        raise ValueError(f"Файл '{file_path}' пуст. Добавьте кошельки в файл.")

    with open(file_path, "r") as file:
        lines = [line.strip() for line in file if line.strip()]
        if not lines:
            raise ValueError(f"Файл '{file_path}' пуст. Добавьте кошельки в файл.")

        # Определяем, зашифрованы ли ключи, по первой строке
        first_line = lines[0]
        encrypted = is_base64(first_line)

        if encrypted:
            # Запрашиваем пароль один раз
            password = None
            while True:
                try:
                    password = get_password("Введите пароль для расшифровки ключей: ").strip()
                    # Проверяем пароль на первой строке
                    decrypt_private_key(first_line, password)
                    break  # Если расшифровка успешна, выходим из цикла
                except (ValueError, UnicodeDecodeError):
                    print("Неверный пароль, попробуйте снова.")
                except Exception as e:
                    raise ValueError(f"Ошибка проверки пароля: {e}")

        for line_num, line in enumerate(lines, start=1):
            try:
                if encrypted:
                    # Расшифровываем приватный ключ
                    private_key = decrypt_private_key(line, password)
                else:
                    # Незашифрованный ключ
                    private_key = line

                # Получаем адрес кошелька из приватного ключа
                wallet_address = Web3().eth.account.from_key(private_key).address
                wallets.append((wallet_address, private_key))
            except Exception as e:
                print(f"Ошибка обработки строки {line_num} ('{line}'): {e}")

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

    choice = 0
    # Считываем кошельки
    wallets = get_wallet_info_from_file()
    # Создаём логгеры для каждого кошелька
    loggers = {address: create_logger(address) for address, _ in wallets}

    for wallet_address, private_key in wallets:
        try:
            if not check_allowance(wallet_address, POSITION_MANAGER_ADDRESS, TOKEN1, ERC20_ABI):
                txn = approve_token(wallet_address, private_key, POSITION_MANAGER_ADDRESS, TOKEN1, ERC20_ABI)
                loggers[wallet_address].info(f"Approve отправлена для кошелька {wallet_address} хэш транзакции {txn}")

        except Exception as e:
            loggers[wallet_address].error("Скрипт не будет работать без approve для всех кошельков!")
            exit(1)
    first_wallet = wallets[0][0]

    while True:
        current_price = None
        try:
            # Получаем текущую цену ETH
            current_price = get_eth_price()
            if current_price is None:
                loggers[first_wallet].warning(
                    f"Не удалось получить текущую цену. Повтор через {PRICE_CHECK_INTERVAL} секунд.")
                time.sleep(PRICE_CHECK_INTERVAL)
                continue
        except Exception as e:
            loggers[first_wallet].error(f"Ошибка при получении цены ETH: {e}")

        amount0, amount1 = None, None

        loggers[first_wallet].info(f"Текущая цена ETH: ${current_price}")

        # Проверка необходимости ребалансировки
        if should_rebalance(current_price, RANGE_LOWER, RANGE_HIGHER, THRESHOLD_PERCENT, first_wallet):
            for wallet_address, private_key in wallets:
                try:
                    loggers[wallet_address].info("Ребалансировка начата...")
                    token_id = get_user_position(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH, wallet_address)
                    # Удаление текущей ликвидности
                    if not (get_position_liquidity(POSITION_MANAGER_ADDRESS, POSITION_MANAGER_ABI_PATH, token_id, wallet_address)):
                        if choice != 1:
                            user_answer = input(
                                f"На некоторых кошельках нет текущей ликвидности, желаете чтобы ее добавил бот? (да/нет) : ").strip().lower()
                            if user_answer in ["да", "yes", "y", "1"]:
                                amount0 = AMOUNT0
                                choice = 1
                            else:
                                loggers[wallet_address].error(
                                    f"Ошибка для кошелька {wallet_address}: Нет текущей ликвидности")
                                continue
                        else:
                            amount0 = AMOUNT0
                    else:
                        # Сбор комиссий
                        if collect_fees(web3, wallet_address, private_key, token_id):
                            # Удаление ликвидности
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
                        f"Ребалансировка для кошелька {wallet_address} завершена. Новый диапазон: ${new_range_lower} - ${new_range_upper}")
                except Exception as e:
                    loggers[wallet_address].error(f"Ошибка для кошелька {wallet_address}: {e}")
        else:
            loggers[first_wallet].info("Ребалансировка не требуется. Ожидание следующей проверки.")


        # Задержка между проверками
        time.sleep(PRICE_CHECK_INTERVAL)


if __name__ == "__main__":
    main()
