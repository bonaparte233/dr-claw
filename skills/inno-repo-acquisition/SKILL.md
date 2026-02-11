---
name: inno-repo-acquisition
description: Acquires missing code repositories for the selected idea and merges them into prepare_res. Use after idea-generation when the Idea branch needs additional codebases.
---

# Inno Repo Acquisition

Mirrors `_acquire_missing_repos` and `_update_prepare_res_with_new_repos` in [run_infer_idea_ours.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer_idea_ours.py).

## Inputs

- `survey_res` (final idea), `download_res` or `updated_download_res`, `prepare_res`, `context_variables`

## Outputs

- Human-readable `extra_repo_info` string, updated `context_variables["acquired_code_repos"]` (dict: name -> path), and `updated_prepare_res` with new `reference_codebases` and `reference_paths`

## Instructions

1. **Acquire repos**: Build `query = build_repo_acquisition_query(survey_res, download_res)`. Call Repo Acquisition Agent with `messages = [{"role": "user", "content": query}]`.

2. **Parse results**: From the agent’s conversation, extract all matches of **`[REPO_ACQUIRED] name=<name>; path=<path>`** (regex: `r"\[REPO_ACQUIRED\] name=(.*?); path=(.*?)(?:\n|$)"`). Include only paths containing `workplace`. Build `acquired_repos_dict = { name: path }` and also merge any `context_variables["acquired_code_repos"]` list (with `name`/`path` keys). Set `context_variables["acquired_code_repos"] = acquired_repos_dict`.

3. **Update prepare_res**: Parse `prepare_res` with `extract_json_from_output`. Ensure `reference_codebases` and `reference_paths` exist. For each entry in `acquired_repos_dict`, if `path` not already in `reference_paths`, append to both `reference_codebases` and `reference_paths` (deduplicate). Serialize back to JSON as `updated_prepare_res`.

4. **Extra repo info string**: If `acquired_repos_dict` non-empty, build `extra_repo_info = "\n".join([f"- Name: {name} | Path: {path}" for name, path in acquired_repos_dict.items()])`. Otherwise return empty string.

## Checklist

- [ ] Repo Acquisition Agent called with correct query.
- [ ] `[REPO_ACQUIRED]` patterns parsed; paths filtered by `workplace`.
- [ ] `context_variables["acquired_code_repos"]` set.
- [ ] `prepare_res` updated and `updated_prepare_res` returned.
- [ ] `extra_repo_info` string built for downstream.

## References

- run_infer_idea_ours.py: `_acquire_missing_repos` (745–792), `_update_prepare_res_with_new_repos` (639–686). Prompt: `build_repo_acquisition_query`.
