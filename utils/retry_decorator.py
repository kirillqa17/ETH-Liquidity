# utils/retry_decorator.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging, os
from dotenv import load_dotenv
load_dotenv()

RPC_RETRY_LIMIT = int(os.getenv("RPC_RETRY_LIMIT", 3))

def custom_before_sleep(retry_state):
    """
    Пользовательская функция для обработки событий перед задержкой.
    Записывает кастомное сообщение в лог.
    """
    logger = retry_state.fn.__module__ + "." + retry_state.fn.__name__
    logger = logging.getLogger(logger)
    exception = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    max_attempts = getattr(retry_state.retry_object.stop, 'max', RPC_RETRY_LIMIT)
    wait = retry_state.next_action.sleep

    # Формируем кастомное сообщение
    message = (f"Пытаемся снова выполнить {retry_state.fn.__name__} (попытка {attempt} из {max_attempts}) "
               f"через {wait:.1f} секунд после ошибки: {exception}")
    logger.warning(message)

def retry_on_exception(max_attempts=RPC_RETRY_LIMIT, min_wait=4, max_wait=11, logger=None):
    """
    Декоратор для повторных попыток выполнения функции при возникновении исключений.

    :param max_attempts: Максимальное количество попыток.
    :param min_wait: Минимальная задержка перед следующей попыткой (секунды).
    :param max_wait: Максимальная задержка перед следующей попыткой (секунды).
    :param logger: Логгер для записи предупреждений перед каждой попыткой.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(Exception),
        before_sleep=custom_before_sleep
    )
