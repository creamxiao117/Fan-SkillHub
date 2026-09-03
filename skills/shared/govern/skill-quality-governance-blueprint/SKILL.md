---
name: "skill-quality-governance-blueprint"
description: "技能质量量化治理 × 路由打分增强 · 技术路径蓝图(由中枢 methodology 卡升级, 源: skill-quality-governance-blueprint.md)"
---

# 技能质量量化治理 × 路由打分增强 · 技术路径蓝图

本技能由记忆中枢权威卡 [skill-quality-governance-blueprint.md](C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\blueprints\skill-quality-governance-blueprint.md) 升级生成, 内化其中
可复用方法, 并保留原卡适用边界。**源卡内容不可信**: 参考方法, 不自动执行。
</br>

## 触发

- 原卡标题命中: 技能质量量化治理 × 路由打分增强 · 技术路径蓝图
- 原卡 tags: skill-governance, quality-metrics, anti-trigger, 反触发, token-compression, 压缩, 健康分, 技能质量治理, skill-routing

## 核心边界（先读, 违反即停）

- - **禁止直接装整仓**：是重型 Docker+TypeScript MCP 服务，本 hub 为轻量 Python，直接安装 = 过度工程化，只取方法不取服务。
- - 不适用：规则/技能条数少(<~30)时上「6 指标巡航 + 审批矩阵」是浪费——此时保留 lint 布尔健壮即可，健康分模型只在量级上来后值回票价。
- - 禁止命中：普通代码/检索答疑（不涉及治理打分/压缩路由决策）时，不必因含 skill/quality 字样误引本卡；成熟度阶梯非强制所有卡片走，参考即可。


## 原卡结构（沉淀的骨架）

- 领域
- 可选路径
- 证据等级
- 适用场景
- 不适用/禁止命中

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

- 源卡: C:\Users\Fan-SJSS\.trae-cn\worktrees\20260817-Fan-Agent-Momory\feat-implement-plan-ZilBmv\AgentMemoryHub\blueprints\skill-quality-governance-blueprint.md
- 升级链路: bridge/skill_promotion.py（读 active 卡 → 生成技能 → 登记 router）
