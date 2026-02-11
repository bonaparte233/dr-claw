---
name: inno-ml-dev-iteration
description: Implements the model from the plan and iterates with Judge feedback until fully_correct or max_iter_times. Use after implementation-plan in both Idea and Plan branches.
---

# Inno ML Dev Iteration

Mirrors `_implement_and_iterate` in [run_infer_idea_ours.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer_idea_ours.py) and [run_infer.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer.py). Plan mode uses `build_iteration_query_for_plan`, `build_judge_simple_query_for_plan`.

## Inputs

- `survey_res`, `updated_prepare_res`, `code_survey_res`, `plan_res`, `dataset_description`, `workplace_name`, `max_iter_times`, `context_variables`
- Plan mode: pass `ideas`; use plan-specific prompts.

## Outputs

- Final `ml_dev_res`, `judge_res`, `judge_messages` (full conversation for continuation), and any paths to modified code

## Instructions

1. **Initial implementation**: Build `ml_dev_query = build_ml_dev_query(survey_res, prepare_res, code_survey_res, plan_res, dataset_description, workplace_name)` (or plan variant if ideas provided). Call **ml_agent** with `messages = [{"role": "user", "content": ml_dev_query}]`. Set `ml_dev_res = ml_messages[-1]["content"]`.

2. **Initial judge**: Build `query = build_judge_query(survey_res, prepare_res, plan_res, ml_dev_res)` (or plan variant). Call **judge_agent** with `input_messages = [{"role": "user", "content": query}]`. Set `judge_res = judge_messages[-1]["content"]`.

3. **Iteration loop** (for i in 0..max_iter_times - 1):
   - Build refinement query: **Idea** `build_iteration_query(survey_res, prepare_res, code_survey_res, plan_res, ml_dev_res, judge_res, workplace_name)`; **Plan** `build_iteration_query_for_plan(ideas, prepare_res, plan_res, survey_res, ml_dev_res, judge_res, workplace_name)`.
   - Append as user message to `judge_messages`; call **ml_agent** with `iter_times=i+1`. Update `ml_dev_res`.
   - Build judge re-eval: **Idea** `build_judge_simple_query(survey_res, prepare_res, plan_res, ml_dev_res)`; **Plan** `build_judge_simple_query_for_plan(ideas, prepare_res, plan_res, survey_res, ml_dev_res)`.
   - Append as user message; call **judge_agent** with `iter_times=i+1`. Update `judge_res`.
   - If `"fully_correct": true` in last message content, break early.

4. Preserve and return **judge_messages** for inno-experiment-submit-refine.

## Checklist

- [ ] Initial ML dev and judge completed.
- [ ] Loop uses correct iteration/judge prompt for Idea vs Plan.
- [ ] judge_messages reused across iterations.
- [ ] Early exit on fully_correct; max_iter_times respected.
- [ ] judge_messages returned for submit/refine step.

## References

- run_infer_idea_ours.py: `_implement_and_iterate` (861–920). Prompts: `build_ml_dev_query`, `build_judge_query`, `build_iteration_query`, `build_judge_simple_query`.
- run_infer.py: same; Plan mode uses `build_iteration_query_for_plan`, `build_judge_simple_query_for_plan`.
