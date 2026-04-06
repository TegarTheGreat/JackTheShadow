"""
Jack The Shadow — UI Package

Rich terminal UI components, each in its own module.
"""

from jack_the_shadow.ui.console import console  # noqa: F401
from jack_the_shadow.ui.banner import display_banner  # noqa: F401
from jack_the_shadow.ui.messages import (  # noqa: F401
    display_ai_message,
    display_ai_stream,
    display_error,
    display_info,
    display_user_message,
)
from jack_the_shadow.ui.panels import (  # noqa: F401
    display_risk_panel,
    display_yolo_auto_approve,
    display_yolo_toggle,
    prompt_approval,
)
from jack_the_shadow.ui.commands import handle_local_command  # noqa: F401
from jack_the_shadow.ui.prompt import prompt_user, status_spinner  # noqa: F401
