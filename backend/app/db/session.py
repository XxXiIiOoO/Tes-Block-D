import time
from dataclasses import dataclass
from collections.abc import Generator

from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.db.migrations import run_migrations
from app.models.user import UserRole
from app.services.presets import (
    PRESET_PROJECT_DESCRIPTION,
    PRESET_PROJECT_NAME,
    PRESET_TESTS,
)


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


#Tut obrabatyvayu get_db, vse po delu i bez lishnego.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@dataclass(frozen=True)
class SeedUser:
    email: str
    username: str
    password: str
    role: UserRole


#Zdes sobrana logika _collect_seed_users, tak ee proshche podderzhivat.
def _collect_seed_users() -> list[SeedUser]:
    seed_users: list[SeedUser] = []
    if (
        settings.bootstrap_admin_email
        and settings.bootstrap_admin_username
        and settings.bootstrap_admin_password
    ):
        seed_users.append(
            SeedUser(
                email=settings.bootstrap_admin_email,
                username=settings.bootstrap_admin_username,
                password=settings.bootstrap_admin_password,
                role=UserRole.admin,
            )
        )

    if (
        settings.bootstrap_worker_email
        and settings.bootstrap_worker_username
        and settings.bootstrap_worker_password
    ):
        seed_users.append(
            SeedUser(
                email=settings.bootstrap_worker_email,
                username=settings.bootstrap_worker_username,
                password=settings.bootstrap_worker_password,
                role=UserRole.worker,
            )
        )

    if (
        settings.bootstrap_viewer_email
        and settings.bootstrap_viewer_username
        and settings.bootstrap_viewer_password
    ):
        seed_users.append(
            SeedUser(
                email=settings.bootstrap_viewer_email,
                username=settings.bootstrap_viewer_username,
                password=settings.bootstrap_viewer_password,
                role=UserRole.viewer,
            )
        )

    return seed_users


#Eto otdelnyy shag ensure_seed_users, chtoby ne kopipastit odno i to zhe.
def ensure_seed_users() -> None:
    from app.models.user import User

    seed_users = _collect_seed_users()
    if not seed_users:
        return

    db = SessionLocal()
    try:
        for seed_user in seed_users:
            user = db.scalar(select(User).where(User.email == seed_user.email))
            if user is None:
                db.add(
                    User(
                        email=seed_user.email,
                        username=seed_user.username,
                        password_hash=get_password_hash(seed_user.password),
                        role=seed_user.role.value,
                        is_admin=seed_user.role == UserRole.admin,
                        email_verified=True,
                        email_verification_token_hash=None,
                        email_verification_expires_at=None,
                    )
                )
                continue

            user.username = seed_user.username
            user.role = seed_user.role.value
            user.is_admin = seed_user.role == UserRole.admin
            user.email_verified = True
            user.email_verification_token_hash = None
            user.email_verification_expires_at = None
            if not verify_password(seed_user.password, user.password_hash):
                user.password_hash = get_password_hash(seed_user.password)
            db.add(user)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            for seed_user in seed_users:
                user = db.scalar(select(User).where(User.email == seed_user.email))
                if user is None:
                    continue
                user.username = seed_user.username
                user.role = seed_user.role.value
                user.is_admin = seed_user.role == UserRole.admin
                user.email_verified = True
                user.email_verification_token_hash = None
                user.email_verification_expires_at = None
                if not verify_password(seed_user.password, user.password_hash):
                    user.password_hash = get_password_hash(seed_user.password)
                db.add(user)
            db.commit()
    finally:
        db.close()


#Funkciya ensure_seed_presets zakryvaet konkretnuyu zadachu v etom meste.
def ensure_seed_presets() -> None:
    if not settings.seed_presets:
        return

    from app.models.project import Project
    from app.models.test import Test
    from app.models.user import User

    if not settings.bootstrap_admin_email:
        return

    db = SessionLocal()
    try:
        admin_user = db.scalar(select(User).where(User.email == settings.bootstrap_admin_email))
        if admin_user is None:
            return

        project = db.scalar(
            select(Project).where(
                Project.owner_id == admin_user.id,
                Project.name == PRESET_PROJECT_NAME,
            )
        )
        if project is None:
            project = Project(
                owner_id=admin_user.id,
                name=PRESET_PROJECT_NAME,
                description=PRESET_PROJECT_DESCRIPTION,
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        elif project.description != PRESET_PROJECT_DESCRIPTION:
            project.description = PRESET_PROJECT_DESCRIPTION
            db.add(project)
            db.commit()

        existing_tests = {
            test.name: test
            for test in db.scalars(select(Test).where(Test.project_id == project.id)).all()
        }
        existing_tests_by_command = {
            test.command: test
            for test in existing_tests.values()
            if test.command
        }
        changed = False
        for preset in PRESET_TESTS:
            existing_test = existing_tests.get(preset.name) or existing_tests_by_command.get(preset.command)
            if existing_test is None:
                db.add(
                    Test(
                        project_id=project.id,
                        name=preset.name,
                        description=preset.description,
                        scenario=preset.scenario,
                        docker_image=preset.docker_image,
                        command=preset.command,
                    )
                )
                changed = True
                continue

            if (
                existing_test.name != preset.name
                or existing_test.description != preset.description
                or existing_test.scenario != preset.scenario
                or existing_test.docker_image != preset.docker_image
                or existing_test.command != preset.command
            ):
                existing_test.name = preset.name
                existing_test.description = preset.description
                existing_test.scenario = preset.scenario
                existing_test.docker_image = preset.docker_image
                existing_test.command = preset.command
                db.add(existing_test)
                changed = True

        if changed:
            db.commit()
    finally:
        db.close()


#Funkciya init_db zakryvaet konkretnuyu zadachu v etom meste.
def init_db() -> None:
    for attempt in range(10):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            break
        except SQLAlchemyError:
            if attempt == 9:
                raise
            time.sleep(2)

    run_migrations(engine)
    ensure_seed_users()
    ensure_seed_presets()
