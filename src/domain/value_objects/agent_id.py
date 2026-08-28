from dataclasses import dataclass
import ulid

PREFIX = "kya_agt_"

@dataclass(frozen=True)
class AgentId:
    value: str

    def __post_init__(self):
        if not self.value.startswith(PREFIX):
            raise ValueError(f"AgentId must start with '{PREFIX}' prefix.")
        if len(self.value) < 16:
            raise ValueError("AgentId format is invalid.")

    @classmethod
    def generate(cls) -> "AgentId":
        new_ulid = ulid.new().str.lower()
        return cls(value=f"{PREFIX}{new_ulid}")

    def __str__(self) -> str:
        return self.value
