"""
Jack The Shadow — Session Management

The ~/.jshadow directory holds credentials, session state, and config.
"""

from jack_the_shadow.session.paths import (  # noqa: F401
    JSHADOW_DIR,
    ensure_session_dir,
    get_credentials_path,
    get_session_dir,
)
from jack_the_shadow.session.auth import (  # noqa: F401
    load_credentials,
    save_credentials,
    clear_credentials,
    is_logged_in,
)
