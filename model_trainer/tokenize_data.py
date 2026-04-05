import json
import pandas as pd

# 1. Load the raw JSON you just extracted
with open('data/ether_pulls/raw_normal_sequences.json', 'r') as f:
    raw_data = json.load(f)

def translate_transaction(tx):
    """Translates a raw JSON transaction into ML tokens."""
    
    # --- 1. DETERMINE MAGNITUDE ---
    # Convert Wei to ETH (1 ETH = 10^18 Wei)
    eth_value = int(tx['value']) / (10**18)
    
    if eth_value == 0:
        val_token = "<VAL_ZERO>"
    elif eth_value < 0.1:
        val_token = "<VAL_DUST>"
    elif eth_value < 10.0:
        val_token = "<VAL_MED>"
    else:
        val_token = "<VAL_WHALE>"

    # --- 2. DETERMINE ACTION ---
    func = tx['functionName'].lower()
    
    if func == "": 
        action_token = "<ETH_TRANSFER>"
    elif "swap" in func:
        action_token = "<DEX_SWAP>"
    elif "approve" in func:
        action_token = "<TOKEN_APPROVE>"
    elif "transfer" in func:
        action_token = "<TOKEN_TRANSFER>"
    elif "addliquidity" in func or "removeliquidity" in func:
        action_token = "<LIQUIDITY_EVENT>"
    elif "deposit" in func:
        action_token = "<DEPOSIT>"
    else:
        action_token = "<OTHER_CONTRACT_CALL>"

    # Return the translated "words"
    return f"{action_token} {val_token}"

# 2. Translate every wallet's history
ml_ready_data = []

for wallet_data in raw_data: # Speed run: This will just run on the wallets you have
    wallet = wallet_data['wallet']
    label = wallet_data['label']
    history = wallet_data['raw_history']
    
    # Translate each transaction in the sequence
    translated_sequence = [translate_transaction(tx) for tx in history]
    
    # Join the array into a single space-separated sentence
    final_sentence = " ".join(translated_sequence)
    
    ml_ready_data.append({
        "wallet": wallet,
        "sequence": final_sentence,
        "label": label
    })

# 3. Save as a super lightweight CSV
df = pd.DataFrame(ml_ready_data)
df.to_csv('data/ml_training_data_normal.csv', index=False)

print(f"Successfully tokenized {len(df)} sequences!")
print("\nExample Sentence:")
print(df['sequence'].iloc[0][:100] + "...") # Show a snippet of the first one