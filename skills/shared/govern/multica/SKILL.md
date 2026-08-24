---
name: "multica"
description: "Multica 多技能合集：autopilot、agents、projects、squads、mentioning、runtimes、onboarding、issue 等 8 个子技能，覆盖 Multica 平台全生命周期操作。"
---

# Multica（多技能合集）

Multica 多技能合集，覆盖 Multica 平台的全生命周期操作能力。

## 包含的子技能

| 子技能 | 用途 |
| -------- | ------ |
| autopilot | 定时/手动/webhook 触发的自动化任务调度 |
| agents | Agent 定义创建、检查与调试 |
| projects | 项目与资源（GitHub 仓库、本地目录）管理 |
| squads | 团队管理与协作配置 |
| mentioning | Issue 评论中 @ 提及操作 |
| runtimes | 运行时环境管理与配置 |
| onboarding | 新成员交互式引导 |
| issue | Issue 工作流管理与分配 |

## 使用场景

- 创建和管理 Agent 定义
- 配置 autopilot 自动化任务
- 管理项目资源和 Squad
- onboarding 新成员

## 触发条件

- 用户明确提到 Multica 平台操作
- 用户要求管理 autopilot、agent、project、squad 等
- 用户提到 "multica"、"autopilot"、"agent 管理" 等关键词

## 使用边界

- **手动触发**：`invoke: user`，仅在用户明确要求时使用
- **不适用**：不需要 Multica 平台操作的场景
