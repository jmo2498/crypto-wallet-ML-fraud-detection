from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from datetime import datetime
from collections import deque

app = FastAPI(title="Wallet Fraud Detection ML")

# Store last 100 predictions for the dashboard
prediction_log = deque(maxlen=100)

# Load model once at startup
print("🤖 Loading AI model...")
tokenizer = AutoTokenizer.from_pretrained("./fraud_detection_model")
model = AutoModelForSequenceClassification.from_pretrained("./fraud_detection_model")
model.eval()
print("✅ Model loaded and ready!\n")

class WalletRequest(BaseModel):
    sequence: str

@app.post("/predict")
def predict(request: WalletRequest):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] 📨 Prediction request received")
    print(f"  Sequence length: {len(request.sequence)} chars")
    
    inputs = tokenizer(request.sequence, return_tensors="pt", padding=True, truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
        prediction = torch.argmax(probs, dim=1).item()
        confidence = probs[0][prediction].item()
        normal_prob = round(probs[0][0].item(), 4)
        launderer_prob = round(probs[0][1].item(), 4)

    result = "Fraudulent" if prediction == 1 else "Normal"
    print(f"  🎯 Prediction: {result} ({confidence*100:.1f}% confidence)")

    entry = {
        "timestamp": timestamp,
        "sequence": request.sequence,
        "prediction": result,
        "confidence": round(confidence, 4),
        "normal_prob": normal_prob,
        "fraud_prob": launderer_prob,
    }
    prediction_log.append(entry)
    
    return {
        "prediction": result,
        "confidence": round(confidence, 4),
        "normal_prob": normal_prob,
        "fraud_prob": launderer_prob,
    }

@app.get("/history")
def get_history():
    return list(prediction_log)

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": True, "predictions_made": len(prediction_log)}