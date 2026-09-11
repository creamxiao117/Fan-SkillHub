---
name: hub-schema-drift-remediation
description: "Use when 中枢卡片 schema 漂移、校验绕过或需加提交前门禁。"
---

# 中枢卡片 schema 漂移 · 排查 → 收口 → 门禁 → 回写

排查 → 收口 → 门禁安装 → 回写闭环（含本地模型优先级 / 检索 embedding）。

## 何时用

- 中枢出现/怀疑出现卡片 frontmatter 不合规（type / status / updated）
- 巡检报「无效卡片 / 非权威区漂移 / 幽灵登记 / INDEX 未登记 / 描述越界」
- 要给「**直接写入路径**」加校验关口（Agent 直写目录绕过 ingest）
- 要调整中枢的本地模型优先级 / 检索 embedding 后端

**不适用**：单纯查询中枢内容（→ `agent-memory-hub-ops`）；新平台 onboarding。

## 0. 铁律（先记 5 条）

1. **中枢是独立 git 仓库**（`AgentMemoryHub/.git`），与父仓库分开提交，别互相卷入。
2. `experience/ notes/ retro/` 是**非权威区**：不参与孤儿/陈旧判定，**但参与检索**（`retrieve._ACTIVE_DIRS`）。
3. 改文件前先 `git status --short`；≥3 modified = **有他人现场** → 只 `git add <自己文件>`；禁止 `git add -A`、禁止 `ruff format <目录>`（整目录会批改他人未提交文件）。
4. 配置**单源**是 `AgentMemoryHub/system/config.yaml`；`hub-engine/config/engine.config.yaml` 只是回退。改配置前先实证真正读到什么（见 §5）。
5. `ingest` 内部 `git add -A` 提交 —— 手工直写的文件会被卷进下一次 `sync: ingest …` 提交，**归因被洗掉**，事后难追溯。

## 1. 5 分钟排查配方

```bash
cd <worktree>
HUB=AgentMemoryHub

# a) 全目录 schema 扫描 —— lint 只扫 5 权威区，必须自己扫全
FILES=$(ls $HUB/{rules,blueprints,methodology,longterm,projects,experience,notes}/*.md 2>/dev/null | sed "s|$HUB/||")
python hub-engine/scripts/check_card_frontmatter.py --root $HUB $FILES

# b) 引擎两把尺子
python hub-engine/engine.py lint  --root $HUB   # orphans/ghosts/stale/invalid/schema_drift
python hub-engine/engine.py audit --root $HUB   # INDEX 登记 + CJK slug + 描述长度

# c) 幂等修复器（dry-run 默认）
python hub-engine/scripts/fix_card_schema_drift.py --root $HUB
python hub-engine/scripts/fix_index_registry.py --root $HUB

# d) 该卡到底进没进检索（解析失败的卡查不到）
python -c "import sqlite3;c=sqlite3.connect('$HUB/.sync/vector.db');print(c.execute(\"select path,type,length(embedding) from docs where path like '%关键词%'\").fetchall())"
```

## 2. schema 判定口径

- 合法 `type`：`rule | exp | note | project | retro | methodology | longterm | blueprint`（**`experience` 非法**，历史最高频漂移值）
- 合法 `status`：`active | archived | candidate | reference`（`draft` 非法）
- `updated` 必填；补值时**优先取卡内 `created`**（填「今天」会让 180 天 stale 判定失真）
- frontmatter **必须在文件起始处**：`# @version` 之类头注释放 `---` 之前 → 解析失败 → 该卡**不进向量库**（静默丢失检索）
- 目录↔type 不一致：**只警告不阻断**（`experience/` 历史混装 rule/methodology/blueprint）

## 3. 根因三分类（决定收口动作）

| 现象 | 根因 | 收口 |
|---|---|---|
| 非权威区静默不合规 | 该区从未被 lint 扫描 | lint 加独立 `schema_drift` 维度（只跑 `validate_card`，不混孤儿/陈旧） |
| 卡在，但向量库没有 | frontmatter 解析失败 | 补/挪 frontmatter + `build-vectors` |
| INDEX 报未登记 / 幽灵 | INDEX 行 slug ≠ 文件名 stem（用了 `title`、去了日期前缀）；裸行无描述；slug 含中文（旧正则不认） | `fix_index_registry.py` 幽灵自动纠偏；裸行/漏登**只报告不臆改** |

## 4. 门禁安装（提交前拦截）

```bash
cp hub-engine/scripts/pre-commit-hub-cards $HUB/.git/hooks/pre-commit
chmod +x $HUB/.git/hooks/pre-commit
```

- 拦的是**提交**，不是**写入**（写文件没有钩子）；这是唯一能覆盖「Agent 直写目录」的拦截点。
- 校验三步：必须以 `---` 开头 → 可解析 → `validate_card`（type/status/updated）。
- 安装后**必测三路径**：坏 type → exit 1；游离前置行 → exit 1；合规卡 → exit 0。
- 对**所有提交者**生效（含其他平台 ingest 提交）：对方有坏卡时 ingest 会报错中断，属设计意图（fail loudly）。
- 人工通道：`git commit --no-verify`。

## 5. 本地模型优先级（检索 / LLM）

调用链：`local_chat`（LM Studio 1234）→ `local_chat_fallbacks`（可空）→ `gateway`（OmniRoute 20128，**最后兜底**）。

检索 embedding：LM Studio `http://127.0.0.1:1234/v1/embeddings`，索引模型 `text-embedding-bge-small-zh-v1.5`（**512 维**）。

**关键约束：两个 bge 模型维度不同**（`bge-small-zh-v1.5`=512 / `bge-m3`=1024）→ **禁止做同一向量库的降级链**，混用会让检索失真；换模型必须**全量重建** `build-vectors`。

改配置后必验：

```bash
python -c "import sys;sys.path.insert(0,'hub-engine');from tools.semsearch import _http_cfg,_embed_via_http;c=_http_cfg();print(c[0],c[1]);print('dim=',len(_embed_via_http('测试')))"
python -c "import sys;sys.path.insert(0,'hub-engine');from common.config import load_engine_config;from engine import _local_endpoint_chain;c=load_engine_config();print('gateway',c.get('gateway_url'));print('chain',[u for u,_m,_t in _local_endpoint_chain(c)])"
```

dim 对不上 → 立即停手，别跑 `build-vectors`（会污染向量库）。

## 6. 回写闭环

draft 落 `.sync/drafts/<platform>_draft/` **根目录**（子目录不被扫）→ `engine.py ingest --platform <p>` → `build-vectors` → INDEX（`post_ingest_hook` 自动登记）→ `git commit`。

- 规则类走 `.sync/pending/` 待人工 confirm。
- LLM 网关不可用时 dedup 降级 → 草稿进 `.sync/conflicts/`（`action=review`、`confidence=0.0`、`reason=LLM 输出无法解析`）——**这不是内容判决**，别当重复丢弃。
- **能折进既有卡就别新建卡**（避免规则增殖）：折进 + 升 `version` + 补 `关联`。

## 7. 坑清单（均已实测）

1. `Path.read_text()` 用通用换行会把 CRLF 折成 LF → 要保留行尾必须 `open(..., newline="")`。
2. `ruff format <目录>` 会批改他人未提交文件 → 只对显式文件清单执行。
3. 目标文件多为 CRLF：写替换脚本时模式要**同时试 LF 与 CRLF** 两种变体。
4. `LLMHealthChecker.get_instance(base)` 曾忽略 `base_url`（全局单例）→ 多端点健康判定串味；须按 base_url 分键。
5. 健康探测曾写死「含 1234 才探 `/v1/models`，否则探 `/api/tags`（Ollama 遗留）」→ 非 LM Studio 的 OpenAI 兼容端点恒判不可用。
6. 配置曾「声明单源却用嵌套 schema」：`system/config.yaml` 用 `gateway:` 子键、引擎读扁平 `gateway_url` → 真配置从未生效，静默吃硬编码默认。改动后用 §5 命令实证。
7. 同文件可能有多处硬编码读旧配置（如 `semsearch._http_cfg()` 曾直读 `hub-engine/config/engine.config.yaml`）→ 单源改造要 `grep -rn 'engine.config.yaml'` 全扫。
8. INDEX 解析正则曾不认 CJK slug → 中文 slug 卡恒被误判「未登记」。
9. 描述长度上限**按分区差异化**（blueprints 800 / 其他 250）：蓝图描述承载路径/判级/状态，砍到 250 丢信息。
10. Windows 上**不要用 `rm -rf`**（触发危险命令拦截并超时）→ 用 Python `Path.unlink()` / `rmdir()`。
11. 脚本报「已改过」可能是判据写错（如拿新模式首行去匹配旧文本）→ 复核真实文件内容，别信布尔。

## 8. 验收清单（缺一不可）

```bash
python hub-engine/engine.py lint  --root $HUB    # 全 0（含 schema_drift）
python hub-engine/engine.py audit --root $HUB    # ✅ 健康
python -m pytest hub-engine/tests -q              # 全 pass
python hub-engine/engine.py build-vectors --root $HUB
git -C $HUB status --short                         # 只剩他人现场
```

同时确认：`hub lint` 输出里有「非权威区漂移」行；门禁三路径实测过；`_http_cfg()` 维度与向量库匹配。

## 关联

`agent-memory-hub-ops` · `memory-hub-card-promotion` · `hub-inventory-baseline-audit` · `single-fact-source-config-pattern` · `activedirs-five-type-discipline` · 规则 `agent-code-discipline-iron-rule` R6
