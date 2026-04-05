import pandas as pd
from datasets import Dataset
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments

print("1. Loading and Merging Data...")
# Load your two CSVs
df_hackers = pd.read_csv('data/ml_training_data_hackers.csv') # Your 1s
df_normals = pd.read_csv('data/ml_training_data_normal.csv')   # Your 0s

# Combine them and shuffle the deck (random_state ensures the shuffle is reproducible)
df_full = pd.concat([df_hackers, df_normals]).sample(frac=1, random_state=42).reset_index(drop=True)
print(f"Total dataset size: {len(df_full)} wallets ({len(df_hackers)} hackers, {len(df_normals)} normal users)")

print("\n2. Initializing DistilRoBERTa...")
tokenizer = AutoTokenizer.from_pretrained("distilroberta-base")
model = AutoModelForSequenceClassification.from_pretrained("distilroberta-base", num_labels=2)

# Convert Pandas to Hugging Face Dataset format
hf_dataset = Dataset.from_pandas(df_full[['sequence', 'label']])

def tokenize_function(examples):
    # Padding and truncation ensure all mathematical tensors are the same length
    return tokenizer(examples["sequence"], padding="max_length", truncation=True, max_length=128)

print("3. Tokenizing sequences for the GPU...")
tokenized_datasets = hf_dataset.map(tokenize_function, batched=True)

# Split into 80% training data, 20% testing data
split_dataset = tokenized_datasets.train_test_split(test_size=0.2, seed=42)
train_dataset = split_dataset["train"]
eval_dataset = split_dataset["test"]

print("\n4. Setting up Training...")
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=5,           # Bumped to 5 loops for better accuracy on a small dataset
    per_device_train_batch_size=8,
    eval_strategy="epoch",        # Tests itself at the end of every loop
    logging_dir="./logs",
    logging_steps=5,
    learning_rate=2e-5            # A standard, safe learning rate for fine-tuning
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

print("\n5. Commencing Training...")
trainer.train()

print("\nSUCCESS! AI Model is fully trained.")

# Save your masterpiece to your hard drive
trainer.save_model("./fraud_detection_model")
tokenizer.save_pretrained("./fraud_detection_model")
print("Model safely saved to the './fraud_detection_model' directory.")