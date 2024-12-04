import json, os


def select_chain(config_file_path="config.json"):
    """
    Позволяет пользователю выбрать сеть и сохраняет соответствующую конфигурацию в .conf файл.

    :param config_file_path: Путь к конфигурационному файлу.
    :return: Словарь с параметрами выбранной сети.
    """
    chain_input = str(input("Выберите сеть, с которой будете работать. (Base/Ethereum): "))
    config = {}
    choice = ''
    if chain_input.lower() in ["1", "base", "b"]:
        choice = "Base"
        config = {
            "RPC_URL_1": "https://mainnet.base.org",
            "RPC_URL_2": "https://base.blockpi.network/v1/rpc/public",
            "RPC_URL_3": "https://rpc.ankr.com/base",
            "CHAINLINK_PRICE_FEED": "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",
            "TOKEN0": "0x4200000000000000000000000000000000000006",
            "TOKEN1": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "POSITION_MANAGER_ADDRESS": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1",
            "PRICE_CHECK_INTERVAL": "60"
        }
    elif chain_input.lower() in ["2", "ethereum", "eth", "e"]:
        choice = "Ethereum"
        config = {
            "RPC_URL_1": "https://mainnet.infura.io/v3/d7337f5ecb9d44a58b6aa799a3d6d71d",
            "RPC_URL_2": "https://eth-mainnet.g.alchemy.com/v2/9kHZK9FFpvNoc8WWNPTHzqSUwVsJkamH",
            "RPC_URL_3": "https://rpc.ankr.com/eth",
            "CHAINLINK_PRICE_FEED": "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419",
            "TOKEN0": "0xC02aaa39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "TOKEN1": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "POSITION_MANAGER_ADDRESS": "0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
            "PRICE_CHECK_INTERVAL": "60"
        }
    else:
        print("Неизвестный выбор сети. Пожалуйста, попробуйте снова.")
        return select_chain()  # Рекурсивный вызов для повторного выбора

    # Запись конфигурации в .conf файл
    write_config_to_file(config, config_file_path)
    print(f"Конфигурация для сети {choice} записана в {config_file_path}")

    return config


def write_config_to_file(config, file_path):
    """
    Записывает конфигурацию в JSON файл.

    :param config: Словарь с конфигурацией.
    :param file_path: Путь к конфигурационному файлу.
    """
    try:
        with open(file_path, 'w') as jsonfile:
            json.dump(config, jsonfile, indent=4)
    except Exception as e:
        print(f"Ошибка при записи конфигурации в файл: {e}")


def load_config(config_file_path="config.json"):
    """
    Загружает конфигурацию из JSON файла.

    :param config_file_path: Путь к конфигурационному файлу.
    :return: Словарь с параметрами конфигурации.
    """
    if not os.path.exists(config_file_path):
        raise FileNotFoundError(f"Конфигурационный файл '{config_file_path}' не найден.")

    try:
        with open(config_file_path, 'r') as jsonfile:
            config = json.load(jsonfile)
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка разбора JSON файла конфигурации: {e}")
    except Exception as e:
        raise e
