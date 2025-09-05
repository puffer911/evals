"""
Uniswap Universal Router Swapper - Entry Point
"""

import sys
from uniswap_swapper import UniversalRouterSwapper, interactive_swap

def main():
    print("🚀 Starting Uniswap Universal Router Swapper...")

    try:
        swapper = UniversalRouterSwapper()
        print("✅ Connected to Ethereum network")
        interactive_swap(swapper)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nMake sure you have:")
        print("1. Set up your .env file with RPC_URL and PRIVATE_KEY")
        print("2. Have sufficient ETH for gas fees")
        sys.exit(1)

if __name__ == "__main__":
    main()
