from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.routes.projects import get_project_access_role, project_access_filter, require_project_write_access
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMemberRole
from app.models.test import Test
from app.models.test_chat_message import TestChatMessage
from app.models.user import User, UserRole
from app.schemas.test import (
    TestChatMessageCreate,
    TestChatMessageRead,
    TestCreate,
    TestRead,
    TestUpdate,
)
from app.services.audit import record_audit_event


router = APIRouter(tags=["tests"])


#Tut ya vynes get_accessible_project, chtoby ne razduvat ostalnoy kod.
def get_accessible_project(db: Session, current_user: User, project_id: int) -> Project:
    query = select(Project).where(Project.id == project_id)
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))

    project = db.scalar(query)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден")
    return project


#Funkciya get_accessible_test zakryvaet konkretnuyu zadachu v etom meste.
def get_accessible_test(db: Session, current_user: User, test_id: int) -> Test:
    query = (
        select(Test)
        .options(joinedload(Test.project))
        .join(Project, Test.project_id == Project.id)
        .where(Test.id == test_id)
    )
    if not current_user.is_admin:
        query = query.where(project_access_filter(current_user))

    test = db.scalar(query)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден")
    return test


def require_test_write_access(db: Session, current_user: User, test_id: int) -> Test:
    if current_user.role == UserRole.viewer.value and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль наблюдателя имеет только доступ на чтение",
        )
    test = get_accessible_test(db, current_user, test_id)
    role = get_project_access_role(db, current_user, test.project)
    if role not in {"admin", "owner", ProjectMemberRole.developer.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для изменения теста",
        )
    return test


def serialize_test(db: Session, current_user: User, test: Test) -> TestRead:
    payload = TestRead.model_validate(test)
    role = get_project_access_role(db, current_user, test.project)
    if role == ProjectMemberRole.viewer.value:
        payload.command = None
        payload.script = None
        payload.setup_command = None
        payload.rpc_url = None
    return payload


#Tut ya vynes list_tests, chtoby ne razduvat ostalnoy kod.
@router.get("/projects/{project_id}/tests", response_model=list[TestRead])
def list_tests(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TestRead]:
    project = get_accessible_project(db, current_user, project_id)
    tests = db.scalars(
        select(Test).where(Test.project_id == project_id).order_by(Test.created_at.desc())
    ).all()
    for test in tests:
        test.project = project
    return [serialize_test(db, current_user, test) for test in tests]


@router.post(
    "/projects/{project_id}/tests",
    response_model=TestRead,
    status_code=status.HTTP_201_CREATED,
)
#Funkciya create_test zakryvaet konkretnuyu zadachu v etom meste.
def create_test(
    project_id: int,
    payload: TestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestRead:
    project = require_project_write_access(db, current_user, project_id)

    test = Test(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        scenario=payload.scenario,
        docker_image=payload.docker_image,
        command=payload.command,
        script=payload.script,
        repository_url=payload.repository_url,
        repository_branch=payload.repository_branch,
        repository_subdir=payload.repository_subdir,
        setup_command=payload.setup_command,
        rpc_url=payload.rpc_url,
        chain_id=payload.chain_id,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    test.project = project
    record_audit_event(
        db,
        action="test.created",
        user=current_user,
        entity_type="test",
        entity_id=test.id,
        details=f"name={test.name}",
        commit=True,
    )
    return serialize_test(db, current_user, test)


#Zdes sobrana logika get_test, tak ee proshche podderzhivat.
@router.get("/tests/{test_id}", response_model=TestRead)
def get_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestRead:
    test = get_accessible_test(db, current_user, test_id)
    return serialize_test(db, current_user, test)


#Funkciya update_test zakryvaet konkretnuyu zadachu v etom meste.
@router.put("/tests/{test_id}", response_model=TestRead)
def update_test(
    test_id: int,
    payload: TestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestRead:
    test = require_test_write_access(db, current_user, test_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(test, field, value)

    db.add(test)
    db.commit()
    db.refresh(test)
    record_audit_event(
        db,
        action="test.updated",
        user=current_user,
        entity_type="test",
        entity_id=test.id,
        details=", ".join(sorted(updates.keys())) if updates else "no fields",
        commit=True,
    )
    return serialize_test(db, current_user, test)


#Tut obrabatyvayu delete_test, vse po delu i bez lishnego.
@router.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    test = require_test_write_access(db, current_user, test_id)
    test_name = test.name
    db.delete(test)
    db.commit()
    record_audit_event(
        db,
        action="test.deleted",
        user=current_user,
        entity_type="test",
        entity_id=test_id,
        details=f"name={test_name}",
        commit=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


#Eto otdelnyy shag list_test_chat_messages, chtoby ne kopipastit odno i to zhe.
@router.get("/tests/{test_id}/chat", response_model=list[TestChatMessageRead])
def list_test_chat_messages(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TestChatMessageRead]:
    get_accessible_test(db, current_user, test_id)
    messages = db.scalars(
        select(TestChatMessage)
        .options(joinedload(TestChatMessage.author))
        .where(TestChatMessage.test_id == test_id)
        .order_by(TestChatMessage.created_at.asc())
    ).all()
    return [
        TestChatMessageRead(
            id=message.id,
            test_id=message.test_id,
            user_id=message.user_id,
            username=message.author.username if message.author else "unknown",
            role=message.author.role if message.author else "worker",
            message=message.message,
            created_at=message.created_at,
        )
        for message in messages
    ]


#Eto otdelnyy shag post_test_chat_message, chtoby ne kopipastit odno i to zhe.
@router.post("/tests/{test_id}/chat", response_model=TestChatMessageRead, status_code=status.HTTP_201_CREATED)
def post_test_chat_message(
    test_id: int,
    payload: TestChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TestChatMessageRead:
    require_test_write_access(db, current_user, test_id)
    chat_message = TestChatMessage(
        test_id=test_id,
        user_id=current_user.id,
        message=payload.message.strip(),
    )
    if not chat_message.message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сообщение не может быть пустым")

    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)
    record_audit_event(
        db,
        action="test.chat.posted",
        user=current_user,
        entity_type="test",
        entity_id=test_id,
        details=f"message_id={chat_message.id}",
        commit=True,
    )
    return TestChatMessageRead(
        id=chat_message.id,
        test_id=chat_message.test_id,
        user_id=chat_message.user_id,
        username=current_user.username,
        role=current_user.role,
        message=chat_message.message,
        created_at=chat_message.created_at,
    )
