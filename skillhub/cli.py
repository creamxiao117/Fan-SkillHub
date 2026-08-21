"""SkillHub 命令行入口: route / record / weight。

复用 router(路由命中排序)与 router_audit(贝叶斯成败反馈) 核心,
把"防上下文膨胀"的路由命中与权重排序暴露为可调用命令, 供自定义脚本与外部
agent 平台接入。审计事件(record 成败)持久化到 <root>/.skillhub/usage.jsonl。

用法:
    python -m skillhub route "<query>" [--router PATH] [--root PATH]
    python -m skillhub record <name> --success|--failure|--neutral [--root PATH]
    python -m skillhub weight <name> [--root PATH] [--base 1.0]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_router() -> Path:
    return PROJECT_ROOT / "router" / "router.yaml"


def _default_root() -> Path:
    # 默认审计根: 项目本地 .skillhub(记录成败事件), 可 --root 覆盖
    return PROJECT_ROOT / ".skillhub"


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillhub", description="SkillHub 路由/反馈/权重 CLI"
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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
