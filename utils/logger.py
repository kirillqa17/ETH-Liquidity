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
def setup_logger(wallet_address, log_folder="logs", log_level="INFO"):
    """
    Настройка логгера для каждого кошелька с сохранением логов в отдельный файл.
    :param wallet_address: Адрес кошелька.
    :param log_folder: Путь к папке логов.
    :param log_level: Уровень логирования.
    :return: Объект logger.
    """
    # Убедимся, что папка для логов существует
    os.makedirs(log_folder, exist_ok=True)

    # Получаем уникальный логгер для кошелька
    logger = logging.getLogger(wallet_address)

    # Если обработчики уже существуют, не добавляем их заново
    if not logger.handlers:
        # Устанавливаем уровень логирования
        logger.setLevel(log_level)

        # Создаем форматтер для логов
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Настраиваем файл для логов
        log_filename = os.path.join(log_folder, f"{wallet_address}.log")
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Настраиваем консольный вывод
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger