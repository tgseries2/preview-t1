from web3 import Web3
from flashbots import Flashbot
import threading
from config import *
from sandwich import monitor_mempool
from arbitrage import check_arbitrage_opportunities

def main():
    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    flashbot = Flashbot(web3, PRIVATE_KEY)
    global ACCOUNT
    ACCOUNT = web3.eth.account.from_key(PRIVATE_KEY).address

    # Start sandwich attack monitoring
    sandwich_thread = threading.Thread(target=monitor_mempool, args=(web3, flashbot))
    sandwich_thread.start()

    # Start arbitrage checking
    check_arbitrage_opportunities(web3, flashbot)

if __name__ == "__main__":
    main()
