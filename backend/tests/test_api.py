from types import SimpleNamespace
from datetime import timedelta

from app.database import SessionLocal
from app.models import Conversation, Message, utcnow
from app.services.inbox import window_open
from tests.conftest import login

API = "/api/v1"


def webhook_payload(message_id: str, text: str, sender: str = "919000000001") -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "test-phone"},
                            "contacts": [{"wa_id": sender, "profile": {"name": "Test Person"}}],
                            "messages": [{"id": message_id, "from": sender, "type": "text", "text": {"body": text}}],
                        }
                    }
                ]
            }
        ]
    }


def connect_test_phone(client, auth):
    client.put(f"{API}/settings/whatsapp", headers=auth, json={"phone_number_id": "test-phone"})


# ---------------------------------------------------------------- auth

def test_login_rejects_wrong_password(client):
    response = client.post(f"{API}/auth/login", json={"email": "admin@omniflow.local", "password": "nope"})
    assert response.status_code == 401


def test_routes_need_a_token(client):
    assert client.get(f"{API}/customers").status_code == 401
    assert client.get(f"{API}/dashboard").status_code == 401


def test_repeated_failed_logins_are_rate_limited(client):
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    codes = [client.post(f"{API}/auth/login", json=body).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429


def test_signup_creates_a_separate_workspace(client):
    created = client.post(
        f"{API}/auth/signup",
        json={"company": "Fresh Co", "name": "Owner", "email": "owner@fresh.example", "password": "long-enough-1"},
    )
    assert created.status_code == 201
    headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
    assert client.get(f"{API}/customers", headers=headers).json() == []
    assert client.get(f"{API}/conversations/1", headers=headers).status_code == 404
    duplicate = client.post(
        f"{API}/auth/signup",
        json={"company": "Fresh Co", "name": "Owner", "email": "owner@fresh.example", "password": "long-enough-1"},
    )
    assert duplicate.status_code == 409


def test_refresh_token_and_password_change_revoke_old_tokens(client):
    client.post(
        f"{API}/auth/signup",
        json={"company": "Rotate Co", "name": "Rita", "email": "rita@rotate.example", "password": "first-password"},
    )
    session = login(client, "rita@rotate.example", "first-password")
    old_headers = {"Authorization": f"Bearer {session['access_token']}"}

    refreshed = client.post(f"{API}/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert refreshed.status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": session["access_token"]}).status_code == 401

    changed = client.post(
        f"{API}/auth/change-password",
        headers=old_headers,
        json={"current_password": "first-password", "new_password": "second-password"},
    )
    assert changed.status_code == 200
    assert client.get(f"{API}/auth/me", headers=old_headers).status_code == 401
    assert client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {changed.json()['access_token']}"}
    ).status_code == 200


# ---------------------------------------------------------------- team and roles

def test_agents_cannot_manage_the_workspace(client, auth):
    added = client.post(
        f"{API}/team",
        headers=auth,
        json={"name": "Asha", "email": "asha@omniflow.example", "password": "agent-password", "role": "agent"},
    )
    assert added.status_code == 201
    agent = {"Authorization": f"Bearer {login(client, 'asha@omniflow.example', 'agent-password')['access_token']}"}

    assert client.get(f"{API}/customers", headers=agent).status_code == 200
    assert client.get(f"{API}/team", headers=agent).status_code == 403
    assert client.get(f"{API}/bot/rules", headers=agent).status_code == 403
    assert client.get(f"{API}/settings/whatsapp", headers=agent).status_code == 403

    client.patch(f"{API}/team/{added.json()['id']}", headers=auth, json={"is_active": False})
    assert client.get(f"{API}/customers", headers=agent).status_code == 401


def test_last_admin_cannot_be_removed(client, auth):
    me = client.get(f"{API}/auth/me", headers=auth).json()
    response = client.patch(f"{API}/team/{me['id']}", headers=auth, json={"role": "agent"})
    assert response.status_code == 400


# ---------------------------------------------------------------- data

def test_dashboard_has_seeded_data(client, auth):
    data = client.get(f"{API}/dashboard", headers=auth).json()
    assert data["total_customers"] >= 8
    assert len(data["week"]) == 7


def test_customer_needs_consent(client, auth):
    body = {"name": "No Consent", "phone": "9876500001"}
    assert client.post(f"{API}/customers", headers=auth, json={**body, "consent": False}).status_code == 422
    created = client.post(f"{API}/customers", headers=auth, json={**body, "consent": True})
    assert created.status_code == 201
    assert created.json()["phone"] == "+919876500001"
    assert client.delete(f"{API}/customers/{created.json()['id']}", headers=auth).status_code == 204


# ---------------------------------------------------------------- WhatsApp

def test_webhook_verification(client):
    ok = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "test-token", "hub.challenge": "12345"},
    )
    assert ok.status_code == 200 and ok.text == "12345"
    bad = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert bad.status_code == 403


def test_incoming_message_is_stored_and_bot_replies(client, auth):
    connect_test_phone(client, auth)
    first = client.post("/webhooks/whatsapp", json=webhook_payload("wamid.1", "What is the menu today?"))
    assert first.json()["stored"] == 1
    duplicate = client.post("/webhooks/whatsapp", json=webhook_payload("wamid.1", "What is the menu today?"))
    assert duplicate.json()["stored"] == 0

    found = client.get(f"{API}/conversations", headers=auth, params={"q": "9000000001"}).json()
    assert len(found) == 1
    detail = client.get(f"{API}/conversations/{found[0]['id']}", headers=auth).json()
    assert [m["source"] for m in detail["messages"]] == ["customer", "bot"]
    assert "dal" in detail["messages"][1]["body"]


def test_delivery_receipts_only_move_status_forward(client, auth):
    connect_test_phone(client, auth)
    conversation_id = client.get(f"{API}/conversations", headers=auth, params={"q": "9000000001"}).json()[0]["id"]
    with SessionLocal() as db:
        db.add(Message(conversation_id=conversation_id, direction="out", body="hi", status="sent", external_id="wamid.OUT1"))
        db.commit()

    def receipt(status):
        payload = {
            "entry": [{"changes": [{"value": {"metadata": {"phone_number_id": "test-phone"}, "statuses": [{"id": "wamid.OUT1", "status": status}]}}]}]
        }
        client.post("/webhooks/whatsapp", json=payload)
        with SessionLocal() as db:
            return db.query(Message).filter_by(external_id="wamid.OUT1").one().status

    assert receipt("delivered") == "delivered"
    assert receipt("read") == "read"
    assert receipt("delivered") == "read"


def test_stop_opts_the_customer_out(client, auth):
    connect_test_phone(client, auth)
    client.post("/webhooks/whatsapp", json=webhook_payload("wamid.stop", "STOP", sender="919000000002"))
    conversation = client.get(f"{API}/conversations", headers=auth, params={"q": "9000000002"}).json()[0]
    blocked = client.post(f"{API}/conversations/{conversation['id']}/messages", headers=auth, json={"body": "hello"})
    assert blocked.status_code == 409


def test_template_message_is_rendered(client, auth):
    created = client.post(
        f"{API}/templates", headers=auth, json={"name": "greeting", "language": "en", "body": "Hi {{1}}, order {{2}} shipped"}
    )
    assert created.status_code == 201 and created.json()["variables"] == 2
    short = client.post(f"{API}/conversations/1/template", headers=auth, json={"template_id": created.json()["id"], "variables": ["Rahul"]})
    assert short.status_code == 422
    sent = client.post(
        f"{API}/conversations/1/template",
        headers=auth,
        json={"template_id": created.json()["id"], "variables": ["Rahul", "ORD-1001"]},
    )
    assert sent.status_code == 201
    assert sent.json()["body"] == "Hi Rahul, order ORD-1001 shipped"


def test_free_text_window_closes_after_24_hours():
    fresh = SimpleNamespace(last_inbound_at=utcnow() - timedelta(hours=2))
    stale = SimpleNamespace(last_inbound_at=utcnow() - timedelta(hours=30))
    never = SimpleNamespace(last_inbound_at=None)
    assert window_open(fresh, configured=True)
    assert not window_open(stale, configured=True)
    assert not window_open(never, configured=True)
    assert window_open(stale, configured=False)


def test_simulated_message_triggers_bot(client, auth):
    response = client.post(f"{API}/demo/simulate", headers=auth, json={"customer_id": 1, "text": "price?"})
    assert response.status_code == 200
    detail = client.get(f"{API}/conversations/{response.json()['conversation_id']}", headers=auth).json()
    assert detail["messages"][-1]["source"] == "bot"


def test_whatsapp_token_is_encrypted_and_never_returned(client, auth):
    response = client.put(
        f"{API}/settings/whatsapp",
        headers=auth,
        json={"phone_number_id": "test-phone", "access_token": "EAAB-secret-token"},
    )
    assert response.status_code == 200
    assert response.json()["token_set"] is True
    assert "EAAB" not in response.text
    with SessionLocal() as db:
        from app.models import Tenant

        stored = db.query(Tenant).filter(Tenant.whatsapp_phone_id == "test-phone").one().whatsapp_token_enc
        assert stored and "EAAB" not in stored
    client.put(f"{API}/settings/whatsapp", headers=auth, json={"phone_number_id": "test-phone", "clear_token": True})


# ---------------------------------------------------------------- schema

def test_migrations_match_models(client):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.database import Base, engine

    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []
