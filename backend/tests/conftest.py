import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["ENVIRONMENT"] = "development"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["DEMO_MODE"] = "false"
os.environ["WORKER_ENABLED"] = "false"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-token"
os.environ["WHATSAPP_TOKEN"] = ""
os.environ["WHATSAPP_PHONE_ID"] = ""
os.environ["WHATSAPP_APP_SECRET"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client, email="admin@omniflow.local", password="admin123"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def auth(client):
    return {"Authorization": f"Bearer {login(client)['access_token']}"}
