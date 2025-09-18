# Roundtable AI MCP Server

An MCP (Model Context Protocol) server that exposes CLI subagents (Codex, Claude, Cursor, Gemini) for AI assistant integration.

## Overview

This package provides a standalone MCP server that allows AI assistants to execute tasks through various CLI providers. It was developed by Roundtable AI to enable seamless integration between AI assistants and powerful coding tools.

## Features

- **Multiple CLI Providers**: Support for Codex, Claude Code, Cursor Agent, and Gemini CLI
- **Availability Checking**: Check which CLI providers are available and configured
- **Task Execution**: Execute coding tasks through any available CLI provider
- **Streaming Support**: Real-time streaming of agent responses and tool usage
- **MCP Protocol**: Standard MCP interface for integration with any MCP client

## Installation

```bash
pip install roundtable-ai
```

## Usage

### Running the Server

```bash
# As a module
python -m roundtable_mcp_server

# Or directly
roundtable-mcp-server
```

### Configuration

Configure via environment variables:

```bash
# Enable specific subagents (default: all enabled)
export CLI_SUBAGENTS="codex,claude,cursor,gemini"

# Set default working directory
export CLI_WORKING_DIR="/path/to/project"
```

### Available MCP Tools

#### Availability Checks
- `check_codex_availability` - Check if Codex CLI is available
- `check_claude_availability` - Check if Claude Code CLI is available
- `check_cursor_availability` - Check if Cursor Agent CLI is available
- `check_gemini_availability` - Check if Gemini CLI is available

#### Task Execution
- `execute_codex_task` - Execute a task using Codex CLI
- `execute_claude_task` - Execute a task using Claude Code CLI
- `execute_cursor_task` - Execute a task using Cursor Agent CLI
- `execute_gemini_task` - Execute a task using Gemini CLI

## Requirements

This server requires the underlying CLI tools to be installed and configured:

- **Codex**: Requires Codex CLI setup
- **Claude Code**: Requires Claude Code CLI and API key
- **Cursor Agent**: Requires Cursor Agent CLI setup
- **Gemini**: Requires Gemini CLI and API key

## Integration

### With Claude Code

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-mcp-server",
      "env": {
        "CLI_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

### With Other MCP Clients

The server follows the standard MCP protocol and can be integrated with any MCP-compatible client.

## Development

### Testing

```bash
python -m roundtable_mcp_server.test_server
```

### Building from Source

```bash
git clone https://github.com/askbudi/roundtable
cd roundtable_mcp_server
pip install -e .[dev]
```

## Architecture

The package includes:
- `roundtable_mcp_server/` - Main MCP server implementation
- `claudable_helper/` - CLI adapter implementations for various providers
- `cli_subagent.py` - Integration layer for TinyAgent compatibility

## License

GNU Affero General Public License v3

## About Roundtable AI

Roundtable AI develops tools and infrastructure to enhance AI-assisted development workflows. Visit us at [askbudi.ai](https://askbudi.ai) for more information.