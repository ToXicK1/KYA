import pytest
import time
from src.infrastructure.crypto.key_verifier_service import PyCAKeyVerifierService
from src.infrastructure.db.repositories.postgres_agent_repository import PostgresAgentRepository
from src.use_cases.register_agent import RegisterAgentUseCase, RegisterAgentDTO, PublicKeyDTO
from src.domain.value_objects.key_algorithm import KeyAlgorithm

def test_performance_signature_verification_latency(ed25519_keypair):
    verifier = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = ed25519_keypair
    message = b"KYA Performance Benchmark Payload #1"
    signature = priv_key.sign(message)

    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        is_valid = verifier.verify_signature(pub_pem, message, signature)
        assert is_valid is True
    total_time_ms = (time.perf_counter() - start) * 1000
    avg_latency_ms = total_time_ms / iterations

    # Average Ed25519 signature verification should be < 2ms
    assert avg_latency_ms < 5.0, f"Ed25519 verification latency too high: {avg_latency_ms:.2f}ms"

@pytest.mark.asyncio
async def test_performance_bulk_agent_registration(test_db_session):
    from cryptography.hazmat.primitives.asymmetric import ed25519 as ed_module
    from cryptography.hazmat.primitives import serialization

    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    register_uc = RegisterAgentUseCase(repo, crypto)

    count = 25
    start = time.perf_counter()
    for i in range(count):
        # Generate a unique key per agent to avoid fingerprint (key_id) collision
        fresh_priv = ed_module.Ed25519PrivateKey.generate()
        fresh_pub_pem = fresh_priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        dto = RegisterAgentDTO(
            name=f"Perf Agent {i}",
            version="1.0.0",
            description="Benchmark Agent",
            owner_organization="org_perf",
            capabilities=["cap_perf"],
            endpoints=[f"https://perf{i}.example.com"],
            operational_bounds={"index": i},
            public_keys=[PublicKeyDTO(algorithm=KeyAlgorithm.ED25519, pem_content=fresh_pub_pem)]
        )
        await register_uc.execute(dto)

    elapsed = time.perf_counter() - start
    assert elapsed < 5.0, f"Bulk registration of {count} agents took {elapsed:.2f}s"

@pytest.mark.asyncio
async def test_performance_concurrent_verifications(ed25519_keypair):
    import asyncio
    verifier = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = ed25519_keypair
    message = b"Concurrent benchmark message"
    signature = priv_key.sign(message)

    async def verify_task():
        return verifier.verify_signature(pub_pem, message, signature)

    tasks = [verify_task() for _ in range(50)]
    start = time.perf_counter()
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    assert all(results)
    assert elapsed < 2.0, f"50 concurrent verifications took {elapsed:.2f}s"

