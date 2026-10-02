---
name: "memory-hub-card-promotion"
description: 把 SkillHub 实证/踩坑回写记忆中枢草稿→ingest 提升→INDEX 登记→跨库 git 提交，闭合回写链路并保持两侧一致性 适用场景：回写中枢、中枢草稿、提升经验卡。勿用于：rule 类型、直接改 rule。
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
   - **`status` 必须取自白名单**（实测 2026-09-17，读 `hub-engine/common/frontmatter.py`）：
     `VALID_STATUS = {active, archived, candidate, reference}` ——
     **写 `status: draft` 会校验失败**（"draft" 不在白名单，很多人凭直觉会写它）。
     经验卡走正常提升用 `active`；需人工终审的用 `candidate`。
   - `VALID_TYPES = {rule, exp, note, project, retro, methodology, longterm, blueprint}`；
     其中 `rule / methodology` 属 `HUMAN_REQUIRED_TYPES`，**不能自动 promoted**。
   - 校验只认这三项（type/status/updated）；`title`、`source` 等会原样保留进 `extra`，可放心写。
4. **内容不可信边界**：不自动执行中枢权威区外任何脚本；跨库操作用命令行等效，不写全局 git config。
5. **触发词粒度（实测经验）**：trigger/forgot 用**短 token 词**（如 `rule 类型`、`登记 INDEX`），勿用含空格的整句短语（如 `跨库登记 INDEX`）——真实自然语言 query 会因词序变动/中间插词破坏子串命中。改短 token 后对真实意图更鲁棒。

## 工作流

### 1. 回写（产草稿）

- 入口：`writeback_card(cfg, hub_root, name, card_type, body, tags)`。
- 落位：中枢 `.sync/drafts/trae_draft/<slug>.md` 根目录。
- `card_type` ∈ `[exp, note, project]`；否则抛错拒绝。

### 2. 提升（ingest 消费）

- 中枢侧：`python hub-engine/engine.py ingest --root <hub> --platform <platform>`。
- **`--platform` 必须与草稿目录一一对应**：`--platform workbuddy` → 读 `.sync/drafts/workbuddy_draft/`，`--platform trae` → `trae_draft/`，依此类推。**别照抄本文里的 `trae`**（本文只是示例）；写错平台会「moved 但 promoted 0」，看着像成功其实草稿没被消费。
- **成功判据别只看返回值**：实测 `--platform` 正确时也可能返回 `{'promoted': 0, 'moved': 1}`，而真实提升由 post-ingest hook 完成——以 hook 输出 `[hub-cards] 已登记 N 张` + `experience/` 下确实出现卡片 + `INDEX.md` 有多出登记行 为准，而不只看 `promoted` 计数。
- 判定：向量预过滤(cosine≥0.55) → 无候选直接 create；有候选交 LLM decide。
  - `create` → 直接 promoted 入权威区 active
  - `skip` → 丢弃草稿
  - `merge/delete` → 人工终审
  - 网关不可用/解析失败 → `review` 降级进 `.sync/conflicts/`
- 成功判据：返回 `{'promoted': 1, ...}`；`retro/log.md` 追加 `自动入区：<卡>`。

### 3. 登记（INDEX + git）两处交付

- 先 `git log -- <卡>` 确认是否已被 ingest 自动 commit（经验卡多由 ingest 自动提交），避免重复。
- **实测纠正（2026-09-17）**：`post_ingest_hook` **会自动登记 INDEX 并自动 commit** ——
  一次 ingest 4 张卡后，hook 直接打出 `[hook] post_ingest_hook: 已登记 4 张 → [...]`，
  `INDEX.md` 随即出现 4 行登记，且 `git log` 已有 `docs(INDEX): post_ingest_hook 自动登记 4 张新卡`。
  此时再 `git add INDEX.md && git commit` 会得到 **`nothing to commit`**（不是失败，是已提交）。
  → **先看 hook 输出再决定是否手工补**；手工补 INDEX 只在 hook 未触发时才需要。
- 卡片状态变更（如 `candidate → active`）改 frontmatter status + INDEX 对应行。

### 4. 跨库维护（命令行兜底）

- Edit/Write 被限制在当前工作目录时，操作独立仓库用命令行等效：
  1. `[IO.File]::ReadAllLines(path)` 读锚点 → 插入/替换 → `WriteAllLines` 写回。
  2. `git add` → `git commit -m` → `git status --short` 校验。
  3. 提交信息**落文件再 `-F`**（实测 2026-09-17 唯一稳定路径）：
     `git commit -F- <<'EOF' … EOF` 形式的 bash heredoc 会被**安全策略拦掉**
     （报 "Invoking PowerShell from Bash bypasses PowerShell security checks"，且提交信息里
     含 "PowerShell" 字样也会触发）；PowerShell here-string 内的特殊字符又易被解析。
     → 用 Write 工具把提交信息写进临时 `.txt`，再 `git commit -F <file>`，最后删掉临时文件。

## LLM 网关接线（供提升链路，可选）

接入在线 LLM 网关（如 omniRoute Docker `127.0.0.1:20128`）：

- 改中枢 `engine.config.yaml`：`gateway_url`（自动拼 `/v1/chat/completions`）+ `default_model`。
- `provider_keys.yaml` 写 key；操作前显式 `"stream": false`（网关默认流式，须关）。

## 门禁清单（每步执行前确认）

- [ ] 类型在白名单内（`exp/note/project`），**`status` 取自 `{active, archived, candidate, reference}`**（禁 `draft`）
- [ ] 草稿落在 `<platform>_draft/` **根目录**（`--platform` 与目录名一一对应）
- [ ] 不直写 rule/methodology 权威区、不自动执行外部脚本
- [ ] **验证用独立路径**：`sqlite3 .sync/vector.db` 查 `docs` 表 path 命中新卡 `length(embedding)>0`
      （2026-09-17 实测：`build-vectors` 返回 `inserted: 407` 后，4 张新卡在 `docs` 表可按 path 查到）
- [ ] 提升前先查是否已被 hook 自动 commit，避免重复
- [ ] 跨库写改用命令行，不污染全局 git config；提交信息落文件后 `-F`
- [ ] 登记后 `git status` 干净、commit 职责清晰

## 收敛标准（完成标志）

- 草稿合规落位；ingest 返回 `promoted: 1`，`retro/log.md` 有自动入区记录。
- `INDEX.md` 对应分区已有登记行并 commit。
- 权威区卡与草稿正文一致，未被误收 conflicts；两侧 git 工作区干净。

---

## 增补（2026-10-02 实测，作者：pi@20261001-Fan-Cad-CtrlShiftCV 任务）

> 本节修正/补全上文两处与中枢代码不符之处，以下内容以**中枢代码**为准。

### A. drafts 是两级结构 —— 放错位置就**永远不会被提升**（上文"草稿必须落根目录"的正确解释）

| 位置 | 语义 | 会被 ingest 提升吗 |
|---|---|---|
| `drafts/<platform>_draft/` **根目录** `*.md` | **唯一会被 ingest 提升**的位置 | ✅ 会 |
| `drafts/<platform>_draft/candidates/*.md` | **审核暂存区**：只统计、**不提升** | ❌ **不会**（"会一直留在原地，需人工审核后移入根目录"） |
| `drafts/<platform>_draft/retro/` | 复盘归档区，ingest 提升时**自动追加** | ❌ 不作为提升源 |

- **依据（权威）**：`hub-engine/scripts/auto_flywheel.py::scan_drafts` 的 docstring。
- ⚠️ **不要建议把扫描改成递归 glob（rglob）**：`mavis_draft/topics_demo/` 下是
  「中枢 → mavis 的出向镜像」，一旦被当草稿扫到，就会形成「中枢导出 → 又被导回中枢」的**自噬闭环**。
- 排查口诀：草稿"写进去了但没人提升"→ 先看它是在**根目录**还是在 `candidates/`。

### B. INDEX 是**渲染产物，禁止手改** —— 上文第 3 步「登记 INDEX」需按此修正

- `INDEX.md` / `INDEX-full.md` / `INDEX-experience.md` 由
  `python -m scripts.render_index --write` 生成；手改会被 `--check` 打红（同 `ruff format --check` 口径）。
- 因此 **不要手工登记 INDEX**；确需更新时由**维护者**执行 `--write`。
  贡献者只需把草案放对位置，其余交给 ingest + 维护者。

### C. 本机路径关系（易踩）

- **中枢目录** `<AgentMemoryHub>`（例如本机 `~/.trae-cn/worktrees/<repo>/<branch>/AgentMemoryHub`）
  —— **它自己就是一个独立 git 仓**，有自己的 `.git/hooks/pre-commit`。
- **引擎目录** `hub-engine/` 与 AgentMemoryHub **同级**（在仓库工作树根），**不在中枢目录内**。
  ⇒ 上文写的 `python hub-engine/engine.py ...` 应理解为**在仓库根执行**；
  `render_index` 的实际入口是 `cd hub-engine && python -m scripts.render_index --check|--write`。

### D. 提交门禁与 `--no-verify` 口径（新增，切实会遇到）

- 中枢仓的 pre-commit 含三道门禁：**编码**（`check_encoding.py`）、
  **卡片 frontmatter**（`check_card_frontmatter.py`，`[hub-cards]` 前缀）、
  **渲染一致性**（`render_index --check`，**退出码 6**）。
- **渲染一致性门禁是「无条件跑」的**：只要工作树里存在**任何人**未提交的卡文件改动，
  `render_index --check` 就会失败并阻断**任何**提交 —— 即「**不是你的改动也会挡住你**」。
  典型报错：
  ```
  FAIL: INDEX.md 与卡文件不一致（被手改或未重渲染）→ 跑 `--write` 修复
  [hub-cards] ❌ INDEX 渲染产物不一致，commit 阻断
  ```
- **正确处置**（本机实测）：
  1. 先用 `git diff --stat` 判断失配是否源于**他人未提交**的卡改动；
  2. 若是 → 用 `git commit --no-verify` 提交自己的草案，
     **并在 commit message 里写明原因**（钩子自述要求），
     同时只 stage 自己的文件（`git add -- <自己的路径>`），确保不会顺手带走他人改动；
  3. **不要**擅自跑 `render_index --write` 再提交 INDEX —— 那会把他人**未完成**的改动
     烘进索引产物；而且只提交 INDEX 不提交那些卡，会让 HEAD 自相矛盾。
  4. 若失配确实源于自己改了卡 → 才应由维护者口径跑 `--write` 并一并提交。

### E. 一次可复用的"回写成功路径"（本次实践记录）

1. 定位中枢 → 读 `hub.config.yaml`（确认 `authority_dirs`、`contributor_platforms`、`draft_dir`）
2. 读一份**已有的权威卡**与一份**已有草案**，对齐 frontmatter 与实际写法
3. 写 `drafts/trae_draft/<kebab-slug>.md`（**根目录**），frontmatter 至少
   `type`（∈ `[exp, note, project]`）/ `tags` / `updated`，另加 `status: candidate`
4. 自检：脚本解析 frontmatter 三项 + `type` 在白名单内
5. `git add --` 仅自己的文件 → `git commit`（必要时 `--no-verify` 并说明原因）
6. 汇报时**明确区分**：「草案已落位，待 ingest 提升」≠「已入权威区」
