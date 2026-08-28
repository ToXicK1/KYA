from src.domain.entities.agent import Agent
from src.domain.value_objects.agent_id import AgentId
from src.domain.interfaces.repositories import AgentRepositoryInterface
from src.domain.exceptions import AgentNotFoundException

class GetAgentUseCase:
    def __init__(self, repository: AgentRepositoryInterface):
        self._repository = repository

    async def execute(self, agent_id_str: str) -> Agent:
        agent_id = AgentId(value=agent_id_str)
        agent = await self._repository.get_by_id(agent_id)
        if not agent:
            raise AgentNotFoundException(agent_id_str)
        return agent
