# SkillHub 工具 → 技能注册标准流程

> 适用：当需要把一个新工具纳入 SkillHub 路由体系时触发
> 版本：V1.0 / 2026-09-07 / Hermes

## 触发条件

- Fan 要求「安装 XXX 工具并在 Hermes 使用」
- 调研发现某工具有多 Agent 场景复用价值
- 从 GitHub/star-distill 发现值得固化的工具

## 标准流程（5 步）

### Step 1 工具安装验证

| 平台 | 安装命令 | 验证 |
|---|---|---|
| Windows | `choco install <pkg>` 或 `pip install <pkg>` | `<cmd> --version` |
| Linux | `apt install <pkg>` / `brew install <pkg>` | 同上 |
| Python | `pip install <pkg>` | `python -c "import pkg; print(pkg.__version__)"` |

**注意**：`pip search` 已废弃（PyPI XMLRPC 2023 停用），查包用 `pip index versions <pkg>` 或直接 `pip install <pkg>` 试装。

### Step 2 技能骨架创建

```bash
# 方式A：用 skillhub new（自动生成骨架）
python -m skillhub new <slug> --slot shared --scope <domain>

# 方式B：手动创建
mkdir -p skills/shared/<domain>/<slug>/
# 手动写 SKILL.md + skill.yaml
```

### Step 3 router.yaml 注册（先 pull！）

```bash
# 必须先 pull，避免与 CI reconcile 冲突
git pull origin master

# 用 Python 安全追加（防 YAML 格式破坏）
python -c "
import yaml
with open('router/router.yaml') as f:
    data = yaml.safe_load(f)
# ...追加技能记录...
with open('router/router.yaml', 'w') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
"
```

**冲突处理原则**：与 CI reconcile 冲突时，**保留双方内容**（CI 新增技能 + 你新增技能），绝不覆盖对方部分。

### Step 4 路由命中测试

```bash
python -m skillhub route "<触发词>"
python -m skillhub route "<负向词>"  # 确认不误命中
```

触发词要求：≥2 个短词，不用整句，短词对自然语言更鲁棒。

### Step 5 Git push

```bash
git add skills/ router/router.yaml
git commit -m "feat(<domain>): <slug> <一句话功能>"
git push origin master
```

## SkillHub submodule 处理（check-code-v1 等）

某些技能是独立 Git 仓库（submodule）。更新这类技能时：

1. **先 push submodule 内部**：`git add . && git commit && git push origin <branch>`（独立仓库自己的远程）
2. **再更新父仓库 submodule 指针**：`git add skills/shared/.../<name>`（只更新 commit hash）
3. **最后 push 父仓库**

顺序不可颠倒。

## record 补数晋级链路

技能从 `reference` → `active` 需要两步：

```bash
# 1. 补 record（需 3 次成功）
python -m skillhub record <slug> --success --root .

# 2. 填写 t1_record（手动或真实使用）
# skill.yaml 中 verification.t1_record 填写真机验证结果

# 3. 自动晋级（下次 cron promote-auto）
python -m skillhub promote-auto
```

注意：`skillhub record` 在 submodule 内有路径 bug，需加 `--root .` 指定工作目录根。

## 坑（防踩）

| 坑 | 解法 |
|---|---|
| `pip search` 报错 `XMLRPC request failed` | PyPI 已废弃，改用 `pip index versions` 或直接安装试跑 |
| router.yaml 合并冲突覆盖 CI 新增技能 | 先 pull；冲突时两方内容都保留 |
| record 写到 `.skillhub/.skillhub/` 嵌套目录 | 用 `--root .` 参数指定根目录 |
| submodule 技能只 push 父仓库 | 先 push submodule 内部，再 push 父仓库 |
| 触发词用整句导致路由失配 | 用短词（2+），整句在真实 query 中词序一变就失效 |
| promote-auto 全跳过但 reuse_count 已够 | 检查 `t1_record` 是否为空，两项需同时满足 |
