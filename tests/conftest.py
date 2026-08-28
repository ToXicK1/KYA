import pytest
import pytest_asyncio
import base64
from typing import AsyncGenerator, Dict, Any, Tuple
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, ec
from cryptography.hazmat.primitives import serialization

from src.main import app
from src.core.database import Base, get_db_session
from src.core.security import create_access_token
from src.domain.value_objects.key_algorithm import KeyAlgorithm

# In-Memory SQLite Engine for Integration Testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def async_client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db_session] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

# --- CRYPTOGRAPHIC KEY FIXTURES ---

@pytest.fixture(scope="session")
def ed25519_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    return pub_pem, priv_pem, priv, pub

@pytest.fixture(scope="session")
def rsa_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    return pub_pem, priv_pem, priv, pub

@pytest.fixture(scope="session")
def ecdsa_keypair():
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    return pub_pem, priv_pem, priv, pub

@pytest.fixture(scope="session")
def rsa_short_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    return pub_pem, priv_pem, priv, pub

@pytest.fixture(scope="session")
def ecdsa_secp256k1_keypair():
    priv = ec.generate_private_key(ec.SECP256K1())
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    return pub_pem, priv_pem, priv, pub

# --- AUTH FIXTURES ---

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    token = create_access_token(
        data={"sub": "test_admin", "org": "org_google_cloud", "roles": ["kya_admin"]}
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_invalid_sub() -> Dict[str, str]:
    token = create_access_token(
        data={"sub": "", "org": "org_google_cloud", "roles": ["kya_admin"]}
    )
    return {"Authorization": f"Bearer {token}"}

# --- PAYLOAD DATA FIXTURES ---

@pytest.fixture
def valid_agent_payload(ed25519_keypair) -> Dict[str, Any]:
    pub_pem, _, _, _ = ed25519_keypair
    return {
        "name": "Autonomous Settlement Agent",
        "version": "1.0.0",
        "description": "Cross-ledger financial reconciliation bot",
        "owner_organization": "org_google_finance",
        "capabilities": ["ledger_read", "payment_settle"],
        "endpoints": ["https://agent.finance.google.com/api/v1"],
        "operational_bounds": {"max_tx_usd": 1000000},
        "public_keys": [
            {
                "algorithm": "ED25519",
                "pem_content": pub_pem
            }
        ]
    }

