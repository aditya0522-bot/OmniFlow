from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, require_admin
from ..models import Template, User
from ..schemas import TemplateIn, TemplateOut
from ..services import audit
from ..services.templates import placeholder_count

router = APIRouter(prefix="/templates", tags=["Templates"])


def _out(template: Template) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "language": template.language,
        "body": template.body,
        "variables": placeholder_count(template.body),
    }


@router.get("", response_model=list[TemplateOut])
def list_templates(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Template).where(Template.tenant_id == user.tenant_id).order_by(Template.name)).all()
    return [_out(t) for t in rows]


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(payload: TemplateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    template = Template(tenant_id=admin.tenant_id, name=payload.name, language=payload.language, body=payload.body.strip())
    db.add(template)
    audit.record(db, admin.tenant_id, admin.id, "template_added", payload.name)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A template with this name and language already exists")
    return _out(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    template = db.get(Template, template_id)
    if template is None or template.tenant_id != admin.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    db.delete(template)
    audit.record(db, admin.tenant_id, admin.id, "template_deleted", template.name)
    db.commit()
