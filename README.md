
# ETH-Liquidity

**ETH-Liquidity** is a Python script for managing liquidity in UniswapV3 pools. It automatically rebalances positions using provided private keys and configuration parameters.

## Requirements

- Python version 3.8 or higher.

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/kirillqa17/ETH-Liquidity.git
   cd ETH-Liquidity
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **`.env` file:**

   Create a `.env` file in the root directory and add the following variables


2. **`wallets.txt` file:**

   Add private keys of the wallets to the `wallets.txt` file, each on a new line.

   Example file content:

   ```
   <PRIVATE_KEY_1>
   <PRIVATE_KEY_2>
   ```

   If the keys are encrypted (Base64), the program will prompt for a password on startup.

## Usage

Run the program with the command:

```bash
python main.py
```

Ensure you are in the correct directory before executing this command.

## Logs

The program maintains a log file, recording important events and errors. Logs are saved in the `<YOUR_WALLET_ADDRESS>.log` file in the root directory.

## Security

- **Private Keys:** Keep the `wallets.txt` file secure and do not share it with third parties.
