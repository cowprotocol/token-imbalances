# token-imbalances

This script is to calculate the raw token imbalances before and after a settlement.
The raw token imbalances are stored in the raw_token_imbalances table.
Additionally, coingecko prices for fetchable token addresses at the time of transaction are stored in the coingecko_prices table. These tables are a part of the Solver Slippage Database.
These prices can be used to convert raw imbalances to ETH.


**Install requirements from root directory:**
```bash
pip install -r requirements.txt
```

**Environment Variables**: Make sure the `.env` file is correctly set up locally. You can use the `.env.sample` file as reference.

**To fetch imbalances for a single transaction hash, run:**
```bash
python -m src.imbalances_script
```

**To run a daemon for checking imbalances, run the following from the root directory:**

```bash
python -m src.daemon
```

**To run the basic test in the `tests/` folder:**
 using pytest, simply run the command: `pytest` 