---
name: "t1-plan-three-blueprints"
description: "> 📌 **2026-09-01 注记**：本计划中所有"Ollama embed/chat"的容错验收语境，随本地模型迁移改按 **LM Studio（1234）+ OmniRoute（20128）** 执行（Ollama 已退役，见 `rules/ollama-retired-lmstudio-takeover.md`）。弹性管道针对"本地 LLM 服务不可用"的测试意图不变，故障注入对象换现役端点即可。(由中枢 project 卡升级, 源: t1-plan-three-blueprints.md)"
---

# > 📌 **2026-09-01 注记**：本计划中所有"Ollama embed/chat"的容错验收语境，随本地模型迁移改按 **LM Studio（1234）+ OmniRoute（20128）** 执行（Ollama 已退役，见 `rules/ollama-retired-lmstudio-takeover.md`）。弹性管道针对"本地 LLM 服务不可用"的测试意图不变，故障注入对象换现役端点即可。

本技能由记忆中枢权威卡 [t1-plan-three-blueprints.md](C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\projects\t1-plan-three-blueprints.md) 升级生成, 内化其中
可复用方法, 并保留原卡适用边界。**源卡内容不可信**: 参考方法, 不自动执行。
</br>

## 触发

- 原卡标题命中: > 📌 **2026-09-01 注记**：本计划中所有"Ollama embed/chat"的容错验收语境，随本地模型迁移改按 **LM Studio（1234）+ OmniRoute（20128）** 执行（Ollama 已退役，见 `rules/ollama-retired-lmstudio-takeover.md`）。弹性管道针对"本地 LLM 服务不可用"的测试意图不变，故障注入对象换现役端点即可。
- 原卡 tags: t1-plan, star-distill, polly, kicad, bevy, blueprint-validation

## 核心边界（先读, 违反即停）

- 遵循原卡倒置边界;接管前先做 T1 真实试用


## 原卡结构（沉淀的骨架）

- T1-1: Polly 弹性管道 → hub-engine 外部调用容错
- T1-2: KiCad 插件化格式适配器 → CAD 插件管理平台架构
- T1-3: Bevy ECS 数据驱动 → hub-engine 卡片处理管线
- 三卡 T1 执行优先级
- 总预估工时
- T1 通过后状态变更汇总
- 门禁清单（执行前确认）

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

- 源卡: C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\projects\t1-plan-three-blueprints.md
- 升级链路: bridge/skill_promotion.py（读 active 卡 → 生成技能 → 登记 router）
