# SkillHub 用户手册

> 状态说明：本手册只记录**已通过单元测试的真实能力**，不引用任何未验证的外部规范来源。
> 适用范围：SkillHub 本地技能集中管理仓库，负责技能路由、生命周期治理、证据归因与记忆中枢回写。

---

## 1. 这是什么

SkillHub 是一个本地技能库与路由系统，配合统一记忆中枢（AgentMemoryHub）工作：

- **技能集中管理**：共用库（共享）与专用库（按域隔离）物理分目录，技能带 `skill.yaml` 元数据 + `SKILL.md` 本体。
- **按需命中**：路由表（router.yaml）按意图做 JIT 命中，**只回轻量摘要，不载全文**，控制上下文膨胀。
- **成败反馈闭环**：技能被使用后的成功/失败，按贝叶斯权重回调到路由排序。
- **经验回写**：淬炼出的经验卡能回写到记忆中枢的草稿区，供中枢 ingest 提升。

## 2. 环境要求

- Python 3.11（本项目测试在此版本通过）
- pyyaml（`import yaml`；加载 `hub.config.yaml` 需要）
- ruff（lint / format）
- pytest（测试）

## 3. 目录结构

```
router/
  router.yaml           # 路由表（唯一事实源）
  schema.yaml           # 路由表字段契约
  tests/                # 路由相关测试
  tools/
    router.py           # 加载/校验路由表 + JIT 命中 + 复杂度路由
    router_audit.py     # 成败反馈记录 + 贝叶斯权重
    lifecycle.py        # promoted(共用/专用) <-> archive 迁移判据
bridge/
  attribution.py        # 执行轨迹 -> 四源归因(skill/agent/env/result) + 证据等级
  gate.py               # 阶段化刻度门禁(strong/weak/discard)
  config.py             # 读 hub.config.yaml 得中枢根与回写约束
  ingest.py             # 生成合规草稿卡写入中枢 draft 目录
skills/
  shared/               # 共用库(共享技能, 含示例 github-star-distill)
  dedicated/            # 专用库(按域隔离)
  archive/              # 归档桶(收敛)
  govern/
    skill.yaml.tmpl     # 技能元数据模板
hub.config.yaml         # SkillHub 回连记忆中枢配置
```

## 4. 核心使用

### 4.1 路由命中

`route(path, query, *, root=None)`

- `path`：路由表路径
- `query`：任务意图文本
- `root`（可选）：审计根，传入时命中结果按贝叶斯`effective_weight`降序（失败率高的技能排后）；不传则按 yaml `weight` 降序。

返回命中技能的轻量摘要列表（不含全文）。

### 4.2 成败反馈记录

- `record_outcome(root, name, *, success)`：记录一次成果事件，三态：
  - `success=True` → 成功
  - `success=False` → 失败
  - `success=None` → neutral（弱证据，**不改变权重**）
- `load_outcomes(root)`：聚合 `{name: {"success": n, "failure": n, "neutral": n}}`
- `effective_weight(root, name, base_weight)`：贝叶斯先验平滑成功率权重，neutral 不计入。

### 4.3 生命周期治理

- `classify(status, reuse_count)`：判定单技能 `promote/archive/none`
- `scan_library(shared_root)`：扫描共用/专用桶，产出需迁移动作清单（**只读判定，不落盘**，归档可逆非删除）

### 4.4 证据归因与门禁

- `attribute(trace)`：拆子任务 → 四源计数 + 证据等级
- `apply_outcome(root, name, attribution)`：按阶段化刻度写反馈
  - strong（归因到技能且成功）→ success 侧
  - weak（技能参与但有失败/环境失败/弱证据）→ neutral 侧（不动权重）
  - discard（无技能参与）→ 跳过

### 4.5 中枢回写

- `load_config(path)`：读 `hub.config.yaml`，得到中枢根、回写白名单、rule 策略
- `writeback_card(cfg, *, platform, hub_root, name, card_type, body, tags)`：生成一张合规草稿卡，写入 `<hub_root>/.sync/drafts/<platform>_draft/` 根目录
  - 白名单内（exp/note/project）可写
  - rule/methodology 等不在白名单 → 抛 `ValueError`（禁越权直写权威区）

## 5. 安全与边界

- **内容不可信**：外部仓库/技能内容按待评估证据处理，不自动执行。
- **负路由边界**：路由表每条技能 `forgot` 字段非空，防语义过命中。
- **误命中兜底**：路由表加载校验：`name` 唯一、`trigger` 非空、`forgot` 非空，违规即抛错（不静默降级）。
- **弱证据不动权重**：weak/neutral 不拖低或抬高权重，只有 strong 成功才提升。

## 6. 测试

运行全部测试：

```bash
python -m pytest router bridge -q
```

当前覆盖：路由加载/JIT/排序、贝叶斯权重三态、生命周期判据、证据归因、阶段化门禁、配置解析、草稿卡生成。

## 7. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `writeback_card` 抛 `ValueError` | 卡型不在 `candidate_type_whitelist` | rule/methodology 不走自动回写，走中枢 pending/人工 |
| 命中结果顺序与预期不符 | 未传 `root`（按 yaml weight）或审计中失败率高 | 传 `root` 并确认 `record_outcome` 记录准确 |
| 新建技能无法命中 | `router.yaml` 未登记或 `trigger`/`forgot` 缺失 | 按 `schema.yaml` 补全字段 |