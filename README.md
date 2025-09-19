# Roundtable AI MCP Server

**Connect to Multiple AI Coding Tools at Once** - Use Codex, Claude, Cursor, and Gemini from one simple interface.

## What You Get

🚀 **Quick Setup** - Install once, use everywhere

🔧 **Works Out of the Box** - Finds and sets up your AI tools automatically. No config files to edit.

🔗 **Same Commands for Everything** - Switch between AI tools without learning different commands

📦 **Works with Popular Editors** - Use it in VS Code, Claude Desktop, Cursor, and 20+ other coding tools

🛡️ **Only Shows Working Tools** - Remembers which AI tools you have installed and only shows the ones that actually work

## Why You Need This

### 1. **Stop Wrestling with Multiple AI Tools**
**The Problem**: Each AI tool (Codex, Claude, Gemini) has different commands, setup steps, and ways to log in. This wastes time switching between them.

**Our Solution**: Roundtable finds your AI tools and lets you use them all the same way. One command, all your AI tools.

### 2. **Use Any AI Tool the Same Way**
**The Problem**: Each AI tool needs different integration code and handles errors differently.

**Our Solution**: All AI tools work exactly the same through Roundtable. Switch tools without changing your code.

### 3. **Know Which Tools Actually Work**
**The Problem**: You waste time trying to use AI tools that aren't installed or configured properly.

**Our Solution**: Roundtable remembers which AI tools work on your system and only shows you the ones that are actually installed.

## Quick Start

```bash
# Install once, access all AI assistants
pip install roundtable-ai

# Check which AI tools are available
roundtable-ai --check

# Start unified AI assistant interface
roundtable-ai

# Use specific assistants only
roundtable-ai --agents codex,gemini
```

## Supported AI Assistants

- **Codex** - Advanced code generation and assistance
- **Claude Code** - Anthropic's Claude with enhanced code capabilities
- **Cursor** - AI-powered code editor integration
- **Gemini** - Google's Gemini AI assistant

*Only assistants that are actually installed and configured will be enabled automatically.*

## Zero-Configuration Intelligence

### Automatic Discovery
- Runs `--help` commands to verify CLI tool availability
- Smart caching saves availability results to avoid repeated checks
- Environment-aware adaptation to different development environments

### Priority-Based Configuration
1. **Command line flags** (`--agents codex,gemini`) - Highest priority
2. **Environment variables** (`CLI_MCP_SUBAGENTS`)
3. **Availability cache** (`~/.roundtable/availability_check.json`)
4. **Defaults** (all available tools) - Lowest priority

## Installation & Usage

### Multiple Installation Options
```bash
# Primary installation method
pip install roundtable-ai

# Multiple command aliases (all equivalent)
roundtable-ai                    # Short and convenient
roundtable-mcp-server           # Descriptive
python -m roundtable_mcp_server # Module execution
```

### Check Available AI Tools
```bash
roundtable-ai --check
```
This command:
- Tests each CLI tool by running `--help` commands
- Saves results to `~/.roundtable/availability_check.json`
- Shows detailed availability report

### Start the Unified Interface
```bash
# Use all available AI assistants
roundtable-ai

# Use only specific assistants
roundtable-ai --agents codex,claude

# Override availability detection
CLI_MCP_IGNORE_AVAILABILITY=true roundtable-ai
```

## MCP Client Integration

### Claude Desktop Configuration
Add to your `~/.config/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

### Universal MCP Compatibility
Works with any MCP-compatible client including:
- Claude Desktop
- VS Code with MCP extensions
- Custom MCP applications
- Future MCP-compatible tools

## IDE & Editor Integration

Roundtable AI MCP Server integrates with **26 different IDEs and AI coding tools**. Below are the installation guides for each platform.

### 🎯 Primary IDEs (Most Popular)

#### 1. **Cursor** - AI-First Code Editor
Create or edit `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

**Alternative using npx:**
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "npx",
      "args": ["-y", "@roundtable/mcp-server"],
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

#### 2. **Claude Code** - Anthropic's Official CLI
Use Claude Code's built-in MCP management:

```bash
# Quick installation
claude mcp add roundtable-ai roundtable-ai

# With specific working directory
claude mcp add roundtable-ai roundtable-ai --env CLI_MCP_WORKING_DIR=/path/to/project

# Verify installation
claude mcp list

# Remove if needed
claude mcp remove roundtable-ai
```

**Manual Configuration** (`~/.config/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

#### 3. **Windsurf** - AI-Powered Development Environment
Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

#### 4. **VS Code** - Microsoft's Editor
Add to your `settings.json` (Ctrl/Cmd + Shift + P → "Open Settings JSON"):

```json
{
  "mcp.servers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

#### 5. **GitHub Copilot** - GitHub's AI Coding Assistant
Add to your GitHub Copilot settings or workspace configuration:

```json
{
  "github.copilot.mcp.servers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

---

### 🖥️ Desktop IDEs

<details>
<summary><b>JetBrains AI Assistant</b> - IntelliJ, PyCharm, WebStorm, etc.</summary>

1. **Settings Path**: `Settings > Tools > AI Assistant > Model Context Protocol (MCP)`
2. **Add New Server**: Click "+" to add new MCP server
3. **Configuration**:
   ```json
   {
     "name": "roundtable-ai",
     "command": "roundtable-ai",
     "transport": "stdio",
     "env": {
       "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
       "CLI_MCP_WORKING_DIR": "/path/to/your/project"
     }
   }
   ```
4. **Apply & Restart**: Apply settings and restart the IDE

</details>

<details>
<summary><b>Visual Studio 2022</b> - Microsoft's Flagship IDE</summary>

Create `mcp_config.json` in your project root:
```json
{
  "servers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "transport": "stdio",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

**Alternative**: Use Extensions > Manage Extensions > Search for "Roundtable AI"

</details>

<details>
<summary><b>Zed</b> - High-Performance Code Editor</summary>

Add to `settings.json` (Cmd/Ctrl + ,):
```json
{
  "context_servers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

**Extension Alternative**: Search for "Roundtable AI" in Zed Extensions

</details>

---

### 💻 CLI Tools

<details>
<summary><b>Gemini CLI</b> - Google's Gemini Command-Line Interface</summary>

Edit `~/.gemini/settings.json`:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Rovo Dev CLI</b> - Atlassian's Development CLI</summary>

Configure via `rovo config` command:
```bash
# Add MCP server
rovo mcp add roundtable-ai roundtable-ai

# Verify
rovo mcp list
```

**Manual configuration** in `~/.rovo/config.json`:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Amazon Q Developer CLI</b> - Amazon's AI Development Assistant</summary>

Edit configuration in `~/.aws/q-developer/config.json`:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Crush</b> - Terminal-Based AI Assistant</summary>

Create or edit `crush.json` in your project:
```json
{
  "mcp": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "transport": "stdio",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Warp</b> - AI-Powered Terminal</summary>

Configure via Warp settings:
1. **Open Settings**: Cmd/Ctrl + ,
2. **Navigate to**: Features > AI > MCP Servers
3. **Add Server**:
   ```json
   {
     "name": "roundtable-ai",
     "command": "roundtable-ai",
     "env": {
       "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
     }
   }
   ```

</details>

---

### 🤖 AI Assistants

<details>
<summary><b>Claude Desktop</b> - Anthropic's Desktop Application</summary>

Edit `~/.config/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Cline</b> - AI Assistant Extension</summary>

**One-Click Install**:
1. Open Cline MCP Server Marketplace
2. Search for "Roundtable AI"
3. Click "Install"

**Manual Configuration** in `cline_mcp_settings.json`:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

</details>

<details>
<summary><b>BoltAI</b> - AI Assistant Application</summary>

1. **Open BoltAI Settings**
2. **Navigate to**: Plugins > MCP Servers
3. **Add New Server**:
   - Name: `roundtable-ai`
   - Command: `roundtable-ai`
   - Environment Variables:
     ```
     CLI_MCP_SUBAGENTS=codex,claude,cursor,gemini
     CLI_MCP_WORKING_DIR=/path/to/your/project
     ```

</details>

<details>
<summary><b>Perplexity Desktop</b> - AI Search and Research Assistant</summary>

Configure in Perplexity settings:
```json
{
  "mcpConfig": {
    "servers": {
      "roundtable-ai": {
        "command": "roundtable-ai",
        "env": {
          "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
        }
      }
    }
  }
}
```

</details>

<details>
<summary><b>Qodo Gen</b> - AI Code Generation and Analysis Tool</summary>

Add to Qodo Gen configuration:
```json
{
  "mcp_servers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
        "CLI_MCP_WORKING_DIR": "/path/to/your/project"
      }
    }
  }
}
```

</details>

---

### 🛠️ Specialized Tools

<details>
<summary><b>Opencode</b> - Open-Source AI Code Editor</summary>

Add to `opencode_config.json`:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

</details>

<details>
<summary><b>OpenAI Codex</b> - OpenAI's Code Generation Model Interface</summary>

Edit `config.toml`:
```toml
[mcp_servers.roundtable-ai]
command = "roundtable-ai"
env = { CLI_MCP_SUBAGENTS = "codex,claude,cursor,gemini" }
```

</details>

<details>
<summary><b>Kiro</b> - AI Development Assistant</summary>

Configure in `~/.kiro/config.json`:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Trae</b> - AI Development Environment</summary>

Add to Trae workspace configuration:
```json
{
  "mcp": {
    "servers": {
      "roundtable-ai": {
        "command": "roundtable-ai",
        "env": {
          "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
          "CLI_MCP_WORKING_DIR": "/path/to/your/project"
        }
      }
    }
  }
}
```

</details>

<details>
<summary><b>LM Studio</b> - Local Language Model Interface</summary>

**One-Click Install**:
1. Navigate to **Program > Install > Edit mcp.json**
2. Search for "Roundtable AI" in marketplace
3. Click "Install"

**Manual Configuration**:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Zencoder</b> - AI-Powered Coding Assistant</summary>

Configure via Zencoder settings panel:
```json
{
  "mcp_configuration": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Augment Code</b> - AI-Powered Code Completion</summary>

Add to Augment Code workspace settings:
```json
{
  "mcpServers": {
    "roundtable-ai": {
      "command": "roundtable-ai",
      "transport": "stdio",
      "env": {
        "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini"
      }
    }
  }
}
```

</details>

<details>
<summary><b>Roo Code</b> - AI Development Environment</summary>

Configure in Roo Code project settings:
```json
{
  "ai_assistants": {
    "mcp_servers": {
      "roundtable-ai": {
        "command": "roundtable-ai",
        "env": {
          "CLI_MCP_SUBAGENTS": "codex,claude,cursor,gemini",
          "CLI_MCP_WORKING_DIR": "/path/to/your/project"
        }
      }
    }
  }
}
```

</details>

---

### 🔧 Configuration Tips

#### Environment Variables Reference
```bash
# Specify which AI assistants to enable
CLI_MCP_SUBAGENTS="codex,claude,cursor,gemini"

# Set working directory for project context
CLI_MCP_WORKING_DIR="/path/to/your/project"

# Enable debug logging
CLI_MCP_DEBUG=true

# Override availability checking
CLI_MCP_IGNORE_AVAILABILITY=true
```

#### Command Alternatives
All IDEs support these equivalent commands:
- `roundtable-ai` (primary command)
- `roundtable-mcp-server` (descriptive alias)
- `python -m roundtable_mcp_server` (Python module)
- `npx @roundtable/mcp-server` (NPM package - coming soon)

#### Verification
After installation, verify the integration works:

```bash
# Check server availability
roundtable-ai --check

# Test connection (varies by IDE)
# Most IDEs will show "Roundtable AI" in their AI assistant panel
```

#### Troubleshooting
1. **Server not found**: Ensure `roundtable-ai` is in your PATH
2. **Permission denied**: Run `chmod +x $(which roundtable-ai)`
3. **Config not loaded**: Check file paths and JSON syntax
4. **No AI tools detected**: Run `roundtable-ai --check` first

## Available MCP Tools

Once integrated, you get access to:

### Availability Checks
- `check_codex_availability` - Verify Codex CLI status
- `check_claude_availability` - Verify Claude Code CLI status
- `check_cursor_availability` - Verify Cursor CLI status
- `check_gemini_availability` - Verify Gemini CLI status

### Unified Task Execution
- `execute_codex_task` - Run coding tasks through Codex
- `execute_claude_task` - Run coding tasks through Claude Code
- `execute_cursor_task` - Run coding tasks through Cursor
- `execute_gemini_task` - Run coding tasks through Gemini

## Advanced Configuration

### Environment Variables
```bash
# Specify which assistants to enable
export CLI_MCP_SUBAGENTS="codex,gemini"

# Set project working directory
export CLI_MCP_WORKING_DIR="/path/to/project"

# Enable all tools regardless of availability
export CLI_MCP_IGNORE_AVAILABILITY=true

# Enable debug logging
export CLI_MCP_DEBUG=true
```

### Command Line Flags
```bash
# Get comprehensive help
roundtable-ai --help

# Check availability and save results
roundtable-ai --check

# Start with specific agents (overrides all other settings)
roundtable-ai --agents cursor,claude
```

## What Teams Get

### Faster Development
- **Quick Setup**: Most teams set up new developers in minutes, not hours
- **Less Debugging**: Fewer "why isn't this AI tool working?" problems
- **Easier Switching**: Try different AI tools on the same problem without hassle
- **Faster Onboarding**: New team members get all AI tools working immediately

### Same Setup Everywhere
- All developers use the same AI tools the same way
- No more "works on my machine" problems with AI tools
- One place to check all AI tool usage

### Works with Future Tools
- Built on MCP standard that major companies support
- Switch AI providers easily without changing your setup
- No vendor lock-in - use any AI tools you want
- New AI tools will work automatically when they support MCP

## Requirements

### System Requirements
- Python 3.8+
- One or more AI CLI tools installed:
  - Codex CLI (for Codex support)
  - Claude Code CLI (for Claude support)
  - Cursor CLI (for Cursor support)
  - Gemini CLI (for Gemini support)

### Dependencies
The server automatically handles all dependencies:
- FastMCP framework for high-performance MCP protocol implementation
- Async/await support for concurrent AI assistant requests
- Intelligent session management and error handling

## How It Works

### Built for Real Use
- **FastMCP Framework** - Fast, reliable MCP server that handles multiple requests
- **Easy to Extend** - Adding new AI tools is straightforward
- **Uses Minimal Resources** - Won't slow down your computer
- **Fails Safely** - If one AI tool breaks, the others keep working

### Keeps Things Working
- Remembers your conversation when switching between AI tools
- Runs commands in the right folder for your project
- Uses your existing AI tool logins - no new passwords to remember
- Handles multiple requests at once without slowing down

## Development & Testing

### Testing the Installation
```bash
# Run the test suite
python -m roundtable_mcp_server.test_server

# Check server functionality
roundtable-ai --check
```

### Building from Source
```bash
git clone https://github.com/askbudi/roundtable
cd roundtable_mcp_server
pip install -e .[dev]
```

### Development Tools
Includes comprehensive development support:
- Black code formatting
- Ruff linting
- MyPy type checking
- Pytest test suite
- Pre-commit hooks

## Troubleshooting

### Common Issues

**No AI tools detected?**
- Run `roundtable-ai --check` to see detailed availability report
- Ensure CLI tools are properly installed and in your PATH
- Check that API keys are configured for tools that require them

**MCP client not connecting?**
- Verify MCP client configuration matches the command aliases
- Check that the working directory is accessible
- Enable debug logging with `CLI_MCP_DEBUG=true`

**Want to force enable specific tools?**
- Use `CLI_MCP_IGNORE_AVAILABILITY=true` to bypass availability checking
- Use `--agents` flag for precise control: `roundtable-ai --agents codex,claude`

### Debug Information
- Debug logs are written to: `roundtable_mcp_server.log`
- Availability cache location: `~/.roundtable/availability_check.json`
- Use `--help` for comprehensive command documentation

## License

GNU Affero General Public License v3

## About Roundtable AI

Roundtable AI develops intelligent infrastructure and tooling solutions to enhance AI-assisted development workflows. We focus on eliminating complexity and friction in developer tools while maintaining the highest standards of reliability and performance.

**Learn more**: [askbudi.ai](https://askbudi.ai)
**Repository**: [github.com/askbudi/roundtable](https://github.com/askbudi/roundtable)
**Support**: support@askbudi.ai

---

*Ready to unify your AI coding assistants? Install `roundtable-ai` and experience zero-configuration AI integration in under 5 minutes.*