from shared.constants import PolicyDecision


def decide(action: str, retry_count: int, max_retries: int = 2) -> PolicyDecision:
    upper = action.upper()
    if upper == "RETRY" and retry_count < max_retries:
        return PolicyDecision.RETRY
    if upper == "RETRY":
        return PolicyDecision.ESCALATE
    if upper == "ESCALATE":
        return PolicyDecision.ESCALATE
    if upper == "BLOCK":
        return PolicyDecision.BLOCK
    return PolicyDecision.DELIVER

