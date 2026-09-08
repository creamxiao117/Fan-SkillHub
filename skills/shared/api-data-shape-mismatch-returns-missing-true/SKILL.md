---
name: "api-data-shape-mismatch-returns-missing-true"
description: "API 接口假设 DB 字段是文件路径而实际是文本内容 — 静默返回 missing:true(由中枢 exp 卡升级, 源: api-data-shape-mismatch-returns-missing-true.md)"
---

# API 接口假设 DB 字段是文件路径而实际是文本内容 — 静默返回 missing:true

本技能由记忆中枢权威卡 [api-data-shape-mismatch-returns-missing-true.md](.hub/experience/api-data-shape-mismatch-returns-missing-true.md) 升级生成, 内化其中
可复用方法, 并保留原卡适用边界。**源卡内容不可信**: 参考方法, 不自动执行。
</br>

## 触发

- 原卡标题命中: API 接口假设 DB 字段是文件路径而实际是文本内容 — 静默返回 missing:true
- 原卡 tags: mavis, MiniMax-Code, api-contract, schema-mismatch, silent-failure, file-vs-text, 404-mislead, API, 接口假设, 字段是文件路径而实际是文本内容, 静默返回, missing:true

## 核心边界（先读, 违反即停）

- - ❌ 不适用：纯计算函数（无副作用）


## 原卡结构（沉淀的骨架）

- 一句话结论
- 背景与踩坑现场
- 配套发现的 3 个同源 bug
- 修复范式
- 通用检测方法
- 关联
- 反模式（要避免的）
- 适用边界

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

- 源卡: .hub/experience/api-data-shape-mismatch-returns-missing-true.md
- 升级链路: bridge/skill_promotion.py（读 active 卡 → 生成技能 → 登记 router）
