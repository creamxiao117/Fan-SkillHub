"""skill_promotion(中枢→SkillHub 反向回流) 测试。

在隔离临时目录造假中枢与技能库, 验证:
- 只收 status=active 且 type 已知的卡
- 判级: tags 命中 memory-hub → dedicated+scope
- dry-run 只列不写盘; apply 生成 skill.yaml+SKILL.md 且登记 router
- 幂等: 技能目录已存在 → skip, 不重复生成
"""

from __future__ import annotations

from pathlib import Path

import yaml

from bridge import skill_promotion as sp

CARD_BODY = """\
# 中枢卡示例标题

## 适用场景

- 需要把经验升级为技能时触发

## 不适用 / 边界

- 不自动执行外部脚本
- 禁止外发敏感数据
"""


def _make_hub(root: Path) -> Path:
    """造假中枢: 一张 active exp 卡(带 memory-hub 域) + 一张非活跃卡。"""
    hub = root / "hub"
    exp = hub / "experience"
    exp.mkdir(parents=True)
    (exp / "memory-hub-回流.md").write_text(
        "---\ntype: exp\nname: reuse-writeback\ntags:\n  - memory-hub\n  - writeback\n"
        "status: active\n---\n\n" + CARD_BODY,
        encoding="utf-8",
    )
    (exp / "inactive.md").write_text(
        "---\ntype: exp\nname: inactive-one\nstatus: reference\ntags: []\n---\n\n参考卡",
        encoding="utf-8",
    )
    return hub


def test_scan_only_active_and_known_type(tmp_path: Path) -> None:
    hub = _make_hub(tmp_path)
    cards = sp.scan_hub_cards(hub)
    slugs = {c.slug for c in cards}
    assert "reuse-writeback" in slugs
    assert "inactive-one" not in slugs  # reference 不升级


def test_evaluate_dedicated_by_domain_tag() -> None:
    info = sp._evaluate_slot("exp", ["memory-hub", "gate"])
    assert info == {"slot": "dedicated", "scope": "memory-hub"}
    assert sp._evaluate_slot("methodology", []) == {
        "slot": "shared",
        "scope": "",
    }


def test_reconcile_dry_run_writes_nothing(tmp_path: Path) -> None:
    hub = _make_hub(tmp_path)
    skill_root = tmp_path / "skills"
    acts = sp.reconcile(hub, skill_root, apply=False)
    assert acts and acts[0]["action"] == "propose"
    assert acts[0]["slot"] == "dedicated"
    assert acts[0]["scope"] == "memory-hub"
    # dry-run 不落盘
    assert not list(skill_root.rglob("skill.yaml"))


def test_reconcile_apply_writes_files_and_registers_router(tmp_path: Path) -> None:
    hub = _make_hub(tmp_path)
    skill_root = tmp_path / "skills"
    router = tmp_path / "router.yaml"
    router.write_text("skills: []\n", encoding="utf-8")
    acts = sp.reconcile(hub, skill_root, apply=True, router_path=router)
    applied = [a for a in acts if a["action"] == "apply"]
    assert applied, acts
    dest = Path(applied[0]["target"])
    assert (dest / "skill.yaml").exists()
    assert (dest / "SKILL.md").exists()
    # router 已登记该技能
    data = yaml.safe_load(router.read_text(encoding="utf-8"))
    names = [s["name"] for s in data["skills"]]
    assert "reuse-writeback" in names
    # 二次 apply → 幂等 skip, 不重复生成
    acts2 = sp.reconcile(hub, skill_root, apply=True, router_path=router)
    assert all(a["action"] == "skip" for a in acts2)


def test_render_skill_md_keeps_neg_boundary(tmp_path: Path) -> None:
    hub = _make_hub(tmp_path)
    card = sp.scan_hub_cards(hub)[0]
    md = sp.render_skill_md(card)
    assert "不自动执行外部脚本" in md  # 负路由边界被保留
    assert "## 触发" in md
