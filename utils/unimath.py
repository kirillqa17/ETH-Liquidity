import math

TICK_SPACING = 60


def price_to_tick(price):
    """
    Преобразует цену в тик.

    :param price: Цена
    :return: Тик
    """

    price = price * 10 **(-12)
    tick = math.floor(math.log(price, 1.0001))
    rounded_tick = round(tick / TICK_SPACING) * TICK_SPACING
    return rounded_tick


def tick_to_price(tick):
    """
    Преобразует тик в цену.

    :param tick: Тик
    :return: Цена
    """
    price = 1.0001 ** tick
    return price * 10 **12

def get_liquidity_0(x, sa, sb):
    return x * sa * sb / (sb - sa)


def get_liquidity_1(y, sa, sb):
    return y / (sb - sa)


def get_liquidity(x, y, sp, sa, sb):
    if sp <= sa:
        liquidity = get_liquidity_0(x, sa, sb)
    elif sp < sb:
        liquidity0 = get_liquidity_0(x, sp, sb)
        liquidity1 = get_liquidity_1(y, sa, sp)
        liquidity = min(liquidity0, liquidity1)
    else:
        liquidity = get_liquidity_1(y, sa, sb)
    return liquidity


def calculate_y(L, sp, sa, sb):
    sp = max(min(sp, sb), sa)  # if the price is outside the range, use the range endpoints instead
    return L * (sp - sa)

def eth_to_usdc(lower_price, upper_price, eth_price, eth_amount):

    sp = eth_price ** 0.5
    sa = lower_price ** 0.5
    sb = upper_price ** 0.5
    L = get_liquidity_0(eth_amount, sp, sb)
    y = calculate_y(L, sp, sa, sb)
    return y
