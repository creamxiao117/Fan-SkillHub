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
    """从 usage.jsonl 聚合 reuse_count, 回写到每个 skill.yaml 的 verification.reuse_count。"""
    from router.tools.router_audit import load_outcomes

    outcomes = load_outcomes(args.root)
    updated = 0
    for skill_yaml in Path(args.skill_root).rglob("skill.yaml"):
        data = yaml.safe_load(skill_yaml.read_text(encoding="utf-8"))
        name = data.get("name", "")
        if not name or name not in outcomes:
            continue
        total = outcomes[name].get("success", 0) + outcomes[name].get("failure", 0)
        verification = data.setdefault("verification", {})
        verification["reuse_count"] = total
        verification["last_verified"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_yaml.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        updated += 1
        print(f"  updated {name}: reuse_count={total}")
    print(f"sync-verification: {updated} skills updated")


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
        help="从 usage.jsonl 聚合 reuse_count 回写到 skill.yaml verification 字段",
    )
    p_sync.add_argument("--skill-root", default=str(SKILLS_ROOT))
    p_sync.add_argument("--root", default=str(_default_root()))
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
    p_reconcile.set_defaults(func=_cmd_reconcile)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
