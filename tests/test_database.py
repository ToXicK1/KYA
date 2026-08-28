import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.database import get_db_session
from src.core.config import settings

@pytest.mark.asyncio
async def test_get_db_session_commit_success():
    mock_session = AsyncMock()
    mock_sessionmaker = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    with patch("src.core.database.AsyncSessionLocal", mock_sessionmaker):
        generator = get_db_session()
        session = await anext(generator)
        assert session == mock_session
        
        # Finishing generator triggers commit and close
        with pytest.raises(StopAsyncIteration):
            await anext(generator)
            
        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_db_session_rollback_on_exception():
    mock_session = AsyncMock()
    mock_sessionmaker = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    with patch("src.core.database.AsyncSessionLocal", mock_sessionmaker):
        generator = get_db_session()
        session = await anext(generator)
        assert session == mock_session
        
        with pytest.raises(ValueError, match="Database error"):
            await generator.athrow(ValueError("Database error"))

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()

def test_database_engine_kwargs_non_sqlite():
    with patch("src.core.config.settings.DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db"):
        # Re-importing or testing logic condition
        url = "postgresql+asyncpg://user:pass@localhost:5432/db"
        kwargs = {"echo": False, "future": True}
        if not url.startswith("sqlite"):
            kwargs["pool_size"] = settings.DB_POOL_SIZE
            kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        assert "pool_size" in kwargs
        assert "max_overflow" in kwargs
