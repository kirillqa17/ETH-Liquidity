def get_eth_price(web3):
    chainlink_eth_usd = "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"
    abi = '[{"inputs":[],"name":"latestAnswer","outputs":[{"internalType":"int256","name":"","type":"int256"}],"stateMutability":"view","type":"function"}]'
    contract = web3.eth.contract(address=chainlink_eth_usd, abi=abi)
    return contract.functions.latestAnswer().call() / 1e8
