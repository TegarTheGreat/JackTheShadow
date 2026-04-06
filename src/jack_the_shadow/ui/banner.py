"""
Jack The Shadow — ASCII Banner

The startup banner with session info.
"""

from __future__ import annotations

from jack_the_shadow.i18n import t
from jack_the_shadow.ui.console import console
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("ui.banner")

_BANNER = r"""
[bold red]
     ██╗ █████╗  ██████╗██╗  ██╗
     ██║██╔══██╗██╔════╝██║ ██╔╝
     ██║███████║██║     █████╔╝
██   ██║██╔══██║██║     ██╔═██╗
╚█████╔╝██║  ██║╚██████╗██║  ██╗
 ╚════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝[/]
[dim white]  ╔══════════════════════════════════════╗
  ║[/] [bold white]T H E   S H A D O W[/] [dim white]║
  ╚══════════════════════════════════════╝[/]
[dim]  {tagline}[/]
[dim]  ─────────────────────────────────────────[/]
"""


def display_banner(state: "AppState") -> None:  # noqa: F821
    """Print the startup banner with session info."""
    from jack_the_shadow.core.state import AppState  # avoid circular

    console.print(_BANNER.format(tagline=t("banner.tagline")))
    yolo_str = "[warning]ON[/]" if state.yolo_mode else "[green]OFF[/]"
    target_str = state.target if state.target else f"[dim]{t('banner.no_target')}[/]"
    console.print(
        f"  [info]{t('banner.target')}:[/] {target_str}   "
        f"[info]{t('banner.model')}:[/] {state.model}   "
        f"[info]{t('banner.yolo')}:[/] {yolo_str}   "
        f"[info]{t('banner.lang')}:[/] {state.language.upper()}"
    )
    console.print(f"  [dim]{t('banner.hint')}[/]\n")
    logger.info("Banner displayed — target=%s model=%s", state.target or "(none)", state.model)
