"""lifecycle 迁移判据测试(TDD)。

cover:
- classify: 给定技能元数据, 判定迁移动作 promote/archive/none
- scan_library: 扫描库目录, 应用判据, 产出迁移动作清单
- 归档门禁: 复用过低或 deprecated 标记才进 archive(可逆, 非删除)
"""

from pathlib import Path

from router.tools.lifecycle import (
    SKILL_YAML_NAME,
    classify,
    scan_library,
)


def _write_skill(base: Path, slot: str, name: str, **fields):
    """写一个最小 skill.yaml"""
    d = base / slot / name
    d.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"name: {name}", f"slot: {slot}"]
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines += ["---", "body"]
    (d / SKILL_YAML_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return d


def test_skill_yaml_name():
    assert SKILL_YAML_NAME == "skill.yaml"


def test_classify_healthy_no_action():
    """正常技能(近用/复用中)不迁移"""
    assert classify(status="active", reuse_count=5) == "none"


def test_classify_low_reuse_archives():
    """长期未复用(复用过低) → archive"""
    assert classify(status="active", reuse_count=0) == "archive"


def test_classify_deprecated_archives():
    """deprecated 标记 → archive"""
    assert classify(status="deprecated", reuse_count=5) == "archive"


def test_classify_requires_gate_not_delete():
    """归档是可逆迁移, 非删除; 返回动作而非直接删文件"""
    kind = classify(status="deprecated", reuse_count=5)
    assert kind == "archive"
    assert kind not in ("delete",)


def test_scan_library_habitat(tmp_path):
    """共用库健康技能留在原地(不迁移)"""
    _write_skill(
        tmp_path, "shared", "github-star-distill", status="active", reuse_count=5
    )
    total = len(list((tmp_path / "shared").rglob("*.yaml")))
    assert total == 1
    actions = scan_library(tmp_path / "shared")
    assert actions == []


def test_scan_library_archives_unused(tmp_path):
    """共用库中复用为 0 的技能 → archive"""
    _write_skill(tmp_path, "shared", "old-tool", status="active", reuse_count=0)
    actions = scan_library(tmp_path / "shared")
    assert len(actions) == 1
    assert actions[0]["name"] == "old-tool"
    assert actions[0]["action"] == "archive"


def test_scan_library_unknown_status(tmp_path):
    """未识别状态不该被当作 deprecated 处理, 有复用则不误迁"""
    _write_skill(tmp_path, "shared", "weird", status="experimental", reuse_count=3)
    assert scan_library(tmp_path / "shared") == []
