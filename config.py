import os
from dotenv import load_dotenv

load_dotenv()

# Blockchain configuration
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT = "YOUR_ADDRESS"  # Derived from private key in main.py

# Contract addresses (Ethereum Mainnet)
UNISWAP_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
UNISWAP_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
DYDX_SOLO_MARGIN = "0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

# Gas and profit settings
MIN_PROFIT_THRESHOLD = 0.01  # 0.01 ETH
BASE_FEE_MULTIPLIER = 2  # For miner payment
