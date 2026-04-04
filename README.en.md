# DevTrace

[Simplified Chinese](./README.md) | [Design](./DESIGN.md)

## Overview

DevTrace is a project for long-running work. It captures key information from chats, discussions, debugging, experiments, and reviews into event units that can be tracked across time, helping AI reconnect to context across future sessions, keep following the same event, preserve work details, and support daily, weekly, monthly, and scheduled stage records.

Across the project, there are four core elements:

* `01_CURRENT.md`: records the current state, usually including the current thread, current problem, current blocker, next step, and recent changes.
* `00_INDEX.md`: the generated-content index, usually including the date, generated content entry, one-line summary, and tags. It helps quickly review what was generated recently and decide which records or events to read next.
* `TraceUnit`: records event facts, usually including a title, one-line summary, details, evidence, status, and tags. It keeps a large event organized as a whole and supports cross-time tracing.
* `tag`: topic labels, mainly written in `TraceUnit` and also shown in `00_INDEX.md`, so related events can be filtered quickly by topic.

## Design

### `01_CURRENT.md`

Current-state entry. It lets you quickly see where the work stands now.

Typical content:

- current thread
- current problem
- current blocker
- next step
- recent changes

Example:

```md
# 01_CURRENT

## Current Thread
- session-loader

## Current Problem
- the filtering rules for relevant content are still unstable

## Current Blocker
- a new session still does not know which units to read first

## Next Step
- fix the reading order as current -> index -> relevant content

## Recent Changes
- 2026-04-03: reading order clarified
- 2026-04-02: loader-related filtering rules expanded
```

### `00_INDEX.md`

Generated-content entry. AI usually reads this after current to quickly see what was generated recently.

Typical content:

- date
- generated content entry
- one-line summary
- tag

Example:

```md
# 00_INDEX

- [2026](#2026)
  - [2026-04](#2026-04)

## 2026

### 2026-04

- 2026-04-03 [reviews/session/2026-04-03-loader-summary.md] Session summary: a new session can enter from current and index first, then read related content as needed. #loader #design #session-summary
- 2026-04-03 [reviews/daily/2026-04-03.md] Daily review: the next step has been confirmed as fixing the reading order to current -> index -> relevant content. #loader #design #daily
- 2026-04-02 [reviews/session/2026-04-02-loader-summary.md] Session summary: the session loader still cannot stably filter related content. #loader #session-summary
```

The one-line summary here can be written by the user or by AI.

### TraceUnit

This is the core record object of the project. `TraceUnit` records events worth continuing to track across time. By default, one large event is captured as one unit. In many cases, `problem / attempt / decision / next-step / result` are only parts inside the same unit. They are better split into a new unit only when they become a new independent state node worth loading again in the future.

A simple rule:

- if the work will keep following this event later, it usually deserves a unit
- if it is only extra detail inside the same event, it usually belongs in an existing unit

### Tag

Topic labels. They are mainly written in `TraceUnit` and also shown in `00_INDEX.md`. AI uses `tag / thread / date / status / affects_current` together to filter related events.

Current built-in common tags:

`meeting / experiment / debug / review / documentation / automation / design / loader`

Users can create new tags themselves, and AI can also add new tags based on the actual situation.

### Reading Order

AI usually reads in the order of `01_CURRENT.md -> 00_INDEX.md -> relevant content / TraceUnit`. It first uses current to recover the present state, then uses index to locate recently generated content, and finally continues with related summaries, reviews, daily/weekly/monthly reports, or further enters the truly relevant event units to read details.

## Usage

### 1. Record

Skill usage:

- `/skill devtrace record the current session`
- `$devtrace record the current progress`

Say to AI:

- `Use DevTrace to record this round of work / write this round of loader progress into DevTrace / record this blocker in DevTrace`

### 2. Continue

Skill usage:

- `/skill devtrace continue the previous loader event`
- `$devtrace continue this event`

Say to AI:

- `Continue the previous loader event with DevTrace / append this new progress to the last event / this is still the same issue, write it back to the original TraceUnit`

### 3. Load

Skill usage:

- `/skill devtrace load the current project context`
- `$devtrace read current and index`

Say to AI:

- `Use DevTrace to load the current project context / read DevTrace current and index first / use DevTrace to reconnect me to this project`

### 4. Search

Skill usage:

- `/skill devtrace find loader-related events`
- `$devtrace find related events`

Say to AI:

- `Use DevTrace to find loader-related events / check recent design changes / trace the before-and-after changes of this event`

### 5. Review

Skill usage:

- `/skill devtrace generate this week's weekly report`
- `$devtrace set a weekly report every Friday`

Say to AI:

- `Use DevTrace to generate today's daily report / generate this month's review / from now on generate a daily report with DevTrace every day at 9 PM / generate a weekly report with DevTrace every Friday afternoon`

Generated daily, weekly, and monthly report files are usually placed under `reviews/` in the project directory, such as `reviews/daily/`, `reviews/weekly/`, and `reviews/monthly/`.

## File Structure

```text
DevTrace/
├─ DESIGN.md
├─ README.md
├─ devtrace/
│  ├─ SKILL.md
│  ├─ agents/
│  ├─ references/
│  ├─ assets/
│  └─ scripts/
```

- `DESIGN.md`: design document
- `devtrace/SKILL.md`: AI execution rules
- `01_CURRENT.md`: current-state entry
- `00_INDEX.md`: generated-content entry
- `trace/`: TraceUnit storage directory

If you want to understand the architecture in more detail, see [DESIGN.md](./DESIGN.md).

If you like the project, a star is welcome ⭐

Have a great day.(´▽`ʃ♡ƪ)
