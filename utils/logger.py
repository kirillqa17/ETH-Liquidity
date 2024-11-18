import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("rebalance.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("RebalanceLogger")
