import re
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, ec, padding
from cryptography.exceptions import InvalidSignature
from src.domain.interfaces.crypto_verifier import CryptoVerifierInterface
from src.domain.value_objects.key_algorithm import KeyAlgorithm
from src.domain.exceptions import InvalidPublicKeyException, PrivateKeyDetectedException

PRIVATE_KEY_PATTERNS = [
    r"-----BEGIN[ A-Z]*PRIVATE KEY-----",
    r"-----BEGIN RSA PRIVATE KEY-----",
    r"-----BEGIN EC PRIVATE KEY-----",
    r"-----BEGIN OPENSSH PRIVATE KEY-----",
    r"PRIVATE KEY",
]

class PyCAKeyVerifierService(CryptoVerifierInterface):

    def assert_no_private_key(self, pem_content: str) -> None:
        # 1. Regex Keyword Pattern Check
        for pattern in PRIVATE_KEY_PATTERNS:
            if re.search(pattern, pem_content, re.IGNORECASE):
                raise PrivateKeyDetectedException()

        # 2. Cryptographic Loader Attempt (Must fail if private key is passed)
        try:
            serialization.load_pem_private_key(pem_content.encode('utf-8'), password=None)
            # If load_pem_private_key DOES NOT raise an error, a private key was submitted!
            raise PrivateKeyDetectedException()
        except ValueError:
            # Expected exception when content is NOT a private key
            pass

    def validate_public_key(self, pem_content: str, algorithm: KeyAlgorithm) -> bool:
        try:
            public_key = serialization.load_pem_public_key(pem_content.encode('utf-8'))

            if algorithm == KeyAlgorithm.ED25519:
                if not isinstance(public_key, ed25519.Ed25519PublicKey):
                    raise InvalidPublicKeyException("Key content does not match Ed25519 algorithm.")
            elif algorithm == KeyAlgorithm.RSA_4096:
                if not isinstance(public_key, rsa.RSAPublicKey):
                    raise InvalidPublicKeyException("Key content does not match RSA algorithm.")
                if public_key.key_size < 2048:
                    raise InvalidPublicKeyException(f"RSA key size ({public_key.key_size}) is below minimum allowed size.")
            elif algorithm in (KeyAlgorithm.ECDSA_P256, KeyAlgorithm.SECP256K1):
                if not isinstance(public_key, ec.EllipticCurvePublicKey):
                    raise InvalidPublicKeyException("Key content does not match EC algorithm.")
            return True
        except Exception as e:
            if isinstance(e, InvalidPublicKeyException):
                raise
            raise InvalidPublicKeyException(str(e))

    def verify_signature(self, pem_content: str, message: bytes, signature: bytes) -> bool:
        try:
            public_key = serialization.load_pem_public_key(pem_content.encode('utf-8'))
            
            if isinstance(public_key, ed25519.Ed25519PublicKey):
                public_key.verify(signature, message)
                return True
            elif isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    signature,
                    message,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                return True
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(
                    signature,
                    message,
                    ec.ECDSA(hashes.SHA256())
                )
                return True
            return False
        except InvalidSignature:
            return False
        except Exception as e:
            raise InvalidPublicKeyException(f"Failed to execute signature verification: {str(e)}")
