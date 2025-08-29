# MCP (Model Context Protocol) - Streamable HTTP

This module provides a sample implementation of a streamable Model Context Protocol (MCP) server using the `fastmcp` library. The main entry point is `mcp_streamable_http.py`.

## What is MCP?
MCP (Model Context Protocol) is a protocol for building modular, composable, and interoperable AI agents and tools. It allows you to define tools and prompts that can be exposed over different transports (HTTP, CLI, etc.) for easy integration and orchestration.

## Features & Capabilities
- **Streamable HTTP Server**: Runs an MCP server with streaming HTTP responses for real-time interaction.
- **Tool Registration**: Easily register Python functions as tools (APIs) that can be called remotely.
- **Prompt Registration**: Register prompt functions for dynamic, prompt-based responses.
- **Extensible**: Add more tools and prompts as needed for your use case.

## Example Tools/Prompts
- `add(a: int, b: int) -> int`: Adds two numbers and returns the result.
- `greet(name: str) -> str`: Returns a greeting for the given name.

## How it Works
- The server is started by running `mcp_streamable_http.py`.
- Tools and prompts are registered using decorators (`@mcp.tool`, `@mcp.prompt`).
- The server exposes these as endpoints over HTTP with streaming support.

## Getting Started
1. **Install dependencies** (see `requirements.txt` or `pyproject.toml`).
2. **Run the server:**
   ```bash
   python mcp_streamable_http.py
   ```
3. **Interact with the server** using HTTP requests to call registered tools/prompts.

## Extending
You can add more tools or prompts by defining Python functions and decorating them with `@mcp.tool` or `@mcp.prompt`.

## Requirements
- Python 3.12+
- `fastmcp` >= 2.11.3

## Files
- `mcp_streamable_http.py`: Main server implementation and tool/prompt registration.
- `requirements.txt` / `pyproject.toml`: Dependency management.

---

For more details, see the code and comments in `mcp_streamable_http.py`.
