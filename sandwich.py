from web3 import Web3
from flashbots import FlashbotsWeb3  # Updated from Flashbot
from config import *
from utils import get_reserves, get_amount_out, get_pair_address, load_abi

class SandwichBot:
    def __init__(self, web3, flashbot):
        self.web3 = web3
        self.flashbot = flashbot  # Updated to FlashbotsWeb3
        self.router = web3.eth.contract(address=UNISWAP_ROUTER, abi=load_abi("UniswapV2Router02.json"))

    def calculate_sandwich_profit(self, amount_in, amount_out_min, path):
        """Calculate optimal front-run amount and profit."""
        token_in, token_out = path[0], path[-1]
        pair_address = get_pair_address(self.web3, UNISWAP_FACTORY, token_in, token_out)
        reserve_in, reserve_out = get_reserves(self.web3, pair_address)

        # Optimal front-run amount (simplified heuristic)
        z = amount_in // 2  # Adjust based on profitability optimization
        y_in = get_amount_in(z, reserve_out, reserve_in)
        
        # After front-run
        new_reserve_in = reserve_in + y_in
        new_reserve_out = reserve_out - z
        
        # Victim's swap
        victim_out = get_amount_out(amount_in, new_reserve_in, new_reserve_out)
        if victim_out < amount_out_min:
            return 0, None  # Victim's tx would revert
        
        # After victim's swap
        final_reserve_in = new_reserve_in + amount_in
        final_reserve_out = new_reserve_out - victim_out
        
        # Back-run profit
        y_out = get_amount_out(z, final_reserve_out, final_reserve_in)
        profit = y_out - y_in
        return profit, z if profit > 0 else (0, None)

    def construct_bundle(self, tx, profit, z, target_block):
        """Construct Flashbots bundle for sandwich attack."""
        # Front-run buy
        buy_tx = self.router.functions.swapExactETHForTokens(
            0, [WETH, tx["path"][-1]], ACCOUNT, int(time.time()) + 60
        ).build_transaction({
            "from": ACCOUNT,
            "value": z,
            "gas": 200000,
            "maxFeePerGas": web3.toWei(50, "gwei"),
            "maxPriorityFeePerGas": web3.toWei(2, "gwei"),
            "nonce": self.web3.eth.get_transaction_count(ACCOUNT),
            "chainId": 1
        })

        # Back-run sell
        sell_tx = self.router.functions.swapExactTokensForETH(
            z, 0, [tx["path"][-1], WETH], ACCOUNT, int(time.time()) + 60
        ).build_transaction({
            "from": ACCOUNT,
            "gas": 200000,
            "maxFeePerGas": web3.toWei(50, "gwei"),
            "maxPriorityFeePerGas": web3.toWei(2, "gwei"),
            "nonce": self.web3.eth.get_transaction_count(ACCOUNT) + 1,
            "chainId": 1
        })

        # Sign transactions
        signed_buy = self.web3.eth.account.sign_transaction(buy_tx, PRIVATE_KEY)
        signed_sell = self.web3.eth.account.sign_transaction(sell_tx, PRIVATE_KEY)
        signed_victim = tx["rawTransaction"]

        return [
            {"signed_transaction": signed_buy.rawTransaction},
            {"signed_transaction": signed_victim},
            {"signed_transaction": signed_sell.rawTransaction}
        ]

    def process_transaction(self, tx_hash):
        """Process a pending transaction for sandwich opportunity."""
        try:
            tx = self.web3.eth.get_transaction(tx_hash)
            if tx and tx["to"] == UNISWAP_ROUTER:
                func, params = self.router.decode_function_input(tx["input"])
                if func.fn_name == "swapExactETHForTokens" and len(params["path"]) == 2 and params["path"][0] == WETH:
                    amount_in = params["amountIn"]
                    amount_out_min = params["amountOutMin"]
                    path = params["path"]
                    pair = get_pair_address(self.web3, UNISWAP_FACTORY, path[0], path[1])
                    reserves = get_reserves(self.web3, pair)
                    
                    profit, z = self.calculate_sandwich_profit(amount_in, amount_out_min, path)
                    gas_cost = 400000 * self.web3.eth.gas_price * BASE_FEE_MULTIPLIER / 1e18  # Estimated gas cost in ETH
                    if profit > gas_cost + MIN_PROFIT_THRESHOLD:
                        target_block = self.web3.eth.block_number + 1
                        bundle = self.construct_bundle(tx, profit, z, target_block)
                        self.flashbot.send_bundle(bundle, target_block_number=target_block)  # Updated to use FlashbotsWeb3
                        print(f"Submitted sandwich bundle for tx {tx_hash.hex()} in block {target_block}, estimated profit: {profit / 1e18} ETH")

        except Exception as e:
            print(f"Error processing tx {tx_hash.hex()}: {e}")

def monitor_mempool(web3, flashbot):
    bot = SandwichBot(web3, flashbot)  # Updated to FlashbotsWeb3
    pending_filter = web3.eth.filter("pending")
    while True:
        try:
            for tx_hash in pending_filter.get_new_entries():
                bot.process_transaction(tx_hash)
        except Exception as e:
            print(f"Subscription error: {e}")
            time.sleep(1)
