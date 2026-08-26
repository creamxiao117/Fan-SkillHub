# context-engineering-v1

`context-engineering-v1` is a lightweight context-engineering skill for building and running a small AI collaboration skeleton.

## What It Solves

- one entry file
- one current state source
- one process log
- small iterative briefs
- reusable methodology cards
- lightweight continue/stop decisions
- feedback loop from old projects back into the skill
- optional context relay to a fresh task window when usage exceeds 85%

## How To Use In Old Projects

1. Add or reuse `AGENTS.md`, `CHARTER.md`, `WORK.md`, and `RUNLOG.md`.
2. For a medium or complex iteration, copy `templates/brief.minimal-template.md` into the project's `briefs/` directory.
3. Keep project-specific lessons in `methodology/project-specific-rules-and-experience/`.
4. Keep reusable lessons in `methodology/shared-rules-and-experience/`.
5. Use `skill-feedback-inbox/` and `scripts/collect-skill-feedback.ps1` to collect candidate rules from multiple projects.
6. When context usage exceeds `85%`, use `templates/relay-prompt-template.md` with an available one-time automation, or open the next window manually after updating `WORK.md`.

## How Feedback Flows Back

1. Project lessons are written locally.
2. Shared lessons are copied into the shared methodology lane.
3. The collector script scans methodology cards and writes `feedback-candidates.md`.
4. Humans review `feedback-candidates.reviewed.md`.
5. Only approved candidates update the skill.

