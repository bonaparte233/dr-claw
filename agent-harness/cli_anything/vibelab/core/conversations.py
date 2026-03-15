"""
Session / conversation operations against the VibeLab REST API.

Terminology note: VibeLab uses "session" on the server side; the CLI surface
calls these "conversations" to avoid clashing with the HTTP session concept.
"""

from typing import Any, Dict, List

from .session import VibeLab


def list_sessions(client: VibeLab, project_id: str) -> List[Dict[str, Any]]:
    """
    GET /api/projects/sessions/:projectId

    Returns a list of session dicts for the given project.  Each dict
    typically contains ``id``, ``title``, ``created_at``, and ``provider``.
    """
    resp = client.get(f"/api/projects/sessions/{project_id}")
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("sessions", data)


def get_session_messages(client: VibeLab, session_id: str) -> List[Dict[str, Any]]:
    """
    GET /api/projects/sessions/:sessionId/messages

    Returns the ordered list of message dicts for the given session.  Each
    dict typically contains ``role``, ``content``, and ``timestamp``.
    """
    resp = client.get(f"/api/projects/sessions/{session_id}/messages")
    data = resp.json()
    if isinstance(data, list):
        return data
    return data.get("messages", data)
