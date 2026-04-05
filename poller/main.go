package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

var (
	ALCHEMY_URL   = "https://eth-mainnet.g.alchemy.com/v2/" + os.Getenv("ALCHEMY_API_KEY")
	FASTAPI_URL   = "http://localhost:8000/predict"
	POLL_INTERVAL = 12 * time.Second
)

var WATCHED_CONTRACTS = map[string]string{
	// --- Mixers ---
	"0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": "Tornado Cash",
	"0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Railgun",

	// --- L2 Bridges ---
	"0x3ee18b2214aff97000d974cf647e7c347e8fa585": "Wormhole Bridge",
	"0x3014ca10b91cb3d0ad85fef7a3cb95bcac9c0f79": "Hop Protocol (ETH)",
	"0xabea9132b05a70803a4e85094fd0e1800777fbef": "zkSync Bridge",
	"0x49048044d57e1c92a77f79988d21fa8faf74e97e": "Base Bridge",
	"0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "Optimism Bridge",
	"0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f": "Arbitrum Bridge",

	// --- DEXes ---
	"0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
	"0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3 Router",
	"0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "SushiSwap Router",
	"0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x Exchange Proxy",
	"0x1111111254eeb25477b68fb85ed929f73a960582": "1inch V5 Router",
}

// --- STRUCTS ---

type AlchemyRequest struct {
	Jsonrpc string        `json:"jsonrpc"`
	Method  string        `json:"method"`
	Params  []interface{} `json:"params"`
	ID      int           `json:"id"`
}

type AlchemyBlockResponse struct {
	Result struct {
		Transactions []struct {
			From string `json:"from"`
			To   string `json:"to"`
		} `json:"transactions"`
	} `json:"result"`
}

type AlchemyTransferResponse struct {
	Result struct {
		Transfers []struct {
			Value    float64 `json:"value"`
			Asset    string  `json:"asset"`
			Category string  `json:"category"`
		} `json:"transfers"`
	} `json:"result"`
}

type FastAPIRequest struct {
	Sequence string `json:"sequence"`
}

type FastAPIResponse struct {
	Prediction string  `json:"prediction"`
	Confidence float64 `json:"confidence"`
}

// --- MAIN ---

func main() {
	fmt.Println("=== Wallet Fraud Detection ML - Poller Started ===")
	fmt.Printf("Watching %d contracts:\n", len(WATCHED_CONTRACTS))
	for addr, name := range WATCHED_CONTRACTS {
		fmt.Printf("  • %s (%s)\n", name, addr[:10]+"...")
	}
	fmt.Printf("Poll interval: %v\n\n", POLL_INTERVAL)

	for {
		fmt.Println("[POLL] Checking latest block...")
		suspects, err := pollBlock()
		if err != nil {
			fmt.Println("❌ Poll error:", err)
		} else {
			if len(suspects) == 0 {
				fmt.Println("✓ No suspicious activity detected")
			} else {
				fmt.Printf("🚨 Found %d suspect(s), analyzing...\n", len(suspects))
				for _, wallet := range suspects {
					go scoreWallet(wallet)
				}
			}
		}
		fmt.Printf("Sleeping %v...\n\n", POLL_INTERVAL)
		time.Sleep(POLL_INTERVAL)
	}
}

// --- POLL 1 ---

func pollBlock() ([]string, error) {
	payload := AlchemyRequest{
		Jsonrpc: "2.0",
		Method:  "eth_getBlockByNumber",
		Params:  []interface{}{"latest", true},
		ID:      1,
	}

	body, _ := json.Marshal(payload)
	fmt.Println("  → Fetching latest block from Alchemy...")
	resp, err := http.Post(ALCHEMY_URL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result AlchemyBlockResponse
	json.NewDecoder(resp.Body).Decode(&result)
	fmt.Printf("  → Block contains %d transactions\n", len(result.Result.Transactions))

	var suspects []string
	for _, tx := range result.Result.Transactions {
		if name, ok := WATCHED_CONTRACTS[tx.To]; ok {
			fmt.Printf("  🎯 WATCHLIST HIT: %s → %s (%s)\n", tx.From, tx.To, name)
			suspects = append(suspects, tx.From)
		}
	}
	return suspects, nil
}

// --- POLL 2 ---

func fetchWalletHistory(wallet string) (string, error) {
	fmt.Printf("  📜 Fetching transaction history for %s...\n", wallet)
	payload := AlchemyRequest{
		Jsonrpc: "2.0",
		Method:  "alchemy_getAssetTransfers",
		Params: []interface{}{
			map[string]interface{}{
				"fromAddress": wallet,
				"maxCount":    "0x32",
				"order":       "desc",
				"category":    []string{"external", "erc20", "internal"},
			},
		},
		ID: 1,
	}

	body, _ := json.Marshal(payload)
	resp, err := http.Post(ALCHEMY_URL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result AlchemyTransferResponse
	rawBody, _ := io.ReadAll(resp.Body)
	json.Unmarshal(rawBody, &result)

	fmt.Printf("  ✓ Found %d transfers\n", len(result.Result.Transfers))

	sequence := ""
	for _, tx := range result.Result.Transfers {
		token := tokenizeTx(tx.Category, tx.Value)
		sequence += token + " "
	}
	return sequence, nil
}

// --- TOKENIZER ---

func tokenizeTx(category string, value float64) string {
	methodToken := "<UNKNOWN>"
	switch category {
	case "erc20":
		methodToken = "<ERC20_TRANSFER>"
	case "external":
		methodToken = "<ETH_TRANSFER>"
	case "internal":
		methodToken = "<INTERNAL_TRANSFER>"
	}

	valToken := "<VAL_DUST>"
	if value > 1.0 {
		valToken = "<VAL_MID>"
	}
	if value > 100.0 {
		valToken = "<VAL_WHALE>"
	}

	return methodToken + "_" + valToken
}

// --- SCORE ---

func scoreWallet(wallet string) {
	fmt.Printf("\n🔍 Analyzing wallet: %s\n", wallet)
	sequence, err := fetchWalletHistory(wallet)
	if err != nil {
		fmt.Printf("  ❌ History fetch error for %s: %v\n", wallet, err)
		return
	}

	fmt.Printf("  🤖 Sending to AI model...\n")
	payload := FastAPIRequest{Sequence: sequence}
	body, _ := json.Marshal(payload)

	resp, err := http.Post(FASTAPI_URL, "application/json", bytes.NewBuffer(body))
	if err != nil {
		fmt.Printf("  ❌ FastAPI error for %s: %v\n", wallet, err)
		return
	}
	defer resp.Body.Close()

	var result FastAPIResponse
	json.NewDecoder(resp.Body).Decode(&result)

	fmt.Println("  " + strings.Repeat("=", 60))
	fmt.Printf("  🎯 WALLET: %s\n", wallet)
	fmt.Printf("  📊 VERDICT: %s (%.1f%% confidence)\n", result.Prediction, result.Confidence*100)
	fmt.Println("  " + strings.Repeat("=", 60))
}