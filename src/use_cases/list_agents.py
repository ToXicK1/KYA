from typing import List, Optional
from src.domain.entities.agent import Agent
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.interfaces.repositories import AgentRepositoryInterface

class ListAgentsUseCase:
    def __init__(self, repository: AgentRepositoryInterface):
        self._repository = repository

    async def execute(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[AgentStatus] = None,
        owner_organization: Optional[str] = None
    ) -> List[Agent]:
        return await self._repository.list(
            limit=limit,
            offset=offset,
            status=status,
            owner_organization=owner_organization
        )
