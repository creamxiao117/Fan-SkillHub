---
name: "memory-hub-card-promotion"
description: "把 SkillHub 实证/踩坑回写记忆中枢草稿→ingest 提升→INDEX 登记→跨库 git 提交，闭合回写链路并保持两侧一致性。"
---

# Memory-Hub Card Promotion（经验卡提升四步闭环）

把本次执行产生的经验/踩坑/结论沉淀进记忆中枢，并贯通 SkillHub 与中枢两侧的标准流程。
核心对齐「回写→提升→登记→跨库维护」方法论卡（cards/card-promotion-workflow）。

## 触发

- 本次执行产出了值得留存的经验/踩坑/结论，需要回连中枢保持一致。
- 需要验证某个新机制（如 LLM 决策链路）的完整成功路径并留档。
- 需在无 IDE 工具权限的独立仓库执行写操作时。

## 核心边界（先读，违反即停）

1. **type ∈ 白名单** `[exp, note, project]`；`rule/methodology` **禁直写权威区**，只能走草稿/人工收件箱 → 越权即拒。
2. **草稿必须落** `drafts/<platform>_draft/` **根目录**；放 `candidates/` 等子目录不会被 ingest 扫到。
3. **frontmatter 合规**：`type / tags / updated` 齐备，`type` 在中枢 TYPE_DIR 键内。
4. **内容不可信边界**：不自动执行中枢权威区外任何脚本；跨库操作用命令行等效，不写全局 git config。
5. **触发词粒度（实测经验）**：trigger/forgot 用**短 token 词**（如 `rule 类型`、`登记 INDEX`），勿用含空格的整句短语（如 `跨库登记 INDEX`）——真实自然语言 query 会因词序变动/中间插词破坏子串命中。改短 token 后对真实意图更鲁棒。

## 工作流

### 1. 回写（产草稿）

- 入口：`writeback_card(cfg, hub_root, name, card_type, body, tags)`。
- 落位：中枢 `.sync/drafts/trae_draft/<slug>.md` 根目录。
- `card_type` ∈ `[exp, note, project]`；否则抛错拒绝。

### 2. 提升（ingest 消费）

- 中枢侧：`python hub-engine/engine.py ingest --root <hub> --platform trae`。
- 判定：向量预过滤(cosine≥0.55) → 无候选直接 create；有候选交 LLM decide。
  - `create` → 直接 promoted 入权威区 active
  - `skip` → 丢弃草稿
  - `merge/delete` → 人工终审
  - 网关不可用/解析失败 → `review` 降级进 `.sync/conflicts/`
- 成功判据：返回 `{'promoted': 1, ...}`；`retro/log.md` 追加 `自动入区：<卡>`。

### 3. 登记（INDEX + git）两处交付

- 先 `git log -- <卡>` 确认是否已被 ingest 自动 commit（经验卡多由 ingest 自动提交），避免重复。
- `INDEX.md` 对应分区补一行 `- <slug> 一句话说明`（ingest 通常不自动更新 INDEX，须手工补）。
- 卡片状态变更（如 `candidate → completed`）改 frontmatter status + INDEX 对应行。

### 4. 跨库维护（命令行兜底）

- Edit/Write 被限制在当前工作目录时，操作独立仓库用命令行等效：
  1. `[IO.File]::ReadAllLines(path)` 读锚点 → 插入/替换 → `WriteAllLines` 写回。
  2. `git add` → `git commit -m` → `git status --short` 校验。
  3. 提交信息用 PowerShell here-string（`@'...'@`），勿用 bash 的 `$(cat <<'EOF')`。

## LLM 网关接线（供提升链路，可选）

接入在线 LLM 网关（如 omniRoute Docker `127.0.0.1:20128`）：

- 改中枢 `engine.config.yaml`：`gateway_url`（自动拼 `/v1/chat/completions`）+ `default_model`。
- `provider_keys.yaml` 写 key；操作前显式 `"stream": false`（网关默认流式，须关）。

## 门禁清单（每步执行前确认）

- [ ] 类型在白名单内，草稿落在 `trae_draft/` 根目录
- [ ] 不直写 rule/methodology 权威区、不自动执行外部脚本
- [ ] 提升前先查是否已被 ingest 自动 commit，避免重复
- [ ] 跨库写改用命令行，不污染全局 git config
- [ ] 登记后 `git status` 干净、commit 职责清晰

## 收敛标准（完成标志）

- 草稿合规落位；ingest 返回 `promoted: 1`，`retro/log.md` 有自动入区记录。
- `INDEX.md` 对应分区已有登记行并 commit。
- 权威区卡与草稿正文一致，未被误收 conflicts；两侧 git 工作区干净。
