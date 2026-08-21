---
type: methodology
tags:
- skillhub
- memory-hub
- omniroute
- ingest
- dedup
- integration
updated: '2026-08-21'
status: active
reuse_count: 1
---

# SkillHub → 记忆中枢 → omniRoute → ingest 自动收购 整条链路

## 链路全景（实证）

```text
SkillHub 技能路由/成败反馈
   │  writeback_card()
   ▼
中枢 .sync/drafts/trae_draft/*.md （exp/note/project 白名单草稿）
   │  engine.py ingest --platform trae
   ▼
向量预过滤 candidates()（cosine ≥ 0.55，召回 topK）
   │  命中候选？
   ├─ 无候选 ──► create 直接 promoted（无相似物）
   └─ 有候选 ──► LLM 仲裁 decide(chat())
                    ├─ create → 直接 promoted
                    ├─ skip   → 丢弃草稿（判重复）
                    ├─ merge/delete → 交权威区人工终审
                    └─ LLM 网关不可用/解析失败 → 降级 review 进冲突区
   │
   ▼
权威区 experience/projects/…（status=active）+ retro/log.md 留痕
```

## 关键实证（2026-08-21 实测）

1. **模型单一事实**：中枢 `chat()` 走 OpenAI 兼容网关，配置 `gateway_url` + `default_model` + `provider_keys.default` 三处。
2. **omniRoute 接入**：本地 Docker 容器（绑 `127.0.0.1:20128`），OpenAI 兼容端点 `/v1/chat/completions`，Bearer 鉴权。
3. **关键坑（stream）**：omniRoute 默认返回 **SSE 流式**（`data:{...}`），中枢 `chat()` 解析 `resp.json()["choices"][0]` 会失败。必须显式传 `"stream": False` 才返回标准非流式 JSON。已在 `chat()` json 加 `"stream": False`。
4. **模型选择**：omniRoute 自带免费档 `oc/hy3-free` 足够 dedup 轻决策，无需本地 Ollama / 拉大模型。
5. **两种 LLM 决策均真实触发**：
   - 相似卡 `ingest-probe-omniroute` → LLM 判 `skip` → 丢弃草稿
   - 全新主题 `ingest-probe-omniroute2` → LLM 判 `create` → **直接 promoted**（`{'promoted': 1}`）
6. **成败闭环的权重参照**：贝叶斯权重以「中性=base」为参照，`weight = base × posterior / 0.5`；成功上浮、失败降权、neutral 不动权重。
7. **跨独立仓库维护**：SkillHub 的 Edit/Write 工具被 IDE 限制在当前工作目录，操作中枢（独立 git 仓库）用命令行等效完成：「读文件 + 内容替换/追加 + git add/commit」，并同步更新 `INDEX.md`。

## 配置快照（SkillHub 侧 hub.config.yaml + 中枢侧）

- 中枢根：`C:/Users/Fan-SJSS/.trae-cn/worktrees/20260817-Fan-Agent-Momory/feat-implement-plan-ZilBmv/AgentMemoryHub`
- 回写白名单 card_type: `[exp, note, project]`（rule/methodology 禁直写，走 pending/人工）
- 中枢 `engine.config.yaml`: `gateway_url: http://127.0.0.1:20128`、`default_model: oc/hy3-free`
- 中枢 `provider_keys.yaml`: `default: <omniRoute key>`
- 中枢 `chat()`: json 含 `"stream": False`

## 复用方法

- **新增一条经验回写**：`bridge/ingest.py writeback_card()` → 草稿落 `drafts/trae_draft/` → 中枢 `ingest` 自动判定。
- **接外部网关**：三处配置即可，无需改代码（若网关默认流式，需在 `chat()` 补 `stream: false`）。
- **真机验证成功路径**：放一张权威区绝无相似的全新主题草稿，预期 `promoted: 1`，`reuse_count` 随之更新。

## 关联

- build/… hub.config.yaml（SkillHub 侧出处）
- bridge/ingest.py、bridge/config.py、bridge/attribution.py、bridge/gate.py
- router/tools/router_audit.py（贝叶斯成败反馈）
- 中枢卡：experience/ingest-probe-omniroute2、projects/improve-ingest-dedup-threshold
