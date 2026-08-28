from enum import Enum

class KeyAlgorithm(str, Enum):
    ED25519 = "ED25519"
    ECDSA_P256 = "ECDSA_P256"
    RSA_4096 = "RSA_4096"
    SECP256K1 = "SECP256K1"
