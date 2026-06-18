from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.projects import require_project_write_access
from app.core.security import encrypt_secret_value
from app.db.session import get_db
from app.models.project_secret import ProjectSecret
from app.models.user import User
from app.schemas.project_secret import (
    ProjectSecretCreate,
    ProjectSecretRead,
    ProjectSecretUpdate,
)
from app.services.audit import record_audit_event


router = APIRouter(prefix="/projects/{project_id}/secrets", tags=["project-secrets"])


def get_project_secret(
    db: Session,
    current_user: User,
    project_id: int,
    secret_id: int,
) -> ProjectSecret:
    require_project_write_access(db, current_user, project_id)
    secret = db.scalar(
        select(ProjectSecret).where(
            ProjectSecret.project_id == project_id,
            ProjectSecret.id == secret_id,
        )
    )
    if secret is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Секрет проекта не найден",
        )
    return secret


@router.get("", response_model=list[ProjectSecretRead])
def list_project_secrets(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectSecretRead]:
    require_project_write_access(db, current_user, project_id)
    secrets = db.scalars(
        select(ProjectSecret)
        .where(ProjectSecret.project_id == project_id)
        .order_by(ProjectSecret.name.asc())
    ).all()
    return [
        ProjectSecretRead(
            id=secret.id,
            project_id=secret.project_id,
            name=secret.name,
            created_at=secret.created_at,
            updated_at=secret.updated_at,
        )
        for secret in secrets
    ]


@router.post("", response_model=ProjectSecretRead, status_code=status.HTTP_201_CREATED)
def create_project_secret(
    project_id: int,
    payload: ProjectSecretCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectSecretRead:
    require_project_write_access(db, current_user, project_id)
    secret = ProjectSecret(
        project_id=project_id,
        name=payload.name,
        encrypted_value=encrypt_secret_value(payload.value),
    )
    db.add(secret)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Секрет с таким именем уже существует",
        ) from exc
    db.refresh(secret)
    record_audit_event(
        db,
        action="project.secret.created",
        user=current_user,
        entity_type="project_secret",
        entity_id=secret.id,
        details=f"project_id={project_id}; name={secret.name}",
        commit=True,
    )
    return ProjectSecretRead.model_validate(secret)


@router.put("/{secret_id}", response_model=ProjectSecretRead)
def update_project_secret(
    project_id: int,
    secret_id: int,
    payload: ProjectSecretUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectSecretRead:
    secret = get_project_secret(db, current_user, project_id, secret_id)
    secret.encrypted_value = encrypt_secret_value(payload.value)
    db.add(secret)
    db.commit()
    db.refresh(secret)
    record_audit_event(
        db,
        action="project.secret.updated",
        user=current_user,
        entity_type="project_secret",
        entity_id=secret.id,
        details=f"project_id={project_id}; name={secret.name}",
        commit=True,
    )
    return ProjectSecretRead.model_validate(secret)


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_secret(
    project_id: int,
    secret_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    secret = get_project_secret(db, current_user, project_id, secret_id)
    secret_name = secret.name
    db.delete(secret)
    db.commit()
    record_audit_event(
        db,
        action="project.secret.deleted",
        user=current_user,
        entity_type="project_secret",
        entity_id=secret_id,
        details=f"project_id={project_id}; name={secret_name}",
        commit=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
