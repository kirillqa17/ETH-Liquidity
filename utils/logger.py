import logging
import os
from dotenv import load_dotenv

# Загружаем настройки из .env
load_dotenv()

# Получаем настройки из переменных окружения
LOG_FOLDER = os.getenv("LOG_FOLDER", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # Преобразуем уровень в верхний регистр

# Убедимся, что папка для логов существует
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

# Функция для настройки логера
def setup_logger(wallet_address, log_folder=LOG_FOLDER, log_level=LOG_LEVEL):
    """
    Настройка логгера для каждого кошелька с сохранением логов в отдельный файл.
    """
    logger = logging.getLogger(wallet_address)
    logger.setLevel(log_level)

    # Создание формата для логов
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Настройка файла для логов
    log_filename = os.path.join(log_folder, f"{wallet_address}.log")
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)

    # Настройка консольного вывода
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Добавляем обработчики к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
