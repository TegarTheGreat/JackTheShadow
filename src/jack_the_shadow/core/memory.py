"""
Jack The Shadow — Memory Discovery

Auto-discovers JSHADOW.md files (user-global, project-level, cwd)
and injects them into the system prompt as persistent context.
Inspired by claude-code's CLAUDE.md discovery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from jack_the_shadow.session.paths import JSHADOW_DIR
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("core.memory")

# File names we look for (case-insensitive)
_MEMORY_FILENAMES = {"jshadow.md", "JSHADOW.md", ".jshadow.md"}

# Max bytes to inject from a single memory file
_MAX_MEMORY_SIZE = 8_000


def discover_memory_files(project_dir: Optional[Path] = None) -> list[Path]:
    """Find JSHADOW.md files in the standard hierarchy.

    Search order (first found wins per level):
    1. User-global: ``~/.jshadow/JSHADOW.md``
    2. Project-level: ``<project_dir>/.jshadow/JSHADOW.md``
    3. Project root: ``<project_dir>/JSHADOW.md``
    4. CWD (if different from project_dir)
    """
    found: list[Path] = []

    # 1. User-global
    global_md = JSHADOW_DIR / "JSHADOW.md"
    if global_md.is_file():
        found.append(global_md)

    # 2 + 3. Project-level
    if project_dir is None:
        project_dir = _find_project_root()

    if project_dir:
        for name in _MEMORY_FILENAMES:
            project_jshadow = project_dir / ".jshadow" / name
            if project_jshadow.is_file() and project_jshadow not in found:
                found.append(project_jshadow)
                break

        for name in _MEMORY_FILENAMES:
            project_root_md = project_dir / name
            if project_root_md.is_file() and project_root_md not in found:
                found.append(project_root_md)
                break

    # 4. CWD (if different)
    cwd = Path.cwd()
    if cwd != project_dir:
        for name in _MEMORY_FILENAMES:
            cwd_md = cwd / name
            if cwd_md.is_file() and cwd_md not in found:
                found.append(cwd_md)
                break

    # Also check persistent memory notes
    notes = JSHADOW_DIR / "memory" / "notes.md"
    if notes.is_file() and notes.stat().st_size > 0 and notes not in found:
        found.append(notes)

    logger.debug("Discovered %d memory files: %s", len(found), [str(p) for p in found])
    return found


def build_memory_prompt(project_dir: Optional[Path] = None) -> str:
    """Build a combined memory section for the system prompt.

    Returns an empty string if no memory files are found.
    """
    files = discover_memory_files(project_dir)
    if not files:
        return ""

    sections: list[str] = []
    for path in files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content) > _MAX_MEMORY_SIZE:
                content = content[:_MAX_MEMORY_SIZE] + "\n... (truncated)"
            label = _friendly_path(path)
            sections.append(f"### {label}\n{content.strip()}")
        except OSError as exc:
            logger.warning("Failed to read memory file %s: %s", path, exc)

    if not sections:
        return ""

    return (
        "\n\n## Persistent Memory\n"
        "The following notes were saved from previous sessions "
        "or configured by the operator:\n\n"
        + "\n\n".join(sections)
    )


def _find_project_root() -> Optional[Path]:
    """Walk up from CWD to find a project root (has .git or .jshadow)."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists() or (parent / ".jshadow").exists():
            return parent
        if parent == parent.parent:
            break
    return cwd


def _friendly_path(path: Path) -> str:
    """Return a short label for the memory file."""
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)
