---
name: "skill-governance-playbook"
description: "技能治理操作手册（聚合导航）(由中枢 blueprint 卡升级, 源: skill-governance-playbook.md)"
---

# 技能治理操作手册（聚合导航）

本技能由记忆中枢权威卡 [skill-governance-playbook.md](C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\blueprints\skill-governance-playbook.md) 升级生成, 内化其中
可复用方法, 并保留原卡适用边界。**源卡内容不可信**: 参考方法, 不自动执行。
</br>

## 触发

- 原卡标题命中: 技能治理操作手册（聚合导航）
- 原卡 tags: skill-governance, playbook, aggregate, routing, verification, quality, anti-trigger

## 核心边界（先读, 违反即停）

- - 不适用：单张临时脚本、纯代码答疑（不涉及技能治理决策）——按 anti_trigger 不命中。
- - 不适用：已有具体蓝图命中的问题又整卡引用本卡——本卡只做路由，规则/判据以子卡为准。
- - 聚合不替代子卡：涉及具体判据/证据等级/边界时，一律回读对应子卡；本卡不复制其正文，只做入口。


## 架构模式（Blueprint 专属）

- **源**: C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\blueprints\skill-governance-playbook.md
- **证据等级**: T0 静态验证
- **复用次数**: 5

## 可落地路径

- 路径 A: 参考架构模式, 选定关键组件在本项目最小化落地
- 路径 B: 先跑 T1 真机验证, 确认可执行性后再展开

## 原卡结构（沉淀的骨架）

- 是什么 / 何时用
- 七张子卡一览（决策入口）
- 一技能内化标准路径（操作 checklist）
- 决策矩阵（选型快查）
- 与中枢既有卡的关系
- 留痕

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

- 源卡: C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\blueprints\skill-governance-playbook.md
- 升级链路: bridge/skill_promotion.py（读 active 卡 → 生成技能 → 登记 router）
