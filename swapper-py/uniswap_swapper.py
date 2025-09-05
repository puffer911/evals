"""
Uniswap Universal Router Swapper - Core functionality
"""

import os
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

    def check_allowance(self, token_address, spender_address):
        contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
        return contract.functions.allowance(self.account.address, spender_address).call()

    def approve_token(self, token_address, spender_address, amount):
        contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
        tx = contract.functions.approve(spender_address, amount).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.w3.eth.gas_price
        })
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash

    def send_calldata_transaction(self, calldata_hex, value=0, gas=800000):
        if not calldata_hex:
            raise ValueError("Calldata is required")

        if not calldata_hex.startswith('0x'):
            calldata_hex = '0x' + calldata_hex

        tx = {
            'to': self.universal_router_address,
            'from': self.account.address,
            'data': calldata_hex,
            'value': int(value) if value else 0,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': gas,
            'gasPrice': self.w3.eth.gas_price
        }

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash

    def wait_for_transaction(self, tx_hash, timeout=300):
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
        print("UNIVERSAL ROUTER SWAPPER")
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
                    calldata = input("Enter ETH to USDC calldata: ").strip()
                    eth_amount = float(input("Enter ETH amount to send: ").strip())
                    eth_amount_wei = swapper.w3.to_wei(eth_amount, 'ether')

                    tx_hash = swapper.send_calldata_transaction(calldata, value=eth_amount_wei)
                    receipt = swapper.wait_for_transaction(tx_hash)
                    print(f"✅ Swap completed! Transaction: {receipt.transactionHash.hex()}")

                except ValueError as e:
                    print(f"❌ Error: {str(e)}")

            elif choice == "3":
                try:
                    calldata = input("Enter USDC to ETH calldata: ").strip()
                    usdc_amount = float(input("Enter USDC amount to spend: ").strip())
                    usdc_amount_int = int(usdc_amount * 10**6)

                    # Approve USDC spending
                    swapper.approve_token(swapper.usdc_address, swapper.universal_router_address, usdc_amount_int)

                    tx_hash = swapper.send_calldata_transaction(calldata)
                    receipt = swapper.wait_for_transaction(tx_hash)
                    print(f"✅ Swap completed! Transaction: {receipt.transactionHash.hex()}")

                except ValueError as e:
                    print(f"❌ Error: {str(e)}")

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
            input("\nPress Enter to continue...")
