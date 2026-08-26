# Reviewed Skill Feedback Candidates

This file records human review results for generated feedback candidates.

## Template

```md
## <candidate title>

Source project:

Decision:
- accept
- reject
- defer

Reason:

Next action:
- update skill
- promote to shared experience
- keep watching
```

## Reviewed Items

## Optional Context Relay

Source project:

- `BuildNewTask` (`git@github.com:creamxiao117/BuildNewTask.git`)
- `context-engineering-v1` integration review

Decision:

- accept

Reason:

- `BuildNewTask` turns the existing stage restart rule into an executable one-time relay.
- It reuses `WORK.md` as the single state source and `RUNLOG.md` for handoff auditing.
- Keeping it optional and triggering only above `85%` preserves the lightweight core workflow.

Next action:

- update skill

## Executable Iteration Brief

Source project:

- `context-engineering-v1` self-refinement round
- `C:\Users\Fan-SJSS\Documents\codex-usage-guide`

Decision:

- accept

Reason:

- The skill already required iteration briefs and a cost-benefit gate, but did not provide a reusable template.
- Real self-application showed that agents still had to reconstruct the required fields from several rule sections.
- One minimal template makes an existing workflow executable without adding mandatory documents for trivial work.

Next action:

- update skill

## Minimal Reasoning Rule

Source project:

- `D:\AIwork\PKPM-Agent`
- `D:\AIwork\20260720-ShangXiaWenGongCheng`
- Codex 历史任务恢复排查
- Codex 配置路径迁移任务

Decision:

- accept

Reason:

- `第一性原理` 和 `奥卡姆剃刀` 已经在多个真实项目中反复出现。
- 两者合并成一个轻量规则块后，能直接指导 AI 先回到真实目标和当前证据，再选择最小可验证结构。
- 以可执行规则写入后，不会把 skill 变成抽象哲学说明，反而能减少误继承旧结构、误信 GUI 表象、误加复杂度的问题。

Next action:

- update skill

## Project Planning Research Rule

Source project:

- `D:\AIwork\PKPM-Agent`
- `D:\AIwork\20260720-ShangXiaWenGongCheng`
- `C:\Users\Fan-SJSS\Documents\Codex\2026-07-20\s`

Decision:

- accept

Reason:

- 把 GitHub 研究前移到“立项后、详细计划生成前”这个时机，费效比最高。
- 这一步能给项目的战略和战术方向提供外部参照，同时避免把“查 GitHub”变成每轮任务的固定负担。
- 用 `可借鉴 / 应避免` 的极简输出形式，符合 `第一性原理` 和 `奥卡姆剃刀`，不会把研究动作扩张成报告写作。

Next action:

- update skill

## Project Visualization Rule

Source project:

- `D:\AIwork\20260720-ShangXiaWenGongCheng`
- `D:\AIwork\PKPM-Agent`
- `C:\Users\Fan-SJSS\Documents\Codex使用指南`

Decision:

- accept

Reason:

- 在骨架稳定后补一页流程图和思维导图，能明显提升全局理解、方案发散和交接效率。
- 这条规则如果不加边界，很容易把小项目拖重；因此必须限定为“按复杂度触发”和“轻量输出”。
- 用 `Mermaid` 或结构化 Markdown 收口到一页 `project-visual-guide.md`，既保留图解收益，也不引入额外工具负担。

Next action:

- update skill
