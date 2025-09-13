# Uniswap V4 ETH to USDC Swapper for Base Network

This script swaps ETH for USDC on the Base mainnet using Uniswap V4. It is a fully functional implementation that connects to the Base network, checks balances, and executes a swap transaction.

## Features

-   **Uniswap V4 Integration**: Uses a simplified V4 ABI to perform swaps.
-   **Base Network**: Configured for the Base mainnet.
-   **Balance Checks**: Displays ETH and USDC balances before and after the swap.
-   **Error Handling**: Includes a try-except block to catch and report transaction errors.
-   **Environment-Friendly**: Uses a `.env` file to securely manage your RPC URL and private key.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd swapper-py2
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your environment variables:**
    -   Rename the `.env.example` file to `.env`.
    -   Open the `.env` file and add your Base RPC URL and wallet private key.

    ```env
    BASE_RPC_URL="https://mainnet.base.org"
    PRIVATE_KEY="YOUR_PRIVATE_KEY"
    ```

## Usage

Once you have completed the setup, you can run the script with the following command:

```bash
python main.py
```

The script will then connect to the Base network, display your initial balances, and attempt to swap 0.00025 ETH for USDC.
