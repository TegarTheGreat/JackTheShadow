"""
Jack The Shadow — Rich Console & Theme

Singleton console instance and colour theme used by all UI modules.
Uses full terminal width for immersive fullscreen feel.
"""

from rich.console import Console
from rich.theme import Theme

THEME = Theme({
    "user": "bold cyan",
    "jack": "bold green",
    "warning": "bold red",
    "info": "bold blue",
    "dim": "dim white",
    "risk.low": "bold green",
    "risk.medium": "bold yellow",
    "risk.high": "bold dark_orange",
    "risk.critical": "bold red blink",
    "menu.cmd": "bold cyan",
    "menu.desc": "dim white",
    "phase": "bold magenta",
    "separator": "dim cyan",
})

console = Console(theme=THEME, highlight=False)
