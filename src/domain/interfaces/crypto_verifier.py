from abc import ABC, abstractmethod
from src.domain.value_objects.key_algorithm import KeyAlgorithm

class CryptoVerifierInterface(ABC):
    
    @abstractmethod
    def assert_no_private_key(self, pem_content: str) -> None:
        """Inspects content and raises PrivateKeyDetectedException if private key indicators exist."""
        pass

    @abstractmethod
    def validate_public_key(self, pem_content: str, algorithm: KeyAlgorithm) -> bool:
        """Validates that the PEM string is a syntactically and cryptographically sound public key."""
        pass

    @abstractmethod
    def verify_signature(self, pem_content: str, message: bytes, signature: bytes) -> bool:
        """Verifies a digital signature against the provided public key PEM."""
        pass
