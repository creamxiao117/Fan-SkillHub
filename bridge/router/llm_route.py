# @version V1.0 / 2026-09-09 / Hermes / LLM 技能路由（替代子串匹配）
"""llm_route.py —— 基于 LLM 的技能路由。

V1.0 (2026-09-09): 改进二 —— 替代 router.yaml 的子串 trigger 匹配，
用 LLM 判断用户 query 应该触发哪些 skill，避免子串匹配的误触/漏触问题。

设计原则：
- 读取 router.yaml 所有 skill 的 description_model + invoke + slot
- 让 LLM 决策（而非子串匹配）
- 支持 fallback：LLM 不可用时降级到关键字匹配
- 输出标准化：skill 名称列表

用法：
    from llm_route import llm_route_skills
    skills = llm_route_skills(query, router_yaml_path)
    # skills = ['memory-hub-card-promotion', 'github-star-distill']
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# LLM 调用（复用了 hub-engine 的 chat 接口，直接 requests 到 omniroute）
# ---------------------------------------------------------------------------

def _llm_complete(prompt: str, *, model: str | None = None) -> str:
    """调用 omniroute 网关，返回 LLM 回复文本。不可用时返回空字符串。"""
    try:
        import requests

        url = os.environ.get(
            "OMNIRoute_URL", "http://127.0.0.1:20128/v1/chat/completions"
        )
        api_key = os.environ.get("OMNIRoute_KEY", "dummy")
        body = {
            "model": model or "default",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Skill 加载
# ---------------------------------------------------------------------------

def load_skills(router_path: str | Path) -> list[dict]:
    """加载 router.yaml 中所有 skill 记录。"""
    with open(router_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("skills", [])


def _skill_summary(skill: dict) -> str:
    """生成 skill 的单行摘要，供 LLM 判断。"""
    return (
        f"[{skill['name']}] "
        f"slot={skill.get('slot','?')} "
        f"invoke={skill.get('invoke','?')} "
        f"desc={skill.get('description_model', skill.get('description_human',''))[:80]}"
    )


# ---------------------------------------------------------------------------
# 核心路由
# ---------------------------------------------------------------------------

def llm_route_skills(
    query: str,
    router_path: str | Path,
    *,
    invoke_filter: str | None = None,
    llm_model: str | None = None,
) -> list[str]:
    """用 LLM 判断 query 应触发哪些 skill。

    Args:
        query: 用户原始 query
        router_path: router.yaml 路径
        invoke_filter: 只考虑特定 invoke 的 skill（如 "model"）
        llm_model: LLM 模型名（None = 用默认）

    Returns:
        命中的 skill 名称列表（去重，可能为空）
    """
    skills = load_skills(router_path)
    if invoke_filter:
        skills = [s for s in skills if s.get("invoke") == invoke_filter]

    active = [s for s in skills if s.get("status") == "active"]
    lines = "\n".join(_skill_summary(s) for s in active)

    system_prompt = (
        "你是一个技能路由决策器。根据用户 query，从候选列表中选择最合适的 skill 名称。\n"
        "规则：\n"
        "1. 只返回 skill 名称（一个或多个，用 | 分隔），不要解释。\n"
        "2. 如果没有匹配的 skill，返回 NONE。\n"
        "3. 优先选 model 类型的 skill（可自动触发），user 类型仅当明确涉及人工操作时选。\n"
        "4. 最多返回 3 个 skill，优先选最特定的那个。\n"
        "示例：\n"
        "  query: '我想把今天的经验写回中枢'\n"
        "  候选: [...memory-hub-card-promotion...] [...github-star-distill...]\n"
        "  返回: memory-hub-card-promotion\n"
    )

    user_prompt = f"候选 skill：\n{lines}\n\n用户 query：{query}\n\n请判断："

    raw = _llm_complete(
        f"system: {system_prompt}\n\n{user_prompt}",
        model=llm_model,
    )

    if not raw or raw.upper() == "NONE":
        return []

    # 解析 skill 名称（支持 | 分隔、换行分隔、逗号分隔）
    import re
    names = re.split(r"[\|\n,]+", raw)
    result = []
    name_set = set()
    for n in names:
        n = n.strip().strip("[]* ")
        if n and n not in name_set:
            # 验证该名称确实在 router.yaml 中存在
            if any(s["name"] == n for s in active):
                result.append(n)
                name_set.add(n)
    return result


def fallback_keyword_route(query: str, skills: list[dict]) -> list[str]:
    """降级路由：基于子串匹配的关键字路由（当 LLM 不可用时使用）。"""
    import re

    hits: list[tuple[str, int]] = []
    for s in skills:
        if s.get("status") != "active":
            continue
        for t in s.get("trigger", []):
            if t in query:
                weight = s.get("weight", 1.0)
                hits.append((s["name"], int(weight * 10)))
                break
    # 按权重降序
    hits.sort(key=lambda x: -x[1])
    return [n for n, _ in hits[:3]]
