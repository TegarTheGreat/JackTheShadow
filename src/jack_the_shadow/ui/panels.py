"""
Jack The Shadow — Risk & YOLO Panels + Approval Prompt

Colour-coded risk panels and the HITL approval flow.
Uses interactive selector instead of manual text input.
All panels expand to full terminal width.
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

    # Truncate very long commands for display, show full in collapsed form
    display_detail = detail if len(detail) <= 500 else detail[:500] + "..."
    body.append(f"  {display_detail}\n", style="bold white")

    console.print()
    console.print(Panel(body, title=header, border_style=border, expand=True, padding=(1, 2)))


def display_yolo_toggle(active: bool) -> None:
    if active:
        console.print(Panel(
            t("yolo.on_body"),
            border_style="red",
            title=f"[warning blink]{t('yolo.on_title')}[/]",
            expand=True,
            padding=(1, 2),
        ))
    else:
        console.print(Panel(
            t("yolo.off_body"),
            border_style="green",
            title=f"[green]{t('yolo.off_title')}[/]",
            expand=True,
            padding=(1, 2),
        ))


def display_yolo_auto_approve(action: str) -> None:
    console.print(f"[warning]{t('yolo.auto_approve')}[/]")


def prompt_approval(action: str, detail: str, risk_level: str) -> bool:
    """Show risk panel and ask for user approval via interactive selector.

    Options:
      - Yes          → approve this single call
      - Yes for all  → auto-approve this tool pattern (adds permission rule)
      - No           → deny
    """
    from jack_the_shadow.ui.selector import interactive_select

    display_risk_panel(action, detail, risk_level)

    options = [
        "✓  Ya / Yes",
        "✓✓ Ya untuk semua (auto-approve tool ini) / Yes for all",
        "✗  Tidak / No",
    ]

    try:
        idx = interactive_select(options, title=t("hitl.prompt_title"))
    except (EOFError, KeyboardInterrupt):
        console.print(f"\n[dim]{t('hitl.cancelled')}[/]")
        return False

    if idx == 0:
        logger.info("Approval: %s [%s] → OK (single)", action, risk_level)
        return True

    if idx == 1:
        # Add a wildcard allow rule for this tool
        from jack_the_shadow.core.permissions import add_permission_rule
        add_permission_rule(action, "*")
        console.print(f"[info]  ✓ Auto-approve rule added: {action}(*)[/]")
        logger.info("Approval: %s [%s] → OK (rule: *)", action, risk_level)
        return True

    # idx == 2 or None (ESC)
    logger.info("Approval: %s [%s] → DENIED", action, risk_level)
    return False
