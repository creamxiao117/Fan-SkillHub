"""SkillHub 生命周期治理：promoted(共用/专用) <-> archive 迁移判据。

对应方案B 三级桶。只读扫描 + 返回迁移动作清单, 由调用方决定是否落盘,
保持可逆(归档非删除)。判据集中在 lifecycle 一处, 不复制到每个 skill。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

SKILL_YAML_NAME = "skill.yaml"

# 复用次数低于该阈值 → 判定归档(长期未被复用)
REUSE_ARCHIVE_THRESHOLD = 0
# 已稳定归入共用库的状态, 健康时不迁移
HEALTHY_STATUSES = {"active"}


def _slot_dir(slot: str) -> str:
    # shared / dedicated 为 promoted 桶; archive 为收敛桶
    return slot


def classify(*, status: str, reuse_count: int) -> str:
    """判定单技能迁移动作: promote / archive / none。

    规则(仅判据, 不落盘):
    - deprecated 或复用低于阈值 → archive(可逆归档)
    - 其余健康状态 → none
    """
    if status == "deprecated":
        return "archive"
    if reuse_count <= REUSE_ARCHIVE_THRESHOLD:
        return "archive"
    return "none"


def _read_skill_yaml(skill_dir: Path) -> dict[str, Any] | None:
    """读取技能元数据(frontmatter name/slot/status/reuse_count)。"""
    p = skill_dir / SKILL_YAML_NAME
    if not p.exists():
        return None
    meta: dict[str, Any] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if (
            ":" in line
            and not line.lstrip().startswith(("---", "body"))
            and not line.startswith("  ")
        ):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta


def scan_library(shared_root: str | Path) -> list[dict[str, Any]]:
    """扫描共用/专用桶, 应用迁移判据, 产出动作清单(不落盘)。

    返回 [{name, slot, action, reason}], 空列表表示无需迁移。
    归档是可逆操作: 只产出动作, 由调用方复核后执行。
    """
    root = Path(shared_root)
    if not root.exists():
        return []
    actions: list[dict[str, Any]] = []
    # 只扫一层技能目录(每个技能一个子目录)
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir():
            continue
        meta = _read_skill_yaml(skill_dir)
        if meta is None:
            continue
        name = meta.get("name", skill_dir.name)
        status = meta.get("status", "reference")
        try:
            reuse = int(meta.get("reuse_count", 0))
        except ValueError:
            continue
        # 已归档的技能不进筛选(避免重复归档)
        if _slot_dir(meta.get("slot", "")) == "archive":
            continue
        action = classify(status=status, reuse_count=reuse)
        if action != "none":
            actions.append(
                {"name": name, "slot": meta.get("slot", ""), "action": action}
            )
    return actions


def promote(base: Path, skill_dir: Path) -> None:
    """(占位)将 skill 从任一桶提升到 promoted 桶; 具体落盘由调用方实现。"""
    raise NotImplementedError("promote 落盘待方案B落地")
