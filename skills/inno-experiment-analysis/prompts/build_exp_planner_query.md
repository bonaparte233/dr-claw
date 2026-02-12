# build_exp_planner_query

Constructs the prompt for the Experiment Analysis Agent to analyze results and plan further experiments.

## Parameters

| Parameter    | Type   | Description |
|--------------|--------|-------------|
| `survey_res` | string | The finalized selected idea |
| `prepare_res`| string | JSON with reference codebases and paths |
| `plan_res`   | string | Detailed implementation plan |
| `submit_res` | string | Submission result from the ML Agent (from inno-experiment-dev Phase 3) |

## Template

```
You are given an innovative idea:
{survey_res}
And the reference codebases chosen by the `Prepare Agent`:
{prepare_res}
And the detailed coding plan:
{plan_res}
You have conducted the experiments and get the experimental results:
{submit_res}
Your task is to:
1. Analyze the experimental results and give a detailed analysis report about the results.
2. Analyze the reference codebases and papers, and give a further plan to let
   `Machine Learning Agent` to do more experiments based on the innovative idea.
   The further experiments could include but not limited to:
    - Modify the implementation to better fit the idea.
    - Add more experiments to prove the effectiveness and superiority of the idea.
    - Visualize the experimental results and give a detailed analysis report about
      the results.
    - ANY other experiments that existing concurrent reference papers and codebases
      have done.
DO NOT use the `case_resolved` function before you have carefully and comprehensively
analyzed the experimental results and the reference codebases and papers.
```

## Usage

This prompt is appended to `judge_messages` (from inno-experiment-dev). The Experiment Analysis Agent:
1. Reviews experiment outputs (logs, metrics, saved models)
2. Reads reference codebases and papers for comparison
3. Creates a detailed `analysis_report`
4. Produces a `further_plan` dict mapping experiment names to descriptions
5. Calls `case_resolved(analysis_report=..., further_plan=...)` which stores in `context_variables["experiment_report"]`

## Output

`context_variables["experiment_report"]` is a list; each call appends:
```json
{
  "analysis_report": "detailed analysis string",
  "further_plan": {
    "experiment_1": "description of what to do",
    "experiment_2": "description of what to do"
  }
}
```
