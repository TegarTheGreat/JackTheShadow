"""
Jack The Shadow — Risk & YOLO Panels + Approval Prompt

Colour-coded risk panels and the HITL approval flow.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text

from jack_the_shadow.i18n import t
from jack_the_shadow.ui.console import console
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("ui.panels")

_RISK_STYLES = {
    "low": "risk.low", "medium": "risk.medium",
    "high": "risk.high", "critical": "risk.critical",
}
_RISK_BORDER = {
    "low": "green", "medium": "yellow",
    "high": "dark_orange", "critical": "red",
}


def display_risk_panel(action: str, detail: str, risk_level: str) -> None:
    level = risk_level.lower()
    style = _RISK_STYLES.get(level, "bold white")
    border = _RISK_BORDER.get(level, "white")

    header = Text()
    header.append(f"{t('hitl.header')} — {t('hitl.risk')}: ", style="bold")
    header.append(risk_level.upper(), style=style)

    body = Text()
    body.append(f"\n{t('hitl.wants_to_run')} ", style="white")
    body.append(action, style="bold white")
    body.append(":\n\n", style="white")
    body.append(f"  {detail}\n", style="bold white")

    console.print()
    console.print(Panel(body, title=header, border_style=border, padding=(1, 2)))


def display_yolo_toggle(active: bool) -> None:
    if active:
        console.print(Panel(
            t("yolo.on_body"),
            border_style="red",
            title=f"[warning blink]{t('yolo.on_title')}[/]",
            padding=(1, 2),
        ))
    else:
        console.print(Panel(
            t("yolo.off_body"),
            border_style="green",
            title=f"[green]{t('yolo.off_title')}[/]",
            padding=(1, 2),
        ))


def display_yolo_auto_approve(action: str) -> None:
    console.print(f"[warning]{t('yolo.auto_approve')}[/]")


def prompt_approval(action: str, detail: str, risk_level: str) -> bool:
    """Show risk panel and ask for user approval."""
    display_risk_panel(action, detail, risk_level)
    try:
        answer = console.input(f"[bold white]{t('hitl.prompt')}[/]").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print(f"\n[dim]{t('hitl.cancelled')}[/]")
        return False
    approved = answer in ("", "y", "yes")
    logger.info("Approval: %s [%s] → %s", action, risk_level, "OK" if approved else "DENIED")
    return approved
