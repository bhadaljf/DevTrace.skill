# DevTrace

[简体中文](./README.zh-CN.md)

DevTrace converts raw development records into structured outputs. It helps extract the main workflow, key turning points, core takeaways, and traceable evidence from chat logs, requirement discussions, debugging records, and project progress materials.

Typical use cases:

- organizing development chat records
- reviewing requirement progress
- reconstructing debugging and troubleshooting workflows
- extracting key conclusions from long discussions
- generating structured summaries for archiving, review, and sharing

---

## Features

DevTrace provides the following capabilities:

- **Workflow reconstruction**: rebuild the main progression path from raw records
- **Key turning point extraction**: identify issue exposure, option comparisons, direction shifts, and result confirmations
- **Core takeaway extraction**: retain decisions, conclusions, risks, and follow-up actions worth preserving
- **Evidence linking**: keep important conclusions traceable to the original text
- **Structured export**: produce Markdown / TXT content suitable for saving and sharing

---

## Supported Inputs

DevTrace is suitable for:

- `.md` chat records
- `.txt` chat records
- requirement discussion text
- debugging process records
- project review materials
- development process text arranged in chronological order

---

## Outputs

Default outputs include:

1. Session theme
2. Overall summary
3. Main workflow
4. Key turning points
5. Core takeaways
6. Source evidence
7. Markdown / TXT export content when needed

---

## Usage

In environments that support DevTrace directly, you can call it by name.

### Example 1: Organize development chat records

```text
/devtrace Organize this development chat record and extract the main workflow, key turning points, and source evidence
```

### Example 2: Review a debugging process

```text
/devtrace Turn this debugging record into a review summary, focusing on the initial issue, attempted solutions, failure turning points, and the final convergence
```

### Example 3: Generate an archive-ready summary

```text
/devtrace Generate a structured Markdown summary from this requirement progress record, including background, workflow, key conclusions, and follow-up actions
```

### Example 4: Compress for demo presentation

```text
/devtrace Extract a concise main workflow from this long conversation for demo presentation
```

If the current environment does not support the `/devtrace` form, natural language requests also work, for example:

- Use DevTrace to organize this development record
- Use DevTrace to extract the workflow from this discussion
- Use DevTrace to produce a structured summary

---

## Repository Structure

```text
DevTrace/
├─ README.md
├─ README.zh-CN.md
├─ README.en.md
└─ devtrace/
   ├─ SKILL.md
   ├─ README.md
   ├─ agents/
   │  └─ openai.yaml
   └─ references/
      ├─ workflow.md
      ├─ output-schema.md
      ├─ prompt-notes.md
      └─ examples.md
```

---

## Intended Uses

DevTrace is designed to:

- convert scattered development records into readable outputs
- prepare review materials for requirement, implementation, and debugging processes
- extract effective information from long-form discussions
- provide structured content for archiving, team sync, and later analysis

---

## Notes

DevTrace currently focuses on one core task: structuring development process records.

Its purpose is not to generate code, but to make existing development processes clear, accurate, traceable, and suitable for review and communication.
