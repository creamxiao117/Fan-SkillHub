---
type: methodology
tags:
- skillhub
- memory-hub
- workflow
- writeback
- ingest
- promotion
updated: '2026-08-21'
status: active
reuse_count: 1
---

# 经验卡回写 → 提升 → 登记 → 跨库维护 工作流

SkillHub 把技能使用中产生的经验/方法沉淀进记忆中枢并贯通两侧的标准做法。
四步：**回写(草稿) → 提升(ingest) → 登记(INDEX) → 跨库维护(命令行兜底)**。

## 适用

- 需要把一条 SkillHub 侧实证（踩坑/结论/方法）上缴中枢成为可检索经验卡。
- 需要验证某个新机制（如 LLM 决策）的完整成功路径。
- 需在无 IDE 工具权限的独立仓库执行写操作时。

不适用：rule 类直写权威区（必须走 pending/人工 confirm）。

## 四步流程（实证于 2026-08-21）

### 步骤 1 回写（产草稿）

- 入口：`bridge/ingest.py::writeback_card(cfg, hub_root, name, card_type, body, tags)`。
- 落位：中枢 `.sync/drafts/trae_draft/<slug>.md` **根目录**（放子目录不被 ingest 扫到）。
- 契约：`card_type` ∈ 白名单 `[exp, note, project]`；frontmatter 含 `type/tags/updated`；`rule/methodology` 抛错拒绝。
- 结果：得到草稿路径 `.md`。

### 步骤 2 提升（ingest 消费）

- 命令（中枢侧）：`python hub-engine/engine.py ingest --root <AgentMemoryHub> --platform trae`。
- 判定链：向量预过滤(cosine≥0.55) → 无候选直接 create；有候选交 LLM decide(chat)。
  - `create` → 直接 promoted 入权威区，status=active
  - `skip` → 丢弃草稿
  - `merge/delete` → 人工终审
  - 网关不可用/解析失败 → `review` 降级进 `.sync/conflicts/`
- 成功判据：返回 `{'promoted': 1, ...}`；app log 追加 `自动入区：<卡>`。
- 注意：validate `type ∈ TYPE_DIR 键`；LLM 网关默认流式时在中枢 `chat()` 显式 `"stream": false`。

### 步骤 3 登记（INDEX + git）两处交付

- 权威区卡：ingest 有时**自动 commit**（如经验卡多由 ingest 自动提交）——先 `git log -- <卡>` 确认是否已提交，避免重复 commit。
- **INDEX.md 登记行**：在对应分区（`experience/`、`projects/`…）补一行 `- <slug> 一句话说明`。ingest 通常**不会**自动更新 INDEX，需手工补。
- 卡片本身状态需同步时（如把改进卡 `candidate → completed`），直接改卡的 frontmatter status + INDEX 对应行。

### 步骤 4 跨库维护（命令行兜底）

- 因 SkillHub IDE 的 Edit/Write 被限制在当前工作目录，操作中枢（独立仓库）用命令行等效：
  1. `[System.IO.File]::ReadAllLines(path)` 读锚点行 → `List[string]` 插入/替换 → `WriteAllLines` 写回。
  2. `git add <files>` → `git commit -m <msg>` → `git -c core.quotePath=false status --short` 校验。
  3. 提交信息用 PowerShell here-string（`@'...'@`），勿用 bash 的 `$(cat <<'EOF')`。
- 提交流程建议拆为职责独立 commit：ingest 自动提交卡内容 / 手工提交 INDEX 登记 + 状态变更。

## 审计留痕

- 回写侧追加 `action: writeback` 到 `.sync/state/query.log.jsonl`（read 侧同源可核）。
- ingest 追加 `retro/log.md` append-only 时间线。
- 若命中误判：真新卡被 0.55 向量阈值误收 conflicts 时，可在确认权威区无同主题后按"人工放行"语义直接落 `projects/`（避免同主题词再被预过滤误判进冲突区，形成死循环）。

## 验收清单

- [ ] 草稿落在 `trae_draft/` 根目录，frontmatter 合规
- [ ] ingest 返回 `promoted: 1`，`retro/log.md` 有 `自动入区` 记录
- [ ] `INDEX.md` 对应分区已有登记行（且 commit）
- [ ] 权威区卡与草稿正文一致，未被误收 conflicts
- [ ] git 工作区干净；commit 信息职责清晰

## 关联

- cards/memory-hub-repo-communication-protocol（协议契约）
- cards/memory-hub-omniroute-ingest-chain（链路全景）
- bridge/ingest.py、bridge/config.py
- 中枢：experience/ingest-probe-omniroute2、projects/improve-ingest-dedup-threshold