from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import hashlib
from src.domain.value_objects.key_algorithm import KeyAlgorithm

@dataclass
class PublicKey:
    key_id: str
    algorithm: KeyAlgorithm
    pem_content: str
    created_at: datetime
    is_active: bool = True
    expires_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        algorithm: KeyAlgorithm,
        pem_content: str,
        expires_at: Optional[datetime] = None
    ) -> "PublicKey":
        # Generate canonical fingerprint hash for key_id
        clean_pem = pem_content.strip()
        fingerprint = hashlib.sha256(clean_pem.encode('utf-8')).hexdigest()
        
        return cls(
            key_id=fingerprint,
            algorithm=algorithm,
            pem_content=clean_pem,
            created_at=datetime.now(timezone.utc),
            is_active=True,
            expires_at=expires_at
        )

