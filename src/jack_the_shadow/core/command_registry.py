"""
Jack The Shadow — Command Registry

Typed command system inspired by claude-code. Each command is a dataclass
with metadata (name, aliases, category, enabled). Registry supports
alias-aware lookup and fuzzy search for autocomplete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Optional


@dataclass
class Command:
    """A registered slash command."""

    name: str                                       # e.g. "/model"
    description: str                                # Short description
    category: str = "general"                       # session / tools / config / …
    aliases: list[str] = field(default_factory=list)  # e.g. ["/m"]
    immediate: bool = False                         # bypass queue (UI-only cmds)
    enabled: Callable[[], bool] = field(default=lambda: True)
    execute: Optional[Callable[[str, Any], Any]] = None  # (arg, state) -> ...

    @property
    def all_names(self) -> list[str]:
        return [self.name] + self.aliases


class CommandRegistry:
    """Centralised registry for all slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}   # name → Command
        self._aliases: dict[str, str] = {}         # alias → canonical name

    def register(self, cmd: Command) -> None:
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._aliases[alias] = cmd.name

    def find(self, name: str) -> Optional[Command]:
        """Find a command by name or alias."""
        name = name.lower()
        if name in self._commands:
            return self._commands[name]
        canonical = self._aliases.get(name)
        if canonical:
            return self._commands.get(canonical)
        return None

    def all(self) -> list[Command]:
        """Return all registered commands in insertion order."""
        return list(self._commands.values())

    def fuzzy_search(self, query: str, limit: int = 10) -> list[Command]:
        """Fuzzy-match commands by name, alias, and description.

        Weighted: name=3x, alias=2x, description=0.5x.
        """
        query = query.lower().lstrip("/")
        if not query:
            return self.all()

        scored: list[tuple[float, Command]] = []
        for cmd in self._commands.values():
            # Name match (3x weight)
            name_score = SequenceMatcher(None, query, cmd.name.lstrip("/")).ratio() * 3.0

            # Alias match (2x weight)
            alias_score = 0.0
            for alias in cmd.aliases:
                s = SequenceMatcher(None, query, alias.lstrip("/")).ratio() * 2.0
                alias_score = max(alias_score, s)

            # Description match (0.5x weight)
            desc_score = SequenceMatcher(None, query, cmd.description.lower()).ratio() * 0.5

            # Prefix bonus (exact start match gets a big boost)
            prefix_bonus = 0.0
            if cmd.name.lstrip("/").startswith(query):
                prefix_bonus = 5.0
            for alias in cmd.aliases:
                if alias.lstrip("/").startswith(query):
                    prefix_bonus = max(prefix_bonus, 4.0)

            total = name_score + alias_score + desc_score + prefix_bonus
            if total > 0.5:
                scored.append((total, cmd))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [cmd for _, cmd in scored[:limit]]

    def completions_for(self, prefix: str) -> list[tuple[str, str]]:
        """Return (command, description) tuples matching a prefix.

        Used by the prompt autocompleter.
        """
        prefix = prefix.lower()
        results: list[tuple[str, str]] = []
        for cmd in self._commands.values():
            for n in cmd.all_names:
                if n.startswith(prefix):
                    results.append((cmd.name, cmd.description))
                    break
        return results
