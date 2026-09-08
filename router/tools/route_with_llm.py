# @version V1.0 / 2026-09-09 / Hermes / route() 的 LLM 增强版
"""route_with_llm.py —— 改进6 落地，LLM 路由 fallback 增强。

V1.0 (2026-09-09): 在 route() 基础上，命中数不足时调用 LLM 决策补充。
- 优先走原有 route()（快、零成本、稳定）
- 当命中数 < min_hits 时调用 LLM 决策
- LLM 不可用时优雅降级（仅返回子串匹配结果）
- LLM 决策结果经 schema 校验（过滤幻觉技能名）
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .router import load_router
from .router_audit import effective_weight as _audit_weight

LOG = logging.getLogger(__name__)

OMNIROUTE_URL = os.environ.get("OMNIROUTE_URL", "http://127.0.0.1:20128/v1/chat/completions")
OMNIROUTE_MODEL = os.environ.get("OMNIROUTE_MODEL", "gpt-4o-mini")


def route_with_llm(
    router_path: str | Path,
    query: str,
    *,
    min_hits: int = 2,
    llm_timeout: float = 8.0,
    root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """route() + LLM 决策 fallback。

    Args:
        router_path: router.yaml 路径
        query: 用户 query
        min_hits: 触发 LLM 决策的最小命中数
        llm_timeout: LLM HTTP timeout（秒）
        root: 审计根（用于贝叶斯有效权重）

    Returns:
        命中技能列表（按权重降序）
    """
    from .router import route as _route

    base_hits = _route(router_path, query, root=root)
    if len(base_hits) >= min_hits:
        return base_hits

    llm_names = _llm_decide(router_path, query, timeout=llm_timeout)
    if not llm_names:
        return base_hits

    rows = {r["name"]: r for r in load_router(router_path)}
    existing = {h["name"] for h in base_hits}
    for n in llm_names:
        if n in existing or n not in rows:
            continue
        r = rows[n]
        hit = {k: r.get(k) for k in ("name", "slot", "scope", "invoke",
                                       "description_human", "description_model")}
        base = float(r.get("weight", 1.0))
        if root is not None:
            hit["weight"] = _audit_weight(root, n, base_weight=base)
        else:
            hit["weight"] = base
        hit["from_llm"] = True
        base_hits.append(hit)
        existing.add(n)

    base_hits.sort(key=lambda h: h["weight"], reverse=True)
    return base_hits


def _llm_decide(
    router_path: str | Path, query: str, *, timeout: float
) -> list[str]:
    """调用 LLM 让其选择命中的技能名列表。失败返回空。"""
    rows = load_router(router_path)
    skill_lines = [
        f"- {r['name']}: {r.get('description_model', '')}" for r in rows
    ]
    prompt = (
        "你是 SkillHub 技能路由助手。根据用户 query 选 0-3 个最相关的技能名。\n"
        "只输出 JSON 数组，例如 [\"skill1\",\"skill2\"]。\n"
        "如果不相关就输出 []。\n\n"
        f"Skills:\n" + "\n".join(skill_lines[:60]) + "\n\n"
        f"Query: {query}\n\nAnswer:"
    )

    try:
        import requests

        resp = requests.post(
            OMNIROUTE_URL,
            json={
                "model": OMNIROUTE_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        LOG.debug("LLM route fallback failed: %s", exc)
        return []

    return _parse_llm_json(text, valid_names={r["name"] for r in rows})


def _parse_llm_json(text: str, *, valid_names: set[str]) -> list[str]:
    """提取 LLM 输出中的 JSON 数组，仅保留白名单内的技能名。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(x) for x in data if isinstance(x, str) and x in valid_names][:3]
