from __future__ import annotations

import os

import torch
from datasets import Dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)


def tokenize_seq2seq(
    examples: dict,
    tokenizer,
    max_input_length: int,
    max_target_length: int,
):
    model_inputs = tokenizer(
        examples["input_text"],
        max_length=max_input_length,
        truncation=True,
        padding=False,
    )
    labels = tokenizer(
        examples["target_text"],
        max_length=max_target_length,
        truncation=True,
        padding=False,
    )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


def train_model(
    base_model: str,
    train_ds: Dataset,
    eval_ds: Dataset | None,
    save_path: str,
    epochs: int = 3,
    learning_rate: float = 3e-5,
    batch_size: int = 8,
    max_input_length: int = 256,
    max_target_length: int = 256,
) -> None:
    os.makedirs(save_path, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSeq2SeqLM.from_pretrained(base_model)

    def _tok(batch):
        return tokenize_seq2seq(batch, tokenizer, max_input_length, max_target_length)

    train_tok = train_ds.map(_tok, batched=True, remove_columns=train_ds.column_names)
    eval_tok = None
    if eval_ds is not None:
        eval_tok = eval_ds.map(_tok, batched=True, remove_columns=eval_ds.column_names)

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)
    args = Seq2SeqTrainingArguments(
        output_dir=os.path.join(save_path, "checkpoints"),
        eval_strategy="epoch" if eval_tok else "no",
        save_strategy="epoch",
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=epochs,
        weight_decay=0.01,
        logging_steps=50,
        load_best_model_at_end=bool(eval_tok),
        predict_with_generate=True,
        save_total_limit=2,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=train_tok,
        eval_dataset=eval_tok,
        processing_class=tokenizer,
        data_collator=data_collator,
    )
    trainer.train()
    trainer.save_model(save_path)
    tokenizer.save_pretrained(save_path)
