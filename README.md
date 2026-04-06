# Jack The Shadow

**Autonomous Cybersecurity CLI Agent** powered by Cloudflare Workers AI.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)
[![PyPI](https://img.shields.io/pypi/v/jshadow)](https://pypi.org/project/jshadow/)

---

## What is Jack?

Jack The Shadow is an enterprise-grade, modular CLI agent for the full
cybersecurity spectrum: **penetration testing**, **CTF challenges**,
**bug bounty hunting**, **security research**, **digital forensics**,
and **OSINT**.

- **30 built-in tools** — bash, file ops, grep, glob, HTTP, web fetch
  (with Cloudflare bypass), web search, git, Python REPL, batch parallel
  execution, CVE lookup, persistent memory, attack plan tracker, payload
  generator, encoder/decoder, network recon, report generator, exploit
  search, wordlist manager, hash analyzer, Shodan integration, and more
- **Human-in-the-Loop (HITL)** — color-coded risk panels (Low → Critical)
  with YOLO mode and granular permission patterns for auto-approve
- **Bilingual** — English (default) and Bahasa Indonesia with casual
  hacker-slang tone
- **Persistent Memory** — save recon findings, credentials, and intel across sessions
- **Attack Planner** — track pentesting phases from recon to reporting
- **MCP support** — connect external tool servers via Model Context Protocol
- **Cost Tracking** — monitor API usage, tokens, and latency per session
- **Rich terminal UI** — ASCII banner, Markdown rendering, interactive
  slash-command menu
- **Session management** — credentials, config, and history in `~/.jshadow/`

## Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/TegarTheGreat/JackTheShadow/main/install.sh | bash
```

### From PyPI

```bash
pip install jshadow
```

### From Source

```bash
git clone https://github.com/TegarTheGreat/JackTheShadow.git
cd JackTheShadow
pip install .
```

## Getting Started

```bash
# Just launch it — Jack handles the rest
jshadow

# Or start with a target already set
jshadow --target 192.168.1.0/24

# With language and model options
jshadow --target example.com --model @cf/meta/llama-3.3-70b-instruct-fp8-fast --lang id
```

On first launch, Jack will ask you to log in with your Cloudflare Workers AI
credentials. You can also skip login and use Jack in offline mode (tools work
but AI responses are unavailable until you `/login`).

## Authentication

Jack uses `~/.jshadow/credentials.json` to store your Cloudflare credentials securely (file permissions: 600).

| Method | How |
|--------|-----|
| `/login` | Interactive — prompted at the `jshadow>` shell |
| `/logout` | Clears stored credentials |
| Env vars | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` (fallback) |

## Configuration

| Variable | Description |
|----------|-------------|
| `JSHADOW_DEFAULT_MODEL` | Default model (default: `@cf/openai/gpt-oss-120b`) |
| `JSHADOW_LANG` | Language: `en` or `id` (default: `en`) |
| `JSHADOW_LOG_LEVEL` | Log level (default: `DEBUG`) |

## Slash Commands

Type `/` at the prompt for an interactive numbered menu, or use directly:

| Command | Description |
|---------|-------------|
| `/login` | Connect Cloudflare AI credentials |
| `/logout` | Clear stored credentials |
| `/yolo` | Toggle auto-approve mode |
| `/clear` | Clear conversation context |
| `/compact` | Compact context (keep last N) |
| `/context` | Show context window usage |
| `/tools` | List available tools |
| `/model` | Switch AI model (numbered list) |
| `/models` | List available models |
| `/lang` | Switch language (en/id) |
| `/target` | Set or change target scope |
| `/history` | List & resume saved sessions |
| `/export` | Export conversation as markdown report |
| `/doctor` | Check pentest tool availability |
| `/cost` | Show API usage statistics |
| `/memory` | View persistent memory / findings |
| `/plan` | View attack plan / task list |
| `/permissions` | Manage auto-approve rules |
| `/mcp` | Manage MCP server connections |
| `/help` | Show command menu |
| `/exit` | Quit (auto-saves session) |

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
| `cve_lookup` | — | NIST NVD CVE search |
| `memory_read` | — | Read persistent memory / findings |
| `memory_write` | — | Save findings to persistent memory |
| `todo_read` | — | Read attack plan / task list |
| `todo_write` | — | Create/update attack plan tasks |
| `git_command` | ✅ | Git operations (status, diff, commit) |
| `doctor_check` | — | Check pentest tool availability |
| `batch_execute` | ✅ | Run multiple tools in parallel |
| `apply_patch` | ✅ | Apply unified diff patches |
| `python_repl` | ✅ | Execute Python code |
| `ask_user` | — | Ask operator a question |
| `mcp_call` | ✅ | Call MCP server tools |
| `payload_generate` | — | Generate injection payloads (SQLi, XSS, SSTI, LFI, etc.) |
| `encode_decode` | — | Encode/decode: base64, URL, hex, HTML, JWT, hashes |
| `network_recon` | ✅ | DNS, WHOIS, port scan, SSL check, traceroute |
| `report_generate` | — | Generate pentest reports from findings |
| `exploit_search` | — | Search Exploit-DB / searchsploit |
| `wordlist_manage` | — | Find, generate, preview wordlists |
| `hash_analyze` | — | Identify, generate, and crack hashes |
| `shodan_recon` | — | Shodan host lookup, search, exploit DB |

## Session Directory

```
~/.jshadow/
├── credentials.json   # Cloudflare auth (chmod 600)
├── config.json        # User preferences (model, language, Shodan API key)
├── permissions.json   # Auto-approve rules per tool
├── sessions/          # Saved conversation history (JSONL)
├── wordlists/         # Custom generated wordlists
└── memory/
    ├── notes.md       # Persistent findings (recon, creds, vulns)
    ├── todos.json     # Attack plan task list
    └── report_*.md    # Generated pentest reports
```

## Architecture

```
src/jack_the_shadow/
├── cli.py              # Entry point + argparse
├── session/            # ~/.jshadow credential & session management
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
git clone https://github.com/TegarTheGreat/JackTheShadow.git
cd JackTheShadow
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This tool is intended for **authorized security testing only**.
Always obtain proper authorization before testing any system.
The authors are not responsible for misuse.
