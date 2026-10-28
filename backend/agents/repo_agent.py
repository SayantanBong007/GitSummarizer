from __future__ import annotations

import os
from pathlib import Path

import git

from backend.agents.state import AnalysisState
from backend.config import get_settings
from backend.core.exceptions import RepositoryCloneError
from backend.core.logging import get_logger
from backend.parsers import SUPPORTED_EXTENSIONS

logger = get_logger(__name__)

_SKIP_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", "target", "vendor", ".cache",
})

_FRAMEWORK_SIGNALS: dict[str, list[str]] = {
    "Next.js": ["next.config.js", "next.config.ts", "next.config.mjs"],
    "React": ["package.json"],  # refined by content below
    "Vue.js": ["vue.config.js", "nuxt.config.ts"],
    "Angular": ["angular.json"],
    "FastAPI": ["main.py"],    # refined by import detection
    "Django": ["manage.py", "settings.py"],
    "Flask": ["app.py"],
    "Spring Boot": ["pom.xml"],
    "Express": ["package.json"],
    "Laravel": ["artisan"],
    "Rails": ["Gemfile"],
    "Gin": ["go.mod"],
    "Actix": ["Cargo.toml"],
    "NestJS": ["nest-cli.json"],
    "Prisma": ["schema.prisma"],
    "SQLAlchemy": ["requirements.txt"],
    "Docker": ["Dockerfile", "docker-compose.yml"],
    "Kubernetes": ["k8s", "helm"],
}


def _detect_languages(file_tree: dict) -> list[str]:
    lang_counts: dict[str, int] = {}
    for meta in file_tree.values():
        lang = meta.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
    return sorted(lang_counts, key=lambda k: lang_counts[k], reverse=True)


def _detect_frameworks(repo_path: Path) -> list[str]:
    detected: list[str] = []
    for framework, signals in _FRAMEWORK_SIGNALS.items():
        for signal in signals:
            if list(repo_path.rglob(signal)):
                if framework not in detected:
                    detected.append(framework)
                break
    return detected


def _build_file_tree(repo_path: Path) -> dict:
    tree: dict = {}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            full_path = Path(root) / fname
            rel_path = str(full_path.relative_to(repo_path))
            ext = full_path.suffix.lower()
            tree[rel_path] = {
                "size": full_path.stat().st_size,
                "type": "file",
                "language": _ext_to_lang(ext) if ext in SUPPORTED_EXTENSIONS else None,
            }
    return tree


def _ext_to_lang(ext: str) -> str:
    mapping = {
        ".py": "python", ".pyw": "python",
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cs": "csharp",
        ".php": "php",
    }
    return mapping.get(ext, "unknown")


async def repo_agent(state: AnalysisState) -> AnalysisState:
    settings = get_settings()
    repo_url = state["repo_url"]
    repo_id = state["repo_id"]

    parts = repo_url.replace("https://github.com/", "").split("/")
    owner, repo_name = parts[0], parts[1]

    clone_dir = Path(settings.repo_clone_base_path) / repo_id
    clone_dir.mkdir(parents=True, exist_ok=True)

    logger.info("repo_agent_start", url=repo_url, clone_dir=str(clone_dir))

    try:
        if (clone_dir / ".git").exists():
            try:
                repo = git.Repo(clone_dir)
                repo.git.clean("-fd")         # remove untracked files/dirs
                repo.git.checkout("--", ".")  # discard local modifications
                repo.remotes.origin.pull()
            except git.GitCommandError:
                # Pull still fails — nuke and re-clone (shallow, fast)
                import shutil
                shutil.rmtree(clone_dir, ignore_errors=True)
                clone_dir.mkdir(parents=True, exist_ok=True)
                repo = git.Repo.clone_from(repo_url, clone_dir, depth=1)
        else:
            repo = git.Repo.clone_from(repo_url, clone_dir, depth=1)

        default_branch = repo.active_branch.name if not repo.head.is_detached else "main"
    except Exception as exc:
        raise RepositoryCloneError(repo_url, str(exc)) from exc

    file_tree = _build_file_tree(clone_dir)
    languages = _detect_languages(file_tree)
    frameworks = _detect_frameworks(clone_dir)

    logger.info(
        "repo_agent_complete",
        owner=owner,
        repo=repo_name,
        files=len(file_tree),
        languages=languages,
    )

    return {
        "local_path": str(clone_dir),
        "owner": owner,
        "repo_name": repo_name,
        "default_branch": default_branch,
        "languages": languages,
        "frameworks": frameworks,
        "file_tree": file_tree,
        "total_files": len(file_tree),
        "current_step": "repo",
        "progress": 0.10,
    }
