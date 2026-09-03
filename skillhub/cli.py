"""SkillHub 命令行入口: route / record / weight / sync-verification / promote / audit / new。

复用 router(路由命中排序)与 router_audit(贝叶斯成败反馈) 核心,
把"防上下文膨胀"的路由命中与权重排序暴露为可调用命令, 供自定义脚本与外部
agent 平台接入。审计事件(record 成败)持久化到 <root>/.skillhub/usage.jsonl。

用法:
    python -m skillhub route "<query>" [--router PATH] [--root PATH]
    python -m skillhub record <name> --success|--failure|--neutral [--root PATH]
    python -m skillhub weight <name> [--root PATH] [--base 1.0]
    python -m skillhub sync-verification [--skill-root PATH] [--root PATH]
    python -m skillhub promote <name> [--status active|reference] [--skill-root PATH]
    python -m skillhub audit [--skill-root PATH]
    python -m skillhub new <name> [--slot shared] [--scope <domain>]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = PROJECT_ROOT / "skills"

# authoring 检查清单（与 skill_promotion.AUTHORING_CHECKLIST 对齐）
_AUTHORING_SECTIONS = [
    (
        "Agentic Loop 设计",
        [
            "scope 明确可改/只读边界",
            "validation 命令必须在提交前通过",
            "每 loop 限 1 个 open PR（PR bounding）",
            "agent-memory 携带两轮间稳定反馈",
            "skill/prompt/memory 单一来源, 不重复",
        ],
    ),
    (
        "指令文件结构",
        [
            "基础上下文裸放, 条件规则用 <important if> 包裹",
            "触发词窄而具体, 禁止宽泛条件",
            "Less is more: 删 linter 管辖/代码片段/含糊指令",
            "保留所有命令表",
        ],
    ),
    (
        "控制论闭环",
        [
            "五要素完整: SetPoint→Sensor→Controller→Actuator→Disturbance",
            "传感器可稳定测量客观属性",
            "组件先本地跑通再接 CI",
            "人留在 loop 上(/iterate 评论反馈)",
        ],
    ),
    (
        "视图选择",
        [
            "按内容选最小视图: 逻辑→伪代码/控制流→调用树/UI→组件树",
            "视觉紧贴支撑短文本",
            "只保留回答问题所需信息",
        ],
    ),
]


def _default_router() -> Path:
    return PROJECT_ROOT / "router" / "router.yaml"


def _default_root() -> Path:
    # 默认审计根: 项目本地 .skillhub(记录成败事件), 可 --root 覆盖
    return PROJECT_ROOT / ".skillhub"


def _default_hub_root() -> Path:
    """从 hub.config.yaml 读中枢根; 不可用则返回空 Path(调用方处理)。"""
    cfg = PROJECT_ROOT / "hub.config.yaml"
    if cfg.is_file():
        try:
            data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
            root = (data.get("hub") or {}).get("root", "")
            if root:
                return Path(root)
        except yaml.YAMLError:
            pass
    return Path()


def _cmd_route(args: argparse.Namespace) -> None:
    from router.tools.router import route

    hits = route(args.router, args.query, root=args.root)
    if not hits:
        print("(无命中)")
        return
    for h in hits:
        print(f"- {h['name']}  slot={h['slot']}  weight={h['weight']:.3f}")


def _cmd_record(args: argparse.Namespace) -> None:
    from router.tools.router_audit import record_outcome

    success = {"success": True, "failure": False, "neutral": None}[args.state]
    p = record_outcome(args.root, args.name, success=success)
    print(f"recorded -> {p}")


def _cmd_weight(args: argparse.Namespace) -> None:
    from router.tools.router_audit import effective_weight

    w = effective_weight(args.root, args.name, base_weight=args.base)
    print(f"{args.name}: effective_weight={w:.3f}")


# --- sync-verification ---
def _cmd_sync_verification(args: argparse.Namespace) -> None:
    """双源同步 verification: usage.jsonl 优先, 回落中枢卡 frontmatter reuse_count.

    数据源优先级:
      1. usage.jsonl (真实调用记录, 需 skill 在 SKILL.md 里调用 skillhub record)
      2. 中枢卡 frontmatter reuse_count (中枢侧自己维护的复用次数, 稳定可用)

    两个数据源都为空时 → 不动 skill.yaml (保持 reuse_count 原值)。
    """
    from router.tools.router_audit import load_outcomes

    # 读中枢 cache (如果有) 或实时扫描中枢拿每张卡的 reuse_count
    hub_reuse: dict[str, int] = {}
    hub_path = Path(getattr(args, "hub_root", "") or "" if hasattr(args, "hub_root") else "")
    if hub_path and hub_path.is_dir():
        try:
            from bridge.skill_promotion import scan_hub_cards
            cards = scan_hub_cards(hub_path)
            for c in cards:
                hub_reuse[c.slug] = c.reuse_count
        except Exception as exc:  # noqa: BLE001 — 中枢读失败不阻塞主流程
            print(f"  (hub scan skipped: {exc})")

    outcomes = load_outcomes(args.root)
    updated = 0
    source_stats = {"usage": 0, "hub": 0, "skip": 0}
    for skill_yaml in Path(args.skill_root).rglob("skill.yaml"):
        data = yaml.safe_load(skill_yaml.read_text(encoding="utf-8")) or {}
        name = data.get("name", "")
        if not name:
            source_stats["skip"] += 1
            continue

        # 双源策略
        usage_count = outcomes.get(name, {}).get("success", 0) + outcomes.get(name, {}).get("failure", 0)
        hub_count = hub_reuse.get(name, 0)

        if usage_count > 0:
            final_count = usage_count
            source = "usage"
        elif hub_count > 0:
            final_count = hub_count
            source = "hub"
        else:
            source_stats["skip"] += 1
            continue

        verification = data.setdefault("verification", {})
        verification["reuse_count"] = final_count
        verification["last_verified"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_yaml.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        updated += 1
        source_stats[source] += 1
        print(f"  [{source:4s}] {name}: reuse_count={final_count}")
    print(f"\nsync-verification: {updated} updated  (usage={source_stats['usage']}, hub={source_stats['hub']}, skip={source_stats['skip']})")


# --- promote ---
def _cmd_promote(args: argparse.Namespace) -> None:
    """手动将技能验证状态从 reference → active (或反向)。"""
    target = args.status
    for skill_yaml in Path(args.skill_root).rglob("skill.yaml"):
        data = yaml.safe_load(skill_yaml.read_text(encoding="utf-8"))
        if data.get("name") != args.name:
            continue
        # 顶层 status + verification.status 同步更新
        data["status"] = target
        verification = data.setdefault("verification", {})
        verification["status"] = target
        if target == "active" and not verification.get("t1_record"):
            verification["t1_record"] = "(手动 promote) 真实试用通过"
        verification["last_verified"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_yaml.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        print(f"promote {args.name} → {target}")
        return
    print(f"promote: skill '{args.name}' not found under {args.skill_root}")
    sys.exit(1)


# --- audit ---
def _cmd_audit(args: argparse.Namespace) -> None:
    """扫描所有 SKILL.md, 检查 authoring 检查清单覆盖率。"""
    skill_root = Path(args.skill_root)
    issues = []
    total = 0
    covered_total = 0
    for skill_md in sorted(skill_root.rglob("SKILL.md")):
        total += 1
        text = skill_md.read_text(encoding="utf-8")
        missing_sections = []
        for label, items in _AUTHORING_SECTIONS:
            if f"**{label}**" not in text and label not in text:
                missing_sections.append(label)
        if missing_sections:
            rel = str(skill_md.relative_to(skill_root))
            issues.append(f"  [{rel}] 缺: {', '.join(missing_sections)}")
        else:
            covered_total += 1
    print(f"audit: {covered_total}/{total} skills 有完整 authoring 检查清单")
    if issues:
        print("\n缺失清单:")
        for line in issues:
            print(line)
    else:
        print("所有技能均通过 authoring 检查清单")


# --- new ---
def _cmd_new(args: argparse.Namespace) -> None:
    """创建新技能: 生成 skill.yaml + SKILL.md 骨架 + authoring 检查清单。"""
    slot = args.slot
    scope = args.scope or ""
    dest = SKILLS_ROOT / slot
    if scope:
        dest = dest / scope
    dest = dest / args.name
    dest.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 写 skill.yaml
    skill_yaml = {
        "name": args.name,
        "version": "0.1.0",
        "slot": slot,
        "scope": scope or "",
        "status": "reference",
        "reuse_count": 0,
        "updated": today,
        "evidence": {"gate": "required", "grade": "pending"},
        "verification": {
            "status": "reference",
            "t1_record": "",
            "reuse_count": 0,
            "last_verified": "",
        },
        "invoke": "user",
        "description_model": args.name,
        "description_human": args.name,
        "trigger": [args.name],
        "forgot": ["不自动执行外部脚本", "push 到远程"],
        "instructions": "SKILL.md",
        "references": [],
    }
    (dest / "skill.yaml").write_text(
        yaml.safe_dump(skill_yaml, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    # 写 SKILL.md (含 authoring 检查清单)
    authoring_lines = []
    for label, items in _AUTHORING_SECTIONS:
        authoring_lines.append(f"**{label}**:")
        authoring_lines.extend(f"  - {i}" for i in items)
    md = f"""---
name: "{args.name}"
description: "{args.name}(新建技能, 待填写)"
---

# {args.name}

<!-- 填写技能描述: 本技能做什么, 什么时候用 -->

## 触发

- 待填写

## 核心边界（先读, 违反即停）

- 待填写不适用情形

## Authoring 检查清单（撰写/维护本技能时对照）

{chr(10).join(authoring_lines)}

## 关联

- 新建技能: {args.name}
"""
    (dest / "SKILL.md").write_text(md, encoding="utf-8")
    print(f"new: skill '{args.name}' created at {dest}")
    print("下一步: 编辑 SKILL.md 填写技能描述, 编辑 skill.yaml 添加 trigger/forgot")


def _cmd_reconcile(args: argparse.Namespace) -> None:
    from bridge.skill_promotion import reconcile

    hub = args.hub_root or _default_hub_root()
    if not hub or not Path(hub).is_dir():
        print(f"[ERROR] 中枢根无效: {hub}")
        print("  检查 hub.config.yaml 中 hub.root 配置, 或传 --hub-root")
        raise SystemExit(1)

    actions = reconcile(
        hub,
        args.skill_root,
        apply=args.apply,
        router_path=args.router,
        card_type_filter=getattr(args, "card_type", None),
        hub_status_filter=getattr(args, "hub_status", None),
        slug_filter=getattr(args, "slug", None),
        scope_filter=getattr(args, "scope", None),
        batch_size=getattr(args, "batch_size", 0) or 0,
        batch_index=getattr(args, "batch_index", 0) or 0,
        save_path=(getattr(args, "save_candidates", "") or None),
        load_path=(getattr(args, "load_candidates", "") or None),
    )

    if not actions:
        print("reconcile: 中枢无卡通过过滤, 无待升级候选")
        return

    # 按 action 类型分组统计
    from collections import Counter

    counts = Counter(a["action"] for a in actions)
    total = len(actions)
    verb = "APPLY" if args.apply else "PROPOSE"

    print(f"reconcile [{verb}]: {total} 卡, 分布: {dict(counts)}")
    print()
    for a in actions:
        status_icon = {"propose": "📋", "apply": "✅", "skip": "⏭"}.get(
            a["action"], "?"
        )
        extra = f" ({a['reason']})" if a.get("reason") else ""
        print(
            f"  {status_icon} [{a.get('card_type', '?')}] {a['slug']}"
            f" → {a.get('target', '')}{extra}"
        )

    if not args.apply:
        print()
        print("dry-run 模式(默认); 加 --apply 才真正写盘并登记 router.yaml")




# --- migrate ---
def _cmd_migrate(args: argparse.Namespace) -> None:
    """回填旧技能缺失的 verification / __reconcile_batch__ / slot 等新字段。

    不改变业务字段 (trigger/forgot/description), 只补系统元数据。
    --dry-run 时只打印 diff 不写文件。
    """
    skill_root = Path(args.skill_root)
    hub_cards: dict[str, dict] = {}
    hub_path = getattr(args, "hub_root", "") or ""
    if hub_path and Path(hub_path).is_dir():
        try:
            from bridge.skill_promotion import scan_hub_cards
            for c in scan_hub_cards(hub_path):
                hub_cards[c.slug] = c.to_dict()
        except Exception as exc:  # noqa: BLE001
            print(f"  (hub scan skipped: {exc})")

    updated = 0
    for skill_yaml in sorted(skill_root.rglob("skill.yaml")):
        rel = str(skill_yaml.relative_to(skill_root.parent))
        data = yaml.safe_load(skill_yaml.read_text(encoding="utf-8")) or {}
        changed = False

        # 1. verification (必须有)
        if "verification" not in data:
            card = hub_cards.get(data.get("name", ""), {})
            data["verification"] = {
                "status": "reference",
                "t1_record": "",
                "reuse_count": card.get("reuse_count", 0),
                "last_verified": "",
            }
            changed = True
            print(f"  [+verification] {rel}")

        # 2. slot 补全 (旧技能可能没有显式 slot)
        if not data.get("slot"):
            parts = skill_yaml.relative_to(skill_root).parts
            # skills/<slot>/<scope?>/<name>/skill.yaml
            if len(parts) >= 2:
                data["slot"] = parts[0]
                changed = True
                print(f"  [+slot={data['slot']}] {rel}")

        # 3. __reconcile_batch__: 如果 references 指向中枢, 标记来源
        if "__reconcile_batch__" not in data and data.get("references"):
            refs = data["references"]
            hub_refs = [r for r in refs if "AgentMemoryHub" in str(r) or hub_path in str(r)]
            if hub_refs:
                data["__reconcile_batch__"] = {
                    "migrated": True,
                    "from_references": hub_refs[:2],
                    "migrated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }
                changed = True
                print(f"  [+__reconcile_batch__] {rel}")

        if changed:
            if args.dry_run:
                print("    (dry-run, 不写盘)")
            else:
                skill_yaml.write_text(
                    yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                    encoding="utf-8",
                )
                updated += 1

    print(f"\nmigrate: {updated} skills updated  (dry_run={args.dry_run})")


# --- verify ---
def _cmd_verify(args: argparse.Namespace) -> None:
    """对一个技能跑最小 T1 验证: 检查 SKILL.md 存在、skill.yaml 解析成功、路由可命中。

    --demo 模式: 打印该技能的 trigger/forgot 清单, 供人工 review 后手动跑一次真实场景。
    验证结果回写 skill.yaml verification.t1_record。
    """
    skill_root = Path(args.skill_root)
    skill_yaml = next(skill_root.rglob(f"{args.name}/skill.yaml"), None)
    if not skill_yaml:
        print(f"verify: skill '{args.name}' not found")
        sys.exit(1)

    data = yaml.safe_load(skill_yaml.read_text(encoding="utf-8"))
    md = skill_yaml.parent / "SKILL.md"
    checks = {}

    # Check 1: SKILL.md 存在
    checks["skill_md_exists"] = md.is_file()
    # Check 2: yaml 可解析 (上面已通过)
    checks["yaml_parseable"] = True
    # Check 3: trigger 非空
    checks["trigger_nonempty"] = bool(data.get("trigger"))
    # Check 4: forgot 非空
    checks["forgot_nonempty"] = bool(data.get("forgot"))

    all_pass = all(checks.values())
    print(f"verify {args.name}:")
    for k, v in checks.items():
        mark = "✅" if v else "❌"
        print(f"  {mark} {k}")

    if args.demo:
        print("\n—— 最小 T1 Demo 清单 ——")
        print(f"  trigger: {data.get('trigger', [])}")
        print(f"  forgot:  {data.get('forgot', [])}")
        print(f"  slot:    {data.get('slot')}/{data.get('scope', '')}")
        print("\n  请用真实场景跑一次, 然后执行:")
        print(f"    skillhub promote {args.name} --status active --t1 '真实试用通过 1 次'")

    # 回写 t1_record (如果检查全过且没手动覆盖)
    verification = data.setdefault("verification", {})
    new_record = args.t1_record or ("静态检查全部通过" if all_pass else "静态检查未全过")
    if verification.get("t1_record") != new_record:
        verification["t1_record"] = new_record
        verification["last_verified"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not args.dry_run:
            skill_yaml.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

    sys.exit(0 if all_pass else 1)


# --- promote (扩展 --auto) ---
def _cmd_promote_auto(args: argparse.Namespace) -> None:
    """自动晋级: verification.reuse_count ≥ 阈值 且 t1_record 非空 → reference→active。

    安全网: 复用 reuse_count≥3 + t1_record 已填 (不能是 "手动 promote" 那行)。
    """
    skill_root = Path(args.skill_root)
    threshold = args.threshold or 3
    promoted = 0
    skipped = 0
    for skill_yaml in sorted(skill_root.rglob("skill.yaml")):
        data = yaml.safe_load(skill_yaml.read_text(encoding="utf-8")) or {}
        name = data.get("name", "")
        v = data.get("verification", {}) or {}
        status = v.get("status", data.get("status", "reference"))
        rc = v.get("reuse_count", 0)
        t1 = v.get("t1_record", "")

        if status != "reference":
            skipped += 1
            continue
        if rc < threshold:
            print(f"  skip {name}: reuse_count={rc} < {threshold}")
            skipped += 1
            continue
        if not t1 or "手动 promote" in t1 or "静态检查" in t1:
            print(f"  skip {name}: t1_record 无真实试用 ({t1[:30] if t1 else '(空)'})")
            skipped += 1
            continue

        # 晋级
        data["status"] = "active"
        v["status"] = "active"
        v["last_verified"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not args.dry_run:
            skill_yaml.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        print(f"  ✨ promote {name}: reuse_count={rc}, t1={t1[:40]}")
        promoted += 1

    print(f"\npromote --auto: {promoted} promoted, {skipped} skipped  (threshold={threshold}, dry_run={args.dry_run})")


# --- push-to-hub ---
def _cmd_push_to_hub(args: argparse.Namespace) -> None:
    """SkillHub → 中枢 反向同步: 把 SkillHub 里 promote 到 active 的技能回写到中枢卡。

    更新中枢卡 frontmatter 的:
      - status: 强制 active (如果 SkillHub 里该技能是 active)
      - reuse_count: max(中枢现有, SkillHub verification.reuse_count)
      - updated: 今天 YYYY-MM-DD
      - anti_trigger: SkillHub 的 forgot 列表合并 (去重)

    --dry-run 预览, 不污染中枢。
    """
    skill_root = Path(args.skill_root)
    hub_root = Path(args.hub_root)
    if not hub_root.is_dir():
        print(f"push-to-hub: hub_root {hub_root} 不存在 -> 跳过")
        sys.exit(0)

    updated = 0
    skipped = 0
    for skill_yaml in sorted(skill_root.rglob("skill.yaml")):
        data = yaml.safe_load(skill_yaml.read_text(encoding="utf-8")) or {}
        name = data.get("name", "")
        status = data.get("status", "")
        v = data.get("verification", {}) or {}
        v_status = v.get("status", "")
        if status != "active" and v_status != "active":
            skipped += 1
            continue

        hub_path = _find_hub_card(hub_root, data.get("references", []), name)
        if not hub_path:
            print(f"  [warn] {name}: 找不到对应中枢卡 -> 跳过")
            skipped += 1
            continue

        raw = hub_path.read_text(encoding="utf-8")
        parts = raw.split("---", 2)
        if len(parts) < 3:
            print(f"  [warn] {name}: frontmatter 格式错误 -> 跳过")
            skipped += 1
            continue
        # parts[0] = (空或前导), parts[1] = frontmatter, parts[2] = body
        fm = yaml.safe_load(parts[1]) or {}
        body = parts[2]

        # 合并策略: 只增不改删, 不覆盖中枢侧手动润色
        new_reuse = v.get("reuse_count", 0) or data.get("reuse_count", 0) or 0
        old_reuse = int(fm.get("reuse_count", 0) or 0)
        fm["reuse_count"] = max(new_reuse, old_reuse)
        fm["status"] = "active"
        fm["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        hub_at = fm.get("anti_trigger", []) or []
        skill_forgot = data.get("forgot", []) or []
        merged_at = list(dict.fromkeys(list(hub_at) + [x for x in skill_forgot if isinstance(x, str)]))
        if merged_at:
            fm["anti_trigger"] = merged_at

        new_fm_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
        new_raw = "---\n" + new_fm_text + "---" + body

        if args.dry_run:
            print(f"  [dry-run] {name}: {hub_path.name}")
        else:
            hub_path.write_text(new_raw, encoding="utf-8")
            print(f"  [push] {name}: {hub_path.name} -> status=active, reuse_count={fm['reuse_count']}")
        updated += 1

    print(f"push-to-hub: {updated} hub cards updated, {skipped} skipped  (dry_run={args.dry_run})")


def _find_hub_card(hub_root: Path, references: list, skill_name: str) -> Path | None:
    """从 references 或 skill_name 定位中枢 .md 文件。"""
    for ref in references or []:
        ref_str = str(ref).replace("\\", "/")
        idx = ref_str.find("AgentMemoryHub")
        if idx >= 0:
            rel = ref_str[idx + len("AgentMemoryHub") + 1:]
            candidate = hub_root / rel
            if candidate.is_file():
                return candidate
        candidate = Path(ref)
        if candidate.is_file() and hub_root in candidate.parents:
            return candidate
    matches = list(hub_root.rglob(f"{skill_name}.md"))
    if matches:
        return matches[0]
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillhub", description="SkillHub 路由/反馈/权重/验证/审核 CLI"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_route = sub.add_parser("route", help="意图路由命中(按权重降序)")
    p_route.add_argument("query", help="任务意图文本")
    p_route.add_argument("--router", default=str(_default_router()))
    p_route.add_argument("--root", default=None, help="审计根(传入则按贝叶斯权重排序)")
    p_route.set_defaults(func=_cmd_route)

    p_record = sub.add_parser(
        "record", help="记录一次成败事件(落 .skillhub/usage.jsonl)"
    )
    p_record.add_argument("name", help="技能名")
    state = p_record.add_mutually_exclusive_group(required=True)
    state.add_argument("--success", dest="state", action="store_const", const="success")
    state.add_argument("--failure", dest="state", action="store_const", const="failure")
    state.add_argument("--neutral", dest="state", action="store_const", const="neutral")
    p_record.add_argument("--root", default=str(_default_root()))
    p_record.set_defaults(func=_cmd_record)

    p_weight = sub.add_parser("weight", help="查贝叶斯有效权重")
    p_weight.add_argument("name", help="技能名")
    p_weight.add_argument("--root", default=str(_default_root()))
    p_weight.add_argument("--base", type=float, default=1.0, help="基础权重(默认 1.0)")
    p_weight.set_defaults(func=_cmd_weight)

    p_sync = sub.add_parser(
        "sync-verification",
        help="双源: usage.jsonl 优先, 回落中枢卡 reuse_count → 回写 skill.yaml verification",
    )
    p_sync.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_sync.add_argument("--root", default=str(_default_root()))
    p_sync.add_argument("--hub-root", default="", help="中枢目录 (用于回落读取卡 frontmatter reuse_count)")
    p_sync.set_defaults(func=_cmd_sync_verification)

    p_promote = sub.add_parser("promote", help="手动设置技能验证状态(reference/active)")
    p_promote.add_argument("name", help="技能名")
    p_promote.add_argument(
        "--status",
        choices=["active", "reference", "deprecated"],
        default="active",
        help="目标状态",
    )
    p_promote.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_promote.set_defaults(func=_cmd_promote)

    p_audit = sub.add_parser(
        "audit", help="扫描 SKILL.md 检查 authoring 检查清单覆盖率"
    )
    p_audit.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_audit.set_defaults(func=_cmd_audit)

    p_new = sub.add_parser("new", help="创建新技能骨架(含 authoring 检查清单)")
    p_new.add_argument("name", help="技能名(slug)")
    p_new.add_argument("--slot", choices=["shared", "dedicated"], default="shared")
    p_new.add_argument("--scope", default="", help="专用域(仅 slot=dedicated 时填写)")
    p_new.set_defaults(func=_cmd_new)

    p_reconcile = sub.add_parser(
        "reconcile",
        help="中枢 → SkillHub 反向回流: 扫描中枢卡, 判级升级成本地技能(dry-run 默认)",
    )
    p_reconcile.add_argument("--hub-root", default="", help="记忆中枢根(默认读 hub.config.yaml)")
    p_reconcile.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_reconcile.add_argument("--router", default=str(_default_router()))
    p_reconcile.add_argument("--apply", action="store_true", help="真正写盘并登记 router.yaml(默认 dry-run)")
    p_reconcile.add_argument(
        "--card-type",
        default=None,
        help="只处理指定卡型(逗号多值), 如 blueprint,methodology,exp,project",
    )
    p_reconcile.add_argument(
        "--hub-status",
        default=None,
        help="只处理指定中枢状态(逗号多值), 如 active,reference",
    )
    p_reconcile.add_argument(
        "--slug",
        default=None,
        help="精确指定 slug(逗号多值), 如 skill-governance-blueprint,skill-governance-playbook",
    )
    p_reconcile.add_argument(
        "--scope",
        default=None,
        help="只处理指定 scope(逗号多值), 空 scope 用 <empty> 匹配, 如 govern,cad",
    )
    p_reconcile.add_argument(
        "--batch-size",
        type=int,
        default=0,
        help="分批大小, 0=不分批; 候选卡过多时用分批避免 --apply 范围过大",
    )
    p_reconcile.add_argument(
        "--batch-index",
        type=int,
        default=0,
        help="分批索引(从 0 开始), 配合 --batch-size 使用",
    )
    p_reconcile.add_argument(
        "--save-candidates",
        default="",
        help="dry-run 时把候选集存 JSON, 后续 --load-candidates 可复用 (避免反复扫描中枢)",
    )
    p_reconcile.add_argument(
        "--load-candidates",
        default="",
        help="跳过中枢 scan/filter, 直接从 JSON 缓存读候选集 (之前 --save-candidates 生成的)",
    )
    p_reconcile.set_defaults(func=_cmd_reconcile)
    # migrate
    p_migrate = sub.add_parser(
        "migrate",
        help="回填旧技能缺失的 verification / slot / __reconcile_batch__ 字段",
    )
    p_migrate.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_migrate.add_argument("--hub-root", default="")
    p_migrate.add_argument("--dry-run", action="store_true")
    p_migrate.set_defaults(func=_cmd_migrate)

    # verify
    p_verify = sub.add_parser(
        "verify",
        help="对一个技能跑最小 T1 验证 (静态检查 + 回写 t1_record)",
    )
    p_verify.add_argument("name")
    p_verify.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_verify.add_argument("--demo", action="store_true")
    p_verify.add_argument("--t1-record", default="")
    p_verify.add_argument("--dry-run", action="store_true")
    p_verify.set_defaults(func=_cmd_verify)

    # promote-auto
    p_promote_auto = sub.add_parser(
        "promote-auto",
        help="自动晋级: reuse_count >= 阈值 且 t1_record 有真实试用 -> reference->active",
    )
    p_promote_auto.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_promote_auto.add_argument("--threshold", type=int, default=3)
    p_promote_auto.add_argument("--dry-run", action="store_true")
    p_promote_auto.set_defaults(func=_cmd_promote_auto)

    # push-to-hub
    p_push = sub.add_parser(
        "push-to-hub",
        help="SkillHub -> 中枢: active 技能回写中枢卡 status/reuse_count/anti_trigger",
    )
    p_push.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_push.add_argument("--hub-root", required=True)
    p_push.add_argument("--dry-run", action="store_true")
    p_push.set_defaults(func=_cmd_push_to_hub)


    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
