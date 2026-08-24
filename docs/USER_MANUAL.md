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

```text
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

### 4.6 中枢 → SkillHub 反向回流（skill_promotion）

- `reconcile(hub_root, skill_root, *, apply, router_path)`：读中枢权威区 active 卡 → 判级 → 生成 `skill.yaml`+`SKILL.md` → 登记 `router.yaml`。
- **默认 dry-run**：只列出"将生成哪些技能 / 落哪个槽位"，不写盘；`apply=True` 才落盘（人工门禁后放行）。
- 判级：卡 `tags` 命中已知域（如 memory-hub）→ 归 `dedicated`+`scope`；`methodology/exp/blueprint` 默认归共用库；`rule/retro` 不自动升级。
- **Blueprint 升级门禁**：`blueprint` 卡额外要求 `reuse_count≥1` 才升级为技能（避免把 reference 级范式直接变成技能）。
- 只读中枢卡文本，**绝不自动执行中枢内脚本**（`guard_import_untrusted`）。
- 生成的 `SKILL.md` 自动注入 **Authoring 检查清单**（4 维度 16 条原则，来自中枢 4 张 methodology 卡）。

### 4.7 命令行入口（skillhub CLI）

#### 基础三命令

```bash
python -m skillhub route "借鉴某个 GitHub 项目的方法并内化"     # 意图命中(按权重降序)
python -m skillhub record cross-repo-index-commit --success     # 成败反馈落盘 .skillhub/usage.jsonl
python -m skillhub weight cross-repo-index-commit --root <path> # 贝叶斯有效权重
```

- `route`：命中技能按 `effective_weight` 降序（传入 `--root` 时）或 yaml `weight` 降序。
- `record`：三态 `--success/--failure/--neutral`，落到 `<root>/.skillhub/usage.jsonl`（`--root` 默认项目本地 `.skillhub`）。

#### 验证生命周期四命令

```bash
python -m skillhub sync-verification                           # 从 usage.jsonl 聚合 reuse_count 回写 skill.yaml
python -m skillhub promote <name> --status active              # 手动设置验证状态
python -m skillhub audit                                       # 扫描 authoring 检查清单覆盖率
python -m skillhub new <name> --slot shared                    # 创建新技能骨架(含 authoring 清单)
```

- `sync-verification`：聚合 `usage.jsonl` 中每个技能的 success+failure 次数 → 回写到对应 `skill.yaml` 的 `verification.reuse_count` 和 `verification.last_verified`。
- `promote`：手动将技能从 `reference` → `active`（或反向 `--status reference` / `--status deprecated`），同步更新顶层 `status` 和 `verification.status`。
- `audit`：扫描所有 `SKILL.md`，检查 4 大维度 authoring 检查清单（Agentic Loop 设计 / 指令文件结构 / 控制论闭环 / 视图选择）的覆盖率，输出缺失清单。
- `new`：创建新技能目录，自动生成含完整 authoring 检查清单的 `SKILL.md` 和 `skill.yaml`，省去手动搭骨架。

### 4.8 技能验证生命周期（verification schema）

每个 `skill.yaml` 新增 `verification` 字段，对齐中枢卡的 T0→T1→active 验证链路：

```yaml
verification:
  status: reference     # reference=静态验证 | active=T1真机通过 | deprecated=已废弃
  t1_record: ""         # T1 真机记录摘要（手动填写或由 promote 自动写入）
  reuse_count: 0        # 从 usage.jsonl 聚合的真实复用次数（由 sync-verification 自动更新）
  last_verified: ""     # 最后验证日期 YYYY-MM-DD
```

生命周期流转：

1. **新建**：`status=reference`，`reuse_count=0`，等待真实试用。
2. **sync-verification** 后：`reuse_count` 从 `usage.jsonl` 聚合，若 `≥3` 可建议 `promote`。
3. **promote** 后：`status=active`，`t1_record` 填充真机记录，技能进入正式可用状态。
4. **废弃**：`promote --status deprecated`，技能不再推荐路由命中。

## 5. 安全与边界

- **内容不可信**：外部仓库/技能内容按待评估证据处理，不自动执行。
- **负路由边界**：路由表每条技能 `forgot` 字段非空，防语义过命中。
- **误命中兜底**：路由表加载校验：`name` 唯一、`trigger` 非空、`forgot` 非空，违规即抛错（不静默降级）。
- **弱证据不动权重**：weak/neutral 不拖低或抬高权重，只有 strong 成功才提升。

## 6. 测试

运行全部测试：

```bash
python -m pytest -q
```

当前覆盖：路由加载/JIT/排序、贝叶斯权重三态、生命周期判据、证据归因、阶段化门禁、配置解析、草稿卡生成、Blueprint 卡接入与门禁、CLI 全部 7 个子命令。

## 7. 常见问题

| 现象 | 原因 | 处理 |
| ---- | ---- | ---- |
| `writeback_card` 抛 `ValueError` | 卡型不在 `candidate_type_whitelist` | rule/methodology 不走自动回写，走中枢 pending/人工 |
| 命中结果顺序与预期不符 | 未传 `root`（按 yaml weight）或审计中失败率高 | 传 `root` 并确认 `record_outcome` 记录准确 |
| 新建技能无法命中 | `router.yaml` 未登记或 `trigger`/`forgot` 缺失 | 按 `schema.yaml` 补全字段 |
| blueprint 卡未被提升为技能 | `reuse_count<1`（reference 级范式） | 在中枢补 T1 记录使 `reuse_count≥1`，重跑 `reconcile` |
| skill.yaml 的 `verification.reuse_count` 始终为 0 | 未跑 `sync-verification` | 先 `record` 成败事件，再跑 `sync-verification` 聚合 |
| audit 报告所有技能缺 authoring 清单 | 存量技能在新特性之前创建，未注入清单 | 对存量技能手动补充清单或 `new` 重建后迁移内容 |
