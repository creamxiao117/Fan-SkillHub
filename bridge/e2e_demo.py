"""SkillHub 端到端闭环演示(dry-run-safe)。

整链: attribute(归因) → gate(门禁) → record_outcome(成败) → effective_weight
      (贝叶斯权重) → route(路由命中排序) → writeback_card(中枢回写草稿)

默认全部在**隔离临时目录**运行, 不触碰真实中枢; 传入 --hub-root <路径> 才切到
指定中枢（用于接入 engine.py ingest 的真机验证）。演示卡一律走 exp/note 白名单,
不写 rule 权威区。

运行: python -m bridge.e2e_demo [--hub-root PATH]
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from bridge import attribution, gate
from bridge.config import load_config as load_hub_config
from bridge.ingest import writeback_card
from router.tools import router_audit
from router.tools.router import route


def _make_router(tmp: Path) -> Path:
    """造一张最简路由表, 含两个同 weight 技能(便于演示贝叶斯排序生效)."""
    p = tmp / "router.yaml"
    p.write_text(
        """\
version: 1.0.0
complexity: {files_threshold: 2, cross_module: true, public_behavior: true}
skills:
  - name: distill-a
    slot: shared
    invoke: user
    description_human: "技能 A"
    trigger: [借鉴]
    forgot: [仅跑命令]
    weight: 1.0
  - name: distill-b
    slot: shared
    invoke: user
    description_human: "技能 B"
    trigger: [借鉴]
    forgot: [仅跑命令]
    weight: 1.0
""",
        encoding="utf-8",
    )
    return p


def run(root: Path, hub_root: str | None, platform: str = "trae") -> None:
    """执行一次完整闭环, 打印关键步骤."""
    # 1) 造环境
    tmp = Path(root)
    router = _make_router(tmp)
    audit_root = tmp  # 审计日志就写在本临时目录
    print("== 1. 造临时路由表 + 审计根 ==")
    print(f"   路由表: {router}")

    # 2) 归因
    print("\n== 2. 证据归因 ==")
    trace_ok = attribution.Trace(
        skill="distill-a",
        subtasks=[
            attribution.Subtask("skill", ok=True, note="按 SKILL 隔离克隆"),
            attribution.Subtask("skill", ok=True, note="判级 B"),
            attribution.Subtask("result", ok=True, note="T1 真实任务通过"),
        ],
        result=True,
    )
    trace_bad = attribution.Trace(
        skill="distill-b",
        subtasks=[
            attribution.Subtask("skill", ok=True, note="按 SKILL 克隆"),
            attribution.Subtask("env", ok=False, note="网络失败"),
        ],
        result=False,
    )
    attr_ok = attribution.attribute(trace_ok)
    attr_bad = attribution.attribute(trace_bad)
    print(f"   distill-a → {attr_ok.grade} ({attr_ok.attribution})")
    print(f"   distill-b → {attr_bad.grade} ({attr_bad.attribution})")

    # 3) 门禁 -> 写反馈
    print("\n== 3. 证据门禁 -> 写成败反馈 ==")
    g_ok = gate.apply_outcome(audit_root, "distill-a", attr_ok)
    g_bad = gate.apply_outcome(audit_root, "distill-b", attr_bad)
    print(f"   distill-a → side={g_ok.side} (recorded={g_ok.recorded})")
    print(f"   distill-b → side={g_bad.side} (recorded={g_bad.recorded})")

    # 4) 贝叶斯权重
    print("\n== 4. 贝叶斯权重 ==")
    aggs = router_audit.load_outcomes(audit_root)
    for name, a in aggs.items():
        w = router_audit.effective_weight(audit_root, name)
        print(f"   {name}: {a} → effective_weight={w:.3f}")

    # 5) 路由命中排序(带审计根)
    print("\n== 5. 路由命中排序 (按贝叶斯权重降序) ==")
    hits = route(router, "想借鉴某个仓库的方法", root=audit_root)
    for h in hits:
        print(f"   {h['name']}: weight={h['weight']:.3f}")
    ranked = [h["name"] for h in hits]
    print(f"   推荐顺序: {ranked}")

    # 6) 中枢回写草稿(演示卡走 exp 白名单)
    print("\n== 6. 中枢回写草稿(exp) ==")
    cfg = load_hub_config(Path(__file__).parent.parent / "hub.config.yaml")
    dest = writeback_card(
        cfg,
        platform=platform,
        hub_root=hub_root or tmp,
        name="skillhub-e2e-demo",
        card_type="exp",
        body="SkillHub 端到端闭环演示: 按贝叶斯成败反馈, distill-a 优于 distill-b。",
        tags=["skillhub", "e2e", "demo"],
    )
    print(f"   草稿: {dest}")

    print("\n✅ 整链跑通。")
    print(f"   (审计日志: {tmp / '.skillhub' / 'usage.jsonl'})")


def main() -> None:
    parser = argparse.ArgumentParser(description="SkillHub 端到端闭环演示")
    parser.add_argument("--hub-root", default=None, help="切到真实中枢根(默认隔离 tmp)")
    parser.add_argument("--platform", default="trae", help="回写平台名")
    args = parser.parse_args()
    run(tempfile.mkdtemp(prefix="skillhub-e2e-"), args.hub_root, args.platform)


if __name__ == "__main__":
    main()