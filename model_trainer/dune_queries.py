# Paste your Dune query IDs here.
# Format: "output_filename": query_id (integer)
# The script will fetch each query and save it as <output_filename>.csv
#
# To find a query ID: open your query on dune.com — the number in the URL is the ID.
# Example: https://dune.com/queries/123456 -> query ID is 6123456

QUERIES = {
    "tornado_cash_wallets": 0,   # Replace 0 with your Tornado Cash query ID
    "normal_wallets": 0,         # Replace 0 with your normal wallets query ID   # Replace 0 with your Uniswap normal activity query ID
}

# -------------------------------------------------------------------------
# REFERENCE QUERIES — paste these into Dune, save, and put the ID above
# -------------------------------------------------------------------------

# tornado_cash_wallets
# SELECT
#     depositor AS malicious_wallet,
#     MIN(block_time) AS first_deposit_time,
#     COUNT(*) AS total_deposits
# FROM tornado_cash.deposits
# WHERE blockchain = 'ethereum'
# GROUP BY depositor
# HAVING COUNT(*) > 1
# ORDER BY total_deposits DESC
# LIMIT 5000

# uniswap_wallets // Used for baseline wallets. 
# SELECT
#     tx_from AS normal_wallet,
#     MIN(block_time) AS first_swap_time,
#     COUNT(*) AS total_swaps
# FROM uniswap_v3_ethereum.trades
# GROUP BY tx_from
# HAVING COUNT(*) > 5
# ORDER BY total_swaps DESC
# LIMIT 5000