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


# ─── apply 分支四象限一致性检查 ──────────────────────────────────────

def _make_router(tmp_path: Path, names: list[str] | None = None) -> Path:
    """创建空 router.yaml, 可选预填 names 条目。"""
    router = tmp_path / "router.yaml"
    skills = []
    for name in (names or []):
        skills.append({"name": name, "slot": "shared", "scope": ""})
    router.write_text(yaml.safe_dump({"skills": skills}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return router


def _make_skill_dir(skill_root: Path, slug: str, scope: str = "") -> Path:
    """在技能库创建已存在的 skill.yaml + SKILL.md (模拟已生成技能)。"""
    if scope:
        dest = skill_root / "shared" / scope / slug
    else:
        dest = skill_root / "shared" / slug
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "skill.yaml").write_text(
        f"name: {slug}\nslot: shared\nscope: {scope}\nstatus: reference\n",
        encoding="utf-8",
    )
    (dest / "SKILL.md").write_text(f"# {slug}\n", encoding="utf-8")
    return dest


def test_apply_quadrant1_both_exist_skip(tmp_path: Path) -> None:
    """象限 ①: skill.yaml 存在 AND router 已登记 → skip (幂等)。"""
    hub = _make_hub(tmp_path)
    skill_root = tmp_path / "skills"
    slug = "reuse-writeback"  # _make_hub 里那张 active exp 卡的 slug
    # 这张卡带 memory-hub tag → _evaluate_slot 返回 dedicated+scope=memory-hub
    router = _make_router(tmp_path, names=[slug])
    # 路径必须与 reconcile 期望一致: dedicated/memory-hub/<slug>
    dest = skill_root / "dedicated" / "memory-hub" / slug
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "skill.yaml").write_text(f"name: {slug}\n", encoding="utf-8")
    (dest / "SKILL.md").write_text(f"# {slug}\n", encoding="utf-8")

    acts = sp.reconcile(hub, skill_root, apply=True, router_path=router)
    assert len(acts) == 1
    assert acts[0]["action"] == "skip"
    assert "均已存在" in acts[0]["reason"]


def test_apply_quadrant2_router_has_skill_missing_warn(tmp_path: Path) -> None:
    """象限 ②: router 已登记 BUT skill.yaml 不存在 → skip + ⚠ 警告。"""
    hub = _make_hub(tmp_path)
    skill_root = tmp_path / "skills"
    slug = "reuse-writeback"
    router = _make_router(tmp_path, names=[slug])
    # 不造 skill 目录 — 模拟之前 apply 被中断, router 写了但文件没落

    acts = sp.reconcile(hub, skill_root, apply=True, router_path=router)
    assert len(acts) == 1
    assert acts[0]["action"] == "skip"
    assert "⚠" in acts[0]["reason"]
    assert "router 已登记但技能目录不存在" in acts[0]["reason"]
    # 技能文件仍不存在
    assert not list(skill_root.rglob("skill.yaml"))


def test_apply_quadrant3_skill_exists_router_missing_patch(tmp_path: Path) -> None:
    """象限 ③: skill.yaml 存在 BUT router 未登记 → patch-router (补登记, 不覆盖技能)。"""
    hub = _make_hub(tmp_path)
    skill_root = tmp_path / "skills"
    slug = "reuse-writeback"
    router = _make_router(tmp_path, names=[])  # router 空
    # 路径必须与 reconcile 期望一致: dedicated/memory-hub/<slug>
    dest = skill_root / "dedicated" / "memory-hub" / slug
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "skill.yaml").write_text(f"name: {slug}\n", encoding="utf-8")
    (dest / "SKILL.md").write_text(f"# {slug}\n", encoding="utf-8")
    original_mtime = (dest / "skill.yaml").stat().st_mtime

    acts = sp.reconcile(hub, skill_root, apply=True, router_path=router)
    assert len(acts) == 1
    assert acts[0]["action"] == "patch-router"
    assert "补登记" in acts[0]["reason"]
    # router 现在有了
    data = yaml.safe_load(router.read_text(encoding="utf-8"))
    assert any(s["name"] == slug for s in data["skills"])
    # 技能文件未被覆盖 (mtime 不应变)
    new_mtime = (dest / "skill.yaml").stat().st_mtime
    assert new_mtime == original_mtime


def test_apply_quadrant4_neither_exists_full_generate(tmp_path: Path) -> None:
    """象限 ④: 两者都不存在 → 正常全量 apply 生成。"""
    hub = _make_hub(tmp_path)
    skill_root = tmp_path / "skills"
    slug = "reuse-writeback"
    router = _make_router(tmp_path, names=[])
    # 不造 skill 目录, router 也空

    acts = sp.reconcile(hub, skill_root, apply=True, router_path=router)
    assert len(acts) == 1
    assert acts[0]["action"] == "apply"
    assert "生成技能" in acts[0]["reason"]

    dest = Path(acts[0]["target"])
    assert (dest / "skill.yaml").exists()
    assert (dest / "SKILL.md").exists()

    data = yaml.safe_load(router.read_text(encoding="utf-8"))
    assert any(s["name"] == slug for s in data["skills"])


def test_apply_four_quadrants_together(tmp_path: Path) -> None:
    """综合: 四张不同卡, 每张落在不同象限, 一次 reconcile 全命中。"""
    # 造中枢: 4 张 active exp 卡 (slug 各不相同)
    hub = tmp_path / "hub"
    exp = hub / "experience"
    exp.mkdir(parents=True)
    slugs = ["quad1-both", "quad2-router-only", "quad3-skill-only", "quad4-neither"]
    for s in slugs:
        (exp / f"{s}.md").write_text(
            f"---\ntype: exp\nname: {s}\ntags: []\nstatus: active\n---\n\n卡正文 {s}",
            encoding="utf-8",
        )

    skill_root = tmp_path / "skills"
    # 象限①: both — 造 skill 目录 + router 预登记
    _make_skill_dir(skill_root, "quad1-both")
    router = _make_router(tmp_path, names=["quad1-both", "quad2-router-only"])
    # 象限②: router-only — router 预登记但不造 skill 目录 (router 已有 quad2-router-only)
    # 象限③: skill-only — 造 skill 目录但 router 空 (router 没有 quad3-skill-only)
    _make_skill_dir(skill_root, "quad3-skill-only")
    # 象限④: neither — 都没造

    acts = sp.reconcile(hub, skill_root, apply=True, router_path=router)
    by_slug = {a["slug"]: a for a in acts}

    assert by_slug["quad1-both"]["action"] == "skip"
    assert "均已存在" in by_slug["quad1-both"]["reason"]

    assert by_slug["quad2-router-only"]["action"] == "skip"
    assert "⚠" in by_slug["quad2-router-only"]["reason"]

    assert by_slug["quad3-skill-only"]["action"] == "patch-router"
    assert "补登记" in by_slug["quad3-skill-only"]["reason"]

    assert by_slug["quad4-neither"]["action"] == "apply"
    assert "生成技能" in by_slug["quad4-neither"]["reason"]


def test_filter_scope_works(tmp_path: Path) -> None:
    """G1: --scope 筛选生效, 空 scope 用 '<empty>' 匹配。"""
    hub = tmp_path / "hub"
    exp = hub / "experience"
    exp.mkdir(parents=True)
    # 两张卡, 一张 memory-hub scope, 一张无 scope
    (exp / "scope-hub.md").write_text(
        "---\ntype: exp\nname: hub-card\ntags: [memory-hub]\nstatus: active\n---\n\n带 scope",
        encoding="utf-8",
    )
    (exp / "scope-empty.md").write_text(
        "---\ntype: exp\nname: empty-card\ntags: []\nstatus: active\n---\n\n无 scope",
        encoding="utf-8",
    )
    skill_root = tmp_path / "skills"

    # scope=memory-hub → 只命中 hub-card
    acts = sp.reconcile(hub, skill_root, apply=False, scope_filter="memory-hub")
    slugs = [a["slug"] for a in acts]
    assert slugs == ["hub-card"]

    # scope=<empty> → 只命中 empty-card
    acts2 = sp.reconcile(hub, skill_root, apply=False, scope_filter="<empty>")
    slugs2 = [a["slug"] for a in acts2]
    assert slugs2 == ["empty-card"]


def test_filter_slug_exact(tmp_path: Path) -> None:
    """slug_filter 精确逗号多值匹配。"""
    hub = _make_hub(tmp_path)
    skill_root = tmp_path / "skills"
    # _make_hub 有两张卡: reuse-writeback (active) + inactive (reference)
    acts = sp.reconcile(hub, skill_root, apply=False, slug_filter="reuse-writeback")
    assert [a["slug"] for a in acts] == ["reuse-writeback"]

    # slug 不存在 → 空
    acts2 = sp.reconcile(hub, skill_root, apply=False, slug_filter="nonexistent")
    assert acts2 == []


def test_batch_split(tmp_path: Path) -> None:
    """G4: batch_size / batch_index 分批切片正确。"""
    hub = tmp_path / "hub"
    exp = hub / "experience"
    exp.mkdir(parents=True)
    # 造 5 张 active exp 卡
    for i in range(5):
        (exp / f"batch-{i}.md").write_text(
            f"---\ntype: exp\nname: batch-{i}\ntags: []\nstatus: active\n---\n\n卡 {i}",
            encoding="utf-8",
        )
    skill_root = tmp_path / "skills"

    # batch_size=2, batch_index=0 → 前 2 张
    acts0 = sp.reconcile(hub, skill_root, apply=False, batch_size=2, batch_index=0)
    assert len(acts0) == 2
    assert acts0[0]["slug"] < acts0[1]["slug"]  # 排序稳定

    # batch_size=2, batch_index=1 → 中间 2 张
    acts1 = sp.reconcile(hub, skill_root, apply=False, batch_size=2, batch_index=1)
    assert len(acts1) == 2

    # batch_size=2, batch_index=2 → 最后 1 张
    acts2 = sp.reconcile(hub, skill_root, apply=False, batch_size=2, batch_index=2)
    assert len(acts2) == 1

    # 三批合计 = 5 张, 无重叠
    all_slugs = [a["slug"] for a in acts0 + acts1 + acts2]
    assert sorted(all_slugs) == ["batch-0", "batch-1", "batch-2", "batch-3", "batch-4"]


def test_enrich_from_index_coverage(tmp_path: Path) -> None:
    """G3: INDEX.md 存在时 title/tags 被补充; 不存在时静默跳过。"""
    hub = _make_hub(tmp_path)
    cards = sp.scan_hub_cards(hub)
    before_title = cards[0].title
    before_tags = list(cards[0].tags)

    # INDEX.md 不存在 → enrich 无变化
    sp._enrich_from_index(cards, hub / "INDEX.md")
    assert cards[0].title == before_title

    # INDEX.md 存在且有对应条目
    (hub / "INDEX.md").write_text(
        "- reuse-writeback  升级回写经验蓝图（含 reuse_count 自动聚合）",
        encoding="utf-8",
    )
    sp._enrich_from_index(cards, hub / "INDEX.md")
    # INDEX 描述较长, title 应该被覆盖
    assert len(cards[0].title) >= 10
    # 应该有新 tags 补充
    assert len(cards[0].tags) >= len(before_tags)


def test_router_has_name_exists_and_missing(tmp_path: Path) -> None:
    """_router_has_name 辅助函数: 有/无/坏文件三种情况。"""
    router = _make_router(tmp_path, names=["foo", "bar"])
    assert sp._router_has_name(router, "foo") is True
    assert sp._router_has_name(router, "baz") is False

    # router.yaml 不存在 → False
    missing = tmp_path / "no-such-router.yaml"
    assert sp._router_has_name(missing, "anything") is False

    # 坏 yaml → False (不崩溃)
    bad = tmp_path / "bad.yaml"
    bad.write_text("::::not valid yaml::::", encoding="utf-8")
    assert sp._router_has_name(bad, "anything") is False
