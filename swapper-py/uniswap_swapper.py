"""
Uniswap Universal Router Swapper - Core functionality for Base Network V4
"""

import os
import traceback
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from dotenv import load_dotenv
import time
from abis import ERC20_ABI
from uniswap_universal_router_decoder import RouterCodec

load_dotenv()

class UniversalRouterSwapper:
    def __init__(self):
        self.rpc_url = os.getenv('RPC_URL')
        if not self.rpc_url:
            raise ValueError("RPC_URL not found in environment variables")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Ethereum network")

        private_key = os.getenv('PRIVATE_KEY')
        if not private_key:
            raise ValueError("PRIVATE_KEY not found in environment variables")

        self.account = Account.from_key(private_key)
        print(f"Connected to wallet: {self.account.address}")

        ur_raw = os.getenv('UNIVERSAL_ROUTER_ADDRESS')
        if not ur_raw:
            raise ValueError("UNIVERSAL_ROUTER_ADDRESS not found in environment variables")
        self.universal_router_address = self.w3.to_checksum_address(ur_raw)

        usdc_raw = os.getenv('USDC_ADDRESS')
        if not usdc_raw:
            raise ValueError("USDC_ADDRESS not found in environment variables")
        self.usdc_address = self.w3.to_checksum_address(usdc_raw)

        self.router_codec = RouterCodec()

    def get_balance(self, token_address=None):
        if token_address is None:
            return self.w3.eth.get_balance(self.account.address)
        else:
            contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            return contract.functions.balanceOf(self.account.address).call()

    def swap_eth_to_usdc(self, eth_amount_wei):
        """
        Swap ETH to USDC using Uniswap Universal Router V4 builder (v4_swap -> swap_exact_in_single)
        
        :param eth_amount_wei: Amount of ETH to swap (in wei)
        """
        # Validate ETH balance
        if self.get_balance() < eth_amount_wei:
            raise ValueError("Insufficient ETH balance")

        # Build pool key dict using RouterCodec helper
        pool_key = self.router_codec.encode.v4_pool_key(
            '0x0000000000000000000000000000000000000000',  # native ETH
            self.usdc_address,
            500,  # fee (0.05%)
            10,   # tick spacing
            '0x0000000000000000000000000000000000000000'  # hooks
        )

        # Use the builder API to construct a v4 swap transaction (exact in single)
        builder = self.router_codec.encode.chain().v4_swap()
        # swap_exact_in_single args: pool_key, zero_for_one, amount_in, amount_out_min
        builder.swap_exact_in_single(
            pool_key=pool_key,
            zero_for_one=True,            # ETH -> token: zero_for_one = True
            amount_in=eth_amount_wei,
            amount_out_min=0
        )
        # take_all to collect output token (USDC)
        builder.take_all(self.usdc_address, 0)
        # finalize builder and produce transaction dict targeting the Universal Router
        v4_swap = builder.build_v4_swap()
        trx = v4_swap.build_transaction(self.account.address, eth_amount_wei, ur_address=self.universal_router_address)

        # Sign and broadcast
        signed = self.w3.eth.account.sign_transaction(trx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash

    def swap_usdc_to_eth(self, usdc_amount):
        """
        Swap USDC to ETH using Universal Router V4 builder (v4_swap -> swap_exact_in_single)
        
        :param usdc_amount: Amount of USDC to swap (in smallest units)
        """
        # Validate USDC balance
        usdc_balance = self.get_balance(self.usdc_address)
        if usdc_balance < usdc_amount:
            raise ValueError("Insufficient USDC balance")

        # Approve Universal Router to spend USDC
        usdc_contract = self.w3.eth.contract(address=self.usdc_address, abi=ERC20_ABI)
        approve_tx = usdc_contract.functions.approve(self.universal_router_address, usdc_amount).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price
        })
        signed_approve_tx = self.w3.eth.account.sign_transaction(approve_tx, self.account.key)
        approve_tx_hash = self.w3.eth.send_raw_transaction(signed_approve_tx.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(approve_tx_hash)

        # Build pool key dict using RouterCodec helper
        pool_key = self.router_codec.encode.v4_pool_key(
            self.usdc_address,
            '0x0000000000000000000000000000000000000000',  # native ETH
            500,  # fee (0.05%)
            10,   # tick spacing
            '0x0000000000000000000000000000000000000000'  # hooks
        )

        # Use the builder API to construct a v4 swap transaction (exact in single)
        builder = self.router_codec.encode.chain().v4_swap()
        # swap_exact_in_single args: pool_key, zero_for_one, amount_in, amount_out_min
        builder.swap_exact_in_single(
            pool_key=pool_key,
            zero_for_one=False,
            amount_in=usdc_amount,
            amount_out_min=0
        )
        # settle_all to send native ETH to recipient (address zero denotes native)
        builder.settle_all('0x0000000000000000000000000000000000000000', 0)

        # finalize builder and produce transaction dict targeting the Universal Router
        v4_swap = builder.build_v4_swap()
        trx = v4_swap.build_transaction(self.account.address, 0, ur_address=self.universal_router_address)

        # Sign and broadcast
        signed = self.w3.eth.account.sign_transaction(trx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash

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

def interactive_swap(swapper):
    while True:
        print("\n" + "="*50)
        print("UNISWAP UNIVERSAL ROUTER V4 - BASE NETWORK")
        print("="*50)
        print("1. Display Balances")
        print("2. Swap ETH to USDC")
        print("3. Swap USDC to ETH")
        print("4. Exit")
        print("="*50)

        try:
            choice = input("Select option (1-4): ").strip()

            if choice == "1":
                print(f"ETH Balance: {swapper.w3.from_wei(swapper.get_balance(), 'ether'):.4f} ETH")
                print(f"USDC Balance: {swapper.get_balance(swapper.usdc_address) / 10**6:.2f} USDC")
                input("\nPress Enter to continue...")

            elif choice == "2":
                try:
                    amount_str = input("Enter ETH amount to swap: ").strip()
                    eth_amount = float(amount_str)
                    eth_amount_wei = swapper.w3.to_wei(eth_amount, 'ether')

                    tx_hash = swapper.swap_eth_to_usdc(eth_amount_wei)
                    print("⏳ Waiting for transaction confirmation...")
                    receipt = swapper.wait_for_transaction(tx_hash)
                    print(f"✅ Swap completed! Transaction: {receipt.transactionHash.hex()}")

                except ValueError as e:
                    print(f"❌ Error: {str(e)}")
                    traceback.print_exc()

            elif choice == "3":
                try:
                    amount_str = input("Enter USDC amount to swap: ").strip()
                    usdc_amount = float(amount_str)
                    usdc_amount_int = int(usdc_amount * 10**6)

                    tx_hash = swapper.swap_usdc_to_eth(usdc_amount_int)
                    print("⏳ Waiting for transaction confirmation...")
                    receipt = swapper.wait_for_transaction(tx_hash)
                    print(f"✅ Swap completed! Transaction: {receipt.transactionHash.hex()}")

                except ValueError as e:
                    print(f"❌ Error: {str(e)}")
                    traceback.print_exc()

            elif choice == "4":
                print("\n👋 Goodbye!")
                break

            else:
                print("❌ Invalid option. Please select 1-4.")

        except KeyboardInterrupt:
            print("\n\n👋 Operation cancelled. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            traceback.print_exc()
            input("\nPress Enter to continue...")
