export type PolicyDecision = "DELIVER" | "RETRY" | "ESCALATE" | "BLOCK";

export type ScoreCard = {
  accuracy: number;
  hallucination: number;
  relevance: number;
  groundedness: number;
  confidence: number;
  lexical: number;
  semantic: number;
  latency_ms: number;
  tokens: number;
  overall: number;
};

