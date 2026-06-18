from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.models.user import User


#Tut ya vynes record_audit_event, chtoby ne razduvat ostalnoy kod.
def record_audit_event(
    db: Session,
    action: str,
    user: User | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: str | None = None,
    *,
    commit: bool = False,
) -> AuditEvent:
    event = AuditEvent(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event
