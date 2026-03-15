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

from .session import VibeLab, NotLoggedInError


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


def _ws_url_from_base(base_url: str) -> str:
    """Convert http(s)://host to ws(s)://host."""
    if base_url.startswith("https://"):
        return "wss://" + base_url[len("https://"):]
    if base_url.startswith("http://"):
        return "ws://" + base_url[len("http://"):]
    return base_url


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
    ws_base = _ws_url_from_base(base_url)
    ws_url = f"{ws_base}?token={token}"

    async def _run() -> Dict[str, Any]:
        try:
            import websockets  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'websockets' package is required for chat commands. "
                "Install it with: pip install websockets>=11.0"
            ) from exc

        text_parts: List[str] = []
        captured_session_id: Optional[str] = session_id
        done = asyncio.Event()

        payload = {
            "type": "claude-command",
            "command": message,
            "options": {
                "projectPath": project_path,
                "sessionId": session_id,
                "resume": session_id is not None,
            },
        }

        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps(payload))

            async def receive_loop() -> None:
                nonlocal captured_session_id
                silence_deadline: Optional[float] = None

                while True:
                    # Use a short receive timeout so we can check silence
                    recv_timeout = 2.0
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
                    except asyncio.TimeoutError:
                        # If we have received content and 2 s of silence, consider done
                        if text_parts and (
                            silence_deadline is None
                            or asyncio.get_event_loop().time() >= silence_deadline
                        ):
                            done.set()
                            return
                        continue
                    except Exception:
                        done.set()
                        return

                    # Reset silence timer on every message
                    silence_deadline = asyncio.get_event_loop().time() + 2.0

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
                        text = _extract_text_from_claude_response(data)
                        if text:
                            text_parts.append(text)

                    elif event_type in ("claude-complete", "complete", "session-complete"):
                        captured_session_id = event.get("sessionId", captured_session_id)
                        done.set()
                        return

                    elif event_type == "claude-error":
                        err_msg = event.get("error", "Unknown error from VibeLab server")
                        raise RuntimeError(f"VibeLab server error: {err_msg}")

                    # Generic done signals
                    elif event.get("final") or event.get("done"):
                        done.set()
                        return

            await asyncio.wait_for(receive_loop(), timeout=timeout)

        reply = "\n".join(text_parts).strip()
        return {
            "reply": reply,
            "session_id": captured_session_id or "",
            "project_path": project_path,
        }

    return asyncio.run(_run())


def get_active_sessions(client: VibeLab) -> List[Dict[str, Any]]:
    """
    Retrieve all active sessions across all projects.

    Calls GET /api/projects, then for each project calls
    GET /api/projects/sessions/<projectId>.

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
        project_id = project.get("id", "")
        project_name = project.get("name") or project.get("display_name") or project_id
        if not project_id:
            continue
        try:
            sessions_resp = client.get(f"/api/projects/sessions/{project_id}")
            sessions_data = sessions_resp.json()
            if isinstance(sessions_data, list):
                sessions = sessions_data
            elif isinstance(sessions_data, dict):
                sessions = sessions_data.get("sessions", [])
            else:
                sessions = []
            for session in sessions:
                if isinstance(session, dict):
                    session = dict(session)
                    session.setdefault("project_id", project_id)
                    session.setdefault("project_name", project_name)
                    all_sessions.append(session)
        except Exception:
            # Skip projects where sessions endpoint fails
            continue

    return all_sessions
