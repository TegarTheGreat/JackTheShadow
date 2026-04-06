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
    "banner.hint": "Type [bold]/[/bold] for commands, start typing to chat.",
    "banner.tagline": "« Autonomous Penetration-Testing Agent »",
    "banner.no_creds": (
        "[warning]⚠  Cloudflare API credentials not configured.[/]\n"
        "[dim]  Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN "
        "in your environment or .env file.\n"
        "  Running in offline mode — tool system is active but AI "
        "responses are stubbed.[/]"
    ),

    # ── Spinner / status
    "spinner.thinking": "Jack's cooking up something...",
    "spinner.tool_result": "Jack's processing tool results...",

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
    "hitl.cancelled": "  Cancelled by operator.",

    # ── Slash commands
    "cmd.yolo.desc": "Toggle YOLO auto-approve mode",
    "cmd.clear.desc": "Clear conversation context / memory",
    "cmd.help.desc": "Show available commands",
    "cmd.exit.desc": "Quit Jack The Shadow",
    "cmd.model.desc": "Switch AI model",
    "cmd.lang.desc": "Switch language (en/id)",
    "cmd.target.desc": "Change target scope",
    "cmd.context.desc": "Show context window usage",
    "cmd.tools.desc": "List available tools",
    "cmd.models.desc": "List available AI models",
    "cmd.compact.desc": "Compact context (keep last N messages)",

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

    # ── Offline stub
    "offline.response": (
        "*[Offline Mode]* No API credentials configured.\n\n"
        "Set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` "
        "in your environment or `.env` file.\n\n"
        "You said: **{input}**\nTarget: `{target}`"
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
