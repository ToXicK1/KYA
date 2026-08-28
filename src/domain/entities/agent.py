from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from src.domain.value_objects.agent_id import AgentId
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.entities.manifest import AgentManifest
from src.domain.entities.public_key import PublicKey
from src.domain.exceptions import InvalidAgentStatusException

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

@dataclass
class Agent:
    id: AgentId
    manifest: AgentManifest
    public_keys: List[PublicKey]
    owner_organization: str
    status: AgentStatus = AgentStatus.ACTIVE
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    @classmethod
    def register(
        cls,
        manifest: AgentManifest,
        public_keys: List[PublicKey],
        agent_id: Optional[AgentId] = None
    ) -> "Agent":
        actual_id = agent_id or AgentId.generate()
        now = datetime.now(timezone.utc)
        return cls(
            id=actual_id,
            manifest=manifest,
            public_keys=public_keys,
            owner_organization=manifest.owner_organization,
            status=AgentStatus.ACTIVE,
            created_at=now,
            updated_at=now
        )

    def suspend(self):
        if self.status == AgentStatus.REVOKED:
            raise InvalidAgentStatusException(self.status.value, AgentStatus.SUSPENDED.value)
        self.status = AgentStatus.SUSPENDED
        self.updated_at = datetime.now(timezone.utc)

    def revoke(self):
        self.status = AgentStatus.REVOKED
        self.updated_at = datetime.now(timezone.utc)
        for pk in self.public_keys:
            pk.is_active = False

    def activate(self):
        if self.status == AgentStatus.REVOKED:
            raise InvalidAgentStatusException(self.status.value, AgentStatus.ACTIVE.value)
        self.status = AgentStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)

