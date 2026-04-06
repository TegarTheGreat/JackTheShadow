from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional
from jack_the_shadow.tools.base import BaseTool
from jack_the_shadow.tools.helpers import result
from jack_the_shadow.utils.logger import get_logger

if TYPE_CHECKING:
    from jack_the_shadow.tools.executor import ToolExecutor

logger = get_logger("tools.ask")

class AskUserTool(BaseTool):
    name = "ask_user"
    description = "Ask the user a question and wait for their response. Use when you need clarification, a decision, or input before proceeding."
    risk_aware = False

    @classmethod
    def parameters_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to ask the user."},
                "choices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional multiple-choice options.",
                },
            },
            "required": ["question"],
        }


def handle_ask_user(
    executor: "ToolExecutor",
    question: str,
    choices: Optional[list[str]] = None,
) -> dict[str, str]:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    
    try:
        console.print()
        console.print(Panel(question, title="[cyan]🤔 Jack needs your input[/]", border_style="cyan"))
        
        if choices:
            for i, choice in enumerate(choices, 1):
                console.print(f"  [bold]{i}.[/] {choice}")
            console.print()
            try:
                import readline
            except ImportError:
                pass
            raw = input("  Your choice (number or text): ").strip()
            # Try to parse as number
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(choices):
                    answer = choices[idx]
                else:
                    answer = raw
            except ValueError:
                answer = raw
        else:
            console.print()
            try:
                import readline
            except ImportError:
                pass
            answer = input("  Your answer: ").strip()
        
        logger.info("User answered: %s", answer)
        return result("success", output=answer)
    except (KeyboardInterrupt, EOFError):
        return result("error", message="User cancelled the question.")
