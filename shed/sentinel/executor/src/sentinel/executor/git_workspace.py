import base64
import os
import subprocess
from collections.abc import Callable
from datetime import datetime
from functools import partial
from pathlib import Path
from urllib.parse import urlparse

from sentinel.core.contracts.changes import ProposedChange
from sentinel.core.domain import RepositoryIdentity
from sentinel.core.git import sync_checkout
from sentinel.executor.github import GitHubGateway
from shed.core.deadline import RunTimedOut, remaining_seconds


class GitWorkspace:
    def __init__(self, root: Path, github: GitHubGateway):
        self.root = root
        self.github = github

    def push_changes(
        self,
        repository: RepositoryIdentity,
        base_branch: str,
        changes: list[ProposedChange],
        branch: str,
        *,
        title: str,
        deadline: datetime,
    ) -> None:
        path = self.root / repository.owner / repository.name
        git = partial(self._git, repository, deadline=deadline)
        sync_checkout(git, path, repository.clone_url, base_branch)
        if git(["-C", str(path), "ls-remote", "--heads", "origin", f"refs/heads/{branch}"]).strip():
            return
        base_sha = git(["-C", str(path), "rev-parse", "HEAD"]).strip()
        tree = self._checked_tree(git, path, changes)
        commit_sha = self.github.create_commit(repository, base_sha, tree, title)
        self.github.create_branch(repository, branch, commit_sha)

    @staticmethod
    def _checked_tree(git: Callable[[list[str]], str], path: Path, changes: list[ProposedChange]) -> list[dict]:
        """Stage each change inside the checkout, refuse whitespace errors, and return its GitHub tree entries.

        The checkout is reset afterwards: the commit itself is created on GitHub, not here.
        """
        root = path.resolve()
        contents: dict[str, str] = {}
        deleted: list[str] = []
        try:
            for change in changes:
                target = (path / change.file_path).resolve()
                if root not in target.parents:
                    raise ValueError(f"change path escapes repository: {change.file_path}")
                relative = target.relative_to(root).as_posix()
                if change.delete:
                    if not target.is_file():
                        raise ValueError(f"change deletes a file that does not exist: {change.file_path}")
                    target.unlink()
                    deleted.append(relative)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(change.content, encoding="utf-8")
                contents[relative] = change.content
            git(["-C", str(path), "add", "--", *contents, *deleted])
            changed = git(["-C", str(path), "diff", "--cached", "--name-only"])
            if not changed.strip():
                raise ValueError("the changes leave every file unchanged")
            git(["-C", str(path), "diff", "--cached", "--check"])
            staged = git(["-C", str(path), "ls-files", "-z", "--stage", "--", *contents]) if contents else ""
        finally:
            git(["-C", str(path), "reset", "--hard", "--quiet"])
            git(["-C", str(path), "clean", "-fd", "--quiet"])
        modes = {}
        for record in staged.split("\0"):
            if record:
                entry, file_path = record.split("\t", 1)
                modes[file_path] = entry.split(" ", 1)[0]
        written = [
            {"path": file_path, "mode": modes[file_path], "type": "blob", "content": content}
            for file_path, content in contents.items()
        ]
        removed = [{"path": file_path, "mode": "100644", "type": "blob", "sha": None} for file_path in deleted]
        return [*written, *removed]

    def _environment(self, repository: RepositoryIdentity) -> dict[str, str]:
        clone_url = urlparse(repository.clone_url)
        token = self.github.auth.installation_token()
        basic = f"x-access-token:{token}".encode()
        credentials = base64.b64encode(basic).decode()
        inherited = {name: os.environ[name] for name in ("PATH", "HOME") if name in os.environ}
        return {
            **inherited,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"http.{clone_url.scheme}://{clone_url.netloc}/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credentials}",
        }

    def _git(self, repository: RepositoryIdentity, arguments: list[str], *, deadline: datetime) -> str:
        environment = self._environment(repository)
        timeout = remaining_seconds(deadline)
        try:
            result = subprocess.run(
                ["git", *arguments], capture_output=True, text=True, timeout=timeout, check=False, env=environment
            )
        except subprocess.TimeoutExpired as exc:
            raise RunTimedOut("git did not finish within the action's time budget") from exc
        if result.returncode:
            raise RuntimeError(f"git operation failed: {result.stderr[-1000:]}")
        return result.stdout
