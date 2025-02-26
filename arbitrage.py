from web3 import Web3
from flashbots import FlashbotsWeb3  # Updated from Flashbot
from config import *
from utils import get_reserves, get_amount_out, load_abi

class ArbitrageBot:
    def __init__(self, web3, flashbot):
        self.web3 = web3
        self.flashbot = flashbot  # Updated to FlashbotsWeb3
        self.uniswap = web3.eth.contract(address=UNISWAP_ROUTER, abi=load_abi("UniswapV2Router02.json"))
        self.sushiswap = web3.eth.contract(address="0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F", abi=load_abi("UniswapV2Router02.json"))  # SushiSwap Router

    def check_arbitrage(self, token_a, token_b, amount_borrow):
        """Check for arbitrage opportunity between Uniswap and SushiSwap."""
        pair1 = get_pair_address(self.web3, UNISWAP_FACTORY, token_a, token_b)
        pair2 = get_pair_address(self.web3, "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac", token_a, token_b)  # SushiSwap Factory
        reserves1 = get_reserves(self.web3, pair1)
        reserves2 = get_reserves(self.web3, pair2)

        # Uniswap: token_a -> token_b, SushiSwap: token_b -> token_a
        amount_b = get_amount_out(amount_borrow, reserves1[0], reserves1[1])
        final_a = get_amount_out(amount_b, reserves2[1], reserves2[0])
        profit = final_a - amount_borrow
        gas_cost = 500000 * self.web3.eth.gas_price / 1e18  # Estimated gas cost in ETH
        return profit > gas_cost + MIN_PROFIT_THRESHOLD, profit

    def execute_arbitrage(self, token_a, token_b, amount_borrow):
        """Execute flash loan arbitrage (assuming contract deployed)."""
        contract = self.web3.eth.contract(address=FLASH_LOAN_CONTRACT, abi=load_abi("FlashLoanArbitrage.json"))
        tx = contract.functions.initiateArbitrage(
            token_a, amount_borrow, UNISWAP_ROUTER, self.sushiswap.address, token_a, token_b, int(MIN_PROFIT_THRESHOLD * 1e18)
        ).build_transaction({
            "from": ACCOUNT,
            "gas": 500000,
            "nonce": self.web3.eth.get_transaction_count(ACCOUNT),
        })
        signed_tx = self.web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        self.flashbot.send_bundle([signed_tx])  # Updated to use FlashbotsWeb3
        print(f"Submitted arbitrage tx with profit {profit / 1e18} ETH")

def check_arbitrage_opportunities(web3, flashbot):
    bot = ArbitrageBot(web3, flashbot)  # Updated to FlashbotsWeb3
    token_a, token_b = WETH, "0x6B175474E89094C44Da98b954EedeAC495271d0F"  # Example: WETH-DAI
    amount_borrow = 10 * 10**18  # 10 WETH
    while True:
        profitable, profit = bot.check_arbitrage(token_a, token_b, amount_borrow)
        if profitable:
            bot.execute_arbitrage(token_a, token_b, amount_borrow)
        time.sleep(5)
