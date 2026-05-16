from shared.constants import PolicyDecision
from shared.score_card import ScoreCard

from governance.enforcement_gate import decide
from governance.rules_evaluator import evaluate_structured_rule, evaluate_text_rule


def evaluate_policies(
    score_card: ScoreCard,
    rules: list[dict],
    retry_count: int,
) -> tuple[PolicyDecision, str | None]:
    ordered = sorted(rules, key=lambda r: r.get("priority", 100))
    for rule in ordered:
        if not rule.get("is_active", True):
            continue
        matched = False
        if "dsl" in rule:
            matched, _ = evaluate_text_rule(str(rule["dsl"]), score_card)
        else:
            matched = evaluate_structured_rule(rule, score_card)
        if matched:
            decision = decide(str(rule.get("action", "DELIVER")), retry_count=retry_count, max_retries=2)
            return decision, str(rule.get("description", "policy matched"))
    return PolicyDecision.DELIVER, None

