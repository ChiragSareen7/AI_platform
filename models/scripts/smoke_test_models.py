"""
POST smoke tests for /python, /organic, /gita (loads all three models like the API).
Run from repo: python models/scripts/smoke_test_models.py
Or: cd models && python scripts/smoke_test_models.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# models/ on sys.path so `import api.main` works
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402


def main() -> None:
    cases = [
        (
            "/python",
            "What is a list comprehension in Python?",
        ),
        (
            "/organic",
            "What are the properties of benzene?",
        ),
        (
            "/gita",
            "What does Krishna say about duty in chapter 2?",
        ),
    ]
    # Context manager required so startup loads models into MODEL_REGISTRY.
    with TestClient(app) as client:
        for path, query in cases:
            r = client.post(path, json={"query": query})
            assert r.status_code == 200, f"{path}: {r.status_code} {r.text}"
            data = r.json()
            assert "answer" in data and data["answer"].strip(), f"{path}: empty answer: {data}"
            assert data.get("model") == path.strip("/"), data
            preview = data["answer"][:200].replace("\n", " ")
            print(f"OK {path} -> ({len(data['answer'])} chars) {preview!r}...")

        r = client.post("/ask", json={"query": "Explain benzene toxicity and solubility."})
        assert r.status_code == 200, r.text
        routed = r.json()
        assert routed.get("model") == "organic", routed
        print(f"OK /ask (routed organic) -> model={routed['model']}")


if __name__ == "__main__":
    main()
    print("All smoke tests passed.")
