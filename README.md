# MEV Sandwich Bot Implementation
## Overview
This bot implements two core functionalities:

### Flash Loan Arbitrage: 
Borrows capital from dYdX, executes profitable arbitrage trades across DEXs, and repays the loan atomically.
### Sandwich Attacks: 
Monitors the mempool, front-runs and back-runs victim trades on Uniswap V2 to capture price differences.

The bot ensures gas optimization, profitability checks, and error handling, and is designed for 24/7 automation across EVM-compatible chains.

# Prerequisites

**Python Packages:**
```
pip install web3.py eth-account flashbots python-dotenv
```

**Environment Variables (in a .env file):**
```
RPC_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY
PRIVATE_KEY=YOUR_PRIVATE_KEY
```
**Contract ABIs:** Download UniswapV2Router02.json and UniswapV2Pair.json from Etherscan or Uniswap documentation.

# Code Structure

> main.py: Entry point, orchestrates the bot's components.
> sandwich.py: Handles sandwich attack logic.
> arbitrage.py: Manages flash loan arbitrage.
> utils.py: Utility functions for reserves, profit calculations, etc.
> config.py: Configuration settings.
