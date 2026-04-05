import streamlit as st
import requests
import pandas as pd
import time
from collections import Counter

FASTAPI_URL = "http://localhost:8000"

st.set_page_config(page_title="Wallet Fraud Detection ML", layout="wide")
st.title("Wallet Fraud Detection ML")
st.caption("Real-time on-chain illicit activity detection — Polled by Go /poller, scored by FastAPI + DistilRoBERTa")

# --- Sidebar: Manual Test ---
st.sidebar.header("Manual Test")
test_sequence = st.sidebar.text_area("Paste a token sequence:", height=150,
    placeholder="<DEPOSIT> <VAL_ZERO> <DEX_SWAP> <VAL_WHALE> ...")

if st.sidebar.button("Run Prediction"):
    if test_sequence.strip():
        try:
            resp = requests.post(f"{FASTAPI_URL}/predict",
                                 json={"sequence": test_sequence}, timeout=10)
            data = resp.json()
            if data["prediction"] == "Fraudulent":
                st.sidebar.error(f"**FRAUDULENT ACTIVITY** ({data['confidence']*100:.1f}%)")
            else:
                st.sidebar.success(f"**Normal** ({data['confidence']*100:.1f}%)")
            st.sidebar.json(data)
        except requests.ConnectionError:
            st.sidebar.error("Cannot connect to FastAPI. Is it running?")
    else:
        st.sidebar.warning("Paste a sequence first")

# --- Health Check ---
col_health, col_stats = st.columns([1, 3])
with col_health:
    try:
        health = requests.get(f"{FASTAPI_URL}/health", timeout=5).json()
        st.metric("API Status", "Online")
        st.metric("Predictions Made", health["predictions_made"])
    except requests.ConnectionError:
        st.metric("API Status", "Offline")
        st.warning("FastAPI is not running. Start it with: `uvicorn fast_api:app --reload`")
        st.stop()

# --- Fetch History ---
try:
    history = requests.get(f"{FASTAPI_URL}/history", timeout=5).json()
except requests.ConnectionError:
    history = []

if not history:
    with col_stats:
        st.info("No predictions yet. Waiting for Go poller to send wallets...")
    st.stop()

df = pd.DataFrame(history)

# --- Summary Stats ---
with col_stats:
    c1, c2, c3, c4 = st.columns(4)
    total = len(df)
    fraudulent = len(df[df["prediction"] == "Fraudulent"])
    normals = len(df[df["prediction"] == "Normal"])
    avg_conf = df["confidence"].mean()
    c1.metric("Total Scanned", total)
    c2.metric("Fraudulent", fraudulent)
    c3.metric("Normal", normals)
    c4.metric("Avg Confidence", f"{avg_conf*100:.1f}%")

st.divider()

# --- Recent Predictions Feed ---
st.subheader("Live Prediction Feed")
st.caption("Wallets sent by Go poller → scored by AI model")

for _, row in df.iloc[::-1].head(20).iterrows():
    with st.container():
        cols = st.columns([2, 1, 1, 1])
        cols[0].text(row["timestamp"])
        if row["prediction"] == "Fraudulent":
            cols[1].error(row['prediction'])
        else:
            cols[1].success(row['prediction'])
        cols[2].metric("Confidence", f"{row['confidence']*100:.1f}%")
        cols[3].metric("P(Fraud)", f"{row['fraud_prob']*100:.1f}%")

st.divider()

# --- Model Internals: What the AI Sees ---
st.subheader("What the Model Sees")
st.caption("Token breakdown from the most recent prediction")

latest = df.iloc[-1]
tokens = latest["sequence"].split()

# Count token types
action_tokens = [t for t in tokens if not t.startswith("<VAL_")]
value_tokens = [t for t in tokens if t.startswith("<VAL_")]

col_seq, col_chart = st.columns([2, 1])

with col_seq:
    st.markdown("**Raw Token Sequence (truncated to model's 128 token window):**")
    display_tokens = tokens[:128]
    colored_parts = []
    for t in display_tokens:
        if "WHALE" in t:
            colored_parts.append(f":red[{t}]")
        elif "DEPOSIT" in t:
            colored_parts.append(f":orange[{t}]")
        elif "DEX_SWAP" in t:
            colored_parts.append(f":blue[{t}]")
        else:
            colored_parts.append(t)
    st.markdown(" ".join(colored_parts))
    st.caption(f"Total tokens: {len(tokens)} | Shown: {len(display_tokens)}")

with col_chart:
    st.markdown("**Action Distribution:**")
    action_counts = Counter(action_tokens)
    action_df = pd.DataFrame(action_counts.items(), columns=["Token", "Count"])
    action_df = action_df.sort_values("Count", ascending=False)
    st.bar_chart(action_df.set_index("Token"))

    st.markdown("**Value Distribution:**")
    val_counts = Counter(value_tokens)
    val_df = pd.DataFrame(val_counts.items(), columns=["Token", "Count"])
    val_df = val_df.sort_values("Count", ascending=False)
    st.bar_chart(val_df.set_index("Token"))

st.divider()

# --- Probability Breakdown ---
st.subheader("Model Probability (Latest)")
prob_col1, prob_col2 = st.columns(2)
with prob_col1:
    st.metric("P(Normal)", f"{latest['normal_prob']*100:.1f}%")
    st.progress(latest["normal_prob"])
with prob_col2:
    st.metric("P(Fraud)", f"{latest['fraud_prob']*100:.1f}%")
    st.progress(latest["fraud_prob"])

# --- Confidence Over Time ---
if len(df) > 1:
    st.subheader("Confidence Over Time")
    chart_df = df[["timestamp", "confidence", "prediction"]].copy()
    chart_df["confidence_pct"] = chart_df["confidence"] * 100
    st.line_chart(chart_df.set_index("timestamp")["confidence_pct"])

# --- Auto Refresh ---
st.divider()
auto_refresh = st.checkbox("Auto-refresh (every 15s)", value=False)
if auto_refresh:
    time.sleep(15)
    st.rerun()
