from utils.blockchain import connect_to_blockchain
from utils.pricing import get_eth_price
from utils.rebalance import rebalance_position
from utils.logger import setup_logger

logger = setup_logger()

def main():
    logger.info("Запуск скрипта...")
    blockchain = connect_to_blockchain()
    eth_price = get_eth_price(blockchain)
    logger.info(f"Текущая цена ETH: ${eth_price}")
    rebalance_position(eth_price)

if __name__ == "__main__":
    main()
