from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.agent import Agent
from src.domain.value_objects.agent_id import AgentId
from src.domain.value_objects.agent_status import AgentStatus

class AgentRepositoryInterface(ABC):

    @abstractmethod
    async def save(self, agent: Agent) -> Agent:
        """Saves an agent aggregate root (and its public keys)."""
        pass

    @abstractmethod
    async def get_by_id(self, agent_id: AgentId) -> Optional[Agent]:
        """Retrieves an agent by AgentId."""
        pass

    @abstractmethod
    async def get_by_key_id(self, key_id: str) -> Optional[Agent]:
        """Retrieves an agent associated with a public key fingerprint."""
        pass

    @abstractmethod
    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[AgentStatus] = None,
        owner_organization: Optional[str] = None
    ) -> List[Agent]:
        """Lists agents with optional filtering and pagination."""
        pass

    @abstractmethod
    async def update_status(self, agent_id: AgentId, status: AgentStatus) -> bool:
        """Updates agent status."""
        pass
