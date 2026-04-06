# Jack The Shadow

**Autonomous Penetration-Testing CLI Agent** powered by Cloudflare Workers AI.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## What is Jack?

Jack The Shadow is an enterprise-grade, modular CLI agent that assists
with penetration testing, security assessments, and red-team operations.
It features:

- **11 built-in tools** — bash, file ops, grep, glob, HTTP, web fetch
  (with Cloudflare bypass), web search, and MCP integration
- **Human-in-the-Loop (HITL)** — color-coded risk panels (Low → Critical)
  with YOLO mode for auto-approve
- **Bilingual** — English (default) and Bahasa Indonesia with casual
  hacker-slang tone
- **MCP support** — connect external tool servers via Model Context Protocol
- **Rich terminal UI** — ASCII banner, Markdown rendering, interactive
  slash-command menu

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/JackTheShadow.git
cd JackTheShadow

# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your Cloudflare credentials

# Run
jack --target 192.168.1.0/24
```

## Configuration

| Variable | Description |
|----------|-------------|
| `CLOUDFLARE_ACCOUNT_ID` | Your Cloudflare account ID |
| `CLOUDFLARE_API_TOKEN` | Workers AI API token |
| `JACK_DEFAULT_MODEL` | Default model (default: `@cf/openai/gpt-oss-120b`) |
| `JACK_LANG` | Language: `en` or `id` (default: `en`) |
| `JACK_LOG_LEVEL` | Log level (default: `DEBUG`) |

## Slash Commands

Type `/` at the prompt for an interactive menu, or use directly:

| Command | Description |
|---------|-------------|
| `/yolo` | Toggle auto-approve mode |
| `/clear` | Clear conversation context |
| `/compact` | Compact context (keep last N) |
| `/context` | Show context window usage |
| `/tools` | List available tools |
| `/model` | Switch AI model |
| `/models` | List available models |
| `/lang` | Switch language (en/id) |
| `/target` | Change target scope |
| `/mcp` | Manage MCP server connections |
| `/help` | Show command menu |
| `/exit` | Quit |

## Tools

| Tool | Risk-Aware | Description |
|------|:----------:|-------------|
| `bash_execute` | ✅ | Execute shell commands |
| `file_read` | — | Read file contents |
| `file_write` | ✅ | Create/overwrite files |
| `file_edit` | ✅ | Surgical text replacement |
| `grep_search` | — | Regex search (ripgrep + fallback) |
| `glob_find` | — | Find files by pattern |
| `list_directory` | — | Tree-style listing |
| `http_request` | ✅ | HTTP requests |
| `web_fetch` | — | Fetch URL → Markdown (CF bypass) |
| `web_search` | — | DuckDuckGo search |
| `mcp_call` | ✅ | Call MCP server tools |

## Architecture

```
src/jack_the_shadow/
├── cli.py              # Entry point + argparse
├── config/             # Settings, model catalog, prompts
├── core/               # AI engine, state, orchestrator
├── i18n/               # Bilingual string tables
├── ui/                 # Rich terminal UI components
├── tools/              # Tool system
│   ├── builtin/        # One file per tool
│   └── mcp/            # Model Context Protocol client
├── services/           # External API clients (NVD, etc.)
└── utils/              # Logging, helpers
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This tool is intended for **authorized security testing only**.
Always obtain proper authorization before testing any system.
The authors are not responsible for misuse.
