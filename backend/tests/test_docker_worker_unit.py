import pytest
from unittest.mock import MagicMock, patch
from docker.errors import ImageNotFound

from app.services.docker_runner import DockerRunner, DockerRunnerError, RepositoryConfig
from app.models.test import Test

@pytest.fixture
def mock_docker_client():
    """Mock the Docker client to prevent actual Docker socket interactions during unit tests."""
    with patch("app.services.docker_runner.docker.from_env") as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        yield mock_client

def test_build_shell_command_github_app(mock_docker_client):
    """Test that the shell command is built correctly for a GitHub repository test."""
    runner = DockerRunner()
    test = Test(
        repository_url="https://github.com/example/repo",
        command="npm run test",
        setup_command="npm install",
    )
    command = runner._build_shell_command(test)
    assert "set -e" in command
    assert "npm install" in command
    assert "npm run test" in command

def test_build_shell_command_project_github_app(mock_docker_client):
    """Test that project-level GitHub sources use the same command flow."""
    runner = DockerRunner()
    test = Test(
        command="npm run test",
        setup_command="npm install",
    )
    command = runner._build_shell_command(
        test,
        RepositoryConfig(
            url="https://github.com/example/repo",
            branch="main",
            subdir=None,
        ),
    )
    assert "set -e" in command
    assert "npm install" in command
    assert "npm run test" in command

def test_build_shell_command_script_only(mock_docker_client):
    """Test that the shell command is built correctly for an isolated python script."""
    runner = DockerRunner()
    test = Test(script="print('Hello World')")
    command = runner._build_shell_command(test)
    assert command == "python3 /workspace/script.py"

def test_build_shell_command_command_only(mock_docker_client):
    """Test that a raw command is passed through correctly."""
    runner = DockerRunner()
    test = Test(command="forge test")
    command = runner._build_shell_command(test)
    assert command == "forge test"

def test_build_shell_command_empty(mock_docker_client):
    """Test that an error is raised if no execution configuration is provided."""
    runner = DockerRunner()
    test = Test()
    with pytest.raises(DockerRunnerError, match="Test has neither script nor command configured"):
        runner._build_shell_command(test)

def test_ensure_image_allowed_and_exists(mock_docker_client):
    """Test that an existing allowed image is not pulled again."""
    with patch("app.services.docker_runner.settings") as mock_settings:
        mock_settings.is_docker_image_allowed.return_value = True
        runner = DockerRunner()
        
        # Act
        runner._ensure_image("python:3.12-slim")
        
        # Assert get was called, but pull was NOT called
        mock_docker_client.images.get.assert_called_once_with("python:3.12-slim")
        mock_docker_client.images.pull.assert_not_called()

def test_ensure_image_rebuilds_local_builder_even_when_image_exists(mock_docker_client, tmp_path):
    """Local preset images are rebuilt so deployed preset code is not stale."""
    with patch("app.services.docker_runner.settings") as mock_settings:
        mock_settings.is_docker_image_allowed.return_value = True
        with patch("app.services.docker_runner.LOCAL_DOCKER_IMAGE_BUILDERS", {"blocktest-evm-presets:latest": tmp_path}):
            runner = DockerRunner()

            runner._ensure_image("blocktest-evm-presets:latest")

        mock_docker_client.images.build.assert_called_once_with(
            path=str(tmp_path),
            tag="blocktest-evm-presets:latest",
            rm=True,
        )
        mock_docker_client.images.get.assert_not_called()
        mock_docker_client.images.pull.assert_not_called()

def test_ensure_image_allowed_but_missing(mock_docker_client):
    """Test that a missing allowed image is pulled."""
    with patch("app.services.docker_runner.settings") as mock_settings:
        mock_settings.is_docker_image_allowed.return_value = True
        # Simulate image not existing locally
        mock_docker_client.images.get.side_effect = ImageNotFound("Not found")
        
        runner = DockerRunner()
        runner._ensure_image("python:3.12-slim")
        
        # Assert pull was called
        mock_docker_client.images.pull.assert_called_once_with("python:3.12-slim")

def test_ensure_image_not_allowed(mock_docker_client):
    """Test that a disallowed image raises an error and does not interact with Docker API."""
    with patch("app.services.docker_runner.settings") as mock_settings:
        mock_settings.is_docker_image_allowed.return_value = False
        runner = DockerRunner()
        
        with pytest.raises(DockerRunnerError, match="Docker image is not allowed: malicious/image:latest"):
            runner._ensure_image("malicious/image:latest")
        
        # Assert Docker API was never touched
        mock_docker_client.images.get.assert_not_called()
        mock_docker_client.images.pull.assert_not_called()
