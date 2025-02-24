from web3 import Web3
import json

def load_abi(file_name):
    """Load ABI from a JSON file."""
    with open(file_name, "r") as f:
        return json.load(f)

def get_pair_address(web3, factory, token0, token1):
    """Get Uniswap V2 pair address."""
    factory_contract = web3.eth.contract(address=factory, abi=load_abi("UniswapV2Factory.json"))
    return factory_contract.functions.getPair(token0, token1).call()

def get_reserves(web3, pair_address):
    """Get reserves from a Uniswap V2 pair."""
    pair_abi = load_abi("UniswapV2Pair.json")
    pair = web3.eth.contract(address=pair_address, abi=pair_abi)
    reserves = pair.functions.getReserves().call()
    return reserves[0], reserves[1]  # reserve0, reserve1

def get_amount_out(amount_in, reserve_in, reserve_out):
    """Calculate amount out using Uniswap V2 formula with 0.3% fee."""
    amount_in_with_fee = amount_in * 997
    numerator = amount_in_with_fee * reserve_out
    denominator = (reserve_in * 1000) + amount_in_with_fee
    return numerator // denominator

def get_amount_in(amount_out, reserve_out, reserve_in):
    """Calculate amount in using Uniswap V2 formula with 0.3% fee."""
    numerator = reserve_in * amount_out * 1000
    denominator = (reserve_out - amount_out) * 997
    return (numerator // denominator) + 1
