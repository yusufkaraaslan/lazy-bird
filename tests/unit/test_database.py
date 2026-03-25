"""Unit tests for lazy_bird.core.database module.

Tests database initialization, session management, and health checks.
"""

from unittest.mock import MagicMock, patch

import pytest

from lazy_bird.core.database import Base


class TestBase:
    """Test declarative base."""

    def test_base_exists(self):
        """Test Base declarative base exists."""
        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_base_has_tables_after_model_import(self):
        """Test Base has tables after importing models."""
        import lazy_bird.models  # noqa: F401

        # Should have at least some tables registered
        assert len(Base.metadata.tables) > 0


class TestGetDb:
    """Test get_db synchronous dependency."""

    def test_get_db_yields_session(self):
        """Test get_db yields a session and closes it."""
        from lazy_bird.core.database import get_db

        mock_session = MagicMock()

        with patch("lazy_bird.core.database.SessionLocal", return_value=mock_session):
            gen = get_db()
            session = next(gen)

            assert session is mock_session

            # Complete the generator
            try:
                next(gen)
            except StopIteration:
                pass

            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_get_db_rolls_back_on_exception(self):
        """Test get_db rolls back on exception."""
        from lazy_bird.core.database import get_db

        mock_session = MagicMock()

        with patch("lazy_bird.core.database.SessionLocal", return_value=mock_session):
            gen = get_db()
            session = next(gen)

            # Simulate exception during request handling
            with pytest.raises(ValueError):
                gen.throw(ValueError("Test error"))

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()


class TestGetAsyncDb:
    """Test get_async_db asynchronous dependency."""

    @pytest.mark.asyncio
    async def test_get_async_db_yields_session(self):
        """Test get_async_db yields a session."""
        from unittest.mock import AsyncMock
        from lazy_bird.core.database import get_async_db

        mock_session = MagicMock()
        mock_session.commit = AsyncMock(return_value=None)
        mock_session.rollback = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("lazy_bird.core.database.AsyncSessionLocal", return_value=mock_session):
            async for session in get_async_db():
                assert session is mock_session


class TestCheckDbConnection:
    """Test check_db_connection function."""

    def test_check_db_connection_success(self):
        """Test successful database connection check."""
        from lazy_bird.core.database import check_db_connection

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch("lazy_bird.core.database.engine") as mock_engine:
            mock_engine.connect.return_value = mock_conn
            result = check_db_connection()

        assert result is True

    def test_check_db_connection_failure(self):
        """Test failed database connection check."""
        from lazy_bird.core.database import check_db_connection

        with patch("lazy_bird.core.database.engine") as mock_engine:
            mock_engine.connect.side_effect = Exception("Connection refused")
            result = check_db_connection()

        assert result is False


class TestInitDb:
    """Test init_db and drop_db functions."""

    def test_init_db(self):
        """Test init_db calls create_all."""
        from lazy_bird.core.database import init_db

        with patch.object(Base.metadata, "create_all") as mock_create:
            init_db()
            mock_create.assert_called_once()

    def test_drop_db(self):
        """Test drop_db calls drop_all."""
        from lazy_bird.core.database import drop_db

        with patch.object(Base.metadata, "drop_all") as mock_drop:
            drop_db()
            mock_drop.assert_called_once()


class TestConnectionPoolEvents:
    """Test connection pool event listeners."""

    @patch("lazy_bird.core.database.settings")
    def test_receive_connect_with_echo(self, mock_settings, capsys):
        """Test connect event listener with echo enabled."""
        mock_settings.DB_ECHO = True
        from lazy_bird.core.database import receive_connect

        receive_connect("mock_dbapi_conn", "mock_record")

        captured = capsys.readouterr()
        assert "Database connection opened" in captured.out

    @patch("lazy_bird.core.database.settings")
    def test_receive_connect_without_echo(self, mock_settings, capsys):
        """Test connect event listener with echo disabled."""
        mock_settings.DB_ECHO = False
        from lazy_bird.core.database import receive_connect

        receive_connect("mock_dbapi_conn", "mock_record")

        captured = capsys.readouterr()
        assert captured.out == ""

    @patch("lazy_bird.core.database.settings")
    def test_receive_checkout_with_echo(self, mock_settings, capsys):
        """Test checkout event listener with echo enabled."""
        mock_settings.DB_ECHO = True
        from lazy_bird.core.database import receive_checkout

        receive_checkout("mock_dbapi_conn", "mock_record", "mock_proxy")

        captured = capsys.readouterr()
        assert "Database connection checked out" in captured.out

    @patch("lazy_bird.core.database.settings")
    def test_receive_checkin_with_echo(self, mock_settings, capsys):
        """Test checkin event listener with echo enabled."""
        mock_settings.DB_ECHO = True
        from lazy_bird.core.database import receive_checkin

        receive_checkin("mock_dbapi_conn", "mock_record")

        captured = capsys.readouterr()
        assert "Database connection checked in" in captured.out
