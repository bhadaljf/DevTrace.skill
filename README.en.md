# DevTrace

[简体中文](./README.zh-CN.md)

## Overview

This repository contains the standalone **skill package** extracted from the completed DevTrace work.

It is not the Web application itself. Instead, it packages DevTrace's proven workflow for turning raw development records into structured, reusable outputs.

Core capabilities:

- organize development chat records
- reconstruct the main workflow
- identify key turning points
- extract core takeaways
- preserve traceable evidence from the source text
- generate structured summaries
- produce Markdown / TXT style export-ready content

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

## Typical Use Cases

Use this repository when you want an AI / agent to:

- process `.md` / `.txt` development chat logs
- summarize a requirement or implementation timeline
- reconstruct a debugging or iteration path
- extract key decisions and evidence
- generate structured summaries for review or sharing

## Notes

`devtrace/SKILL.md` is the core file written for AI / agent execution.  
`devtrace/README.md` is the human-facing explanation for the skill.

This repository currently focuses on the **Skill package only**, kept separate from the original Web application.
