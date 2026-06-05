import os
import tempfile
import pytest
import app as app_module


@pytest.fixture
def temp_db(monkeypatch):
    """Create an isolated temporary database for each test."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    monkeypatch.setattr(app_module, "DB_PATH", db_path)
    app_module.init_db()
    yield db_path
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(temp_db):
    """Flask test client backed by the isolated database."""
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def db(temp_db):
    """Direct database connection for inspecting state in assertions."""
    conn = app_module.get_db()
    yield conn
    conn.close()