import io
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import time

import docker
from docker.errors import APIError, DockerException, ImageNotFound
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decrypt_secret_value
from app.db.session import SessionLocal
from app.models.project_secret import ProjectSecret
from app.models.run import Run, RunStatus
from app.models.test import Test
from app.services.github_sources import GitHubSourceError, checkout_github_repository
from app.services.presets import LOCAL_DOCKER_IMAGE_BUILDERS

PYTHON_DEFAULT_IMAGE = "python:3.12-slim"
NODE_DAPP_IMAGE = "node:20-bookworm-slim"


class DockerRunnerError(Exception):
    pass


@dataclass
class DockerRunResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    cancelled: bool = False


@dataclass(frozen=True)
class RepositoryConfig:
    url: str
    branch: str | None
    subdir: str | None


class DockerRunner:
    #Eto otdelnyy shag __init__, chtoby ne kopipastit odno i to zhe.
    def __init__(self) -> None:
        self.client = docker.from_env()

    #Funkciya _ensure_image zakryvaet konkretnuyu zadachu v etom meste.
    def _ensure_image(self, image: str) -> None:
        if not settings.is_docker_image_allowed(image):
            raise DockerRunnerError(f"Docker image is not allowed: {image}")

        build_context = LOCAL_DOCKER_IMAGE_BUILDERS.get(image)
        if build_context is not None and build_context.exists():
            self.client.images.build(path=str(build_context), tag=image, rm=True)
            return

        try:
            self.client.images.get(image)
            return
        except ImageNotFound:
            pass

        self.client.images.pull(image)

    def _ensure_cache_volumes(self) -> None:
        volumes_to_create = ["blocktest_npm_cache", "blocktest_pip_cache"]
        volumes_created = False

        for vol_name in volumes_to_create:
            try:
                self.client.volumes.get(vol_name)
            except docker.errors.NotFound:
                self.client.volumes.create(vol_name)
                volumes_created = True

        if volumes_created:
            # Fix permissions on newly created volumes for non-root user (default 1000:1000)
            try:
                self._ensure_image(settings.default_docker_image)
                self.client.containers.run(
                    settings.default_docker_image,
                    "chown -R 1000:1000 /cache/npm /cache/pip",
                    volumes={
                        "blocktest_npm_cache": {"bind": "/cache/npm", "mode": "rw"},
                        "blocktest_pip_cache": {"bind": "/cache/pip", "mode": "rw"},
                    },
                    remove=True,
                )
            except DockerException:
                pass

    def _project_secret_environment(self, project_id: int) -> dict[str, str]:
        db = SessionLocal()
        try:
            secrets = db.scalars(
                select(ProjectSecret).where(ProjectSecret.project_id == project_id)
            ).all()
            environment: dict[str, str] = {}
            for secret in secrets:
                try:
                    environment[secret.name] = decrypt_secret_value(secret.encrypted_value)
                except ValueError as exc:
                    raise DockerRunnerError(f"Project secret cannot be decrypted: {secret.name}") from exc
            return environment
        finally:
            db.close()

    def _repository_config(self, test: Test) -> RepositoryConfig | None:
        if test.repository_url:
            return RepositoryConfig(
                url=test.repository_url,
                branch=test.repository_branch,
                subdir=test.repository_subdir,
            )
        if not test.command or test.script or test.project_id is None:
            return None

        db = SessionLocal()
        try:
            from app.models.project import Project

            project = db.get(Project, test.project_id)
            if project is None or not project.repository_url:
                return None
            return RepositoryConfig(
                url=project.repository_url,
                branch=project.repository_branch,
                subdir=project.repository_subdir,
            )
        finally:
            db.close()

    def _inject_file(self, container: object, directory: str, filename: str, content: bytes) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(content)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(content))
        buf.seek(0)
        container.put_archive(directory, buf)

    #Funkciya _inject_script zakryvaet konkretnuyu zadachu v etom meste.
    def _inject_script(self, container: object, script: str) -> None:
        """Write script.py into /workspace inside the running container."""
        self._inject_file(container, "/workspace", "script.py", script.encode("utf-8"))

    def _inject_ready_marker(self, container: object) -> None:
        self._inject_file(container, "/tmp", "blocktest-ready", b"ready\n")

    def _inject_directory(self, container: object, source_dir: Path) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for path in source_dir.rglob("*"):
                arcname = path.relative_to(source_dir)
                tar.add(path, arcname=str(arcname), recursive=False)
        buf.seek(0)
        container.put_archive("/workspace", buf)

    def _build_shell_command(
        self,
        test: Test,
        repository_config: RepositoryConfig | None = None,
    ) -> str:
        repository_config = repository_config if repository_config is not None else self._repository_config(test)
        if repository_config:
            command_parts = ["set -e"]
            if test.setup_command:
                command_parts.append(test.setup_command)
            if not test.command:
                raise DockerRunnerError("GitHub-backed test has no test command configured")
            command_parts.append(test.command)
            return "\n".join(command_parts)

        if test.script:
            return "python3 /workspace/script.py"
        if test.command:
            return test.command
        raise DockerRunnerError("Test has neither script nor command configured")

    def _is_cancelled(self, run_id: int | None) -> bool:
        if run_id is None:
            return False

        db = SessionLocal()
        try:
            run = db.get(Run, run_id)
            return run is not None and run.status == RunStatus.cancelled
        finally:
            db.close()

    #Funkciya execute_test zakryvaet konkretnuyu zadachu v etom meste.
    def execute_test(self, test: Test, *, run_id: int | None = None) -> DockerRunResult:
        repository_config = self._repository_config(test)
        if repository_config:
            image = test.docker_image or NODE_DAPP_IMAGE
        elif test.script:
            image = test.docker_image or PYTHON_DEFAULT_IMAGE
        elif test.command:
            image = test.docker_image or settings.default_docker_image
        else:
            raise DockerRunnerError("Test has neither script nor command configured")

        shell_command = self._build_shell_command(test, repository_config)
        command = [
            "/bin/sh",
            "-lc",
            "while [ ! -f /tmp/blocktest-ready ]; do sleep 0.1; done\n"
            "cd /workspace\n"
            f"{shell_command}",
        ]

        container = None
        timed_out = False
        cancelled = False

        try:
            self._ensure_image(image)
            self._ensure_cache_volumes()

            environment = {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
                "BLOCKTEST_RPC_URL": test.rpc_url or "",
                "BLOCKTEST_CHAIN_ID": str(test.chain_id or ""),
                "BLOCKTEST_REPOSITORY_URL": repository_config.url if repository_config else "",
                "npm_config_cache": "/cache/npm",
                "PIP_CACHE_DIR": "/cache/pip",
            }
            environment.update(self._project_secret_environment(test.project_id))

            create_kwargs: dict = {
                "image": image,
                "command": command,
                "detach": True,
                "mem_limit": settings.docker_memory_limit,
                "pids_limit": settings.docker_pids_limit,
                "nano_cpus": settings.docker_nano_cpus,
                "read_only": settings.docker_read_only_rootfs,
                "user": settings.docker_user,
                "cap_drop": ["ALL"],
                "security_opt": ["no-new-privileges"],
                "environment": environment,
                "working_dir": "/workspace",
                "volumes": {
                    "blocktest_npm_cache": {"bind": "/cache/npm", "mode": "rw"},
                    "blocktest_pip_cache": {"bind": "/cache/pip", "mode": "rw"},
                },
            }
            if run_id is not None:
                create_kwargs["labels"] = {"blocktest.run_id": str(run_id)}
            if settings.docker_compose_network:
                create_kwargs["network"] = settings.docker_compose_network
            else:
                create_kwargs["network_disabled"] = settings.docker_network_disabled

            container = self.client.containers.create(**create_kwargs)

            container.start()
            if repository_config:
                try:
                    with checkout_github_repository(
                        repository_config.url,
                        repository_config.branch,
                        repository_config.subdir,
                    ) as source_dir:
                        self._inject_directory(container, source_dir)
                except GitHubSourceError as exc:
                    raise DockerRunnerError(str(exc)) from exc
            elif test.script:
                self._inject_script(container, test.script)
            self._inject_ready_marker(container)

            started = datetime.now(timezone.utc)
            while True:
                container.reload()
                if container.status in {"exited", "dead"}:
                    break

                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                if elapsed > settings.docker_run_timeout_seconds:
                    timed_out = True
                    container.kill()
                    break
                if self._is_cancelled(run_id):
                    cancelled = True
                    container.kill()
                    break

                time.sleep(1)

            result = container.wait()
            exit_code = result.get("StatusCode", 1)
            if timed_out:
                exit_code = 124
            if cancelled:
                exit_code = 130

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            return DockerRunResult(
                stdout=stdout.strip(),
                stderr=stderr.strip(),
                exit_code=exit_code,
                timed_out=timed_out,
                cancelled=cancelled,
            )
        except (APIError, DockerException) as exc:
            raise DockerRunnerError(str(exc)) from exc
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except DockerException:
                    pass


class AsyncDockerRunner:
    """Async wrapper around DockerRunner that offloads blocking Docker SDK calls
    to a thread pool via asyncio.to_thread, keeping the event loop responsive."""

    def __init__(self) -> None:
        self._sync_runner = DockerRunner()

    async def execute_test(self, test: Test, *, run_id: int | None = None) -> DockerRunResult:
        import asyncio
        return await asyncio.to_thread(self._sync_runner.execute_test, test, run_id=run_id)

