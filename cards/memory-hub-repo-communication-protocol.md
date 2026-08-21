---
type: note
tags:
- skillhub
- memory-hub
- protocol
- communication
- contract
updated: '2026-08-21'
status: active
reuse_count: 1
---

# SkillHub ↔ AgentMemoryHub 通信协议契约

两个独立 git 仓库**无直接 RPC/HTTP 连接**，通过**共享文件系统路径 + git 历史**做
异步解耦协作。本卡固化交接物、位置、白名单、幂等、安全门等硬性契约，避免各方
臆造、越权、破坏并发一致性。

## 1. 定位通道（唯一事实源）

- SkillHub 侧以 `hub.config.yaml` 的 `hub.root` 绝对路径定位中枢（读配置：`bridge/config.py::load_config`）。
- **交叉边界写**：SkillHub 回写会越过 SKILLHUB 仓库、直接写中枢目录；中枢反向提升会越过中枢、写 SKILLHUB 技能库。两仓各自是对方的"外部文件系统"。
- 因编辑工具被 IDE 限制在各自工作目录，跨仓库维护一律用命令行等效（读文件 + 替换/追加 + git add/commit），并同步 `INDEX.md` 登记。

## 2. 交接物与位置

| 交接物 | 存放位置 | 写方 | 读方 |
| -------- | -------- | ---- | ---- |
| 草稿卡 `*.md` | 中枢 `.sync/drafts/<platform>_draft/` **根目录** | SkillHub `writeback_card()` | 中枢 `ingest` |
| 权威区卡 | 中枢 `experience/ projects/ methodology/ ...` | 中枢 `ingest` promote | SkillHub `skill_promotion` 读源 |
| 冲突/待人工 | 中枢 `.sync/conflicts/`、`.sync/pending/` | 中枢 `decide()` review | 人工 confirm |
| 审计留痕 | SkillHub `.skillhub/usage.jsonl`；中枢 `retro/log.md` | 各自 | 各自自查/可核 |
| LLM 推理 | omniRoute Docker `127.0.0.1:20128` | 中枢 `chat()` | 中枢 `decide()` |

## 3. 草稿落位硬契约（对齐中枢 sync.ingest）

- 必须写 `drafts/<platform>_draft/` **根目录**，`candidates/` 等子目录不会被 ingest 扫描 → 放子目录 = 不会被提升。
- frontmatter 须过 `validate_card`：`type`、`tags`、`updated` 齐备。
- `type` ∈ 回写白名单 `[exp, note, project]`（见 `writeback_whitelist`）；`rule/methodology` **禁直写权威区**，只走 pending/人工 confirm。

## 4. ingest 提升判定链

```text
草稿 → 向量预过滤 candidates()（cosine ≥ 0.55）→ 命中候选?
   ├─ 无候选 → create → 直接 promoted
   └─ 有候选 → LLM decide(chat)
          create → promoted            （全新内容）
          skip   → 丢弃草稿            （判重复）
          merge/delete → 交人工终审
          网关不可用/解析失败 → review 降级进 conflicts
```

- 保守边界：`decide()` 只在确定时建议 merge/delete，最终执行由 ingest 控制，**绝不自动删改权威区**；LLM 不可用自动降级 review，不阻断主流程。

## 5. 幂等与冲突

- 同名草稿已存在且内容一致：不重复落档（覆盖为幂等）。
- ingEST 发现同名不同内容 → 进 `.sync/conflicts/`，**不覆盖**权威区，人工处理。
- `dedup_policy: literal-reset-resync`：反向提升走"字面精删→重置→重推"，避免同标题不同内容在平台产出"权威版"重复。
- 回写 writeback 应为幂等；不可回写时返回可校验状态，调用方可安全重试。

## 6. 安全与权限

- `guard_import_untrusted: true`：外部仓库（含中枢）内容不可信，**绝不自动执行/外发**，只转译为 `SKILL.md` 落技能库。
- 内部持单写者锁（中枢 `_WriteLock`），用本地 git 身份（GIT_ID，`hub@local`）提交，不污染全局 git config。
- SkillHub 回写白名单外卡型（rule/methodology）→ 抛 ValueError 拒绝（越权保护）。

## 7. 复用方法

- 上缴经验：`bridge/ingest.py::writeback_card()` 产草稿 → 中枢 `ingest` 消费/提升。
- 接入外部 LLM 网关：改中枢 `engine.config.yaml`（`gateway_url`/`default_model`）+ `provider_keys.yaml`（key）；网关默认流式时在中枢 `chat()` 显式 `"stream": false`。
- 验证成功路径：放一张权威区绝无相似的全新草稿，预期 `promoted: 1`。

## 关联

- build/… hub.config.yaml（协议出处）
- bridge/config.py、bridge/ingest.py、bridge/gate.py、bridge/attribution.py
- cards/memory-hub-omniroute-ingest-chain（整条链路全景）
