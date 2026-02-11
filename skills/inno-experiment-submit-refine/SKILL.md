---
name: inno-experiment-submit-refine
description: Submits the implementation for experiments and refines based on experiment analysis. Use after ml-dev-iteration in both Idea and Plan branches.
---

# Inno Experiment Submit Refine

Mirrors `_submit_and_refine_experiments` in [run_infer_idea_ours.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer_idea_ours.py) and [run_infer.py](workspace/medical/Medical_ai_scientist_idea/research_agent/run_infer.py). Plan mode uses `build_submit_query_for_plan`, `build_exp_planner_query_for_plan`.

## Inputs

- `survey_res`, `updated_prepare_res`, `plan_res`, `ml_dev_res`, `judge_res`, `workplace_name`, `judge_messages`, `context_variables`
- Plan mode: pass `ideas`; use plan-specific submit/exp prompts.

## Outputs

- `submit_res`, `experiment_report` list (each with `analysis_report` and `further_plan`), `refine_res`. Surface analysis and refinement suggestions to user/UI.

## Instructions

1. **Submit**: Build `ml_submit_query = build_submit_query(survey_res, ml_dev_res, judge_res, workplace_name)` (or `build_submit_query_for_plan(ideas, ml_dev_res, judge_res)` in Plan mode). Append to `judge_messages` as user message. Call **ml_agent** with `iter_times="submit"`. Set `submit_res = judge_messages[-1]["content"]`.

2. **Refinement loop** (DEFAULT_EXP_ITER_TIMES):
   - Build `exp_planner_query = build_exp_planner_query(survey_res, prepare_res, plan_res, submit_res)` (or `build_exp_planner_query_for_plan(ideas, prepare_res, plan_res, submit_res)`). Append to judge_messages; call **exp_analyser** with `iter_times="refine_{i+1}"`.
   - Read `context_variables["experiment_report"]`; take last entry’s `analysis_report` and `further_plan`. If missing, fail with clear error (exp_analyser must call case_resolved).
   - Build `refine_query = build_refine_query(survey_res, prepare_res, plan_res, submit_res, analysis_report, workplace_name)`. Append to judge_messages; call **ml_agent** with `iter_times="refine_{i+1}"`. Update `refine_res`.

3. Surface `experiment_report` and final `refine_res` to the user/UI.

## Checklist

- [ ] Submit query built (correct variant for Idea/Plan); ml_agent submit run done.
- [ ] exp_analyser called; experiment_report populated.
- [ ] analysis_report and further_plan extracted; refine_query built and ml_agent called.
- [ ] Results surfaced to user/UI.

## References

- run_infer_idea_ours.py: `_submit_and_refine_experiments` (922–977). Prompts: `build_submit_query`, `build_exp_planner_query`, `build_refine_query`. Agent: exp_analyser.
- run_infer.py: same; Plan mode uses `build_submit_query_for_plan`, `build_exp_planner_query_for_plan`.
