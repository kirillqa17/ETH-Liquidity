from logger import setup_logger

logger = setup_logger()

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

def remove_liquidity():
    """
    Удаляет ликвидность из текущей позиции.
    """
    logger.info("Удаление ликвидности начато.")
    # Здесь будет реализация удаления ликвидности через смарт-контракт
    logger.info("Ликвидность успешно удалена.")

def add_liquidity(new_range_lower, new_range_upper):
    """
    Добавляет ликвидность в новый диапазон.
    :param new_range_lower: Новая нижняя граница диапазона.
    :param new_range_upper: Новая верхняя граница диапазона.
    """
    logger.info(f"Добавление ликвидности в диапазон {new_range_lower} - {new_range_upper} начато.")
    # Здесь будет реализация добавления ликвидности через смарт-контракт
    logger.info("Ликвидность успешно добавлена.")
