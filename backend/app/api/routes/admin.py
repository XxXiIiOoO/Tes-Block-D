from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_admin
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.user import User, UserRole
from app.schemas.admin import AdminUserCreate, AdminUserUpdate, AuditEventRead
from app.schemas.user import UserRead
from app.services.audit import record_audit_event


router = APIRouter(prefix="/admin", tags=["admin"])


def ensure_admin_can_lose_admin_role(db: Session, user: User) -> None:
    if not user.is_admin:
        return
    admin_count = db.scalar(select(func.count(User.id)).where(User.is_admin.is_(True))) or 0
    if admin_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя убрать права у последнего администратора",
        )


def apply_user_text_fields(user: User, data: dict[str, object], changes: list[str]) -> None:
    for field in ("full_name", "position", "avatar_url", "bio"):
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(user, field, value)
            changes.append(f"{field}=updated")


#Tut ya vynes list_users, chtoby ne razduvat ostalnoy kod.
@router.get("/users", response_model=list[UserRead])
def list_users(
    search: str | None = Query(default=None, max_length=120),
    role: str | None = Query(default=None, pattern="^(admin|worker|viewer)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserRead]:
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if search:
        search_mask = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.email.ilike(search_mask),
                User.username.ilike(search_mask),
                User.full_name.ilike(search_mask),
            )
        )

    users = db.scalars(query.order_by(User.created_at.desc())).all()
    return [UserRead.model_validate(user) for user in users]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> UserRead:
    user = User(
        email=payload.email,
        username=payload.username.strip(),
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        is_admin=payload.role == UserRole.admin.value,
        email_verified=payload.email_verified,
        full_name=payload.full_name.strip() if payload.full_name else None,
        position=payload.position.strip() if payload.position else None,
        avatar_url=payload.avatar_url.strip() if payload.avatar_url else None,
        bio=payload.bio.strip() if payload.bio else None,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email или логином уже существует",
        ) from exc
    db.refresh(user)

    record_audit_event(
        db,
        action="admin.user.created",
        user=current_admin,
        entity_type="user",
        entity_id=user.id,
        details=f"email={user.email}; role={user.role}",
        commit=True,
    )
    return UserRead.model_validate(user)


#Tut obrabatyvayu update_user, vse po delu i bez lishnego.
@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> UserRead:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    changes: list[str] = []
    data = payload.model_dump(exclude_unset=True)

    if "email" in data:
        email = str(data["email"]).strip().lower()
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email не может быть пустым")
        user.email = email
        changes.append("email=updated")

    if "username" in data:
        username = str(data["username"]).strip()
        if not username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Логин не может быть пустым")
        user.username = username
        changes.append("username=updated")

    if data.get("password"):
        user.password_hash = get_password_hash(str(data["password"]))
        changes.append("password=updated")

    new_role = data.get("role")
    if new_role is not None:
        if new_role == UserRole.admin.value:
            user.is_admin = True
        else:
            if user.is_admin:
                ensure_admin_can_lose_admin_role(db, user)
                admin_count = db.scalar(
                    select(func.count(User.id)).where(User.is_admin.is_(True))
                ) or 0
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Нельзя убрать права у последнего администратора",
                    )
            user.is_admin = False
        user.role = new_role
        changes.append(f"role={new_role}")

    if "email_verified" in data:
        user.email_verified = bool(data["email_verified"])
        if user.email_verified:
            user.email_verification_token_hash = None
            user.email_verification_expires_at = None
        changes.append(f"email_verified={user.email_verified}")

    for field in ("full_name", "position", "avatar_url", "bio"):
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(user, field, value)
            changes.append(f"{field}=updated")

    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email или логином уже существует",
        ) from exc
    db.refresh(user)

    details = ", ".join(changes) if changes else "no explicit fields changed"
    record_audit_event(
        db,
        action="admin.user.updated",
        user=current_admin,
        entity_type="user",
        entity_id=user.id,
        details=details,
        commit=True,
    )

    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> Response:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    ensure_admin_can_lose_admin_role(db, user)

    deleted_email = user.email
    db.delete(user)
    db.commit()
    record_audit_event(
        db,
        action="admin.user.deleted",
        user=current_admin,
        entity_type="user",
        entity_id=user_id,
        details=f"email={deleted_email}",
        commit=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


#Tut ya vynes list_audit_events, chtoby ne razduvat ostalnoy kod.
@router.get("/audit-events", response_model=list[AuditEventRead])
def list_audit_events(
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    user_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[AuditEventRead]:
    query = select(AuditEvent).options(joinedload(AuditEvent.user))
    if action:
        query = query.where(AuditEvent.action == action)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if user_id is not None:
        query = query.where(AuditEvent.user_id == user_id)

    events = db.scalars(query.order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    return [
        AuditEventRead(
            id=event.id,
            user_id=event.user_id,
            username=event.user.username if event.user else None,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            details=event.details,
            created_at=event.created_at,
        )
        for event in events
    ]
