# SkillHub 项目交接手册（trae work → Hermes）

> 交接时间：2026-09-06
> 交接方：trae work（本平台只维护 SkillHub，中枢归 Hermes）
> 接收方：Hermes（后续由你统一维护，含中枢收口）
> 本文档用途：快速接手依据，避免重复勘查

---

## 1. 项目是什么

**SkillHub**：一套「经验/方法论 → 技能」的自动进化中枢，与 AgentMemoryHub（记忆中枢）通过共享文件系统 + git 联动。核心闭环由 GitHub Actions 每日自动驱动。

```
中枢卡(exp/methodology/blueprint)
  ──reconcile──▶ 本地技能(skills/ + router/) ──record/weight──▶ 权重
      ▲                                                          │
      └────────────── push-to-hub ──────────────────────────────┘
              （晋级 active 后回写中枢卡 status/reuse_count）
```

## 2. 仓库定位与关键配置

| 项 | 值 |
|---|---|
| 仓库根 | `D:\AIwork\20260821-Fan-SkillHub` |
| 远程 | `git@github.com:creamxiao117/Fan-SkillHub.git`（SSH，gh 有 GH_TOKEN + keyring 双凭据） |
| 中枢根 | `C:/Users/Fan-SJSS/.trae-cn/worktrees/.../AgentMemoryHub`（见 `hub.config.yaml`，唯一出处） |
| 槽位目录 | `skills/shared`（通用）、`skills/dedicated/<domain>`（域名专属，带 scope）、`skills/archive`（归档） |
| CLI 入口 | `python -m skillhub <命令>`（12 命令） |
| 用户手册 | `docs/USER_MANUAL.md` |
| 流程文档 | `cards/`（card-promotion-workflow、ingest-chain、repo-communication-protocol） |

## 3. 核心链路现状（2026-09-06 实证）

| 链路 | 状态 | 实证 |
|---|---|---|
| 升级（经验/方法论→技能） | 🟢 通且已自动化 | reconcile `--card-type blueprint,methodology,exp` 三源放开（run 34023367297 实测 apply 5 张 exp/methodology 卡） |
| 调度 CI | 🟢 健康 | 每日 06:34 UTC 成功；产物直接 push 回 master |
| 反馈 sync-verification | 🟢 通 | usage.jsonl → 双源回填 reuse_count |
| 晋级 promote-auto | 🟢 安全网正常 | reuse_count≥3 + t1_record 才晋级（t1 空则拦截，防 false 功劳） |
| 回写 push-to-hub | 🟢 通 | 回写中枢卡 status/reuse_count |
| 产物回流 | 🟢 已修复 | 见下章「已完成的修复」 |

## 4. 已完成的修复（2026-09-06 里程碑）

1. **P0 产物回流 master**（commit `6acd9cc`）：仓库禁 Actions 开 PR（`GitHub Actions is not permitted to create or approve pull requests`）→ 放弃 PR 流程，改由 `secrets.HUB_PAT` 直接 push master 产物。CLONE 步骤加 `.hub_clone_ok` 标志门控 + `rm -rf .hub` 修复误跟踪。
2. **P1 reconcile 三源放开**（同一 commit）：`--card-type blueprint` → `blueprint,methodology,exp`。注意：非 blueprint 卡要求中枢 `status=active` 才进候选；blueprint 卡要 `reuse_count>=1`。
3. **P2 汇入滞留产物**：auto-evolution 分支 5 张新技能合回 master。
4. 经验沉淀：两卡已入中枢权威区（`ci-push-products-back-to-master`、`reconcile-card-type-multisource-flywheel`，commit `9469f3a`/`c7da0f0`，已 push 远程 `9b6964d`）。

## 5. 运维关键点（接手必读）

### CI 依赖的 Secrets（仓库 → Settings → Secrets）
- `HUB_PAT`：**必须存在**（仓库 owner 的 PAT，CI 用它 clone 私有中枢 + push 产物回 master）。为空则相关步骤跳过，飞轮空转。
- `GITHUB_TOKEN`：内置，仅用于基础操作；**不能用来创建 PR**（被仓库级策略限制）。

### 仓库级设置要点
- **Actions → Workflow permissions**：允许创建 PR 未勾选（所以 CI 用 PAT 直推 master 而非 PR）。若未来想改回 PR 流程，需在网页勾选，并把 workflow 的 push-master 步骤改回 create-pull-request。

### 飞轮「转但不产出」的排查判据
- CI 成功但 master 没变 → 查 `git ls-remote origin <branch>` 是否产物进了别的分支；看 push-master 步骤日志是否报 permission / 空 flag。
- reconcile 输出 `0 updated` → 大概率 `.hub` clone 失败（HUB_PAT 空 或 clone 路径非空前残留），看 Clone 步骤。

## 6. 使用反馈 → 晋级（主动维护项）
- 飞轮要真正 reference→active 晋级，需真实使用时调用 `skillhub record <slug>`（写 usage.jsonl），再 `sync-verification` 双源回填、`promote-auto` 晋级。
- 当前 30 技能全为 reference、reuse_count 不足 → promote 全 skip 是**正确**安全网，非故障。

## 7. 待办/待确认（交接前遗留）
- [ ] Master 已与远程同步（fast-forward 至 `db05341`），31 技能就位，基线干净。
- [ ] 使用反馈（record 调用）未接通 → 如需晋级，需设计"何时/谁触发 record"。
- [ ] 中枢侧 4 项待定（`M retro/log.md`、`M rules/rules-routing-table.md`、`?? projects/pluginhub-current-state.md`、`?? rules/auto-promote-empty-today-rule.md`）——属 Hermes 职责，trae work 不越权处理。

## 8. 交接方式（给 Hermes）
- 建议用 `hermes project create skillhub` 绑定仓库根 + `hermes project bind-board`（如需看板→worktree 约定）。
- 中枢维护（ingest/INDEX/git push/四平台同步）全部由 Hermes 收口；SkillHub 仓库本体（workflow、skills、router）由维护方负责。