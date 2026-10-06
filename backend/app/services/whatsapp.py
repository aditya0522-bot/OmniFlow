import logging

import httpx

from ..config import settings
from ..security import decrypt_secret

logger = logging.getLogger("omniflow.whatsapp")
GRAPH_URL = "https://graph.facebook.com/v21.0"


def credentials(tenant) -> tuple[str, str]:
    phone_id = tenant.whatsapp_phone_id
    token = decrypt_secret(tenant.whatsapp_token_enc)
    if settings.allow_env_whatsapp:
        phone_id = phone_id or settings.whatsapp_phone_id
        token = token or settings.whatsapp_token
    return phone_id, token


def is_configured(tenant) -> bool:
    phone_id, token = credentials(tenant)
    return bool(phone_id and token)


def _post(phone_id: str, token: str, payload: dict) -> tuple[str, str | None]:
    try:
        response = httpx.post(
            f"{GRAPH_URL}/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"messaging_product": "whatsapp", **payload},
            timeout=10,
        )
        response.raise_for_status()
        return "sent", response.json()["messages"][0]["id"]
    except httpx.HTTPStatusError as exc:
        logger.warning("WhatsApp rejected message: %s %s", exc.response.status_code, exc.response.text[:300])
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        logger.warning("WhatsApp request failed", exc_info=True)
    return "failed", None


def send_text(tenant, to: str, body: str) -> tuple[str, str | None]:
    """Returns (status, whatsapp_message_id). Status is sent, failed or queued."""
    phone_id, token = credentials(tenant)
    if not (phone_id and token):
        return "queued", None
    return _post(phone_id, token, {"to": to.lstrip("+"), "type": "text", "text": {"body": body}})


def send_template(tenant, to: str, name: str, language: str, variables: list[str]) -> tuple[str, str | None]:
    phone_id, token = credentials(tenant)
    if not (phone_id and token):
        return "queued", None
    template = {"name": name, "language": {"code": language}}
    if variables:
        template["components"] = [
            {"type": "body", "parameters": [{"type": "text", "text": value} for value in variables]}
        ]
    return _post(phone_id, token, {"to": to.lstrip("+"), "type": "template", "template": template})
