import pandas as pd
import requests
import time
import os
import json

#Get Hacker Data

# 1. Load your CSV (No Unix conversion here anymore!)
df = pd.read_csv('data/dune_pulls/normal_wallets.csv')

# Use environment variable for API key (more secure)
ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]


def get_pre_mixer_sequence(wallet_address, target_timestamp_str):
    """
    Fetches transactions starting from the wallet's creation and filters 
    for the 50 actions right BEFORE the mixer deposit.
    """
    # Updated to Etherscan API V2
    url = f"https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address={wallet_address}&startblock=0&endblock=99999999&page=1&offset=500&sort=asc&apikey={ETHERSCAN_API_KEY}"
    
    try:
        response = requests.get(url).json()
    except Exception as e:
        print(f"  -> API Error: {e}")
        return []
        
    if response.get('status') != '1':
        error_msg = response.get('message', 'Unknown error')
        error_result = response.get('result', '')
        print(f"  -> Etherscan Error: {error_msg}")
        if error_result:
            print(f"     Details: {error_result}")
        return [] 
        
    all_txs = response['result']
    
    # Handle timestamp with UTC suffix properly
    target_unix = int(pd.to_datetime(target_timestamp_str, utc=True).timestamp())
    
    # Filter out anything that happened AFTER they used the mixer
    prior_txs = all_txs
    
    # FIX 2: Grab the LAST 50 transactions from the filtered list (the ones closest to the deposit)
    sequence = prior_txs[-50:] 
    
    print(f"  -> Found {len(prior_txs)} total prior txs. Kept {len(sequence)} for sequence.")
    return sequence

# 2. The Extraction Loop
ml_dataset = []
attempts = 0

for index, row in df.iterrows(): # We remove .head() and let it read the whole file
    attempts += 1
    wallet = row['wallet']
    deposit_time_str = row['reference_time'] 
    
    print(f"Fetching history for {wallet}...")
    
    try:
        raw_sequence = get_pre_mixer_sequence(wallet, deposit_time_str)
        
        # Quality check: only keep wallets with more than 5 transactions
        if len(raw_sequence) > 5:
            ml_dataset.append({
                "wallet": wallet,
                "raw_history": raw_sequence,
                "label": 0 # 0 = Normal User
            })
            
            # --- THE BRAKE PEDAL ---
            # Once we hit exactly 26, we kill the loop.
            if len(ml_dataset) == 26:
                print("\n🎯 Target acquired! We have 26 normal sequences.")
                break 
                
    except Exception as e:
        print(f"  -> Error processing {wallet}: {e}")
        continue
        
    time.sleep(0.3) 

print(f"\nSuccessfully extracted {len(ml_dataset)} sequences!")
print(f"Total wallets attempted: {attempts}")
print(f"Success rate: {len(ml_dataset)}/{attempts}")

#3. Save the dataset to your PC
import json
output_file = 'data/raw_normal_sequences.json'
with open(output_file, 'w') as f:
    json.dump(ml_dataset, f, indent=4)

print(f"Data safely saved to {output_file}!")














# def get_pre_mixer_sequence(wallet_address, target_timestamp_str):
#     """
#     Fetches transactions starting from the wallet's creation and filters 
#     for the 50 actions right BEFORE the mixer deposit.
#     """
#     # Updated to Etherscan API V2
#     url = f"https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address={wallet_address}&startblock=0&endblock=99999999&page=1&offset=500&sort=asc&apikey={ETHERSCAN_API_KEY}"
    
#     try:
#         response = requests.get(url).json()
#     except Exception as e:
#         print(f"  -> API Error: {e}")
#         return []
        
#     if response.get('status') != '1':
#         error_msg = response.get('message', 'Unknown error')
#         error_result = response.get('result', '')
#         print(f"  -> Etherscan Error: {error_msg}")
#         if error_result:
#             print(f"     Details: {error_result}")
#         return [] 
        
#     all_txs = response['result']
    
#     # Handle timestamp with UTC suffix properly
#     target_unix = int(pd.to_datetime(target_timestamp_str, utc=True).timestamp())
    
#     # Filter out anything that happened AFTER they used the mixer
#     prior_txs = [tx for tx in all_txs if int(tx['timeStamp']) < target_unix]
    
#     # FIX 2: Grab the LAST 50 transactions from the filtered list (the ones closest to the deposit)
#     sequence = prior_txs[-50:] 
    
#     print(f"  -> Found {len(prior_txs)} total prior txs. Kept {len(sequence)} for sequence.")
#     return sequence

# # 2. The Extraction Loop
# ml_dataset = []

# for index, row in df.head(50).iterrows():
#     wallet = row['malicious_wallet']
#     # Passing the raw string directly
#     deposit_time_str = row['first_deposit_time'] 
    
#     print(f"Fetching history for {wallet}...")
    
#     try:
#         raw_sequence = get_pre_mixer_sequence(wallet, deposit_time_str)
        
#         if len(raw_sequence) > 5:
#             ml_dataset.append({
#                 "wallet": wallet,
#                 "raw_history": raw_sequence,
#                 "label": 1 # 1 = Launderer
#             })
#     except Exception as e:
#         print(f"  -> Error processing {wallet}: {e}")
#         continue
        
#     time.sleep(0.3)  # Respect API rate limits

# # 3. Save the dataset to your PC
# # output_file = 'data/raw_mixer_sequences.json'
# # with open(output_file, 'w') as f:
# #     json.dump(ml_dataset, f, indent=4)

# #print(f"Data safely saved to {output_file}!")
# print(f"\nSuccessfully extracted {len(ml_dataset)} sequences!")
# print(f"Total wallets processed: {len(df)}")
# print(f"Success rate: {len(ml_dataset)}/{len(df)}")
