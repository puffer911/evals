"""
ABI definitions for Uniswap V4 and related contracts
"""

POOL_MANAGER_ABI = [
    {
        "inputs": [
            {"name": "key", "type": "tuple", "components": [
                {"name": "currency0", "type": "address"},
                {"name": "currency1", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "tickSpacing", "type": "int24"},
                {"name": "hooks", "type": "address"}
            ]},
            {"name": "params", "type": "tuple", "components": [
                {"name": "zeroForOne", "type": "bool"},
                {"name": "amountSpecified", "type": "int256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ]},
            {"name": "data", "type": "bytes"}
        ],
        "name": "swap",
        "outputs": [{"name": "", "type": "int256"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "key", "type": "tuple", "components": [
                {"name": "currency0", "type": "address"},
                {"name": "currency1", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "tickSpacing", "type": "int24"},
                {"name": "hooks", "type": "address"}
            ]}
        ],
        "name": "getSlot0",
        "outputs": [
            {"name": "sqrtPriceX96", "type": "uint160"},
            {"name": "tick", "type": "int24"},
            {"name": "protocolFee", "type": "uint24"},
            {"name": "hookFee", "type": "uint24"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"}
]
