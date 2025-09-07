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

        # Provide our Web3 instance to RouterCodec so builder can query chain/nonce/etc.
        self.router_codec = RouterCodec(self.w3)

    def get_balance(self, token_address=None):
        if token_address is None:
            return self.w3.eth.get_balance(self.account.address)
        else:
            contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            return contract.functions.balanceOf(self.account.address).call()

    def swap_eth_to_usdc(self, eth_amount_wei):
        print(f"🔍 Network: Base ({self.w3.eth.chain_id})")
        print(f"🔍 Amount: {self.w3.from_wei(eth_amount_wei, 'ether')} ETH")
        
        # Validate balance
        balance = self.get_balance()
        gas_buffer = self.w3.to_wei(0.0003, 'ether')
        if balance < eth_amount_wei + gas_buffer:
            raise ValueError(f"Insufficient ETH balance")

        # Use the exact pool parameters from the screenshot
        pool_key = self.router_codec.encode.v4_pool_key(
            '0x0000000000000000000000000000000000000000',  # ETH (native)
            self.usdc_address,  # 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
            500,   # 0.05% fee (confirmed from screenshot)
            10,    # tick spacing (standard for 0.05%)
            '0x0000000000000000000000000000000000000000'  # no hooks
        )
        
        # Calculate reasonable minimum output
        # From pool: ~84.87 ETH / 394.6K USDC = ~4650 USDC per ETH
        eth_amount_ether = float(self.w3.from_wei(eth_amount_wei, 'ether'))  
        estimated_usdc = eth_amount_ether * 4650  # Use pool ratio
        min_usdc_out = int(estimated_usdc * 0.95 * 10**6)  # 5% slippage, 6 decimals
        
        print(f"📊 Estimated USDC out: {estimated_usdc:.4f}")
        print(f"📊 Minimum USDC (5% slippage): {min_usdc_out / 10**6:.4f}")
        
        # Build swap
        builder = self.router_codec.encode.chain().v4_swap()
        
        # Double-check token ordering: ETH (0x000...) < USDC (0x833...)
        # So ETH is token0, USDC is token1, zero_for_one = True ✓
        builder.swap_exact_in_single(
            pool_key=pool_key,
            zero_for_one=True,  # ETH -> USDC
            amount_in=eth_amount_wei,
            amount_out_min=max(min_usdc_out, 100000)  # At least 0.1 USDC
        )
        builder.take_all(self.usdc_address, 0)
        
        try:
            v4_swap = builder.build_v4_swap()
            trx = v4_swap.build_transaction(
                self.account.address,
                eth_amount_wei,
                ur_address=self.universal_router_address,
                gas_limit=600000  # Increase gas limit
            )
            
            # Simulate first
            print("🔄 Simulating transaction...")
            self.w3.eth.call(trx)
            print("✅ Simulation passed!")
            
            # Send transaction
            signed = self.w3.eth.account.sign_transaction(trx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"📤 Transaction sent: {tx_hash.hex()}")
            print("⏳ Waiting for confirmation...")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                print(f"✅ SUCCESS! Gas used: {receipt.gasUsed}")
                return tx_hash
            else:
                print(f"❌ Transaction failed on-chain")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

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
        try:
            # Provide a conservative gas_limit to avoid RPC estimate_gas (which can revert during simulation)
            trx = v4_swap.build_transaction(
                self.account.address,
                0,
                ur_address=self.universal_router_address,
                gas_limit=500000
            )
        except Exception as e:
            print("❌ Error building transaction (did RPC simulation revert?):", str(e))
            traceback.print_exc()
            raise

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
