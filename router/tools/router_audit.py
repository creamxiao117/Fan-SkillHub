"""SkillHub 成败反馈闭环：按成功率贝叶斯更新技能权重。

设计要点(对标 Skill Context Manager 贝叶斯反馈, 本地简化版):
- record_outcome 记录一次"归因到该技能且成功/失败"的事件(成功/失败),
  追加写 .skillhub/usage.jsonl, best-effort 不阻断业务。
- load_outcomes 聚合成功率。
- effective_weight 用贝叶斯先验平滑成功率驱动权重:
    未见过 → 原权重(不做惩罚/奖励, 中立先验)
    否则    → base * (success + prior) / (success + failure + alpha)
  成功率越高的技能权重越高, 失败多的技能被降权(将被路由表更少命中)。
- 带 FLOOR 下界, 防止权重归零导致技能被永久禁用(vs 单纯按次数降权)。
- 纯函数 + 可注入 load 便于单测。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# 贝叶斯先验计数(平滑项, 避免小样本被极端率碾压)
SUCCESS_PRIOR = 1  # 参与成功侧平滑
ALPHA = 2  # 分母追加: 相当于 (success+prior)/(success+failure+prior+alpha)
# 权重下限, 防止失败技能被永久禁用
FLOOR = 0.05
LOG_NAME = "usage.jsonl"


def usage_log_path(root: str | Path) -> Path:
    """命中日志路径: 固定 <root>/.skillhub/usage.jsonl"""
    return Path(root) / ".skillhub" / LOG_NAME


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_outcome(root: str | Path, name: str, *, success: bool) -> Path:
    """记录一次成果事件(success=True/False), 参数以关键字形式确保语义清晰。

    写入失败静默(D4 best-effort), 不阻断路由业务。
    """
    p = usage_log_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(p, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "outcome": "success" if success else "failure",
                        "name": name,
                        "ts": _ts(),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except OSError:
        pass
    return p


def load_outcomes(root: str | Path) -> dict[str, dict[str, int]]:
    """聚合各技能成功/失败次数。

    返回 {name: {"success": n, "failure": n}}; 无日志返回空 dict.
    """
    p = usage_log_path(root)
    result: dict[str, dict[str, int]] = {}
    if not p.exists():
        return result
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = rec.get("name") if isinstance(rec, dict) else None
        outcome = rec.get("outcome") if isinstance(rec, dict) else None
        if not name or outcome not in ("success", "failure"):
            continue
        agg = result.setdefault(name, {"success": 0, "failure": 0})
        agg[outcome] += 1
    return result


def effective_weight(root: str | Path, name: str, base_weight: float = 1.0) -> float:
    """按贝叶斯成功率计算有效权重。

    未见历史 → 原权重(中立先验); 否则
        base * (success + PRIOR) / (success + failure + PRIOR + ALPHA)
    成功率越高权重越高, 失败多被降权; 有 FLOOR 下界防永久禁用。
    """
    agg = load_outcomes(root).get(name)
    if agg is None:
        return base_weight
    success = agg["success"]
    failure = agg["failure"]
    total = success + failure
    if total == 0:
        return base_weight
    w = base_weight * (success + SUCCESS_PRIOR) / (total + SUCCESS_PRIOR + ALPHA)
    return max(w, FLOOR)
