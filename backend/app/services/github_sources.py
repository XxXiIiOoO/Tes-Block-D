from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import io
import re
import shutil
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import zipfile


MAX_GITHUB_ARCHIVE_BYTES = 100 * 1024 * 1024
GITHUB_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class GitHubSourceError(Exception):
    pass


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str


def parse_github_repository_url(value: str) -> GitHubRepository:
    url = value.strip()
    if not url:
        raise GitHubSourceError("GitHub repository URL is empty")

    if url.startswith("git@github.com:"):
        path = url.removeprefix("git@github.com:")
    else:
        if "://" not in url:
            url = f"https://{url}"
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname != "github.com":
            raise GitHubSourceError("Only github.com repository URLs are supported")
        path = parsed.path.strip("/")

    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        raise GitHubSourceError("GitHub URL must look like https://github.com/owner/repo")

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not GITHUB_NAME_RE.fullmatch(owner) or not GITHUB_NAME_RE.fullmatch(repo):
        raise GitHubSourceError("GitHub owner or repository name contains unsupported characters")
    return GitHubRepository(owner=owner, name=repo)


def _download_archive(repository: GitHubRepository, ref: str) -> bytes:
    quoted_ref = quote(ref.strip() or "main", safe="/")
    archive_url = f"https://codeload.github.com/{repository.owner}/{repository.name}/zip/{quoted_ref}"
    request = Request(archive_url, headers={"User-Agent": "BlockTest/1.0"})
    data = io.BytesIO()

    try:
        with urlopen(request, timeout=60) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                data.write(chunk)
                if data.tell() > MAX_GITHUB_ARCHIVE_BYTES:
                    raise GitHubSourceError("GitHub archive is larger than the 100 MB import limit")
    except HTTPError as exc:
        if exc.code == 404:
            raise GitHubSourceError("GitHub repository or branch was not found") from exc
        raise GitHubSourceError(f"GitHub returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise GitHubSourceError(f"Failed to download GitHub archive: {exc.reason}") from exc

    return data.getvalue()


def _safe_extract_zip(archive: bytes, target_dir: Path) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            for member in zip_file.infolist():
                member_path = target_dir / member.filename
                resolved = member_path.resolve()
                if target_dir.resolve() not in (resolved, *resolved.parents):
                    raise GitHubSourceError("GitHub archive contains unsafe paths")
            zip_file.extractall(target_dir)
    except zipfile.BadZipFile as exc:
        raise GitHubSourceError("GitHub archive is not a valid ZIP file") from exc


def _resolve_source_dir(extract_dir: Path, subdir: str | None) -> Path:
    top_level_dirs = [path for path in extract_dir.iterdir() if path.is_dir()]
    source_root = top_level_dirs[0] if len(top_level_dirs) == 1 else extract_dir

    if not subdir:
        return source_root

    normalized_subdir = subdir.strip().strip("/\\")
    if not normalized_subdir:
        return source_root
    if normalized_subdir.startswith(("..", "/", "\\")) or ".." in Path(normalized_subdir).parts:
        raise GitHubSourceError("Repository subdirectory is unsafe")

    source_dir = (source_root / normalized_subdir).resolve()
    root_resolved = source_root.resolve()
    if root_resolved not in (source_dir, *source_dir.parents):
        raise GitHubSourceError("Repository subdirectory is outside the repository")
    if not source_dir.is_dir():
        raise GitHubSourceError("Repository subdirectory was not found")
    return source_dir


@contextmanager
def checkout_github_repository(repository_url: str, ref: str | None, subdir: str | None):
    repository = parse_github_repository_url(repository_url)
    extract_dir = Path(tempfile.mkdtemp(prefix="blocktest-github-"))
    try:
        archive = _download_archive(repository, ref or "main")
        _safe_extract_zip(archive, extract_dir)
        yield _resolve_source_dir(extract_dir, subdir)
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)
