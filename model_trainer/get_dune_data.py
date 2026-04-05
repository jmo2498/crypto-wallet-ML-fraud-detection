import os
import pandas as pd
from dune_client.client import DuneClient
from dune_queries import QUERIES

DUNE_API_KEY = os.environ.get("DUNE_API_KEY")
if not DUNE_API_KEY:
    raise EnvironmentError("DUNE_API_KEY environment variable not set. See .env.example.")

dune = DuneClient(DUNE_API_KEY)

for query_name, query_id in QUERIES.items():
    print(f"Fetching '{query_name}' (query ID: {query_id})...")
    response = dune.get_latest_result(query_id)
    data = response.result.rows
    df = pd.DataFrame(data)
    file_name = f"{query_name}.csv"
    df.to_csv(file_name, index=False)
    print(f"  Exported {len(df)} rows to {file_name}")

print("Done.")