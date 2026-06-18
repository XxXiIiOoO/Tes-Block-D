from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_admin, require_write_access
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectMemberRole
from app.models.user import User, UserRole
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberRead,
    ProjectMemberUpdate,
    ProjectRead,
    ProjectUpdate,
)
from app.services.audit import record_audit_event


router = APIRouter(prefix="/projects", tags=["projects"])


def project_access_filter(user: User):
    return or_(
        Project.owner_id == user.id,
        Project.members.any(ProjectMember.user_id == user.id),
    )


def get_project_access_role(db: Session, current_user: User, project: Project) -> str | None:
    if current_user.is_admin:
        return "admin"
    if project.owner_id == current_user.id:
        return "owner"

    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
        )
    )
    return membership.role if membership else None


def serialize_project(db: Session, current_user: User, project: Project) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        owner_id=project.owner_id,
        owner_username=project.owner_username,
        access_role=get_project_access_role(db, current_user, project),
        name=project.name,
        description=project.description,
        repository_url=project.repository_url,
        repository_branch=project.repository_branch,
        repository_subdir=project.repository_subdir,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def get_accessible_project(db: Session, current_user: User, project_id: int) -> Project:
    query = select(Project).options(joinedload(Project.owner)).where(Project.id == project_id)
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))

    project = db.scalar(query)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден")
    return project


def require_project_write_access(db: Session, current_user: User, project_id: int) -> Project:
    if current_user.role == UserRole.viewer.value and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль наблюдателя имеет только доступ на чтение",
        )
    project = get_accessible_project(db, current_user, project_id)
    role = get_project_access_role(db, current_user, project)
    if role not in {"admin", "owner", ProjectMemberRole.developer.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для изменения проекта",
        )
    return project


def serialize_member(member: ProjectMember) -> ProjectMemberRead:
    return ProjectMemberRead(
        id=member.id,
        project_id=member.project_id,
        user_id=member.user_id,
        username=member.user.username,
        email=member.user.email,
        full_name=member.user.full_name,
        role=member.role,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


@router.get("", response_model=list[ProjectRead])
def list_projects(
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectRead]:
    query = select(Project).options(joinedload(Project.owner))
    query = query.where(Project.name.not_ilike("Load Test Project%"))
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))

    projects = db.scalars(query.order_by(Project.created_at.desc())).all()
    return [serialize_project(db, current_user, project) for project in projects]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access),
) -> ProjectRead:
    project = Project(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
        repository_url=payload.repository_url,
        repository_branch=payload.repository_branch,
        repository_subdir=payload.repository_subdir,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    record_audit_event(
        db,
        action="project.created",
        user=current_user,
        entity_type="project",
        entity_id=project.id,
        details=f"name={project.name}",
        commit=True,
    )
    return serialize_project(db, current_user, project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_accessible_project(db, current_user, project_id)
    return serialize_project(db, current_user, project)


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectRead:
    project = require_project_write_access(db, current_user, project_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(project, field, value)

    db.add(project)
    db.commit()
    db.refresh(project)
    record_audit_event(
        db,
        action="project.updated",
        user=current_user,
        entity_type="project",
        entity_id=project.id,
        details=", ".join(sorted(updates.keys())) if updates else "no fields",
        commit=True,
    )
    return serialize_project(db, current_user, project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    project = require_project_write_access(db, current_user, project_id)
    project_name = project.name
    db.delete(project)
    db.commit()
    record_audit_event(
        db,
        action="project.deleted",
        user=current_user,
        entity_type="project",
        entity_id=project_id,
        details=f"name={project_name}",
        commit=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/members", response_model=list[ProjectMemberRead])
def list_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> list[ProjectMemberRead]:
    get_accessible_project(db, current_admin, project_id)
    members = db.scalars(
        select(ProjectMember)
        .options(joinedload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.desc())
    ).all()
    return [serialize_member(member) for member in members]


@router.post("/{project_id}/members", response_model=ProjectMemberRead, status_code=status.HTTP_201_CREATED)
def create_project_member(
    project_id: int,
    payload: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> ProjectMemberRead:
    project = get_accessible_project(db, current_admin, project_id)
    target_user = db.scalar(select(User).where(User.id == payload.user_id))
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if target_user.id == project.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Владелец уже имеет полный доступ")

    member = ProjectMember(project_id=project_id, user_id=payload.user_id, role=payload.role)
    db.add(member)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сотрудник уже добавлен в проект") from exc
    db.refresh(member)
    member.user = target_user
    record_audit_event(
        db,
        action="project.member.created",
        user=current_admin,
        entity_type="project_member",
        entity_id=member.id,
        details=f"project_id={project_id}; user_id={member.user_id}; role={member.role}",
        commit=True,
    )
    return serialize_member(member)


@router.put("/{project_id}/members/{member_id}", response_model=ProjectMemberRead)
def update_project_member(
    project_id: int,
    member_id: int,
    payload: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> ProjectMemberRead:
    get_accessible_project(db, current_admin, project_id)
    member = db.scalar(
        select(ProjectMember)
        .options(joinedload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id, ProjectMember.id == member_id)
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник проекта не найден")

    member.role = payload.role
    db.add(member)
    db.commit()
    db.refresh(member)
    record_audit_event(
        db,
        action="project.member.updated",
        user=current_admin,
        entity_type="project_member",
        entity_id=member.id,
        details=f"project_id={project_id}; user_id={member.user_id}; role={member.role}",
        commit=True,
    )
    return serialize_member(member)


@router.delete("/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_member(
    project_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> Response:
    get_accessible_project(db, current_admin, project_id)
    member = db.scalar(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.id == member_id)
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник проекта не найден")

    user_id = member.user_id
    db.delete(member)
    db.commit()
    record_audit_event(
        db,
        action="project.member.deleted",
        user=current_admin,
        entity_type="project_member",
        entity_id=member_id,
        details=f"project_id={project_id}; user_id={user_id}",
        commit=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
