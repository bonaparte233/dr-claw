# VibeLab CLI Harness — Standard Operating Procedure

## Overview

VibeLab (also known as Dr.Claw) is a full-stack AI research workspace that lets
teams manage, run, and review conversations with multiple AI providers (Claude,
Cursor, Codex, Gemini) from a single interface.  The platform surfaces a REST
API backed by a Node.js/Express server with SQLite persistence and a React
frontend.

The `cli-anything-vibelab` package wraps that REST API in a stateful, scriptable
Python CLI so that automation scripts, CI pipelines, and agent harnesses can
interact with VibeLab without opening a browser.

---

## Architecture

```
┌─────────────────────────────────────────┐
│  React Frontend  (Vite, port 5173 dev)  │
└────────────────────┬────────────────────┘
                     │ REST / WebSocket
┌────────────────────▼────────────────────┐
│  Express Server  (Node.js, port 3001)   │
│  ├─ /api/auth        JWT auth           │
│  ├─ /api/projects    project management │
│  ├─ /api/settings    API keys / creds   │
│  └─ /api/skills      skill registry     │
└────────────────────┬────────────────────┘
                     │
              ┌──────▼──────┐
              │  SQLite DB  │
              └─────────────┘
```

**Providers supported:** `claude`, `cursor`, `codex`, `gemini`

Session files for each provider are read from:
- `~/.claude/projects/`
- `~/.cursor/chats/`
- `~/.codex/sessions/`
- `~/.gemini/sessions/`

---

## CLI Harness Purpose

The harness exists to:

1. **Script repetitive workflows** — log in, list projects, pull session
   transcripts, rotate API keys, etc., without manual browser interaction.
2. **Feed agent pipelines** — other agents or CI scripts call
   `cli-anything-vibelab` to discover work, fetch conversation context, or
   manage credentials programmatically.
3. **Provide a stable, version-controlled interface** — the Click CLI surface is
   typed and versioned independently of the web UI, so downstream scripts do not
   break when the frontend changes.

---

## Common Workflows

### 1. First-time login

```bash
# Check whether the server needs initial setup
cli-anything-vibelab auth status

# If needsSetup is true, register a user first via the web UI or API directly.
# Then log in:
cli-anything-vibelab auth login --username admin --password s3cr3t
```

The token is stored in `~/.vibelab_session.json` and reused on every subsequent
command.

### 2. List projects and browse sessions

```bash
# List all projects
cli-anything-vibelab projects list

# List conversation sessions for a specific project
cli-anything-vibelab sessions list <project-id>

# Retrieve all messages for a session
cli-anything-vibelab sessions messages <session-id>
```

### 3. Manage API keys

```bash
# List existing keys
cli-anything-vibelab settings api-keys list

# Create a new key
cli-anything-vibelab settings api-keys create "my-automation-key"

# Delete a key by its numeric ID
cli-anything-vibelab settings api-keys delete 42
```

### 4. Rename or delete a project

```bash
cli-anything-vibelab projects rename <project-id> "New Project Name"
cli-anything-vibelab projects delete <project-id>
```

### 5. Machine-readable output

Append `--json` to any command to receive newline-terminated JSON on stdout,
suitable for piping to `jq` or other tools:

```bash
cli-anything-vibelab --json projects list | jq '.[].display_name'
```

### 6. Logout

```bash
cli-anything-vibelab auth logout
```

This deletes the local session file.  The JWT itself is stateless; the server
does not maintain a revocation list, so the token remains valid until it expires.

---

## Configuration

| Variable              | Purpose                                      | Default                    |
|-----------------------|----------------------------------------------|----------------------------|
| `VIBELAB_URL`         | Override the server base URL                 | `http://localhost:3001`    |
| `VIBELAB_TOKEN`       | Provide a token without logging in           | *(read from session file)* |

The `--url URL` CLI flag takes precedence over `VIBELAB_URL`, which in turn
takes precedence over the URL stored in `~/.vibelab_session.json`.

The `VIBELAB_TOKEN` env var lets CI systems inject a token without writing a
session file to disk.

### Session file format

```json
{
  "token": "<jwt>",
  "base_url": "http://localhost:3001",
  "username": "admin"
}
```

Stored at `~/.vibelab_session.json` with mode `0600`.
