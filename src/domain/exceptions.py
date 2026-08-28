class DomainException(Exception):
    """Base domain exception."""
    pass

class AgentNotFoundException(DomainException):
    def __init__(self, agent_id: str):
        super().__init__(f"Agent with ID '{agent_id}' was not found.")

class AgentAlreadyExistsException(DomainException):
    def __init__(self, agent_id: str):
        super().__init__(f"Agent with ID '{agent_id}' already exists.")

class InvalidPublicKeyException(DomainException):
    def __init__(self, reason: str):
        super().__init__(f"Invalid public key provided: {reason}")

class PrivateKeyDetectedException(DomainException):
    def __init__(self):
        super().__init__("SECURITY ALERT: Private keys are strictly forbidden and rejected by KYA security policies.")

class InvalidAgentStatusException(DomainException):
    def __init__(self, current_status: str, target_status: str):
        super().__init__(f"Cannot transition agent status from '{current_status}' to '{target_status}'.")
