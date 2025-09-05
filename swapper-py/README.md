# Uniswap V4 ETH/USDC Swapper

A Python script for swapping ETH to USDC and vice versa using Uniswap V4 protocol.

## Features

- Swap ETH to USDC
- Swap USDC to ETH
- Web3.py integration
- Environment-based configuration
- Transaction monitoring

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

3. Configure your environment variables (all REQUIRED):
- `RPC_URL`: Your Ethereum RPC endpoint (Infura, Alchemy, etc.)
- `PRIVATE_KEY`: Your wallet's private key (NEVER commit this!)
- `POOL_MANAGER_ADDRESS`: Uniswap V4 PoolManager contract (**must be checksummed!**)
- `USDC_ADDRESS`: USDC contract address (**must be checksummed!**)

## ⚠️ **Important: Checksummed Addresses Required**

**All contract addresses must be checksummed** (proper casing) to work with web3.py:

### **To checksum an address:**
```python
from web3 import Web3
w3 = Web3()
checksummed = w3.to_checksum_address("0x498581ff718922c3f8e6a244956af099b2652b2b")
print(checksummed)  # 0x498581fF718922c3f8e6A244956AF099B2652b2b
```

### **Network-Specific Addresses:**

**Base Network:**
- PoolManager: `0x498581fF718922c3f8e6A244956AF099B2652b2b`
- USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- RPC: `https://mainnet.base.org`

**Ethereum Mainnet:**
- PoolManager: `0x000000000004444c5dC75cB358380D2e3dE08A90`
- USDC: `0xA0b86a33E6441e88C5F2712C3E9b74F5F0e3f0a8`
- RPC: `https://mainnet.infura.io/v3/YOUR_PROJECT_ID`

## Contract Address Explanation

### POOL_MANAGER_ADDRESS vs ETH_USDC_POOL

**POOL_MANAGER_ADDRESS** (Required):
- The main Uniswap V4 contract that manages all liquidity pools
- Used for all swap operations
- Single contract that handles routing to specific pools

**ETH_USDC_POOL** (Optional):
- Specific pool identifier for the ETH/USDC trading pair
- If not provided, the system constructs pool keys dynamically
- Current implementation uses PoolManager with dynamic pool discovery (recommended)

### Do We Need a Specific ETH/USDC Pool?

**NO** - The current implementation does NOT require a specific pool ID!

The implementation uses the **PoolManager approach**:
- ✅ **Dynamic Pool Discovery**: Constructs pool keys based on token addresses
- ✅ **Automatic Routing**: PoolManager finds/creates appropriate pools
- ✅ **No Hardcoded IDs**: Works without knowing specific pool addresses
- ✅ **Production Ready**: More flexible and maintainable

**How it works:**
1. We provide token addresses (ETH + USDC)
2. PoolManager constructs the pool key dynamically
3. PoolManager handles finding or creating the appropriate pool
4. Swap executes through the discovered pool

**ETH_USDC_POOL** is optional and currently unused in the implementation.

This is the **recommended production approach** for Uniswap V4!

## Usage

### Interactive Mode (Recommended)

```bash
python main.py
```

This launches an interactive menu with options to:
- Display current balances and allowances
- Swap ETH to USDC
- Swap USDC to ETH
- Exit

### Command Line Mode

```bash
# Swap 0.1 ETH to USDC
python main.py eth_to_usdc 0.1

# Swap 100 USDC to ETH
python main.py usdc_to_eth 100
```

### Python API

```python
from uniswap_swapper import UniswapV4Swapper

swapper = UniswapV4Swapper()

# Swap ETH to USDC
eth_amount_wei = swapper.w3.to_wei(0.1, 'ether')
tx_hash = swapper.swap_eth_to_usdc(eth_amount_wei)

# Swap USDC to ETH
usdc_amount = 100 * 10**6  # USDC has 6 decimals
tx_hash = swapper.swap_usdc_to_eth(usdc_amount)
```

## Important Notes

⚠️ **This is a simplified implementation for educational purposes.**

For production use with Uniswap V4, you would need:

- **Pool Discovery**: Find the correct pool ID for WETH/USDC pairs
- **Fee Tiers**: Determine appropriate fee tiers (0.05%, 0.3%, 1%)
- **Tick Spacing**: Calculate correct tick spacing for the pool
- **Price Limits**: Implement proper sqrtPriceLimitX96 calculations
- **Hooks**: Handle any custom hooks if present
- **Slippage Protection**: Add minimum output amounts
- **Gas Optimization**: Optimize gas usage

## Security

- Never commit your `.env` file or private keys to version control
- Test on testnets (Sepolia, Goerli) before mainnet
- Use hardware wallets for significant amounts
- Implement proper error handling and logging

## Dependencies

- web3==6.0.0
- python-dotenv==1.0.0
- eth-account==0.8.0

## License

MIT License
