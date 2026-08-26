---
name: context-engineering-v1
description: Use when bootstrapping or refining a lightweight AI collaboration project skeleton that needs a single entry file, a single state source, iterative briefs, run logs, methodology cards, archive lanes, and a lightweight co
...
---

# Context Engineering V1

## Overview

This skill packages the first stable version of a lightweight context-engineering workflow.

Use it when a project needs to:

- start from a minimum viable collaboration skeleton
- keep AI work continuous across sessions
- record current state in one place
- append process notes without creating document sprawl
- accumulate reusable methodology cards
- decide whether the next iteration is worth doing

This is a `v1` skill. Favor simplicity over completeness.

## Core Rules

1. Keep one entry file.
   - Use `AGENTS.md` as the only mandatory startup entry.
2. Keep one current-state source.
   - Use `WORK.md` as the single source of current project status.
3. Keep one process log.
   - Use `RUNLOG.md` as the append-only iteration log.
4. Keep iteration work small.
   - Each round should usually add one main capability only.
5. Keep methodology reusable.
   - Cross-project rules and project-specific rules must be separated.
6. Keep the continue/stop decision lightweight.
   - Use the 4-field cost-benefit gate, not a heavy scoring system.
7. Keep context usage within a practical budget.
   - `<=45%`: execute normally.
   - `45%-75%`: reduce unrelated documents, repeated explanations, and raw tool output.
   - `>75%`: stop expanding the read set, write a summary to `WORK.md`, and restart context when needed.

## Minimal Reasoning Rule

Use first-principles thinking before adding structure:

- reduce the task to its real goal, hard constraints, current evidence, and smallest verifiable next action
- do not inherit old workflows, UI states, file layouts, or assumptions unless current evidence supports them

Use Occam's razor when choosing an implementation:

- choose the fewest files, fields, steps, dependencies, and rules that can satisfy the current goal
- add complexity only when it removes proven ambiguity, prevents a serious error, or enables necessary validation

## Recommended Skeleton

```text
project-root/
|- AGENTS.md
|- CHARTER.md
|- WORK.md
|- RUNLOG.md
|- STARTUP.md
|- results-overview.md
|- project-visual-guide.md
|- roadmap.md
|- safe-rename-plan.md
|- briefs/
|- adr/
|- kb/
|- retro/
|- methodology/
|  |- shared-rules-and-experience/
|  `- project-specific-rules-and-experience/
`- archive/
   |- long-logs/
   |- old-versions/
   `- low-frequency-materials/
```

## When To Use

Use this skill when the user asks to:

- build a reusable AI project skeleton
- reduce prompt/context drift in a long project
- make project work continuous across sessions
- standardize project status, briefs, logs, and methodology
- decide whether another iteration is still worth the cost

Equivalent Chinese prompts should also trigger this skill, for example:

- “把这套方法论封装成 skill”
- “给项目搭一个 AI 协作骨架”
- “让这个项目能跨会话持续推进”
- “做一个轻量的上下文工程框架”

## Workflow

1. Inspect the current project first.
   - Look for `AGENTS.md`, `CHARTER.md`, `WORK.md`, `RUNLOG.md`, `briefs/`, `methodology/`, and `archive/`.
   - Detect whether the project already has overlapping files such as old memory-bank style files.
2. Prefer the minimum viable skeleton.
   - Do not add extra files unless they clearly reduce confusion.
   - Preserve the “single entry, single state source, single run log” rule.
3. If the skeleton is missing, create it.
   - Use ASCII filenames for core files.
   - Keep Chinese in document titles or body content if useful.
4. Run work through iteration briefs.
   - Each brief should state what to add, why now, what not to add, and how to validate.
   - For medium or complex work, copy `templates/brief.minimal-template.md` into `briefs/`.
   - Do not create a brief for a trivial one-step task unless it has meaningful risk.
5. Append every completed round to `RUNLOG.md`.
   - Do not create a new note file for every round.
   - Prefer reverse chronological order: newest round first, older rounds later.
6. If the round produces reusable learning, write a methodology card.
   - Put reusable rules in `methodology/shared-rules-and-experience/`.
   - Put project-local rules in `methodology/project-specific-rules-and-experience/`.
7. At the end of each round, run the cost-benefit gate.

## Engineering Execution Layer

Use the following layer when the project contains maintainable code or a
shared GitHub delivery workflow. Keep the core skill usable for documents,
research, and old projects without forcing all of these tools.

### Core execution loop

1. Read `AGENTS.md`, `CHARTER.md`, `WORK.md`, and the current brief.
2. Inspect the current state before editing.
3. Make one bounded change.
4. Run the project's configured lint, tests, and build checks.
5. Update `WORK.md` and `RUNLOG.md`.
6. Create one small, logically complete Git snapshot.

Use a fixed task template with these fields:

- current evidence
- change for this round
- out of scope
- validation commands
- documentation update
- snapshot or delivery result

### Conditional engineering tools

- Use `git-worktree-bootstrap` for code, configuration, or higher-risk changes.
  The default is an isolated worktree and task branch.
- Direct edits are acceptable for documentation-only work, small investigations,
  and projects that are not yet Git repositories.
- Use `ruff`, `pytest`, `pre-commit`, or an equivalent checker only when the
  project already uses it or the benefit of adding it is clear.
- Use `gh` when the repository has a GitHub remote and the task involves Issues,
  pull requests, reviews, or CI. Check `gh auth status` before relying on it.
- Use GitHub Actions when the project has a repeatable lint, test, or build gate
  that should run on the remote repository before merge.
- Configure project-specific rules by path through `AGENTS.md` or the existing
  Codex configuration; do not mix CAD, Python, Office, and Web assumptions.
- Keep MCP services to the minimum required set. Treat each enabled service as
  extra context and action surface.

### Branch, snapshot, and delivery boundaries

- Prefer one feature, one branch, and one logical commit sequence.
- A local snapshot is a normal checkpoint; `push`, PR creation, and merge are
  delivery actions that require explicit user intent.
- Verify lint, tests, build, and the resulting `HEAD` before reporting a task as
  complete.
- Preserve unrelated dirty changes and never mix them into a task snapshot.

## Project Planning Research Rule

After project kickoff, when generating the first detailed project plan, do one lightweight GitHub scan for related projects.

Purpose:

- provide strategic and tactical direction for the project
- reduce avoidable design mistakes and repeated exploration
- identify what is worth borrowing and what should be avoided

Default scope:

- check 3-5 related repositories
- prioritize higher-star repositories first
- then filter by fit to the current goal, recency, issue quality, implementation maturity, and maintenance signals

Research output must stay minimal.
Use first-principles thinking and Occam's razor.
Only produce a short project guide with:

- what to borrow
- what to avoid

Use stars for discovery, not for adoption.
Do not rerun this research unless the project direction changes materially.

## Project Visualization Rule

After the minimum skeleton is stable, add a lightweight project visualization when it would improve planning, handoff, or option exploration.

Default outputs:

- one project flowchart
- one project mind map

Purpose:

- make the main workflow easier to understand
- help expand and compare solution directions
- improve handoff speed for later agents or humans

Keep it minimal:

- prefer Mermaid or structured Markdown
- prefer one page such as `project-visual-guide.md`
- show only the core steps, branches, risks, and decision points
- skip this for tiny or isolated tasks where the diagram cost is higher than the benefit

## Next High-ROI Options Rule

After completing one meaningful capability, recommend 2-3 high-ROI improvement directions.

For each direction, provide only:

- expected benefit
- estimated time cost
- estimated token cost
- main risk or blocker

Then pick exactly one recommended next addition.

Use this rule to help the user decide what to do next when the project can continue in multiple useful directions. Keep it lightweight:

- do not create a large roadmap unless the user asks
- do not score with complex formulas
- do not recommend more than 3 options by default
- prefer options that move the current MVP closer to the final goal

This rule complements the iteration gate:

- the iteration gate decides whether another round is worth doing
- this rule decides which next direction has the best cost-benefit fit

## Skill Feedback Loop Rule

When this skill is used across old projects, useful project experience should flow back into the skill as candidates, not as automatic rules.

At the end of a project stage, collect feedback candidates when one of these appears:

- the same workflow improvement helped more than once
- a project-specific rule seems reusable across projects
- a template field repeatedly reduced clarification cost
- a failure mode repeatedly caused context drift, rework, or wrong priorities
- a user correction exposed unclear wording in this skill

Record each candidate with only:

- source project
- observed problem or improvement
- evidence from real use
- proposed skill change
- reuse scope: project-only, cross-project, or skill-core

Promote feedback into the skill only when:

- it is reusable beyond one project, or
- it prevents a serious repeated failure, or
- it makes the workflow simpler without adding heavy structure

Do not promote:

- one-off project preferences
- domain-specific details that belong in project methodology cards
- long logs or raw chat excerpts
- changes that make the core workflow heavier without clear benefit

Recommended flow:

1. old project produces local lessons in `methodology/project-specific-rules-and-experience/`
2. reusable lessons are copied or summarized into `methodology/shared-rules-and-experience/`
3. strong repeated lessons become skill feedback candidates
4. only selected candidates update `context-engineering-v1`

This keeps the skill improving from real project evidence while protecting it from becoming a dumping ground.

## Skill Self-Refinement Rule

When improving `context-engineering-v1` itself:

- start from a repeated failure, measurable friction, or a missing executable step in a real project
- change one core capability per round
- validate the change with one real project or representative workflow
- keep speculative ideas in feedback candidates until real use supports promotion

The skill must not grow merely because a rule sounds useful. Every new core rule
must either reduce repeated clarification, prevent a serious failure, or make an
existing step directly executable.

### Executable Feedback MVP

This skill package includes a minimum runnable feedback loop:

- `skill-feedback-inbox/`: stores generated feedback candidate reports
- `templates/feedback-candidate-template.md`: manual candidate template
- `templates/brief.minimal-template.md`: minimal iteration brief template
- `README.md`: human-facing entry point
- `skill-feedback-inbox/manual-feedback-candidates.md`: manually selected feedback candidates before review
- `skill-feedback-inbox/feedback-candidates.reviewed.md`: human review log
- `skill-feedback-inbox/project-roots.example.txt`: example project list
- `scripts/collect-skill-feedback.ps1`: scans project methodology cards and generates `feedback-candidates.md`

Use it like this:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/collect-skill-feedback.ps1 `
  -ProjectListFile "skill-feedback-inbox\project-roots.example.txt"
```

The script scans:

- `methodology/shared-rules-and-experience/`
- `methodology/project-specific-rules-and-experience/` when `-IncludeProjectSpecific` is supplied

It summarizes candidates by:

- occurrence count
- reuse scope
- whether the candidate can simplify the workflow
- whether the candidate can prevent serious errors
- a light semantic cluster built from title and body terms

Automation boundary:

- the script only generates candidates and review scaffolds
- humans decide whether a candidate should update the skill
- the script does not modify `context-engineering-v1` automatically

## Stage Restart Rule

At the end of a real stage, prefer a context compression and restart.

This does not mean clearing context after every small task. Use it when:

- a stage is complete
- the goal changes
- the conversation becomes long or mixed
- the project structure becomes stable enough to hand off
- another AI agent may continue the work

Before restart, update the project documents:

- update `WORK.md` with the current MVP, completed work, next useful addition, blockers, and validation method
- append the stage record to `RUNLOG.md`, newest entry first
- create or update a brief only when the next stage needs a concrete iteration brief
- update methodology cards only when a reusable rule was learned

After restart, the next agent should treat project documents as the source of truth.

Use this startup order:

1. `AGENTS.md`
2. `CHARTER.md`
3. `WORK.md`
4. current or next `briefs/*.md` if present
5. results entrypoint or relevant methodology cards only when needed

Do not rely on previous chat history as the primary source after a stage restart.

## Context Budget Rule

Use a three-level, approximate budget for the context consumed by one task. The
budget includes conversation history, project documents, and tool output. It is
an operating signal, not a requirement to calculate exact tokens.

- `<=45%`: normal execution.
- `45%-75%`: reduce unrelated document reads, repeated explanations, and raw
  command output; prefer targeted searches and summaries.
- `>75%`: pause expanding the read set, summarize the current state into
  `WORK.md`, record the compression in `RUNLOG.md`, and restart the context when
  the task can continue from the project documents.

Do not clear context after every small task. Use the threshold together with
stage boundaries, task complexity, and the cost of losing still-needed evidence.

Supporting practices:

- judge the budget mainly for the current task stage, not only for the whole conversation
- compress tool output by default; prefer matches, summaries, selected ranges, and counts over full-file dumps
- before restarting, write `WORK.md` handoff information: completed work, current blocker, next action, and validation method
- code review, incident diagnosis, and evidence checks may temporarily exceed `75%` when full evidence is necessary; record the reason in `RUNLOG.md`

## Optional Context Relay

Use `BuildNewTask` or an equivalent one-time automation as an optional runtime
adapter for context restart. It is not required for the core skill.

Trigger relay preparation when:

- context usage is above `85%`
- a stage ends with unfinished work
- the session is interrupted and the task must continue
- the user explicitly requests a clean task window

Before scheduling a relay:

1. Update `WORK.md` with the goal, completed work, current blocker, next action,
   key files, and validation method.
2. Append the handoff state to `RUNLOG.md` when the project uses it.
3. Confirm the task is not already complete.

If `automation_update` is available, create one active, one-time automation as
the final action:

- schedule it for 30 seconds later
- use the `接力-` name prefix
- set `cwds` to the project root
- use `templates/relay-prompt-template.md`
- allow exactly one failure retry at 10 seconds, guarded by
  `relay-retry=1` in `WORK.md`

If automation is unavailable, stop after writing the handoff documents and
report that the next window must be opened manually. Do not pretend that a
relay was scheduled.

## Minimal Migration For Old Projects

Use this sequence when applying `context-engineering-v1` to an existing project.

1. Do not refactor the whole project first.
   - Keep the old folder structure and existing business files unchanged.
   - Add only the minimum collaboration layer needed to make the next round continuous.
2. Add the 4 core files first.
   - Create or complete `AGENTS.md`, `CHARTER.md`, `WORK.md`, and `RUNLOG.md`.
   - If similar files already exist, reuse their content instead of rewriting everything.
3. Map old materials before moving anything.
   - Treat old docs, notes, specs, and logs as reference sources.
   - Write in `AGENTS.md` and `WORK.md` where the old project truth currently lives.
4. Define the current MVP in plain language.
   - State what the project can already do.
   - State what the next smallest useful addition should be.
5. Run only 1 real iteration first.
   - Add one brief in `briefs/`.
   - Complete one small but real improvement.
   - Append the result to `RUNLOG.md`.
6. Write migration lessons only after real use.
   - If a reusable rule appears, create a methodology card.
   - If no real pattern appears yet, do not invent extra structure.
7. Decide whether to deepen the migration.
   - If the 4 core files already keep work continuous, stop there for now.
   - Only then consider adding `methodology/`, `archive/`, `roadmap.md`, or other helper files.

### Minimal Old-Project Target State

For most old projects, the first acceptable migration state is only:

- `AGENTS.md` for startup order
- `CHARTER.md` for total goal and boundaries
- `WORK.md` for current MVP and next useful addition
- `RUNLOG.md` for append-only process writeback
- `briefs/` with one real iteration brief

If this small layer already improves continuity, the migration is successful.

## Suggested Startup Prompt For Old Projects

Use or adapt this prompt when starting in an existing project:

```md
请使用 context-engineering-v1 skill 接管这个旧项目，并按最小迁移方式工作。

要求：
1. 不要先全面重构。
2. 保留原有目录、业务文件和已有工作流。
3. 先识别现有资料里，哪些内容分别对应 AGENTS.md、CHARTER.md、WORK.md、RUNLOG.md。
4. 先补最小协作骨架，只补必要文件，不扩张结构。
5. 先写清当前 MVP、当前状态、这一轮最值得补充的功能。
6. 先完成 1 轮真实小迭代，并把过程追加写入 RUNLOG.md。
7. 完成后再判断，是否值得继续补 methodology/、archive/、roadmap.md 等结构。

先告诉我：
1. 这个项目当前的事实来源主要在哪些文件；
2. 当前 MVP 是什么；
3. 这一轮最值得补充的功能是什么；
然后直接开始改。
```

### Short Version

```md
请使用 context-engineering-v1 skill 处理这个旧项目。
不要先重构，保留原结构。
先补 AGENTS.md、CHARTER.md、WORK.md、RUNLOG.md。
先定义当前 MVP，并完成 1 轮真实小迭代。
做完后再判断是否继续扩展骨架。
```

## Iteration Gate

Use only these 4 fields unless there is a strong reason to expand:

- expected benefit of the next round
- time cost of the next round
- token cost of the next round
- current blocking severity

Then decide one of:

- continue next round
- enter maintenance/wrap-up
- require human judgment

If the team cannot explain the decision in one short reason, the gate is too vague.

## Output Expectations

When using this skill, prefer to leave behind:

- a clear `WORK.md`
- an updated `RUNLOG.md`
- one concrete brief for the current or next round
- methodology cards only when they are genuinely reusable

## What To Avoid

- multiple current-state files
- a new explanation document every round
- heavy scoring frameworks
- expanding the workflow before validating the current lightweight version
- Chinese filenames for core runtime files

## Version Note

This skill represents the first stable version of the methodology.

Treat it as:

- lightweight
- pragmatic
- validated enough to reuse
- still open to future v2 refinement
