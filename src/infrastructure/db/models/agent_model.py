from sqlalchemy import String, Enum as SQLEnum, DateTime, JSON, Text, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import List, Optional
from src.core.database import Base
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.value_objects.key_algorithm import KeyAlgorithm

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

class AgentModel(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_organization: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[AgentStatus] = mapped_column(
        SQLEnum(AgentStatus, name="agent_status_enum", native_enum=False),
        nullable=False,
        default=AgentStatus.ACTIVE,
        index=True
    )
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now_utc)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    public_keys: Mapped[List["PublicKeyModel"]] = relationship(
        "PublicKeyModel",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="joined"
    )

class PublicKeyModel(Base):
    __tablename__ = "public_keys"

    key_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    algorithm: Mapped[KeyAlgorithm] = mapped_column(
        SQLEnum(KeyAlgorithm, name="key_algorithm_enum", native_enum=False),
        nullable=False
    )
    pem_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now_utc)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped["AgentModel"] = relationship("AgentModel", back_populates="public_keys")

    __table_args__ = (
        CheckConstraint(
            "pem_content NOT LIKE '%PRIVATE KEY%' AND pem_content NOT LIKE '%RSA PRIVATE KEY%'",
            name="chk_no_private_key"
        ),
    )
