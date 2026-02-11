# new_idea_prompt

Constructs the follow-up prompt for generating additional diverse ideas (rounds 2 through N).

## Parameters

| Parameter             | Type   | Description |
|-----------------------|--------|-------------|
| `previous_ideas_text` | string | All previously generated ideas, formatted as numbered candidates |

## Building `previous_ideas_text`

Iterate over all current `raw_ideas` and format:

```
--- Candidate Idea #1 ---
<raw_idea_1>

--- Candidate Idea #2 ---
<raw_idea_2>

...
```

## Template

```
Here are the ideas from previous rounds:
{previous_ideas_text}

Please survey again and give me another idea that is different from all ideas above. You MUST obey these hard constraints:
1) Do NOT introduce any new input modalities, new data sources, or new labels/targets.
2) Do NOT change the task, the disease/condition, the primary modality, or the prediction target.
```

## Usage

This prompt is **appended** to the existing conversation with the Idea Agent (not a new conversation). The agent continues the same chat thread and generates a new idea that is distinct from all previous ones.

The iteration uses `iter_times = i + 1` (where `i` is the 0-based loop index), which maps to the cache filename `idea_generation_agent_iter_{i+1}.json`.

## Constraint rationale

The two hard constraints prevent scope creep:
1. **No new modalities/data/labels** — the idea must work within the existing data pipeline
2. **No task/target changes** — ensures all ideas are comparable and address the same research problem
