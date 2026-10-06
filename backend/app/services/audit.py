from sqlalchemy.orm import Session

from ..models import AuditLog


def record(db: Session, tenant_id: int, user_id: int | None, action: str, detail: str = "") -> None:
    db.add(AuditLog(tenant_id=tenant_id, user_id=user_id, action=action, detail=detail[:255]))
