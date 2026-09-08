# SkillHub 工具 → 技能注册标准流程

> 建立：2026-09-07 ｜ Hermes
> 适用：把一个新工具（CLI/系统包）注册为 SkillHub 技能的标准操作流程
> 前提：工具已安装 / 安装方式已知

## 触发条件

当需要把一个新工具纳入 SkillHub 路由体系时触发，例：
- Fan 要求「安装 XXX 工具并在 Hermes 使用」
- 调研发现某工具有多 Agent 场景复用价值
- 从 GitHub/star-distill 发现值得固化的工具

## 标准流程（5 步）

### Step 1：工具安装验证

**目标**：确认工具在当前平台可用，记录跨平台安装方式。

| 平台 | 安装命令 | 验证 |
|---|---|---|
| Windows | `choco install <pkg>` 或 `pip install <pkg>` | `<cmd> --version` |
| Linux | `apt install <pkg>` / `brew install <pkg>` | 同上 |
| Python | `pip install <pkg>` | `python -c "import <pkg>; print(<pkg>.__version__)"` |

- 记录：版本号、安装路径（`which` / `where`）
- 如工具不存在且无包管理器 → 记录「需手动下载」并提供 URL

### Step 2：创建技能骨架

```bash
python -m skillhub new <slug> --slot shared [--scope <domain>]
```

或手动创建目录：
```
skills/shared/<domain>/<slug>/
  SKILL.md        # 技能本体
  skill.yaml      # 元数据
```

SKILL.md 必须包含：
- **触发词**（trigger）：用户会说哪些话激活这个技能
- **负路由词**（forgot）：哪些场景不应该激活
- **使用限制**：平台差异 / 依赖要求 / 注意事项
- **安装前置**：（本卡 Step1 的安装命令）
- **典型场景示例**：2~3 个具体用法

skill.yaml 字段：
- `name`：与目录名一致
- `slot`：shared 或 dedicated
- `invoke`：user（人触发）或 model（Agent 可自动调用）
- `status`：新建时 `reference`

### Step 3：注册到 router.yaml

**方式 A（推荐）**：用 `reconcile --apply` 从中枢 blueprint/methodology 卡生成（适用于中枢已有对应卡的情况）

**方式 B（手动）**：直接在 `router/router.yaml` 末尾追加：

```yaml
- name: <slug>
  slot: shared
  invoke: user
  description_model: <给模型读的触发描述，限 1~2 句>
  description_human: <给人读的摘要>
  trigger:
  - <触发词1>
  - <触发词2>
  forgot:
  - <不应激活的场景1>
  - <不应激活的场景2>
  weight: 1.0
  status: active
```

**注意**：编辑 router.yaml 前先 `git pull`，多人协作场景防冲突。

### Step 4：路由命中测试

```bash
python -m skillhub route "<典型触发词>"
python -m skillhub route "<负向测试词>"  # 应不命中
```

确认：
- ✅ 技能出现在命中列表首位（或预期位置）
- ✅ 负向词不触发

### Step 5：Git 提交

```bash
git add skills/shared/<domain>/<slug>/ router/router.yaml
git commit -m "feat(<domain>): 新增 <slug> 技能（<一句话功能>）"
git push origin master
```

**commit 信息规范**：`feat|fix|chore|docs(<domain>): <slug> <动作>`

---

## 防坑 checklist

| # | 检查项 | 通过标准 |
|---|---|---|
| 1 | 工具已安装且 `--version` 正常 | ✅ |
| 2 | router.yaml 中 `name` 与 skill 目录名完全一致 | ✅ |
| 3 | `trigger` 至少 2 个短词（避免整句） | ✅ |
| 4 | `forgot` 非空（防语义过命中） | ✅ |
| 5 | `description_model` ≤ 2 句（控制路由表膨胀） | ✅ |
| 6 | 路由测试命中 / 负向测试不命中 | ✅ |
| 7 | git push 成功（先 pull 防冲突） | ✅ |

---

## 晋级后续（与技能生命周期衔接）

新技能默认 `status=reference`：
- 真实使用 3 次 `skillhub record <slug> --success` → `reuse_count≥3`
- 补充 `t1_record`（真机验证记录）
- `skillhub promote-auto` 或 `skillhub promote <slug> --status active` → 正式 active

---

## 关联

- cards/card-promotion-workflow.md（技能→中枢反馈链路）
- cards/memory-hub-omniroute-ingest-chain.md（中枢→SkillHub 回流全景）
- hub config: `hub.config.yaml`
