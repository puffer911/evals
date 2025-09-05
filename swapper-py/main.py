"""
Uniswap Universal Router Swapper - Entry Point for Base Network V4
"""

import sys
from uniswap_swapper import UniversalRouterSwapper, interactive_swap

def main():
    print("🚀 Starting Uniswap Universal Router Swapper for Base Network V4...")

    try:
        swapper = UniversalRouterSwapper()
        print("✅ Connected to Ethereum network")
        interactive_swap(swapper)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nMake sure you have:")
        print("1. Set up your .env file with RPC_URL, PRIVATE_KEY, UNIVERSAL_ROUTER_ADDRESS, and USDC_ADDRESS")
        print("2. Use Base Network RPC URL (e.g., https://mainnet.base.org)")
        print("3. Have sufficient ETH for gas fees")
        sys.exit(1)

if __name__ == "__main__":
    main()
