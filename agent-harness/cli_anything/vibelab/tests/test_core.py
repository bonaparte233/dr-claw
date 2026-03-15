"""
Unit tests for cli_anything.vibelab core modules.

All tests mock HTTP calls so no running server is required.

Run with:
    pytest cli_anything/vibelab/tests/test_core.py -v
"""

import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

# ---------------------------------------------------------------------------
# Helpers — build fake requests.Response objects
# ---------------------------------------------------------------------------

def _fake_response(json_data, status_code=200):
    """Return a mock requests.Response that returns *json_data* from .json()."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# session.py tests
# ---------------------------------------------------------------------------

class TestSessionFile(unittest.TestCase):
    """Tests for token persistence helpers in session.py."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.session_path = Path(self.tmpdir) / ".vibelab_session.json"

    def _patch_session_file(self):
        return patch(
            "cli_anything.vibelab.core.session.SESSION_FILE",
            self.session_path,
        )

    def test_login_stores_token(self):
        """login() should write the JWT token to the session file."""
        from cli_anything.vibelab.core.session import VibeLab

        fake_resp = _fake_response(
            {"success": True, "token": "fake-jwt-token", "user": {"username": "alice"}}
        )

        with self._patch_session_file():
            client = VibeLab()
            with patch.object(client._session, "post", return_value=fake_resp):
                result = client.login("alice", "secret")

        self.assertEqual(result["token"], "fake-jwt-token")
        stored = json.loads(self.session_path.read_text())
        self.assertEqual(stored["token"], "fake-jwt-token")
        self.assertEqual(stored["username"], "alice")

    def test_logout_removes_session_file(self):
        """logout() should delete the session file."""
        from cli_anything.vibelab.core.session import VibeLab

        self.session_path.write_text(json.dumps({"token": "old-token"}))

        with self._patch_session_file():
            client = VibeLab()
            client.logout()

        self.assertFalse(self.session_path.exists())

    def test_get_token_reads_session_file(self):
        """get_token() should return the token from the session file."""
        from cli_anything.vibelab.core.session import VibeLab

        self.session_path.write_text(json.dumps({"token": "stored-token"}))

        with self._patch_session_file():
            client = VibeLab()
            token = client.get_token()

        self.assertEqual(token, "stored-token")

    def test_get_token_prefers_env_var(self):
        """VIBELAB_TOKEN env var should take precedence over the session file."""
        from cli_anything.vibelab.core.session import VibeLab

        self.session_path.write_text(json.dumps({"token": "file-token"}))

        with self._patch_session_file():
            with patch.dict(os.environ, {"VIBELAB_TOKEN": "env-token"}):
                client = VibeLab()
                token = client.get_token()

        self.assertEqual(token, "env-token")

    def test_not_logged_in_error(self):
        """Calling get() without a token raises NotLoggedInError."""
        from cli_anything.vibelab.core.session import VibeLab, NotLoggedInError

        with self._patch_session_file():
            client = VibeLab()
            with self.assertRaises(NotLoggedInError):
                client.get("/api/projects")

    def test_get_base_url_default(self):
        """get_base_url() should fall back to localhost:3001."""
        from cli_anything.vibelab.core.session import VibeLab

        with self._patch_session_file():
            with patch.dict(os.environ, {}, clear=True):
                # Remove VIBELAB_URL if set in environment
                env = {k: v for k, v in os.environ.items() if k != "VIBELAB_URL"}
                with patch.dict(os.environ, env, clear=True):
                    client = VibeLab()
                    url = client.get_base_url()

        self.assertEqual(url, "http://localhost:3001")

    def test_get_base_url_env_var(self):
        """VIBELAB_URL env var overrides the default."""
        from cli_anything.vibelab.core.session import VibeLab

        with self._patch_session_file():
            with patch.dict(os.environ, {"VIBELAB_URL": "http://myserver:4000"}):
                client = VibeLab()
                url = client.get_base_url()

        self.assertEqual(url, "http://myserver:4000")

    def test_get_base_url_override_param(self):
        """url_override constructor param takes highest precedence."""
        from cli_anything.vibelab.core.session import VibeLab

        with self._patch_session_file():
            with patch.dict(os.environ, {"VIBELAB_URL": "http://env:9000"}):
                client = VibeLab(url_override="http://explicit:1234")
                url = client.get_base_url()

        self.assertEqual(url, "http://explicit:1234")


# ---------------------------------------------------------------------------
# projects.py tests
# ---------------------------------------------------------------------------

class TestProjects(unittest.TestCase):

    def _make_client(self, json_data, status_code=200):
        """Return a VibeLab client whose get() returns a fake response."""
        from cli_anything.vibelab.core.session import VibeLab
        client = VibeLab()
        client.get = MagicMock(return_value=_fake_response(json_data, status_code))
        client.patch = MagicMock(return_value=_fake_response({"success": True}))
        client.delete = MagicMock(return_value=_fake_response({"success": True}))
        return client

    def test_list_projects_returns_list(self):
        """list_projects() should return the list of project dicts."""
        from cli_anything.vibelab.core.projects import list_projects

        projects = [
            {"id": "p1", "display_name": "Alpha"},
            {"id": "p2", "display_name": "Beta"},
        ]
        client = self._make_client(projects)
        result = list_projects(client)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "p1")

    def test_list_projects_unwraps_dict(self):
        """list_projects() handles a server response wrapped in {projects: [...]}."""
        from cli_anything.vibelab.core.projects import list_projects

        wrapped = {"projects": [{"id": "p3", "display_name": "Gamma"}]}
        client = self._make_client(wrapped)
        result = list_projects(client)
        self.assertEqual(result[0]["id"], "p3")

    def test_rename_project_calls_patch(self):
        """rename_project() should PATCH the correct URL."""
        from cli_anything.vibelab.core.projects import rename_project

        client = self._make_client({})
        rename_project(client, "proj-abc", "New Name")
        client.patch.assert_called_once_with(
            "/api/projects/proj-abc/rename", {"newName": "New Name"}
        )

    def test_delete_project_calls_delete(self):
        """delete_project() should DELETE the correct URL."""
        from cli_anything.vibelab.core.projects import delete_project

        client = self._make_client({})
        result = delete_project(client, "proj-abc")
        client.delete.assert_called_once_with("/api/projects/proj-abc")
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# conversations.py tests
# ---------------------------------------------------------------------------

class TestConversations(unittest.TestCase):

    def test_list_sessions_returns_list(self):
        """list_sessions() should return sessions for a project."""
        from cli_anything.vibelab.core.conversations import list_sessions
        from cli_anything.vibelab.core.session import VibeLab

        sessions = [{"id": "s1", "title": "First session"}]
        client = VibeLab()
        client.get = MagicMock(return_value=_fake_response(sessions))

        result = list_sessions(client, "proj-123")
        client.get.assert_called_once_with("/api/projects/sessions/proj-123")
        self.assertEqual(result[0]["id"], "s1")

    def test_get_session_messages_returns_messages(self):
        """get_session_messages() should return ordered messages."""
        from cli_anything.vibelab.core.conversations import get_session_messages
        from cli_anything.vibelab.core.session import VibeLab

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        client = VibeLab()
        client.get = MagicMock(return_value=_fake_response({"messages": messages}))

        result = get_session_messages(client, "sess-456")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["role"], "assistant")


# ---------------------------------------------------------------------------
# settings.py tests
# ---------------------------------------------------------------------------

class TestSettings(unittest.TestCase):

    def test_list_api_keys(self):
        """list_api_keys() should return key dicts from {apiKeys: [...]}."""
        from cli_anything.vibelab.core.settings import list_api_keys
        from cli_anything.vibelab.core.session import VibeLab

        keys = [{"id": 1, "key_name": "my-key", "api_key": "sk-12345678..."}]
        client = VibeLab()
        client.get = MagicMock(return_value=_fake_response({"apiKeys": keys}))

        result = list_api_keys(client)
        self.assertEqual(result[0]["id"], 1)

    def test_create_api_key(self):
        """create_api_key() should POST and return the new key dict."""
        from cli_anything.vibelab.core.settings import create_api_key
        from cli_anything.vibelab.core.session import VibeLab

        new_key = {"id": 7, "key_name": "ci-key", "api_key": "full-secret-value"}
        client = VibeLab()
        client.post = MagicMock(
            return_value=_fake_response({"success": True, "apiKey": new_key})
        )

        result = create_api_key(client, "ci-key")
        client.post.assert_called_once_with("/api/settings/api-keys", {"keyName": "ci-key"})
        self.assertEqual(result["id"], 7)

    def test_delete_api_key(self):
        """delete_api_key() should DELETE the correct endpoint."""
        from cli_anything.vibelab.core.settings import delete_api_key
        from cli_anything.vibelab.core.session import VibeLab

        client = VibeLab()
        client.delete = MagicMock(return_value=_fake_response({"success": True}))

        result = delete_api_key(client, "42")
        client.delete.assert_called_once_with("/api/settings/api-keys/42")
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# output.py tests
# ---------------------------------------------------------------------------

class TestOutput(unittest.TestCase):

    def _capture(self, fn, *args, **kwargs):
        """Run fn() and capture both stdout and stderr."""
        import io
        from contextlib import redirect_stdout, redirect_stderr

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            fn(*args, **kwargs)
        return stdout_buf.getvalue(), stderr_buf.getvalue()

    def test_output_json_mode_list(self):
        """output() with json_mode=True emits valid JSON."""
        from cli_anything.vibelab.utils.output import output

        data = [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}]
        stdout, _ = self._capture(output, data, json_mode=True)
        parsed = json.loads(stdout.strip())
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["name"], "foo")

    def test_output_pretty_mode_list_of_dicts(self):
        """output() in pretty mode renders column headers."""
        from cli_anything.vibelab.utils.output import output

        data = [{"id": "1", "name": "Alpha"}]
        stdout, _ = self._capture(output, data, json_mode=False)
        self.assertIn("ID", stdout.upper())
        self.assertIn("Alpha", stdout)

    def test_output_empty_list(self):
        """output() handles an empty list without crashing."""
        from cli_anything.vibelab.utils.output import output

        stdout, _ = self._capture(output, [], json_mode=False)
        self.assertIn("no items", stdout)

    def test_success_json_mode(self):
        """success() in JSON mode emits {"status": "ok", ...}."""
        from cli_anything.vibelab.utils.output import success

        stdout, _ = self._capture(success, "Done!", True)
        parsed = json.loads(stdout.strip())
        self.assertEqual(parsed["status"], "ok")
        self.assertIn("Done!", parsed["message"])

    def test_error_goes_to_stderr(self):
        """error() always writes to stderr."""
        from cli_anything.vibelab.utils.output import error

        stdout, stderr = self._capture(error, "Something went wrong")
        self.assertEqual(stdout, "")
        self.assertIn("Something went wrong", stderr)

    def test_info_goes_to_stderr(self):
        """info() writes to stderr, not stdout."""
        from cli_anything.vibelab.utils.output import info

        stdout, stderr = self._capture(info, "Just a heads-up")
        self.assertEqual(stdout, "")
        self.assertIn("Just a heads-up", stderr)

    def test_output_json_mode_dict(self):
        """output() with a dict in JSON mode emits the dict as JSON."""
        from cli_anything.vibelab.utils.output import output

        data = {"needsSetup": False, "isAuthenticated": False}
        stdout, _ = self._capture(output, data, json_mode=True)
        parsed = json.loads(stdout.strip())
        self.assertFalse(parsed["needsSetup"])


if __name__ == "__main__":
    unittest.main()
