import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from src.infrastructure.crypto.key_verifier_service import PyCAKeyVerifierService
from src.domain.value_objects.key_algorithm import KeyAlgorithm
from src.domain.exceptions import PrivateKeyDetectedException, InvalidPublicKeyException

def test_reject_ed25519_private_key(ed25519_keypair):
    _, priv_pem, _, _ = ed25519_keypair
    verifier = PyCAKeyVerifierService()
    with pytest.raises(PrivateKeyDetectedException):
        verifier.assert_no_private_key(priv_pem)

def test_reject_rsa_private_key(rsa_keypair):
    _, priv_pem, _, _ = rsa_keypair
    verifier = PyCAKeyVerifierService()
    with pytest.raises(PrivateKeyDetectedException):
        verifier.assert_no_private_key(priv_pem)

def test_reject_ecdsa_private_key(ecdsa_keypair):
    _, priv_pem, _, _ = ecdsa_keypair
    verifier = PyCAKeyVerifierService()
    with pytest.raises(PrivateKeyDetectedException):
        verifier.assert_no_private_key(priv_pem)

def test_validate_public_keys(ed25519_keypair, rsa_keypair, ecdsa_keypair):
    verifier = PyCAKeyVerifierService()
    ed_pub_pem, _, _, _ = ed25519_keypair
    rsa_pub_pem, _, _, _ = rsa_keypair
    ecdsa_pub_pem, _, _, _ = ecdsa_keypair

    # Valid
    assert verifier.validate_public_key(ed_pub_pem, KeyAlgorithm.ED25519) is True
    assert verifier.validate_public_key(rsa_pub_pem, KeyAlgorithm.RSA_4096) is True
    assert verifier.validate_public_key(ecdsa_pub_pem, KeyAlgorithm.ECDSA_P256) is True

def test_algorithm_mismatch_rejection(ed25519_keypair, rsa_keypair):
    verifier = PyCAKeyVerifierService()
    ed_pub_pem, _, _, _ = ed25519_keypair
    rsa_pub_pem, _, _, _ = rsa_keypair

    # Passing Ed25519 key but requesting RSA algorithm
    with pytest.raises(InvalidPublicKeyException, match="does not match RSA algorithm"):
        verifier.validate_public_key(ed_pub_pem, KeyAlgorithm.RSA_4096)

    # Passing RSA key but requesting Ed25519 algorithm
    with pytest.raises(InvalidPublicKeyException, match="does not match Ed25519 algorithm"):
        verifier.validate_public_key(rsa_pub_pem, KeyAlgorithm.ED25519)

def test_ed25519_signature_verification(ed25519_keypair):
    verifier = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = ed25519_keypair

    message = b"KYA Payment Authorization #5501"
    signature = priv_key.sign(message)

    # Valid signature
    assert verifier.verify_signature(pub_pem, message, signature) is True

    # Tampered message
    assert verifier.verify_signature(pub_pem, b"Tampered Message", signature) is False

def test_rsa_signature_verification(rsa_keypair):
    verifier = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = rsa_keypair

    message = b"KYA Contract Sign Payload"
    signature = priv_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    assert verifier.verify_signature(pub_pem, message, signature) is True
    assert verifier.verify_signature(pub_pem, b"Wrong payload", signature) is False

def test_ecdsa_signature_verification(ecdsa_keypair):
    verifier = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = ecdsa_keypair

    message = b"KYA Audit Telemetry Frame"
    signature = priv_key.sign(message, ec.ECDSA(hashes.SHA256()))

    assert verifier.verify_signature(pub_pem, message, signature) is True
    assert verifier.verify_signature(pub_pem, b"Bad Frame", signature) is False

def test_rsa_short_key_rejection(rsa_short_keypair):
    verifier = PyCAKeyVerifierService()
    pub_pem, _, _, _ = rsa_short_keypair
    with pytest.raises(InvalidPublicKeyException, match="below minimum allowed size"):
        verifier.validate_public_key(pub_pem, KeyAlgorithm.RSA_4096)

def test_ec_algorithm_mismatch(ed25519_keypair):
    verifier = PyCAKeyVerifierService()
    ed_pub_pem, _, _, _ = ed25519_keypair
    with pytest.raises(InvalidPublicKeyException, match="does not match EC algorithm"):
        verifier.validate_public_key(ed_pub_pem, KeyAlgorithm.ECDSA_P256)

def test_private_key_loader_fallback(ed25519_keypair):
    from unittest.mock import patch
    verifier = PyCAKeyVerifierService()
    _, priv_pem, _, _ = ed25519_keypair
    # Mock re.search to return None so regex check passes, testing load_pem_private_key fallback
    with patch("re.search", return_value=None):
        with pytest.raises(PrivateKeyDetectedException):
            verifier.assert_no_private_key(priv_pem)

def test_signature_verification_exception_handling():
    verifier = PyCAKeyVerifierService()
    # Invalid PEM string causing load_pem_public_key to raise ValueError
    invalid_pem = "-----BEGIN PUBLIC KEY-----\nINVALID_KEY_DATA\n-----END PUBLIC KEY-----"
    with pytest.raises(InvalidPublicKeyException, match="Failed to execute signature verification"):
        verifier.verify_signature(invalid_pem, b"message", b"sig")

def test_password_hashing():
    from src.core.security import get_password_hash, verify_password
    pwd = "testpass123"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpass", hashed) is False


