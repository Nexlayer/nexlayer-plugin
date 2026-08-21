# Nexlayer MCP Setup Guide

The Nexlayer MCP (Model Context Protocol) enables direct deployment from your AI coding agent.

## What is Nexlayer MCP?

Nexlayer MCP is a server-side integration that allows AI agents to:
- Deploy applications directly to Nexlayer cloud
- Manage deployments (list, status, logs)
- Generate and validate launchfiles
- Access deployment URLs and status

**MCP URL:** `https://mcp.nexlayer.ai/api/mcp`

## Setup by IDE

### Claude Code

**Installation:**
```bash
npx @nexlayer/mcp-install
```

Or add it manually:
```bash
claude mcp add nexlayer-mcp --transport http https://mcp.nexlayer.ai/api/mcp
```

**Authentication:**
1. Start a new Claude Code session
2. Type `/mcp`
3. Select `nexlayer-mcp` server
4. Select "Authenticate"
5. Sign in with one of the SSO providers
6. You're ready to deploy!

**Usage:**
```
Deploy my application to Nexlayer
```

### Cursor

**Installation:**

Add to `~/.cursor/mcp.json` (or the project's `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "nexlayer-mcp": {
      "transport": "http",
      "url": "https://mcp.nexlayer.ai/api/mcp"
    }
  }
}
```

Verify under Settings → Tools & Integrations → MCP — `nexlayer-mcp` should show a green status indicator.

**Authentication:**
After adding the configuration, you'll be prompted to authenticate. Sign in with one of the SSO providers to complete setup.

**Usage:**
In Cursor chat, ask:
```
Deploy this project to Nexlayer
```

### VS Code with GitHub Copilot

**Installation:**

1. Open Command Palette (`Ctrl+Shift+P` on Windows/Linux, `Cmd+Shift+P` on macOS)
2. Search for "MCP: Add Server"
3. Select **HTTP (HTTP or Server-Sent Events)**
4. Enter server URL: `https://mcp.nexlayer.ai/api/mcp`
5. Enter server ID: `nexlayer-mcp`
6. Select **Global** for configuration target

**Authentication:**
1. You'll be prompted to authenticate with the MCP
2. Select "Allow" then "Open"
3. Sign in with an SSO provider
4. You'll be redirected back to VS Code

**Usage:**
In GitHub Copilot chat:
```
@nexlayer Deploy my application
```

### Windsurf

**Installation:**

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "nexlayer-mcp": {
      "transport": "http",
      "url": "https://mcp.nexlayer.ai/api/mcp"
    }
  }
}
```

### Cline

**Installation:**

Add to your Cline MCP settings:

```json
{
  "mcpServers": {
    "nexlayer-mcp": {
      "serverUrl": "https://mcp.nexlayer.ai/api/mcp",
      "transport": "http"
    }
  }
}
```

## Troubleshooting

### MCP Connection Failed

If the Nexlayer MCP fails to connect or re-connect:

1. **Re-authenticate:** You may need to re-authenticate with the MCP
2. **Check network:** Ensure you have internet access to `mcp.nexlayer.ai`
3. **Restart IDE:** Sometimes a fresh restart resolves connection issues

### Authentication Expired

MCP sessions may expire. If you see authentication errors:

1. Remove the existing MCP configuration
2. Re-add the MCP server
3. Re-authenticate with SSO

### Deployment Failed

If deployment fails via MCP:

1. Validate your `nexlayer.yaml` syntax
2. Check that images exist and are accessible
3. Verify port numbers are valid
4. Review MCP error messages for specific issues

## MCP Commands

Once connected, the Nexlayer MCP provides these capabilities:

| Capability | Description |
|------------|-------------|
| Deploy application | Deploy a launchfile to Nexlayer |
| List deployments | Show all your deployments |
| Get deployment status | Check status of a specific deployment |
| Get deployment logs | View logs from a deployment |
| Delete deployment | Remove a deployment |

## Example Prompts

**Deploy current project:**
```
Deploy this project to Nexlayer as a preview
```

**Deploy with custom name:**
```
Deploy this as "my-awesome-app" to Nexlayer
```

**Check deployment status:**
```
What's the status of my Nexlayer deployment?
```

**Get deployment URL:**
```
What's the URL for my deployed application?
```

**View logs:**
```
Show me the logs from my Nexlayer deployment
```

## Without MCP

If you cannot use MCP, you can deploy manually:

1. **Install Nexlayer CLI:**
   ```bash
   npm install -g nexlayer
   ```

2. **Login:**
   ```bash
   nexlayer login
   ```

3. **Deploy:**
   ```bash
   nexlayer deploy
   ```

This will deploy the `nexlayer.yaml` in your current directory.

## Web Dashboard

You can also manage deployments via the web dashboard:

**URL:** https://app.nexlayer.com

Features:
- View all deployments
- Monitor status and health
- View logs
- Configure custom domains
- Manage secrets
