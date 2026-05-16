from enum import Enum


class PolicyDecision(str, Enum):
    DELIVER = "DELIVER"
    RETRY = "RETRY"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"

