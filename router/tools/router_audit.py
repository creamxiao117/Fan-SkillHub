"""SkillHub 反触发降权：记录命中事件并按复用次数降权。

设计要点(对齐记忆中枢能力路由经验卡):
- 命中事件追加写 .skillhub/usage.jsonl, best-effort 不阻断业务。
- effective_weight: base_weight * decay(usages)。复用越多权重越低,
  带下限 floor, 防止技能被降权到永不可用。
- 纯函数 + 可注入 load_usages, 便于单测。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# 降权衰减: effective = base * pow(DECAY, usages)
DECAY = 0.9
# 权重下限, 防止降到归零
FLOOR = 0.1
LOG_NAME = "usage.jsonl"


def usage_log_path(root: str | Path) -> Path:
    """命中日志路径: 固定 <root>/.skillhub/usage.jsonl"""
    return Path(root) / ".skillhub" / LOG_NAME


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_usage(root: str | Path, name: str) -> Path:
    """记录一次技能命中事件(追加一行 jsonl)。

    写入失败静默(D4 best-effort), 不阻断路由业务。
    """
    p = usage_log_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(p, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {"action": "route_hit", "name": name, "ts": _ts()},
                    ensure_ascii=False,
                )
                + "\n"
            )
    except OSError:
        pass
    return p


def load_usages(root: str | Path) -> dict[str, int]:
    """汇总各技能命中次数; 无日志返回空 dict."""
    p = usage_log_path(root)
    if not p.exists():
        return {}
    counts: dict[str, int] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            name = json.loads(line).get("name")
        except (json.JSONDecodeError, AttributeError):
            continue
        if name:
            counts[name] = counts.get(name, 0) + 1
    return counts


def effective_weight(root: str | Path, name: str, base_weight: float = 1.0) -> float:
    """复用降权后的有效权重。

    未用过 → 原权重; 复用次数越多权重越低; 有 FLOOR 下限。
    """
    usages = load_usages(root).get(name, 0)
    if usages == 0:
        return base_weight
    w = base_weight * (DECAY**usages)
    return max(w, FLOOR)
