"""
Uniswap V4 ETH/USDC Swapper - CLI Entry Point
"""

import sys
from uniswap_swapper import UniswapV4Swapper, interactive_swap

def main():
    if len(sys.argv) == 1:
        # Interactive mode
        print("🚀 Starting Uniswap V4 ETH/USDC Swapper...")

        try:
            swapper = UniswapV4Swapper()
            print("✅ Connected to Ethereum network")

            # Start interactive mode
            interactive_swap(swapper)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("\nMake sure you have:")
            print("1. Set up your .env file with RPC_URL and PRIVATE_KEY")
            print("2. Have sufficient ETH for gas fees")

    elif len(sys.argv) == 3:
        # CLI mode
        direction = sys.argv[1]
        amount = float(sys.argv[2])

        try:
            swapper = UniswapV4Swapper()

            if direction == "eth_to_usdc":
                eth_amount_wei = swapper.w3.to_wei(amount, 'ether')
                tx_hash = swapper.swap_eth_to_usdc(eth_amount_wei)
                if tx_hash:
                    receipt = swapper.wait_for_transaction(tx_hash)
                    print(f"✅ Swap completed! Transaction: {receipt.transactionHash.hex()}")

            elif direction == "usdc_to_eth":
                # Assuming USDC has 6 decimals
                usdc_amount = int(amount * 10**6)
                tx_hash = swapper.swap_usdc_to_eth(usdc_amount)
                if tx_hash:
                    receipt = swapper.wait_for_transaction(tx_hash)
                    print(f"✅ Swap completed! Transaction: {receipt.transactionHash.hex()}")

            else:
                print("❌ Usage: python main.py [eth_to_usdc|usdc_to_eth] <amount>")
                print("   Or: python main.py (for interactive mode)")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

    else:
        print("❌ Usage:")
        print("   Interactive mode: python main.py")
        print("   CLI mode: python main.py [eth_to_usdc|usdc_to_eth] <amount>")

if __name__ == "__main__":
    main()
