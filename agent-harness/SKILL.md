---
name: vibelab
description: VibeLab / Dr. Claw workspace skill for project lookup, session inspection, TaskMaster progress, and OpenClaw reporting
---

# VibeLab Research Skill

Use this skill when the user asks about VibeLab or Dr. Claw projects, wants to inspect Claude/Cursor/Codex/Gemini sessions, or needs task progress pushed to OpenClaw/mobile.

## Setup check

Before using VibeLab, verify the server is reachable:

```bash
vibelab server status
```

If needed, start it:

```bash
vibelab server on
```

## Project discovery

```bash
vibelab --json projects list
```

Project references accepted by the CLI:

- `name`
- `displayName`
- filesystem `path` / `fullPath`

If a path exists locally but is not registered yet:

```bash
vibelab projects add /absolute/path/to/project --name "Display Name"
```

## Session workflows

List sessions:

```bash
vibelab --json sessions list <project-ref>
vibelab --json sessions list <project-ref> --provider cursor
```

Fetch messages:

```bash
vibelab --json sessions messages <project-ref> <session-id> --provider claude --limit 100
```

Send Claude a message:

```bash
vibelab --json chat send --project <project-ref> --message "<user message>"
```

List active sessions across projects:

```bash
vibelab --json chat sessions
```

## TaskMaster workflows

Check whether TaskMaster is present:

```bash
vibelab --json taskmaster detect <project-ref>
```

Get progress and next action:

```bash
vibelab --json taskmaster summary <project-ref>
vibelab --json taskmaster next-guidance <project-ref>
```

Initialize `.pipeline` for a project if needed:

```bash
vibelab taskmaster init <project-ref>
```

## OpenClaw / mobile reporting

Configure the default push channel once:

```bash
vibelab openclaw configure --push-channel feishu:<chat_id>
```

Preview a mobile report:

```bash
vibelab --json openclaw report --project <project-ref> --dry-run
```

Send it:

```bash
vibelab openclaw report --project <project-ref>
```

## Recommended operating flow

1. If the user did not specify a project, run `projects list` and resolve the project first.
2. For freeform project questions, use `chat send`.
3. For status/progress questions, prefer `taskmaster summary` and `taskmaster next-guidance`.
4. For proactive mobile updates, use `openclaw report`.
