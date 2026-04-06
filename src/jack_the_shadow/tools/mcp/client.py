"""
Jack The Shadow — MCP Client

MCPServer (single subprocess) and MCPManager (multi-server orchestration).
JSON-RPC 2.0 over stdio transport.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Optional

from jack_the_shadow.tools.mcp.protocol import jsonrpc_request
from jack_the_shadow.utils.logger import get_logger

logger = get_logger("tools.mcp.client")


class MCPServer:
    """Manages a single MCP server subprocess (stdio transport)."""

    def __init__(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env
        self._proc: Optional[subprocess.Popen[bytes]] = None
        self._tools: list[dict[str, Any]] = []
        self._resources: list[dict[str, Any]] = []
        self._initialized = False

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> bool:
        if self.is_running:
            return True
        try:
            cmd = [self.command] + self.args
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
            )
            init_result = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "jshadow", "version": "0.2.0"},
            })
            if init_result is None:
                logger.error("MCP server %s: initialize failed", self.name)
                self.stop()
                return False

            self._send_notification("notifications/initialized")
            self._initialized = True
            self._discover_tools()
            self._discover_resources()

            logger.info(
                "MCP server %s started — %d tools, %d resources",
                self.name, len(self._tools), len(self._resources),
            )
            return True

        except FileNotFoundError:
            logger.error("MCP server %s: command not found: %s", self.name, self.command)
            return False
        except OSError as exc:
            logger.error("MCP server %s: start failed: %s", self.name, exc)
            return False

    def stop(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self._proc.kill()
                except OSError:
                    pass
            self._proc = None
            self._initialized = False
            logger.info("MCP server %s stopped", self.name)

    def list_tools(self) -> list[dict[str, Any]]:
        return self._tools

    def list_resources(self) -> list[dict[str, Any]]:
        return self._resources

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.is_running:
            return {"error": f"MCP server {self.name} is not running"}

        res = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        if res is None:
            return {"error": f"MCP tool call {tool_name} returned no result"}

        if isinstance(res, dict):
            content = res.get("content", [])
            if isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                if texts:
                    return {"output": "\n".join(texts), "is_error": res.get("isError", False)}
            return {"output": json.dumps(res, ensure_ascii=False), "is_error": False}
        return {"output": str(res), "is_error": False}

    def read_resource(self, uri: str) -> dict[str, Any]:
        if not self.is_running:
            return {"error": f"MCP server {self.name} is not running"}

        res = self._send_request("resources/read", {"uri": uri})
        if res is None:
            return {"error": f"Resource read {uri} returned no result"}

        contents = res.get("contents", [])
        texts = []
        for c in contents:
            if "text" in c:
                texts.append(c["text"])
            elif "blob" in c:
                texts.append(f"[binary data: {c.get('mimeType', 'unknown')}]")

        return {"output": "\n".join(texts) if texts else str(res)}

    # ── Private I/O

    def _send_request(
        self, method: str, params: dict[str, Any] | None = None,
    ) -> Any | None:
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            return None

        msg = jsonrpc_request(method, params)
        msg_id = msg["id"]
        payload = json.dumps(msg) + "\n"

        try:
            self._proc.stdin.write(payload.encode("utf-8"))
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            logger.error("MCP %s: write failed: %s", self.name, exc)
            return None

        try:
            while True:
                line = self._proc.stdout.readline()
                if not line:
                    return None
                line = line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    resp = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if resp.get("id") == msg_id:
                    if "error" in resp:
                        logger.error("MCP %s: JSON-RPC error: %s", self.name, resp["error"])
                        return None
                    return resp.get("result")
        except (OSError, ValueError) as exc:
            logger.error("MCP %s: read failed: %s", self.name, exc)
            return None

    def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        if not self._proc or not self._proc.stdin:
            return
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params:
            msg["params"] = params
        payload = json.dumps(msg) + "\n"
        try:
            self._proc.stdin.write(payload.encode("utf-8"))
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def _discover_tools(self) -> None:
        res = self._send_request("tools/list")
        if res and isinstance(res, dict):
            self._tools = res.get("tools", [])
        else:
            self._tools = []

    def _discover_resources(self) -> None:
        res = self._send_request("resources/list")
        if res and isinstance(res, dict):
            self._resources = res.get("resources", [])
        else:
            self._resources = []


class MCPManager:
    """Manages multiple MCP server connections."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPServer] = {}

    def add_server(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> bool:
        if name in self._servers:
            logger.warning("MCP server %s already registered", name)
            return self._servers[name].is_running

        server = MCPServer(name, command, args, env)
        self._servers[name] = server
        return server.start()

    def remove_server(self, name: str) -> None:
        server = self._servers.pop(name, None)
        if server:
            server.stop()

    def get_server(self, name: str) -> MCPServer | None:
        return self._servers.get(name)

    def list_servers(self) -> list[dict[str, Any]]:
        out = []
        for name, server in self._servers.items():
            out.append({
                "name": name,
                "running": server.is_running,
                "tools": [t.get("name", "?") for t in server.list_tools()],
                "resources": len(server.list_resources()),
            })
        return out

    def list_all_tools(self) -> list[dict[str, Any]]:
        tools = []
        for name, server in self._servers.items():
            if server.is_running:
                for tool in server.list_tools():
                    tool_copy = dict(tool)
                    tool_copy["_mcp_server"] = name
                    tools.append(tool_copy)
        return tools

    def call_tool(
        self, server_name: str, tool_name: str, arguments: dict[str, Any],
    ) -> dict[str, Any]:
        server = self._servers.get(server_name)
        if not server:
            return {"error": f"MCP server '{server_name}' not found"}
        if not server.is_running:
            return {"error": f"MCP server '{server_name}' is not running"}
        return server.call_tool(tool_name, arguments)

    def shutdown(self) -> None:
        for server in self._servers.values():
            server.stop()
        self._servers.clear()
        logger.info("All MCP servers stopped")
