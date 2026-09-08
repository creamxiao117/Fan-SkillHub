# @version V1.0 / 2026-09-09 / Hermes / 技能版本感与健康度评估
"""skill_health.py —— 改进1 落地，技能健康度评估器。

V1.0 (2026-09-09): 扫描所有 skill.yaml，输出每个技能的：
- version（版本号是否存在）
- health_score（健康度 0-100）
- days_since_update（距上次更新天数）
- issues（发现的问题列表）

被 flywheel_daily_report.py 调用以生成"技能健康度报告"。
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml

from .router import load_router

HEALTH_RULES = {
    "missing_version": 20,
    "no_changelog": 5,
    "no_last_used": 5,
    "stale_180d": 15,
    "stale_90d": 5,
    "no_reuse_record": 5,
    "low_reuse_count": 5,
}

STALE_DAYS = 90
VERY_STALE_DAYS = 180


def evaluate_skill(skill_path: Path) -> dict[str, Any]:
    """评估单个 skill 的健康度。返回 dict 含 score, issues, version, updated。"""
    if not skill_path.exists():
        return {"name": skill_path.parent.name, "score": 0, "issues": ["file_missing"]}

    try:
        data = yaml.safe_load(skill_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {
            "name": skill_path.parent.name,
            "score": 0,
            "issues": [f"yaml_error: {exc}"],
        }

    issues: list[str] = []
    score = 100

    if "version" not in data:
        issues.append("missing_version")
        score -= HEALTH_RULES["missing_version"]
    if "changelog" not in data and data.get("version", "0.0.0").startswith("0."):
        issues.append("no_changelog")
        score -= HEALTH_RULES["no_changelog"]
    if "last_used" not in data and "reuse_count" not in data:
        issues.append("no_reuse_record")
        score -= HEALTH_RULES["no_reuse_record"]

    updated_val = data.get("updated", "")
    updated_str = updated_val.isoformat() if isinstance(updated_val, dt.date) else (updated_val or "")
    days_old = None
    if updated_str:
        try:
            updated_date = dt.date.fromisoformat(updated_str[:10])
            days_old = (dt.date.today() - updated_date).days
            if days_old > VERY_STALE_DAYS:
                issues.append(f"stale_{VERY_STALE_DAYS}d")
                score -= HEALTH_RULES[f"stale_{VERY_STALE_DAYS}d"]
            elif days_old > STALE_DAYS:
                issues.append(f"stale_{STALE_DAYS}d")
                score -= HEALTH_RULES[f"stale_{STALE_DAYS}d"]
        except ValueError:
            issues.append("invalid_date")
    else:
        issues.append("no_updated")
        score -= 5

    return {
        "name": data.get("name", skill_path.parent.name),
        "score": max(0, score),
        "issues": issues,
        "version": data.get("version", ""),
        "updated": updated_str,
        "days_old": days_old,
        "reuse_count": data.get("reuse_count", 0),
    }


def scan_skillhub(skillhub_root: Path) -> list[dict[str, Any]]:
    """扫描 SkillHub 所有 skill，返回健康度报告。"""
    results = []
    for skill_yaml in sorted(skillhub_root.rglob("skill.yaml")):
        if "archive" in skill_yaml.parts:
            continue
        result = evaluate_skill(skill_yaml)
        result["path"] = str(skill_yaml.relative_to(skillhub_root))
        results.append(result)
    return results


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """聚合健康度报告。"""
    if not results:
        return {"count": 0, "avg_score": 0, "by_status": {}}
    scores = [r["score"] for r in results]
    by_issues: dict[str, int] = {}
    for r in results:
        for issue in r["issues"]:
            by_issues[issue] = by_issues.get(issue, 0) + 1
    return {
        "count": len(results),
        "avg_score": round(sum(scores) / len(scores), 1),
        "min_score": min(scores),
        "max_score": max(scores),
        "low_health": [r["name"] for r in results if r["score"] < 60],
        "common_issues": dict(sorted(by_issues.items(), key=lambda x: -x[1])[:5]),
    }
