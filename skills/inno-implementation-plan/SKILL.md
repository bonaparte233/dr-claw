---
name: inno-implementation-plan
description: Creates a detailed implementation plan from the selected idea and code survey. Use after code-survey in both Idea and Plan branches.
---

# Inno Implementation Plan

Mirrors `_create_implementation_plan` in [run_infer_idea_ours.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer_idea_ours.py) and [run_infer.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer.py). Optionally uses `_specify_selected_idea` (idea_refinement_agent) for a slightly more implementation-ready idea before planning.

## Inputs

- `survey_res` (or `refined_for_downstream`), `references`, `updated_prepare_res`, `code_survey_res` (or `context_variables["model_survey"]`), `dataset_description`
- Plan mode: use `ideas` and `survey_res` from model_survey; coding plan agent expects `build_plan_query_with_survey` when ideas are provided.

## Outputs

- `plan_res` (detailed implementation plan); optionally `refined_idea` if `_specify_selected_idea` was run

## Instructions

1. **Optional pre-step (Idea mode)**: If refining the idea for implementation clarity, call `idea_refinement_agent` with a prompt that refines the draft to be implementation-ready (tensor interfaces, forward-pass sketch) while keeping section titles; store result as `refined_for_downstream` if used. See `_specify_selected_idea` in run_infer_idea_ours.py (688–743).

2. **Build plan query**:
   - **Idea mode**: `plan_query = build_plan_query(survey_res, references, updated_prepare_res, code_survey_res, dataset_description)`.
   - **Plan mode**: `plan_query = build_plan_query_with_survey(ideas, references, prepare_res, code_survey_res, dataset_description)` (code_survey_res here is the survey output from survey_agent).

3. Call **coding_plan_agent** with `messages = [{"role": "user", "content": plan_query}]`. Set `plan_res = plan_messages[-1]["content"]`.

4. Encourage structured sections in the plan: data, model, training, evaluation, file layout so that inno-ml-dev-iteration can follow them.

## Checklist

- [ ] Optional idea refinement applied if desired.
- [ ] Correct build (build_plan_query vs build_plan_query_with_survey) for mode.
- [ ] Coding plan agent called; plan_res recorded.
- [ ] Plan has clear sections for downstream ML dev.

## References

- run_infer_idea_ours.py: `_create_implementation_plan` (830–859), `_specify_selected_idea` (688–743). Prompts: `build_plan_query`.
- run_infer.py: `_create_implementation_plan` (392–427); Plan mode uses `build_plan_query_with_survey`.
