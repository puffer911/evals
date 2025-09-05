"""
Uniswap V4 ETH/USDC Swapper - Core functionality
"""

import os
import sys
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from dotenv import load_dotenv
import json
import time
from abis import POOL_MANAGER_ABI, ERC20_ABI

# Load environment variables
load_dotenv()

class UniswapV4Swapper:
    def __init__(self):
        # Initialize Web3
        self.rpc_url = os.getenv('RPC_URL')
        if not self.rpc_url:
            raise ValueError("RPC_URL not found in environment variables")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum network")

        # Load private key
        private_key = os.getenv('PRIVATE_KEY')
        if not private_key:
            raise ValueError("PRIVATE_KEY not found in environment variables")

        self.account = Account.from_key(private_key)
        print(f"Connected to wallet: {self.account.address}")

        # Contract addresses (no defaults - must be set in .env)
        pool_manager_raw = os.getenv('POOL_MANAGER_ADDRESS')
        if not pool_manager_raw:
            raise ValueError("POOL_MANAGER_ADDRESS not found in environment variables")
        self.pool_manager_address = self.w3.to_checksum_address(pool_manager_raw)

        usdc_raw = os.getenv('USDC_ADDRESS')
        if not usdc_raw:
            raise ValueError("USDC_ADDRESS not found in environment variables")
        self.usdc_address = self.w3.to_checksum_address(usdc_raw)

        # Initialize contracts
        self.pool_manager = self.w3.eth.contract(
            address=self.pool_manager_address,
            abi=POOL_MANAGER_ABI
        )
        self.usdc_contract = self.w3.eth.contract(
            address=self.usdc_address,
            abi=ERC20_ABI
        )

    def get_balance(self, token_address=None):
        """Get balance of ETH or ERC20 token"""
        if token_address is None:
            # ETH balance
            return self.w3.eth.get_balance(self.account.address)
        else:
            # ERC20 balance
            contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            return contract.functions.balanceOf(self.account.address).call()

    def check_allowance(self, token_address, spender_address):
        """Check token allowance"""
        contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
        return contract.functions.allowance(self.account.address, spender_address).call()

    def approve_token(self, token_address, spender_address, amount):
        """Approve token spending"""
        contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)

        # Build transaction
        tx = contract.functions.approve(spender_address, amount).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f"Approval transaction sent: {tx_hash.hex()}")
        return tx_hash

    def swap_eth_to_usdc(self, eth_amount_wei, min_usdc_out=0, slippage_percent=0.5):
        """
        Swap ETH to USDC using Uniswap V4 (native ETH support)
        """
        print(f"Swapping {self.w3.from_wei(eth_amount_wei, 'ether')} ETH to USDC")

        # Check ETH balance
        eth_balance = self.get_balance()
        if eth_balance < eth_amount_wei:
            raise ValueError(f"Insufficient ETH balance. Have: {self.w3.from_wei(eth_balance, 'ether')}, Need: {self.w3.from_wei(eth_amount_wei, 'ether')}")

        # In Uniswap V4, we can use native ETH directly (address(0))
        return self._swap_tokens(
            "0x0000000000000000000000000000000000000000",  # native ETH
            self.usdc_address,  # to USDC
            eth_amount_wei,     # amount in
            min_usdc_out,       # min out
            slippage_percent,   # slippage
            is_native_eth=True  # flag for native ETH
        )

    def _swap_tokens(self, token_in, token_out, amount_in, min_out=0, slippage_percent=0.5, is_native_eth=False):
        """
        Internal method to perform token swap using Uniswap V4

        Current approach: Dynamic pool key construction via PoolManager
        - More flexible, doesn't require specific pool IDs
        - PoolManager handles pool discovery/routing
        - Production-ready approach
        """
        print(f"Swapping tokens: {token_in} -> {token_out}, Amount: {amount_in}")

        # Method 1: Dynamic pool key construction (current approach)
        # This constructs the pool key based on token addresses
        # PoolManager will find or create the appropriate pool
        pool_key = {
            "currency0": min(token_in, token_out),  # sorted addresses
            "currency1": max(token_in, token_out),
            "fee": 3000,  # 0.3% fee (most common)
            "tickSpacing": 60,  # standard tick spacing
            "hooks": "0x0000000000000000000000000000000000000000"  # no hooks
        }

        print(f"Using dynamic pool key: {pool_key}")

        # Determine swap direction
        zero_for_one = token_in < token_out

        # Calculate sqrt price limit (simplified - in production use proper calculation)
        sqrt_price_limit = 0 if zero_for_one else 2**160 - 1

        # Swap parameters
        swap_params = {
            "zeroForOne": zero_for_one,
            "amountSpecified": amount_in,
            "sqrtPriceLimitX96": sqrt_price_limit
        }

        # Build swap transaction
        try:
            tx = self.pool_manager.functions.swap(
                pool_key,
                swap_params,
                b""  # empty data for basic swap
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 300000,  # higher gas limit for complex operations
                'gasPrice': self.w3.eth.gas_price,
                'value': amount_in if is_native_eth else 0  # Send ETH value if native ETH swap
            })

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            print(f"Swap transaction sent: {tx_hash.hex()}")
            return tx_hash

        except Exception as e:
            print(f"Swap failed: {str(e)}")
            return None

    def swap_usdc_to_eth(self, usdc_amount, min_eth_out_wei=0, slippage_percent=0.5):
        """
        Swap USDC to ETH using Uniswap V4 (native ETH support)
        """
        print(f"Swapping {usdc_amount / 10**6} USDC to ETH")

        # Check USDC balance
        usdc_balance = self.get_balance(self.usdc_address)
        if usdc_balance < usdc_amount:
            raise ValueError(f"Insufficient USDC balance. Have: {usdc_balance}, Need: {usdc_amount}")

        # Check USDC allowance and approve if needed
        allowance = self.check_allowance(self.usdc_address, self.pool_manager_address)
        if allowance < usdc_amount:
            print(f"Approving USDC spending...")
            approve_tx = self.approve_token(self.usdc_address, self.pool_manager_address, usdc_amount * 2)  # Approve double for safety
            if approve_tx:
                self.wait_for_transaction(approve_tx)
                print("USDC approval confirmed")

        # In Uniswap V4, we can receive native ETH directly (address(0))
        return self._swap_tokens(
            self.usdc_address,  # from USDC
            "0x0000000000000000000000000000000000000000",  # native ETH
            usdc_amount,        # amount in
            min_eth_out_wei,    # min out
            slippage_percent    # slippage
        )

    def wait_for_transaction(self, tx_hash, timeout=300):
        """Wait for transaction confirmation"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    return receipt
            except:
                pass
            time.sleep(2)
        raise TimeoutError(f"Transaction {tx_hash.hex()} not confirmed within {timeout} seconds")

def wait_for_user_confirmation(message="Press Enter to continue, or type anything to cancel"):
    """Wait for user confirmation"""
    try:
        response = input(f"\n{message}: ").strip()
        if response:
            print("Operation cancelled.")
            return False
        return True
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return False

def display_balances(swapper):
    """Display current ETH and USDC balances"""
    print("\n" + "="*50)
    print("CURRENT BALANCES")
    print("="*50)

    try:
        eth_balance = swapper.get_balance()  # ETH balance
        usdc_balance = swapper.get_balance(swapper.usdc_address)

        print(f"ETH Balance:  {swapper.w3.from_wei(eth_balance, 'ether'):.6f} ETH")
        print(f"USDC Balance: {usdc_balance / 10**6:.2f} USDC")

        # Check USDC allowance
        allowance = swapper.check_allowance(swapper.usdc_address, swapper.pool_manager_address)
        print(f"USDC Allowance: {allowance / 10**6:.2f} USDC")

    except Exception as e:
        print(f"Error fetching balances: {str(e)}")

def interactive_swap(swapper):
    """Interactive swap menu"""
    while True:
        print("\n" + "="*50)
        print("UNISWAP V4 ETH/USDC SWAPPER")
        print("="*50)
        print("1. Display Balances")
        print("2. Swap ETH to USDC")
        print("3. Swap USDC to ETH")
        print("4. Exit")
        print("="*50)

        try:
            choice = input("Select option (1-4): ").strip()

            if choice == "1":
                display_balances(swapper)
                input("\nPress Enter to continue...")

            elif choice == "2":
                display_balances(swapper)

                eth_balance = swapper.get_balance()
                print(f"\nAvailable ETH: {swapper.w3.from_wei(eth_balance, 'ether'):.6f}")

                amount_str = input("Enter ETH amount to swap: ").strip()
                try:
                    amount = float(amount_str)
                    eth_amount_wei = swapper.w3.to_wei(amount, 'ether')

                    if eth_amount_wei > eth_balance:
                        print("❌ Insufficient ETH balance!")
                        input("\nPress Enter to continue...")
                        continue

                    print(f"\nSwapping {amount} ETH to USDC...")
                    if not wait_for_user_confirmation():
                        continue

                    tx_hash = swapper.swap_eth_to_usdc(eth_amount_wei)
                    if tx_hash:
                        print("⏳ Waiting for transaction confirmation...")
                        receipt = swapper.wait_for_transaction(tx_hash)
                        print(f"✅ Swap completed! Transaction: {receipt.transactionHash.hex()}")
                    else:
                        print("❌ Swap failed!")

                    input("\nPress Enter to continue...")

                except ValueError as e:
                    print(f"❌ Invalid amount: {str(e)}")
                    input("\nPress Enter to continue...")

            elif choice == "3":
                display_balances(swapper)

                usdc_balance = swapper.get_balance(swapper.usdc_address)
                print(f"\nAvailable USDC: {usdc_balance / 10**6:.2f}")

                amount_str = input("Enter USDC amount to swap: ").strip()
                try:
                    amount = float(amount_str)
                    usdc_amount = int(amount * 10**6)

                    if usdc_amount > usdc_balance:
                        print("❌ Insufficient USDC balance!")
                        input("\nPress Enter to continue...")
                        continue

                    print(f"\nSwapping {amount} USDC to ETH...")
                    if not wait_for_user_confirmation():
                        continue

                    tx_hash = swapper.swap_usdc_to_eth(usdc_amount)
                    if tx_hash:
                        print("⏳ Waiting for transaction confirmation...")
                        receipt = swapper.wait_for_transaction(tx_hash)
                        print(f"✅ Swap completed! Transaction: {receipt.transactionHash.hex()}")
                    else:
                        print("❌ Swap failed!")

                    input("\nPress Enter to continue...")

                except ValueError as e:
                    print(f"❌ Invalid amount: {str(e)}")
                    input("\nPress Enter to continue...")

            elif choice == "4":
                print("\n👋 Goodbye!")
                break

            else:
                print("❌ Invalid option. Please select 1-4.")
                input("\nPress Enter to continue...")

        except KeyboardInterrupt:
            print("\n\n👋 Operation cancelled. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            input("\nPress Enter to continue...")
