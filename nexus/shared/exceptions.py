class NexusException(Exception):
    pass


class PolicyViolationError(NexusException):
    pass


class UnauthorizedTenantError(NexusException):
    pass

