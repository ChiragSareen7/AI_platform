"""
Retrain all three domain models from CSVs using Flan-T5 (default: google/flan-t5-base; override BASE_MODEL).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import torch
from datasets import Dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "utils"))

from dataset_loader import _normalize_columns, _read_csv  # noqa: E402


def build_python_df() -> pd.DataFrame:
    p = ROOT / "faq_dataset.csv"
    df = _read_csv(str(p))
    df = _normalize_columns(df)
    if "question" not in df.columns or "answer" not in df.columns:
        raise ValueError("faq_dataset.csv needs question, answer columns")
    rows = []
    for _, r in df.iterrows():
        q = str(r["question"]).strip()
        a = str(r["answer"]).strip()
        inp = f"task: python_faq; question: {q}"
        rows.append({"input_text": inp, "target_text": a})
    return pd.DataFrame(rows)


def build_organic_df() -> pd.DataFrame:
    p = ROOT / "Organic_Compounds_Properties.csv"
    try:
        df = pd.read_csv(str(p), encoding="utf-8", skiprows=2)
    except UnicodeDecodeError:
        df = pd.read_csv(str(p), encoding="latin-1", skiprows=2)
    df = _normalize_columns(df)
    if "compound_name" in df.columns:
        name_col = "compound_name"
    else:
        name_col = next((c for c in df.columns if "compound" in c or "name" in c), df.columns[0])
    prop_cols = [c for c in df.columns if c != name_col]
    rows = []
    for _, r in df.iterrows():
        name = str(r.get(name_col, "")).strip()
        if not name:
            continue
        parts = [f"{c}: {r[c]}" for c in prop_cols if pd.notna(r.get(c))]
        props = "; ".join(parts)
        q = f"What are the properties of {name}?"
        inp = f"task: organic_props; question: {q}"
        rows.append({"input_text": inp, "target_text": props})
    return pd.DataFrame(rows)


def build_gita_df() -> pd.DataFrame:
    p = ROOT / "Bhagvad Gita.csv"
    df = _read_csv(str(p))
    df = _normalize_columns(df)
    rows = []
    for _, r in df.iterrows():
        ch = r.get("chapter_no", r.get("chapter", r.get("ch", "")))
        vs = r.get("verse_no", r.get("verse", r.get("v", "")))
        trans = r.get("english_translation", r.get("translation", r.get("english", "")))
        expl = r.get("explanation", r.get("commentary", ""))
        q = f"Chapter {ch} Verse {vs}: explain the teaching."
        a = f"Translation: {trans}. Explanation: {expl}"
        inp = f"task: gita_verse; question: {q}"
        rows.append({"input_text": inp, "target_text": str(a).strip()})
    return pd.DataFrame(rows)


def _tokenize(batch, tokenizer, max_in: int, max_out: int):
    enc = tokenizer(batch["input_text"], truncation=True, max_length=max_in, padding=False)
    lab = tokenizer(batch["target_text"], truncation=True, max_length=max_out, padding=False)
    enc["labels"] = lab["input_ids"]
    return enc


def _load_start_model(path: Path, base: str):
    if path.exists() and (path / "config.json").exists():
        try:
            tok = AutoTokenizer.from_pretrained(str(path))
            model = AutoModelForSeq2SeqLM.from_pretrained(str(path))
            return tok, model
        except Exception:
            pass
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForSeq2SeqLM.from_pretrained(base)
    return tok, model


def _train(name: str, df: pd.DataFrame, out_dir: Path, epochs: int, lr: float, bs: int, max_in: int, max_out: int):
    ds = Dataset.from_pandas(df)
    split = ds.train_test_split(test_size=0.2, seed=42)
    base = os.getenv("BASE_MODEL", "google/flan-t5-base")
    tok, model = _load_start_model(out_dir, base)

    def tok_map(batch):
        return _tokenize(batch, tok, max_in, max_out)

    tr = split["train"].map(tok_map, batched=True, remove_columns=split["train"].column_names)
    ev = split["test"].map(tok_map, batched=True, remove_columns=split["test"].column_names)
    collator = DataCollatorForSeq2Seq(tok, model=model)
    args = Seq2SeqTrainingArguments(
        output_dir=str(out_dir / "checkpoints"),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=lr,
        per_device_train_batch_size=bs,
        per_device_eval_batch_size=bs,
        num_train_epochs=epochs,
        weight_decay=0.01,
        logging_steps=30,
        load_best_model_at_end=True,
        predict_with_generate=True,
        save_total_limit=2,
        use_cpu=True,
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=tr,
        eval_dataset=ev,
        processing_class=tok,
        data_collator=collator,
    )
    trainer.train()
    trainer.save_model(str(out_dir))
    tok.save_pretrained(str(out_dir))


def main() -> None:
    device = torch.device("cpu")
    print(f"Using device: {device}")
    _train("python", build_python_df(), ROOT / "python_model", epochs=5, lr=3e-5, bs=8, max_in=256, max_out=256)
    _train("organic", build_organic_df(), ROOT / "organic_model", epochs=4, lr=3e-5, bs=8, max_in=256, max_out=256)
    _train("gita", build_gita_df(), ROOT / "gita_model", epochs=5, lr=1e-4, bs=8, max_in=196, max_out=220)


if __name__ == "__main__":
    main()
