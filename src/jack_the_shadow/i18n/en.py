"""
Jack The Shadow — English String Table

Casual, slang-heavy hacker tone — like a streetwise Claude.
"""

STRINGS: dict[str, str] = {
    # ── Banner & startup
    "banner.target": "Target",
    "banner.model": "Model",
    "banner.yolo": "YOLO",
    "banner.lang": "Lang",
    "banner.no_target": "Not set — use /target or tell Jack",
    "banner.hint": "Type [bold]/[/bold] for commands, start typing to chat with Jack.",
    "banner.tagline": "« Autonomous Cybersecurity Agent »",
    "banner.no_creds": (
        "[warning]⚠  No Cloudflare AI connection.[/]\n"
        "[dim]  Use [bold]/login[/bold] to connect your Cloudflare account.\n"
        "  Tools still work, but Jack can't think without an AI backend.[/]"
    ),

    # ── Auth gate (startup)
    "auth.gate_header": "🔐 First things first — you need to connect your AI backend.",
    "auth.gate_body": (
        "Jack needs Cloudflare Workers AI credentials to think.\n"
        "  You can get these from: https://dash.cloudflare.com → AI → Workers AI"
    ),
    "auth.skipped": "No worries, running in offline mode. Use /login anytime to connect.",
    "auth.connected": "🟢 Connected to Cloudflare Workers AI",

    # ── Welcome message
    "welcome.message": (
        "  [bold cyan]What's the play?[/]\n"
        "  [dim]Drop a target, describe a CTF challenge, ask about a CVE,\n"
        "  or just tell Jack what you need. Use /target to lock scope.[/]"
    ),

    # ── Spinner / status
    "spinner.thinking": "Jack's cooking up something...",
    "spinner.tool_result": "Jack's processing tool results...",

    # ── AI responses
    "ai.empty_response": "(Jack didn't produce a response.)",

    # ── YOLO mode
    "yolo.on_title": "☠  DANGER ZONE",
    "yolo.on_body": (
        "[warning]⚡ YOLO MODE ACTIVE ⚡[/]\n"
        "All tool executions will be auto-approved. No safety net.\n"
        "Type /yolo again to come back to your senses."
    ),
    "yolo.off_title": "✓ Safe Mode",
    "yolo.off_body": (
        "[green]YOLO mode deactivated.[/]\n"
        "Back to manual approval. Smart move."
    ),
    "yolo.auto_approve": "  ⚡ [YOLO MODE] Auto-approving...",

    # ── HITL approval
    "hitl.header": "⚠  ACTION REQUIRED",
    "hitl.risk": "RISK",
    "hitl.wants_to_run": "Jack wants to execute",
    "hitl.prompt": "  Allow Jack to execute? [Y/n]: ",
    "hitl.prompt_title": "Allow execution?",
    "hitl.cancelled": "  Cancelled by operator.",

    # ── Slash commands
    "cmd.yolo.desc": "Toggle YOLO auto-approve mode",
    "cmd.clear.desc": "Clear conversation context / memory",
    "cmd.help.desc": "Show available commands",
    "cmd.exit.desc": "Quit Jack The Shadow",
    "cmd.model.desc": "Switch AI model",
    "cmd.lang.desc": "Switch language (en/id)",
    "cmd.target.desc": "Set or change target scope",
    "cmd.context.desc": "Show context window usage",
    "cmd.tools.desc": "List available tools",
    "cmd.models.desc": "List available AI models",
    "cmd.compact.desc": "Compact context (keep last N messages)",
    "cmd.history.desc": "List & resume saved sessions",
    "cmd.export.desc": "Export conversation as markdown report",
    "cmd.doctor.desc": "Check pentest tool availability",
    "cmd.cost.desc": "Show API usage statistics",
    "cmd.memory.desc": "View persistent memory / findings",
    "cmd.plan.desc": "View attack plan / task list",
    "cmd.permissions.desc": "Manage auto-approve rules",

    # ── Login / Logout
    "cmd.login.desc": "Connect Cloudflare AI credentials",
    "cmd.logout.desc": "Disconnect / clear stored credentials",
    "login.already_logged_in": "You're already logged in.",
    "login.source": "Credentials loaded from: {source}",
    "login.overwrite_prompt": "Overwrite existing credentials? [y/N]: ",
    "login.instruction": "Enter your Cloudflare Workers AI credentials.",
    "login.empty_fields": "Account ID and API Token cannot be empty.",
    "login.success": "Credentials saved to ~/.jshadow/credentials.json",
    "login.reconnect_hint": "Jack will reconnect automatically — no restart needed.",
    "logout.success": "Credentials cleared. You're now logged out.",
    "logout.not_logged_in": "No stored credentials found.",

    # ── Context
    "context.title": "Context Window",
    "context.messages": "Messages",
    "context.limit": "Limit",

    # ── Tool output
    "tool.call": "Tool call",
    "tool.denied": "User denied execution.",
    "tool.timeout": "Command timed out after {timeout}s",
    "tool.max_rounds": "Jack hit the tool-call limit ({limit} rounds). Breaking loop.",

    # ── Goodbye
    "goodbye": "👋 Jack fades into the shadows...",

    # ── Offline hint (shown when user types but no AI connected)
    "offline.hint": (
        "Jack's brain isn't connected yet. Use [bold]/login[/bold] to hook up "
        "Cloudflare Workers AI, or set env vars."
    ),

    # ── Language switch
    "lang.switched": "Language switched to English.",
    "lang.invalid": "Invalid language. Use: /lang en  or  /lang id",

    # ── Model switch
    "model.switched": "Model switched to: {model}",
    "model.invalid": "Unknown model. Use /models to see available options.",

    # ── Target
    "target.switched": "Target changed to: {target}",
    "target.usage": "Usage: /target <new_target>",

    # ── MCP
    "cmd.mcp.desc": "Manage MCP server connections",
    "mcp.title": "MCP Servers",
    "mcp.no_servers": "No MCP servers connected. Use: /mcp add <name> <command> [args...]",
    "mcp.added": "MCP server '{name}' connected — {tools} tools discovered.",
    "mcp.add_failed": "Failed to start MCP server '{name}'.",
    "mcp.removed": "MCP server '{name}' disconnected.",
    "mcp.usage": "Usage: /mcp add <name> <command> [args...] | /mcp remove <name> | /mcp list",
}
