---
name: dr-claw
description: Dr. Claw skill for OpenClaw project discovery, idea intake, waiting-session triage, session replies, workflow control, and mobile reporting through the local vibelab CLI.
---

# Dr. Claw for OpenClaw

Use this skill when OpenClaw needs to operate Dr. Claw from chat or mobile, especially for:
- listing Dr. Claw projects
- finding sessions waiting for response
- replying into a session on the user's behalf
- continuing, approving, rejecting, retrying, or resuming workflows
- creating a new project from a fresh idea
- generating daily or per-project digests

## Preconditions

Before running VibeLab commands:

```bash
vibelab server status
```

If the server is not running:

```bash
vibelab server on
```

## Core operating rule

Prefer direct CLI facts over model guesses. For stateful operations, return the raw CLI result first, then summarize for the user.

When calling OpenClaw locally from automation or shell, use:

```bash
./scripts/openclaw_vibelab_turn.sh
```

This serializes `openclaw agent --local` calls per agent and avoids session-lock collisions.

## Project discovery

List projects:

```bash
vibelab projects list
```

Create a new empty project workspace:

```bash
vibelab projects create /absolute/path/to/project --name "Display Name" --json
```

Create a new project from a fresh idea and immediately start discussion:

```bash
vibelab projects idea /absolute/path/to/project --name "Display Name" --idea "<idea text>" --json
```

Use `projects idea` for the “I suddenly have an idea” flow.

## Session lookup and waiting triage

List known sessions for one project:

```bash
vibelab chat sessions --project <project> --json
```

List waiting sessions across all projects or one project:

```bash
vibelab chat waiting --json
vibelab chat waiting --project <project> --json
```

Recommended triage flow:
1. Resolve the project first if needed.
2. Use `chat waiting --json` to find actionable sessions.
3. Use `chat sessions --project ... --json` when the user wants more detail.

## Replying to an existing session

Once the user chooses a session:

```bash
vibelab chat reply --project <project> --session <session-id> -m "<message>" --json
```

Do not ask for provider. `chat reply` derives the provider from the stored session.

Immediately after replying, check whether the session is still processing:

```bash
vibelab chat waiting --project <project> --json
```

If you need to wait until the session leaves the waiting list, use:

```bash
./scripts/vibelab_wait_until_clear.sh --project <project> --session <session-id>
```

The script returns JSON indicating whether the session cleared or timed out.

## Workflow control

Use these commands for workflow actions:

```bash
vibelab workflow status --project <project> --json
vibelab workflow continue --project <project> --session <session-id> -m "<instruction>" --json
vibelab workflow approve --project <project> --session <session-id> --json
vibelab workflow reject --project <project> --session <session-id> -m "<reason>" --json
vibelab workflow retry --project <project> --session <session-id> --json
vibelab workflow resume --project <project> --session <session-id> --json
```

## Digests and reporting

Daily digest:

```bash
vibelab digest daily --json
```

Per-project digest:

```bash
vibelab digest project --project <project> --json
```

Artifacts and workflow state:

```bash
vibelab workflow status --project <project> --json
vibelab taskmaster artifacts --project <project> --json
```

## Response format guidance for mobile / chat

Keep replies compact:
- first line: direct answer
- then: short project / session / status bullets if relevant
- always include exact session ids when asking the user to choose one
- when reporting a post-reply state, say whether the session is still processing or has cleared

## Reliable OpenClaw patterns

Pattern: list projects
1. Run `vibelab projects list`.
2. Present short names, display names, and paths only when needed.

Pattern: user asks what needs attention
1. Run `vibelab chat waiting --json`.
2. Group by project.
3. Present session id, provider, summary, and last activity.

Pattern: user asks OpenClaw to answer a waiting session
1. Run `vibelab chat reply --project ... --session ... -m ... --json`.
2. Immediately run `vibelab chat waiting --project ... --json`.
3. If the same session is still present, report that it is still processing.
4. Optionally run `vibelab_wait_until_clear.sh` and report the final clearance.

Pattern: user suddenly has a new idea
1. Pick a workspace path, usually `/Users/<user>/vibelab/<slug>`.
2. Run `vibelab projects idea <path> --name <display-name> --idea <idea> --json`.
3. Return the created project, session id, and first VibeLab reply.
4. Continue the discussion with `vibelab chat reply` on that session.

Pattern: user wants an update without opening VibeLab
1. Run `vibelab digest daily --json` or `vibelab digest project --project ... --json`.
2. Summarize only the load-bearing items: waiting sessions, task progress, blockers, next actions.
