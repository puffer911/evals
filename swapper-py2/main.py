import os
import json
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# --- Configuration ---
BASE_RPC_URL = os.getenv("BASE_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
# Uniswap V4 Router address on Base
UNISWAP_V4_ROUTER_ADDRESS = "0x4a7A52CFc73785C590c836945d2045a919A43b14" 
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base USDC
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"  # Base WETH

# --- Web3 Connection ---
w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
if not w3.is_connected():
    raise ConnectionError("Failed to connect to Base node")

account = w3.eth.account.from_key(PRIVATE_KEY)
w3.eth.default_account = account.address

# --- ABIs ---
# A minimal ABI for ERC20 tokens
ERC20_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}]')

# Uniswap V4 Router ABI (simplified for this example)
UNISWAP_V4_ROUTER_ABI = json.loads('[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"}],"internalType":"struct IMultiHopSwap.Path[]","name":"path","type":"tuple[]"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"minAmountOut","type":"uint256"}],"name":"swap","outputs":[],"stateMutability":"payable","type":"function"}]')

# --- Contract Instances ---
usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
uniswap_router = w3.eth.contract(address=UNISWAP_V4_ROUTER_ADDRESS, abi=UNISWAP_V4_ROUTER_ABI)

def get_eth_balance():
    """Returns the ETH balance of the account in Ether."""
    balance_wei = w3.eth.get_balance(account.address)
    return w3.from_wei(balance_wei, 'ether')

def get_usdc_balance():
    """Returns the USDC balance of the account."""
    balance = usdc_contract.functions.balanceOf(account.address).call()
    decimals = usdc_contract.functions.decimals().call()
    return balance / (10 ** decimals)

def swap_eth_for_usdc():
    """
    Swaps a fixed amount of ETH for USDC on the Base network using Uniswap V4.
    """
    print("--- Uniswap V4 ETH to USDC Swapper on Base ---")
    print(f"Account: {account.address}")
    print(f"Initial ETH Balance: {get_eth_balance():.6f} ETH")
    print(f"Initial USDC Balance: {get_usdc_balance():.6f} USDC")
    print("-" * 50)

    amount_in = w3.to_wei(0.00025, 'ether')
    
    # Define the swap path for ETH -> USDC
    # Even for native ETH swaps, the path uses the WETH address as it represents
    # the ETH liquidity pool on Uniswap. The router handles the wrapping automatically
    # when msg.value is sent with the transaction.
    # The fee tier is typically 500, 3000, or 10000. We'll use 3000 as an example.
    path = [
        (WETH_ADDRESS, USDC_ADDRESS, 3000)
    ]

    # Set a minimum amount out to avoid high slippage (e.g., 1% slippage tolerance)
    # This is a placeholder calculation. A real implementation would use a price oracle.
    min_amount_out = 0 

    print(f"Attempting to swap {w3.from_wei(amount_in, 'ether')} ETH for USDC...")

    try:
        # Build the transaction
        tx = uniswap_router.functions.swap(
            path,
            amount_in,
            min_amount_out
        ).build_transaction({
            'from': account.address,
            'value': amount_in,
            'gas': 300000,  # Increased gas limit for V4
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': 8453  # Base Mainnet Chain ID
        })

        # Sign and send the transaction
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"Transaction sent with hash: {tx_hash.hex()}")
        
        # Wait for the transaction to be mined
        print("Waiting for transaction receipt...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print("Transaction successful!")
        print(f"Transaction hash: {receipt.transactionHash.hex()}")
        print(f"Block number: {receipt.blockNumber}")
        print(f"Gas used: {receipt.gasUsed}")

    except Exception as e:
        print(f"An error occurred: {e}")
        return

    print("-" * 50)
    print(f"Final ETH Balance: {get_eth_balance():.6f} ETH")
    print(f"Final USDC Balance: {get_usdc_balance():.6f} USDC")
    print("--- Swap Complete ---")


if __name__ == "__main__":
    if not all([BASE_RPC_URL, PRIVATE_KEY]):
        print("Error: BASE_RPC_URL and PRIVATE_KEY must be set in the .env file.")
    else:
        swap_eth_for_usdc()
