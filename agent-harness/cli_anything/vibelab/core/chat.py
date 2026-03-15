"""
WebSocket chat client for the VibeLab server.

Connects to the VibeLab WebSocket endpoint, sends a claude-command, and
collects the streamed response until the session signals completion.

The server streams back JSON events of the following relevant types:
  - claude-response:   SDK message wrapped in {type, data, sessionId}
                       data.type may be 'assistant', 'result', etc.
                       Text content lives in data.message.content (array of
                       content blocks with type 'text').
  - session-created:   {type: 'session-created', sessionId: '...'}
  - claude-complete:   {type: 'claude-complete', sessionId: '...', exitCode: 0}
  - claude-error:      {type: 'claude-error', error: '...', sessionId: '...'}

Authentication: JWT token passed as query parameter `token`.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from .session import VibeLab


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_text_from_claude_response(data: Dict[str, Any]) -> Optional[str]:
    """
    Extract human-readable text from a claude-response data payload.

    The SDK sends messages where data is the raw SDK message object.
    Assistant messages have data.type == 'assistant' and
    data.message.content is a list of content blocks.
    """
    if not isinstance(data, dict):
        return None

    msg_type = data.get("type")

    # SDK 'assistant' messages carry content blocks
    if msg_type == "assistant":
        message = data.get("message", {})
        content = message.get("content", [])
        if isinstance(content, list):
            parts = [
                block["text"]
                for block in content
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
                and block["text"].strip()
            ]
            return "\n".join(parts) if parts else None
        if isinstance(content, str) and content.strip():
            return content

    # SDK 'result' messages may also carry a result string
    if msg_type == "result":
        result = data.get("result", "")
        if isinstance(result, str) and result.strip():
            return result

    return None


def _normalize_project_path(project_path: str) -> str:
    """Expand `~` and normalize filesystem-style project paths."""
    return os.path.abspath(os.path.expanduser(project_path))


def _ws_url_from_base(base_url: str) -> str:
    """Convert http(s)://host to ws(s)://host."""
    if base_url.startswith("https://"):
        return "wss://" + base_url[len("https://"):]
    if base_url.startswith("http://"):
        return "ws://" + base_url[len("http://"):]
    return base_url.rstrip("/")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_message(
    client: VibeLab,
    project_path: str,
    message: str,
    session_id: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Connect to the VibeLab WebSocket, send a claude-command, collect the full
    response, and return {"reply": str, "session_id": str, "project_path": str}.

    Parameters
    ----------
    client:
        Authenticated VibeLab client.
    project_path:
        Filesystem path (or project ID) passed as projectPath in the command
        options.
    message:
        The text to send to Claude.
    session_id:
        If provided, resumes an existing session.  If None, starts a new one.
    timeout:
        Maximum seconds to wait for the full response.
    """
    token = client._require_token()
    base_url = client.get_base_url()
    ws_base = _ws_url_from_base(base_url).rstrip("/")
    ws_url = f"{ws_base}/ws?token={token}"
    normalized_project_path = _normalize_project_path(project_path)

    async def _run() -> Dict[str, Any]:
        try:
            import websockets  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'websockets' package is required for chat commands. "
                "Install it with: pip install websockets>=11.0"
            ) from exc

        text_parts: List[str] = []
        stream_parts: List[str] = []
        captured_session_id: Optional[str] = session_id

        payload = {
            "type": "claude-command",
            "command": message,
            "options": {
                "cwd": normalized_project_path,
                "projectPath": normalized_project_path,
                "sessionId": session_id,
                "resume": session_id is not None,
            },
        }

        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps(payload))

            async def receive_loop() -> None:
                nonlocal captured_session_id

                while True:
                    try:
                        raw = await ws.recv()
                    except Exception:
                        return

                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("type", "")

                    # Capture session ID
                    if not captured_session_id:
                        sid = event.get("sessionId") or (
                            event.get("data", {}).get("session_id")
                            if isinstance(event.get("data"), dict)
                            else None
                        )
                        if sid:
                            captured_session_id = sid

                    if event_type == "session-created":
                        captured_session_id = event.get("sessionId", captured_session_id)

                    elif event_type == "claude-response":
                        data = event.get("data", {})
                        # Capture session id embedded in data
                        if not captured_session_id and isinstance(data, dict):
                            captured_session_id = data.get("session_id") or captured_session_id

                        if isinstance(data, dict) and data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            delta_text = delta.get("text") if isinstance(delta, dict) else None
                            if isinstance(delta_text, str) and delta_text:
                                stream_parts.append(delta_text)
                            continue

                        if isinstance(data, dict) and data.get("type") == "content_block_stop":
                            if stream_parts:
                                text_parts.append("".join(stream_parts))
                                stream_parts.clear()
                            continue

                        text = _extract_text_from_claude_response(data)
                        if text:
                            text_parts.append(text)

                    elif event_type in ("claude-complete", "complete", "session-complete"):
                        captured_session_id = event.get("sessionId", captured_session_id)
                        if stream_parts:
                            text_parts.append("".join(stream_parts))
                            stream_parts.clear()
                        return

                    elif event_type == "claude-error":
                        err_msg = event.get("error", "Unknown error from VibeLab server")
                        raise RuntimeError(f"VibeLab server error: {err_msg}")

                    # Generic done signals
                    elif event.get("final") or event.get("done"):
                        if stream_parts:
                            text_parts.append("".join(stream_parts))
                            stream_parts.clear()
                        return

            await asyncio.wait_for(receive_loop(), timeout=timeout)

        reply = "\n".join(text_parts).strip()
        return {
            "reply": reply,
            "session_id": captured_session_id or "",
            "project_path": normalized_project_path,
        }

    return asyncio.run(_run())


def get_active_sessions(client: VibeLab) -> List[Dict[str, Any]]:
    """
    Retrieve all active sessions across all projects.

    Returns a flat list of session dicts, each augmented with
    ``project_id`` and ``project_name`` keys.
    """
    projects_resp = client.get("/api/projects")
    projects_data = projects_resp.json()
    if isinstance(projects_data, dict):
        projects_list = projects_data.get("projects", [])
    else:
        projects_list = projects_data if isinstance(projects_data, list) else []

    all_sessions: List[Dict[str, Any]] = []
    for project in projects_list:
        project_name = project.get("name") or project.get("id") or ""
        project_label = (
            project.get("displayName")
            or project.get("display_name")
            or project_name
        )
        if not project_name:
            continue

        provider_collections = [
            ("claude", project.get("sessions") or []),
            ("cursor", project.get("cursorSessions") or []),
            ("codex", project.get("codexSessions") or []),
            ("gemini", project.get("geminiSessions") or []),
        ]

        for provider, sessions in provider_collections:
            if not isinstance(sessions, list):
                continue

            for session in sessions:
                if not isinstance(session, dict):
                    continue

                normalized = dict(session)
                normalized.setdefault("provider", provider)
                normalized.setdefault("project_id", project_name)
                normalized.setdefault("project_name", project_name)
                normalized.setdefault("project_display_name", project_label)
                normalized.setdefault(
                    "summary",
                    session.get("summary") or session.get("name") or session.get("title") or "",
                )
                all_sessions.append(normalized)

    return all_sessions
