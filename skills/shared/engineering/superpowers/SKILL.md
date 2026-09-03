---
name: "superpowers"
description: superpowers 插件提供的 13 个开发方法论技能合集：brainstorming、test-driven-development、writing-plans、debugging、code-review、git-worktree 等，通用开发场景自动命中 适用场景：头脑风暴、brainstorming、TDD。勿用于：纯知识问答、不需要工具的简单解释。
...
...
...
---

# Superpowers（开发方法论合集）

Superpowers 插件提供的 **13 个核心开发方法论技能合集**，覆盖从需求构思到代码交付的完整开发链路。

## 包含的子技能

| 子技能 | 用途 |
| -------- | ------ |
| brainstorming | 需求发散与方案探索 |
| test-driven-development | 测试驱动开发 |
| writing-plans | 分阶段实现计划制定 |
| debugging | 系统化调试策略 |
| code-review | 代码评审与质量门禁 |
| git-worktree | Git worktree 隔离开发 |
| branch-management | 分支策略与管理 |
| refactoring | 安全重构方法论 |
| performance-tuning | 性能分析与优化 |
| security-review | 安全审计 |
| documentation | 文档驱动开发 |
| integration-testing | 集成测试策略 |
| release-planning | 发布计划与风险管理 |

## 触发条件

当开发过程中需要方法论辅助时自动触发，包括但不限于：

- 面对新需求需要头脑风暴
- 需要制定分阶段实现计划
- 代码出现 bug 需要系统化调试
- 需要进行代码评审
- 涉及 Git 分支/worktree 操作

## 使用边界

- **自动触发**：`invoke: model`，在开发场景中由路由自动命中
- **不适用**：纯知识问答、不需要工具的简单解释场景
