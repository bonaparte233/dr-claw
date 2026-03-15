# VibeLab CLI Harness - Standard Operating Procedure

## Overview

VibeLab, now also branded as Dr. Claw, is a full-stack AI research workspace for managing multi-provider coding and research sessions. The Python `vibelab` CLI exposes the same server capabilities for automation, OpenClaw integration, and mobile status reporting.

## Core workflows

### Authentication

```bash
vibelab auth status
vibelab auth login --username admin --password s3cr3t
vibelab auth logout
```

### Projects

```bash
vibelab projects list
vibelab projects add /absolute/path/to/project --name "My Project"
vibelab projects rename <project-ref> "New Display Name"
vibelab projects delete <project-ref>
```

`<project-ref>` may be a project `name`, `displayName`, or filesystem path.

### Sessions and chat

```bash
vibelab sessions list <project-ref>
vibelab sessions list <project-ref> --provider cursor --limit 20 --offset 0
vibelab sessions messages <project-ref> <session-id> --provider claude --limit 100
vibelab chat sessions --project <project-ref>
vibelab chat send --project <project-ref> --message "What changed?"
vibelab chat send --project <project-ref> --session <session-id> --message "Continue"
```

`chat send` resolves the project reference to a real filesystem path before opening the websocket, and waits for explicit completion events instead of using a silence timeout.

### TaskMaster / pipeline progress

```bash
vibelab taskmaster status
vibelab taskmaster detect <project-ref>
vibelab taskmaster detect-all
vibelab taskmaster init <project-ref>
vibelab taskmaster tasks <project-ref>
vibelab taskmaster next <project-ref>
vibelab taskmaster next-guidance <project-ref>
vibelab taskmaster summary <project-ref>
```

The server now also exposes a dedicated summary route, so OpenClaw and other agents can fetch one stable progress payload instead of stitching together multiple endpoints.

### OpenClaw / mobile reporting

```bash
vibelab openclaw install
vibelab openclaw configure --push-channel feishu:<chat_id>
vibelab openclaw report --project <project-ref> --dry-run
vibelab openclaw report --project <project-ref>
```

`openclaw report` generates a concise status digest with counts, next task, required inputs, suggested skills, and optional next-action prompt text.

## Server contract notes

Important server routes used by the CLI:

- `GET /api/projects`
- `POST /api/projects`
- `PUT /api/projects/:projectName/rename`
- `GET /api/projects/:projectName/sessions`
- `GET /api/projects/:projectName/sessions/:sessionId/messages`
- `GET /api/taskmaster/installation-status`
- `GET /api/taskmaster/detect/:projectName`
- `GET /api/taskmaster/detect-all`
- `POST /api/taskmaster/initialize/:projectName`
- `GET /api/taskmaster/tasks/:projectName`
- `GET /api/taskmaster/next/:projectName`
- `GET /api/taskmaster/next-guidance/:projectName`
- `GET /api/taskmaster/summary/:projectName`
- WebSocket: `/ws?token=<jwt>`

## JSON mode

Use `--json` whenever OpenClaw or another agent needs machine-readable output:

```bash
vibelab --json projects list
vibelab --json sessions list <project-ref> --provider codex
vibelab --json taskmaster summary <project-ref>
vibelab --json openclaw report --project <project-ref> --dry-run
```
