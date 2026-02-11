---
name: inno-code-survey
description: Conducts code survey (Idea mode) or survey on ideas and papers (Plan mode). Output is always stored as model_survey for implementation-plan. Use after idea-generation+repo (Idea) or after prepare (Plan).
---

# Inno Code Survey

Mirrors `_conduct_code_survey` and Plan-mode survey in [run_infer_idea_ours.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer_idea_ours.py) and [run_infer.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer.py). One skill for both Idea and Plan; downstream reads `model_survey` only.

## Inputs

- **Idea mode**: `survey_res` / `refined_for_downstream`, `updated_download_res`, `extra_repo_info`, `context_variables`
- **Plan mode**: `ideas`, `references`, `prepare_res`, `download_res`, `context_variables`

## Outputs

- `code_survey_res` or `survey_res` stored as `context_variables["model_survey"]`; optionally structured notes

## Instructions

### Idea mode

1. Optional short pre-wait (e.g. 1s) to avoid rate limits.
2. Build `code_survey_query = build_code_survey_query(survey_res, updated_download_res, extra_repo_info)`. Call **code_survey_agent** with `messages = [{"role": "user", "content": code_survey_query}]`.
3. Set `context_variables["model_survey"] = code_survey_res` (last message content). Optional short post-wait.

### Plan mode

1. Build `survey_query = build_survey_query_for_plan(ideas, references, prepare_res, download_res)`. Call **survey_agent** (not code_survey_agent) with `messages = [{"role": "user", "content": survey_query}]`.
2. Set `context_variables["model_survey"] = survey_res` (last message content).

Downstream **inno-implementation-plan** reads only `model_survey`; it does not need to know the source.

## Checklist

- [ ] Mode determined (Idea vs Plan) from inputs.
- [ ] Idea: `build_code_survey_query` + code_survey_agent; Plan: `build_survey_query_for_plan` + survey_agent.
- [ ] `context_variables["model_survey"]` set.
- [ ] No distinction exposed to downstream.

## References

- run_infer_idea_ours.py: `_conduct_code_survey` (794–828). Prompts: `build_code_survey_query`.
- run_infer.py: `_conduct_survey` (362–390). Prompts: `build_survey_query_for_plan`; agent: survey_agent.
