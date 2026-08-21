"""SkillHub 路由核心：JIT 命中注入 + 反触发降权 + 复杂度路由。

数据源: router/router.yaml(唯一事实源)。契约见 router/schema.yaml。
设计要点(对齐记忆中枢能力路由经验卡):
- 意图 -> 命中技能集,只回"摘要"不回全文(防上下文膨胀的主干)。
- forgot 负路由边界非空: 命中边界即放弃,防语义过命中/路由撒谎。
- complexity 复杂度判据集中在路由一处,不复制到每个技能。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# 命中结果仅携带给调用方做 JIT 决策的元数据键
HIT_KEYS = ("name", "slot", "scope", "invoke", "description_human", "description_model")


class RouterError(ValueError):
    """路由表加载/校验错误; 加载失败宁可拒绝, 不静默降级(路由撒谎比没有更糟)"""


def load_router(path: str | Path) -> list[dict[str, Any]]:
    """加载并校验路由表, 返回技能行列表。

    Raises:
        RouterError: 文件缺失/非法 yaml/契约违规(重复 name / forgot 为空)
    """
    p = Path(path)
    if not p.exists():
        raise RouterError(f"路由表不存在: {p}")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise RouterError(f"路由表 yaml 解析失败: {e}") from None
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        raise RouterError("路由表缺少 skills 列表")
    rows = data["skills"]
    _validate(rows)
    return rows


def _validate(rows: list[dict[str, Any]]) -> None:
    """契约校验: name 唯一、forgot 非空、含必要字段。"""
    seen: set[str] = set()
    for r in rows:
        name = r.get("name")
        if not name:
            raise RouterError("技能缺失 name")
        if name in seen:
            raise RouterError(f"技能 name 重复: {name}")
        seen.add(name)
        # 负路由边界必须非空, 防止语义过命中
        forgot = r.get("forgot")
        if not isinstance(forgot, list) or not forgot:
            raise RouterError(f"技能 {name} 的 forgot(负路由边界)必须非空")
        if not r.get("trigger"):
            raise RouterError(f"技能 {name} 的 trigger 必须非空")


def _match(row: dict[str, Any], query: str) -> str:
    """返回命中类型: hit(trigger命中) / forgot(负路由边界命中) / none"""
    q = query.lower()
    if any(str(t).lower() in q for t in row.get("trigger", [])):
        # 先检查负路由边界: 命中边界则放弃, 即使含 trigger 词
        if any(str(f).lower() in q for f in row.get("forgot", [])):
            return "forgot"
        return "hit"
    return "none"


def route(
    path: str | Path, query: str, *, root: str | Path | None = None
) -> list[dict[str, Any]]:
    """意图 -> 命中技能集(JIT 命中注入), 按权重降序返回。

    只返回命中技能的轻量摘要(HIT_KEYS), 不含全文, 由调用方按需再取本体。
    排序规则:
    - 未提供 root(审计根): 按 yaml 基础 weight 降序, 高权重靠前。
    - 提供 root: 按 effective_weight(贝叶斯成败反馈)降序, 失败率高的技能排后。
    同权重保持 yaml 声明顺序(稳定排序); 纯函数无副作用, 成败反馈由事件侧负责。
    """
    q = query.strip()
    if not q:
        return []
    from .router_audit import effective_weight

    hits: list[dict[str, Any]] = []
    for row in load_router(path):
        if _match(row, q) != "hit":
            continue
        hit = {k: row.get(k) for k in HIT_KEYS}
        base = float(row.get("weight", 1.0))
        if root is not None:
            hit["weight"] = effective_weight(root, hit["name"], base_weight=base)
        else:
            hit["weight"] = base
        hits.append(hit)
    hits.sort(key=lambda h: h["weight"], reverse=True)
    return hits


def complexity_of(*, files: int, cross_module: bool, public_behavior: bool) -> bool:
    """复杂度路由判据: 命中任一判据视为复杂(启用重审查/双轴)。

    阈值由调用方从路由表 complexity 读取, 此处仅聚合布尔判据。
    """
    return files > 2 or cross_module or public_behavior


def threshold_complexity(data: dict[str, Any], *, files: int) -> bool:
    """按路由表 complexity 阈值判定: 改动文件数/跨模块/公开行为任一命中即复杂。

    归口集中判定, 避免判据散落在每个技能。
    """
    c = data.get("complexity") or {}
    cross = bool(c.get("cross_module", False))
    pub = bool(c.get("public_behavior", False))
    thr = int(c.get("files_threshold", 2))
    return files > thr or cross or pub
