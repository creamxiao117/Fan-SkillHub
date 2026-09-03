---
name: "skillhub-reconcile-checklist"
description: "记忆中枢 → SkillHub 反向回流实操清单。Invoke when running reconcile, applying hub cards, or doing blueprints/methodology upgrade."
---

# SkillHub 反向回流 reconcile 实操 Checklist

## 场景

从记忆中枢（AgentMemoryHub）扫描卡并升级为 SkillHub 技能文件的过程。核心链路：
`中枢卡(.md frontmatter) → scan_hub_cards → reconcile --apply → skill.yaml + SKILL.md + router.yaml 登记`

## 前置检查（必做）

| # | 检查项 | 命令 | 预期 |
|---|--------|------|------|
| 1 | hub.config.yaml 存在且 hub.root 指向有效中枢 | `cat hub.config.yaml` | yaml 结构合法，root 路径可读 |
| 2 | 中枢四个卡型目录可访问 | `ls experience/ methodology/ projects/ blueprints/` | 无权限错误 |
| 3 | 工作区干净，无未提交改动 | `git status --short` | 空或只剩本次相关文件 |
| 4 | pytest 基线通过 | `python -m pytest -q` | 全绿 |

## Step 1: 扫描中枢卡（dry-run）

永远先 dry-run，确认候选池范围正确。

```bash
# 全量扫描（默认）
python -m skillhub reconcile

# 精确筛选: 只看 blueprint 卡
python -m skillhub reconcile --card-type blueprint

# 精确筛选: 只看 reference 状态（选型参考级 blueprint）
python -m skillhub reconcile --hub-status reference

# 精确筛选: 按 slug 单点/多点命中
python -m skillhub reconcile --slug "skill-governance-blueprint,skill-governance-playbook"

# 组合筛选
python -m skillhub reconcile --card-type blueprint --hub-status active,reference
```

### 筛选优先级

`--slug` > `--card-type` + `--hub-status`（三者可叠加，AND 语义）

### reconcile 候选数快速判读

| 候选数 | 含义 | 下一步 |
|--------|------|--------|
| ≤ 20 | 范围可控 | 可考虑直接 --apply |
| 20~50 | 中等范围 | 先 --slug 分批，每批 ≤ 10 张 |
| > 50 | 范围过大 | **必须用 --slug 精确指定**，绝对不能 --apply 全量 |

## Step 2: 确认中枢卡 frontmatter 质量

reconcile 依赖中枢卡 frontmatter 的以下字段：

| 字段 | 必填 | 作用 |
|------|------|------|
| `type` | ✅ | 决定卡是否被扫描（必须 ∈ TYPE_DEFAULT_SLOT） |
| `status` | ✅ | blueprint 卡不过滤；其他卡要求 active |
| `reuse_count` | ✅（blueprint） | ≥ BLUEPRINT_MIN_REUSE(1) 才升级 |
| `tags` | ⚠️ | 可为 null，已做防御；用于路由 trigger |
| `anti_trigger` | 建议 | 用作 skill.yaml forgot；缺失时 fallback GENERIC_FORGOT |

### 常见问题

| 现象 | 根因 | 处理 |
|------|------|------|
| slug 是中文长句或"提炼自" | blueprint 卡正文首行非标题 | 已在代码中修复（优先 f.stem 英文文件名） |
| `tags: null` 崩溃 | 中枢卡显式声明 null | 已在代码中修复（`fm.get("tags") or []`） |
| 43/56 blueprint 卡被过滤 | 误把 blueprint 当非 blueprint 处理 | 已在代码中修复（blueprint 不过滤 status） |
| 生成的 forgot 都是 GENERIC_FORGOT | 中枢卡缺失 anti_trigger | 正常 fallback；建议中枢补 anti_trigger |

## Step 3: 临时目录备份（高危操作前）

**每次 --apply 前必做**。防止大规模生成错误文件需要 `git clean -fd -x` 清理：

```bash
# 备份 4 张 governance blueprint 到临时位置（示例）
mkdir -Force .tmp_backup
Move-Item skills/shared/govern/skill-governance-* .tmp_backup/ -Force
Move-Item skills/shared/govern/skill-authoring-verify-* .tmp_backup/ -Force
Move-Item skills/shared/govern/skill-quality-governance-* .tmp_backup/ -Force

# 执行 --apply（范围必须由 --slug 精确限制）
python -m skillhub reconcile --slug "skill-xxx-blueprint" --apply

# 如果 apply 生成了 571 个垃圾目录需要清理:
# git checkout -- router/router.yaml   # 回退 router.yaml 垃圾条目
# git clean -fd -x                    # 清除所有未跟踪文件
# 从 .tmp_backup 恢复正确的目录
```

### --apply 灾难恢复

```bash
# 1. 回退 router.yaml（最常见：被 reconciliation 加了上千条垃圾）
git checkout -- router/router.yaml

# 2. 清除所有未跟踪文件（会把临时备份也清掉！）
git clean -fd -x

# 3. 从 .tmp_backup 恢复正确的技能目录
Move-Item .tmp_backup/xxx skills/shared/govern/xxx -Force
```

## Step 4: 执行 --apply（范围必须精确）

**严禁无筛选的 `--apply`**。每次 apply 必须满足：
1. 候选数 ≤ 10 张（通过 dry-run 确认）
2. 用 `--slug` 精确指定，或 `--card-type` + `--hub-status` 组合后候选数仍 ≤ 10

```bash
# 正确: 精确 slug，4 张 governance
python -m skillhub reconcile --slug "skill-governance-blueprint,skill-governance-playbook,skill-authoring-verify-blueprint,skill-quality-governance-blueprint" --apply

# 错误: 无筛选，会生成 175 个目录 + router.yaml 垃圾
python -m skillhub reconcile --apply
```

## Step 5: 落盘后手动调整

apply 生成的技能目录默认在 `skills/<slot>/<scope>/<slug>/`。需要手动检查：

| 检查项 | 调整 |
|--------|------|
| scope 归属 | 生成后可能在 `shared/` 而非 `shared/govern/`，需 Move-Item 移动目录 |
| skill.yaml 的 scope/directory | Move-Item 后需同步更新 skill.yaml 里的 scope 和 directory 字段 |
| router.yaml 的 scope | `_register_router` 自动登记的 scope 可能是 `""`，需手动改为正确 scope |
| forgot 质量 | 检查 anti_trigger 是否合理，不合理时手动修改 skill.yaml forgot |

### 落盘后自动同步脚本

```python
"""落盘后同步 scope/directory/router.yaml 的辅助脚本"""
import pathlib, yaml

slugs = {"slug1", "slug2"}
new_scope = "govern"
base = pathlib.Path(f"skills/shared/{new_scope}")

# 1. 移动目录（如果 apply 生成在错误位置）
for slug in slugs:
    for possible_parent in ["skills/shared", "skills/dedicated"]:
        src = pathlib.Path(possible_parent) / slug
        dst = base / slug
        if src.is_dir() and possible_parent != "skills/shared":  # 避免同位置
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            print(f"  moved: {src} → {dst}")

# 2. 更新 skill.yaml
for slug in slugs:
    sp = base / slug / "skill.yaml"
    if sp.is_file():
        sd = yaml.safe_load(sp.read_text(encoding="utf-8"))
        sd["scope"] = new_scope
        sd["directory"] = f"shared/{new_scope}/{slug}"
        sp.write_text(yaml.safe_dump(sd, allow_unicode=True, sort_keys=False), encoding="utf-8")

# 3. 更新 router.yaml
rp = pathlib.Path("router/router.yaml")
rd = yaml.safe_load(rp.read_text(encoding="utf-8"))
for s in rd.get("skills", []):
    if s["name"] in slugs:
        s["scope"] = new_scope
rp.write_text(yaml.safe_dump(rd, allow_unicode=True, sort_keys=False), encoding="utf-8")

print("完成: scope/directory/router.yaml 同步")
```

## Step 6: 验证

```bash
# pytest 全量（最关键，覆盖 router 解析/skill.yaml 格式/路由命中）
python -m pytest -q

# ruff 检查代码（如果本轮改了 skill_promotion.py / cli.py）
ruff check bridge/skill_promotion.py skillhub/cli.py

# reconcile 再次 dry-run，确认 apply 后候选池不再包含已升级卡
python -m skillhub reconcile --slug "已升级的 slug"
# 预期: action=skip, reason="技能目录已存在"
```

## Step 7: 提交

```bash
git add <精确文件列表>  # 不要 git add -A，会把 .pytest_cache 等垃圾带进去
git status --short       # 确认只有本轮相关文件
git commit -m "feat: 从记忆中枢 reconcile 升级 <slug> 为 SkillHub 技能"
```

## 中枢语义备忘

| 中枢目录 | 设计语义 | SkillHub 过滤行为 |
|----------|----------|-------------------|
| `blueprints/` | 新项目立项选型范式 | **不过滤 status**（reference 是设计预期），只要求 reuse_count ≥ 1 |
| `methodology/` | 方法论/最佳实践 | 要求 status=active |
| `experience/` | 实战经验/踩坑 | 要求 status=active |
| `projects/` | 项目级架构蓝图 | 要求 status=active |

**type 字段与目录名不一致是允许的**（blueprints/ 里可能有 type=methodology 的卡）。SkillHub 按 frontmatter.type 判断卡型，不按目录名。

## 常见坑速查

| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | reconcile dry-run 显示 175 卡 | blueprint 不过滤 status | 用 `--card-type` / `--slug` 缩小范围 |
| 2 | slug 是中文长句 | blueprint 卡正文首行非标题 | 已修复，自动用 f.stem 英文文件名 |
| 3 | tags=null 崩溃 | 中枢卡显式声明 null | 已修复，`fm.get("tags") or []` |
| 4 | router.yaml 被加了上千条垃圾条目 | `--apply` 时候选数过大 | **永远不要无筛选 --apply** |
| 5 | 生成的 forgot 都是 GENERIC_FORGOT | 中枢卡缺 anti_trigger | 正常 fallback；建议中枢补 anti_trigger |
| 6 | 落盘位置不对（在 shared/ 而非 shared/govern/） | reconcile 按 tags 推断 scope，可能不准 | 落盘后 Move-Item + 同步 skill.yaml/router.yaml |
| 7 | `git clean -fd -x` 把临时备份也清了 | 备份放在 git clean 范围 | 备份放到仓库外层目录（如 `D:/tmp/`） |
| 8 | pytest RouterError: forgot 为空 | apply 时有些卡 anti_trigger=None 且 fallback 未覆盖 | 手动补全 skill.yaml forgot 字段 |
