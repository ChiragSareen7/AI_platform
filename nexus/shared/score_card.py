from dataclasses import dataclass


@dataclass
class ScoreCard:
    accuracy: float
    hallucination: float
    relevance: float
    groundedness: float
    confidence: float
    lexical: float
    semantic: float
    latency_ms: int
    tokens: int
    overall: float

