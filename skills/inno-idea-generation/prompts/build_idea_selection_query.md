# build_idea_selection_query

Constructs the prompt for selecting the best idea from all generated candidates.

## Parameters

| Parameter  | Type         | Description |
|------------|--------------|-------------|
| `idea_num` | int          | Total number of generated ideas |
| `ideas`    | list[string] | List of all raw idea texts |

## Building the ideas text

Join all ideas with the double-separator:

```
separator = '\n===================\n===================\n'
ideas_text = separator.join(ideas)
```

## Template

```
You have generated {idea_num} innovative ideas for the given task:
{ideas_text}

Your task is to analyze multiple existing ideas, select the most novel one, enhance the idea if any key information is missing, finally give me the most novel idea with refined math formula and code implementation. Directly output the selected refined idea report.
```

## Usage

This is sent as a **new conversation** (fresh message list, not appended to the generation thread) to the Idea Agent with `iter_times = "select"`.

The agent uses its built-in rubric to evaluate:
- **Novelty**: is the core contribution genuinely new?
- **Contract-fit**: does it strictly match task/modality/target constraints?
- **Feasibility**: can it be implemented with available components?
- **Evidence alignment**: are claims supported by the provided papers?
- **Risk profile**: hidden dependencies or implicit new data requirements?

The agent selects one idea, optionally enhances it, and outputs the final report.

## Post-processing

After receiving the selection response:

1. Compare the response text against each entry in `raw_ideas`
2. If a raw idea's text appears as a substring (or the first 100 characters match), use the original raw idea as `best_candidate`
3. Otherwise, use the agent's response as-is (it may have been enhanced)

Store both the original and the selected version in `context_variables["final_selected_idea_data"]`.
