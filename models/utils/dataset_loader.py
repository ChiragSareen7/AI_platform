from __future__ import annotations

import pandas as pd
from datasets import Dataset


def _read_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def build_qa_from_plain(df: pd.DataFrame) -> pd.DataFrame:
    cols = set(df.columns)
    if "question" in cols and "answer" in cols:
        out = df[["question", "answer"]].copy()
    elif "q" in cols and "a" in cols:
        out = df.rename(columns={"q": "question", "a": "answer"})[["question", "answer"]]
    else:
        raise ValueError(f"Expected question/answer columns, got: {list(df.columns)}")
    out = out.dropna()
    out["input_text"] = out["question"].astype(str).str.strip()
    out["target_text"] = out["answer"].astype(str).str.strip()
    return out


def build_qa_organic(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize_columns(df)
    name_col = next((c for c in df.columns if "compound" in c or "name" in c), df.columns[0])
    prop_cols = [c for c in df.columns if c != name_col]
    rows = []
    for _, row in df.iterrows():
        name = str(row.get(name_col, "")).strip()
        if not name:
            continue
        parts = [f"{c}: {row[c]}" for c in prop_cols if pd.notna(row.get(c))]
        ans = "; ".join(parts) if parts else ""
        q = f"What are the properties of {name}?"
        rows.append({"input_text": q, "target_text": ans})
    return pd.DataFrame(rows)


def build_qa_gita(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize_columns(df)
    rows = []
    for _, row in df.iterrows():
        ch = row.get("chapter", row.get("ch", ""))
        vs = row.get("verse", row.get("v", ""))
        trans = row.get("translation", row.get("english", ""))
        expl = row.get("explanation", row.get("commentary", ""))
        q = f"Chapter {ch} Verse {vs}: explain the teaching."
        a = f"Translation: {trans}. Explanation: {expl}"
        rows.append({"input_text": str(q).strip(), "target_text": str(a).strip()})
    return pd.DataFrame(rows)


def load_qa_csv(path: str, kind: str) -> Dataset:
    df = _read_csv(path)
    df = _normalize_columns(df)
    if kind == "python":
        qa = build_qa_from_plain(df)
    elif kind == "organic":
        qa = build_qa_organic(df)
    elif kind == "gita":
        qa = build_qa_gita(df)
    else:
        raise ValueError(f"Unknown kind: {kind}")
    return Dataset.from_pandas(qa[["input_text", "target_text"]])


def split_dataset(ds: Dataset, test_ratio: float = 0.2, seed: int = 42):
    return ds.train_test_split(test_size=test_ratio, seed=seed)
