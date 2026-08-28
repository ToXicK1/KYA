from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from src.domain.entities.agent import Agent
from src.domain.entities.manifest import AgentManifest
from src.domain.entities.public_key import PublicKey
from src.domain.value_objects.agent_id import AgentId
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.interfaces.repositories import AgentRepositoryInterface
from src.infrastructure.db.models.agent_model import AgentModel, PublicKeyModel

class PostgresAgentRepository(AgentRepositoryInterface):
    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_domain(self, model: AgentModel) -> Agent:
        manifest = AgentManifest(
            name=model.manifest.get("name", ""),
            version=model.manifest.get("version", ""),
            description=model.manifest.get("description", ""),
            owner_organization=model.manifest.get("owner_organization", ""),
            capabilities=model.manifest.get("capabilities", []),
            endpoints=model.manifest.get("endpoints", []),
            operational_bounds=model.manifest.get("operational_bounds", {})
        )

        public_keys = [
            PublicKey(
                key_id=pk.key_id,
                algorithm=pk.algorithm,
                pem_content=pk.pem_content,
                created_at=pk.created_at,
                is_active=pk.is_active,
                expires_at=pk.expires_at
            ) for pk in model.public_keys
        ]

        return Agent(
            id=AgentId(value=model.id),
            manifest=manifest,
            public_keys=public_keys,
            owner_organization=model.owner_organization,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    async def save(self, agent: Agent) -> Agent:
        stmt = select(AgentModel).options(joinedload(AgentModel.public_keys)).where(AgentModel.id == agent.id.value)
        res = await self._session.execute(stmt)
        model = res.scalars().unique().one_or_none()

        manifest_dict = {
            "name": agent.manifest.name,
            "version": agent.manifest.version,
            "description": agent.manifest.description,
            "owner_organization": agent.manifest.owner_organization,
            "capabilities": agent.manifest.capabilities,
            "endpoints": agent.manifest.endpoints,
            "operational_bounds": agent.manifest.operational_bounds,
        }

        if not model:
            model = AgentModel(
                id=agent.id.value,
                owner_organization=agent.owner_organization,
                status=agent.status,
                manifest=manifest_dict,
                manifest_hash=agent.manifest.compute_hash(),
                created_at=agent.created_at,
                updated_at=agent.updated_at
            )
            self._session.add(model)
        else:
            model.owner_organization = agent.owner_organization
            model.status = agent.status
            model.manifest = manifest_dict
            model.manifest_hash = agent.manifest.compute_hash()
            model.updated_at = agent.updated_at

        # Sync public keys
        existing_pk_map = {pk.key_id: pk for pk in model.public_keys}
        for pk_domain in agent.public_keys:
            if pk_domain.key_id in existing_pk_map:
                existing_pk_map[pk_domain.key_id].is_active = pk_domain.is_active
            else:
                pk_model = PublicKeyModel(
                    key_id=pk_domain.key_id,
                    agent_id=agent.id.value,
                    algorithm=pk_domain.algorithm,
                    pem_content=pk_domain.pem_content,
                    is_active=pk_domain.is_active,
                    created_at=pk_domain.created_at,
                    expires_at=pk_domain.expires_at
                )
                self._session.add(pk_model)

        await self._session.flush()
        res = await self._session.execute(stmt)
        refreshed_model = res.scalars().unique().one()
        return self._to_domain(refreshed_model)

    async def get_by_id(self, agent_id: AgentId) -> Optional[Agent]:
        stmt = (
            select(AgentModel)
            .options(joinedload(AgentModel.public_keys))
            .where(
                AgentModel.id == agent_id.value,
                AgentModel.deleted_at.is_(None)
            )
        )
        res = await self._session.execute(stmt)
        model = res.scalars().unique().one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_key_id(self, key_id: str) -> Optional[Agent]:
        stmt = (
            select(AgentModel)
            .options(joinedload(AgentModel.public_keys))
            .join(PublicKeyModel, PublicKeyModel.agent_id == AgentModel.id)
            .where(
                PublicKeyModel.key_id == key_id,
                AgentModel.deleted_at.is_(None)
            )
        )
        res = await self._session.execute(stmt)
        model = res.scalars().unique().one_or_none()
        return self._to_domain(model) if model else None

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[AgentStatus] = None,
        owner_organization: Optional[str] = None
    ) -> List[Agent]:
        stmt = select(AgentModel).options(joinedload(AgentModel.public_keys)).where(AgentModel.deleted_at.is_(None))
        if status:
            stmt = stmt.where(AgentModel.status == status)
        if owner_organization:
            stmt = stmt.where(AgentModel.owner_organization == owner_organization)
        stmt = stmt.order_by(AgentModel.created_at.desc()).offset(offset).limit(limit)

        res = await self._session.execute(stmt)
        models = res.scalars().unique().all()
        return [self._to_domain(m) for m in models]

    async def update_status(self, agent_id: AgentId, status: AgentStatus) -> bool:
        agent = await self.get_by_id(agent_id)
        if not agent:
            return False
        agent.status = status
        await self.save(agent)
        return True
