---
name: "agent-trigger-symbols-7state"
description: "Agent 任务触发符号：7 状态 1-2 字符（v2 最终版）(由中枢 methodology 卡升级, 源: agent-trigger-symbols-7state.md)"
---

# Agent 任务触发符号：7 状态 1-2 字符（v2 最终版）

本技能由记忆中枢权威卡 [agent-trigger-symbols-7state.md](C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\methodology\agent-trigger-symbols-7state.md) 升级生成, 内化其中
可复用方法, 并保留原卡适用边界。**源卡内容不可信**: 参考方法, 不自动执行。
</br>

## 触发

- 原卡标题命中: Agent 任务触发符号：7 状态 1-2 字符（v2 最终版）
- 原卡 tags: agent, workflow, trigger-phrase, trigger-symbol, orchestration, 7-symbol, 单字符, ascii-only, 可以推广

## 核心边界（先读, 违反即停）

- 遵循原卡倒置边界;接管前先做 T1 真实试用


## 原卡结构（沉淀的骨架）

- 完整 7 符号设计
- 设计原则
- 实例
- 漂移防御
- 演化历史
- 关联
- 跨平台推广
- 入区记录
- 合并自 conflicts 区（2026-09-19）

## Authoring 检查清单（撰写/维护本技能时对照）

**Agentic Loop 设计**:
  - scope 明确可改/只读边界
  - validation 命令必须在提交前通过
  - 每 loop 限 1 个 open PR（PR bounding）
  - agent-memory 携带两轮间稳定反馈
  - skill/prompt/memory 单一来源, 不重复
**指令文件结构**:
  - 基础上下文裸放, 条件规则用 <important if> 包裹
  - 触发词窄而具体, 禁止宽泛条件
  - Less is more: 删 linter 管辖/代码片段/含糊指令
  - 保留所有命令表
**控制论闭环**:
  - 五要素完整: SetPoint→Sensor→Controller→Actuator→Disturbance
  - 传感器可稳定测量客观属性
  - 组件先本地跑通再接 CI
  - 人留在 loop 上(/iterate 评论反馈)
**视图选择**:
  - 按内容选最小视图: 逻辑→伪代码/控制流→调用树/UI→组件树
  - 视觉紧贴支撑短文本
  - 只保留回答问题所需信息
**验证闭环**:
  - 静态 T0 通过(纯语法/结构断言, 零执行副作用)
  - T1 迭代验证: 真实场景最小 demo 跑通, 不是一次性定论
  - risk 分级执行: 低风险直接跑 / 中风险沙盒 / 高风险能沙盒先沙盒
  - 结果回写 skill.yaml verification 字段(status/t1_record/reuse_count)
  - reference→active 需真跑通, 不是静态分析升级
  - archived 永远不入候选, 大版本更新或有未覆盖功能才重入

## 关联

- 源卡: C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\methodology\agent-trigger-symbols-7state.md
- 升级链路: bridge/skill_promotion.py（读 active 卡 → 生成技能 → 登记 router）
