# VibeLab CLI Harness — Test Plan

## Unit Tests (`test_core.py`)

All unit tests mock HTTP calls and require no running server.

### `TestSessionFile`

| Test | What It Covers |
|------|---------------|
| `test_login_stores_token` | `VibeLab.login()` writes the JWT and username to `~/.vibelab_session.json` |
| `test_logout_removes_session_file` | `VibeLab.logout()` deletes the session file |
| `test_get_token_reads_session_file` | `get_token()` reads the persisted token from disk |
| `test_get_token_prefers_env_var` | `VIBELAB_TOKEN` env var takes precedence over the session file |
| `test_not_logged_in_error` | Calling `get()` without any token raises `NotLoggedInError` |
| `test_get_base_url_default` | `get_base_url()` returns `http://localhost:3001` when nothing else is set |
| `test_get_base_url_env_var` | `VIBELAB_URL` env var overrides the default |
| `test_get_base_url_override_param` | The `url_override` constructor param takes highest precedence |

### `TestProjects`

| Test | What It Covers |
|------|---------------|
| `test_list_projects_returns_list` | `list_projects()` returns a plain list of dicts |
| `test_list_projects_unwraps_dict` | `list_projects()` unwraps a `{projects: [...]}` server response |
| `test_rename_project_calls_patch` | `rename_project()` sends `PATCH /api/projects/:id/rename` with `{newName}` |
| `test_delete_project_calls_delete` | `delete_project()` sends `DELETE /api/projects/:id` and returns True |

### `TestConversations`

| Test | What It Covers |
|------|---------------|
| `test_list_sessions_returns_list` | `list_sessions()` calls the correct endpoint and returns a list |
| `test_get_session_messages_returns_messages` | `get_session_messages()` unwraps `{messages: [...]}` |

### `TestSettings`

| Test | What It Covers |
|------|---------------|
| `test_list_api_keys` | `list_api_keys()` unwraps `{apiKeys: [...]}` from the server response |
| `test_create_api_key` | `create_api_key()` POSTs `{keyName}` and returns the new key dict |
| `test_delete_api_key` | `delete_api_key()` sends `DELETE /api/settings/api-keys/:id` and returns True |

### `TestOutput`

| Test | What It Covers |
|------|---------------|
| `test_output_json_mode_list` | `output()` emits valid JSON when `json_mode=True` |
| `test_output_pretty_mode_list_of_dicts` | `output()` renders column headers in pretty mode |
| `test_output_empty_list` | `output()` handles an empty list without crashing |
| `test_success_json_mode` | `success()` emits `{"status": "ok"}` JSON |
| `test_error_goes_to_stderr` | `error()` writes to stderr, not stdout |
| `test_info_goes_to_stderr` | `info()` writes to stderr, not stdout |
| `test_output_json_mode_dict` | `output()` serialises a plain dict as JSON |

---

## E2E Tests (`test_full_e2e.py`)

E2E tests are skipped unless `VIBELAB_E2E=1` is set.

### Required environment variables

| Variable | Purpose |
|----------|---------|
| `VIBELAB_E2E` | Set to `1` to enable E2E tests |
| `VIBELAB_URL` | Base URL of the running server (default: `http://localhost:3001`) |
| `VIBELAB_USER` | Username for authentication |
| `VIBELAB_PASS` | Password for authentication |

### `TestAuthStatus`

| Test | What It Tests |
|------|--------------|
| `test_auth_status_endpoint_responds` | `GET /api/auth/status` returns 200 with `needsSetup` key |
| `test_auth_status_via_cli` | `cli-anything-vibelab --json auth status` exits 0 and returns valid JSON |

### `TestLogin`

| Test | What It Tests |
|------|--------------|
| `test_login_returns_token` | `POST /api/auth/login` with valid credentials returns a JWT |
| `test_login_wrong_password` | Invalid password returns HTTP 401 |
| `test_login_stores_token_via_session` | `VibeLab.login()` persists the token to the session file |

### `TestListProjects`

| Test | What It Tests |
|------|--------------|
| `test_list_projects_returns_list` | `GET /api/projects` with a valid token returns a list |
| `test_list_projects_via_module` | `list_projects()` against the live server returns a list |

### `TestCLISubprocess`

| Test | What It Tests |
|------|--------------|
| `test_help_flag` | `cli-anything-vibelab --help` exits 0 and shows usage |
| `test_auth_status_subprocess` | `cli-anything-vibelab --json auth status` exits 0 with JSON output |
| `test_missing_subcommand_shows_help` | Running with no args shows help text |
| `test_auth_group_help` | `cli-anything-vibelab auth --help` lists login/logout/status |

---

## Test Results

### Run on 2026-03-14 — Python 3.9.6 / pytest 8.4.2

```
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/david/Developer/agent/VibeLab/agent-harness

cli_anything/vibelab/tests/test_core.py::TestSessionFile::test_get_base_url_default PASSED
cli_anything/vibelab/tests/test_core.py::TestSessionFile::test_get_base_url_env_var PASSED
cli_anything/vibelab/tests/test_core.py::TestSessionFile::test_get_base_url_override_param PASSED
cli_anything/vibelab/tests/test_core.py::TestSessionFile::test_get_token_prefers_env_var PASSED
cli_anything/vibelab/tests/test_core.py::TestSessionFile::test_get_token_reads_session_file PASSED
cli_anything/vibelab/tests/test_core.py::TestSessionFile::test_login_stores_token PASSED
cli_anything/vibelab/tests/test_core.py::TestSessionFile::test_logout_removes_session_file PASSED
cli_anything/vibelab/tests/test_core.py::TestSessionFile::test_not_logged_in_error PASSED
cli_anything/vibelab/tests/test_core.py::TestProjects::test_delete_project_calls_delete PASSED
cli_anything/vibelab/tests/test_core.py::TestProjects::test_list_projects_returns_list PASSED
cli_anything/vibelab/tests/test_core.py::TestProjects::test_list_projects_unwraps_dict PASSED
cli_anything/vibelab/tests/test_core.py::TestProjects::test_rename_project_calls_patch PASSED
cli_anything/vibelab/tests/test_core.py::TestConversations::test_get_session_messages_returns_messages PASSED
cli_anything/vibelab/tests/test_core.py::TestConversations::test_list_sessions_returns_list PASSED
cli_anything/vibelab/tests/test_core.py::TestSettings::test_create_api_key PASSED
cli_anything/vibelab/tests/test_core.py::TestSettings::test_delete_api_key PASSED
cli_anything/vibelab/tests/test_core.py::TestSettings::test_list_api_keys PASSED
cli_anything/vibelab/tests/test_core.py::TestOutput::test_error_goes_to_stderr PASSED
cli_anything/vibelab/tests/test_core.py::TestOutput::test_info_goes_to_stderr PASSED
cli_anything/vibelab/tests/test_core.py::TestOutput::test_output_empty_list PASSED
cli_anything/vibelab/tests/test_core.py::TestOutput::test_output_json_mode_dict PASSED
cli_anything/vibelab/tests/test_core.py::TestOutput::test_output_json_mode_list PASSED
cli_anything/vibelab/tests/test_core.py::TestOutput::test_output_pretty_mode_list_of_dicts PASSED
cli_anything/vibelab/tests/test_core.py::TestOutput::test_success_json_mode PASSED
cli_anything/vibelab/tests/test_full_e2e.py::TestAuthStatus::test_auth_status_endpoint_responds SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestAuthStatus::test_auth_status_via_cli SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestLogin::test_login_returns_token SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestLogin::test_login_stores_token_via_session SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestLogin::test_login_wrong_password SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestListProjects::test_list_projects_returns_list SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestListProjects::test_list_projects_via_module SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestCLISubprocess::test_auth_group_help SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestCLISubprocess::test_auth_status_subprocess SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestCLISubprocess::test_help_flag SKIPPED
cli_anything/vibelab/tests/test_full_e2e.py::TestCLISubprocess::test_missing_subcommand_shows_help SKIPPED

======================== 24 passed, 11 skipped in 0.03s ========================
```

**Summary:** 24 unit tests PASSED, 11 E2E tests SKIPPED (no live server; set `VIBELAB_E2E=1` to activate).
