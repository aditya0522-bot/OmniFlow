from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import BotRule, User
from ..schemas import BotRuleIn, BotRuleOut, BotRulePatch

router = APIRouter(prefix="/bot/rules", tags=["Auto-replies"])


def _get_owned(db: Session, user: User, rule_id: int) -> BotRule:
    rule = db.get(BotRule, rule_id)
    if rule is None or rule.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return rule


@router.get("", response_model=list[BotRuleOut])
def list_rules(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(BotRule).where(BotRule.tenant_id == user.tenant_id).order_by(BotRule.id)).all()


@router.post("", response_model=BotRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(payload: BotRuleIn, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rule = BotRule(tenant_id=user.tenant_id, keyword=payload.keyword.strip(), reply=payload.reply.strip())
    db.add(rule)
    db.commit()
    return rule


@router.patch("/{rule_id}", response_model=BotRuleOut)
def toggle_rule(rule_id: int, payload: BotRulePatch, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rule = _get_owned(db, user, rule_id)
    rule.active = payload.active
    db.commit()
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    db.delete(_get_owned(db, user, rule_id))
    db.commit()
