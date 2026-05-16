from shared.score_card import ScoreCard


def _compare(left: float, op: str, right: float) -> bool:
    if op == "gt":
        return left > right
    if op == "lt":
        return left < right
    if op == "gte":
        return left >= right
    if op == "lte":
        return left <= right
    return False


def evaluate_structured_rule(rule: dict, score_card: ScoreCard) -> bool:
    metric = rule.get("metric")
    op = rule.get("operator")
    threshold = float(rule.get("threshold", 0))
    value = float(getattr(score_card, metric, 0.0))
    return _compare(value, op, threshold)


def evaluate_text_rule(rule_text: str, score_card: ScoreCard) -> tuple[bool, dict]:
    # format: "hallucination gt 0.4 => BLOCK"
    tokens = [x.strip() for x in rule_text.split("=>", 1)[0].split(" ")]
    if len(tokens) < 3:
        return False, {}
    metric, operator, threshold = tokens[0], tokens[1], float(tokens[2])
    rule = {"metric": metric, "operator": operator, "threshold": threshold}
    return evaluate_structured_rule(rule, score_card), rule

